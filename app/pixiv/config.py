# 必须配置 PIXIV_TAGS 和 PIXIV_REFRESH_TOKEN，其他配置可默认

# 推送图片的 tags
PIXIV_TAGS = ['a', 'b']

# refresh token
# 获取方法：https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362
PIXIV_REFRESH_TOKEN = 'dF8jpliqu0UlM519k09ICNLQQYnbLL6MBO9XuqDGEBPFAC'

# 用户白名单，填入 uid，在该名单内的用户的作品会被立即推送（无视分数）
PIXIV_USER_WHITELIST = []

# 每个 tag 爬取的最大页数
PIXIV_MAX_PAGE = 1

# 推送的投稿的最小分数，用于排除低质量的投稿
# 计算公式 view + bookmark * 5
PIXIV_MIN_POST_SCORE = 300

# 是否推送关注的作者
PIXIV_FOLLOW = False

# 反代 i.pixiv.re，目前不需要
PIXIV_REVERSE_PROXY = ''
