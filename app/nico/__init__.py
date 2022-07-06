from app.models import ImageDB, ImagePD
from config import PROXY

from .config import *
from .crawler import NSCrawler


def parse_message(info):
    username = info['nickname']
    title = info['title']
    description = info['description'][:150]
    created = '投稿时间' + info['created']
    sid = info['id']
    tags = ['#' + tag['name'] for tag in info['tag_list']['tag']]

    content = 'im' + sid + '\n' + title + '\n'
    content += '投稿者: ' + username + '\n'
    content += description + '\n\n'
    content += ' | '.join(tags) + '\n\n' + created

    return content


async def run():
    async with NSCrawler(NICO_USER_SESS, proxy=PROXY) as crawler:
        for tag in NICO_TAGS:
            async for imlist in crawler.get_many_pages(tag, 1, NICO_PAGE_NUM):
                for im in imlist:
                    dct = {
                        'original_site': 'nico',
                        'original_id': im,
                    }

                    if not await ImageDB.filter(**dct):
                        info = await crawler.get_info(im)

                        if info['user_id'] in NICO_USER_BLACKLIST:  # type: ignore
                            continue

                        content = parse_message(info)[:250]
                        pd = ImagePD(content=content, pic_hash_list=[], **dct)
                        await ImageDB.create(**pd.dict())

                        yield pd
