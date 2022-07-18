"""
运行全部爬虫，入库数据
"""
import asyncio

from tortoise import Tortoise, run_async

from app.gelbooru import run as run_gel
from app.nico import run as run_nico
from app.pixiv import run as run_pixiv
from app.twitter import run as run_twitter


async def init_db():
    db_url = 'sqlite://db.sqlite3'

    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )

    await Tortoise.generate_schemas()


funcs = {
    'Gelbooru': run_gel,
    'Nico': run_nico,
    'Twitter': run_twitter,
    'Pixiv': run_pixiv
}


async def main():
    await init_db()

    for name, func in funcs.items():
        print('=' * 30)
        print(f'开始执行 {name} 爬虫')
        try:
            async for img in func():
                print(img)
        except Exception as e:
            print(f'{name} 爬虫失败:', e)
        print('=' * 30)
        print()


if __name__ == '__main__':
    run_async(main())
