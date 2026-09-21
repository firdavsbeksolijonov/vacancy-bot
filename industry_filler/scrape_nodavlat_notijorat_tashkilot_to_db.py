"""
HH.uz Jamoat tashkilotlari / NKO sektoridan kompaniyalarni DB ga saqlaydi.
"""

import requests
import re
import sqlite3
import time
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

DB_PATH = Path("industry_filler/company_vacancies.db")

URLS = [
    ("Jamoat tashkilotlari (umumiy)", "https://tashkent.hh.uz/employers_company/obshestvennaya_deyatelnost_partii_blagotvoritelnost_nko"),
    ("Madaniyat assotsiatsiyasi", "https://tashkent.hh.uz/employers_company/obshestvennaya_deyatelnost_partii_blagotvoritelnost_nko/associaciya_v_sfere_kultury_iskusstva"),
    ("Xayriya tashkiloti", "https://tashkent.hh.uz/employers_company/obshestvennaya_deyatelnost_partii_blagotvoritelnost_nko/blagotvoritelnaya_organizaciya"),
    ("Jamoat / Siyosiy tashkilot", "https://tashkent.hh.uz/employers_company/obshestvennaya_deyatelnost_partii_blagotvoritelnost_nko/obshestvennaya_politicheskaya_organizaciya"),
    ("Kasbiy / Tadbirkorlik tashkiloti", "https://tashkent.hh.uz/employers_company/obshestvennaya_deyatelnost_partii_blagotvoritelnost_nko/professionalnaya_predprinimatelskaya_organizaciya"),
    ("Sport federatsiyasi", "https://tashkent.hh.uz/employers_company/obshestvennaya_deyatelnost_partii_blagotvoritelnost_nko/sportivnaya_federaciya"),
    ("Jamg'arma / Grant beruvchi", "https://tashkent.hh.uz/employers_company/obshestvennaya_deyatelnost_partii_blagotvoritelnost_nko/fond_grantodatel"),
]

PATTERN = r'/employer/(\d+)[^"]*"[^>]*>\s*([^<]{2,60})\s*<'


def scrape(category: str, url: str) -> list[dict]:
    companies = {}
    page = 0
    while True:
        try:
            r = requests.get(url, headers=HEADERS, params={"page": page, "vacanciesRequired": "false"}, timeout=10)
            if r.status_code != 200:
                break
            matches = re.findall(PATTERN, r.text)
            found = {emp_id: name.strip() for emp_id, name in matches if name.strip() and len(name.strip()) > 1}
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


def save_to_db(companies: list[dict]):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    added = 0
    skipped = 0
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
            """, (c["id"], c["name"], "Jamoat tashkilotlari / NKO", "Общественная деятельность / НКО", "NGO / Public Organizations", "94", 95, "hh_catalog"))
            added += 1
    conn.commit()
    conn.close()
    return added, skipped


def main():
    all_companies = {}
    print("HH.uz Jamoat tashkilotlari / NKO — yuklanmoqda...\n")

    for category, url in URLS:
        print(f"📂 {category}:")
        companies = scrape(category, url)
        for c in companies:
            all_companies[c["id"]] = c["name"]
        print(f"  ✅ {len(companies)} ta\n")
        time.sleep(0.5)

    unique = [{"id": k, "name": v} for k, v in all_companies.items()]
    print(f"Jami topildi: {len(unique)} ta")

    added, skipped = save_to_db(unique)
    print(f"DB ga qo'shildi: {added} ta")
    print(f"Allaqachon bor: {skipped} ta")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM company_classifications WHERE industry_uz='Jamoat tashkilotlari / NKO'")
    total = cur.fetchone()[0]
    conn.close()
    print(f"\nDB da jami: {total} ta")


if __name__ == "__main__":
    main()