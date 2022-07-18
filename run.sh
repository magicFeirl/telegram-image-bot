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
