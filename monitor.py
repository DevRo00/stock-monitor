import os
import time
import requests
import re
import schedule
from datetime import datetime
from urllib.parse import quote

# ==========================================
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
CHECK_INTERVAL_HOURS = int(os.environ.get("CHECK_INTERVAL_HOURS", "4"))

# คนดังที่ติดตาม + หุ้นที่เกี่ยวข้อง
TARGETS = [
    {
        "name": "Jensen Huang",
        "queries": ["Jensen Huang stock", "Jensen Huang NVIDIA invest", "Jensen Huang says"],
        "role": "CEO NVIDIA",
        "emoji": "🟢"
    },
    {
        "name": "Elon Musk",
        "queries": ["Elon Musk stock buy", "Elon Musk invest company", "Elon Musk praises"],
        "role": "CEO Tesla / SpaceX / xAI",
        "emoji": "🔵"
    },
    {
        "name": "Donald Trump",
        "queries": ["Trump stock market", "Trump company invest", "Trump tariff stock"],
        "role": "President USA",
        "emoji": "🔴"
    },
    {
        "name": "Cathie Wood",
        "queries": ["Cathie Wood buy stock", "Cathie Wood ARK invest", "Cathie Wood bullish"],
        "role": "CEO ARK Invest",
        "emoji": "🟡"
    },
    {
        "name": "Warren Buffett",
        "queries": ["Warren Buffett buy stock", "Buffett Berkshire invest", "Warren Buffett bullish"],
        "role": "CEO Berkshire Hathaway",
        "emoji": "🟠"
    },
]

# หุ้นที่สนใจ (ใช้จับว่าคนดังพูดถึงหุ้นที่ติดตามไหม)
WATCHLIST = ["NVDA","TSLA","RKLB","ASTS","LUNR","AMD","IONQ","RGTI","QUBT","PLTR","AAPL","META","GOOG","AMZN","MSFT"]

SEEN_TITLES = set()

# ==========================================

def send_discord(title, description, color=0x00b4d8):
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
        print(f"Discord {'✅' if r.status_code in [200,204] else '❌'} {r.status_code}")
    except Exception as e:
        print(f"Discord error: {e}")


def fetch_news(query):
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
                    "description": re.sub(r'<[^>]+>', '', desc.group(1)).strip()[:300] if desc else "",
                })
        return articles
    except Exception as e:
        print(f"  RSS error: {e}")
        return []


def get_sentiment(text):
    t = text.lower()
    bull = ["buy","bullish","surge","rally","upgrade","beat","record","soar","profit","gain","strong","rise","outperform","raise","praise","recommends","loves","backs","supports","invests"]
    bear = ["sell","bearish","crash","drop","downgrade","miss","loss","plunge","weak","fall","concern","risk","cut","underperform","warning","dumps","exits"]
    b = sum(1 for w in bull if w in t)
    s = sum(1 for w in bear if w in t)
    if b > s: return ("📈 Bullish", 0x2ecc71)
    if s > b: return ("📉 Bearish", 0xe74c3c)
    return ("➡️ Neutral", 0x95a5a6)


def find_mentioned_stocks(text):
    """หาว่าพูดถึงหุ้นตัวไหนบ้าง"""
    mentioned = []
    for ticker in WATCHLIST:
        if ticker in text.upper():
            mentioned.append(f"${ticker}")
    return mentioned


def check_all():
    print(f"\n{'='*45}")
    print(f"🔍 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] เช็คข่าวคนดัง")
    print(f"{'='*45}")

    found_any = False

    for target in TARGETS:
        print(f"\n  {target['emoji']} ค้นหา: {target['name']}...")
        
        for query in target["queries"]:
            articles = fetch_news(query)
            time.sleep(1)

            for art in articles:
                if art["title"] in SEEN_TITLES:
                    continue
                SEEN_TITLES.add(art["title"])

                full = f"{art['title']} {art['description']}"
                
                # ต้องมีชื่อคนดังจริงๆ ในข่าว
                if target["name"].split()[0].lower() not in full.lower() and \
                   target["name"].split()[-1].lower() not in full.lower():
                    continue

                sentiment, color = get_sentiment(full)
                stocks_mentioned = find_mentioned_stocks(full)

                # แจ้งเฉพาะถ้ามีหุ้นที่สนใจ หรือ sentiment ชัดเจน
                if stocks_mentioned or sentiment != "➡️ Neutral":
                    found_any = True
                    print(f"    🚨 {art['title'][:60]}...")

                    desc = f"**{target['role']}** {target['emoji']}\n\n"
                    desc += f"_{sentiment}_\n\n"
                    desc += f"📰 {art['title']}\n\n"
                    
                    if stocks_mentioned:
                        desc += f"🎯 **หุ้นที่พูดถึง:** {', '.join(stocks_mentioned)}\n\n"
                    
                    if art['description']:
                        desc += f"📝 {art['description'][:200]}...\n\n"
                    
                    if art['url']:
                        desc += f"[🔗 อ่านข่าวเต็ม]({art['url']})"

                    send_discord(
                        f"{target['emoji']} {target['name']} พูดถึงหุ้น!",
                        desc,
                        color
                    )
                    time.sleep(0.5)

    if not found_any:
        print("  ✓ ไม่มีข่าวสำคัญจากคนดังรอบนี้")


def morning_summary():
    names = [f"{t['emoji']} {t['name']}" for t in TARGETS]
    send_discord(
        "🌅 Good Morning! Stock Monitor",
        f"ระบบทำงานปกติ ✅\n\n**ติดตามคนดัง:**\n" + "\n".join(names) + f"\n\n⏰ เช็คทุก {CHECK_INTERVAL_HOURS} ชั่วโมง",
        color=0xf39c12
    )
    check_all()


def main():
    print("🚀 Stock Monitor (Celebrity Edition) เริ่มทำงาน!")
    print(f"👤 ติดตาม {len(TARGETS)} คนดัง")
    print(f"⏰ เช็คทุก {CHECK_INTERVAL_HOURS} ชั่วโมง")

    names = "\n".join([f"{t['emoji']} {t['name']} ({t['role']})" for t in TARGETS])
    send_discord(
        "✅ Stock Monitor เริ่มทำงานแล้ว!",
        f"**กำลังติดตามคนดัง:**\n{names}\n\n⏰ แจ้งเตือนทุก {CHECK_INTERVAL_HOURS} ชั่วโมง",
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
