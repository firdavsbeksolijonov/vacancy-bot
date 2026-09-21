"""Classify every company in the Excel source and cache the result in SQLite."""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.state_store import StateStore

LOGGER = logging.getLogger(__name__)
ORGINFO_URL = "https://orginfo.uz/search/"
MOYANA_URL = "https://moyana.uz/search"
DUCKDUCKGO_URL = "https://api.duckduckgo.com/"
REQUEST_TIMEOUT = 10
REQUEST_INTERVAL_SECONDS = 1.5

INDUSTRY_LABELS = {
    "finance":      ("Moliya / Bank / Fintech",    "Финансы / Банки / Fintech",        "Finance / Banking / Fintech"),
    "it":           ("IT / Texnologiya",            "IT / Технологии",                  "IT / Technology"),
    "trade":        ("Savdo / E-commerce",          "Торговля / E-commerce",            "Trade / E-commerce"),
    "transport":    ("Logistika / Transport",       "Логистика / Транспорт",            "Logistics / Transport"),
    "construction": ("Qurilish",                    "Строительство",                    "Construction"),
    "real_estate":  ("Ko'chmas mulk",               "Недвижимость",                     "Real Estate"),
    "professional": ("Professional xizmatlar",      "Профессиональные услуги",          "Professional Services"),
    "education":    ("Ta'lim",                      "Образование",                      "Education"),
    "health":       ("Sog'liqni saqlash",           "Здравоохранение",                  "Healthcare"),
    "unknown":      ("Noma'lum",                    "Неизвестно",                       "Unknown"),
}

OKVED_RANGES = (
    ((64, 66), "finance"),
    ((62, 63), "it"),
    ((45, 47), "trade"),
    ((49, 53), "transport"),
    ((41, 43), "construction"),
    ((68, 68), "real_estate"),
    ((69, 75), "professional"),
    ((78, 78), "professional"),
    ((85, 85), "education"),
    ((86, 88), "health"),
)

FUZZY_KEYWORDS = {
    "finance":      ("bank", "finance", "financial", "credit", "кредит", "банк", "moliya", "sugurta", "insurance", "fintech", "lombard", "ломбард", "мфо", "акб"),
    "it":           ("software", "technology", "technologies", "digital", "tech", "IT", "программ", "технолог", "информацион"),
    "trade":        ("retail", "shop", "торгов", "savdo", "market", "commerce", "e-commerce"),
    "transport":    ("logistics", "transport", "логист", "транспорт", "logistika"),
    "construction": ("construction", "строител", "qurilish"),
    "real_estate":  ("real estate", "недвижим", "ko'chmas", "estate"),
    "education":    ("school", "education", "университет", "образован", "ta'lim", "akademiya", "мактаб"),
    "health":       ("clinic", "hospital", "medical", "здравоохран", "медицина", "tibbiyot", "pharm", "фарм"),
}

# DuckDuckGo dan kelgan matn ichidan industry aniqlash uchun kalit so'zlar
DUCKDUCKGO_KEYWORDS = {
    "finance":      ("bank", "banking", "finance", "financial", "insurance", "credit", "fintech", "investment", "leasing"),
    "it":           ("software", "technology", "tech", "digital", "IT", "programming", "development"),
    "trade":        ("retail", "trade", "commerce", "shop", "market", "distribution"),
    "transport":    ("logistics", "transport", "shipping", "cargo", "delivery"),
    "construction": ("construction", "building", "real estate", "architecture"),
    "education":    ("education", "school", "university", "academy", "training"),
    "health":       ("healthcare", "medical", "hospital", "clinic", "pharmacy"),
}


def _labels(key: str) -> tuple[str, str, str]:
    return INDUSTRY_LABELS.get(key, INDUSTRY_LABELS["unknown"])


def _cell_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _industry_from_excel(value: str) -> str | None:
    text = value.casefold().strip()
    if not text or text in {"nan", "none", "unknown", "noma'lum", "неизвестно"}:
        return None
    for key, keywords in FUZZY_KEYWORDS.items():
        if any(keyword.casefold() in text for keyword in keywords):
            return key
    return "unknown"


def _extract_okved(response_text: str) -> str | None:
    patterns = (
        r"(?:OK(?:ED|VED)|ОКЭД|ОКВЭД)\s*[:#-]?\s*(\d{2}(?:\.\d{1,2})?)",
        r"(?:код\s+деятельности|activity\s+code)\s*[:#-]?\s*(\d{2}(?:\.\d{1,2})?)",
    )
    for pattern in patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _industry_from_okved(okved_code: str | None) -> str | None:
    if not okved_code:
        return None
    try:
        major_code = int(okved_code[:2])
    except ValueError:
        return None
    for (start, end), industry in OKVED_RANGES:
        if start <= major_code <= end:
            return industry
    return None


def _orginfo_classify(session: requests.Session, company_name: str) -> tuple[str | None, str | None]:
    try:
        response = session.get(ORGINFO_URL, params={"q": company_name}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        LOGGER.warning("Orginfo lookup failed for %s: %s", company_name, error)
        return None, None
    okved_code = _extract_okved(response.text)
    return _industry_from_okved(okved_code), okved_code


def _moyana_classify(session: requests.Session, company_name: str) -> tuple[str | None, str | None]:
    try:
        response = session.get(MOYANA_URL, params={"q": company_name}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        LOGGER.warning("Moyana lookup failed for %s: %s", company_name, error)
        return None, None
    okved_code = _extract_okved(response.text)
    if okved_code is None:
        import re as _re
        match = _re.search(r'"oked"\s*:\s*"?(\d{2}(?:\.\d{1,2})?)', response.text, _re.IGNORECASE)
        okved_code = match.group(1) if match else None
    return _industry_from_okved(okved_code), okved_code


def _duckduckgo_classify(session: requests.Session, company_name: str) -> str | None:
    """DuckDuckGo dan kompaniya haqida ma'lumot olib, sohasini aniqlaydi."""
    try:
        response = session.get(
            DUCKDUCKGO_URL,
            params={
                "q": f"{company_name} Uzbekistan company industry",
                "format": "json",
                "no_html": "1",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        LOGGER.warning("DuckDuckGo lookup failed for %s: %s", company_name, error)
        return None

    # Barcha matnni yig'amiz
    parts = [str(data.get("AbstractText", ""))]
    for topic in data.get("RelatedTopics", []):
        if isinstance(topic, dict):
            parts.append(str(topic.get("Text", "")))
    context = " ".join(part for part in parts if part).casefold()

    if not context.strip():
        return None

    # Kalit so'zlar bo'yicha soha aniqlash
    for industry, keywords in DUCKDUCKGO_KEYWORDS.items():
        if any(kw.casefold() in context for kw in keywords):
            LOGGER.info("DuckDuckGo classified %s → %s", company_name, industry)
            return industry

    return None


def _fuzzy_classify(company_name: str) -> str:
    text = company_name.casefold()
    for industry, keywords in FUZZY_KEYWORDS.items():
        if any(keyword.casefold() in text for keyword in keywords):
            return industry
    return "unknown"


def _read_companies(excel_path: Path) -> list[dict[str, str]]:
    dataframe = pd.read_excel(excel_path)
    dataframe.columns = [str(column).lower().strip() for column in dataframe.columns]
    id_column = next((c for c in dataframe.columns if "employer" in c and "id" in c), None)
    id_column = id_column or ("id" if "id" in dataframe.columns else None)
    name_column = next((c for c in dataframe.columns if "name" in c or "company" in c), None)
    industry_column = next((c for c in dataframe.columns if "industry" in c), None)
    if not id_column or not name_column:
        raise ValueError("Excel must contain employer_id/id and company_name columns")

    companies = []
    for _, row in dataframe.iterrows():
        employer_id = _cell_text(row.get(id_column))
        company_name = _cell_text(row.get(name_column))
        industry = _cell_text(row.get(industry_column)) if industry_column else ""
        if employer_id and company_name:
            companies.append({"employer_id": employer_id, "company_name": company_name, "industry": industry})
    return companies


def classify_companies(
    excel_path: Path,
    db_path: Path,
    *,
    reclassify_unknown: bool = False,
) -> dict[str, int]:
    companies = _read_companies(excel_path)
    summary = {
        "total": len(companies), "skipped": 0, "excel": 0,
        "moyana": 0, "orginfo": 0, "duckduckgo": 0, "fuzzy": 0, "unknown": 0,
    }
    session = requests.Session()
    session.headers.update({"User-Agent": "HH-Vacancy-Company-Classifier/1.0"})

    with StateStore(db_path) as state:
        for index, company in enumerate(companies, start=1):
            employer_id = company["employer_id"]
            name = company["company_name"]

            cached = state.get_classification(employer_id)
            if cached and not (reclassify_unknown and cached["industry_uz"] == "Noma'lum"):
                summary["skipped"] += 1
                continue

            # 1. Excel industry ustuni
            industry_key = _industry_from_excel(company["industry"])
            okved_code = None
            source = "excel"
            confidence = 100

            # 2. Moyana.uz → OKVED
            if industry_key is None:
                time.sleep(REQUEST_INTERVAL_SECONDS)
                industry_key, okved_code = _moyana_classify(session, name)
                if industry_key is not None:
                    source = "moyana.uz"
                    confidence = 85

            # 3. Orginfo.uz → OKVED
            if industry_key is None:
                industry_key, okved_code = _orginfo_classify(session, name)
                if industry_key is not None:
                    source = "orginfo.uz"
                    confidence = 85

            # 4. DuckDuckGo
            if industry_key is None:
                industry_key = _duckduckgo_classify(session, name)
                if industry_key is not None:
                    source = "duckduckgo"
                    confidence = 60

            # 5. Fuzzy match
            if industry_key is None:
                industry_key = _fuzzy_classify(name)
                source = "fuzzy"
                confidence = 70 if industry_key != "unknown" else 0

            uz, ru, en = _labels(industry_key)
            state.save_classification(
                employer_id, name,
                industry_uz=uz, industry_ru=ru, industry_en=en,
                okved_code=okved_code,
                confidence=confidence,
                source=source,
            )

            source_key = {"moyana.uz": "moyana", "orginfo.uz": "orginfo"}.get(source, source)
            summary[source_key] = summary.get(source_key, 0) + 1
            if industry_key == "unknown":
                summary["unknown"] += 1

            if index % 50 == 0:
                LOGGER.info("Progress: %s/%s companies classified", index, len(companies))

    session.close()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify all companies from Excel")
    parser.add_argument("--excel", type=Path, default=REPO_ROOT / "industry_filler" / "tashkent_hh_companies_clean.xlsx")
    parser.add_argument("--db",    type=Path, default=REPO_ROOT / "industry_filler" / "company_vacancies.db")
    parser.add_argument("--reclassify-unknown", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        summary = classify_companies(args.excel, args.db, reclassify_unknown=args.reclassify_unknown)
    except Exception:
        LOGGER.exception("Company classification failed")
        return 1

    print("Classification complete:")
    print(", ".join(f"{key}={value}" for key, value in summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())