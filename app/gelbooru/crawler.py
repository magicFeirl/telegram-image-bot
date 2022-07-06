from typing import Optional

import aiohttp
from aiohttp import TCPConnector


class GelbooruCrawler(object):
    def __init__(self, proxy: Optional[str] = ''):
        self.proxy = proxy

        self.session = aiohttp.ClientSession(connector=TCPConnector(ssl=False))

    async def __aenter__(self):
        return self

    async def close(self):
        await self.session.close()

    async def __aexit__(self, ex1, e2, e3):
        await self.close()

    async def get_one_page(self, tags: str, page: int, limit: int = 42):
        api = 'https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1'

        params = {
            'tags': tags,
            'pid': page,
            'limit': limit
        }

        headers = {
            'user-agent': 'wasp',
            'cookie': 'fringeBenefits=yup'
        }

        async with self.session.get(api, params=params, headers=headers, proxy=self.proxy) as resp:
            return await resp.json()

    async def get_many_pages(self, tags: str, begin: int, end: int, limit: int = 42):
        for page in range(begin, end):
            yield await self.get_one_page(tags, page, limit)
