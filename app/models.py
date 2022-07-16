from typing import List, Optional

from pydantic import BaseModel
from tortoise import fields, models


class ImageDB(models.Model):
    id = fields.IntField(pk=True)
    content = fields.CharField(255)
    pic_hash_list = fields.JSONField()
    original_site = fields.CharField(max_length=10, index=True)
    original_id = fields.CharField(max_length=25, index=True)
    send_at = fields.DatetimeField(auto_now_add=True)
    send_successed = fields.BooleanField(default=False)
    retry = fields.IntField(default=0)
    reason = fields.CharField(max_length=50, default='')

    def __str__(self):
        return f'{self.content}'

    def __repr__(self):
        return f'{self.content}\n\n{self.original_site} - {self.original_id}\n{ self.send_at}\n{self.send_successed}'

# pydantic creator doesn't work on pyright lint, so just written a pydantic model of ImageDB


class ImagePD(BaseModel):
    content: str
    pic_hash_list: List[str]
    original_site: str
    original_id: str

    def __str__(self):
        pic_number = len(self.pic_hash_list)
        return self.content + f'\npic number: {pic_number}\n'

# TODO: 添加一个新表/字段，实现记录推送成功的人/群的ID，以避免多消息推送其中部分失败无法重发的问题
