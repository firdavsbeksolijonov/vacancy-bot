"""Production entry point for the company vacancy batch monitor."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow `python cli/check_vacancies.py` from the repository root.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.company_batch_service import CompanyBatchService
from src.config import Config
from src.state_store import StateStore
from src.telegram_client import TelegramClient

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Run one configured company batch and close resources cleanly."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        config = Config.from_environment()
    except RuntimeError as error:
        LOGGER.error("Configuration error: %s", error)
        return 2

    state_store = StateStore(config.db_file)
    try:
        telegram = TelegramClient(
            config.telegram_bot_token,
            config.telegram_chat_id,
        )
        service = CompanyBatchService(
            config.excel_file,
            state_store,
            telegram,
        )
        sent_count = service.process_batch(config.batch_size)
        print(
            f"Batch complete: sent={sent_count}, "
            f"companies_checked={service.last_checked_count}"
        )
        return 0
    except Exception:
        LOGGER.exception("Vacancy batch failed")
        return 1
    finally:
        state_store.close()


if __name__ == "__main__":
    raise SystemExit(main())
