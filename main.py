import asyncio
import logging
import os
from typing import List, Optional, Union
import imghdr

import httpx
from telegram import Bot, InputMediaDocument, InputMediaPhoto, InputFile
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


def get_filesizeMB(url: str):
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


def get_file_size_type(url: str):
    filesize = get_filesizeMB(url)

    if filesize < HTTP_FILE_MAXSIZE:
        return 'photo'
    elif filesize > HTTP_FILE_MAXSIZE and filesize < FILE_MAX_SIZE:
        return 'document'
    elif filesize >= FILE_MAX_SIZE:
        return 'exceed'


def download_media(url: str):
    return httpx.get(url, timeout=30).read()


def get_media_list(urls: List[str], caption):
    """获取 PhotoMediaList 或者 DocumentMediaList
    当所有文件大小 < 5MB 时，全为 PhotoMedia
    当有文件大小 >= 5MB 且 < 50 MB 时，全为 DocumentMedia
    当有文件大小 >= 50MB 时，跳过该文件
    """
    media_list = []
    section = 1
    document = False

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

        ft = get_file_size_type(url)

        if ft == 'exceed':
            continue
        elif ft == 'document':
            document = True

        filename = None

        if document:
            filename = url[url.rfind('/') + 1:]

        media = {
            'media': url,
            'caption': title,
            'filename': filename
        }

        media_list.append(media)

    media_method = InputMediaDocument if document else InputMediaPhoto

    def List2InputMedia(li):
        return media_method(**li)

    media_list = list(map(List2InputMedia, media_list))

    for idx in range(0, len(media_list), PER_MESSAGE_MAX_IMAGE_COUNT):
        yield media_list[idx:idx+PER_MESSAGE_MAX_IMAGE_COUNT]


async def do_send_message(bot: Bot, chat_id: str, photos, retry=1):
    timeout = {
        'read_timeout': 30,
        'write_timeout': 30,
        'connect_timeout': 30,
        'pool_timeout': 30
    }

    if retry > 6:
        return

    try:
        await bot.send_media_group(chat_id, photos, **timeout)  # type: ignore
    except RetryAfter as e:
        after = e.retry_after
        logger.info('发送消息过于频繁，将于 %s 秒后进行第 %s 尝试' % (after, retry))
        await asyncio.sleep(after)
        await do_send_message(bot, chat_id, photos, retry + 1)
    except BadRequest as e:
        exstr = str(e)
        errors = ['wrong file', 'wrong type', 'photo_invalid_dimensions']

        logger.info('Bad Request %s', e)

        if list(filter(lambda e: exstr.find(e) != -1, errors)):
            downloaded_photos = []
            logger.info('发送图片失败，尝试下载后发送 %s', retry)

            for photo in photos:
                obj = photo.media
                caption = photo.caption
                media_obj = None
                filename = None

                if isinstance(photo.media, str):
                    url = photo.media
                    obj = download_media(photo.media)
                    filename = url[url.rfind('/') + 1:]
                elif isinstance(photo.media, bytes):
                    filename = 'wth.' + str(imghdr.what('', photo.media))

                if isinstance(photo, InputMediaDocument) or exstr.find('photo_invalid_dimensions') != -1:
                    # filename arg doesn't work
                    media_obj = InputMediaDocument(obj, caption=caption)
                elif isinstance(photo, InputMediaPhoto):
                    media_obj = InputMediaPhoto(obj, caption=caption)

                if media_obj:
                    downloaded_photos.append(media_obj)

            await do_send_message(bot, chat_id, downloaded_photos, retry + 1)


async def send_message(bot: Bot, chat_id, message: str, urls: Optional[List[str]] = None, document=False, download=False):
    """发送消息，多块消息只要有一个被发送成功则视整个消息发送成功"""

    if not urls:
        await bot.send_message(chat_id, message)
        return

    for data in get_media_list(urls, message):
        await do_send_message(bot, chat_id, data)


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

    reason = ''

    try:
        await send_message(bot, chat_id, str(message), img_list)
    except TimedOut:
        reason = 'time out'

    if reason:
        await orm.update(retry=F('retry') + 1, send_successed=False, reason=reason)
        logger.info('发送失败: %s', reason)
    else:
        await orm.update(retry=F('retry') + 1, send_successed=True, reason='')
        logger.info('发送成功')

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
