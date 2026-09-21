"""Shared vacancy title, experience, date, and text filters."""

from __future__ import annotations

import html
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from rapidfuzz import fuzz
import requests

LOGGER = logging.getLogger(__name__)

_INCLUDE_TERMS = (
    # English
    "analyst", "manager", "coordinator", "specialist",
    "consultant", "lawyer", "auditor", "accountant",
    "recruiter", "marketer", "economist", "financier",
    "officer", "director", "assistant", "administrator",
    "developer", "engineer", "supervisor", "head",
    "intern", "trainee", "junior", "associate",
    "compliance", "risk", "treasury", "controller",
    "underwriter", "actuary", "teller", "cashier",

    # Russian
    "аналитик", "менеджер", "координатор", "специалист",
    "консультант", "юрист", "аудитор", "бухгалтер",
    "рекрутер", "маркетолог", "экономист", "финансист",
    "директор", "помощник", "администратор", "сотрудник",
    "инспектор", "контролер", "операционист", "кассир",
    "руководитель", "начальник", "ассистент", "офицер",
    "стажер", "стажёр", "риск", "казначей", "андеррайтер",
    "комплаенс", "финансовый", "кредитный", "операционный",
    "главный", "ведущий", "старший", "младший",

    # Uzbek
    "tahlilchi", "menejer", "koordinator", "mutaxassis",
    "maslahatchi", "yurist", "auditor", "buxgalter",
    "rekruter", "marketolog", "iqtisodchi", "moliyachi",
    "direktor", "yordamchi", "administrator", "inspektor",
    "xodim", "rahbar", "boshliq", "asistent",
    "stajyor", "moliyaviy", "kredit", "operatsion",
)

_EXCLUDE_TERMS = (
    "driver", "водитель", "haydovchi",
    "cleaner", "уборщик", "уборщица", "farrosh",
    "cook", "повар", "oshpaz",
    "security guard", "охранник", "qorovul",
    "loader", "грузчик", "yukchi",
    "janitor", "дворник",
    "courier", "курьер", "kuryer",
)

_NO_EXPERIENCE_TERMS = (
    "без опыта", "tajribasiz", "no experience",
    "без опыта работы", "опыт не требуется",
    "experience not required",
)

_JUNIOR_TERMS = (
    "junior", "стажер", "стажёр", "intern", "trainee",
    "помощник", "assistant", "yordamchi", "stajyor",
)

_ONE_TO_THREE_YEAR_TERMS = (
    "1-3 года", "1–3 года", "1 yil", "1 year",
    "от 1 года", "от 1 до 3", "1-3 years",
    "2 года", "2 yil", "2 years",
    "3 года", "3 yil", "3 years",
)

_SENIOR_TERMS = (
    "senior director", "старший директор",
)

_HIGH_EXPERIENCE_PATTERN = re.compile(
    r"(?:от\s*)?(?:[6-9]|\d{2,})\s*\+?\s*"
    r"(?:лет|года|год|years?|year|yil)",
    re.IGNORECASE,
)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

_BANK_KEYWORDS = (
    "bank", "banki", "moliya",
    "кредит", "credit", "kredit",
    "lombard", "ломбард",
    "sugurta", "страхов", "insurance",
    "lizing", "leasing", "лизинг",
    "fintech", "микрофинанс", "microfinance",
    "мфо", "мкб", "акб",
)

TARGET_INDUSTRIES = {
    "moliya / bank / fintech",
    "moliya / bank",
    "finance / banking / fintech",
    "финансы / банки / fintech",
    "финансы",
    "banking",
    "moliya",
    "финансы / банки",
    "bank",
}

KNOWN_BANK_COMPANIES = {
    "aloqabank", "kapitalbank", "ipak yuli bank",
    "hamkorbank", "tbc bank uzbekistan", "xalq banki",
    "agrobank", "asaka bank", "davr bank", "hi-tech bank",
    "infinbank", "insulin bank", "ipoteka bank",
    "mikrokreditbank", "nbu", "orientfinance", "pab",
    "poytaxt bank", "ravnaq bank", "savdogarbank",
    "trustbank", "turonbank", "universalbank", "uzagroexportbank",
    "uzmfo", "ziraatbank", "alif bank", "anor bank",
}

_ENRICHMENT_STORE = None
_ENRICHMENT_RATE_LOCK = threading.Lock()
_LAST_ENRICHMENT_REQUEST = 0.0
_ENRICHMENT_INTERVAL_SECONDS = 2.0
_DUCKDUCKGO_URL = "https://api.duckduckgo.com/"
_ORGINFO_URL = "https://orginfo.uz/search/"
_OPENINFO_URL = "https://openinfo.uz/search/"
_WIKIPEDIA_URL = "https://en.wikipedia.org/w/api.php"
_SOURCE_ERROR = object()


def _contains_term(text: str, terms: tuple[str, ...]) -> bool:
    for term in terms:
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    without_tags = _HTML_TAG_PATTERN.sub(" ", text)
    unescaped = html.unescape(without_tags)
    return " ".join(unescaped.split())


def configure_enrichment_store(store: object | None) -> None:
    global _ENRICHMENT_STORE
    _ENRICHMENT_STORE = store


def _name_has_bank_keyword(name: str) -> bool:
    return any(term in name for term in _BANK_KEYWORDS)


def _name_fuzzy_match(name: str, fuzzy_threshold: int = 85) -> bool:
    words = re.findall(r"\w+", name)
    return any(
        len(word) >= 5
        and any(
            len(keyword) >= 5
            and fuzz.ratio(word, keyword.casefold()) >= fuzzy_threshold
            for keyword in _BANK_KEYWORDS
        )
        for word in words
    )


def _get_cached_enrichment(name: str) -> dict | None:
    if _ENRICHMENT_STORE is None:
        return None
    return _ENRICHMENT_STORE.get_enrichment(name) # type: ignore


def _save_enrichment(
    name: str,
    is_finance: bool,
    confidence: int,
    source: str,
) -> None:
    if _ENRICHMENT_STORE is not None:
        _ENRICHMENT_STORE.save_enrichment( # type: ignore
            name,
            is_finance=is_finance,
            source=source,
            confidence=confidence,
        )


def _check_orginfo_uz(company_name: str) -> dict | None | object:
    try:
        response = requests.get(
            _ORGINFO_URL,
            params={"q": company_name},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        LOGGER.warning("Orginfo.uz lookup failed for %s: %s", company_name, error)
        return _SOURCE_ERROR

    content = normalize_text(response.text)
    code_matches = re.findall(
        r"(?:OK(?:ED|VED)|ОКЭД|ОКВЭД)\s*[:#-]?\s*(\d{2})",
        content,
        re.IGNORECASE,
    )
    if not any(code in {"64", "65", "66"} for code in code_matches):
        return None
    return {
        "is_finance": True,
        "industry": "Moliya / Bank / Fintech",
        "source": "orginfo.uz",
        "confidence": 90,
    }


def _check_hh_employer(employer_id: str | None) -> dict | None | object:
    if not employer_id:
        return None
    try:
        response = requests.get(
            f"https://tashkent.hh.uz/employer/{quote(str(employer_id))}",
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        LOGGER.warning("HH employer lookup failed for %s: %s", employer_id, error)
        return None
    content = normalize_text(response.text).casefold()
    if any(term in content for term in _BANK_KEYWORDS):
        return {
            "is_finance": True,
            "industry": "Moliya / Bank / Fintech",
            "source": "hh.uz",
            "confidence": 90,
        }
    return None


def _check_openinfo_uz(company_name: str) -> dict | None | object:
    try:
        response = requests.get(
            _OPENINFO_URL,
            params={"q": company_name},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        LOGGER.warning("Openinfo.uz lookup failed for %s: %s", company_name, error)
        return _SOURCE_ERROR

    content = normalize_text(response.text)
    code_matches = re.findall(
        r"(?:OK(?:ED|VED)|ОКЭД|ОКВЭД)\s*[:#-]?\s*(\d{2})",
        content,
        re.IGNORECASE,
    )
    if not any(code in {"64", "65", "66"} for code in code_matches):
        return None
    return {
        "is_finance": True,
        "industry": "Moliya / Bank / Fintech",
        "source": "openinfo.uz",
        "confidence": 85,
    }


def _check_wikipedia(company_name: str) -> dict | None | object:
    try:
        response = requests.get(
            _WIKIPEDIA_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": company_name,
                "format": "json",
                "srlimit": 1,
            },
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("query", {}).get("search", [])
    except (requests.RequestException, ValueError, AttributeError) as error:
        LOGGER.warning("Wikipedia lookup failed for %s: %s", company_name, error)
        return _SOURCE_ERROR
    if results:
        snippet = normalize_text(results[0].get("snippet", "")).casefold()
        if any(term in snippet for term in _BANK_KEYWORDS):
            return {
                "is_finance": True,
                "industry": "Moliya / Bank / Fintech",
                "source": "wikipedia",
                "confidence": 60,
            }
    return None


def _rate_limited_duckduckgo_request(name: str) -> dict | None | object:
    global _LAST_ENRICHMENT_REQUEST
    with _ENRICHMENT_RATE_LOCK:
        elapsed = time.monotonic() - _LAST_ENRICHMENT_REQUEST
        if elapsed < _ENRICHMENT_INTERVAL_SECONDS:
            time.sleep(_ENRICHMENT_INTERVAL_SECONDS - elapsed)
        _LAST_ENRICHMENT_REQUEST = time.monotonic()
        try:
            response = requests.get(
                _DUCKDUCKGO_URL,
                params={
                    "q": f"{name} Tashkent industry sector",
                    "format": "json",
                    "no_html": "1",
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            LOGGER.warning("Company enrichment failed for %s: %s", name, error)
            return _SOURCE_ERROR


def _check_duckduckgo(name: str) -> dict | None | object:
    data = _rate_limited_duckduckgo_request(name)
    if data is _SOURCE_ERROR:
        return _SOURCE_ERROR
    if data is None:
        return None

    parts = [str(data.get("Abstract", ""))] # type: ignore
    for topic in data.get("RelatedTopics", []): # type: ignore
        if isinstance(topic, dict):
            parts.append(str(topic.get("Text", "")))
    content = " ".join(parts).casefold()

    finance_terms = (
        "bank", "banking", "finance", "financial", "credit", "insurance",
        "fintech", "банк", "финанс", "кредит", "страхов", "молия",
    )
    is_finance = any(term in content for term in finance_terms)
    confidence = 55 if data.get("Abstract") and is_finance else 35 if is_finance else 0 # pyright: ignore[reportAttributeAccessIssue]
    return {"is_finance": is_finance, "confidence": confidence, "source": "duckduckgo"}


def _enrich_company(name: str, employer_id: str | None = None) -> dict | None:
    source_error = False
    for checker in (
        lambda: _check_hh_employer(employer_id),
        lambda: _check_orginfo_uz(name),
        lambda: _check_wikipedia(name),
        lambda: _check_duckduckgo(name),
    ):
        result = checker()
        if result is _SOURCE_ERROR:
            source_error = True
            continue
        if result and result.get("is_finance"): # type: ignore
            _save_enrichment(
                name,
                True,
                int(result["confidence"]), # type: ignore
                str(result["source"]), # type: ignore
            )
            LOGGER.info(
                "Enriched via %s: %s -> finance (confidence=%s)",
                result["source"], # type: ignore
                name,
                result["confidence"], # type: ignore
            )
            return result # type: ignore

    if source_error:
        return None
    _save_enrichment(name, False, 0, "checked")
    return {"is_finance": False, "confidence": 0, "source": "checked"}


def is_bank_company(
    name: str,
    industry: str = "",
    fuzzy_threshold: int = 85,
    employer_id: str | None = None,
) -> bool:
    """Classify a company using local signals and cached online enrichment."""
    normalized = normalize_text(name).casefold()
    if not normalized:
        return False

    # Known companies — darhol True
    if normalized in KNOWN_BANK_COMPANIES:
        LOGGER.info("Company decision: %s -> True (score=100, known)", name)
        return True

    score = 0

    # Industry ustuni — 40 ball
    normalized_industry = normalize_text(industry).casefold()
    if normalized_industry in TARGET_INDUSTRIES:
        score += 40
    # Industry da bank kalit so'zi bo'lsa ham hisoblash
    elif any(term in normalized_industry for term in _BANK_KEYWORDS):
        score += 30

    # Nom kalit so'z — 30 ball
    if _name_has_bank_keyword(normalized):
        score += 30

    # Fuzzy match — 20 ball
    if _name_fuzzy_match(normalized, fuzzy_threshold):
        score += 20

    if score >= 40:  # 50 dan 40 ga tushirildi
        LOGGER.info("Company decision: %s -> True (score=%s)", name, score)
        return True

    # Online enrichment — faqat score past bo'lsa
    cached = _get_cached_enrichment(normalized)
    if cached is not None:
        if cached.get("is_finance") and int(cached.get("confidence", 0)) >= 85:
            score += int(cached.get("confidence", 0))
    elif _ENRICHMENT_STORE is not None:
        enriched = _enrich_company(normalized, employer_id)
        if enriched and enriched.get("is_finance") and int(enriched.get("confidence", 0)) >= 85:
            score += int(enriched.get("confidence", 0))

    result = score >= 40
    LOGGER.info("Company decision: %s -> %s (score=%s)", name, result, score)
    return result


def is_title_allowed(title: str) -> bool:
    normalized = normalize_text(title).casefold()
    if not normalized:
        return False
    if _contains_term(normalized, _EXCLUDE_TERMS):
        return False
    return _contains_term(normalized, _INCLUDE_TERMS)


def is_experience_allowed(description: str) -> tuple[bool, str]:
    normalized = normalize_text(description).casefold()
    if _HIGH_EXPERIENCE_PATTERN.search(normalized) or _contains_term(
        normalized, _SENIOR_TERMS
    ):
        return False, "senior"
    if _contains_term(normalized, _NO_EXPERIENCE_TERMS):
        return True, "no_experience"
    if _contains_term(normalized, _JUNIOR_TERMS):
        return True, "junior"
    if _contains_term(normalized, _ONE_TO_THREE_YEAR_TERMS):
        return True, "1_3_years"
    return True, "other"


def is_recent(
    published_at: datetime | None,
    max_age_days: int = 7,  # 3 dan 7 ga oshirildi
) -> bool:
    if published_at is None:
        return False
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    else:
        published_at = published_at.astimezone(timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    return published_at >= cutoff