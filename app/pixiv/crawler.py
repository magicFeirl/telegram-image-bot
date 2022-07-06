import asyncio
from random import randint

from pixivpy_async import AppPixivAPI, PixivClient

from .model import parse_illust
from .pixiv_auth import refresh


class PixivCrawler(object):
    def __init__(self, refresh_token, proxy='') -> None:
        self.client = PixivClient(proxy=proxy)
        self.aapi = AppPixivAPI(client=self.client.start())

        ACCESS_TOKEN, _ = refresh(refresh_token, proxy)
        self.aapi.set_auth(ACCESS_TOKEN, refresh_token)

    async def __aenter__(self):
        return self

    async def __aexit__(self, ex, e1, e2):
        await self.client.close()

    async def search_illust(self, tag: str, max_page=3):
        """抓取指定 Tag 的内容并返回一个生成器
        :param max_page: 抓取的最大页数
        """
        offset = 0
        page_idx = 1

        while page_idx <= max_page:
            detail = await self.aapi.search_illust(tag, offset=offset)

            offset += len(detail['illusts'])
            page_idx += 1

            for item in detail['illusts']:
                illust = parse_illust(item)
                yield illust

            # if page_idx <= max_page:
            #     await asyncio.sleep(randint(1, 3))

    async def craw_follow(self, max_page=3):
        for page in range(max_page):
            for illust in (await self.aapi.illust_follow(offset=page * 30))['illusts']:
                yield parse_illust(illust)

            # if page != max_page - 1:
            #     await asyncio.sleep(randint(1, 3))
