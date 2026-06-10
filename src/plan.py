"""Deterministic 24-week training plan logic.

Source of truth for content is data/exercise_master_prompt.md; this module
encodes the schedule so that, for any date, we can compute the exact session
without calling an LLM. The renderer (exercise.py) turns these facts into a
message and may optionally pass them through Claude for friendlier wording.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import config

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]


@dataclass
class Session:
    week: int                 # 1..24, or 0 = before plan, 99 = after plan
    phase: int                # 1, 2, 3 (0 if outside plan)
    weekday: int              # 0=Mon .. 6=Sun
    title: str
    details: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def weekday_name(self) -> str:
        return WEEKDAY_NAMES[self.weekday]


def week_for(d: date) -> int:
    """Plan week number for a date. 0 = before start, 99 = after week 24."""
    delta = (d - config.PLAN_START).days
    if delta < 0:
        return 0
    w = delta // 7 + 1
    return w if w <= config.PLAN_WEEKS else 99


def phase_for(week: int) -> int:
    if week < 1 or week > config.PLAN_WEEKS:
        return 0
    if week <= 8:
        return 1
    if week <= 16:
        return 2
    return 3


def cycle_week(week: int) -> int:
    """Position in the repeating 4-week progression block (1..4)."""
    return (week - 1) % 4 + 1


def progression_note(week: int) -> str:
    cw = cycle_week(week)
    return {
        1: "Week 1 of block — establish form, baseline weight.",
        2: "Week 2 of block — add 1 rep per exercise vs last week.",
        3: "Week 3 of block — increase one bell size where form allows.",
        4: "Week 4 of block — DELOAD. Drop back to block week-1 weight.",
    }[cw]


def martial_arts_intensity(week: int) -> str:
    return {1: "low", 2: "moderate", 3: "low"}[phase_for(week)]


def _thursday_run(week: int) -> tuple[str, list[str]]:
    """Return (summary, detail_lines) for the Thursday run."""
    phase = phase_for(week)
    if phase == 1:
        if week <= 2:
            return "Walk/run intervals", ["Walk 2 min / run 1 min x8 (start with the walk)."]
        if week <= 4:
            return "Walk/run intervals", ["Walk 1 min / run 2 min x8."]
        if week <= 6:
            return "Walk/run intervals", ["Walk 1 min / run 5 min x4."]
        return "Walk/run intervals", ["Walk 1 min / run 10 min x3."]
    if phase == 2:
        # 5km (wk9) building +1km/week to 12km (wk16), easy conversational pace.
        km = 5 + (week - 9)
        lines = [f"{km} km easy, conversational pace."]
        if week >= 9:
            lines.append("Finish with 4 x strides (bone-density / turnover stimulus).")
        return f"{km} km easy run", lines
    # Phase 3
    if week <= 22:
        # weeks 17..22 build 13 -> 20 km.
        targets = {17: 13, 18: 14.5, 19: 16, 20: 17, 21: 18.5, 22: 20}
        km = targets[week]
        return f"{km:g} km long run", [f"{km:g} km easy/long run.",
                                       "Finish with 4 x strides."]
    if week == 23:
        return "10 km taper run", ["10 km easy — taper week, stay fresh."]
    # week 24 race week
    return "Race week", [
        "Tuesday: 5 km easy shakeout, then rest through to race day.",
        "SUNDAY: HALF MARATHON — race day! Trust the taper.",
    ]


def _saturday_run(week: int) -> str:
    phase = phase_for(week)
    if phase == 1:
        return "Run after: easy 10 min (or Japanese interval walk)."
    if phase == 2:
        return "Run after: easy 20 min."
    return "Run after: tempo 30 min with 4 strides at the end."


def session_for(d: date) -> Session:
    """Full session for a given calendar date."""
    week = week_for(d)
    phase = phase_for(week)
    wd = d.weekday()

    if week == 0:
        return Session(0, 0, wd, "Plan hasn't started yet",
                       [f"Week 1 begins {config.PLAN_START.isoformat()} (Monday)."])
    if week == 99:
        return Session(99, 0, wd, "Plan complete 🎉",
                       ["The 24-week block is done. Time to set the next goal."])

    # Race week (24) overrides the normal layout: 5 km shakeout Tuesday, then
    # rest through to the Sunday half marathon.
    if week == 24:
        return _race_week_session(week, phase, wd)

    ma_int = martial_arts_intensity(week)
    maint = ("Phase 3: KB at maintenance — keep it light, protect for race prep."
             if phase == 3 else None)

    if wd == 0:  # Monday — KB strength
        return Session(week, phase, wd,
                       "KB Strength — 4-pattern EMOM (30 min)",
                       [
                           "EMOM, every 2 min cycle: Press → Row → Swing → Goblet Squat.",
                           "3 cycles total.",
                           "Core finisher: dead bug.",
                           "Presses 16–20kg · Rows/Swings 24–32kg · Goblet squat 20–24kg.",
                       ],
                       [progression_note(week),
                        "Dead bug = weekly core + bone-density stimulus."]
                       + ([maint] if maint else []))

    if wd in (1, 4):  # Tue / Fri — martial arts
        return Session(week, phase, wd,
                       "Martial Arts (45 min)",
                       [
                           "10 min movement prep.",
                           "25 min technique.",
                           "10 min mobility.",
                       ],
                       [f"Intensity this phase: {ma_int}."])

    if wd == 2:  # Wednesday — rest
        return Session(week, phase, wd, "Rest day",
                       ["Full rest. Eat, hydrate, sleep."])

    if wd == 3:  # Thursday — run
        summary, lines = _thursday_run(week)
        return Session(week, phase, wd, f"Run — {summary}", lines,
                       ["Easy pace = able to hold a conversation."])

    if wd == 5:  # Saturday — KB complex + run
        return Session(week, phase, wd,
                       "KB Complex + Run (50 min)",
                       [
                           "5 rounds: Swing → Clean → Push Press → Goblet Squat → "
                           "Row → Farmer Carry → Overhead Carry.",
                           "Rest 90 sec between rounds.",
                           _saturday_run(week),
                       ],
                       [progression_note(week),
                        "Farmer + overhead carries = key bone-density loading."]
                       + ([maint] if maint else []))

    # wd == 6 Sunday — active recovery
    return Session(week, phase, wd,
                   "Active Recovery",
                   [
                       "25 min easy walk.",
                       "15 min mobility (hip 90/90, pigeon, child's pose, "
                       "supine twist, doorframe chest, neck).",
                       "5 min 4-7-8 breathing.",
                   ],
                   ["Move gently — this is recovery, not training."])


def _race_week_session(week: int, phase: int, wd: int) -> Session:
    """Week 24: 5 km shakeout Tuesday, rest, then Sunday half marathon."""
    if wd == 1:  # Tuesday
        return Session(week, phase, wd, "Run — 5 km shakeout",
                       ["5 km very easy shakeout, then rest through to race day."],
                       ["Race week — stay fresh, nothing hard from here."])
    if wd == 6:  # Sunday — RACE DAY
        return Session(week, phase, wd, "🏁 RACE DAY — Half Marathon",
                       ["Trust the taper. Start easy, settle into rhythm, finish strong.",
                        "Hydrate, fuel, enjoy it — this is what the 24 weeks built to."],
                       ["Go get it. 🏃"])
    # Mon, Wed, Thu, Fri, Sat — rest / very light
    return Session(week, phase, wd, "Rest — race week",
                   ["Easy mobility and walking only. Legs fresh for Sunday."],
                   ["Race week taper — resist the urge to train."])


def week_sessions(week: int) -> list[Session]:
    """The seven sessions of a given plan week (Mon..Sun)."""
    if week < 1 or week > config.PLAN_WEEKS:
        return []
    monday = config.PLAN_START.fromordinal(
        config.PLAN_START.toordinal() + (week - 1) * 7)
    return [session_for(monday.fromordinal(monday.toordinal() + i))
            for i in range(7)]
