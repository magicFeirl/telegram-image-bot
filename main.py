import asyncio
import logging
import os
from typing import List, Optional

import httpx

import telegram
from telegram import Bot, InputMediaDocument, InputMediaPhoto
from telegram.error import BadRequest, RetryAfter, TimedOut
from tortoise import run_async
from tortoise.expressions import F

from app.models import ImageDB
from app.nico import config as nico_config
from app.nico.crawler import NSCrawler
from app.pixiv.config import PIXIV_REVERSE_PROXY
from config import *
from run_crawlers import init_db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


# 发现 tg 有提供常量...
FILE_MAX_SIZE = 50
HTTP_FILE_MAXSIZE = 5
PER_MESSAGE_MAX_IMAGE_COUNT = 10

os.environ['HTTP_PROXY'] = PROXY
os.environ['HTTPS_PROXY'] = PROXY


def get_filesizeMB(url):
    # 可以添加返回文件类型功能
    resp = httpx.head(url, proxies=PROXY)

    if 'content-length' in resp.headers:
        length = int(resp.headers['content-length'])
        return round(length / 1024 / 1024, 2)
    else:
        return -1


def get_media_list(urls: List[str], caption, document=False):
    """获取 PhotoMediaList 或者 DocumentMediaList
    当所有文件大小 < 5MB 时，全为 PhotoMedia
    当有文件大小 >= 5MB 且 < 50 MB 时，全为 DocumentMedia
    当有文件大小 >= 50MB 时，跳过该文件
    """
    media_list = []
    section = 1
    filesize_exceed = False
    filesize_exceed_max = False

    for idx, img in enumerate(urls):
        # 仅一个 caption 或者 11n 个 caption 设置标题
        title = None
        # idx = 0, true; idx = 10, true, idx = 20, true; ...
        # 第 idx + 1 张图片
        if idx % PER_MESSAGE_MAX_IMAGE_COUNT == 0:
            title = caption
            if len(urls) > PER_MESSAGE_MAX_IMAGE_COUNT:
                title = title + '\n\n' + f'SECTION: {section}'
                section += 1

        # 如果只发送 document 形式的图片，不获取文件大小
        # 如果之前文件大小超过 50MB，这张图片强制获取大小
        if (document or filesize_exceed) and not filesize_exceed_max:
            filesize = -1
        else:
            filesize = get_filesizeMB(img)

        # 判断文件大小是否能够通过 http 方法发送
        # 更新：因为两种类型不能 mix up，所以一旦有大小超限的数据就直接用 Document 类型
        if filesize > HTTP_FILE_MAXSIZE and filesize < FILE_MAX_SIZE:
            filesize_exceed = True
            filesize_exceed_max = False
        elif filesize >= FILE_MAX_SIZE:  # 文件大小超过 50MB，跳过该文件
            filesize_exceed_max = True
            continue

        media = {
            'media': img,
            'caption': title
        }

        media_list.append(media)

    media_method = InputMediaDocument if (
        document or filesize_exceed) else InputMediaPhoto
    media_list = list(map(lambda _: media_method(**_), media_list))

    # 最多同时只能上传十张图片
    for idx in range(0, len(media_list), PER_MESSAGE_MAX_IMAGE_COUNT):
        yield media_list[idx:idx+PER_MESSAGE_MAX_IMAGE_COUNT]


async def send_message(bot: Bot, chat_id, message: str, media_list: Optional[List[str]] = None, document=False):
    """发送消息"""
    timeout = {
        'read_timeout': 30,
        'write_timeout': 30,
        'connect_timeout': 30,
        'pool_timeout': 30
    }

    if not media_list:
        await bot.send_message(chat_id, message)
        return

    failed = []

    for media_list_section in get_media_list(media_list, message, document):
        try:
            await bot.send_media_group(chat_id, media_list_section, **timeout)
        except RetryAfter as e:
            failed.append(media_list_section)
            await asyncio.sleep(e.retry_after)

    retry = 1
    while retry <= 5 and failed:
        print('retry', retry)
        media_list_section = failed[-1]

        try:
            await bot.send_media_group(chat_id, media_list_section, **timeout)
            failed.pop()
        except RetryAfter as e:
            delay = e.retry_after
            print(f'limition exceeded, delay: {delay}s')
            await asyncio.sleep(delay)

        retry += 1


async def preprocess_message(message: ImageDB) -> List[str]:
    """预处理数据库数据
    :return: img list"""
    if message.original_site == 'nico':
        async with NSCrawler(nico_config.NICO_USER_SESS, proxy=PROXY) as crw:
            img_list = [await crw.get_source_url(message.original_id)]
    elif message.original_site == 'pixiv':
        img_list = list(map(lambda url: url.replace(
            'i.pximg.net', PIXIV_REVERSE_PROXY), message.pic_hash_list))
    else:
        img_list = message.pic_hash_list

    return img_list


async def send_message_and_update_db(bot: Bot, chat_id: str, message: ImageDB):
    """包装发送消息方法并更新数据库"""
    img_list = await preprocess_message(message)

    original_site = message.original_site
    original_id = message.original_id
    orm = ImageDB.filter(
        original_site=original_site, original_id=original_id)

    print(original_site, original_id, '开始发送')

    sended = False
    reason = ''

    try:
        await send_message(bot, '-609419368', str(message), img_list)
        await orm.update(retry=F('retry') + 1, send_successed=True, reason='')
        sended = True
        print('发送成功')
    except TimedOut:
        reason = 'time out'
    except BadRequest as e:
        reason = 'bad request'
        # 如果遇到 wrong file 或者 wrong type 的异常，直接发送原消息并提示
        exstr = str(e)
        errors = ['wrong file', 'wrong type']

        if filter(lambda e: exstr.find(e) != -1, errors):
            message_with_error = str(
                message) + '\n\n发送图片失败: TG 无法处理图片 URL，请点击下面的链接访问原图。\n' + '\n'.join(img_list)

            await send_message(bot, '-609419368', message_with_error)
            await orm.update(retry=MESSAGE_MAX_RETRY, send_successed=False, reason='wrong file, fatual error.')

    if not sended:
        print(reason)
        await orm.update(retry=F('retry') + 1, reason=reason)


async def main():
    await init_db()
    bot = telegram.Bot(TOKEN)

    async with bot:
        async for message in ImageDB.filter(send_successed=False, retry__lt=MESSAGE_MAX_RETRY):
            for chat_id in CHAD_ID_LIST:
                await send_message_and_update_db(bot, chat_id, message)


if __name__ == '__main__':
    run_async(main())
