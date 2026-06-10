"""Central configuration for the reminders system.

Edit the constants below to change behaviour. Secrets are read from the
environment (set as GitHub Actions secrets), never hard-coded here.
"""

import os
from datetime import date

# --- Schedule anchor ---------------------------------------------------------
# Monday of Week 1 of the 24-week training plan.
# Verified: 2026-06-01 is a Monday. The plan runs weeks 1..24 from here.
PLAN_START = date(2026, 6, 1)
PLAN_WEEKS = 24

# --- Timezone ----------------------------------------------------------------
# All target send times below are expressed in this local timezone. The
# scheduler fires in UTC; main.py gates on real local time so DST is handled
# automatically (Sydney switches AEST<->AEDT mid-plan).
TIMEZONE = "Australia/Sydney"

# How many minutes after a target time a scheduled run is still allowed to send.
# Absorbs GitHub Actions cron delays without letting the wrong-DST-offset cron
# (which lands ~60 min off) also fire.
SEND_WINDOW_MINUTES = 45

# --- Dinner preferences ------------------------------------------------------
# Injected into every dinner seed prompt. Edit to taste.
DIET_PREFS = (
    "Style: RecipeTin Eats / Nagi. Approachable, well-tested, big on flavour. "
    "Prefer dinners that are realistic on a weeknight and reuse pantry staples. "
    "Call out anything that needs marinating or advance prep."
)

# --- Claude (for rendering the exercise message) -----------------------------
# The training facts are computed deterministically in plan.py; Claude only
# makes the message friendly. If the API key is missing or the call fails, a
# deterministic fallback message is sent instead — reminders never go silent.
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")


def bot_token(stream: str) -> str:
    """Bot token for a stream: 'exercise' or 'dinner'."""
    return os.environ.get(f"{stream.upper()}_BOT_TOKEN", "")


def chat_id(stream: str) -> str:
    """Chat ID for a stream: 'exercise' or 'dinner'."""
    return os.environ.get(f"{stream.upper()}_CHAT_ID", "")


def anthropic_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "")
