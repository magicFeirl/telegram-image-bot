from typing import List

from pydantic import BaseModel


class Illust(BaseModel):
    title: str
    description: str
    illust_id: str
    tags: List[str]
    create_date: str
    user_id: str
    username: str
    images: List[str]
    score: int

    def __str__(self):
        pid = f'Pixiv ID: {self.illust_id}\n\n'
        title = f'{self.title}\n' if self.title else '(无题)'
        description = f'{self.description}\n\n' if self.description else ''
        poster = f'投稿者(id={self.user_id}): {self.username}\n\n'
        tags = f'{" | ".join(self.tags)}\n\n'
        post_at = f'投稿时间: {self.create_date}'

        return ''.join([pid, title, description, poster, tags, post_at])


def parse_illust(illust: dict) -> Illust:
    title = illust['title']
    description = illust['caption'][:50]
    illust_id = illust['id']
    tags = ['#' + tag['name'] for tag in illust['tags']]
    create_date = illust['create_date']

    view = illust['total_view']
    bookmark = illust['total_bookmarks']

    user = illust['user']
    user_id = user['id']
    name = user['name']

    meta_single_page = illust['meta_single_page']
    meta_pages = illust['meta_pages']

    if 'original_image_url' in meta_single_page:
        images = [meta_single_page['original_image_url']]
    else:
        images = [image['image_urls']['original'] for image in meta_pages]

    illust_model = Illust(**{
        'title': title,
        'description': description,
        'illust_id': illust_id,
        'tags': tags,
        'create_date': create_date,
        'user_id': user_id,
        'username': name,
        'images': images,
        'score': view + bookmark * 5
    })

    return illust_model
