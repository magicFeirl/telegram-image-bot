# import logging
from typing import List, Optional

from aiohttp import ClientSession, TCPConnector
from lxml.html import fromstring

# logging.Logger = 

def get_id(sid: str):
    if sid.startswith('im'):
        sid = sid[2:]

    return sid


class NSCrawler():
    def __init__(self, user_sess: Optional[str] = '', session: Optional[ClientSession] = None, proxy: Optional[str] = None):
        self.session = session or ClientSession(
            connector=TCPConnector(ssl=False))
        self.proxy = proxy
        self.headers = {
            # 'Host': 'seiga.nicovideo.jp',
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                           ' AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/87.0.4280.141 Safari/537.36'),
            # image_search_sort item 指定按投稿时间排序
            'Cookie': f'user_session={user_sess}; sort_search_image_keyword=image_created;image_search_sort=image_created;'
        }

    async def __aenter__(self):
        return self

    async def close(self):
        await self.session.close()

    async def __aexit__(self, ex1, e2, e3):
        await self.close()

    async def request(self, url):
        async with self.session.get(url, proxy=self.proxy, headers=self.headers) as resp:
            if 'content-type' in resp.headers:
                ctype = resp.headers['content-type']
            else:
                # print(resp.headers)
                ctype = ''

            if 'application/json' in ctype:
                return await resp.json()

            return await resp.text()

    async def get_one_page(self, tags: str, pn: int) -> List[str]:
        """
        :return:
           [1, 2, ...]
        """

        url = f'https://seiga.nicovideo.jp/tag/{tags}?page={pn}'

        try:
            html = await self.request(url)
            es = fromstring(html)
            im_xpath = '//li[@class="list_item list_no_trim2"]/a/@href'

            return [item.replace('/seiga/im', '') for item in es.xpath(im_xpath)]
        except Exception as e:
            # logging.error(f'[NICO] {tags} 请求第 {pn} 页数据出错:', e)
            return []

    async def get_many_pages(self, tags: str, begin: int, end: int):
        if end == begin:
            end += 1

        for pn in range(begin, end):
            im_list = await self.get_one_page(tags, pn)

            if not im_list:
                return

            yield im_list

    async def get_info(self, sid: str):
        id = get_id(sid)

        api = f'https://sp.seiga.nicovideo.jp/ajax/seiga?id={id}'

        json_data = await self.request(api)

        if 'errors' in json_data:
            # logging.error('[NICO]%s 请求图片信息出错: %s', id, json_data['errors'])
            return []

        return json_data['target_image']

    async def get_source_url(self, sid: str):
        id = get_id(sid)
        # 如果用户未登录默认使用缩略图
        source_url = f'https://lohas.nicoseiga.jp/thumb/{id}i'
        api = f'https://seiga.nicovideo.jp/image/source?id={id}'

        async with self.session.get(api, headers=self.headers, proxy=self.proxy, allow_redirects=False) as resp:
            if 'location' in resp.headers:
                location = resp.headers['location']
                if 'lohas.nicoseiga.jp' in location:
                    source_url = location.replace('/o/', '/priv/')

        return source_url

    async def get_tag_list(self, sid: str):
        id = get_id(sid)
        api = f'https://seiga.nicovideo.jp/ajax/illust/tag/list?id={id}'
        json_data = await self.request(api)

        if 'errors' in json_data:
            # logging.error('[NICO]%s 请求 tag list 失败: %s', id, json_data['errors'])
            return []

        return json_data['tag_list']
