"""
HH.uz Mehmonxona / Restoran sektoridan kompaniyalarni DB ga saqlaydi.
"""

import requests, re, sqlite3, time
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}
DB_PATH = Path("industry_filler/company_vacancies.db")

URLS = [
    ("Mehmonxona / Restoran (umumiy)", "https://tashkent.hh.uz/employers_company/gostinicy_restorany_obshepit_kejtering"),
    ("Mehmonxona", "https://tashkent.hh.uz/employers_company/gostinicy_restorany_obshepit_kejtering/gostinica"),
    ("Keyterin", "https://tashkent.hh.uz/employers_company/gostinicy_restorany_obshepit_kejtering/kejtering_vyezdnoe_obsluzhivanie"),
    ("Restoran / Fast-food", "https://tashkent.hh.uz/employers_company/gostinicy_restorany_obshepit_kejtering/restoran_obshestvennoe_pitanie_fast_fud"),
]

PATTERN = r'/employer/(\d+)[^"]*"[^>]*>\s*([^<]{2,60})\s*<'

def scrape(category, url):
    companies = {}
    page = 0
    while True:
        try:
            r = requests.get(url, headers=HEADERS, params={"page": page, "vacanciesRequired": "false"}, timeout=10)
            if r.status_code != 200:
                break
            found = {eid: n.strip() for eid, n in re.findall(PATTERN, r.text) if n.strip() and len(n.strip()) > 1}
            if not found:
                break
            companies.update(found)
            print(f"  [{category}] Page {page}: {len(found)} ta")
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  Xato: {e}")
            break
    return [{"id": k, "name": v} for k, v in companies.items()]

def save_to_db(companies):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    added = skipped = 0
    for c in companies:
        cur.execute("SELECT employer_id FROM company_classifications WHERE employer_id=?", (c["id"],))
        if cur.fetchone():
            skipped += 1
        else:
            cur.execute("""
                INSERT INTO company_classifications
                    (employer_id, company_name, industry_uz, industry_ru, industry_en,
                     okved_code, confidence, source, classified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (c["id"], c["name"], "Mehmonxona / Restoran", "Гостиницы / Рестораны", "Hospitality / Restaurant", "55", 95, "hh_catalog"))
            added += 1
    conn.commit()
    conn.close()
    return added, skipped

def main():
    all_companies = {}
    print("HH.uz Mehmonxona / Restoran — yuklanmoqda...\n")
    for category, url in URLS:
        print(f"📂 {category}:")
        for c in scrape(category, url):
            all_companies[c["id"]] = c["name"]
        print(f"  ✅ {len(all_companies)} ta\n")
        time.sleep(0.5)

    unique = [{"id": k, "name": v} for k, v in all_companies.items()]
    added, skipped = save_to_db(unique)
    print(f"Jami: {len(unique)} ta | DB ga: {added} ta | Bor: {skipped} ta")

    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM company_classifications WHERE industry_uz='Mehmonxona / Restoran'").fetchone()[0]
    conn.close()
    print(f"DB da jami: {total} ta")

if __name__ == "__main__":
    main()