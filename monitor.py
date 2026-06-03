import os
import time
import requests
import re
import schedule
from datetime import datetime
from urllib.parse import quote

# ==========================================
# ตั้งค่าใน Railway Environment Variables
# ==========================================
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
CHECK_INTERVAL_HOURS = int(os.environ.get("CHECK_INTERVAL_HOURS", "4"))

# หุ้นที่ติดตาม
WATCHLIST = [
    "RKLB", "ASTS", "LUNR",
    "NVDA", "AMD", "QCOM",
    "IONQ", "RGTI", "QUBT",
    "PLTR", "TSLA",
]

INFLUENCERS = [
    "Elon Musk", "Cathie Wood", "Warren Buffett",
    "Michael Burry", "Jim Cramer", "Ray Dalio",
    "Chamath", "Saylor",
]

SEEN_TITLES = set()

# ==========================================

def send_discord(title, description, color=0x00b4d8):
    """ส่งข้อความผ่าน Discord Webhook แบบ Embed สวยงาม"""
    if not DISCORD_WEBHOOK_URL:
        print(f"[NO WEBHOOK] {title}")
        return
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json={
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "footer": {"text": f"Stock Monitor • {datetime.now().strftime('%d/%m/%Y %H:%M')}"}
            }]
        }, timeout=10)
        print(f"Discord {'✅' if r.status_code in [200, 204] else '❌'} {r.status_code}")
    except Exception as e:
        print(f"Discord error: {e}")


def fetch_google_news(query):
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if r.status_code != 200:
            return []
        articles = []
        items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
        for item in items[:5]:
            title = re.search(r'<title>(.*?)</title>', item)
            link = re.search(r'<link>(.*?)</link>', item)
            desc = re.search(r'<description>(.*?)</description>', item)
            if title:
                articles.append({
                    "title": re.sub(r'<[^>]+>', '', title.group(1)).strip(),
                    "url": link.group(1).strip() if link else "",
                    "description": re.sub(r'<[^>]+>', '', desc.group(1)).strip()[:200] if desc else "",
                })
        return articles
    except Exception as e:
        print(f"  RSS error [{query}]: {e}")
        return []


def get_sentiment(text):
    t = text.lower()
    bull = ["surge","rally","bullish","buy","upgrade","beat","record","soar","growth","profit","gain","strong","rise","outperform","raised"]
    bear = ["crash","drop","bearish","sell","downgrade","miss","loss","plunge","weak","fall","concern","risk","cut","underperform","warning"]
    b = sum(1 for w in bull if w in t)
    s = sum(1 for w in bear if w in t)
    if b > s: return ("📈 Bullish", 0x2ecc71)   # สีเขียว
    if s > b: return ("📉 Bearish", 0xe74c3c)   # สีแดง
    return ("➡️ Neutral", 0x95a5a6)             # สีเทา


def check_influencer(text):
    return [p for p in INFLUENCERS if p.lower() in text.lower()]


def check_all():
    print(f"\n{'='*45}")
    print(f"🔍 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] เริ่มเช็คข่าว")
    print(f"{'='*45}")

    alerts = []

    for ticker in WATCHLIST:
        articles = fetch_google_news(f"{ticker} stock")
        time.sleep(1)
        for art in articles:
            if art["title"] in SEEN_TITLES:
                continue
            SEEN_TITLES.add(art["title"])
            full = f"{art['title']} {art['description']}"
            sentiment, color = get_sentiment(full)
            influencers = check_influencer(full)
            if influencers or "Neutral" not in sentiment:
                alerts.append({**art, "ticker": ticker, "sentiment": sentiment, "color": color, "influencers": influencers})
                print(f"  🚨 {ticker} {sentiment} | {art['title'][:55]}...")

    for query in ["Elon Musk stock", "Cathie Wood buy sell", "Warren Buffett invest"]:
        articles = fetch_google_news(query)
        time.sleep(1)
        for art in articles:
            if art["title"] not in SEEN_TITLES:
                SEEN_TITLES.add(art["title"])
                for ticker in WATCHLIST:
                    if ticker in art["title"] or ticker in art["description"]:
                        sentiment, color = get_sentiment(art["title"])
                        alerts.append({**art, "ticker": ticker, "sentiment": sentiment, "color": color, "influencers": check_influencer(query)})

    if alerts:
        # ส่งทีละ alert เป็น embed สวยๆ
        for a in alerts[:5]:
            desc = f"**{a['sentiment']}**\n\n"
            desc += f"📰 {a['title']}\n\n"
            if a['influencers']:
                desc += f"👤 พูดถึงโดย: **{', '.join(a['influencers'])}**\n\n"
            if a['url']:
                desc += f"[🔗 อ่านข่าวเต็ม]({a['url']})"
            send_discord(f"${a['ticker']} Alert", desc, a['color'])
            time.sleep(0.5)
        print(f"\n✅ ส่ง Discord แล้ว ({len(alerts)} alerts)")
    else:
        print("  ✓ ไม่มีข่าวสำคัญรอบนี้")

    return alerts


def morning_summary():
    send_discord(
        "🌅 Good Morning! Stock Summary",
        f"Monitor ทำงานปกติ ✅\n\n🎯 **ติดตาม:** {', '.join(WATCHLIST)}\n⏰ เช็คทุก {CHECK_INTERVAL_HOURS} ชั่วโมง",
        color=0xf39c12
    )
    check_all()


def main():
    print("🚀 Stock Monitor Bot เริ่มทำงาน!")
    print(f"📋 Watchlist: {', '.join(WATCHLIST)}")
    print(f"⏰ เช็คทุก {CHECK_INTERVAL_HOURS} ชั่วโมง")
    print(f"🎮 Discord Webhook: {'✅ มี' if DISCORD_WEBHOOK_URL else '❌ ยังไม่ได้ตั้งค่า'}\n")

    send_discord(
        "✅ Stock Monitor เริ่มทำงานแล้ว!",
        f"📋 ติดตาม **{len(WATCHLIST)} หุ้น**\n⏰ แจ้งเตือนทุก **{CHECK_INTERVAL_HOURS} ชั่วโมง**\n🎯 {', '.join(WATCHLIST)}",
        color=0x00b4d8
    )

    check_all()

    schedule.every(CHECK_INTERVAL_HOURS).hours.do(check_all)
    schedule.every().day.at("08:00").do(morning_summary)
    schedule.every().day.at("22:00").do(lambda: send_discord("🌙 Evening Check", "Monitor ยังทำงานปกติ ✅", 0x6c5ce7))

    print("\n⏳ Monitor กำลังทำงาน...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
