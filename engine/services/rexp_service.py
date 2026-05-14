"""Rested Experience (REXP) banking, consumption, and offline drain helpers."""

from __future__ import annotations

import time

REXP_CAP_SECONDS = 14400
REXP_BANKING_RATIO = 2.0
REXP_IDLE_THRESHOLD_SECONDS = 300
REXP_CYCLE_DURATION_SECONDS = 23.5 * 3600
REXP_CONSUMPTION_PER_GROUP_PULSE = 20
REXP_DRAIN_MULTIPLIER = 3.0
STATIC_OFFLINE_DRAIN_BITS_PER_SECOND = 1.0
SLEEP_XP_BLOCK_NOTIFICATION_WINDOW_SECONDS = 300


def _now(now=None):
    return float(now if now is not None else time.time())


def ensure_rexp_defaults(character, now=None):
    db = getattr(character, "db", None)
    if db is None:
        return
    if hasattr(character, "ensure_sleep_defaults"):
        character.ensure_sleep_defaults()
        return
    current_time = _now(now)
    if getattr(db, "sleep_state", None) is None:
        db.sleep_state = "awake"
    if getattr(db, "rexp_banked_seconds", None) is None:
        db.rexp_banked_seconds = 0
    if getattr(db, "rexp_cycle_start", None) is None:
        db.rexp_cycle_start = current_time
    if getattr(db, "rexp_used_this_cycle_seconds", None) is None:
        db.rexp_used_this_cycle_seconds = 0
    if getattr(db, "rexp_last_active_check", None) is None:
        db.rexp_last_active_check = current_time
    if getattr(db, "rexp_last_offline", None) is None:
        db.rexp_last_offline = None


def is_character_idle(character):
    ensure_rexp_defaults(character)
    if hasattr(character, "is_in_deep_sleep") and character.is_in_deep_sleep():
        return True
    skill_store = getattr(getattr(character, "db", None), "exp_skill_state", None) or {}
    for state in skill_store.values():
        if float((state or {}).get("pool", 0.0) or 0.0) > 0.0:
            return False
    return True


def update_rexp_banking(character, now=None):
    ensure_rexp_defaults(character, now=now)
    current_time = _now(now)
    raw_last_check = getattr(character.db, "rexp_last_active_check", None)
    last_check = current_time if raw_last_check is None else float(raw_last_check)

    if not is_character_idle(character):
        character.db.rexp_last_active_check = current_time
        return 0

    idle_duration = current_time - last_check
    if idle_duration < REXP_IDLE_THRESHOLD_SECONDS:
        return 0

    bankable_seconds = max(0.0, idle_duration - REXP_IDLE_THRESHOLD_SECONDS)
    rexp_to_bank = int(bankable_seconds / REXP_BANKING_RATIO)
    if rexp_to_bank <= 0:
        return 0

    current_bank = int(getattr(character.db, "rexp_banked_seconds", 0) or 0)
    new_bank = min(REXP_CAP_SECONDS, current_bank + rexp_to_bank)
    character.db.rexp_banked_seconds = new_bank
    character.db.rexp_last_active_check = current_time - REXP_IDLE_THRESHOLD_SECONDS
    return max(0, new_bank - current_bank)


def can_consume_rexp(character, now=None):
    ensure_rexp_defaults(character, now=now)
    if getattr(character, "db", None) is None:
        return False
    current_time = _now(now)
    bank = int(getattr(character.db, "rexp_banked_seconds", 0) or 0)
    if bank <= 0:
        return False

    raw_cycle_start = getattr(character.db, "rexp_cycle_start", None)
    cycle_start = current_time if raw_cycle_start is None else float(raw_cycle_start)
    if current_time - cycle_start > REXP_CYCLE_DURATION_SECONDS:
        character.db.rexp_cycle_start = current_time
        character.db.rexp_used_this_cycle_seconds = 0

    used = int(getattr(character.db, "rexp_used_this_cycle_seconds", 0) or 0)
    return used < REXP_CAP_SECONDS


def consume_rexp_for_group_pulse(character, group_drained, now=None):
    ensure_rexp_defaults(character, now=now)
    if getattr(character, "db", None) is None:
        return False
    if not group_drained or not can_consume_rexp(character, now=now):
        return False

    bank = int(getattr(character.db, "rexp_banked_seconds", 0) or 0)
    used = int(getattr(character.db, "rexp_used_this_cycle_seconds", 0) or 0)
    consumed = min(REXP_CONSUMPTION_PER_GROUP_PULSE, bank, REXP_CAP_SECONDS - used)
    if consumed <= 0:
        return False
    character.db.rexp_banked_seconds = bank - consumed
    character.db.rexp_used_this_cycle_seconds = used + consumed
    return True


def notify_sleep_blocks_xp(character, now=None):
    if character is None:
        return False
    current_time = _now(now)
    notifications = getattr(getattr(character, "ndb", None), "sleep_xp_block_notifications", None) or {}
    last_notification = float(notifications.get("sleep_xp", 0.0) or 0.0)
    if current_time - last_notification < SLEEP_XP_BLOCK_NOTIFICATION_WINDOW_SECONDS:
        return False
    notifications = dict(notifications)
    notifications["sleep_xp"] = current_time
    character.ndb.sleep_xp_block_notifications = notifications
    from engine.services.messaging import send_untargeted_action

    send_untargeted_action(actor=character, actor_message="You cannot absorb new experience while resting.")
    return True


def _iter_skill_names(character):
    store = getattr(getattr(character, "db", None), "exp_skill_state", None) or {}
    return [str(name or "").strip().lower() for name in store.keys() if str(name or "").strip()]


def apply_offline_drain(character, now=None):
    ensure_rexp_defaults(character, now=now)
    last_offline = getattr(character.db, "rexp_last_offline", None)
    if last_offline is None:
        return 0
    current_time = _now(now)
    offline_duration = max(0.0, current_time - float(last_offline))
    if offline_duration <= 0.0:
        character.db.rexp_last_offline = None
        return 0

    drained_total = _apply_static_offline_drain(character, offline_duration)
    if offline_duration > REXP_IDLE_THRESHOLD_SECONDS:
        bankable = offline_duration - REXP_IDLE_THRESHOLD_SECONDS
        rexp_gained = int(bankable / REXP_BANKING_RATIO)
        current_bank = int(getattr(character.db, "rexp_banked_seconds", 0) or 0)
        character.db.rexp_banked_seconds = min(REXP_CAP_SECONDS, current_bank + rexp_gained)

    character.db.rexp_last_offline = None
    character.db.rexp_last_active_check = current_time
    return drained_total


def _apply_static_offline_drain(character, offline_seconds):
    drained_total = 0
    drain_amount_per_skill = max(0.0, float(offline_seconds or 0.0) * STATIC_OFFLINE_DRAIN_BITS_PER_SECOND)
    if drain_amount_per_skill <= 0.0:
        return 0
    for skill_id in _iter_skill_names(character):
        skill = character._sync_exp_skill_state(skill_id)
        current_pool = float(getattr(skill, "pool", 0.0) or 0.0)
        if current_pool <= 0.0:
            continue
        drained = min(drain_amount_per_skill, current_pool)
        skill.pool = max(0.0, current_pool - drained)
        skill.rank_progress = max(0.0, float(getattr(skill, "rank_progress", 0.0) or 0.0) + drained)
        skill.recalc_pool()
        from world.systems.skills import process_rank, persist_skill_state

        process_rank(skill)
        persist_skill_state(skill)
        drained_total += drained
    return int(round(drained_total))


def get_rexp_display(character, now=None):
    ensure_rexp_defaults(character, now=now)
    current_time = _now(now)
    raw_cycle_start = getattr(character.db, "rexp_cycle_start", None)
    cycle_start = current_time if raw_cycle_start is None else float(raw_cycle_start)
    if current_time - cycle_start > REXP_CYCLE_DURATION_SECONDS:
        character.db.rexp_cycle_start = current_time
        character.db.rexp_used_this_cycle_seconds = 0
        cycle_start = current_time
    bank_sec = int(getattr(character.db, "rexp_banked_seconds", 0) or 0)
    used_sec = int(getattr(character.db, "rexp_used_this_cycle_seconds", 0) or 0)
    usable_sec = max(0, min(bank_sec, REXP_CAP_SECONDS - used_sec))
    cycle_remaining = max(0.0, REXP_CYCLE_DURATION_SECONDS - (current_time - cycle_start))
    return {
        "banked": _format_hours_minutes(bank_sec),
        "usable_this_cycle": _format_hours_minutes(usable_sec),
        "cycle_refreshes_in": _format_hours_minutes(cycle_remaining),
        "sleep_state": str(getattr(character.db, "sleep_state", "awake") or "awake").replace("_", " ").title(),
    }


def _format_hours_minutes(seconds):
    total_minutes = int(max(0.0, float(seconds or 0.0)) // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}:{minutes:02d} hours"
