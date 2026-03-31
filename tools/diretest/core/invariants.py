"""Invariant registry and baseline invariants for DireTest."""

from __future__ import annotations


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
    coins = int(getattr(getattr(character, "db", None), "coins", 0) or 0)
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