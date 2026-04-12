import random

from tests.scenarios._roundtime import assert_roundtime_blocks
from world.systems.stealth import detect


def scenario(ctx):
    room = ctx.harness.create_test_room(key="TEST_THIEF_HIDE_ROOM")
    hider = ctx.harness.create_test_character(room=room, key="TEST_THIEF_HIDER")
    ctx.character = hider
    ctx.room = room

    hider.learn_skill("stealth", {"rank": 80, "mindstate": 0})

    ctx.cmd("hide")
    alone_hidden = bool(getattr(hider.db, "stealthed", False)) and hider.is_hidden()
    stealth_score = int(getattr(hider.db, "stealth_value", 0) or 0)
    if not alone_hidden:
        raise AssertionError("Hide alone should leave the character hidden.")

    ctx.cmd("unhide")
    hider_messages = assert_roundtime_blocks(ctx, "hide")
    roundtime_blocked = True

    observer = ctx.harness.create_test_character(room=room, key="TEST_THIEF_OBSERVER")
    observer.learn_skill("perception", {"rank": 50, "mindstate": 0})

    original_randint = random.randint
    try:
        random.randint = lambda _a, _b: 40
        hider.db.stealthed = True
        hider.db.stealth_value = 100
        hider.set_state("hidden", {"strength": 100, "source": "test"})
        detect_fail = detect(observer, hider)

        random.randint = lambda _a, _b: 60
        detect_success = detect(observer, hider)
    finally:
        random.randint = original_randint

    if detect_fail or not detect_success:
        raise AssertionError("Single-observer detection should produce mixed results across seeded rolls.")

    entry_room = ctx.harness.create_test_room(key="TEST_THIEF_ENTRY_ROOM")
    ctx.harness.create_test_exit(room, entry_room, "east", aliases=["e"])
    ctx.harness.create_test_exit(entry_room, room, "west", aliases=["w"])
    late_observer = ctx.harness.create_test_character(room=entry_room, key="TEST_THIEF_LATE")
    late_observer.learn_skill("perception", {"rank": 0, "mindstate": 0})

    hider.db.stealthed = True
    hider.db.stealth_value = 999
    hider.set_state("hidden", {"strength": 999, "source": "test"})
    late_observer.move_to(room, quiet=True)
    post_entry_visible = room.get_display_characters(late_observer)
    if "TEST_THIEF_HIDER" in post_entry_visible:
        raise AssertionError("Observer entering after hide should still be gated by the room visibility check.")

    weak_observer = ctx.harness.create_test_character(room=room, key="TEST_THIEF_WEAK")
    strong_observer = ctx.harness.create_test_character(room=room, key="TEST_THIEF_STRONG")
    weak_observer.learn_skill("perception", {"rank": 0, "mindstate": 0})
    strong_observer.learn_skill("perception", {"rank": 100, "mindstate": 0})

    try:
        random.randint = lambda _a, _b: 1
        hider.db.stealthed = True
        hider.db.stealth_value = 101
        hider.set_state("hidden", {"strength": 101, "source": "test"})
        multi_results = [
            {"observer": weak_observer.key, "detected": detect(weak_observer, hider)},
            {"observer": strong_observer.key, "detected": detect(strong_observer, hider)},
        ]
    finally:
        random.randint = original_randint

    detected_values = [entry["detected"] for entry in multi_results]
    if all(detected_values) or not any(detected_values):
        raise AssertionError("Multiple observers should not all resolve the same way in the mixed-detection scenario.")

    ctx.log({
        "stealth_score": stealth_score,
        "detect_results": multi_results,
        "roundtime_blocked": roundtime_blocked,
    })

    return {
        "stealth_score": stealth_score,
        "detect_results": multi_results,
        "alone_hidden": alone_hidden,
        "roundtime_blocked": roundtime_blocked,
        "single_observer_results": [detect_fail, detect_success],
        "observer_entry_visibility": post_entry_visible,
    }