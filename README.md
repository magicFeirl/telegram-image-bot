## Telegram 图片推送 bot

**支持多种网站推送**
- [Pixiv](https://www.pixiv.net/)
- [Nico Seiga](http://seiga.nicovideo.jp/)
- [Twitter](https://twitter.com/home)
- [Gelbooru](https://gelbooru.com/)

**其它功能**
* 消息自动重发
* 当图片数量过多时支持图片分段发送
* 判断图片大小以选择不同的消息类型

## 开始

### 0. 依赖

1. 需要 Python3.7+
2. 运行 `pip install -r requirements.txt` 安装依赖
3. 一个能用的 TG 账号

### 1. 创建bot

1. 前往 [BotFather](https://core.telegram.org/bots#3-how-do-i-create-a-bot) 创建自己的bot
2. 获取 BotFather 给出的 token

### 2. 推送配置

**获取 chat id**

参考：[Get the Telegram channel ID (github.com)](https://gist.github.com/mraaroncruz/e76d19f7d61d59419002db54030ebe35)

如果运行 bot 时提示 chat not found，可以试试不加 `-100` 前缀。

**推送前需要把bot加入到你的频道/群，也可以私聊推送，具体取决于传入的 chat id 是哪一种。**

修改项目根目录的全局配置 `vim ~/config.py`

```python
# bot token
TOKEN = 'xxxx'

# 消息发送失败的最大重试次数
MESSAGE_MAX_RETRY = 12

# group/user/channel id 列表
CHAD_ID_LIST = ['1234567']

# 代理地址（本地使用需要设置）
PROXY = None # 'http://127.0.0.1:1081'
```

> 推送网站均为可选，可根据实际需求配置自己需要推送的网站

**Gelbooru 配置**

`vim app/gelbooru/config.py`

```python
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
```

**Pixiv 配置**

`vim app/pixiv/config.py`

```python
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
```

**Twitter 配置**

`vim app/twitter/config.py`

```python
# 目标列表Id
# 关于 LIST 参考：https://help.twitter.com/en/using-twitter/twitter-lists
TWITTER_LIST_ID = ['123456789']
# 爬取页数
TWITTER_PAGE_NUM = 5
# 只推送含图片的动态
TWITTER_ONLY_IMAGE = True

# KEY 相关，生成 Authentication Tokens 
# https://developer.twitter.com/en/portal/dashboard
# 获取方法：
# https://developer.twitter.com/en/docs/authentication/oauth-2-0/bearer-tokens
TWITTER_API_KEY = ''
TWITTER_API_KEY_SECRET = ''
TWITTER_ACCESS_TOKEN = ''
TWITTER_ACCESS_SECRET = ''
```

**N静配置**

`vim app/nico/config.py`

```python
# 要推送的图片 tags
NICO_TAGS = ['a', 'b']

# user_sess 同名 cookie，推送原图时需要
NICO_USER_SESS = ''

# 爬取页数
NICO_PAGE_NUM = 1

# 用户黑名单，该名单内的用户的作品不会被推送
NICO_USER_BLACKLIST = []
```

### 3. 运行

1. `python run_crawlers.py`  运行爬虫
2. `python main.py` 发送消息

服务器端可设置 cron 定时运行，只需编辑 `run.sh` 第一行 cd 的目录为项目在服务器的目录，然后 `sh 项目目录/run.sh` 即可。

**run.sh**

提供一个运行脚本，该脚本先执行图片爬取功能，然后执行推送，并且实现脚本单例运行。

```bash
# 修改这行为你项目的根目录地址 
cd /root/telegram-bot/th-telegram-image-bot

LOCK="LOCK"

if [ ! -f "$LOCK" ]; then
  touch $LOCK
  python run_crawlers.py
  sleep 1
  python main.py
  rm -rf $LOCK
else
  ts=`stat -c %Y LOCK`
  now=`date +%s`
  if [ $[ $now - $ts ] -gt 1800 ]; then
    rm -rf $LOCK
    echo "Lock expired, deleted"
  fi
fi

```

## TODOs
1. 只发送发送失败的消息 - group message 发送失败视为整体发送失败
2. 只有一张表
3. 爬虫提供一个 yield 方法获取来获取数据
4. 爬虫 yield 的 model 应该符合数据表的 model
5. 发送成功
6. 可在爬虫 insert 部分添加时间判断

数据库表结构 - 同 qq 推送bot