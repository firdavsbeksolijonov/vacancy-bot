"""Small, retrying Telegram Bot API client.

The public ``send_message`` function accepts plain text. It escapes HTML
metacharacters before sending so vacancy data cannot inject Telegram markup.
"""

from __future__ import annotations

import html
import logging
import os
import threading
import time
from typing import Optional

import requests

LOGGER = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0
MIN_MESSAGE_INTERVAL_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30.0

_rate_limit_lock = threading.Lock()
_last_message_at = 0.0


def _configuration() -> tuple[str, str]:
    """Read and validate Telegram credentials at call time."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured"
        )
    return token, chat_id


def _wait_for_rate_limit() -> None:
    """Allow at most one outgoing message per second per process."""
    global _last_message_at

    with _rate_limit_lock:
        now = time.monotonic()
        wait_seconds = MIN_MESSAGE_INTERVAL_SECONDS - (now - _last_message_at)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        _last_message_at = time.monotonic()


def _backoff(attempt: int) -> None:
    time.sleep(BACKOFF_SECONDS * (2 ** (attempt - 1)))


def _send_message(text: str, token: str, chat_id: str) -> bool:
    """Send plain text to Telegram, returning whether delivery succeeded.

    The text is HTML-escaped before being sent with Telegram's HTML parse mode.
    Network errors, HTTP errors, and Telegram API errors are retried up to
    three total attempts with exponential backoff.
    """
    if not isinstance(text, str) or not text.strip():
        LOGGER.error("Telegram message must be a non-empty string")
        return False

    payload = {
        "chat_id": chat_id,
        "text": html.escape(text, quote=False),
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        _wait_for_rate_limit()
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
            response_data: Optional[dict] = None
            try:
                response_data = response.json()
            except ValueError:
                pass

            if response.ok and response_data is not None and response_data.get("ok"):
                return True

            LOGGER.warning(
                "Telegram delivery failed on attempt %s/%s: HTTP %s",
                attempt,
                MAX_ATTEMPTS,
                response.status_code,
            )
        except requests.RequestException as error:
            LOGGER.warning(
                "Telegram request failed on attempt %s/%s: %s",
                attempt,
                MAX_ATTEMPTS,
                error,
            )

        if attempt < MAX_ATTEMPTS:
            _backoff(attempt)

    LOGGER.error("Telegram delivery failed after %s attempts", MAX_ATTEMPTS)
    return False


def send_message(text: str) -> bool:
    """Send a message using credentials from the environment."""
    try:
        token, chat_id = _configuration()
    except RuntimeError as error:
        LOGGER.error("Telegram configuration error: %s", error)
        return False
    return _send_message(text, token, chat_id)


class TelegramClient:
    """Telegram sender with explicitly supplied credentials."""

    def __init__(self, token: str, chat_id: str):
        self.token = token.strip()
        self.chat_id = chat_id.strip()
        if not self.token or not self.chat_id:
            raise ValueError("Telegram token and chat ID must be non-empty")

    def send_message(self, text: str) -> bool:
        return _send_message(text, self.token, self.chat_id)
