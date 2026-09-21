"""
tashkent_hh_companies_clean.xlsx faylidagi kompaniyalarning
sohasini hh.uz sahifasidan olib, industry ustunini to'ldiradi.
"""

import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup

INPUT_FILE  = "tashkent_hh_companies_clean.xlsx"
OUTPUT_FILE = "tashkent_hh_companies_with_industry.xlsx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
    "Referer": "https://tashkent.hh.uz/",
}

def get_industry(employer_id):
    """Kompaniya sahifasidan sohasini oladi."""
    url = f"https://tashkent.hh.uz/employer/{employer_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. "Отрасль" qatori
        for item in soup.find_all(["dt", "span", "div", "p"]):
            text = item.get_text(strip=True)
            if "отрасль" in text.lower() or "сфера" in text.lower():
                # Keyingi elementdan qiymatni olish
                nxt = item.find_next_sibling()
                if nxt:
                    return nxt.get_text(strip=True)

        # 2. JSON-LD dan olish
        import json, re
        scripts = soup.find_all("script", type="application/ld+json")
        for s in scripts:
            try:
                data = json.loads(s.string or "")
                if isinstance(data, dict):
                    industry = data.get("industry", "")
                    if industry:
                        return industry
            except:
                pass

        # 3. Meta description dan olish
        meta = soup.find("meta", {"name": "description"})
        if meta:
            content = meta.get("content", "")
            # "отрасль: X" kabi pattern
            match = re.search(r"отрасль[:\s]+([^,\.]+)", content, re.I)
            if match:
                return match.group(1).strip()

        return ""

    except Exception as e:
        print(f"  ⚠️ Xato ({employer_id}): {e}")
        return ""

def main():
    df = pd.read_excel(INPUT_FILE)

    if 'industry' not in df.columns:
        df['industry'] = pd.NA

    total = len(df)
    print(f"📋 Jami: {total} ta kompaniya")
    print(f"⏱  Taxminiy vaqt: {total * 2 // 60} daqiqa\n")

    # Allaqachon industry bor bo'lganlarini o'tkazib yuboramiz
    for i, row in df.iterrows():
        if pd.notna(row.get("industry")) and str(row.get("industry")).strip():
            continue

        employer_id = row["employer_id"]
        company = row["company_name"]

        industry = get_industry(employer_id)
        df.at[i, "industry"] = industry

        print(f"[{i+1}/{total}] {company} → {industry or '(topilmadi)'}")

        # Har 50 ta satrda saqlab qo'yamiz
        if (i + 1) % 50 == 0:
            df.to_excel(OUTPUT_FILE, index=False)
            print(f"  💾 {i+1} ta saqlandi...")

        # Anti-ban: 1-3 soniya kutish
        time.sleep(random.uniform(1.0, 3.0))

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n✅ Tayyor! {OUTPUT_FILE} ga saqlandi.")
    filled = df["industry"].fillna("").astype(str).str.strip().ne("").sum()
    print(f"📊 Industry topildi: {filled}/{total} ta")

if __name__ == "__main__":
    main()