"""Shared company batch processing service."""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from . import filters, rss_client
from .state_store import StateStore

LOGGER = logging.getLogger(__name__)

MAX_WORKERS = 8
MAX_AGE_DAYS = 3


class TelegramClient(Protocol):
    def send_message(self, text: str) -> bool:
        ...


class CompanyBatchService:
    """Load finance-related employers and send unseen vacancies in batches."""

    def __init__(
        self,
        excel_path: Path,
        state_store: StateStore,
        telegram: TelegramClient | Any,
    ):
        self.excel_path = Path(excel_path)
        self.state_store = state_store
        self.telegram = telegram
        self.last_checked_count = 0
        filters.configure_enrichment_store(state_store)

    def load_companies(self) -> list[dict[str, Any]]:
        """Read and normalize finance-related companies from Excel."""
        if not self.excel_path.exists():
            LOGGER.error("Company Excel file does not exist: %s", self.excel_path)
            return []

        dataframe = pd.read_excel(self.excel_path)
        dataframe.columns = [str(column).lower().strip() for column in dataframe.columns]

        employer_id_column = next(
            (
                column
                for column in dataframe.columns
                if "employer" in column and "id" in column
            ),
            None,
        ) or ("id" if "id" in dataframe.columns else None)
        name_column = next(
            (column for column in dataframe.columns if "name" in column or "company" in column),
            None,
        )
        industry_column = next(
            (column for column in dataframe.columns if "industry" in column),
            None,
        )

        if employer_id_column is None:
            raise ValueError("Excel file must contain an employer_id or id column")

        companies: list[dict[str, Any]] = []
        for _, row in dataframe.iterrows():
            employer_id = self._cell_text(row.get(employer_id_column))
            name = self._cell_text(row.get(name_column)) if name_column else ""
            industry = self._cell_text(row.get(industry_column)) if industry_column else ""
            if not employer_id or not name or not filters.is_bank_company(
                name,
                industry,
                employer_id=employer_id,
            ):
                continue
            companies.append(
                {
                    "id": employer_id,
                    "name": name,
                    "industry": industry or "Moliya / Bank",
                }
            )

        return companies

    @staticmethod
    def _cell_text(value: Any) -> str:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        return str(value).strip()

    def get_next_batch(self, batch_size: int = 10) -> list[dict[str, Any]]:
        """Return remaining companies first, then unchecked companies."""
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        companies = self.load_companies()
        if not companies:
            return []
        by_id = {company["id"]: company for company in companies}

        remaining = [
            by_id[row["employer_id"]]
            for row in self.state_store.get_remaining_companies(batch_size)
            if row["employer_id"] in by_id
        ]
        if remaining:
            return remaining

        checked_ids = self.state_store.get_checked_company_ids()
        unchecked = [company for company in companies if company["id"] not in checked_ids]
        if unchecked:
            return unchecked[:batch_size]

        self.state_store.reset_company_batches()
        return companies[:batch_size]

    def _fetch_company_vacancies(
        self,
        company: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Fetch vacancies via RSS."""
        vacancies = rss_client.fetch_vacancies(
            "https://tashkent.hh.uz/search/vacancy/rss",
            params={
                "employer_id": company["id"],
                "area": "2759",
                "order_by": "publication_time",
            },
        )

        filtered = []
        for vacancy in vacancies:
            if not filters.is_title_allowed(vacancy.get("title", "")):
                continue
            experience_allowed, exp_type = filters.is_experience_allowed(
                vacancy.get("description", "")
            )
            if not experience_allowed:
                continue
            if not filters.is_recent(vacancy.get("published_at"), MAX_AGE_DAYS):
                continue
            vacancy = dict(vacancy)
            vacancy["company"] = company["name"]
            vacancy["industry"] = company["industry"]
            vacancy["exp_type"] = exp_type
            filtered.append(vacancy)

        return company, filtered

    def _send(self, text: str) -> bool:
        sender = getattr(self.telegram, "send_message", None)
        if sender is None and callable(self.telegram):
            sender = self.telegram
        if sender is None:
            raise TypeError("telegram must expose send_message(text)")
        return bool(sender(text))

    @staticmethod
    def _format_vacancy(vacancy: dict[str, Any]) -> str:
        exp_labels = {
            "no_experience": "🟢 Tajriba shart emas",
            "junior":        "🔵 Junior / Intern / Stajyor",
            "1_3_years":     "🟡 1-3 yil tajriba",
            "other":         "⚪ Tajriba darajasi ko'rsatilmagan",
        }

        lines = [
            f"🏢 {vacancy['company']}",
            f"💼 {vacancy['title']}",
            f"{exp_labels.get(vacancy['exp_type'], '⚪ Boshqa')}",
        ]

        if vacancy.get("description"):
            lines.append(f"📝 {vacancy['description']}")

        lines.append(f"🔗 {vacancy['link']}")
        return "\n".join(lines)

    def process_batch(self, batch_size: int = 10) -> int:
        """Fetch, filter, deliver, and track one company batch."""
        batch = self.get_next_batch(batch_size)
        self.last_checked_count = len(batch)
        if not batch:
            return 0

        fetched: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(batch))) as executor:
            futures = {
                executor.submit(self._fetch_company_vacancies, company): company
                for company in batch
            }
            for future in as_completed(futures):
                company = futures[future]
                try:
                    fetched[company["id"]] = future.result()
                except Exception:
                    LOGGER.exception("Failed to fetch vacancies for %s", company["name"])
                    fetched[company["id"]] = (company, [])

        sent_count = 0
        for company in batch:
            _, vacancies = fetched.get(company["id"], (company, []))
            unseen = [
                vacancy
                for vacancy in vacancies
                if vacancy.get("id") and not self.state_store.is_seen(vacancy["id"])
            ]
            selected = unseen[:1]
            for vacancy in selected:
                self._send(f"💰 {company['industry']} 👇👇")
                if self._send(self._format_vacancy(vacancy)):
                    self.state_store.mark_seen(
                        vacancy["id"],
                        {
                            "title":    vacancy["title"],
                            "company":  company["name"],
                            "industry": company["industry"],
                            "exp_type": vacancy["exp_type"],
                        },
                    )
                    sent_count += 1
                    unseen = unseen[1:]

            self.state_store.mark_company_checked(
                company["id"],
                company["name"],
                company["industry"],
                bool(unseen),
            )

        return sent_count