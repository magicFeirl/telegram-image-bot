from pydantic import BaseModel
from datetime import datetime

from typing import List


class TimeLine(BaseModel):
    author_name: str
    created_at: datetime
    text: str
    id: str
    photos: List[str]

    def __str__(self):
        author = self.author_name
        created_at = self.created_at
        text = self.text
        id = self.id

        return id + '\n\n' + 'author: ' + author + '\n' + 'created_at(utc+8):\n' + str(created_at) + '\n\n' + text
