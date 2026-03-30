import logging
from collections.abc import Mapping

from .definitions import DEFAULT_RACE
from .utils import get_race_base_carry_weight, get_race_profile, resolve_race_name


LOGGER = logging.getLogger(__name__)


def build_race_state(race_name):
    profile = get_race_profile(race_name)
    return {
        "race": profile["key"],
        "name": profile["name"],
        "stat_caps": dict(profile["stat_caps"]),
        "learning_modifiers": dict(profile["learning_modifiers"]),
        "size": profile["size"],
        "carry_modifier": float(profile["carry_modifier"]),
        "max_carry_weight": float(get_race_base_carry_weight(profile["key"])),
        "description": profile.get("description", ""),
    }


def apply_race(character, race_name, sync=True, emit_messages=False):
    if not character:
        return build_race_state(DEFAULT_RACE)

    state = build_race_state(race_name)
    previous_race = resolve_race_name(getattr(getattr(character, "db", None), "race", None), default=DEFAULT_RACE)
    character.db.race = state["race"]
    character.db.stat_caps = dict(state["stat_caps"])
    character.db.learning_modifiers = dict(state["learning_modifiers"])
    character.db.size = state["size"]
    character.db.carry_modifier = float(state["carry_modifier"])
    character.db.max_carry_weight = float(state["max_carry_weight"])

    clamp_method = getattr(character, "clamp_stats_to_race", None)
    if callable(clamp_method):
        clamp_method(emit_messages=emit_messages)
    else:
        current_stats = getattr(character.db, "stats", None)
        if isinstance(current_stats, Mapping):
            updated = dict(current_stats)
            for stat_name, cap in state["stat_caps"].items():
                updated[stat_name] = min(int(updated.get(stat_name, 10) or 10), int(cap or 100))
            if updated != dict(current_stats):
                character.db.stats = updated

    if sync and hasattr(character, "update_encumbrance_state"):
        character.update_encumbrance_state()
    if sync and hasattr(character, "sync_client_state"):
        character.sync_client_state()

    if previous_race != state["race"]:
        LOGGER.info("Applied race %s to %s", state["race"], character)
    return state