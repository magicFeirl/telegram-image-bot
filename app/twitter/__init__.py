from app.models import ImageDB, ImagePD
from config import PROXY
from .config import *

from .crawler import TwitterListCrawler

api_config = {
    'api_key': TWITTER_API_KEY,
    'api_key_secret': TWITTER_API_KEY_SECRET,
    'access_token': TWITTER_ACCESS_TOKEN,
    'access_secret': TWITTER_ACCESS_SECRET
}


async def run():
    crawler = TwitterListCrawler(proxy=PROXY, **api_config)
    for list_id in TWITTER_LIST_ID:
        for timeline in crawler.get_timeline(list_id, pages=TWITTER_PAGE_NUM, only_img=TWITTER_ONLY_IMAGE):
            dct = {
                'original_site': 'twitter',
                'original_id': timeline.id,
                'pic_hash_list': timeline.photos
            }

            if not await ImageDB.filter(**dct):
                pd = ImagePD(content=str(timeline), **dct)
                await ImageDB.create(**pd.dict())
                
                yield pd
