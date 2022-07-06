from typing import List
from app.models import ImageDB, ImagePD

from config import PROXY

from .config import *
from .crawler import PixivCrawler
from .model import Illust


async def run():
    illust_list: List[Illust] = []

    async with PixivCrawler(PIXIV_REFRESH_TOKEN, PROXY) as crawler:
        for tag in PIXIV_TAGS:
            async for illust in crawler.search_illust(tag, PIXIV_MAX_PAGE):
                if illust.score >= PIXIV_MIN_POST_SCORE or (illust.user_id in PIXIV_USER_WHITELIST):
                    illust_list.append(illust)

        if PIXIV_FOLLOW:
            async for illust in crawler.craw_follow(PIXIV_MAX_PAGE):
                illust_list.append(illust)

    for illust in illust_list:
        dct = {
            'original_site': 'pixiv',
            'original_id': illust.illust_id,
            'pic_hash_list': illust.images
        }

        if not await ImageDB.filter(**dct):
            pd = ImagePD(content=str(illust)[:254], **dct)
            await ImageDB.create(**pd.dict())
            yield pd
