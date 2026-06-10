"""Boundary tests for the deterministic plan logic.

Anchors on PLAN_START = 2026-06-01 (Monday). Run with: python -m pytest
"""

from datetime import date, timedelta

from src import config, plan


def d(week: int, weekday: int) -> date:
    """Date for a given plan week (1-based) and weekday (0=Mon)."""
    return config.PLAN_START + timedelta(days=(week - 1) * 7 + weekday)


def test_anchor_is_monday_week_one():
    assert config.PLAN_START.weekday() == 0
    assert plan.week_for(config.PLAN_START) == 1


def test_week_numbering_and_bounds():
    assert plan.week_for(config.PLAN_START - timedelta(days=1)) == 0   # before start
    assert plan.week_for(d(2, 2)) == 2                                 # Wed of week 2
    assert plan.week_for(d(24, 6)) == 24                               # last day
    assert plan.week_for(d(24, 6) + timedelta(days=1)) == 99           # after plan


def test_phase_boundaries():
    assert plan.phase_for(8) == 1
    assert plan.phase_for(9) == 2
    assert plan.phase_for(16) == 2
    assert plan.phase_for(17) == 3
    assert plan.phase_for(24) == 3


def test_progression_cycle_deload():
    assert plan.cycle_week(1) == 1
    assert plan.cycle_week(4) == 4
    assert plan.cycle_week(5) == 1
    assert "DELOAD" in plan.progression_note(4)
    assert "DELOAD" in plan.progression_note(8)


def test_weekly_layout():
    assert plan.session_for(d(2, 0)).title.startswith("KB Strength")     # Mon
    assert "Martial Arts" in plan.session_for(d(2, 1)).title             # Tue
    assert plan.session_for(d(2, 2)).title == "Rest day"                 # Wed
    assert plan.session_for(d(2, 3)).title.startswith("Run")            # Thu
    assert "Martial Arts" in plan.session_for(d(2, 4)).title             # Fri
    assert "KB Complex" in plan.session_for(d(2, 5)).title               # Sat
    assert "Active Recovery" in plan.session_for(d(2, 6)).title          # Sun


def test_phase2_run_distance():
    # Week 9 = 5km, +1km/week to week 16 = 12km.
    assert "5 km" in plan.session_for(d(9, 3)).title
    assert "12 km" in plan.session_for(d(16, 3)).title


def test_race_week_overrides():
    # Tuesday shakeout, Sunday race, other days rest.
    assert "5 km shakeout" in plan.session_for(d(24, 1)).title
    assert "RACE DAY" in plan.session_for(d(24, 6)).title
    assert plan.session_for(d(24, 0)).title.startswith("Rest")
    # Sunday of race week must NOT be active recovery.
    assert "Active Recovery" not in plan.session_for(d(24, 6)).title


def test_weekly_summary_rollover():
    from src import exercise
    # On Sunday of week 1, preview week 2.
    assert "Week 2/24" in exercise.weekly_summary(d(1, 6))
    # On Sunday of week 22, preview week 23 (taper flag).
    assert "TAPER" in exercise.weekly_summary(d(22, 6))
    # On Sunday of week 23, preview week 24 (race week flag).
    assert "RACE WEEK" in exercise.weekly_summary(d(23, 6))
    # On Sunday of week 24, no "next week" — terminal message.
    assert "final week" in exercise.weekly_summary(d(24, 6)).lower()
