"""Render exercise reminders (daily session + weekly summary).

Facts come from plan.py (deterministic). The daily message is optionally passed
through Claude for friendlier wording; if Claude is unavailable the
deterministic text is sent as-is so a reminder always goes out.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import config, plan
from .plan import Session


def _format_session(s: Session, header: str | None = None) -> str:
    lines = []
    if header:
        lines.append(header)
    lines.append(f"🏋️ {s.weekday_name} — {s.title}")
    if s.week in (0, 99):
        lines += [f"• {d}" for d in s.details]
        return "\n".join(lines)
    lines.append(f"Week {s.week}/24 · Phase {s.phase}")
    lines.append("")
    lines += [f"• {d}" for d in s.details]
    if s.notes:
        lines.append("")
        lines += [f"› {n}" for n in s.notes]
    return "\n".join(lines)


def daily_message(d: date | None = None) -> str:
    """The 05:30 daily session message."""
    d = d or date.today()
    s = plan.session_for(d)
    base = _format_session(s, header="Good morning — today's training:")
    rendered = _render_with_claude(s, base)
    return rendered or base


def weekly_summary(today: date | None = None) -> str:
    """The Sunday 18:00 summary of the *coming* week."""
    today = today or date.today()
    this_week = plan.week_for(today)

    if this_week in (0, 99) or this_week >= config.PLAN_WEEKS:
        # On/after the final week's Sunday there is no "next week".
        if this_week == config.PLAN_WEEKS:
            return ("🎉 That was the final week — race done (or here)!\n"
                    "The 24-week block wraps up now. Time to plan what's next.")
        if this_week == 99:
            return "🎉 Plan complete. No upcoming week to preview."
        return (f"Plan starts {config.PLAN_START.isoformat()}. "
                "Weekly summaries begin once Week 1 is under way.")

    next_week = this_week + 1
    sessions = plan.week_sessions(next_week)
    phase = plan.phase_for(next_week)

    lines = [f"📅 Next week — Week {next_week}/24 (Phase {phase})",
             f"Progression: {plan.progression_note(next_week)}",
             f"Martial arts intensity: {plan.martial_arts_intensity(next_week)}",
             ""]

    # Phase-boundary / milestone flags.
    if next_week == 9:
        lines.append("⚑ Enters PHASE 2 — run distance starts building.")
    elif next_week == 17:
        lines.append("⚑ Enters PHASE 3 — peak distance, KB to maintenance.")
    elif next_week == 23:
        lines.append("⚑ TAPER week — keep it short and fresh.")
    elif next_week == 24:
        lines.append("⚑ RACE WEEK — half marathon on Sunday! 🏁")
    if next_week in (9, 17, 23, 24):
        lines.append("")

    for s in sessions:
        m = s.metrics
        lines.append(f"• {s.weekday_name}: {s.title}")
        lines.append(f"    kg: {m['weights']}  |  reps/rounds: {m['reps']}  "
                     f"|  speed: {m['speed']}")

    return "\n".join(lines)


def _render_with_claude(s: Session, fallback: str) -> str | None:
    """Optionally reword the daily session via Claude. Returns None on failure."""
    key = config.anthropic_key()
    if not key or s.week in (0, 99):
        return None
    try:
        from anthropic import Anthropic
    except Exception:
        return None

    facts = _format_session(s)
    prompt = (
        "You are writing a short morning training reminder for a Telegram "
        "message. Rewrite the session below as a concise, motivating note.\n"
        "STRICT RULES: keep every number, weight, rep, distance and interval "
        "EXACTLY as given. Do not invent or change any training detail. Plain "
        "text only (no markdown asterisks/backticks). Keep it under 120 words. "
        "You may keep simple emoji.\n\n"
        f"SESSION:\n{facts}"
    )
    try:
        client = Anthropic(api_key=key)
        msg = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        ).strip()
        return text or None
    except Exception:
        return None
