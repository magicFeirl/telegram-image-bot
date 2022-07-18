# 推送图片的 tags
GELBOORU_TAGS = ['a', 'b']

# 爬取页数
GELBOORU_PAGE_NUM = 1

# 图片质量
# file_url: 原图
# sample_url: 压缩图
GELBOORU_IMAGE_QUALITY = 'file_url'  # or sample_url

# 因为 Gelbooru 限制了 API 请求次数（目测是 110 次每天），所以需要减少请求次数
# 每隔多少分钟请求 Gelbooru，取值为 1 - 59
REQ_INTERVAL = 20

# API KEY
# 在 https://gelbooru.com/index.php?page=account&s=options 中
API_KEY = ''
USER_ID = ''