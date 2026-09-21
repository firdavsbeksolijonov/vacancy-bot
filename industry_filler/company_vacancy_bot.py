"""
Moliya / Bank / Fintech kompaniyalaridan yangi vakansiyalarni
topib Telegram ga yuboradi.

Har ishga tushganda:
1. HH.uz dan hozirgi kompaniyalar ro'yxatini yangilaydi
2. RSS orqali vakansiyalarni tekshiradi
3. Telegram ga yuboradi

Ishga tushirish:
    export TELEGRAM_BOT_TOKEN="..."
    export TELEGRAM_CHAT_ID="..."
    python check_vacancies_v2.py
    python check_vacancies_v2.py --dry-run
"""

import argparse
import html
import logging
import os
import random
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

# ============================================================
# SOZLAMALAR
# ============================================================
BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_DIR     = Path(__file__).resolve().parent
DB_FILE      = BASE_DIR / "company_vacancies.db"

MAX_AGE_DAYS    = 3
MAX_WORKERS     = 8
BATCH_SIZE      = 30
MAX_PER_COMPANY = 1

TARGET_INDUSTRY = "Moliya / Bank / Fintech"

# HH.uz Moliya sub-kategoriyalari
FINANCE_URLS = [
    "https://tashkent.hh.uz/employers_company/finansovyj_sektor/bank",
    "https://tashkent.hh.uz/employers_company/finansovyj_sektor/audit_upravlencheskij_uchet_finansovo_yuridicheskij_konsalting",
    "https://tashkent.hh.uz/employers_company/finansovyj_sektor/lizingovye_kompanii",
    "https://tashkent.hh.uz/employers_company/finansovyj_sektor/strakhovanie_perestrakhovanie",
    "https://tashkent.hh.uz/employers_company/finansovyj_sektor/upravlyayushaya_investicionnaya_kompaniya_upravlenie_aktivami",
    "https://tashkent.hh.uz/employers_company/finansovyj_sektor/kollektorskaya_deyatelnost",
    "https://tashkent.hh.uz/employers_company/finansovyj_sektor/uslugi_po_vedeniyu_bukhgalterskogo_i_nalogovogo_ucheta_raschet_zarabotnoj_platy",
    "https://tashkent.hh.uz/employers_company/finansovyj_sektor/finansovo_kreditnoe_posrednichestvo_birzha_brokerskaya_deyatelnost_vypusk_i_obsluzhivanie_kart_ocenka_riskov_obmennye_punkty_agentstva_po_kreditovaniyu_inkassaciya_lombard_platezhnye_sistemy",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ============================================================
# TAJRIBA FILTRI
# ============================================================
HIGH_EXP = re.compile(
    r"(?:от\s*)?(?:[5-9]|\d{2,})\s*\+?\s*(?:лет|года|год|years?|yil)",
    re.IGNORECASE,
)
NO_EXP_KW  = ["без опыта", "tajribasiz", "no experience", "entry level", "fresh graduate", "выпускник"]
JUNIOR_KW  = ["junior", "стажер", "стажёр", "intern", "trainee", "amaliyotchi", "младший", "помощник"]
EXP_1_3_KW = ["от 1 года", "1-3 года", "1 год", "1 year", "1-3 years", "1 yil", "1-3 yil"]

EXP_LABELS = {
    "no_experience": "🟢 Tajriba shart emas",
    "junior":        "🔵 Junior / Intern",
    "1_3_years":     "🟡 1-3 yil tajriba",
    "other":         "⚪ Boshqa",
}

def classify_experience(desc: str) -> tuple[bool, str]:
    d = desc.lower()
    if HIGH_EXP.search(d):
        return False, "senior"
    for kw in NO_EXP_KW:
        if kw in d:
            return True, "no_experience"
    for kw in JUNIOR_KW:
        if kw in d:
            return True, "junior"
    for kw in EXP_1_3_KW:
        if kw in d:
            return True, "1_3_years"
    return True, "other"

# ============================================================
# KOMPANIYALAR SINXRONIZATSIYASI
# ============================================================
PATTERN = r'/employer/(\d+)[^"]*"[^>]*>\s*([^<]{2,60})\s*<'

def scrape_page(url: str) -> dict:
    """Bir sahifadan employer_id va nomlarni oladi."""
    companies = {}
    page = 0
    while True:
        try:
            r = requests.get(
                url,
                headers=HEADERS,
                params={"page": page},  # vacanciesRequired yo'q — faqat vakansiyalilar
                timeout=10
            )
            if r.status_code != 200:
                break
            found = {
                eid: name.strip()
                for eid, name in re.findall(PATTERN, r.text)
                if name.strip() and len(name.strip()) > 1
            }
            if not found:
                break
            companies.update(found)
            page += 1
            time.sleep(0.3)
        except Exception as e:
            log.warning("Scrape xato: %s", e)
            break
    return companies


def sync_companies(conn: sqlite3.Connection) -> int:
    """HH.uz dan yangi kompaniyalar ro'yxatini oladi va DB ni yangilaydi."""
    log.info("HH.uz dan moliya kompaniyalari yangilanmoqda...")

    # Yangi ro'yxat
    fresh = {}
    for url in FINANCE_URLS:
        companies = scrape_page(url)
        fresh.update(companies)
        time.sleep(0.3)

    if not fresh:
        log.warning("HH.uz dan kompaniya olinmadi — eski ro'yxat saqlanadi")
        return 0

    log.info("HH.uz dan %s ta kompaniya topildi", len(fresh))

    # DB ni yangilash
    # 1. Eski hh_catalog kompaniyalarni o'chirish
    conn.execute("""
        DELETE FROM company_classifications
        WHERE industry_uz = ? AND source = 'hh_catalog'
    """, (TARGET_INDUSTRY,))

    # 2. Yangilarini qo'shish
    added = 0
    for emp_id, name in fresh.items():
        existing = conn.execute(
            "SELECT employer_id FROM company_classifications WHERE employer_id=?",
            (emp_id,)
        ).fetchone()

        if not existing:
            conn.execute("""
                INSERT INTO company_classifications
                    (employer_id, company_name, industry_uz, industry_ru, industry_en,
                     okved_code, confidence, source, classified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (emp_id, name, TARGET_INDUSTRY, "Финансы / Банки", "Finance / Banking", "64", 95, "hh_catalog"))
            added += 1

    conn.commit()
    log.info("DB yangilandi: %s ta yangi kompaniya qo'shildi", added)
    return len(fresh)

# ============================================================
# DATABASE
# ============================================================
def get_companies(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
        SELECT employer_id, company_name, industry_uz
        FROM company_classifications
        WHERE industry_uz = ?
        ORDER BY company_name
    """, (TARGET_INDUSTRY,)).fetchall()
    return [{"id": r[0], "name": r[1], "industry": r[2]} for r in rows]


def get_next_batch(conn: sqlite3.Connection, companies: list[dict]) -> list[dict]:
    checked = {r[0] for r in conn.execute("SELECT employer_id FROM company_batches").fetchall()}
    unchecked = [c for c in companies if c["id"] not in checked]
    if not unchecked:
        log.info("Hammasi tekshirildi — reset!")
        conn.execute("DELETE FROM company_batches")
        conn.commit()
        unchecked = companies
    batch = random.sample(unchecked, min(BATCH_SIZE, len(unchecked)))
    log.info("%s ta kompaniya tanlandi", len(batch))
    return batch


def is_seen(conn: sqlite3.Connection, vid: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sent_jobs WHERE vacancy_id=?", (vid,)
    ).fetchone() is not None


def mark_seen(conn, vid, title, company, industry, exp_type):
    conn.execute("""
        INSERT OR IGNORE INTO sent_jobs
            (vacancy_id, title, company, industry, exp_type, sent_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (vid, title, company, industry, exp_type))
    conn.commit()


def mark_checked(conn, employer_id, company_name, industry, has_remaining):
    conn.execute("""
        INSERT INTO company_batches
            (employer_id, company_name, industry, last_checked, has_remaining)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
        ON CONFLICT(employer_id) DO UPDATE SET
            last_checked=CURRENT_TIMESTAMP,
            has_remaining=excluded.has_remaining
    """, (employer_id, company_name, industry, int(has_remaining)))
    conn.commit()

# ============================================================
# RSS FETCH
# ============================================================
def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def fetch_for_company(company: dict) -> tuple[dict, list[dict]]:
    time.sleep(random.uniform(0.3, 1.5))
    url = "https://tashkent.hh.uz/search/vacancy/rss"
    params = {"employer_id": company["id"], "area": "2759", "order_by": "publication_time"}
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)

    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=(8, 20))
            if resp.status_code == 429:
                time.sleep(2 * attempt)
                continue
            if resp.status_code != 200:
                return company, []
            break
        except requests.RequestException:
            time.sleep(2 * attempt)
    else:
        return company, []

    try:
        feed = feedparser.parse(resp.content)
    except Exception:
        return company, []

    vacancies = []
    for entry in feed.entries:
        vid   = entry.get("link", "")
        title = entry.get("title", "")
        desc  = strip_html(entry.get("summary", ""))
        pub   = entry.get("published_parsed")

        if not vid or not title:
            continue

        if pub:
            pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue

        allowed, exp_type = classify_experience(desc)
        if not allowed:
            continue

        vacancies.append({
            "id":       vid,
            "title":    title,
            "desc":     desc[:400],
            "link":     vid,
            "company":  company["name"],
            "industry": company["industry"],
            "exp_type": exp_type,
        })

    return company, vacancies

# ============================================================
# TELEGRAM
# ============================================================
def send_telegram(text: str, dry_run: bool = False) -> bool:
    if dry_run:
        print(f"[DRY RUN]\n{text[:200]}\n")
        return True
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return resp.ok
    except Exception as e:
        log.warning("Telegram xato: %s", e)
        return False


def format_msg(v: dict) -> str:
    exp_label = EXP_LABELS.get(v["exp_type"], "⚪ Boshqa")
    return (
        f"🏢 <b>{html.escape(v['company'])}</b>\n"
        f"💼 {html.escape(v['title'])}\n"
        f"{exp_label}\n\n"
        f"📝 {html.escape(v['desc'])}\n\n"
        f"🔗 <a href='{html.escape(v['link'])}'>Apply</a>"
    )

# ============================================================
# ASOSIY
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-sync", action="store_true", help="Kompaniyalarni yangilamaslik")
    args = parser.parse_args()

    if not BOT_TOKEN or not CHAT_ID:
        sys.exit("❌ TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID kerak!")

    conn = sqlite3.connect(DB_FILE)

    # 1. Kompaniyalarni yangilash
    if not args.no_sync:
        sync_companies(conn)

    # 2. Kompaniyalar ro'yxati
    companies = get_companies(conn)
    log.info("Moliya kompaniyalari: %s ta", len(companies))

    # 3. Batch tanlash
    batch = get_next_batch(conn, companies)

    # 4. RSS parallel fetch
    results = {}
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(batch))) as ex:
        futures = {ex.submit(fetch_for_company, c): c for c in batch}
        for future in as_completed(futures):
            company, vacancies = future.result()
            results[company["id"]] = (company, vacancies)
            log.info("%s: %s ta vakansiya", company["name"], len(vacancies))

    # 5. Yuborish
    sent_total = 0
    send_telegram("💰 <b>Moliya / Bank / Fintech</b> 👇👇", args.dry_run)
    time.sleep(0.5)

    for company in batch:
        _, vacancies = results.get(company["id"], (company, []))
        unseen = [v for v in vacancies if not is_seen(conn, v["id"])]
        sent = 0

        for v in unseen[:MAX_PER_COMPANY]:
            if send_telegram(format_msg(v), args.dry_run):
                mark_seen(conn, v["id"], v["title"], company["name"], v["industry"], v["exp_type"])
                sent += 1
                sent_total += 1
                log.info("✅ %s | %s", company["name"], v["title"])
                time.sleep(0.8)

        mark_checked(conn, company["id"], company["name"], company["industry"], len(unseen) > sent)

    conn.close()
    print(f"\n✅ Tugadi: {len(batch)} ta kompaniya, {sent_total} ta yuborildi")


if __name__ == "__main__":
    main()