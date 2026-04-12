import random
import time


MARK_BONUS = 10
MARK_WINDOW_SECONDS = 60.0
OBSERVE_WINDOW_SECONDS = 60.0


def _get_skill_rank(character, skill_name):
    if character is None:
        return 0

    if hasattr(character, "get_skill_rank"):
        try:
            return int(character.get_skill_rank(skill_name) or 0)
        except Exception:
            return 0

    if hasattr(character, "get_skill"):
        try:
            return int(character.get_skill(skill_name) or 0)
        except Exception:
            return 0

    skills = getattr(character, "skills", None)
    if skills and hasattr(skills, "get"):
        try:
            skill = skills.get(skill_name, None)
        except TypeError:
            skill = skills.get(skill_name)
        if skill is not None and hasattr(skill, "rank"):
            return int(getattr(skill, "rank", 0) or 0)

    db_skills = getattr(getattr(character, "db", None), "skills", None) or {}
    if isinstance(db_skills, dict):
        entry = db_skills.get(skill_name, {})
        if isinstance(entry, dict):
            return int(entry.get("rank", 0) or 0)
    return 0


def get_mark_bonus(actor, target, context=None):
    if actor is None or target is None:
        return 0

    context = dict(context or {})
    now = float(context.get("now", time.time()) or time.time())
    target_id = getattr(target, "id", None)
    if target_id is None:
        return 0

    last_target = getattr(getattr(actor, "db", None), "last_mark_target", None)
    last_time = float(getattr(getattr(actor, "db", None), "last_mark_time", 0) or 0)
    if last_target == target_id and (now - last_time) <= MARK_WINDOW_SECONDS:
        return MARK_BONUS

    marked_target = getattr(getattr(actor, "db", None), "marked_target", None)
    mark_data = dict(getattr(getattr(actor, "db", None), "mark_data", None) or {})
    mark_time = float(mark_data.get("timestamp", 0) or 0)
    if marked_target == target_id and (now - mark_time) <= MARK_WINDOW_SECONDS:
        return MARK_BONUS

    return 0


def get_awareness_total(observer, actor=None, context=None):
    context = dict(context or {})
    base = _get_skill_rank(observer, "perception")
    modifier = 0

    if hasattr(observer, "get_awareness_bonus"):
        try:
            modifier += int(observer.get_awareness_bonus() or 0)
        except Exception:
            modifier += 0

    awareness_state = dict(getattr(getattr(observer, "db", None), "awareness_state", None) or {})
    modifier += int(awareness_state.get("suspicion_bonus", 0) or 0)

    actor_modifiers = dict(awareness_state.get("actor_modifiers") or {})
    actor_key = str(getattr(actor, "id", "")) if actor is not None else ""
    if actor_key:
        modifier += int(actor_modifiers.get(actor_key, 0) or 0)

    if actor is not None and hasattr(observer, "get_suspicion_for"):
        try:
            modifier += int(observer.get_suspicion_for(actor) or 0)
        except Exception:
            modifier += 0

    theft_log = dict(getattr(getattr(observer, "db", None), "theft_attempt_log", None) or {})
    recent_suspicion = dict(theft_log.get("recent_suspicion") or {})
    if actor_key:
        modifier += int(recent_suspicion.get(actor_key, 0) or 0)

    room = context.get("room") or getattr(observer, "location", None)
    if room is not None:
        modifier += int(getattr(getattr(room, "db", None), "suspicion_level", 0) or 0)

    observe_target = context.get("observe_target")
    if observe_target is not None:
        observe_target_id = getattr(observe_target, "id", observe_target)
        actor_id = getattr(actor, "id", None) if actor is not None else None
        if observe_target_id == actor_id:
            modifier += 30

    modifier += int(context.get("awareness_bonus", 0) or 0)
    return int(base + modifier)


def record_observe_attempt(actor, target, now=None):
    if actor is None or target is None:
        return 0

    now = float(now or time.time())
    theft_log = dict(getattr(getattr(target, "db", None), "theft_attempt_log", None) or {})
    observe_history = dict(theft_log.get("observe_history") or {})
    actor_key = str(getattr(actor, "id", "unknown") or "unknown")
    entry = dict(observe_history.get(actor_key) or {"count": 0, "last_observe_at": 0})
    if now - float(entry.get("last_observe_at", 0) or 0) > OBSERVE_WINDOW_SECONDS:
        entry["count"] = 0
    entry["count"] = int(entry.get("count", 0) or 0) + 1
    entry["last_observe_at"] = now
    observe_history[actor_key] = entry
    theft_log["observe_history"] = observe_history
    target.db.theft_attempt_log = theft_log

    if entry["count"] >= 2:
        awareness_state = dict(getattr(target.db, "awareness_state", None) or {})
        actor_modifiers = dict(awareness_state.get("actor_modifiers") or {})
        actor_modifiers[actor_key] = int(actor_modifiers.get(actor_key, 0) or 0) + 5
        awareness_state["actor_modifiers"] = actor_modifiers
        awareness_state["suspicion_bonus"] = int(awareness_state.get("suspicion_bonus", 0) or 0) + 2
        target.db.awareness_state = awareness_state
        if hasattr(target, "adjust_suspicion_for"):
            target.adjust_suspicion_for(actor, 1)

    return int(entry["count"])


def resolve_awareness_contest(actor, observer, action_type, context=None):
    context = dict(context or {})
    actor_total = int(context.get("actor_total", 0) or 0)
    if actor_total <= 0:
        actor_total = _get_skill_rank(actor, "thievery")
        if action_type in {"steal", "shoplift", "pickpocket"}:
            actor_total += get_mark_bonus(actor, observer, context=context)

    observer_total = get_awareness_total(observer, actor=actor, context=context)
    actor_roll = actor_total + random.randint(1, 100)
    observer_roll = observer_total + random.randint(1, 100)
    margin = actor_roll - observer_roll
    return {
        "success": margin > 0,
        "actor_total": int(actor_roll),
        "observer_total": int(observer_roll),
        "margin": int(margin),
    }