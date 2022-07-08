# 标签列表
PIXIV_TAGS = []

# 用户白名单，填入用户id，为空表示不启用
# 在白名单的用户的作品无论分数会被立即推送
PIXIV_USER_WHITELIST = []

# 爬取页数
PIXIV_MAX_PAGE = 5

# 推送的投稿的最小分数，低于该分数的投稿不会被推送
# 计算公式 view + bookmark * 5
PIXIV_MIN_POST_SCORE = 200

# 是否推送关注的作者
PIXIV_FOLLOW = True

# 反代地址，无需修改
PIXIV_REVERSE_PROXY = 'i.pixiv.re'

# refresh token：如何获取见链接
# https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362
PIXIV_REFRESH_TOKEN = ''
