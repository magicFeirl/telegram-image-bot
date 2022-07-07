from datetime import timedelta
import os

import tweepy

from .model import TimeLine

"""
from datetime import timedelta, datetime
import pytz
  utc8now = datetime.now(tz=pytz.timezone(
                        'Asia/Shanghai')).replace(tzinfo=None)

                    date_interval = utc8now - \
                        timedelta(minutes=config.INTERVAL)

                    date_interval = date_interval.replace(tzinfo=None)

                    if date_interval > created_at:
                        continue

                    for media in entities['media']:
                        if media['type'] == 'photo':
                            photos.append(media['media_url_https'] + ':orig')

                            
async def parse_message():
    timeline = await get_formatted_timeline()

    for item in timeline:
        author_name = item.author_name
        created_at = item.created_at
        text = item.text
        id = item.id
        photos = item.photos

        content = ('author: ' + author_name + '\n' +
                   'created_at(utc+8):\n' + str(created_at) + '\n\n' +
                   text + '\n' + 'id=' + id + '\n' +
                   ''.join([f'[CQ:image,file={photo}]' for photo in photos])
                   )

        yield content, item
"""


def parse_timeline_item(item, only_img):
    author_name = item.author.name
    # 转为 utc+8
    created_at = item.created_at + timedelta(hours=8)
    created_at = created_at.replace(tzinfo=None)
    text = item.text
    id = item.id_str
    photos = []

    has_entities = hasattr(item, 'extended_entities')

    # 如果没有 entities
    if not has_entities:
        # 且指定只返回包含图片的 twitter，直接结束函数
        if only_img:
            return
        # 否则赋值一个空 entities
        else:
            entities = {'media': []}
    else:
        entities = item.extended_entities

    for media in entities['media']:
        if media['type'] == 'photo':
            photos.append(media['media_url_https'])

    if not photos:
        return

    return TimeLine(author_name=author_name,
                    created_at=created_at, text=text, id=id, photos=photos)


class TwitterListCrawler(object):
    def __init__(self, api_key, api_key_secret, access_token, access_secret, proxy='') -> None:
        self.api_key = api_key
        self.api_key_secret = api_key_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self.proxy = proxy

    def get_timeline(self, list_id: str, count=200, pages=1, include_rts=False, only_img=True):
        """获取 count 条列表时间线数据，支持翻页"""
        if self.proxy:
            os.environ['http_proxy'] = self.proxy
            os.environ['https_proxy'] = self.proxy

        auth = tweepy.OAuthHandler(self.api_key, self.api_key_secret)
        auth.set_access_token(self.access_token, self.access_secret)

        api = tweepy.API(auth)

        for data in tweepy.Cursor(api.list_timeline, list_id=list_id, count=count, include_rts=include_rts, include_entities={'extended_entities': True}).pages(pages):
            for item in data:
                twitter = parse_timeline_item(item, only_img)

                if twitter:
                    yield twitter
