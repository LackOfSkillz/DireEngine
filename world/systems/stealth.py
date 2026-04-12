import random

from evennia.utils import logger

from engine.services.skill_service import SkillService


def _get_skill_rank(character, skill_name):
    if character is None:
        return None

    if hasattr(character, "get_skill_rank"):
        try:
            return int(character.get_skill_rank(skill_name) or 0)
        except Exception:
            return None

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

    return None


def _is_hidden(target):
    if not target:
        return False
    if hasattr(target, "is_hidden"):
        try:
            return bool(target.is_hidden())
        except Exception:
            pass
    return bool(getattr(getattr(target, "db", None), "stealthed", False))


def sync_stealth_cache(character):
    if character is None:
        return False

    authoritative_hidden = False
    if hasattr(character, "has_state"):
        try:
            authoritative_hidden = bool(character.has_state("hidden"))
        except Exception:
            authoritative_hidden = False

    mirrored_hidden = bool(getattr(getattr(character, "db", None), "stealthed", False))
    if mirrored_hidden != authoritative_hidden:
        logger.log_err(
            f"[STEALTH_SYNC] hidden-state mismatch for {character}: db.stealthed={mirrored_hidden} authoritative={authoritative_hidden}"
        )
        character.db.stealthed = authoritative_hidden

    if not authoritative_hidden and int(getattr(getattr(character, "db", None), "stealth_value", 0) or 0) != 0:
        character.db.stealth_value = 0

    return authoritative_hidden


def _set_hidden_state(character, stealth_score):
    if hasattr(character, "set_state"):
        current = character.get_state("hidden") if hasattr(character, "get_state") else {}
        if not isinstance(current, dict):
            current = {}
        current["strength"] = max(0, int(stealth_score or 0))
        current["source"] = "hide"
        character.set_state("hidden", current)


def enter_stealth(character):
    skill_rank = _get_skill_rank(character, "stealth")
    if skill_rank is None:
        return False

    roll = random.randint(1, 100)
    stealth_score = int(skill_rank) + roll

    if stealth_score < 20:
        break_stealth(character)
        logger.log_info(f"[STEALTH] {character} score={stealth_score} result=failure")
        return False

    character.db.stealthed = True
    character.db.stealth_value = stealth_score
    _set_hidden_state(character, stealth_score)
    sync_stealth_cache(character)
    logger.log_info(f"[STEALTH] {character} score={stealth_score} result=success")
    return stealth_score


def break_stealth(character):
    if character is None:
        return

    character.db.stealthed = False
    character.db.stealth_value = 0
    if hasattr(character, "clear_state"):
        for state_key in ("hidden", "sneaking", "stalking", "ambush_target"):
            character.clear_state(state_key)
    if getattr(getattr(character, "db", None), "position_state", "neutral") == "advantaged":
        character.db.position_state = "neutral"
    sync_stealth_cache(character)


def resolve_detection(observer, target, award_xp=False, active=False, context=None):
    context = dict(context or {})
    if not _is_hidden(target):
        return {
            "success": True,
            "margin": 999,
            "detect_score": 0,
            "stealth_score": 0,
            "hint": "visible",
        }

    sync_stealth_cache(target)

    skill_rank = _get_skill_rank(observer, "perception")
    if skill_rank is None:
        return {
            "success": False,
            "margin": -999,
            "detect_score": 0,
            "stealth_score": int(getattr(getattr(target, "db", None), "stealth_value", 0) or 0),
            "hint": "none",
        }

    perception_bonus = int(context.get("perception_bonus", 0) or 0)
    if active:
        perception_bonus += 20

    roll = random.randint(1, 100)
    detect_score = int(skill_rank) + perception_bonus + roll
    stealth_value = int(getattr(getattr(target, "db", None), "stealth_value", 0) or 0)
    if stealth_value <= 0 and hasattr(target, "get_stealth_total"):
        stealth_value = int(target.get_stealth_total() or 0)
        if hasattr(target, "get_hidden_strength"):
            stealth_value += int(target.get_hidden_strength() or 0)

    margin = int(detect_score - stealth_value)
    result = margin >= 0
    if result and award_xp:
        SkillService.award_xp(observer, "perception", 1, source={"mode": "difficulty"}, success=True, outcome="success", event_key="perception")

    hint = "none"
    if result and margin >= 20:
        hint = "reveal"
    elif result or (active and margin >= -10):
        hint = "hint"

    logger.log_info(
        f"[DETECT] {observer} vs {target} result={result} active={active} detect_score={detect_score} target={stealth_value} margin={margin}"
    )
    return {
        "success": bool(result),
        "margin": margin,
        "detect_score": int(detect_score),
        "stealth_score": int(stealth_value),
        "hint": hint,
    }


def can_detect(observer, target, award_xp=False, active=False, context=None):
    return bool(resolve_detection(observer, target, award_xp=award_xp, active=active, context=context).get("success", False))


def detect(observer, target, award_xp=False):
    return can_detect(observer, target, award_xp=award_xp)