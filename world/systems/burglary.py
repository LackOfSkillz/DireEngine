import time

from evennia.utils import logger

from engine.services.skill_service import SkillService
from engine.services.state_service import StateService
from utils.contests import run_contest
from world.systems.theft import adjust_thief_reputation, increase_room_suspicion, trigger_justice_response


BURGLE_HEAT_DIFFICULTY_STEP = 5


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
    return 0


def _ensure_target_state(target):
    if target is None:
        return
    if target.db.burglary_enabled is None:
        target.db.burglary_enabled = False
    if target.db.lock_difficulty is None:
        target.db.lock_difficulty = 0
    if target.db.trap_difficulty is None:
        target.db.trap_difficulty = 0
    if target.db.entry_open is None:
        target.db.entry_open = False
    if target.db.last_burgled_at is None:
        target.db.last_burgled_at = 0
    if target.db.burgle_heat is None:
        target.db.burgle_heat = 0
    if target.db.burgle_heat_updated_at is None:
        target.db.burgle_heat_updated_at = 0


def _get_target_kind(target):
    if target is None:
        return "entry"
    explicit = str(target.db.burglary_kind or "").strip().lower()
    if explicit in {"entry", "container"}:
        return explicit
    if bool(target.db.is_container):
        return "container"
    return "entry"


def get_burgle_heat(target):
    if target is None:
        return 0
    _ensure_target_state(target)
    return int(target.db.burgle_heat or 0)


def add_burgle_heat(target, amount=1):
    if target is None:
        return 0
    _ensure_target_state(target)
    target.db.burgle_heat = max(0, int(target.db.burgle_heat or 0) + int(amount or 0))
    target.db.burgle_heat_updated_at = time.time()
    return int(target.db.burgle_heat or 0)


def decay_burgle_heat(target):
    if target is None:
        return 0
    _ensure_target_state(target)
    if not float(target.db.burgle_heat_updated_at or 0):
        target.db.burgle_heat_updated_at = time.time()
    return int(target.db.burgle_heat or 0)


def get_burgle_heat_penalty(target):
    return get_burgle_heat(target) * BURGLE_HEAT_DIFFICULTY_STEP


def can_burgle(actor, target):
    _ensure_target_state(target)
    result = {
        "allowed": False,
        "reason": None,
        "requires_lockpick": False,
        "requires_disarm": False,
    }
    if actor is None or target is None:
        result["reason"] = "There is nothing here to burgle."
        return result
    result["requires_lockpick"] = int(target.db.lock_difficulty or 0) > 0
    result["requires_disarm"] = int(target.db.trap_difficulty or 0) > 0
    if not bool(target.db.burglary_enabled):
        result["reason"] = "That is not a viable burglary target."
        return result
    if getattr(actor, "location", None) != getattr(target, "location", None):
        result["reason"] = "You need to be at the target to work it."
        return result
    if bool(target.db.entry_open):
        result["reason"] = "That entry has already been compromised."
        return result
    if result["requires_lockpick"] and hasattr(actor, "has_lockpick") and not actor.has_lockpick():
        result["reason"] = "You need a lockpick before you can try that."
        return result
    if bool(getattr(getattr(actor, "db", None), "guard_attention", False)):
        result["reason"] = "The law is already too interested in you for that stunt."
        return result
    result["allowed"] = True
    return result


def _run_locksmith_contest(actor, difficulty, stat="intelligence"):
    if actor is None:
        return {"diff": -100, "outcome": "fail"}
    if hasattr(actor, "locksmith_contest"):
        try:
            return actor.locksmith_contest(difficulty, stat=stat)
        except TypeError:
            return actor.locksmith_contest(difficulty)
    stats = dict(getattr(getattr(actor, "db", None), "stats", None) or {})
    total = _get_skill_rank(actor, "locksmithing") + int(stats.get(stat, 10) or 10)
    return run_contest(total, difficulty, attacker=actor)


def _apply_trap_consequence(actor, target, room):
    if actor is None:
        return
    trap_type = str(target.db.trap_type or "alarm")
    if hasattr(actor, "break_stealth"):
        actor.break_stealth()
    elif hasattr(actor, "reveal"):
        actor.reveal()
    if hasattr(actor, "apply_box_trap_effect"):
        actor.apply_box_trap_effect(trap_type)
    elif hasattr(actor, "set_hp"):
        current_hp = int(actor.db.hp or 0)
        StateService.apply_damage(actor, min(5, max(0, current_hp)), damage_type="impact")
    if room is not None:
        increase_room_suspicion(room, amount=2)


def _finalize_success(actor, target, room, result, difficulty_total):
    now = time.time()
    target.db.entry_open = True
    target.db.last_burgled_at = now
    add_burgle_heat(target, amount=1)
    if _get_target_kind(target) == "container":
        target.db.is_open = True
        target.db.opened = True
        result["entry_result"] = "container_open"
    else:
        destination = target.db.burglary_destination
        if destination is not None and hasattr(actor, "move_to"):
            actor.move_to(destination, quiet=True, move_type="burgle")
        result["entry_result"] = "entry_opened"
    if room is not None:
        increase_room_suspicion(room, amount=1)
    rep_delta = 2 if difficulty_total >= 35 else 1
    adjust_thief_reputation(actor, rep_delta)
    result["success"] = True
    return result


def _result_with_state(actor, target, result):
    return {
        **result,
        "burgle_heat": get_burgle_heat(target),
        "wanted_level": int(getattr(getattr(actor, "db", None), "wanted_level", 0) or 0),
        "guard_attention": bool(getattr(getattr(actor, "db", None), "guard_attention", False)),
        "thief_reputation": int(getattr(getattr(actor, "db", None), "thief_reputation", 0) or 0),
    }


def _award_burglary_movement_training(actor, difficulty_total, *, success):
    difficulty = max(10, int(difficulty_total or 0))
    outcome = "success" if success else "failure"
    SkillService.award_xp(actor, "stealth", difficulty, source={"mode": "difficulty"}, success=success, outcome=outcome, event_key="burglary")
    SkillService.award_xp(actor, "athletics", difficulty, source={"mode": "difficulty"}, success=success, outcome=outcome, event_key="burglary")


def attempt_entry(actor, target):
    validation = can_burgle(actor, target)
    if not validation.get("allowed"):
        return {
            "success": False,
            "caught": False,
            "lock_result": "blocked",
            "trap_result": "blocked",
            "entry_result": str(validation.get("reason") or "blocked"),
            "severity": 0,
        }

    _ensure_target_state(target)
    decay_burgle_heat(target)

    room = getattr(actor, "location", None)
    base_lock_difficulty = int(getattr(target.db, "lock_difficulty", 0) or 0)
    base_trap_difficulty = int(getattr(target.db, "trap_difficulty", 0) or 0)
    heat_penalty = get_burgle_heat_penalty(target)
    lock_difficulty = max(0, base_lock_difficulty + heat_penalty)
    trap_difficulty = max(0, base_trap_difficulty + heat_penalty)
    difficulty_total = base_lock_difficulty + base_trap_difficulty
    result = {
        "success": False,
        "caught": False,
        "lock_result": "skipped",
        "trap_result": "skipped",
        "entry_result": "blocked",
        "severity": 0,
    }

    roundtime = 3.0
    if lock_difficulty > 0:
        roundtime += 0.5
    if trap_difficulty > 0:
        roundtime += 0.5

    if trap_difficulty > 0:
        trap_contest = _run_locksmith_contest(actor, trap_difficulty)
        trap_diff = int(trap_contest.get("diff", 0) or 0)
        trap_outcome = str(trap_contest.get("outcome", "fail") or "fail")
        SkillService.award_xp(
            actor,
            "locksmithing",
            max(10, trap_difficulty),
            source={"mode": "difficulty"},
            success=trap_outcome != "fail",
            outcome=trap_outcome,
            event_key="trap_disarm",
        )
        if trap_diff <= -30:
            result["trap_result"] = "triggered"
            result["caught"] = True
            result["severity"] = 3
            result["entry_result"] = "trap_triggered"
            _award_burglary_movement_training(actor, difficulty_total or trap_difficulty, success=False)
            _apply_trap_consequence(actor, target, room)
            add_burgle_heat(target, amount=2)
            adjust_thief_reputation(actor, -3)
            trigger_justice_response(actor, target, action_type="burglary", severity=3)
            if hasattr(actor, "apply_thief_roundtime"):
                actor.apply_thief_roundtime(roundtime + 1.0)
            logger.log_info(f"[BURGLARY] actor={actor} target={target} trap=triggered severity=3")
            return _result_with_state(actor, target, result)
        if trap_outcome == "fail":
            result["trap_result"] = "noisy_failure"
            result["caught"] = True
            result["severity"] = 2
            result["entry_result"] = "trap_alerted"
            _award_burglary_movement_training(actor, difficulty_total or trap_difficulty, success=False)
            add_burgle_heat(target, amount=1)
            adjust_thief_reputation(actor, -2)
            if room is not None:
                increase_room_suspicion(room, amount=2)
            trigger_justice_response(actor, target, action_type="trespass", severity=2)
            if hasattr(actor, "apply_thief_roundtime"):
                actor.apply_thief_roundtime(roundtime)
            logger.log_info(f"[BURGLARY] actor={actor} target={target} trap=noisy_failure severity=2")
            return _result_with_state(actor, target, result)
        result["trap_result"] = "bypassed"

    if lock_difficulty > 0:
        lock_contest = _run_locksmith_contest(actor, lock_difficulty)
        lock_diff = int(lock_contest.get("diff", 0) or 0)
        lock_outcome = str(lock_contest.get("outcome", "fail") or "fail")
        SkillService.award_xp(
            actor,
            "locksmithing",
            max(10, lock_difficulty),
            source={"mode": "difficulty"},
            success=lock_outcome != "fail",
            outcome=lock_outcome,
            event_key="locksmithing",
        )
        if lock_diff <= -30:
            result["lock_result"] = "catastrophic_failure"
            result["caught"] = True
            result["severity"] = 2
            result["entry_result"] = "lock_alerted"
            _award_burglary_movement_training(actor, difficulty_total or lock_difficulty, success=False)
            add_burgle_heat(target, amount=2)
            adjust_thief_reputation(actor, -2)
            if room is not None:
                increase_room_suspicion(room, amount=2)
            trigger_justice_response(actor, target, action_type="burglary", severity=2)
            if hasattr(actor, "apply_thief_roundtime"):
                actor.apply_thief_roundtime(roundtime + 0.5)
            logger.log_info(f"[BURGLARY] actor={actor} target={target} lock=catastrophic severity=2")
            return _result_with_state(actor, target, result)
        if lock_outcome == "fail":
            result["lock_result"] = "no_progress"
            result["entry_result"] = "blocked"
            add_burgle_heat(target, amount=1)
            adjust_thief_reputation(actor, -1)
            if room is not None:
                increase_room_suspicion(room, amount=1)
            if hasattr(actor, "apply_thief_roundtime"):
                actor.apply_thief_roundtime(roundtime)
            logger.log_info(f"[BURGLARY] actor={actor} target={target} lock=no_progress")
            return _result_with_state(actor, target, result)
        if lock_outcome == "partial":
            result["lock_result"] = "noisy_failure"
            result["caught"] = True
            result["severity"] = 1
            result["entry_result"] = "noisy_failure"
            _award_burglary_movement_training(actor, difficulty_total or lock_difficulty, success=False)
            add_burgle_heat(target, amount=1)
            adjust_thief_reputation(actor, -1)
            if room is not None:
                increase_room_suspicion(room, amount=1)
            trigger_justice_response(actor, target, action_type="trespass", severity=1)
            if hasattr(actor, "apply_thief_roundtime"):
                actor.apply_thief_roundtime(roundtime)
            logger.log_info(f"[BURGLARY] actor={actor} target={target} lock=noisy_failure severity=1")
            return _result_with_state(actor, target, result)
        result["lock_result"] = "opened"

    result = _finalize_success(actor, target, room, result, difficulty_total)
    _award_burglary_movement_training(actor, difficulty_total, success=True)
    if hasattr(actor, "apply_thief_roundtime"):
        actor.apply_thief_roundtime(roundtime)
    logger.log_info(f"[BURGLARY] actor={actor} target={target} success=True heat={get_burgle_heat(target)}")
    return _result_with_state(actor, target, result)