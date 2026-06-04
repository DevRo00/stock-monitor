import os
import time
import requests
import re
import schedule
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from email.utils import parsedate_to_datetime

# ==========================================
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
CHECK_INTERVAL_HOURS = int(os.environ.get("CHECK_INTERVAL_HOURS", "4"))
TH_TZ = timezone(timedelta(hours=7))

TARGETS = [
    {"name": "Jensen Huang", "queries": ["Jensen Huang", "Jensen Huang NVIDIA", "Jensen Huang says", "Jensen Huang interview", "Jensen Huang keynote", "Jensen Huang AI chip", "Nvidia CEO Jensen"], "role": "CEO NVIDIA", "emoji": "🟢"},
    {"name": "Elon Musk", "queries": ["Elon Musk stock buy", "Elon Musk invest company"], "role": "CEO Tesla/SpaceX/xAI", "emoji": "🔵"},
    {"name": "Donald Trump", "queries": ["Trump stock market", "Trump tariff stock"], "role": "President USA", "emoji": "🔴"},
    {"name": "Cathie Wood", "queries": ["Cathie Wood buy stock", "Cathie Wood ARK invest"], "role": "CEO ARK Invest", "emoji": "🟡"},
    {"name": "Warren Buffett", "queries": ["Warren Buffett buy stock", "Buffett Berkshire invest"], "role": "CEO Berkshire Hathaway", "emoji": "🟠"},
]

# ticker + ชื่อเต็มของบริษัท (ครอบคลุมหุ้นที่คนดังมักพูดถึง)
STOCK_MAP = {
    # ══════════════════════════════════════
    # 🔵 AI / GPU / Semiconductor หลัก
    # ══════════════════════════════════════
    "NVDA": ["NVDA", "Nvidia"],
    "AMD":  ["AMD", "Advanced Micro Devices"],
    "INTC": ["INTC", "Intel"],
    "QCOM": ["QCOM", "Qualcomm"],
    "MRVL": ["MRVL", "Marvell"],
    "ARM":  ["ARM Holdings"],
    "SMCI": ["SMCI", "Super Micro"],
    "AVGO": ["AVGO", "Broadcom"],
    "TSM":  ["TSM", "TSMC", "Taiwan Semiconductor"],
    "AMAT": ["AMAT", "Applied Materials"],
    "ASML": ["ASML"],
    "LRCX": ["LRCX", "Lam Research"],
    "MU":   ["MU", "Micron"],
    "KLAC": ["KLAC", "KLA"],
    "ON":   ["ON Semiconductor", "onsemi"],
    "WOLF": ["WOLF", "Wolfspeed"],
    "SWKS": ["SWKS", "Skyworks"],
    "MCHP": ["MCHP", "Microchip Technology"],
    "TXN":  ["TXN", "Texas Instruments"],
    "ADI":  ["ADI", "Analog Devices"],
    "NXPI": ["NXPI", "NXP Semiconductors"],
    "STM":  ["STM", "STMicroelectronics"],
    "MPWR": ["MPWR", "Monolithic Power"],
    "ONTO": ["ONTO", "Onto Innovation"],
    "COHR": ["COHR", "Coherent"],
    "LITE": ["LITE", "Lumentum"],
    "ACLS": ["ACLS", "Axcelis"],
    "UCTT": ["UCTT", "Ultra Clean"],
    "FORM": ["FORM", "FormFactor"],
    "ENTG": ["ENTG", "Entegris"],
    "AMKR": ["AMKR", "Amkor"],
    "CRUS": ["CRUS", "Cirrus Logic"],
    "MTSI": ["MTSI", "MACOM"],
    "POWI": ["POWI", "Power Integrations"],
    "SITM": ["SITM", "SiTime"],
    "AMBA": ["AMBA", "Ambarella"],
    "ALGM": ["ALGM", "Allegro MicroSystems"],
    "DIOD": ["DIOD", "Diodes"],
    "SLAB": ["SLAB", "Silicon Labs"],
    "RMBS": ["RMBS", "Rambus"],
    "SIGI": ["SIGI", "Selective Insurance"],
    "IPGP": ["IPGP", "IPG Photonics"],

    # ══════════════════════════════════════
    # 🟣 AI Infrastructure / Data Center
    # ══════════════════════════════════════
    "VRT":  ["VRT", "Vertiv"],
    "DELL": ["DELL", "Dell"],
    "HPE":  ["HPE", "Hewlett Packard Enterprise"],
    "ANET": ["ANET", "Arista Networks"],
    "CRDO": ["CRDO", "Credo Technology"],
    "CIEN": ["CIEN", "Ciena"],
    "PSTG": ["PSTG", "Pure Storage"],
    "NTAP": ["NTAP", "NetApp"],
    "WDC":  ["WDC", "Western Digital"],
    "STX":  ["STX", "Seagate"],
    "EQIX": ["EQIX", "Equinix"],
    "DLR":  ["DLR", "Digital Realty"],
    "AMT":  ["AMT", "American Tower"],
    "IREN": ["IREN", "Iris Energy"],
    "CORZ": ["CORZ", "Core Scientific"],

    # ══════════════════════════════════════
    # 🟢 Big Tech
    # ══════════════════════════════════════
    "AAPL": ["AAPL", "Apple"],
    "MSFT": ["MSFT", "Microsoft"],
    "GOOG": ["GOOG", "GOOGL", "Google", "Alphabet"],
    "AMZN": ["AMZN", "Amazon"],
    "META": ["META", "Meta", "Facebook"],
    "NFLX": ["NFLX", "Netflix"],
    "ORCL": ["ORCL", "Oracle"],
    "IBM":  ["IBM"],
    "SAP":  ["SAP"],
    "CSCO": ["CSCO", "Cisco"],

    # ══════════════════════════════════════
    # 🟡 AI Software / SaaS / Cloud
    # ══════════════════════════════════════
    "CRM":  ["CRM", "Salesforce"],
    "ADBE": ["ADBE", "Adobe"],
    "SNOW": ["SNOW", "Snowflake"],
    "DDOG": ["DDOG", "Datadog"],
    "MDB":  ["MDB", "MongoDB"],
    "GTLB": ["GTLB", "GitLab"],
    "CFLT": ["CFLT", "Confluent"],
    "ESTC": ["ESTC", "Elastic"],
    "SUMO": ["SUMO", "Sumo Logic"],
    "AI":   ["C3.ai"],
    "BBAI": ["BBAI", "BigBear"],
    "SOUN": ["SOUN", "SoundHound"],
    "AIRS": ["AIRS", "Airsculpt"],
    "GFAI": ["GFAI", "Guardforce AI"],
    "SYNTX":["Synthetix"],
    "PATH": ["PATH", "UiPath"],
    "APPF": ["APPF", "AppFolio"],
    "HUBS": ["HUBS", "HubSpot"],
    "SHOP": ["SHOP", "Shopify"],
    "TWLO": ["TWLO", "Twilio"],
    "ZM":   ["ZM", "Zoom"],
    "DOCU": ["DOCU", "DocuSign"],
    "COUP": ["COUP", "Coupa"],
    "BRZE": ["BRZE", "Braze"],
    "PCOR": ["PCOR", "Procore"],
    "TOST": ["TOST", "Toast"],
    "BILL": ["BILL"],
    "APPN": ["APPN", "Appian"],
    "ALTR": ["ALTR", "Altair"],
    "AZPN": ["AZPN", "Aspen Technology"],
    "PTC":  ["PTC"],
    "ANSS": ["ANSS", "Ansys"],
    "CDNS": ["CDNS", "Cadence"],
    "SNPS": ["SNPS", "Synopsys"],
    "MANH": ["MANH", "Manhattan Associates"],
    "VEEV": ["VEEV", "Veeva"],
    "NUAN": ["NUAN", "Nuance"],
    "PLTR": ["PLTR", "Palantir"],

    # ══════════════════════════════════════
    # 🔴 Cybersecurity
    # ══════════════════════════════════════
    "NET":  ["NET", "Cloudflare"],
    "ZS":   ["ZS", "Zscaler"],
    "CRWD": ["CRWD", "CrowdStrike"],
    "PANW": ["PANW", "Palo Alto"],
    "FTNT": ["FTNT", "Fortinet"],
    "OKTA": ["OKTA"],
    "S":    ["SentinelOne"],
    "TENB": ["TENB", "Tenable"],
    "VRNS": ["VRNS", "Varonis"],
    "QLYS": ["QLYS", "Qualys"],
    "RPD":  ["RPD", "Rapid7"],

    # ══════════════════════════════════════
    # 🚀 Space / Aerospace / Defense
    # ══════════════════════════════════════
    "RKLB": ["RKLB", "Rocket Lab"],
    "ASTS": ["ASTS", "AST SpaceMobile"],
    "LUNR": ["LUNR", "Intuitive Machines"],
    "MNTS": ["MNTS", "Momentus"],
    "RDW":  ["RDW", "Redwire"],
    "SPCE": ["SPCE", "Virgin Galactic"],
    "ASTR": ["ASTR", "Astra Space"],
    "LMT":  ["LMT", "Lockheed Martin"],
    "RTX":  ["RTX", "Raytheon"],
    "NOC":  ["NOC", "Northrop Grumman"],
    "BA":   ["BA", "Boeing"],
    "GD":   ["GD", "General Dynamics"],
    "HII":  ["HII", "Huntington Ingalls"],
    "KTOS": ["KTOS", "Kratos Defense"],
    "AJRD": ["AJRD", "Aerojet"],
    "BWXT": ["BWXT", "BWX Technologies"],
    "MAXR": ["MAXR", "Maxar"],
    "PLBY": ["PLBY"],
    "ATRO": ["ATRO", "Astronics"],
    "TDY":  ["TDY", "Teledyne"],
    "HXL":  ["HXL", "Hexcel"],
    "MOOG": ["MOOG"],
    "AXON": ["AXON", "Axon Enterprise"],
    "LDOS": ["LDOS", "Leidos"],
    "BAH":  ["BAH", "Booz Allen"],
    "SAIC": ["SAIC"],
    "DRS":  ["DRS", "Leonardo DRS"],

    # ══════════════════════════════════════
    # ⚛️ Quantum Computing
    # ══════════════════════════════════════
    "IONQ": ["IONQ", "IonQ"],
    "RGTI": ["RGTI", "Rigetti"],
    "QUBT": ["QUBT", "Quantum Computing"],
    "QBTS": ["QBTS", "D-Wave"],
    "ARQQ": ["ARQQ", "Arqit Quantum"],
    "QTUM": ["QTUM"],

    # ══════════════════════════════════════
    # ⚡ EV / Clean Energy Tech
    # ══════════════════════════════════════
    "TSLA": ["TSLA", "Tesla"],
    "RIVN": ["RIVN", "Rivian"],
    "LCID": ["LCID", "Lucid"],
    "NIO":  ["NIO"],
    "XPEV": ["XPEV", "XPeng"],
    "FSR":  ["FSR", "Fisker"],
    "CHPT": ["CHPT", "ChargePoint"],
    "BLNK": ["BLNK", "Blink Charging"],
    "EVGO": ["EVGO"],
    "BE":   ["BE", "Bloom Energy"],
    "FCEL": ["FCEL", "FuelCell"],
    "PLUG": ["PLUG", "Plug Power"],
    "ENPH": ["ENPH", "Enphase"],
    "SEDG": ["SEDG", "SolarEdge"],
    "ARRY": ["ARRY", "Array Technologies"],

    # ══════════════════════════════════════
    # 🤖 Robotics / Automation
    # ══════════════════════════════════════
    "ISRG": ["ISRG", "Intuitive Surgical"],
    "ABB":  ["ABB"],
    "ROK":  ["ROK", "Rockwell Automation"],
    "BRKS": ["BRKS", "Brooks Automation"],
    "TRMB": ["TRMB", "Trimble"],
    "IRBT": ["IRBT", "iRobot"],
    "AEHR": ["AEHR", "Aehr Test"],
    "RMTI": ["RMTI"],
    "ZZZZZ":["Figure AI", "1X Technologies", "Apptronik"],

    # ══════════════════════════════════════
    # 💰 Crypto / Fintech
    # ══════════════════════════════════════
    "COIN": ["COIN", "Coinbase"],
    "MSTR": ["MSTR", "MicroStrategy"],
    "SQ":   ["SQ", "Block", "Square"],
    "PYPL": ["PYPL", "PayPal"],
    "AFRM": ["AFRM", "Affirm"],
    "SOFI": ["SOFI", "SoFi"],
    "HOOD": ["HOOD", "Robinhood"],
    "MARA": ["MARA", "Marathon Digital"],
    "RIOT": ["RIOT", "Riot Platforms"],
    "HUT":  ["HUT", "Hut 8"],
    "CLSK": ["CLSK", "CleanSpark"],
    "V":    ["Visa"],
    "MA":   ["Mastercard"],

    # ══════════════════════════════════════
    # 🏦 Buffett / Value favorites
    # ══════════════════════════════════════
    "OXY":  ["OXY", "Occidental"],
    "KO":   ["KO", "Coca-Cola"],
    "CVX":  ["CVX", "Chevron"],
    "BRK":  ["Berkshire"],
    "KHC":  ["KHC", "Kraft Heinz"],
    "BAC":  ["BAC", "Bank of America"],
    "GS":   ["GS", "Goldman Sachs"],
    "JPM":  ["JPM", "JPMorgan"],
    "AXP":  ["AXP", "American Express"],

    # ══════════════════════════════════════
    # 📱 Consumer Tech / Social
    # ══════════════════════════════════════
    "UBER": ["UBER"],
    "LYFT": ["LYFT"],
    "ABNB": ["ABNB", "Airbnb"],
    "DASH": ["DASH", "DoorDash"],
    "SNAP": ["SNAP", "Snapchat"],
    "PINS": ["PINS", "Pinterest"],
    "RDDT": ["RDDT", "Reddit"],
    "SPOT": ["SPOT", "Spotify"],
    "ROKU": ["ROKU"],
    "TDOC": ["TDOC", "Teladoc"],
    "DJT":  ["DJT", "Truth Social"],
}

SEEN_TITLES = set()
NEWS_MAX_AGE_HOURS = 48  # แสดงเฉพาะข่าวไม่เกิน 48 ชั่วโมง

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
                "footer": {"text": f"Stock Monitor • {datetime.now(TH_TZ).strftime('%d/%m/%Y %H:%M')} (เวลาไทย)"}
            }]
        }, timeout=10)
        print(f"Discord {'✅' if r.status_code in [200,204] else '❌'} {r.status_code}")
    except Exception as e:
        print(f"Discord error: {e}")


def parse_pub_date(pub_date_str):
    """แปลง pubDate → datetime และ string เวลาไทย"""
    try:
        dt = parsedate_to_datetime(pub_date_str)
        dt_th = dt.astimezone(TH_TZ)
        return dt_th, dt_th.strftime("%d/%m/%Y %H:%M")
    except:
        return None, None


def is_recent(dt, max_hours=NEWS_MAX_AGE_HOURS):
    """เช็คว่าข่าวใหม่พอไหม"""
    if dt is None:
        return True  # ถ้าไม่รู้วันที่ ให้ผ่าน
    now = datetime.now(TH_TZ)
    age = now - dt.astimezone(TH_TZ)
    return age.total_seconds() < max_hours * 3600


def fetch_news(query):
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        articles = []
        items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
        for item in items[:6]:
            title = re.search(r'<title>(.*?)</title>', item)
            link = re.search(r'<link>(.*?)</link>', item)
            desc = re.search(r'<description>(.*?)</description>', item)
            pub = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if title:
                clean_desc = ""
                if desc:
                    clean_desc = desc.group(1)
                    clean_desc = re.sub(r'<[^>]+>', ' ', clean_desc)       # ตัด HTML tags
                    clean_desc = re.sub(r'https?://\S+', '', clean_desc)   # ตัด URL
                    clean_desc = re.sub(r'&[a-zA-Z]+;', ' ', clean_desc)   # ตัด HTML entities
                    clean_desc = re.sub(r'&#\d+;', ' ', clean_desc)        # ตัด numeric entities
                    clean_desc = re.sub(r'a href=.*', '', clean_desc)       # ตัด href ที่เหลือ
                    clean_desc = re.sub(r'font color=.*', '', clean_desc)   # ตัด font tags
                    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()[:250]
                dt_obj, dt_str = parse_pub_date(pub.group(1).strip()) if pub else (None, None)
                articles.append({
                    "title": re.sub(r'<[^>]+>', '', title.group(1)).strip(),
                    "url": link.group(1).strip() if link else "",
                    "description": clean_desc,
                    "pub_dt": dt_obj,
                    "pub_str": dt_str,
                })
        return articles
    except Exception as e:
        print(f"  RSS error: {e}")
        return []


def get_sentiment(text):
    t = text.lower()
    bull = ["buy","bullish","surge","rally","upgrade","beat","record","soar","profit","gain","strong","rise","outperform","raise","praise","recommends","loves","backs","supports","invests","loads up","still bullish"]
    bear = ["sell","bearish","crash","drop","downgrade","miss","loss","plunge","weak","fall","concern","risk","cut","underperform","warning","dumps","exits","sold","dumped"]
    b = sum(1 for w in bull if w in t)
    s = sum(1 for w in bear if w in t)
    if b > s: return ("📈 Bullish", 0x2ecc71)
    if s > b: return ("📉 Bearish", 0xe74c3c)
    return ("➡️ Neutral", 0x95a5a6)


def find_mentioned_stocks(text):
    """หาหุ้นที่พูดถึง โดยค้นหาทั้ง ticker และชื่อบริษัท"""
    clean = re.sub(r'https?://\S+', '', text)
    mentioned = []
    for ticker, keywords in STOCK_MAP.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', clean, re.IGNORECASE):
                mentioned.append(f"${ticker} ({keywords[0] if len(keywords) > 1 else ticker})")
                break
    return mentioned


def check_all():
    print(f"\n{'='*45}")
    print(f"🔍 [{datetime.now(TH_TZ).strftime('%Y-%m-%d %H:%M')}] เช็คข่าวคนดัง")
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

                # กรองข่าวเก่า
                if not is_recent(art["pub_dt"]):
                    print(f"    ⏭ ข่าวเก่าเกิน 48h: {art['title'][:50]}...")
                    continue

                SEEN_TITLES.add(art["title"])

                full = f"{art['title']} {art['description']}"

                if target["name"].split()[0].lower() not in full.lower() and \
                   target["name"].split()[-1].lower() not in full.lower():
                    continue

                sentiment, color = get_sentiment(full)
                stocks_mentioned = find_mentioned_stocks(full)

                if stocks_mentioned and sentiment != "➡️ Neutral":
                    found_any = True
                    print(f"    🚨 {art['title'][:60]}...")

                    desc = f"**{target['role']}** {target['emoji']}\n"
                    desc += f"_{sentiment}_\n\n"
                    desc += f"📰 **{art['title']}**\n\n"

                    if stocks_mentioned:
                        desc += f"🎯 **หุ้นที่พูดถึง:** {', '.join(stocks_mentioned)}\n\n"

                    if art['description']:
                        desc += f"📝 {art['description']}\n\n"

                    if art['pub_str']:
                        desc += f"🕐 **เวลาข่าว (ไทย):** {art['pub_str']}\n\n"

                    if art['url']:
                        desc += f"[🔗 อ่านข่าวเต็ม]({art['url']})"

                    send_discord(f"{target['emoji']} {target['name']} พูดถึงหุ้น!", desc, color)
                    time.sleep(0.5)

    if not found_any:
        print("  ✓ ไม่มีข่าวสำคัญจากคนดังรอบนี้")


def morning_summary():
    names = [f"{t['emoji']} {t['name']}" for t in TARGETS]
    send_discord(
        "🌅 Good Morning! Stock Monitor",
        f"ระบบทำงานปกติ ✅\n\n**ติดตามคนดัง:**\n" + "\n".join(names) +
        f"\n\n⏰ เช็คทุก {CHECK_INTERVAL_HOURS} ชั่วโมง",
        color=0xf39c12
    )
    check_all()


SEC_PEOPLE = {
    "Warren Buffett": {"cik": "0001067983", "name": "Berkshire Hathaway"},
    "Cathie Wood":    {"cik": "0001579982", "name": "ARK Investment"},
}

def check_sec_filings():
    """ตรวจ SEC EDGAR — จับเมื่อ Buffett/Cathie Wood ซื้อขายหุ้นจริงๆ"""
    print("\n📋 เช็ค SEC Filings...")
    
    for person, info in SEC_PEOPLE.items():
        try:
            url = f"https://data.sec.gov/submissions/CIK{info['cik'].zfill(10)}.json"
            r = requests.get(url, timeout=10, headers={"User-Agent": "StockMonitor admin@stockmonitor.com"})
            if r.status_code != 200:
                continue
            
            data = r.json()
            filings = data.get("filings", {}).get("recent", {})
            forms = filings.get("form", [])
            dates = filings.get("filingDate", [])
            accessions = filings.get("accessionNumber", [])
            descriptions = filings.get("primaryDocument", [])

            # หา filing ใหม่ใน 48 ชั่วโมง
            now = datetime.now(TH_TZ)
            for i, (form, date, acc) in enumerate(zip(forms, dates, accessions)):
                if form not in ["4", "13F-HR", "SC 13G", "SC 13D"]:
                    continue
                
                filing_dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=TH_TZ)
                age_hours = (now - filing_dt).total_seconds() / 3600
                
                if age_hours > 48:
                    continue

                acc_clean = acc.replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/full-index/{date[:4]}/{date[5:7]}/{acc_clean}/"
                
                form_label = {
                    "4": "📝 Form 4 (ซื้อ/ขายหุ้นจริง!)",
                    "13F-HR": "📊 13F (รายงานถือหุ้นรายไตรมาส)",
                    "SC 13G": "📋 SC 13G (ถือหุ้น >5%)",
                    "SC 13D": "🚨 SC 13D (ถือหุ้น >5% เชิงรุก)",
                }.get(form, form)

                msg = f"**{info['name']}**\n\n"
                msg += f"📋 {form_label}\n"
                msg += f"🕐 ยื่นเมื่อ: {filing_dt.strftime('%d/%m/%Y')} (เวลาไทย)\n\n"
                msg += f"[🔗 ดู Filing จริงบน SEC]({filing_url})"

                send_discord(
                    f"🏛️ SEC Filing: {person}",
                    msg,
                    color=0xe67e22
                )
                print(f"  🚨 SEC: {person} ยื่น {form} วันที่ {date}")
                time.sleep(0.5)

        except Exception as e:
            print(f"  SEC error [{person}]: {e}")


def check_nvidia_events():
    """ดักข่าว Jensen Huang / NVIDIA event แบบเร็วที่สุด"""
    print("\n🟢 เช็ค Jensen Huang / NVIDIA...")
    queries = [
        "Jensen Huang speaking",
        "Jensen Huang keynote today",
        "NVIDIA announcement today",
        "Jensen Huang conference",
        "Jensen Huang interview today",
    ]
    for query in queries:
        articles = fetch_news(query)
        time.sleep(0.5)
        for art in articles:
            if art["title"] in SEEN_TITLES:
                continue
            if not is_recent(art["pub_dt"], max_hours=12):  # เฉพาะ 12 ชม.ล่าสุด
                continue
            SEEN_TITLES.add(art["title"])
            
            full = f"{art['title']} {art['description']}"
            if "jensen" not in full.lower() and "nvidia" not in full.lower():
                continue

            sentiment, color = get_sentiment(full)
            stocks = find_mentioned_stocks(full)

            desc = f"**CEO NVIDIA** 🟢\n_{sentiment}_\n\n"
            desc += f"📰 **{art['title']}**\n\n"
            if stocks:
                desc += f"🎯 **หุ้นที่พูดถึง:** {', '.join(stocks)}\n\n"
            if art['description']:
                desc += f"📝 {art['description']}\n\n"
            if art['pub_str']:
                desc += f"🕐 **เวลาข่าว (ไทย):** {art['pub_str']}\n\n"
            if art['url']:
                desc += f"[🔗 อ่านข่าวเต็ม]({art['url']})"

            send_discord("🟢 Jensen Huang พูด/ให้สัมภาษณ์!", desc, color)
            print(f"  🚨 Jensen: {art['title'][:60]}")
            time.sleep(0.5)


def main():
    print("🚀 Stock Monitor เริ่มทำงาน!")
    names = "\n".join([f"{t['emoji']} {t['name']} ({t['role']})" for t in TARGETS])
    send_discord(
        "✅ Stock Monitor เริ่มทำงานแล้ว!",
        f"**กำลังติดตามคนดัง:**\n{names}\n\n⏰ แจ้งเตือนทุก {CHECK_INTERVAL_HOURS} ชั่วโมง",
        color=0x00b4d8
    )
    check_all()
    schedule.every(CHECK_INTERVAL_HOURS).hours.do(check_all)
    schedule.every(1).hours.do(check_nvidia_events)   # Jensen ทุก 1 ชม.
    schedule.every(6).hours.do(check_sec_filings)     # SEC ทุก 6 ชม.
    schedule.every().day.at("08:00").do(morning_summary)
    schedule.every().day.at("22:00").do(lambda: send_discord("🌙 Evening Check", "Monitor ยังทำงานปกติ ✅", 0x6c5ce7))
    print("\n⏳ Monitor กำลังทำงาน...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
