# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime, timezone, timedelta

import feedparser
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "26"))
MAX_POSTS = int(os.environ.get("MAX_POSTS", "15"))

FEEDS = [
    "https://www.bayt.com/associates/rss/feed.xml?aff_id=1458967&country_list=all&jobrole_list=all",  # للتجربة فقط — احذفه بعد التأكد
    "https://www.indeed.com/rss?q=&l=Egypt",
    "https://www.indeed.com/rss?q=&l=Riyadh",
    "https://www.indeed.com/rss?q=&l=Dubai",
]


def entry_time(entry):
    for attr in ("published_parsed", "updated_parsed"):
        t = entry.get(attr)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def send_to_telegram(text):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    if not r.ok:
        print("Telegram error:", r.status_code, r.text)
    r.raise_for_status()


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items = []

    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            feed_title = feed.feed.get("title", "مصدر الوظائف")
            print(f"📡 المصدر {feed_title}: فيه {len(feed.entries)} عنصر")
        except Exception as ex:
            print(f"[خطأ في المصدر] {url}: {ex}")
            continue

        for e in feed.entries:
            t = entry_time(e)
            if t and t >= cutoff:
                items.append((t, e, feed_title))

    items.sort(key=lambda x: x[0], reverse=True)
    items = items[:MAX_POSTS]

    if not items:
        print("✅ لا توجد وظائف جديدة اليوم.")
        return

    sent = 0
    for t, e, feed_title in items:
        title = (e.get("title") or "💼 فرصة عمل جديدة").strip()
        link = (e.get("link") or "").strip()

        msg = f"💼 {title}\n🌐 المصدر: {feed_title}\n🔗 {link}"
        try:
            send_to_telegram(msg)
            sent += 1
            print(f"📤 تم النشر: {title}")
            time.sleep(1.5)
        except Exception as ex:
            print(f"[فشل الإرسال] {title}: {ex}")

    print(f"✅ انتهى. تم نشر {sent} وظيفة اليوم.")


if __name__ == "__main__":
    main()
