import asyncio
import logging
import os
from typing import List, Optional

import httpx
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


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# 发现 tg 有提供常量...
FILE_MAX_SIZE = 50
HTTP_FILE_MAXSIZE = 5
PER_MESSAGE_MAX_IMAGE_COUNT = 10


if PROXY:
    os.environ['HTTP_PROXY'] = PROXY
    os.environ['HTTPS_PROXY'] = PROXY


def get_filesizeMB(url):
    # 可以添加返回文件类型功能
    proxies = PROXY or None
    try:
        resp = httpx.head(url, proxies=proxies)
    except TimeoutError:
        logger.error('获取文件大小请求超时')
        return -1

    if 'content-length' in resp.headers:
        length = int(resp.headers['content-length'])
        return round(length / 1024 / 1024, 2)
    else:
        return -1


def download_media(url: str):
    return httpx.get(url).read()


def get_media_list(urls: List[str], caption, document=False, download=False):
    """获取 PhotoMediaList 或者 DocumentMediaList
    当所有文件大小 < 5MB 时，全为 PhotoMedia
    当有文件大小 >= 5MB 且 < 50 MB 时，全为 DocumentMedia
    当有文件大小 >= 50MB 时，跳过该文件
    """
    media_list = []
    section = 1
    filesize_exceed = False
    filesize_exceed_max = False

    for idx, url in enumerate(urls):
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
            filesize = get_filesizeMB(url)

        # 判断文件大小是否能够通过 http 方法发送
        # 更新：因为两种类型不能 mix up，所以一旦有大小超限的数据就直接用 Document 类型
        if filesize > HTTP_FILE_MAXSIZE and filesize < FILE_MAX_SIZE:
            filesize_exceed = True
            filesize_exceed_max = False
        elif filesize >= FILE_MAX_SIZE:  # 文件大小超过 50MB，跳过该文件
            filesize_exceed_max = True
            continue

        img = url
        if download:
            img = download_media(url)

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


async def send_message(bot: Bot, chat_id, message: str, media_list: Optional[List[str]] = None, document=False, download=False):
    """发送消息，多块消息只要有一个被发送成功则视整个消息发送成功"""
    timeout = {
        'read_timeout': 30,
        'write_timeout': 30,
        'connect_timeout': 30,
        'pool_timeout': 30
    }

    sended = False

    if not media_list:
        await bot.send_message(chat_id, message)
        return True

    for media_list_section in get_media_list(media_list, message, document, download):
        params = {
            'chat_id': chat_id,
            'media': media_list_section,
            **timeout
        }
        # 重发思路：
        # 先发送一次消息，成功，发下一条
        # 失败，不断尝试发送 n 次，直到发送成功

        async def retry_send_message(exstr):
            global sended
            # 分块发送的时候判断是否为 BadRequest
            # 如果遇到 wrong file 或者 wrong type 的异常，直接发送原消息并提示
            errors = ['wrong file', 'wrong type']

            if filter(lambda e: exstr.find(e) != -1, errors):
                # 潜在bug：如果 downlod = true list 内容为 bytes
                img_list: List[str] = [
                    media.media for media in media_list_section]  # type: ignore

                try:
                    logger.info('发送图片失败，尝试下载后发送')
                    await send_message(bot, chat_id, str(message), img_list, download=not download)
                    sended = True
                except Exception as e:
                    logger.error('下载失败 %s' % e)
                    message_with_error = str(
                        message) + '\n\n发送图片失败: TG 无法处理图片 URL，请点击下面的链接访问原图。\n' + '\n'.join(img_list)

                    await send_message(bot, chat_id, message_with_error)

        try:
            await bot.send_media_group(**params)
            sended = True
        except BadRequest as e:
            await retry_send_message(str(e))
        except RetryAfter as e:
            retry = 1
            await asyncio.sleep(e.retry_after)

            while retry <= 5:
                try:
                    logger.info('send message failed, retry %s' % retry)
                    await bot.send_media_group(**params)
                    sended = True
                    break
                except RetryAfter as e:
                    retry += 1
                    await asyncio.sleep(e.retry_after)
                except BadRequest as e:
                    await retry_send_message(str(e))

    return sended


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

    # 图片超过 60 张直接退出（避免消息太长出错）
    if len(img_list) > 60:
        return

    original_site = message.original_site
    original_id = message.original_id
    orm = ImageDB.filter(
        original_site=original_site, original_id=original_id)

    # 发送时标记该消息已被发送
    await orm.update(send_successed=True)

    logger.info(f'{original_site} {original_id} 开始发送')

    sended = False
    reason = ''

    try:
        sended = await send_message(bot, chat_id, str(message), img_list)
    except TimedOut:
        reason = 'time out'

    if sended:
        await orm.update(retry=F('retry') + 1, send_successed=True, reason='')
        logger.info('发送成功')
    else:
        logger.info(reason)
        await orm.update(retry=F('retry') + 1, send_successed=False, reason=reason)

    print()


async def main():
    logger.info('开始启动推送程序...')

    await init_db()
    bot = Bot(TOKEN)

    async with bot:
        logger.info('启动完成！')

        async for message in ImageDB.filter(send_successed=False, retry__lt=MESSAGE_MAX_RETRY):
            for chat_id in CHAD_ID_LIST:
                await send_message_and_update_db(bot, chat_id, message)


if __name__ == '__main__':
    run_async(main())
