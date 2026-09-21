"""
HH.uz IT / Texnologiya sektoridan kompaniyalarni DB ga saqlaydi.
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
    ("IT (umumiy)", "https://tashkent.hh.uz/employers_company/informacionnye_tekhnologii_sistemnaya_integraciya_internet"),
    ("Internet kompaniyalar", "https://tashkent.hh.uz/employers_company/informacionnye_tekhnologii_sistemnaya_integraciya_internet/internet_kompaniya_poiskoviki_platezhnye_sistemy_soc.seti_informacionno_poznavatelnye_i_razvlekatelnye_resursy_prodvizhenie_sajtov_i_prochee"),
    ("Internet provayderlar", "https://tashkent.hh.uz/employers_company/informacionnye_tekhnologii_sistemnaya_integraciya_internet/internet_provajder"),
    ("Dasturiy ta'minot", "https://tashkent.hh.uz/employers_company/informacionnye_tekhnologii_sistemnaya_integraciya_internet/razrabotka_programmnogo_obespecheniya"),
    ("Tizim integratsiyasi / IT konsalting", "https://tashkent.hh.uz/employers_company/informacionnye_tekhnologii_sistemnaya_integraciya_internet/sistemnaya_integraciya__avtomatizacii_tekhnologicheskikh_i_biznes_processov_predpriyatiya_it_konsalting"),
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
            """, (c["id"], c["name"], "IT / Texnologiya", "IT / Технологии", "IT / Technology", "62", 95, "hh_catalog"))
            added += 1
    conn.commit()
    conn.close()
    return added, skipped


def main():
    all_companies = {}
    print("HH.uz IT / Texnologiya — yuklanmoqda...\n")

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
    cur.execute("SELECT COUNT(*) FROM company_classifications WHERE industry_uz='IT / Texnologiya'")
    total = cur.fetchone()[0]
    conn.close()
    print(f"\nDB da jami: {total} ta")


if __name__ == "__main__":
    main()