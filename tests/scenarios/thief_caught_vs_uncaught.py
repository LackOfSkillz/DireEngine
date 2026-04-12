import random

from world.systems import justice
from world.systems.theft import resolve_theft_attempt


class _RollPatch:
    def __init__(self, rolls, fallback=50):
        self._rolls = list(rolls)
        self._fallback = fallback
        self._original = None

    def __enter__(self):
        self._original = random.randint

        def _patched(_a, _b):
            if self._rolls:
                return self._rolls.pop(0)
            return self._fallback

        random.randint = _patched
        return self

    def __exit__(self, exc_type, exc, tb):
        random.randint = self._original
        return False


def _hide(character, strength=150):
    character.db.stealthed = True
    character.db.stealth_value = strength
    character.set_state("hidden", {"strength": strength, "source": "test"})


def _reset_justice(actor):
    actor.db.crime_count = 0
    actor.db.last_crime_time = 0
    actor.db.last_crime_decay_time = 0
    actor.db.law_reputation = 0
    actor.db.last_law_reputation_decay_time = 0
    actor.db.wanted_level = 0
    actor.db.last_wanted_update = 0
    actor.db.guard_attention = False
    actor.db.pending_arrest = False
    actor.db.justice_incidents = []
    actor.db.warrants = {}
    actor.db.crime_flag = False
    actor.db.wanted_stub = False


def scenario(ctx):
    room = ctx.harness.create_test_room(key="TEST_THIEF_CAUGHT_VS_UNCAUGHT")

    thief = ctx.harness.create_test_character(room=room, key="TEST_THIEF_FAIRNESS")
    thief.learn_skill("thievery", {"rank": 110, "mindstate": 0})
    thief.learn_skill("stealth", {"rank": 80, "mindstate": 0})
    thief.learn_skill("perception", {"rank": 40, "mindstate": 0})

    npc_success = ctx.harness.create_test_character(room=room, key="TEST_UNCAUGHT_SUCCESS")
    npc_success.db.is_npc = True
    npc_success.learn_skill("perception", {"rank": 10, "mindstate": 0})
    npc_success.db.coins = 25

    npc_empty = ctx.harness.create_test_character(room=room, key="TEST_UNCAUGHT_FAIL")
    npc_empty.db.is_npc = True
    npc_empty.learn_skill("perception", {"rank": 10, "mindstate": 0})
    npc_empty.db.coins = 0

    npc_caught = ctx.harness.create_test_character(room=room, key="TEST_CAUGHT_FAIL")
    npc_caught.db.is_npc = True
    npc_caught.learn_skill("perception", {"rank": 140, "mindstate": 0})
    npc_caught.db.coins = 30

    _reset_justice(thief)
    _hide(thief)
    with _RollPatch([95, 5]):
        uncaught_success = resolve_theft_attempt(thief, npc_success)
    if not uncaught_success.get("success") or uncaught_success.get("caught"):
        raise AssertionError(f"Expected uncaught success, saw: {uncaught_success}")
    uncaught_success_crime = int(getattr(thief.db, "crime_count", 0) or 0)
    if uncaught_success_crime != 0:
        raise AssertionError(f"Uncaught success should not increment crime_count, saw {uncaught_success_crime}")

    _reset_justice(thief)
    _hide(thief)
    with _RollPatch([95, 5]):
        uncaught_fail = resolve_theft_attempt(thief, npc_empty)
    if uncaught_fail.get("success") or uncaught_fail.get("caught"):
        raise AssertionError(f"Expected uncaught failure, saw: {uncaught_fail}")
    uncaught_fail_crime = int(getattr(thief.db, "crime_count", 0) or 0)
    if uncaught_fail_crime != 0:
        raise AssertionError(f"Uncaught failure should not increment crime_count, saw {uncaught_fail_crime}")

    _reset_justice(thief)
    _hide(thief)
    with _RollPatch([1, 100]):
        caught_fail = resolve_theft_attempt(thief, npc_caught)
    if not caught_fail.get("caught"):
        raise AssertionError(f"Expected caught failure, saw: {caught_fail}")
    caught_fail_crime = int(getattr(thief.db, "crime_count", 0) or 0)
    if caught_fail_crime != 1:
        raise AssertionError(f"Caught failure should increment crime_count once, saw {caught_fail_crime}")

    _reset_justice(thief)
    _hide(thief)
    with _RollPatch([95, 5]):
        caught_success = resolve_theft_attempt(thief, npc_success)
    if not caught_success.get("success") or caught_success.get("caught"):
        raise AssertionError(f"Expected initial uncaught success before later proof, saw: {caught_success}")
    justice.trigger_justice_response(thief, npc_success, action_type="theft", severity=1, was_caught=True)
    caught_success_crime = int(getattr(thief.db, "crime_count", 0) or 0)
    if caught_success_crime != 1:
        raise AssertionError(f"Caught success should increment crime_count once, saw {caught_success_crime}")

    ctx.log(
        {
            "uncaught_success_crime": uncaught_success_crime,
            "uncaught_fail_crime": uncaught_fail_crime,
            "caught_fail_crime": caught_fail_crime,
            "caught_success_crime": caught_success_crime,
        }
    )

    return {
        "uncaught_success_crime": uncaught_success_crime,
        "uncaught_fail_crime": uncaught_fail_crime,
        "caught_fail_crime": caught_fail_crime,
        "caught_success_crime": caught_success_crime,
    }