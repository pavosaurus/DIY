"""Dinner reminders.

These are *seed prompts*, not finished recipes: you iterate with Claude based on
leftover ingredients. The system's job is to kick off that session with the
right context pre-loaded. No API call is needed here, so dinner reminders never
depend on Claude being reachable.

Recommended companion setup: keep one Claude Project for dinners with DIET_PREFS
as its custom instructions, so the seed prompt stays short and the Project's
history gives natural repeat-avoidance week to week.
"""

from __future__ import annotations

from . import config


def daily_seed() -> str:
    """The 15:00 daily dinner kickoff."""
    return (
        "🍽️ Tonight's dinner — paste this into your Claude dinner Project:\n"
        "────────────────────\n"
        f"{config.DIET_PREFS}\n\n"
        "I want one dinner for tonight using mainly what I have left over. "
        "Ask me what's in the fridge if I haven't said. Avoid repeating recent "
        "dinners. Give me a single recipe with ingredients and method.\n"
        "→ Tonight I have: "
    )


def weekly_seed() -> str:
    """The Saturday 09:00 weekly dinner-planning kickoff."""
    return (
        "🛒 Weekly dinner plan — paste this into your Claude dinner Project "
        "before you shop:\n"
        "────────────────────\n"
        f"{config.DIET_PREFS}\n\n"
        "Help me plan dinners for the coming week. First ask what I already "
        "have to use up, then propose a varied week of dinners that builds on "
        "those ingredients, avoids repeats from recent weeks, and gives me a "
        "consolidated shopping list of what's still needed.\n"
        "→ To use up this week: "
    )
