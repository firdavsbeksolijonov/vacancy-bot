"""Central application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    excel_file: Path
    db_file: Path
    max_age_days: int = 3
    batch_size: int = 10
    max_per_company: int = 1

    @classmethod
    def from_environment(cls) -> "Config":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured"
            )

        return cls(
            telegram_bot_token=token,
            telegram_chat_id=chat_id,
            excel_file=REPO_ROOT / "industry_filler" / "tashkent_hh_companies_clean.xlsx",
            db_file=REPO_ROOT / "industry_filler" / "company_vacancies.db",
        )

    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        return self.telegram_bot_token

    @property
    def TELEGRAM_CHAT_ID(self) -> str:
        return self.telegram_chat_id

    @property
    def EXCEL_FILE(self) -> Path:
        return self.excel_file

    @property
    def DB_FILE(self) -> Path:
        return self.db_file

    @property
    def MAX_AGE_DAYS(self) -> int:
        return self.max_age_days

    @property
    def BATCH_SIZE(self) -> int:
        return self.batch_size

    @property
    def MAX_PER_COMPANY(self) -> int:
        return self.max_per_company
