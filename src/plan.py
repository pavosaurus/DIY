"""Deterministic 24-week training plan logic.

Source of truth for content is data/exercise_master_prompt.md; this module
encodes the schedule so that, for any date, we can compute the exact session
without calling an LLM.

Output contract (per the master prompt): every training session exposes three
figures via Session.metrics — exact weights in kg, exact reps/rounds, and
running/walking speeds in km/hr. Non-applicable figures are shown as "—".

Acceleration: the athlete found Weeks 1–2 easy, so progression is advanced one
step. This is implemented by offsetting the progression index by
ACCEL_STEP weeks from ACCEL_FROM onward (see effective_prog_week).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import config

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

# --- Acceleration -----------------------------------------------------------
# The athlete found Weeks 1–2 easy and asked to "skip ahead one progression
# step" for the upcoming week (Week 3): KB -> increase one bell size, run ->
# the Weeks 3–4 structure. This week-indexed model ALREADY advances every week,
# so Week 3 natively lands on exactly those targets — no artificial offset is
# applied (an offset would push Week 3 into a deload, the opposite of intent).
# Keep at 0 unless you want to genuinely compress the timeline.
ACCEL_FROM = 3
ACCEL_STEP = 0

# --- Kettlebell loading -----------------------------------------------------
BELL_SIZES = [12, 16, 20, 24, 28, 32]  # kg available

# Baseline (low end of each master-prompt range) per movement group.
KB_BASE = {
    "heavy": 24,   # swings, rows, farmer carry      (24–32)
    "squat": 20,   # goblet squat, front squat       (20–24)
    "press": 16,   # press, clean, push press         (16–20)
    "ohc": 12,     # overhead carry                   (12–16)
}
KB_MAX = {"heavy": 32, "squat": 24, "press": 20, "ohc": 16}

# Monday EMOM baseline reps per movement (per cycle, 3 cycles).
MON_BASE_REPS = {"Press": 6, "Row": 8, "Swing": 12, "Goblet squat": 8}


@dataclass
class Session:
    week: int                 # 1..24, or 0 = before plan, 99 = after plan
    phase: int                # 1, 2, 3 (0 if outside plan)
    weekday: int              # 0=Mon .. 6=Sun
    title: str
    details: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Required output figures; "—" when not applicable.
    metrics: dict = field(default_factory=lambda: {"weights": "—", "reps": "—", "speed": "—"})

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


def effective_prog_week(week: int) -> int:
    """Week used for progression maths, advanced once acceleration kicks in."""
    if week >= ACCEL_FROM:
        return week + ACCEL_STEP
    return week


def cycle_week(week: int) -> int:
    """Position in the repeating 4-week progression block (1..4)."""
    return (effective_prog_week(week) - 1) % 4 + 1


def progression_note(week: int) -> str:
    cw = cycle_week(week)
    base = {
        1: "Block week 1 — establish form, baseline weight.",
        2: "Block week 2 — add 1 rep per exercise vs last week.",
        3: "Block week 3 — increase one bell size where form allows.",
        4: "Block week 4 — DELOAD. Drop back to block week-1 weight.",
    }[cw]
    if week == ACCEL_FROM and cw == 3:
        base += " (Steps up from Weeks 1–2 — train at the top of each range if it feels easy.)"
    return base


def martial_arts_intensity(week: int) -> str:
    return {1: "low", 2: "moderate", 3: "low"}[phase_for(week)]


# --- weight helpers ---------------------------------------------------------
def _step_bell(base: int, steps: int, cap: int) -> int:
    """Move `steps` standard bell sizes up from base, capped at cap."""
    idx = BELL_SIZES.index(base)
    idx = min(idx + steps, BELL_SIZES.index(cap))
    return BELL_SIZES[idx]


def kb_weight(group: str, week: int) -> int:
    """Exact working kg for a movement group in a given week."""
    base = KB_BASE[group]
    cap = KB_MAX[group]
    phase = phase_for(week)
    if phase == 3:
        return base  # Phase 3: KB at maintenance, baseline load.
    cw = cycle_week(week)
    # +1 bell on block week 3 (and carried as the working load); deload/others baseline.
    steps = 1 if cw == 3 else 0
    # Phase 2 protects joints: cap one size below max.
    if phase == 2:
        cap = _step_bell(base, 1, cap)
    return _step_bell(base, steps, cap)


def _mon_reps(week: int) -> dict:
    cw = cycle_week(week)
    add = 1 if cw == 2 else 0  # block week 2 adds a rep
    return {k: v + add for k, v in MON_BASE_REPS.items()}


# --- run speed / structure helpers ------------------------------------------
def _thursday_run(week: int):
    """Return (title_summary, detail_lines, speed_str)."""
    phase = phase_for(week)
    pw = effective_prog_week(week)  # accelerated for Phase 1 structure
    if phase == 1:
        # Structure keyed to the accelerated progression week.
        if pw <= 2:
            return ("Walk/run intervals",
                    ["Walk 2 min / run 1 min x8 (start with the walk)."],
                    "walk 5.5 / run 8.0 km/hr")
        if pw <= 4:
            return ("Walk/run intervals",
                    ["Walk 1 min / run 2 min x8."],
                    "walk 5.5 / run 8.0 km/hr")
        if pw <= 6:
            return ("Walk/run intervals",
                    ["Walk 1 min / run 5 min x4."],
                    "walk 5.5 / run 8.5 km/hr")
        return ("Walk/run intervals",
                ["Walk 1 min / run 10 min x3."],
                "walk 5.5 / run 8.5 km/hr")
    if phase == 2:
        km = 5 + (week - 9)  # 5km wk9 .. 12km wk16
        lines = [f"{km} km easy, conversational pace."]
        lines.append("Finish with 4 x strides (turnover / bone-density stimulus).")
        return (f"{km} km easy run", lines, "easy 8.5 / strides ~14 km/hr")
    # Phase 3
    if week <= 22:
        targets = {17: 13, 18: 14.5, 19: 16, 20: 17, 21: 18.5, 22: 20}
        km = targets[week]
        return (f"{km:g} km long run",
                [f"{km:g} km easy/long run.", "Finish with 4 x strides."],
                "easy 9.0 / strides ~14 km/hr")
    if week == 23:
        return ("10 km taper run", ["10 km easy — taper week, stay fresh."],
                "easy 9.0 km/hr")
    return ("Race week", [
        "Tuesday: 5 km easy shakeout, then rest through to race day.",
        "SUNDAY: HALF MARATHON — race day! Trust the taper.",
    ], "shakeout 9.0 / race ~9.5 km/hr")


def _saturday_run(week: int):
    """Return (detail_line, speed_str)."""
    phase = phase_for(week)
    if phase == 1:
        return ("Run after: easy 10 min (or Japanese interval walk).",
                "easy 8.0 km/hr (or walk 6.5/4.5)")
    if phase == 2:
        return ("Run after: easy 20 min.", "easy 8.5 km/hr")
    return ("Run after: tempo 30 min with 4 strides at the end.",
            "tempo 10.5 / strides ~14 km/hr")


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

    if week == 24:
        return _race_week_session(week, phase, wd)

    ma_int = martial_arts_intensity(week)
    maint = ("Phase 3: KB at maintenance — keep it light, protect for race prep."
             if phase == 3 else None)

    if wd == 0:  # Monday — KB strength
        h, s, p, o = (kb_weight("heavy", week), kb_weight("squat", week),
                      kb_weight("press", week), kb_weight("ohc", week))
        reps = _mon_reps(week)
        weights_str = f"Swing/Row {h}kg, Goblet squat {s}kg, Press {p}kg"
        reps_str = (f"3 cycles × (Press {reps['Press']}, Row {reps['Row']}/side, "
                    f"Swing {reps['Swing']}, Goblet squat {reps['Goblet squat']})")
        return Session(week, phase, wd,
                       "KB Strength — 4-pattern EMOM (30 min)",
                       [
                           "EMOM, every 2 min cycle: Press → Row → Swing → Goblet Squat.",
                           f"Weights: {weights_str}.",
                           f"Reps: {reps_str}.",
                           "Core finisher: dead bug (2 × 10/side).",
                       ],
                       [progression_note(week),
                        "Dead bug = weekly core + trunk stability."]
                       + ([maint] if maint else []),
                       {"weights": weights_str, "reps": reps_str, "speed": "—"})

    if wd in (1, 4):  # Tue / Fri — martial arts
        return Session(week, phase, wd,
                       "Martial Arts (45 min)",
                       ["10 min movement prep.", "25 min technique.", "10 min mobility."],
                       [f"Intensity this phase: {ma_int}."],
                       {"weights": "—", "reps": "45 min (10 prep / 25 technique / 10 mobility)",
                        "speed": "—"})

    if wd == 2:  # Wednesday — rest
        return Session(week, phase, wd, "Rest day",
                       ["Full rest. Eat, hydrate, sleep."],
                       [], {"weights": "—", "reps": "—", "speed": "—"})

    if wd == 3:  # Thursday — run
        summary, lines, speed = _thursday_run(week)
        reps_str = lines[0]
        return Session(week, phase, wd, f"Run — {summary}", lines + [f"Pace: {speed}."],
                       ["Easy pace = able to hold a conversation."],
                       {"weights": "—", "reps": reps_str, "speed": speed})

    if wd == 5:  # Saturday — KB complex + run
        h, s, p, o = (kb_weight("heavy", week), kb_weight("squat", week),
                      kb_weight("press", week), kb_weight("ohc", week))
        run_line, run_speed = _saturday_run(week)
        weights_str = (f"Swing/Row/Farmer {h}kg, Goblet {s}kg, "
                       f"Clean/Push press {p}kg, Overhead carry {o}kg")
        reps_str = "5 rounds × 5 reps each (carries ~20 m), 90s rest between rounds"
        return Session(week, phase, wd,
                       "KB Complex + Run (50 min)",
                       [
                           "5 rounds: Swing → Clean → Push Press → Goblet Squat → "
                           "Row → Farmer Carry → Overhead Carry.",
                           f"Weights: {weights_str}.",
                           f"Reps: {reps_str}.",
                           run_line + f" Pace: {run_speed}.",
                       ],
                       [progression_note(week),
                        "Farmer + overhead carries = key bone-density loading."]
                       + ([maint] if maint else []),
                       {"weights": weights_str, "reps": reps_str, "speed": run_speed})

    # wd == 6 Sunday — active recovery
    return Session(week, phase, wd,
                   "Active Recovery",
                   [
                       "25 min easy walk.",
                       "15 min mobility (hip 90/90, pigeon, child's pose, "
                       "supine twist, doorframe chest, neck).",
                       "5 min 4-7-8 breathing.",
                   ],
                   ["Move gently — this is recovery, not training."],
                   {"weights": "—", "reps": "25 min walk + 15 min mobility",
                    "speed": "walk ~5.5 km/hr"})


def _race_week_session(week: int, phase: int, wd: int) -> Session:
    """Week 24: 5 km shakeout Tuesday, rest, then Sunday half marathon."""
    if wd == 1:  # Tuesday
        return Session(week, phase, wd, "Run — 5 km shakeout",
                       ["5 km very easy shakeout, then rest through to race day."],
                       ["Race week — stay fresh, nothing hard from here."],
                       {"weights": "—", "reps": "5 km easy", "speed": "easy 9.0 km/hr"})
    if wd == 6:  # Sunday — RACE DAY
        return Session(week, phase, wd, "🏁 RACE DAY — Half Marathon",
                       ["21.1 km. Trust the taper. Start easy, settle in, finish strong.",
                        "Hydrate, fuel, enjoy it — this is what the 24 weeks built to."],
                       ["Go get it. 🏃"],
                       {"weights": "—", "reps": "21.1 km", "speed": "target ~9.5 km/hr"})
    return Session(week, phase, wd, "Rest — race week",
                   ["Easy mobility and walking only. Legs fresh for Sunday."],
                   ["Race week taper — resist the urge to train."],
                   {"weights": "—", "reps": "rest / easy walk", "speed": "walk ~5.5 km/hr"})


def week_sessions(week: int) -> list[Session]:
    """The seven sessions of a given plan week (Mon..Sun)."""
    if week < 1 or week > config.PLAN_WEEKS:
        return []
    monday = config.PLAN_START.fromordinal(
        config.PLAN_START.toordinal() + (week - 1) * 7)
    return [session_for(monday.fromordinal(monday.toordinal() + i))
            for i in range(7)]
