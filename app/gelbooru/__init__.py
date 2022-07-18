from app.models import ImageDB, ImagePD
from config import PROXY
from datetime import datetime

from .config import *
from .crawler import GelbooruCrawler


def parse_item(item, tag):
    content = f'[Gel #{tag}]\nid={item["id"]}'
    pics = [item[GELBOORU_IMAGE_QUALITY]]
    return ImagePD(content=content, pic_hash_list=pics, original_site='gelbooru', original_id=item['id'])


async def run():
    minute = datetime.now().minute

    if minute % REQ_INTERVAL != 0:
        return

    async with GelbooruCrawler(proxy=PROXY) as crawler:
        for tag in GELBOORU_TAGS:
            async for data in crawler.get_many_pages(tag, begin=0, end=GELBOORU_PAGE_NUM):
                for item in data['post']:
                    pd = parse_item(item, tag)
                    dct = pd.dict()
                    if not await ImageDB.filter(original_site=pd.original_site, original_id=pd.original_id):
                        await ImageDB.create(**dct)
                        yield pd
