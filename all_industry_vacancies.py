"""
hh.uz (Toshkent) — barcha sohalar bo'yicha yangi vakansiyalarni
topib, Telegram botga yuboradi.

Filtrlar:
- Sohalar bo'yicha (8 ta soha)
- Har sohadan max 2 ta
- Junior/intern/stajyor ham qabul qilinadi
- Tajriba: 0-3 yil
- Til: O'zbek, Rus, Ingliz (aralash ham bo'lsa mayli)
- EXCLUDE: охранник, водитель, уборщик, повар va boshqalar
"""

import html
import json
import os
import random
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

# ---------- SOZLAMALAR ----------
HH_AREA_ID = 2759
MAX_AGE_DAYS = 3
MAX_PER_INDUSTRY = 2
MAX_WORKERS = 8
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
REQUEST_JITTER_MAX_SECONDS = 2.5
REQUEST_TIMEOUT = (8, 20)
SEEN_IDS_FILE = "seen_ids.json"
MAX_STORED_IDS = 5000

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

RSS_URL = "https://tashkent.hh.uz/search/vacancy/rss"

# ---------- FILTRLAR ----------

# ✅ QO'SHISH kerak — shu so'zlar sarlavhada bo'lsin
INCLUDE_TITLES = [
    # No experience / Junior
    "junior", "джуниор", "джун",
    "стажер", "стажёр", "intern", "trainee",
    "начинающий", "entry level", "entry-level",
    "помощник", "ассистент", "assistant",
    "младший", "молодой специалист",

    # 1-3 yil tajriba
    "специалист", "менеджер", "analyst", "аналитик",
    "coordinator", "координатор", "officer",
    "executive", "associate",

    # Sohalar bo'yicha
    "финансовый", "financial", "кредитный", "credit",
    "аудитор", "auditor", "бухгалтер", "accountant",
    "комплаенс", "compliance", "AML", "KYC",
    "казначей", "treasury", "инвестиционный", "investment",
    "риск", "risk", "консультант", "consultant",
    "юрист", "lawyer", "налоговый", "tax",
    "маркетолог", "marketer", "маркетинг", "marketing",
    "бренд", "brand", "SMM", "digital", "контент", "content",
    "рекрутер", "recruiter", "HR", "персонал", "talent",
    "логист", "logistic", "supply", "закупки", "procurement",
    "склад", "warehouse", "операционный", "operations",
    "учитель", "teacher", "преподаватель", "тренер", "trainer",
    "методист", "педагог", "репетитор", "tutor",
    "продажи", "sales", "аккаунт", "account", "коммерческий",
    "data", "product", "систем", "system",
    "business development", "partnership", "партнерств",
    "project manager", "project coordinator",
]

# ❌ CHIQARIB TASHLASH — shu so'zlar sarlavhada bo'lsa o'tkazib yuborish
EXCLUDE_TITLES = [
    # Noto'g'ri kasb
    "охранник", "охрана", "security guard",
    "водитель", "шофер", "driver",
    "уборщик", "уборщица", "cleaner",
    "повар", "cook", "chef", "официант", "waiter",
    "кассир", "cashier",
    "грузчик", "loader",
    "строитель", "builder",
    "сварщик", "welder",
    "электрик", "electrician",
    "сантехник", "plumber",
    "курьер", "courier", "delivery",
    "продавец", "продавщица",  # oddiy sotuvchi (sales manager emas)
    "швея", "seams",
    "агроном", "agronomist",
    "ветеринар", "veterinary",
    # Senior (tajriba ko'p talab qiluvchi)
    "senior", "сениор", "старший директор",
    "директор", "director", "CTO", "CEO", "CFO", "COO",
    "вице-президент", "vice president",
    "главный бухгалтер",  # faqat junior accountant kerak
]

# 🌍 TIL FILTRI — shu tillardan biri tavsifda bo'lsa qabul qilinadi
# O'zbek, Rus, Ingliz — aralash ham mayli
LANGUAGE_KEYWORDS = [
    # O'zbek tili
    "o'zbek tili", "uzbek tili", "o'zbek", "uzbek",
    "узбекский язык", "узбекский",
    # Rus tili
    "русский язык", "русский", "russian language", "russian",
    # Ingliz tili
    "английский язык", "английский", "english language", "english",
    "инглиз тили", "ingliz tili",
    # Umumiy
    "знание языков", "language skills", "til bilish",
    # Til talab qilinmasa ham o'tkazib yubormaymiz
    "без опыта", "no experience", "tajribasiz", "опыт не требуется",
]

# Tajriba darajasi — tavsifda shu so'zlar bo'lsa qabul qilinadi
EXPERIENCE_KEYWORDS = [
    "без опыта", "no experience", "опыт не требуется",
    "0-1 год", "от 1 года", "1-2 года", "1-3 года",
    "до 3 лет", "2-3 года", "3 года",
    "entry level", "junior", "начинающий",
    "стажер", "intern", "trainee",
    # Tajriba bo'lmasa ham qabul qilinadi (tavsifda hech narsa yo'q bo'lsa)
]

# ---------- SOHALAR ----------
INDUSTRIES = {
    "💰 Moliya / Bank / Fintech": [
        "финансовый аналитик", "financial analyst",
        "кредитный аналитик", "credit analyst",
        "аудитор", "auditor", "бухгалтер", "accountant",
        "комплаенс", "compliance", "AML", "KYC",
        "казначей", "treasury", "инвестиционный аналитик",
        "риск аналитик", "risk analyst",
    ],
    "⚖️ Konsalting / Huquq": [
        "консультант", "consultant", "юрист", "lawyer",
        "налоговый консультант", "tax consultant",
        "бизнес аналитик", "business analyst",
    ],
    "💻 IT / Texnologiya": [
        "data analyst", "дата аналитик",
        "product manager", "системный аналитик",
        "BI аналитик", "business analyst IT",
    ],
    "👥 HR / Rekruting": [
        "рекрутер", "recruiter", "HR менеджер",
        "talent acquisition", "HR аналитик",
        "менеджер по персоналу",
    ],
    "📢 Marketing / Media": [
        "маркетолог", "marketing manager",
        "бренд менеджер", "brand manager",
        "SMM менеджер", "digital маркетолог",
        "контент менеджер", "media planner",
    ],
    "🛒 Savdo / E-commerce": [
        "менеджер по продажам", "sales manager",
        "аккаунт менеджер", "account manager",
        "key account manager", "коммерческий менеджер",
    ],
    "🚚 Logistika": [
        "логист", "logistics manager",
        "supply chain", "менеджер по закупкам",
        "procurement manager", "операционный менеджер",
    ],
    "📚 Ta'lim / O'qituvchilik": [
        "учитель", "teacher", "преподаватель", "lecturer",
        "бизнес тренер", "корпоративный тренер",
        "методист", "инструктор",
    ],
}

# ---------- YORDAMCHI ----------

def load_seen_ids():
    if os.path.exists(SEEN_IDS_FILE):
        try:
            with open(SEEN_IDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return set(data) if isinstance(data, list) else set()
        except (OSError, json.JSONDecodeError, TypeError):
            print(f"Warning: unable to read {SEEN_IDS_FILE}; starting with empty state")
    return set()

def save_seen_ids(seen_ids):
    ids_list = list(seen_ids)[-MAX_STORED_IDS:]
    temp_file = f"{SEEN_IDS_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(ids_list, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, SEEN_IDS_FILE)

def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def parse_pub_date(item):
    raw = item.findtext("pubDate", default="").strip()
    if raw:
        try:
            return parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            pass
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    description_raw = item.findtext("description", default="")
    match = re.search(r"Создана:\s*(\d{2})\.(\d{2})\.(\d{4})", description_raw)
    if match:
        day, month, year = match.groups()
        try:
            tz = timezone(timedelta(hours=5))
            dt = datetime(int(year), int(month), int(day), tzinfo=tz)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return None

def is_title_ok(title):
    """Sarlavha filtridan o'tkazadi."""
    t = title.lower()

    # Chiqarib tashlash
    for word in EXCLUDE_TITLES:
        if word.lower() in t:
            return False, f"❌ EXCLUDE: '{word}'"

    # Qabul qilish
    for word in INCLUDE_TITLES:
        if word.lower() in t:
            return True, f"✅ INCLUDE: '{word}'"

    return False, "❌ Mos emas"

def is_description_ok(description):
    """Tavsif filtridan o'tkazadi — til va tajriba."""
    d = description.lower()

    # Tajriba tekshiruvi — agar "10 лет опыта" kabi narsa bo'lsa chiqarib tashlash
    high_exp = re.search(
        r"(?:от\s*)?(?:[4-9]|\d{2,})\s*\+?\s*(?:лет|года|год|years?|year|yil)",
        d,
    )
    if high_exp:
        return False, f"❌ Ko'p tajriba talab qilinadi"

    # Til tekshiruvi — tillardan biri bo'lsa yoki umuman til haqida gap bo'lmasa OK
    has_lang = any(lang.lower() in d for lang in LANGUAGE_KEYWORDS)
    mentions_lang = any(w in d for w in ["язык", "language", "til", "тил"])

    if mentions_lang and not has_lang:
        return False, "❌ Til mos emas"

    return True, "✅ OK"

def fetch_for_keyword(session, keyword, industry_name):
    """Bitta kalit so'z uchun RSS dan vakansiyalar oladi."""
    time.sleep(random.uniform(0, REQUEST_JITTER_MAX_SECONDS))

    params = {
        "text": keyword,
        "area": HH_AREA_ID,
        "order_by": "publication_time",
    }

    resp = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                RSS_URL, params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 429:
                wait = RETRY_BACKOFF_SECONDS * attempt
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            resp = None
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue
            print(f"[{keyword}] Xato: {e}")
            break

    if resp is None:
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return []

    items = []
    for item in root.findall("./channel/item"):
        link = item.findtext("link", default="").strip()
        title = item.findtext("title", default="Noma'lum").strip()
        description = strip_html(item.findtext("description", default=""))
        pub_date = parse_pub_date(item)

        # 1. Sarlavha filtri
        title_ok, title_reason = is_title_ok(title)
        if not title_ok:
            continue

        # 2. Tavsif filtri (til + tajriba)
        desc_ok, desc_reason = is_description_ok(description)
        if not desc_ok:
            continue

        items.append({
            "id": link,
            "title": title,
            "description": description[:400],
            "link": link,
            "pub_date": pub_date,
            "industry": industry_name,
        })
    return items

def fetch_by_industry():
    """Har soha uchun alohida qidiradi."""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=MAX_WORKERS,
        pool_maxsize=MAX_WORKERS
    )
    session.mount("https://", adapter)

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    result = {name: [] for name in INDUSTRIES}
    for industry_name, keywords in INDUSTRIES.items():
        all_for_industry = []
        seen_links = set()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(fetch_for_keyword, session, kw, industry_name): kw
                for kw in keywords
            }
            for future in as_completed(futures):
                try:
                    items = future.result()
                    for item in items:
                        if item["id"] and item["id"] not in seen_links:
                            seen_links.add(item["id"])
                            all_for_industry.append(item)
                except Exception as e:
                    print(f"Xato: {e}")

        fresh = [v for v in all_for_industry
                 if v["pub_date"] and v["pub_date"] >= cutoff]
        fresh.sort(key=lambda v: v["pub_date"] or epoch, reverse=True)
        result[industry_name] = fresh[:MAX_PER_INDUSTRY]
        print(f"  {industry_name}: {len(fresh)} → {len(result[industry_name])} ta")

    return result

def format_message(v):
    return (
        f"{html.escape(v['industry'])}\n"
        f"💼 <b>{html.escape(v['title'])}</b>\n\n"
        f"📝 {html.escape(v['description'][:300])}\n\n"
        f"🔗 <a href='{html.escape(v['link'], quote=True)}'>Apply qilish</a>"
    )

def send_to_telegram(text):
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(TELEGRAM_API_URL, data=payload, timeout=30)
        if not resp.ok:
            print(f"Telegram xato: {resp.status_code} {resp.text}")
            return False
        return True
    except requests.RequestException as e:
        print(f"Telegram xato: {e}")
        return False

def send_summary(counts):
    lines = ["📊 <b>Yangi vakansiyalar xulosasi:</b>\n"]
    total = 0
    for industry, count in counts.items():
        if count > 0:
            lines.append(f"{industry}: {count} ta")
            total += count
    if total == 0:
        lines.append("Yangi vakansiya topilmadi")
    else:
        lines.append(f"\n<b>Jami: {total} ta yangi vakansiya</b>")
    send_to_telegram("\n".join(lines))

# ---------- ASOSIY ----------

def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID "
            "environment variable sifatida berilishi kerak."
        )

    seen_ids = load_seen_ids()

    print("🔍 Sohalar bo'yicha qidirilmoqda...")
    print(f"📋 Filtrlar: max {MAX_PER_INDUSTRY} ta/soha | {MAX_AGE_DAYS} kunlik\n")

    vacancies_by_industry = fetch_by_industry()

    counts = {}
    try:
        for industry_name, vacancies in vacancies_by_industry.items():
            sent = 0
            for v in vacancies:
                vid = v["id"]
                if not vid or vid in seen_ids:
                    continue
                msg = format_message(v)
                ok = send_to_telegram(msg)
                if ok:
                    seen_ids.add(vid)
                    sent += 1
                    save_seen_ids(seen_ids)
                    print(f"✅ {v['industry']} | {v['title']}")
                time.sleep(1)
            counts[industry_name] = sent
    finally:
        save_seen_ids(seen_ids)

    total = sum(counts.values())
    send_summary(counts)
    print(f"\n🎉 Tugadi. Jami yuborilgan: {total} ta")


if __name__ == "__main__":
    main()