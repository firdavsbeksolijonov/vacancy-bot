"""
Noma'lum kompaniyalarni Groq AI bilan batch classify qiladi.
30 ta kompaniyani bitta so'rovda yuboradi.
"""

import sqlite3
import requests
import json
import re
import time
import logging
from pathlib import Path

DB_PATH    = Path("industry_filler/company_vacancies.db")
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
BATCH_SIZE = 30
INTERVAL   = 2  # soniya

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

PERSON_PATTERNS = [
    r"^ЯТТ\s",
    r"^ИП\s",
    r"^ЧП\s",
    r"^ФХ\s",
    r"O'G'LI",
    r"QIZI",
    r"OVICH$",
    r"EVNA$",
    r"OVNA$",
    r"ULI$",
    r"UGLI$",
]

INDUSTRY_MAP = {
    "Finance/Bank":    "Moliya / Bank / Fintech",
    "IT":              "IT / Texnologiya",
    "Healthcare":      "Sog'liqni saqlash",
    "Education":       "Ta'lim",
    "Trade":           "Savdo / E-commerce",
    "Logistics":       "Logistika / Transport",
    "Food/Restaurant": "Oziq-ovqat / Restoran",
    "Construction":    "Qurilish",
    "Consulting/Legal":"Konsalting / Huquq",
    "Manufacturing":   "Sanoat / Ishlab chiqarish",
    "Tourism":         "Turizm",
    "Automotive":      "Avtomobil",
    "Marketing":       "Marketing / Media",
    "HR":              "HR / Rekruting",
    "Agriculture":     "Qishloq xo'jaligi",
    "Other":           "Boshqa",
    "Individual":      "Jismoniy shaxs",
}

def is_person(name):
    for p in PERSON_PATTERNS:
        if re.search(p, name, re.IGNORECASE):
            return True
    return False

def groq_classify_batch(companies: list[dict], api_key: str) -> dict:
    """30 ta kompaniyani bitta Groq so'rovida classify qiladi."""
    
    numbered = "\n".join(
        f"{i+1}. {c['company_name']}"
        for i, c in enumerate(companies)
    )

    prompt = f"""You are a company industry classifier for Uzbekistan/Tashkent companies.

Classify each company into EXACTLY one of these industries:
- Finance/Bank (banks, insurance, leasing, microfinance, fintech)
- IT (software, tech, digital, telecom)
- Healthcare (clinics, pharmacies, medical)
- Education (schools, universities, courses)
- Trade (retail, wholesale, import/export)
- Logistics (transport, cargo, delivery)
- Food/Restaurant (cafes, restaurants, food production)
- Construction (building, architecture, repair)
- Consulting/Legal (audit, law, accounting, consulting)
- Manufacturing (factories, industrial, chemical, energy)
- Tourism (hotels, travel, visa)
- Automotive (car dealers, auto service)
- Marketing (advertising, media, design, PR)
- HR (recruiting, staffing)
- Agriculture (farming, agro)
- Individual (person's name, not a company)
- Other (unknown or doesn't fit)

Companies to classify:
{numbered}

Return ONLY valid JSON, no explanation:
{{"1": "Finance/Bank", "2": "IT", "3": "Other", ...}}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1000,
    }

    try:
        r = requests.post(GROQ_URL, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip()
        
        # JSON ni tozalaymiz
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
        result = json.loads(text)
        return result
    except Exception as e:
        log.error(f"Groq xato: {e}")
        return {}

def main():
    import os
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("❌ GROQ_API_KEY environment variable kerak!")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Noma'lum kompaniyalarni olish
    cur.execute("""
        SELECT employer_id, company_name 
        FROM company_classifications 
        WHERE industry_uz IN ('Noma''lum', 'Boshqa')
        ORDER BY company_name
    """)
    all_unknowns = cur.fetchall()
    log.info(f"Noma'lum kompaniyalar: {len(all_unknowns)} ta")

    # Jismoniy shaxslarni ajratamiz
    persons = []
    to_classify = []
    for row in all_unknowns:
        if is_person(row["company_name"]):
            persons.append(row)
        else:
            to_classify.append(dict(row))

    log.info(f"Jismoniy shaxs: {len(persons)} ta")
    log.info(f"Groq bilan classify: {len(to_classify)} ta")

    # Jismoniy shaxslarni yangilash
    for row in persons:
        cur.execute("""
            UPDATE company_classifications
            SET industry_uz='Jismoniy shaxs', source='pattern', confidence=95
            WHERE employer_id=?
        """, (row["employer_id"],))
    conn.commit()
    log.info(f"✅ {len(persons)} ta jismoniy shaxs yangilandi")

    # Groq bilan batch classify
    total_batches = (len(to_classify) + BATCH_SIZE - 1) // BATCH_SIZE
    classified = 0
    failed = 0

    for batch_num in range(total_batches):
        start = batch_num * BATCH_SIZE
        end   = start + BATCH_SIZE
        batch = to_classify[start:end]

        log.info(f"Batch {batch_num+1}/{total_batches}: {len(batch)} ta kompaniya")

        result = groq_classify_batch(batch, api_key)

        if not result:
            log.warning(f"Batch {batch_num+1} bo'sh natija — o'tkazildi")
            failed += len(batch)
            time.sleep(INTERVAL)
            continue

        # Natijani DB ga yozish
        for i, company in enumerate(batch):
            key = str(i + 1)
            industry_en = result.get(key, "Other")
            industry_uz = INDUSTRY_MAP.get(industry_en, "Boshqa")

            cur.execute("""
                UPDATE company_classifications
                SET industry_uz=?, source='groq', confidence=75
                WHERE employer_id=?
            """, (industry_uz, company["employer_id"]))

            log.info(f"  {company['company_name']} → {industry_uz}")
            classified += 1

        conn.commit()
        log.info(f"✅ Batch {batch_num+1} saqlandi")
        time.sleep(INTERVAL)

    conn.close()

    print("\n=== YAKUNIY NATIJA ===")
    print(f"Jami tekshirildi:   {len(all_unknowns)} ta")
    print(f"Jismoniy shaxs:     {len(persons)} ta")
    print(f"Groq classified:    {classified} ta")
    print(f"Xato/o'tkazilgan:   {failed} ta")

if __name__ == "__main__":
    main()