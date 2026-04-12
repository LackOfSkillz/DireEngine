import random
import time

from tests.scenarios._roundtime import assert_roundtime_blocks
from world.systems import awareness, stealth
from world.systems.theft import can_steal_from, get_contact_info, resolve_theft_attempt


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


def scenario(ctx):
    room = ctx.harness.create_test_room(key="TEST_THIEF_COUNTERPLAY_ROOM")
    passage_room = ctx.harness.create_test_room(key="TEST_THIEF_PASSAGE_DEST")
    room.db.has_passage = True
    room.db.passage_links = [passage_room]

    thief = ctx.harness.create_test_character(room=room, key="TEST_THIEF_COUNTERPLAY")
    ctx.character = thief
    ctx.room = room
    thief.set_profession("thief")
    thief.learn_skill("stealth", {"rank": 90, "mindstate": 0})
    thief.learn_skill("thievery", {"rank": 95, "mindstate": 0})
    thief.learn_skill("perception", {"rank": 70, "mindstate": 0})

    hidden_target = ctx.harness.create_test_character(room=room, key="TEST_HIDDEN_TARGET")
    hidden_target.learn_skill("stealth", {"rank": 80, "mindstate": 0})
    _hide(hidden_target, strength=95)

    with _RollPatch([90]):
        ctx.cmd("search")
    if hidden_target.is_hidden():
        raise AssertionError("Search should expose a hidden target when the active-detection margin is high enough.")
    if room.id not in list(getattr(thief.db, "known_passages", None) or []):
        raise AssertionError("Search should reveal a hidden passage in the room.")
    search_roundtime_messages = assert_roundtime_blocks(ctx, "search")

    watch_target = ctx.harness.create_test_character(room=room, key="TEST_OBSERVE_TARGET")
    watch_target.learn_skill("perception", {"rank": 40, "mindstate": 0})
    baseline_awareness = awareness.get_awareness_total(watch_target, actor=thief, context={"room": room})
    thief.set_roundtime(0)
    ctx.cmd("observe TEST_OBSERVE_TARGET")
    observe_roundtime_messages = assert_roundtime_blocks(ctx, "observe TEST_OBSERVE_TARGET")
    thief.set_roundtime(0)
    ctx.cmd("observe TEST_OBSERVE_TARGET")
    repeated_awareness = awareness.get_awareness_total(watch_target, actor=thief, context={"room": room})
    if repeated_awareness <= baseline_awareness:
        raise AssertionError("Repeated observe should increase the target's awareness against the thief.")

    chest_owner = ctx.harness.create_test_character(room=room, key="TEST_CHEST_OWNER")
    chest_owner.db.is_npc = True
    chest_owner.learn_skill("perception", {"rank": 15, "mindstate": 0})
    chest = ctx.harness.create_test_object(key="shadow chest", location=chest_owner, is_container=True, weight=2)
    gem = ctx.harness.create_test_object(key="moonstone", location=chest, weight=1)
    _hide(thief, strength=150)
    thief.set_roundtime(0)
    with _RollPatch([95, 5]):
        ctx.cmd("steal moonstone from shadow chest")
    if getattr(gem, "location", None) != thief:
        raise AssertionError("Steal should support taking an item from a nested container.")

    thief.set_roundtime(0)
    ctx.cmd("passage")
    passage_travel_success = thief.location == passage_room
    if not passage_travel_success:
        raise AssertionError("Passage should move the thief to the linked hidden room.")

    shop_room = ctx.harness.create_test_room(key="TEST_COUNTERPLAY_SHOP")
    shop_room.db.is_shop = True
    shopkeeper = ctx.harness.create_test_object(
        key="TEST_COUNTERPLAY_SHOPKEEPER",
        location=shop_room,
        typeclass="typeclasses.vendor.Vendor",
    )
    shopkeeper.db.is_shopkeeper = True
    shopkeeper.db.shop_heat = 3
    shopkeeper.learn_skill("perception", {"rank": 25, "mindstate": 0})
    ctx.harness.create_test_object(key="silver clasp", location=shopkeeper, weight=1)

    thief.move_to(shop_room, quiet=True)
    _hide(thief, strength=150)
    allowed, message = can_steal_from(thief, shopkeeper)
    if allowed or "watching" not in str(message or ""):
        raise AssertionError("High shop heat should block fresh theft attempts.")

    caught_target = ctx.harness.create_test_character(room=shop_room, key="TEST_COUNTERPLAY_CAUGHT")
    caught_target.db.is_npc = True
    caught_target.learn_skill("perception", {"rank": 140, "mindstate": 0})
    caught_target.db.coins = 25
    _hide(thief, strength=120)
    thief.db.thief_reputation = 0
    thief.db.wanted_level = 0
    with _RollPatch([1, 100]):
        caught_result = resolve_theft_attempt(thief, caught_target, context={"room": shop_room})
    if not caught_result.get("caught"):
        raise AssertionError("Caught theft should still be possible under the counterplay rules.")
    if int(getattr(thief.db, "wanted_level", 0) or 0) <= 0:
        raise AssertionError("Caught theft should raise wanted level.")
    if int(getattr(thief.db, "thief_reputation", 0) or 0) >= 0:
        raise AssertionError("Caught theft should reduce thief reputation.")

    suspicion_room = ctx.harness.create_test_room(key="TEST_SUSPICION_ROOM")
    suspicious_observer = ctx.harness.create_test_character(room=suspicion_room, key="TEST_SUSPICIOUS_OBSERVER")
    suspicious_observer.learn_skill("perception", {"rank": 10, "mindstate": 0})
    sneaking_target = ctx.harness.create_test_character(room=suspicion_room, key="TEST_SNEAKING_TARGET")
    _hide(sneaking_target, strength=70)
    suspicion_room.db.suspicion_level = 0
    base_bonus = awareness.get_awareness_total(suspicious_observer, actor=sneaking_target, context={"room": suspicion_room}) - 10
    with _RollPatch([20]):
        low_result = stealth.resolve_detection(suspicious_observer, sneaking_target, active=True, context={"perception_bonus": base_bonus})
    suspicion_room.db.suspicion_level = 25
    high_bonus = awareness.get_awareness_total(suspicious_observer, actor=sneaking_target, context={"room": suspicion_room}) - 10
    with _RollPatch([20]):
        high_result = stealth.resolve_detection(suspicious_observer, sneaking_target, active=True, context={"perception_bonus": high_bonus})
    if high_result.get("margin", -999) <= low_result.get("margin", -999):
        raise AssertionError("Room suspicion should improve active detection results.")

    thief.db.contacts = {"fence": {"role": "fence", "disposition": 2}}
    contact_info = get_contact_info(thief, "fence")
    if str(contact_info.get("role", "")) != "fence":
        raise AssertionError("Contact scaffold should return stored contact information.")

    ctx.log({
        "repeated_awareness": repeated_awareness,
        "wanted_level": int(getattr(thief.db, "wanted_level", 0) or 0),
        "thief_reputation": int(getattr(thief.db, "thief_reputation", 0) or 0),
        "low_margin": int(low_result.get("margin", 0) or 0),
        "high_margin": int(high_result.get("margin", 0) or 0),
        "search_roundtime_blocked": bool(search_roundtime_messages),
        "observe_roundtime_blocked": bool(observe_roundtime_messages),
    })

    return {
        "search_revealed_hidden": not hidden_target.is_hidden(),
        "passage_revealed": room.id in list(getattr(thief.db, "known_passages", None) or []),
        "observe_awareness_gain": repeated_awareness - baseline_awareness,
        "container_theft_success": getattr(gem, "location", None) == thief,
        "passage_travel_success": passage_travel_success,
        "wanted_level": int(getattr(thief.db, "wanted_level", 0) or 0),
        "thief_reputation": int(getattr(thief.db, "thief_reputation", 0) or 0),
        "shop_block_message": str(message or ""),
        "room_suspicion_margin_gain": int(high_result.get("margin", 0) or 0) - int(low_result.get("margin", 0) or 0),
        "contact_role": str(contact_info.get("role", "") or ""),
        "search_roundtime_blocked": True,
        "observe_roundtime_blocked": True,
    }
