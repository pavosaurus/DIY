"""Telegram delivery with retry/backoff."""

from __future__ import annotations

import time

import requests

from . import config

API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(text: str, *, retries: int = 4) -> bool:
    """Send a plain-text message. Retries on network / 5xx errors."""
    token = config.telegram_token()
    chat_id = config.telegram_chat_id()
    if not token or not chat_id:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variable."
        )

    url = API.format(token=token)
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}

    delay = 2
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, data=payload, timeout=30)
            if resp.status_code == 200:
                return True
            # 4xx (bad token/chat) won't fix itself — fail fast.
            if 400 <= resp.status_code < 500:
                raise RuntimeError(
                    f"Telegram rejected the message ({resp.status_code}): {resp.text}"
                )
            last_err = f"HTTP {resp.status_code}: {resp.text}"
        except requests.RequestException as e:
            last_err = str(e)

        if attempt < retries:
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(f"Telegram send failed after {retries} attempts: {last_err}")
