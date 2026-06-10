"""Entry point.

Decides which reminder (if any) is due based on the real local time in
config.TIMEZONE, builds the message, and sends it via Telegram.

The GitHub Actions workflow fires several UTC crons (two per reminder, covering
both the AEST and AEDT offsets). Only the firing whose moment maps to the
correct local time passes the window check here — so DST is handled with no
seasonal maintenance, and the wrong-offset cron (which lands ~60 min off) is
ignored.

Manual / test runs: set FORCE_REMINDER to one of
  exercise | dinner_daily | dinner_weekly | training_summary | all
to bypass the time gate. Add DRY_RUN=1 to print instead of send.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from . import config, dinner, exercise
from .send import send_telegram

# Reminder targets, expressed in local (config.TIMEZONE) time.
#   key: (weekdays where it applies, target time, stream, builder)
# weekdays: set of 0=Mon..6=Sun, or None for every day.
# stream: which Telegram bot sends it — 'exercise' or 'dinner'.
REMINDERS = {
    "exercise":         (None,  dtime(5, 30),  "exercise", lambda d: exercise.daily_message(d)),
    "dinner_weekly":    ({5},   dtime(9, 0),   "dinner",   lambda d: dinner.weekly_seed()),
    "dinner_daily":     (None,  dtime(15, 0),  "dinner",   lambda d: dinner.daily_seed()),
    "training_summary": ({6},   dtime(18, 0),  "exercise", lambda d: exercise.weekly_summary(d)),
}


def _now_local() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE))


def _due_now(now: datetime) -> list[str]:
    """Reminder keys whose target time falls within the send window right now."""
    due = []
    window = timedelta(minutes=config.SEND_WINDOW_MINUTES)
    for key, (weekdays, target, _stream, _builder) in REMINDERS.items():
        if weekdays is not None and now.weekday() not in weekdays:
            continue
        target_dt = now.replace(hour=target.hour, minute=target.minute,
                                second=0, microsecond=0)
        if target_dt <= now < target_dt + window:
            due.append(key)
    return due


def _build(key: str, now: datetime) -> str:
    return REMINDERS[key][3](now.date())


def _stream(key: str) -> str:
    return REMINDERS[key][2]


def main() -> int:
    now = _now_local()
    dry = os.environ.get("DRY_RUN", "") not in ("", "0", "false", "False")
    forced = os.environ.get("FORCE_REMINDER", "").strip()

    if forced:
        keys = list(REMINDERS) if forced == "all" else [forced]
        for k in keys:
            if k not in REMINDERS:
                print(f"Unknown FORCE_REMINDER value: {k}", file=sys.stderr)
                return 2
    else:
        keys = _due_now(now)

    if not keys:
        print(f"[{now.isoformat()}] Nothing due. Exiting cleanly.")
        return 0

    failures = []
    for key in keys:
        message = _build(key, now)
        stream = _stream(key)
        if dry:
            print(f"--- {key} via [{stream}] bot ({now.isoformat()}) ---\n{message}\n")
            continue
        try:
            send_telegram(message, stream)
            print(f"[{now.isoformat()}] Sent: {key} via {stream} bot")
        except Exception as e:  # noqa: BLE001 - surface but keep going
            print(f"[{now.isoformat()}] FAILED {key}: {e}", file=sys.stderr)
            failures.append(key)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
