"""Telegram delivery with retry/backoff."""

from __future__ import annotations

import time

import requests

from . import config

API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(text: str, stream: str, *, retries: int = 4) -> bool:
    """Send a plain-text message via the given stream's bot ('exercise'/'dinner').

    Retries on network / 5xx errors.
    """
    token = config.bot_token(stream)
    target = config.chat_id(stream)
    if not token or not target:
        tok_var, chat_var = config.env_names(stream)
        raise RuntimeError(
            f"Missing {tok_var} or {chat_var} environment variable."
        )

    url = API.format(token=token)
    payload = {"chat_id": target, "text": text, "disable_web_page_preview": True}

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
