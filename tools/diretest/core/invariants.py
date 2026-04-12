"""Invariant registry and baseline invariants for DireTest."""

from __future__ import annotations

import json


INVARIANTS = {}


def invariant(name):
    """Register a named invariant function."""

    invariant_name = str(name or "").strip()
    if not invariant_name:
        raise ValueError("Invariant name must be a non-empty string.")

    def decorator(func):
        INVARIANTS[invariant_name] = func
        return func

    return decorator


def _object_exists(obj):
    from evennia.objects.models import ObjectDB

    object_id = int(getattr(obj, "id", 0) or 0)
    return object_id > 0 and ObjectDB.objects.filter(id=object_id).exists()


def _object_weight(obj):
    if hasattr(obj, "get_total_weight"):
        try:
            return max(0.0, float(obj.get_total_weight() or 0.0))
        except TypeError:
            pass
    try:
        return float(obj.db.weight or 0.0)
    except (TypeError, ValueError):
        return 0.0


def run_invariant(name, ctx):
    """Run a registered invariant and return a structured result."""

    invariant_name = str(name or "").strip()
    checker = INVARIANTS.get(invariant_name)
    if checker is None:
        raise KeyError(f"Unknown DireTest invariant: {invariant_name}")

    outcome = checker(ctx)
    if isinstance(outcome, tuple):
        passed = bool(outcome[0])
        message = str(outcome[1] if len(outcome) > 1 else "")
    elif isinstance(outcome, dict):
        passed = bool(outcome.get("passed", False))
        message = str(outcome.get("message", "") or "")
    elif outcome is False:
        passed = False
        message = "Invariant returned False."
    else:
        passed = True
        message = str(outcome or "")

    return {
        "name": invariant_name,
        "passed": passed,
        "message": message,
    }


@invariant("no_negative_currency")
def _no_negative_currency(ctx):
    character = ctx.get_character()
    if not character:
        return True, "No active character."
    coins = int(character.db.coins or 0)
    if coins < 0:
        return False, f"Character has negative coins: {coins}."
    return True, "Currency is non-negative."


@invariant("valid_room_state")
def _valid_room_state(ctx):
    character = ctx.get_character()
    room = ctx.get_room()
    if room is None:
        return False, "No active room."
    if character is not None and getattr(character, "location", None) != room:
        return False, "Character location does not match active room."
    return True, "Room state is valid."


@invariant("character_exists")
def _character_exists(ctx):
    character = ctx.get_character()
    if character is None:
        return False, "No active character."
    if not _object_exists(character):
        return False, "Active character no longer exists in the database."
    return True, "Character exists."


@invariant("no_duplicate_objects")
def _no_duplicate_objects(ctx):
    harness = getattr(ctx, "harness", None)
    tracked = list(getattr(harness, "created_objects", []) or [])
    tracked_ids = [int(getattr(obj, "id", 0) or 0) for obj in tracked if getattr(obj, "id", None)]
    if len(tracked_ids) != len(set(tracked_ids)):
        return False, "Tracked object list contains duplicate ids."

    room = ctx.get_room()
    if room is not None:
        room_ids = [int(getattr(obj, "id", 0) or 0) for obj in list(getattr(room, "contents", []) or []) if getattr(obj, "id", None)]
        if len(room_ids) != len(set(room_ids)):
            return False, "Room contains duplicate object ids."

    return True, "No duplicate objects detected."


@invariant("valid_combat_state")
def _valid_combat_state(ctx):
    character = ctx.get_character()
    if not character:
        return True, "No active character."

    in_combat = bool(getattr(character.db, "in_combat", False))
    target = character.get_target() if hasattr(character, "get_target") else getattr(character.db, "target", None)
    if in_combat and not target:
        return False, "Character is marked in combat without a target."
    if target and not _object_exists(target):
        return False, "Combat target no longer exists."
    if target and getattr(target, "location", None) != getattr(character, "location", None):
        return False, "Combat target is no longer in the same room."
    if not in_combat and target:
        return False, "Disengaged character still retains a combat target."
    if hasattr(character, "is_dead") and character.is_dead() and (in_combat or target):
        return False, "Dead character remains linked to active combat state."
    return True, "Combat state is valid."


@invariant("valid_death_state")
def _valid_death_state(ctx):
    character = ctx.get_character()
    if not character:
        return True, "No active character."

    life_state = str(getattr(character.db, "life_state", "ALIVE") or "ALIVE").upper()
    corpse = character.get_death_corpse() if hasattr(character, "get_death_corpse") else None
    grave = character.get_owned_grave() if hasattr(character, "get_owned_grave") else None
    allowed_states = {"ALIVE", "DEAD", "DEPARTED"}

    if life_state not in allowed_states:
        return False, f"Illegal life_state: {life_state}."
    if life_state == "ALIVE" and corpse and _object_exists(corpse):
        return False, "Alive character still has an active corpse link."
    if life_state == "DEPARTED" and corpse and _object_exists(corpse):
        return False, "Departed character still has an unresolved corpse link."
    if life_state == "DEAD" and corpse is None and grave is None:
        return False, "Dead character has neither corpse nor grave recovery state."
    if life_state == "ALIVE" and getattr(character.db, "last_corpse_id", None) and not grave:
        return False, "Alive character retains corpse linkage without grave recovery."
    return True, "Death state is valid."


@invariant("valid_weight_state")
def _valid_weight_state(ctx):
    character = ctx.get_character()
    if not character:
        return True, "No active character."

    total_weight = float(character.get_total_weight() if hasattr(character, "get_total_weight") else 0.0)
    max_carry_weight = float(character.get_max_carry_weight() if hasattr(character, "get_max_carry_weight") else getattr(character.db, "max_carry_weight", 0.0) or 0.0)
    encumbrance_ratio = float(character.get_encumbrance_ratio() if hasattr(character, "get_encumbrance_ratio") else getattr(character.db, "encumbrance_ratio", 0.0) or 0.0)
    expected_ratio = total_weight / max(0.0001, max_carry_weight)

    if total_weight < 0:
        return False, "Character total weight is negative."
    if max_carry_weight <= 0:
        return False, "Character max carry weight is not positive."
    if abs(encumbrance_ratio - expected_ratio) > 0.01:
        return False, f"Encumbrance ratio drifted from computed value: {encumbrance_ratio} vs {expected_ratio}."

    for item in list(getattr(character, "contents", []) or []) + list(character.get_worn_items() or []):
        if _object_weight(item) < 0:
            return False, f"Negative item weight detected on {getattr(item, 'key', 'item')}."

    return True, "Weight state is valid."


@invariant("valid_race_state")
def _valid_race_state(ctx):
    from world.races import RACE_DEFINITIONS, RACE_LEARNING_CATEGORIES, RACE_STATS, get_race_carry_modifier, get_race_learning_modifier, resolve_race_name

    character = ctx.get_character()
    if not character:
        return True, "No active character."

    race_key = resolve_race_name(getattr(character.db, "race", None), default=None)
    if race_key not in RACE_DEFINITIONS:
        return False, f"Unknown race: {race_key}."

    carry_modifier = float(character.get_race_carry_modifier() if hasattr(character, "get_race_carry_modifier") else getattr(character.db, "carry_modifier", 1.0) or 1.0)
    expected_carry = float(get_race_carry_modifier(race_key))
    if abs(carry_modifier - expected_carry) > 0.0001:
        return False, f"Carry modifier drifted from race definition: {carry_modifier} vs {expected_carry}."

    if hasattr(character, "validate_race_application"):
        valid, details = character.validate_race_application()
        if not valid:
            return False, f"Race application validation failed: {details}"

    for stat_name in RACE_STATS:
        expected_cap = int(character.get_race_stat_cap(stat_name) if hasattr(character, "get_race_stat_cap") else 0)
        if expected_cap <= 0:
            return False, f"Invalid race stat cap for {stat_name}."

    for category in RACE_LEARNING_CATEGORIES:
        modifier = float(character.get_race_learning_modifier(category=category) if hasattr(character, "get_race_learning_modifier") else get_race_learning_modifier(race_key, category))
        if modifier <= 0:
            return False, f"Invalid race learning modifier for {category}."

    return True, "Race state is valid."


@invariant("client_payload_safe")
def _client_payload_safe(ctx):
    from world.area_forge.character_api import get_character_payload, get_subsystem_payload
    from world.area_forge.map_api import get_zone_map

    character = ctx.get_character()
    if not character:
        return True, "No active character."

    payloads = {
        "character": get_character_payload(character),
        "subsystem": get_subsystem_payload(character),
        "map": get_zone_map(character),
    }
    try:
        json.dumps(payloads, sort_keys=True)
    except Exception as error:
        return False, f"Client payload serialization failed: {error}"
    return True, "Client payloads are safe to serialize."