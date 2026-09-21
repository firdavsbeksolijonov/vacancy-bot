"""
company_classifications jadvalidagi Noma'lum kompaniyalarni
Orginfo.uz + Moyana.uz + fuzzy match orqali qayta classify qiladi.
"""

import sqlite3
import requests
import time
import re
import logging
from pathlib import Path

DB_PATH = Path("industry_filler/company_vacancies.db")
REQUEST_TIMEOUT = 10
INTERVAL = 1.5

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

ORGINFO_URL = "https://orginfo.uz/search/"
MOYANA_URL  = "https://moyana.uz/search"

OKVED_MAP = {
    range(64, 67): "Moliya / Bank / Fintech",
    range(62, 64): "IT / Texnologiya",
    range(45, 48): "Savdo / E-commerce",
    range(49, 54): "Logistika / Transport",
    range(41, 44): "Qurilish",
    range(68, 69): "Ko'chmas mulk",
    range(69, 79): "Konsalting / Huquq",
    range(85, 86): "Ta'lim",
    range(86, 89): "Sog'liqni saqlash",
    range(73, 75): "Marketing / Media",
    range(78, 79): "HR / Rekruting",
}

FUZZY = {
    "Moliya / Bank / Fintech":    ["bank", "банк", "moliya", "finance", "credit", "кредит", "lombard", "ломбард", "sugurta", "страхов", "leasing", "лизинг", "fintech", "мфо", "invest", "инвест"],
    "IT / Texnologiya":           ["tech", "software", "digital", "программ", "computer", "компьютер", "telecom", "телеком", "internet", "систем", "cloud", "data", ".ai", "dev"],
    "Sog'liqni saqlash":          ["pharm", "фарм", "medical", "медицин", "clinic", "клиник", "hospital", "health", "здоров", "tibbiy", "dori", "аптек", "laborator"],
    "Ta'lim":                     ["school", "школ", "academy", "академи", "university", "университ", "education", "образован", "ta'lim", "maktab", "institute", "институт", "курс"],
    "Savdo / E-commerce":         ["trade", "торгов", "retail", "shop", "магазин", "distribution", "дистрибьют", "wholesale", "import", "импорт", "export", "экспорт"],
    "Logistika / Transport":      ["logist", "логист", "transport", "транспорт", "cargo", "карго", "delivery", "доставк", "shipping", "express", "forwarding"],
    "Oziq-ovqat / Restoran":      ["food", "фуд", "restaurant", "ресторан", "cafe", "кафе", "catering", "bakery", "пекарн", "confect", "кондитер", "dairy", "молоч", "agro", "агро", "tea", "coffee"],
    "Qurilish":                   ["build", "строит", "construct", "qurilish", "remont", "ремонт", "архитект", "электр"],
    "HR / Rekruting":             ["hr ", " hr", "рекрутин", "recrut", "кадр", "персонал", "staffing", "talent"],
    "Marketing / Media":          ["marketing", "маркетинг", "media", "медиа", "реклам", "advert", "brand", "бренд", "smm", "дизайн", "design"],
    "Konsalting / Huquq":         ["consult", "консалт", "audit", "аудит", "law", "юрид", "lawyer", "legal", "адвокат", "налог", "tax", "accounting", "бухгалтер"],
    "Sanoat / Ishlab chiqarish":  ["manufactur", "производств", "factory", "фабрик", "zavod", "завод", "plant", "industrial", "промышлен", "химич", "нефт", "oil", "gas", "газ", "energy"],
    "Turizm":                     ["tour", "тур", "travel", "тревел", "hotel", "отель", "hostel", "resort", "visa", "виза"],
    "Avtomobil":                  ["auto", "авто", " car", "motor", "мотор", "vehicle", "truck", "грузов", "dealer", "дилер"],
    "Qishloq xo'jaligi":          ["farm", "фермер", "agro", "агро", "овощ", "фрукт", "dehqon", "qishloq"],
}

PERSON_PATTERNS = [
    r"^ЯТТ\s", r"^ИП\s", r"^ЧП\s", r"^ФХ\s",
    r"O'G'LI", r"QIZI", r"OVICH$", r"EVNA$", r"OVNA$", r"ULI$",
    r"^[A-ZА-Я][a-zа-я]+ [A-ZА-Я]\. ?[A-ZА-Я]\.$",
]

def is_person(name):
    for p in PERSON_PATTERNS:
        if re.search(p, name, re.IGNORECASE):
            return True
    return False

def okved_to_industry(code_str):
    try:
        code = int(str(code_str)[:2])
        for rng, industry in OKVED_MAP.items():
            if code in rng:
                return industry
    except:
        pass
    return None

def extract_okved(text):
    patterns = [
        r"(?:OKVED|OKED|ОКЭД|ОКВЭД)\s*[:#-]?\s*(\d{2})",
        r"код\s+деятельности\s*[:#-]?\s*(\d{2})",
        r'"oked"\s*:\s*"?(\d{2})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

def classify_fuzzy(name):
    n = name.lower()
    for industry, keywords in FUZZY.items():
        for kw in keywords:
            if kw.lower() in n:
                return industry
    return None

def fetch_okved(session, url, name):
    try:
        r = session.get(url, params={"q": name}, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            code = extract_okved(r.text)
            if code:
                return okved_to_industry(code), code
    except Exception as e:
        log.warning(f"{url} xato ({name}): {e}")
    return None, None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Noma'lum kompaniyalarni olish
    cur.execute("SELECT employer_id, company_name FROM company_classifications WHERE industry_uz = 'Noma''lum'")
    unknowns = cur.fetchall()
    total = len(unknowns)
    log.info(f"Noma'lum kompaniyalar: {total} ta")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    stats = {"person": 0, "orginfo": 0, "moyana": 0, "fuzzy": 0, "unknown": 0}

    for i, row in enumerate(unknowns, 1):
        emp_id = row["employer_id"]
        name   = row["company_name"]
        industry = None
        source   = "unknown"
        confidence = 0

        # 1. Jismoniy shaxs
        if is_person(name):
            industry   = "Jismoniy shaxs"
            source     = "pattern"
            confidence = 95
            stats["person"] += 1

        # 2. Fuzzy match
        if not industry:
            industry = classify_fuzzy(name)
            if industry:
                source     = "fuzzy"
                confidence = 70
                stats["fuzzy"] += 1

        # 3. Orginfo.uz
        if not industry:
            time.sleep(INTERVAL)
            industry, okved = fetch_okved(session, ORGINFO_URL, name)
            if industry:
                source     = "orginfo"
                confidence = 85
                stats["orginfo"] += 1

        # 4. Moyana.uz
        if not industry:
            industry, okved = fetch_okved(session, MOYANA_URL, name)
            if industry:
                source     = "moyana"
                confidence = 80
                stats["moyana"] += 1

        # 5. Hali ham noma'lum
        if not industry:
            industry   = "Noma'lum"
            source     = "unknown"
            confidence = 0
            stats["unknown"] += 1

        # DB yangilash
        cur.execute("""
            UPDATE company_classifications
            SET industry_uz=?, industry_ru=?, industry_en=?, source=?, confidence=?
            WHERE employer_id=?
        """, (
            industry,
            industry,  # keyinroq tarjima qo'shsa bo'ladi
            industry,
            source,
            confidence,
            emp_id,
        ))

        if i % 50 == 0:
            conn.commit()
            log.info(f"Progress: {i}/{total} | person={stats['person']} orginfo={stats['orginfo']} moyana={stats['moyana']} fuzzy={stats['fuzzy']} unknown={stats['unknown']}")

    conn.commit()
    conn.close()

    print("\n=== YAKUNIY NATIJA ===")
    print(f"Jami tekshirildi: {total} ta")
    print(f"  Jismoniy shaxs: {stats['person']} ta")
    print(f"  Orginfo.uz:     {stats['orginfo']} ta")
    print(f"  Moyana.uz:      {stats['moyana']} ta")
    print(f"  Fuzzy match:    {stats['fuzzy']} ta")
    print(f"  Hali noma'lum:  {stats['unknown']} ta")

if __name__ == "__main__":
    main()