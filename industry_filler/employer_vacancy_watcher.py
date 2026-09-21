"""
- Har safar 10 ta kompaniya tanlaydi
- Har biridan 1 ta vakansiya
- DB ga saqlaydi
- Keyingi ishga tushganda: eski kompaniyalarda qolgan bo'lsa shulardan
- Qolmagan bo'lsa yangi 10 ta kompaniyaga o'tadi
- Soha sarlavhasi alohida xabar sifatida yuboriladi
"""

import sqlite3
import feedparser
import requests
import pandas as pd
import os
import re
import html
import time
import random
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ============================================================
# SOZLAMALAR
# ============================================================
BOT_TOKEN       = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID         = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_DIR        = Path(__file__).resolve().parent
EXCEL_FILE      = BASE_DIR / "tashkent_hh_companies_clean.xlsx"
DB_FILE         = BASE_DIR / "company_vacancies.db"
MAX_AGE_DAYS    = 3
MAX_WORKERS     = 8
BATCH_SIZE      = 10   # Har safar shuncha kompaniya
MAX_PER_COMPANY = 1    # Har kompaniyadan max shuncha vakansiya

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ============================================================
# ANIQ KOMPANIYALAR
# ============================================================
EXACT_COMPANIES = [
    "Aloqabank", "APEX BANK",
    "АКБ Asia Alliance Bank", "АКБ Агробанк",
    "АКБ Банк развития бизнеса", "АКБ Тенге Банк",
    "АКБ Туронбанк", "АКБ Универсал банк",
    "АО ANOR BANK", "АО Асакабанк",
    "КДБ Банк Узбекистан", "Капиталбанк",
    "Национальный банк внешнеэкономической деятельности",
    "Центральный Банк Республики Узбекистан",
    "АИКБ ИПАК ЙУЛИ БАНК",
    "Alif Uzbekistan",
    "Национальный межбанковский процессинговый центр",
    "ZIYNAT MOLIYA", "ZOLOTO LOMBARD",
    "Компания по рефинансированию ипотеки Узбекистана",
    "МФО Agat Credit", "Национальная страховая компания Узбекинвест",
    "ООО HURMA LOMBARD", "ООО MK LEASING",
    "ИП ООО TASFINANCE MIKROMOLIYA TASHKILOTI",
    "ООО Kreditomat Tashkent Mikrokredit Tashkiloti",
    "СК IMPEX INSURANCE", "СП АО EUROASIA INSURANCE",
    "СП ООО МФО KORONA", "СП ООО МФО UNA MOLIYA",
    "ООО Finserv Tech", "ООО FARDO INVESTMENT GLOBAL",
    "Семейный офис", "СП ООО EAST-WEST INVEST",
    "ИП ООО CHINARA BIZNES KREDIT LOMBARD",
    "ИП ООО NEW GOLD-BANYO", "ЧП ISHONCH KAPITAL INVEST",
    "ЧП XK PLUTUS", "СП IZZAT INVEST",
    "Yengil Kredit Mikrokredit Tashkiloti",
    "ABRAU Capital", "AFSONA INVEST", "AIVA INVEST",
    "ARHAT HOLDING", "ARIN GOLDEN FUTURES",
    "BA Holding", "BEK GROUP", "BERA",
    "ALPHACON", "ARUS PAY SYSTEM", "ASTERIUM",
    "BALANCE DIGITAL GROUP",
    "ATB CONSULT HOLDING", "BDO AUDIT",
    "ПУ PricewaterhouseCoopers Central Asia and Caucasus B.V.",
    "Бюро Веритас", "ООО MONTFORT CA",
    "СOMPASS MANAGEMENT", "АО MOORE CA",
    "АО NEXIA CA EXPERTS", "АО ООО BAKER TILLY INTEGRA ADVISER",
    "ARIA SUGURTA TASHKILOTI", "ASSET LEASING AND FINANCE",
    "ADVOCA", "AZIZOV & PARTNERS",
    "ZHONG CHENG LAW FIRM", "АФ ONELAW",
    "АФ PROFESSIONAL LAWYER CONSULT",
    "YUSUF EXPERT CONSULTING", "YulDosh Consult",
]

INCLUDE_KEYWORDS = [
    "bank", "moliya", "kredit", "lombard", "sug'urta",
    "lizing", "mikrokredit", "mikromoliya", "invest",
    "kapital", "fond", "pay", "fintech", "audit",
    "konsalt", "huquq", "advokat", "yurist", "broker",
    "банк", "финанс", "кредит", "ломбард", "страхов",
    "лизинг", "микрокредит", "микрофинанс", "инвест",
    "капитал", "фонд", "процессинг", "аудит",
    "консалт", "юрид", "адвокат", "брокер",
    "мфо", "акб", "аикб", "холдинг",
    "finance", "financial", "credit", "leasing",
    "insurance", "capital", "fund", "payment",
    "consulting", "legal", "law firm",
    "holding", "processing", "microfinance",
    "accounting", "tax", "treasury", "compliance",
]

TARGET_INDUSTRIES = [
    "Moliya / Bank / Fintech",
    "Konsalting / Audit",
    "Konsalting / Huquq",
    "IT / Texnologiya",
    "HR / Rekruting",
    "Marketing / Media / PR",
    "Savdo / E-commerce",
    "Logistika / Transport",
]

# ============================================================
# TAJRIBA FILTRI
# ============================================================
NO_EXPERIENCE_KEYWORDS = [
    "tajriba talab etilmaydi", "tajribasiz", "rezyume talab etilmaydi",
    "bez opyta", "без опыта", "опыт не требуется", "без резюме",
    "резюме не требуется", "молодой специалист", "выпускник",
    "no experience", "no experience required", "no resume required",
    "entry level", "entry-level", "fresh graduate",
]

JUNIOR_KEYWORDS = [
    "junior", "стажер", "стажёр", "stajer", "intern", "amaliyotchi",
    "джуниор", "джун", "начинающий", "помощник", "ассистент",
    "младший", "практикант", "trainee", "assistant",
]

EXPERIENCE_1_3_KEYWORDS = [
    "от 1 года", "от 1 до 3", "1-3 года", "1 год", "до 3 лет",
    "2-3 года", "1-2 года", "не менее 1", "1 year", "1-3 years",
    "1 to 3 years", "up to 3 years", "minimum 1 year",
    "1 yil", "1-3 yil", "bir yil",
]

def classify_experience(desc):
    d = desc.lower()
    for kw in NO_EXPERIENCE_KEYWORDS:
        if kw.lower() in d:
            return "no_experience"
    for kw in JUNIOR_KEYWORDS:
        if kw.lower() in d:
            return "junior"
    for kw in EXPERIENCE_1_3_KEYWORDS:
        if kw.lower() in d:
            return "1_3_years"
    return "other"

EXP_LABELS = {
    "no_experience": "🟢 Tajriba shart emas",
    "junior":        "🔵 Junior / Intern / Stajyor",
    "1_3_years":     "🟡 1-3 yil tajriba",
    "other":         "⚪ Boshqa",
}

# ============================================================
# DATABASE
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            employer_id  TEXT PRIMARY KEY,
            company_name TEXT,
            industry     TEXT,
            hh_url       TEXT,
            is_active    INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_jobs (
            job_id      TEXT PRIMARY KEY,
            title       TEXT,
            company     TEXT,
            industry    TEXT,
            exp_type    TEXT,
            sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Batch tracker — qaysi kompaniyalar ko'rilgan
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_batches (
            employer_id   TEXT PRIMARY KEY,
            company_name  TEXT,
            industry      TEXT,
            last_checked  TIMESTAMP,
            has_remaining INTEGER DEFAULT 0
        )
    """)

    # Eski DB ga exp_type qo'shish
    try:
        cur.execute("ALTER TABLE sent_jobs ADD COLUMN exp_type TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.commit()
    return conn, cur

# ============================================================
# EXCEL → DB
# ============================================================
def import_excel_to_db(conn, cur):
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Excel topilmadi: {EXCEL_FILE}")
        return 0

    df = pd.read_excel(EXCEL_FILE)
    df.columns = [c.lower().strip() for c in df.columns]

    id_col   = next((c for c in df.columns if 'employer' in c and 'id' in c), None)
    id_col   = id_col or next((c for c in df.columns if c == 'id'), None)
    name_col = next((c for c in df.columns if 'name' in c or 'company' in c), None)
    ind_col  = next((c for c in df.columns if 'industry' in c), None)
    url_col  = next((c for c in df.columns if 'url' in c or 'link' in c), None)

    if not id_col:
        print("❌ employer_id ustuni topilmadi!")
        return 0

    count = 0
    for _, row in df.iterrows():
        emp_id   = str(row[id_col]).strip()
        name     = str(row[name_col]).strip() if name_col else ""
        industry = str(row[ind_col]).strip()  if ind_col  else ""
        url      = str(row[url_col]).strip()  if url_col  else ""

        if emp_id in ("nan", "", "None"):
            continue

        industry = "" if industry in ("nan", "None") else industry
        url      = "" if url      in ("nan", "None") else url

        cur.execute("""
            INSERT OR REPLACE INTO companies
            (employer_id, company_name, industry, hh_url)
            VALUES (?, ?, ?, ?)
        """, (emp_id, name, industry, url))
        count += 1

    conn.commit()
    return count

# ============================================================
# KOMPANIYA FILTR
# ============================================================
def is_target_company(name, industry):
    n = name.lower()
    for exact in EXACT_COMPANIES:
        if exact.lower() in n or n in exact.lower():
            return True
    for kw in INCLUDE_KEYWORDS:
        if kw.lower() in n:
            return True
    if industry and industry in TARGET_INDUSTRIES:
        return True
    return False

def get_all_target_companies(cur):
    cur.execute("SELECT employer_id, company_name, industry FROM companies")
    rows = cur.fetchall()
    companies = []
    for emp_id, name, industry in rows:
        if is_target_company(name or "", industry or ""):
            companies.append({
                "id":       emp_id,
                "name":     name or "Noma'lum",
                "industry": industry or "Moliya / Bank / Fintech",
            })
    return companies

# ============================================================
# BATCH TANLASH
# ============================================================
def get_next_batch(cur, all_companies):
    """
    Oldin ko'rilgan kompaniyalarda qolgan vakansiya bormi?
    Bor → shulardan; Yo'q → yangi 10 ta
    """
    # Oldin ko'rilgan kompaniyalar
    cur.execute("""
        SELECT employer_id, company_name, industry
        FROM company_batches
        WHERE has_remaining = 1
        ORDER BY last_checked DESC
        LIMIT ?
    """, (BATCH_SIZE,))
    remaining = cur.fetchall()

    if remaining:
        print(f"♻️  Eski kompaniyalarda qolgan vakansiyalar tekshirilmoqda: {len(remaining)} ta")
        return [{"id": r[0], "name": r[1], "industry": r[2]} for r in remaining]

    # Yangi 10 ta — ko'rilmaganlardan
    checked_ids = set()
    cur.execute("SELECT employer_id FROM company_batches")
    for row in cur.fetchall():
        checked_ids.add(row[0])

    unchecked = [c for c in all_companies if c["id"] not in checked_ids]

    if not unchecked:
        # Hammasi ko'rilgan — boshidan boshlaymiz
        print("🔄 Barcha kompaniyalar ko'rildi — boshidan boshlanmoqda")
        cur.execute("DELETE FROM company_batches")
        unchecked = all_companies

    batch = random.sample(unchecked, min(BATCH_SIZE, len(unchecked)))
    print(f"🆕 Yangi {len(batch)} ta kompaniya tanlandi")
    return batch

# ============================================================
# RSS FETCH
# ============================================================
def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def fetch_for_employer(company):
    time.sleep(random.uniform(0.5, 2.0))
    emp_id   = company["id"]
    name     = company["name"]
    industry = company["industry"]

    url = (
        f"https://tashkent.hh.uz/search/vacancy/rss"
        f"?employer_id={emp_id}&area=2759&order_by=publication_time"
    )

    resp = None
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=(8, 20))
            if resp.status_code == 429:
                time.sleep(2 * attempt)
                continue
            if resp.status_code != 200:
                return []
            break
        except requests.RequestException:
            if attempt < 3:
                time.sleep(2 * attempt)
            continue

    if resp is None:
        return []

    try:
        feed = feedparser.parse(resp.content)
    except Exception:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    items  = []

    for entry in feed.entries:
        job_id = getattr(entry, "link", "")
        title  = getattr(entry, "title", "Noma'lum")
        desc   = strip_html(getattr(entry, "summary", ""))
        pub    = getattr(entry, "published_parsed", None)

        if not pub:
            continue
        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
        if pub_dt < cutoff:
            continue

        exp_type = classify_experience(desc)

        items.append({
            "id":       job_id,
            "title":    title,
            "desc":     desc[:350],
            "link":     job_id,
            "company":  name,
            "industry": industry,
            "exp_type": exp_type,
        })

    return items

# ============================================================
# TELEGRAM
# ============================================================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id":                  CHAT_ID,
            "text":                     text,
            "parse_mode":               "HTML",
            "disable_web_page_preview": False,
        }, timeout=15)
        return resp.ok
    except Exception:
        return False

def format_msg(v):
    exp_label = EXP_LABELS.get(v["exp_type"], "⚪ Boshqa")
    return (
        f"🏢 <b>{html.escape(v['company'])}</b>\n"
        f"💼 <b>{html.escape(v['title'])}</b>\n"
        f"{exp_label}\n\n"
        f"📝 {html.escape(v['desc'])}\n\n"
        f"🔗 <a href='{html.escape(v['link'], quote=True)}'>Apply qilish</a>"
    )

INDUSTRY_ICONS = {
    "Moliya / Bank / Fintech":  "💰",
    "IT / Texnologiya":         "💻",
    "Konsalting / Audit":       "⚖️",
    "Konsalting / Huquq":       "⚖️",
    "HR / Rekruting":           "👥",
    "Marketing / Media / PR":   "📢",
    "Savdo / E-commerce":       "🛒",
    "Logistika / Transport":    "🚚",
}

# ============================================================
# ASOSIY
# ============================================================
def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise SystemExit("❌ TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID kerak!")

    conn, cur = init_db()
    import_excel_to_db(conn, cur)

    # Barcha mos kompaniyalar
    all_companies = get_all_target_companies(cur)
    if not all_companies:
        print("❌ Mos kompaniya topilmadi!")
        return

    # Keyingi batch tanlash
    batch = get_next_batch(cur, all_companies)

    # Parallel RSS fetch
    all_vacancies = []
    seen_links    = set()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_for_employer, c): c for c in batch}
        for future in as_completed(futures):
            try:
                items = future.result()
                for v in items:
                    if v["id"] and v["id"] not in seen_links:
                        seen_links.add(v["id"])
                        all_vacancies.append(v)
            except Exception as e:
                print(f"  ⚠️ {e}")

    print(f"📊 Topildi: {len(all_vacancies)} ta vakansiya")

    # Soha bo'yicha guruhlash
    by_industry = {}
    for v in all_vacancies:
        ind = v["industry"]
        if ind not in by_industry:
            by_industry[ind] = []
        by_industry[ind].append(v)

    # Yuborish
    sent_per_company = {}
    new_count        = 0
    now              = datetime.now().isoformat()

    for industry, vacancies in by_industry.items():
        icon     = INDUSTRY_ICONS.get(industry, "🏢")
        industry_sent = 0

        for v in vacancies:
            company = v["company"]

            if sent_per_company.get(company, 0) >= MAX_PER_COMPANY:
                continue

            cur.execute("SELECT job_id FROM sent_jobs WHERE job_id=?", (v["id"],))
            if cur.fetchone():
                continue

            # Birinchi vakansiyadan oldin soha sarlavhasi
            if industry_sent == 0:
                send_telegram(f"{icon} <b>{industry}</b> 👇👇")
                time.sleep(0.5)

            msg = format_msg(v)
            ok  = send_telegram(msg)
            if ok:
                cur.execute(
                    "INSERT OR IGNORE INTO sent_jobs (job_id,title,company,industry,exp_type) VALUES (?,?,?,?,?)",
                    (v["id"], v["title"], company, industry, v["exp_type"])
                )
                conn.commit()
                sent_per_company[company] = sent_per_company.get(company, 0) + 1
                new_count      += 1
                industry_sent  += 1
                print(f"  ✅ {company} | {v['title']}")
            time.sleep(0.8)

    # Batch ni DB ga saqlash
    for c in batch:
        # Bu kompaniyada ko'rilmagan vakansiya qoldimi?
        company_vacs = [v for v in all_vacancies if v["company"] == c["name"]]
        sent_ids = {row[0] for row in cur.execute("SELECT job_id FROM sent_jobs")}
        has_remaining = 1 if any(
            v["id"] not in sent_ids for v in company_vacs if v["id"]
        ) else 0

        cur.execute("""
            INSERT OR REPLACE INTO company_batches
            (employer_id, company_name, industry, last_checked, has_remaining)
            VALUES (?, ?, ?, ?, ?)
        """, (c["id"], c["name"], c["industry"], now, has_remaining))

    conn.commit()
    conn.close()

    send_telegram(
        f"📊 <b>Tekshiruv tugadi</b>\n\n"
        f"🏢 {len(batch)} ta kompaniya tekshirildi\n"
        f"🆕 {new_count} ta yangi vakansiya yuborildi"
    )
    print(f"\n🎉 Tugadi. Yangi: {new_count} ta")

if __name__ == "__main__":
    main()