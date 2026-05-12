import logging

from engine.services.skill_service import SkillService
from world.systems.skills import normalize_skill_name


logger = logging.getLogger(__name__)


def _skill_exists(character, skill_name):
    normalized_skill = normalize_skill_name(skill_name)
    try:
        from typeclasses.characters import SKILL_REGISTRY
    except Exception:
        return True
    return normalized_skill in SKILL_REGISTRY


def attempt_with_failure_learning(
    character,
    skill_name,
    difficulty,
    *,
    success,
    failure_reason="skill_too_low",
    success_multiplier=1.0,
    failure_multiplier=0.25,
    event_key=None,
    source_mode="difficulty",
):
    """Award attempt XP for success or low-skill failure.

    Returns metadata describing whether XP was awarded and how much.
    """

    normalized_skill = normalize_skill_name(skill_name)
    metadata = {
        "skill": normalized_skill,
        "difficulty": max(1, int(difficulty or 1)),
        "awarded": 0.0,
        "awarded_xp": False,
        "outcome": "success" if success else "failure",
        "failure_reason": None if success else str(failure_reason or "generic").strip().lower(),
    }

    if character is None:
        metadata["outcome"] = "blocked"
        metadata["failure_reason"] = "missing_character"
        return metadata

    if not _skill_exists(character, normalized_skill):
        logger.warning("attempt_with_failure_learning received unknown skill '%s'", normalized_skill)
        metadata["outcome"] = "blocked"
        metadata["failure_reason"] = "unknown_skill"
        return metadata

    should_award = bool(success)
    outcome = "success" if success else "failure"
    context_multiplier = max(0.0, float(success_multiplier if success else failure_multiplier))
    if not success:
        failure_reason = metadata["failure_reason"]
        should_award = failure_reason == "skill_too_low" and context_multiplier > 0.0

    if not should_award:
        return metadata

    result = SkillService.award_xp(
        character,
        normalized_skill,
        metadata["difficulty"],
        source={"mode": str(source_mode or "difficulty")},
        success=bool(success),
        outcome=outcome,
        event_key=event_key,
        context_multiplier=context_multiplier,
    )
    awarded = float(getattr(result, "amount", 0.0) or 0.0)
    metadata["awarded"] = awarded
    metadata["awarded_xp"] = awarded > 0.0 or bool(getattr(result, "success", False))
    return metadata