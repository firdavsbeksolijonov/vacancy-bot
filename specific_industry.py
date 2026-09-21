"""
hh.uz (Toshkent) — sohalar bo'yicha yangi vakansiyalarni
topib, Telegram botga yuboradi.
"""

import sqlite3
import time
import html
import re
import os
import random
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests

# ============================================================
# SOZLAMALAR
# ============================================================
BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL = 600
MAX_PER_INDUSTRY = 2
MAX_AGE_DAYS = 3
MAX_WORKERS = 8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

# ============================================================
# SOHALAR VA INDUSTRY ID LAR
# ============================================================
INDUSTRIES = {
    "💰 Moliya / Bank / Fintech": {
        "ids": ["7", "7.538", "7.539"],
        "keywords": [
            "финансовый аналитик", "financial analyst",
            "кредитный аналитик", "credit analyst",
            "аудитор", "auditor", "бухгалтер", "accountant",
            "комплаенс", "compliance", "AML", "KYC",
            "казначей", "treasury", "риск аналитик", "risk analyst",
            "инвестиционный аналитик", "investment analyst",
        ],
    },
    "⚖️ Konsalting / Huquq": {
        "ids": ["8", "8.541"],
        "keywords": [
            "консультант", "consultant", "юрист", "lawyer",
            "налоговый консультант", "tax consultant",
            "бизнес аналитик", "business analyst",
            "стратег", "strategy",
        ],
    },
    "💻 IT / Texnologiya": {
        "ids": ["7.96", "7.97", "7.98"],
        "keywords": [
            "data analyst", "дата аналитик",
            "product manager", "системный аналитик",
            "BI аналитик", "IT аналитик",
            "project manager IT",
        ],
    },
    "👥 HR / Rekruting": {
        "ids": ["27"],
        "keywords": [
            "рекрутер", "recruiter", "HR менеджер",
            "talent acquisition", "HR аналитик",
            "менеджер по персоналу", "HRBP",
        ],
    },
    "📢 Marketing / Media": {
        "ids": ["14", "14.302"],
        "keywords": [
            "маркетолог", "marketing manager",
            "бренд менеджер", "brand manager",
            "SMM менеджер", "digital маркетолог",
            "контент менеджер", "медиа планировщик",
        ],
    },
    "🛒 Savdo / E-commerce": {
        "ids": ["9"],
        "keywords": [
            "менеджер по продажам", "sales manager",
            "аккаунт менеджер", "account manager",
            "key account manager", "коммерческий менеджер",
        ],
    },
    "🚚 Logistika": {
        "ids": ["11"],
        "keywords": [
            "логист", "logistics manager",
            "supply chain", "менеджер по закупкам",
            "procurement manager", "операционный менеджер",
            "складской менеджер", "warehouse manager",
        ],
    },
}

# ============================================================
# FILTRLAR
# ============================================================
INCLUDE_TITLES = [
    "junior", "джуниор", "стажер", "стажёр",
    "intern", "trainee", "начинающий",
    "entry level", "entry-level",
    "помощник", "ассистент", "assistant",
    "младший", "молодой специалист",
    "аналитик", "analyst", "менеджер", "manager",
    "специалист", "specialist", "coordinator", "координатор",
    "officer", "executive", "associate", "consultant",
    "консультант", "юрист", "маркетолог", "рекрутер",
    "recruiter", "логист", "бухгалтер", "accountant",
    "аудитор", "auditor", "trainer", "тренер",
    "teacher", "учитель", "преподаватель",
    "sales", "продажи", "account", "аккаунт",
    "финансовый", "financial", "кредитный", "credit",
    "операционный", "operations", "project", "проект",
    "business", "бизнес", "партнер", "partner",
    "маркетинг", "marketing", "бренд", "brand",
    "digital", "SMM", "контент", "content",
    "HR", "персонал", "talent", "подбор",
    "data", "product", "систем", "system",
    "supply", "закупки", "procurement", "склад",
]

EXCLUDE_TITLES = [
    "охранник", "охрана", "security guard",
    "водитель", "шофер", "driver",
    "уборщик", "уборщица", "cleaner",
    "повар", "cook", "chef",
    "официант", "waiter", "бариста", "barista",
    "кассир", "cashier", "грузчик", "loader",
    "курьер", "courier", "delivery",
    "продавец", "продавщица", "кладовщик",
    "сварщик", "welder", "электрик", "electrician",
    "сантехник", "plumber", "строитель", "builder",
    "швея", "агроном", "ветеринар",
    "главный бухгалтер",
    "вице-президент", "vice president",
    "генеральный директор", "general director",
]

LANG_KEYWORDS = [
    "o'zbek", "uzbek", "узбекский",
    "русский", "russian",
    "английский", "english",
    "без опыта", "no experience", "tajribasiz",
    "инглиз", "ingliz",
]

# ============================================================
# SQLite
# ============================================================
def init_db():
    conn = sqlite3.connect("rss_vacancies.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            industry TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn, cursor

def is_seen(cursor, job_id):
    cursor.execute("SELECT job_id FROM sent_jobs WHERE job_id = ?", (job_id,))
    return cursor.fetchone() is not None

def mark_seen(conn, cursor, job_id, title, industry):
    cursor.execute(
        "INSERT OR IGNORE INTO sent_jobs (job_id, title, industry) VALUES (?, ?, ?)",
        (job_id, title, industry)
    )
    conn.commit()

# ============================================================
# FILTR FUNKSIYALARI
# ============================================================
def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_title_ok(title):
    t = title.lower()
    for word in EXCLUDE_TITLES:
        if word.lower() in t:
            return False
    for word in INCLUDE_TITLES:
        if word.lower() in t:
            return True
    return False

def is_desc_ok(desc):
    d = desc.lower()
    high_exp = re.search(
        r"(?:от\s*)?(?:[4-9]|\d{2,})\s*\+?\s*(?:лет|года|год|years?|year|yil)",
        d,
    )
    if high_exp:
        return False
    mentions_lang = any(w in d for w in ["язык", "language", "til", "тил"])
    has_our_lang = any(w in d for w in LANG_KEYWORDS)
    if mentions_lang and not has_our_lang:
        return False
    return True

# ============================================================
# RSS FETCH
# ============================================================
def build_rss_url(industry_ids, keyword):
    base = "https://tashkent.hh.uz/search/vacancy/rss"
    params = f"?area=2759&text={requests.utils.quote(keyword)}&order_by=publication_time"
    for iid in industry_ids:
        params += f"&industry={iid}"
    return base + params

def fetch_for_keyword(keyword, industry_name, industry_ids):
    time.sleep(random.uniform(0.3, 2.0))
    url = build_rss_url(industry_ids, keyword)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"  ⚠️ [{keyword}] Xato: {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    items = []

    for entry in feed.entries:
        job_id = getattr(entry, "link", "")
        title  = getattr(entry, "title", "Noma'lum")
        desc   = strip_html(getattr(entry, "summary", ""))

        pub = getattr(entry, "published_parsed", None)
        if not pub:
            continue
        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
        if pub_dt < cutoff:
            continue

        if not is_title_ok(title):
            continue
        if not is_desc_ok(desc):
            continue

        items.append({
            "id": job_id,
            "title": title,
            "desc": desc[:350],
            "link": job_id,
            "industry": industry_name,
        })

    return items

# ============================================================
# TELEGRAM
# ============================================================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.ok
    except Exception as e:
        print(f"  ❌ Telegram xato: {e}")
        return False

def format_message(v):
    return (
        f"💼 <b>{html.escape(v['title'])}</b>\n\n"
        f"📝 {html.escape(v['desc'])}\n\n"
        f"🔗 <a href='{html.escape(v['link'], quote=True)}'>Apply qilish</a>"
    )

# ============================================================
# ASOSIY JARAYON
# ============================================================
def process():
    conn, cursor = init_db()
    counts = {name: 0 for name in INDUSTRIES}

    print(f"\n{'='*50}")
    print(f"🔍 Tekshirilmoqda: {datetime.now().strftime('%H:%M:%S')}")

    for industry_name, cfg in INDUSTRIES.items():
        industry_ids = cfg["ids"]
        keywords     = cfg["keywords"]
        collected    = []
        seen_links   = set()

        # Parallel fetch
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {
                ex.submit(fetch_for_keyword, kw, industry_name, industry_ids): kw
                for kw in keywords
            }
            for future in as_completed(futures):
                try:
                    items = future.result()
                    for item in items:
                        if item["id"] and item["id"] not in seen_links:
                            seen_links.add(item["id"])
                            collected.append(item)
                except Exception as e:
                    print(f"  ⚠️ Xato: {e}")

        # Yangi vakansiyalarni tanlash (max 2 ta)
        to_send = []
        for v in collected:
            if len(to_send) >= MAX_PER_INDUSTRY:
                break
            if not is_seen(cursor, v["id"]):
                to_send.append(v)

        # Avval soha sarlavhasi, keyin vakansiyalar
        if to_send:
            # 1. Soha sarlavhasi
            send_telegram(f"{industry_name} 👇")
            time.sleep(0.5)

            # 2. Vakansiyalar
            for v in to_send:
                msg = format_message(v)
                ok = send_telegram(msg)
                if ok:
                    mark_seen(conn, cursor, v["id"], v["title"], industry_name)
                    print(f"  ✅ {v['industry']} | {v['title']}")
                time.sleep(1)

        counts[industry_name] = len(to_send)
        print(f"  {industry_name}: {len(collected)} topildi → {len(to_send)} yuborildi")

    # Xulosa xabari
    total = sum(counts.values())
    if total > 0:
        lines = ["📊 <b>Xulosa:</b>\n"]
        for industry, count in counts.items():
            if count > 0:
                lines.append(f"{industry}: {count} ta")
        lines.append(f"\n<b>Jami: {total} ta yangi vakansiya</b>")
        send_telegram("\n".join(lines))
    else:
        print("  Yangi vakansiya topilmadi")

    conn.close()
    print(f"🎉 Tugadi. Jami: {total} ta")

# ============================================================
# ISHGA TUSHIRISH
# ============================================================
if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        raise SystemExit("❌ TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID kerak!")

    send_telegram(
        "✅ <b>Vacancy Bot ishga tushdi!</b>\n\n"
        f"📋 {len(INDUSTRIES)} ta soha kuzatilmoqda\n"
        f"📅 So'nggi {MAX_AGE_DAYS} kunlik vakansiyalar\n"
        f"🔢 Har sohadan max {MAX_PER_INDUSTRY} ta\n"
        # f"⏱ Har {CHECK_INTERVAL // 60} daqiqada tekshiriladi"
    )
    process()