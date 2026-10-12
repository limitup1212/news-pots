import asyncio
import html
import json
import os
import re
import sys

import edge_tts
import feedparser
import requests

FEED_URL = "https://sabrinanews.com/feed/"
VOICE = "ar-LB-LaylaNeural"
SEEN_FILE = "seen.json"
FIRST_RUN_LIMIT = 5      # عدد الأخبار عند أول تشغيل
MAX_ITEMS = 8            # أقصى عدد أخبار في ملف صوتي واحد
SUMMARY_CHARS = 250

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen[-500:], f, ensure_ascii=False)


async def make_audio(text, path):
    await edge_tts.Communicate(text, VOICE).save(path)


def send_audio(path, caption):
    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendAudio",
            data={"chat_id": CHAT_ID, "caption": caption[:1000], "title": "أخبار صابرينا"},
            files={"audio": f},
            timeout=120,
        )
    r.raise_for_status()


def main():
    feed = feedparser.parse(FEED_URL)
    if not feed.entries:
        print("لا توجد أخبار في الخلاصة")
        sys.exit(0)

    seen = load_seen()
    first_run = seen is None
    seen = seen or []

    new = [e for e in feed.entries if e.link not in seen]
    if first_run:
        new = new[:FIRST_RUN_LIMIT]
    if not new:
        print("لا جديد")
        sys.exit(0)

    new = list(reversed(new[:MAX_ITEMS]))  # الأقدم أولاً

    parts = ["أخبار جديدة من صابرينا نيوز."]
    for e in new:
        title = clean(e.title)
        summary = clean(e.get("summary", ""))[:SUMMARY_CHARS]
        parts.append(f"{title}. {summary}")
    text = "\n".join(parts)

    audio_path = "news.mp3"
    asyncio.run(make_audio(text, audio_path))

    caption = "\n".join(f"• {clean(e.title)}" for e in new)
    send_audio(audio_path, caption)

    seen.extend(e.link for e in feed.entries if e.link not in seen)
    save_seen(seen)
    print(f"أُرسل {len(new)} خبر")


if __name__ == "__main__":
    main()
