"""Shared RSS client for hh.uz vacancy feeds."""

from __future__ import annotations

import html
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import requests
from requests.adapters import HTTPAdapter

LOGGER = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0
REQUEST_TIMEOUT = (8.0, 20.0)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount(
    "https://",
    HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=0),
)

_DATE_IN_DESCRIPTION = re.compile(
    r"(?:Создана|Created)\s*:\s*(\d{2})\.(\d{2})\.(\d{4})",
    re.IGNORECASE,
)


def _backoff_seconds(attempt: int, response: requests.Response | None = None) -> float:
    """Return Retry-After for 429, otherwise exponential backoff."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                LOGGER.debug("Invalid Retry-After header: %r", retry_after)
    return BACKOFF_SECONDS * (2 ** (attempt - 1))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_date_value(value: Any) -> datetime | None:
    if not value:
        return None

    if hasattr(value, "tm_year"):
        return datetime(
            value.tm_year,
            value.tm_mon,
            value.tm_mday,
            value.tm_hour,
            value.tm_min,
            value.tm_sec,
            tzinfo=timezone.utc,
        )

    if isinstance(value, datetime):
        return _as_utc(value)

    if isinstance(value, str):
        try:
            return _as_utc(parsedate_to_datetime(value))
        except (TypeError, ValueError, IndexError):
            try:
                return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
            except ValueError:
                return None

    return None


def _parse_published_at(entry: Any, description: str) -> datetime | None:
    """Parse feedparser's structured date, raw date, then description fallback."""
    published_parsed = entry.get("published_parsed")
    parsed = _parse_date_value(published_parsed)
    if parsed is not None:
        return parsed

    for key in ("published", "pubDate", "pubdate", "date"):
        parsed = _parse_date_value(entry.get(key))
        if parsed is not None:
            return parsed

    match = _DATE_IN_DESCRIPTION.search(description)
    if match:
        day, month, year = match.groups()
        try:
            return datetime(
                int(year),
                int(month),
                int(day),
                tzinfo=timezone(timedelta(hours=5)),
            ).astimezone(timezone.utc)
        except ValueError:
            LOGGER.debug("Invalid fallback date in RSS description: %s", match.group(0))

    return None


def _strip_html(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _request_feed(url: str, params: dict[str, str] | None) -> bytes | None:
    response = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = SESSION.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429:
                LOGGER.warning("RSS request rate-limited: attempt %s/%s", attempt, MAX_ATTEMPTS)
            else:
                response.raise_for_status()
                return response.content
        except requests.RequestException as error:
            LOGGER.warning(
                "RSS request failed on attempt %s/%s for %s: %s",
                attempt,
                MAX_ATTEMPTS,
                url,
                error,
            )

        if attempt < MAX_ATTEMPTS:
            delay = _backoff_seconds(attempt, response)
            time.sleep(delay)

    LOGGER.error("RSS request failed after %s attempts: %s", MAX_ATTEMPTS, url)
    return None


def fetch_vacancies(
    url: str,
    *,
    params: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch and normalize an RSS/XML feed into vacancy dictionaries."""
    if not isinstance(url, str) or not url.strip():
        LOGGER.error("RSS URL must be a non-empty string")
        return []

    content = _request_feed(url, params)
    if content is None:
        return []

    try:
        feed = feedparser.parse(content)
    except Exception:
        LOGGER.exception("Failed to parse RSS response from %s", url)
        return []

    if getattr(feed, "bozo", False):
        LOGGER.warning("RSS feed reported a parsing issue: %s", getattr(feed, "bozo_exception", "unknown"))

    vacancies: list[dict[str, Any]] = []
    for entry in feed.entries:
        link = str(entry.get("link", "")).strip()
        vacancy_id = str(entry.get("id", "") or link).strip()
        if not vacancy_id or not link:
            LOGGER.debug("Skipping RSS entry without id/link")
            continue

        description = _strip_html(
            entry.get("summary")
            or entry.get("description")
            or entry.get("content", [{}])[0].get("value", "")
        )
        vacancies.append(
            {
                "id": vacancy_id,
                "title": str(entry.get("title", "Untitled vacancy")).strip(),
                "description": description,
                "link": link,
                "published_at": _parse_published_at(entry, description),
            }
        )

    LOGGER.info("Fetched %s vacancies from %s", len(vacancies), url)
    return vacancies


