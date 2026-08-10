# -*- coding: utf-8 -*-
import os
import re
import time
import html as html_lib
from datetime import datetime, timezone, timedelta

import feedparser
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "26"))
MAX_POSTS = int(os.environ.get("MAX_POSTS", "10"))
SUMMARY_LEN = 350

FEEDS = [
    "https://www.bayt.com/associates/rss/feed.xml?aff_id=1458967&country_list=all&jobrole_list=all",
    "https://news.google.com/rss/search?q=وظائف&hl=ar&gl=EG&ceid=EG:ar",
    "https://news.google.com/rss/search?q=توظيف&hl=ar&gl=EG&ceid=EG:ar",
    "https://news.google.com/rss/search?q=وظائف+السعودية&hl=ar&gl=EG&ceid=EG:ar",
    "https://news.google.com/rss/search?q=وظائف+الإمارات&hl=ar&gl=EG&ceid=EG:ar",
    "https://news.google.com/rss/search?q=وظائف+مصر+التعيين&hl=ar&gl=EG&ceid=EG:ar",
]


def clean_text(s, limit=SUMMARY_LEN):
    if not s:
        return ""
    s = html_lib.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > limit:
        s = s[:limit].rstrip() + " …"
    return s


def shorten(url):
    for api in (
        f"https://tinyurl.com/api-create.php?url={requests.utils.quote(url)}",
        f"https://is.gd/create.php?format=simple&url={requests.utils.quote(url)}",
    ):
        try:
            r = requests.get(api, timeout=10)
            if r.ok and r.text.strip().startswith("http"):
                return r.text.strip()
        except Exception:
            continue
    return url


def entry_time(entry):
    for attr in ("published_parsed", "updated_parsed"):
        t = entry.get(attr)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def send_to_telegram(text):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    if not r.ok:
        print("Telegram error:", r.status_code, r.text)
    r.raise_for_status()


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items, seen = [], set()

    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            feed_title = feed.feed.get("title", "مصدر الوظائف")
            print(f"📡 {feed_title}: {len(feed.entries)} عنصر")
        except Exception as ex:
            print(f"[خطأ في المصدر] {url}: {ex}")
            continue

        for e in feed.entries:
            t = entry_time(e)
            if not t or t < cutoff:
                continue
            title = (e.get("title") or "").strip()
            key = title[:80]
            if not title or key in seen:
                continue
            seen.add(key)
            items.append((t, e, feed_title))

    items.sort(key=lambda x: x[0], reverse=True)
    items = items[:MAX_POSTS]

    if not items:
        print("✅ لا توجد وظائف جديدة اليوم.")
        return

    sent = 0
    for t, e, feed_title in items:
        title = e.get("title", "💼 فرصة عمل جديدة").strip()
        summary = clean_text(e.get("summary") or e.get("description") or "")
        link = shorten((e.get("link") or "").strip())

        msg = f"💼 {title}"
        if summary:
            msg += f"\n\n📝 {summary}"
        msg += f"\n\n🌐 المصدر: {feed_title}\n🔗 {link}"

        try:
            send_to_telegram(msg)
            sent += 1
            print(f"📤 تم النشر: {title[:50]}")
            time.sleep(1.5)
        except Exception as ex:
            print(f"[فشل الإرسال] {title[:50]}: {ex}")

    print(f"✅ انتهى. تم نشر {sent} منشور اليوم.")


if __name__ == "__main__":
    main()
