"""Thread-safe SQLite state store for sent vacancy IDs."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sent_jobs (
    vacancy_id TEXT PRIMARY KEY,
    title TEXT,
    company TEXT,
    industry TEXT,
    exp_type TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_BATCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS company_batches (
    employer_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    industry TEXT,
    last_checked TIMESTAMP,
    has_remaining INTEGER NOT NULL DEFAULT 0
)
"""

_ENRICHMENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS company_enrichment (
    company_name TEXT PRIMARY KEY,
    is_finance INTEGER NOT NULL,
    source TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_CLASSIFICATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS company_classifications (
    employer_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    industry_uz TEXT NOT NULL,
    industry_ru TEXT NOT NULL,
    industry_en TEXT NOT NULL,
    okved_code TEXT,
    confidence INTEGER NOT NULL,
    source TEXT NOT NULL,
    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class StateStore:
    """SQLite-backed sent-vacancy store with legacy state migration."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._closed = False
        self._connection = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA busy_timeout=30000")
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            self._connection.execute("BEGIN")
            try:
                table_info = self._connection.execute(
                    "PRAGMA table_info(sent_jobs)"
                ).fetchall()
                columns = {row[1] for row in table_info}

                if table_info and "vacancy_id" not in columns:
                    self._connection.execute("ALTER TABLE sent_jobs RENAME TO sent_jobs_legacy")
                    self._connection.execute(_SCHEMA)
                    legacy_columns = {row[1] for row in table_info}
                    source_id = "job_id" if "job_id" in legacy_columns else None
                    if source_id:
                        self._connection.execute(
                            """
                            INSERT OR IGNORE INTO sent_jobs
                                (vacancy_id, title, company, industry, exp_type, sent_at)
                            SELECT job_id, title, NULL, industry, NULL, sent_at
                            FROM sent_jobs_legacy
                            WHERE job_id IS NOT NULL AND job_id != ''
                            """
                        )
                    self._connection.execute("DROP TABLE sent_jobs_legacy")
                else:
                    self._connection.execute(_SCHEMA)
                    columns = {
                        row[1]
                        for row in self._connection.execute(
                            "PRAGMA table_info(sent_jobs)"
                        ).fetchall()
                    }
                    if "exp_type" not in columns:
                        self._connection.execute(
                            "ALTER TABLE sent_jobs ADD COLUMN exp_type TEXT"
                        )
                    for column, definition in (
                        ("company", "TEXT"),
                        ("industry", "TEXT"),
                    ):
                        if column not in columns:
                            self._connection.execute(
                                f"ALTER TABLE sent_jobs ADD COLUMN {column} {definition}"
                            )
                self._connection.execute(_BATCH_SCHEMA)
                self._connection.execute(_ENRICHMENT_SCHEMA)
                self._connection.execute(_CLASSIFICATION_SCHEMA)

                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

            self._import_legacy_json()

    def _import_legacy_json(self) -> None:
        json_path = self.db_path.with_name("seen_ids.json")
        if not json_path.exists():
            return

        try:
            with json_path.open("r", encoding="utf-8") as file:
                values = json.load(file)
            if not isinstance(values, list):
                raise ValueError("legacy seen_ids.json must contain a list")
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            LOGGER.warning("Could not import legacy state %s: %s", json_path, error)
            return

        try:
            with self._lock:
                self._connection.executemany(
                    "INSERT OR IGNORE INTO sent_jobs (vacancy_id) VALUES (?)",
                    [
                        (str(value),)
                        for value in values
                        if isinstance(value, (str, int)) and str(value).strip()
                    ],
                )
                self._connection.commit()

            migrated_path = json_path.with_name("seen_ids.json.migrated")
            if migrated_path.exists():
                migrated_path.unlink()
            os.replace(json_path, migrated_path)
            LOGGER.info("Imported %s legacy vacancy IDs", len(values))
        except Exception:
            self._connection.rollback()
            LOGGER.exception("Could not import legacy state %s", json_path)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("StateStore is closed")

    def is_seen(self, vacancy_id: str) -> bool:
        """Return whether a non-empty vacancy ID is already stored."""
        if not isinstance(vacancy_id, str) or not vacancy_id.strip():
            return False
        with self._lock:
            self._ensure_open()
            row = self._connection.execute(
                "SELECT 1 FROM sent_jobs WHERE vacancy_id = ? LIMIT 1",
                (vacancy_id,),
            ).fetchone()
            return row is not None

    def mark_seen(self, vacancy_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Atomically store a vacancy, ignoring duplicate IDs."""
        if not isinstance(vacancy_id, str) or not vacancy_id.strip():
            raise ValueError("vacancy_id must be a non-empty string")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("metadata must be a dictionary or None")

        metadata = metadata or {}
        with self._lock:
            self._ensure_open()
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute(
                    """
                    INSERT OR IGNORE INTO sent_jobs
                        (vacancy_id, title, company, industry, exp_type, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vacancy_id,
                        metadata.get("title"),
                        metadata.get("company"),
                        metadata.get("industry"),
                        metadata.get("exp_type"),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def get_remaining_companies(self, limit: int) -> list[dict[str, Any]]:
        """Return previously checked companies with unseen work remaining."""
        with self._lock:
            self._ensure_open()
            rows = self._connection.execute(
                """
                SELECT employer_id, company_name, industry
                FROM company_batches
                WHERE has_remaining = 1
                ORDER BY last_checked ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_checked_company_ids(self) -> set[str]:
        with self._lock:
            self._ensure_open()
            rows = self._connection.execute(
                "SELECT employer_id FROM company_batches"
            ).fetchall()
            return {row[0] for row in rows}

    def mark_company_checked(
        self,
        employer_id: str,
        company_name: str,
        industry: str,
        has_remaining: bool,
    ) -> None:
        with self._lock:
            self._ensure_open()
            self._connection.execute(
                """
                INSERT INTO company_batches
                    (employer_id, company_name, industry, last_checked, has_remaining)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
                ON CONFLICT(employer_id) DO UPDATE SET
                    company_name = excluded.company_name,
                    industry = excluded.industry,
                    last_checked = excluded.last_checked,
                    has_remaining = excluded.has_remaining
                """,
                (employer_id, company_name, industry, int(has_remaining)),
            )
            self._connection.commit()

    def reset_company_batches(self) -> None:
        with self._lock:
            self._ensure_open()
            self._connection.execute("DELETE FROM company_batches")
            self._connection.commit()

    def get_enrichment(self, company_name: str) -> dict[str, Any] | None:
        with self._lock:
            self._ensure_open()
            row = self._connection.execute(
                """
                SELECT company_name, is_finance, source, confidence, checked_at
                FROM company_enrichment
                WHERE company_name = ?
                """,
                (company_name,),
            ).fetchone()
            return dict(row) if row else None

    def save_enrichment(
        self,
        company_name: str,
        *,
        is_finance: bool,
        source: str,
        confidence: int,
    ) -> None:
        with self._lock:
            self._ensure_open()
            self._connection.execute(
                """
                INSERT INTO company_enrichment
                    (company_name, is_finance, source, confidence, checked_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(company_name) DO UPDATE SET
                    is_finance = excluded.is_finance,
                    source = excluded.source,
                    confidence = excluded.confidence,
                    checked_at = excluded.checked_at
                """,
                (company_name, int(is_finance), source, confidence),
            )
            self._connection.commit()

    def get_classification(self, employer_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._ensure_open()
            row = self._connection.execute(
                "SELECT * FROM company_classifications WHERE employer_id = ?",
                (employer_id,),
            ).fetchone()
            return dict(row) if row else None

    def save_classification(
        self,
        employer_id: str,
        company_name: str,
        *,
        industry_uz: str,
        industry_ru: str,
        industry_en: str,
        okved_code: str | None,
        confidence: int,
        source: str,
    ) -> None:
        with self._lock:
            self._ensure_open()
            self._connection.execute(
                """
                INSERT INTO company_classifications
                    (employer_id, company_name, industry_uz, industry_ru,
                     industry_en, okved_code, confidence, source, classified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(employer_id) DO UPDATE SET
                    company_name = excluded.company_name,
                    industry_uz = excluded.industry_uz,
                    industry_ru = excluded.industry_ru,
                    industry_en = excluded.industry_en,
                    okved_code = excluded.okved_code,
                    confidence = excluded.confidence,
                    source = excluded.source,
                    classified_at = excluded.classified_at
                """,
                (
                    employer_id,
                    company_name,
                    industry_uz,
                    industry_ru,
                    industry_en,
                    okved_code,
                    confidence,
                    source,
                ),
            )
            self._connection.commit()

    def get_classified_companies(
        self,
        exclude: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """DB dan classified kompaniyalarni qaytaradi."""
        exclude = exclude or ["Noma'lum", "Jismoniy shaxs", "Boshqa"]
        placeholders = ",".join("?" for _ in exclude)
        with self._lock:
            self._ensure_open()
            rows = self._connection.execute(
                f"""
                SELECT employer_id, company_name, industry_uz
                FROM company_classifications
                WHERE industry_uz NOT IN ({placeholders})
                AND industry_uz IS NOT NULL
                ORDER BY company_name
                """,
                exclude,
            ).fetchall()
            return [
                {
                    "id":       row["employer_id"],
                    "name":     row["company_name"],
                    "industry": row["industry_uz"],
                }
                for row in rows
            ]

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True

    def __enter__(self) -> "StateStore":
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
