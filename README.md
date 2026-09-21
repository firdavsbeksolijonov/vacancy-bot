# HH.uz Data Analytics Vacancy Tracker

Python-based monitoring service that continuously scans job postings on
**tashkent.hh.uz** for roles related to data analytics — Data Analyst,
Data Scientist, Data Engineer, BI Developer, Business Analyst, and
related positions — and delivers matching vacancies to a Telegram channel
in real time.

## Overview

The project searches across dozens of keyword variations in both Russian
and English, applies title-based root-word matching (e.g. `analitik`,
`analyst`, `data`, `BI`) to catch postings that simple keyword search
would miss, and filters out irrelevant results common to fuzzy search
engines (e.g. "Project Manager" appearing in an "analyst" search).

## Features

- **Broad keyword coverage** — matches full phrases (`data analyst`,
  `бизнес-аналитик`, `Power BI`) as well as root-word variations
  (`analitik`, `аналитик`, `data`, `BI`) using word-boundary regex,
  avoiding false positives from unrelated words.
- **Parallel fetching** — queries multiple search terms concurrently
  instead of sequentially, with automatic retry and backoff on rate
  limiting (HTTP 429).
- **Deduplication** — tracks previously seen postings so each vacancy is
  only delivered once.
- **Recency filtering** — only surfaces postings within a configurable
  recent time window, falling back to the posting date embedded in the
  listing description when the feed's own timestamp is unreliable.
- **Resilient delivery** — a failure on one keyword or one message does
  not interrupt the rest of the run; progress is saved incrementally.
- **Automated scheduling** — runs on a recurring schedule via CI, with
  no server or always-on process required.

## Tech Stack

- Python 3.11
- `requests` for HTTP
- `feedparser`, `pandas`, `beautifulsoup4`, `rapidfuzz`, and `openpyxl`
- `xml.etree.ElementTree` for feed parsing
- GitHub Actions for scheduling and execution

## Setup

Install the declared dependencies from this directory:

```bash
python -m pip install -r requirements.txt
```

The Telegram-enabled scripts require `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_CHAT_ID` environment variables. The scheduled workflow reads these
values from GitHub Actions secrets.

The main one-shot monitor is `check_vacancies.py`. The other root monitors are
alternative RSS workflows. The scripts under `industry_filler/` use the Excel
files in that directory and maintain `company_vacancies.db`; they can be run
from any working directory because their input paths are based on the script
location.

Vacancies without a reliable publication date are ignored rather than treated
as recent. State files are written atomically so an interrupted run does not
leave partially written JSON.

## License

This project is provided as-is for personal use.
