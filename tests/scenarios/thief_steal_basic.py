import random
import time

from tests.scenarios._roundtime import assert_roundtime_blocks
from world.systems.theft import (
    apply_steal_reward,
    get_repeat_target_penalty,
    get_shop_heat,
    get_theft_skill_total,
    resolve_theft_attempt,
)


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


def _capture_messages(character):
    original_msg = character.msg
    entries = []

    def _wrapped(*args, **kwargs):
        payload = kwargs.get("text")
        if payload is None and args:
            payload = args[0]
        if payload is not None:
            entries.append(str(payload))
        return original_msg(*args, **kwargs)

    character.msg = _wrapped
    return entries, original_msg


def scenario(ctx):
    room = ctx.harness.create_test_room(key="TEST_THIEF_STEAL_ROOM")
    thief = ctx.harness.create_test_character(room=room, key="TEST_THIEF_ACTOR")
    ctx.character = thief
    ctx.room = room

    thief.learn_skill("thievery", {"rank": 110, "mindstate": 0})
    thief.learn_skill("stealth", {"rank": 80, "mindstate": 0})
    thief.learn_skill("appraisal", {"rank": 60, "mindstate": 0})
    thief.learn_skill("perception", {"rank": 50, "mindstate": 0})

    npc_success = ctx.harness.create_test_character(room=room, key="TEST_THIEF_NPC_SUCCESS")
    npc_success.db.is_npc = True
    npc_success.learn_skill("perception", {"rank": 10, "mindstate": 0})
    npc_success.db.coins = 25
    observer = ctx.harness.create_test_character(room=room, key="TEST_THIEF_STEAL_OBSERVER")
    observer.learn_skill("perception", {"rank": 25, "mindstate": 0})

    thievery_before = float(thief.exp_skills.get("thievery").pool)
    _hide(thief)
    npc_success_before = int(getattr(thief.db, "coins", 0) or 0)
    observer_messages, original_observer_msg = _capture_messages(observer)
    try:
        with _RollPatch([95, 5]):
            ctx.cmd("steal TEST_THIEF_NPC_SUCCESS")
    finally:
        observer.msg = original_observer_msg
    npc_success_after = int(getattr(thief.db, "coins", 0) or 0)
    thievery_after = float(thief.exp_skills.get("thievery").pool)
    if npc_success_after <= npc_success_before:
        raise AssertionError("Successful NPC theft through the command path should increase the thief's coins.")
    if thievery_after <= thievery_before:
        raise AssertionError(f"Successful theft should train thievery: before={thievery_before}, after={thievery_after}")
    if not thief.is_hidden():
        raise AssertionError("Uncaught steal should leave the thief hidden.")
    observer_transcript = " ".join(observer_messages).lower()
    if observer_transcript and ("test_thief_actor" in observer_transcript or "steal" in observer_transcript):
        raise AssertionError(f"Uncaught steal leaked identity or theft messaging to observers: {observer_messages}")

    steal_roundtime_messages = assert_roundtime_blocks(ctx, "steal TEST_THIEF_NPC_SUCCESS")

    repeat_target = ctx.harness.create_test_character(room=room, key="TEST_THIEF_REPEAT_TARGET")
    repeat_target.db.is_npc = True
    repeat_target.learn_skill("perception", {"rank": 5, "mindstate": 0})
    repeat_target.db.coins = 40

    _hide(thief)
    baseline_total = get_theft_skill_total(thief, repeat_target)
    with _RollPatch([90, 5]):
        repeat_result = resolve_theft_attempt(thief, repeat_target)
    repeat_reward = apply_steal_reward(thief, repeat_target, repeat_result.get("item"))
    repeated_total = get_theft_skill_total(thief, repeat_target)
    repeat_penalty = get_repeat_target_penalty(thief, repeat_result.get("target_key"))
    if not repeat_reward:
        raise AssertionError("Repeat-target setup theft should have produced a reward.")
    if repeated_total >= baseline_total or repeat_penalty <= 0:
        raise AssertionError(
            f"Repeat-target theft did not get harder immediately: baseline={baseline_total}, repeated={repeated_total}, penalty={repeat_penalty}"
        )

    mark_target = ctx.harness.create_test_character(room=room, key="TEST_THIEF_MARK_TARGET")
    mark_target.db.is_npc = True
    mark_target.learn_skill("perception", {"rank": 20, "mindstate": 0})
    mark_target.db.coins = 10

    thief.db.repeat_theft_targets = {}
    thief.db.last_mark_target = None
    thief.db.last_mark_time = 0
    appraisal_before = float(thief.exp_skills.get("appraisal").pool)
    perception_before = float(thief.exp_skills.get("perception").pool)
    unmarked_total = get_theft_skill_total(thief, mark_target)
    ctx.cmd("mark TEST_THIEF_MARK_TARGET")
    marked_total = get_theft_skill_total(thief, mark_target)
    appraisal_after = float(thief.exp_skills.get("appraisal").pool)
    perception_after = float(thief.exp_skills.get("perception").pool)
    if marked_total <= unmarked_total:
        raise AssertionError(f"Marked target should be easier to steal from: unmarked={unmarked_total}, marked={marked_total}")
    if appraisal_after <= appraisal_before:
        raise AssertionError(f"Mark should train appraisal: before={appraisal_before}, after={appraisal_after}")
    if perception_after <= perception_before:
        raise AssertionError(f"Mark should train perception: before={perception_before}, after={perception_after}")

    player_target = ctx.harness.create_test_character(room=room, key="TEST_THIEF_PLAYER_TARGET")
    player_target.learn_skill("perception", {"rank": 15, "mindstate": 0})
    player_target.db.coins = 12

    _hide(thief)
    thief.db.pvp_open_until = 0
    with _RollPatch([80, 10]):
        player_result = resolve_theft_attempt(thief, player_target)
    player_reward = apply_steal_reward(thief, player_target, player_result.get("item"))
    if not player_reward:
        raise AssertionError("Player theft test should have produced a stolen reward.")
    if float(getattr(thief.db, "pvp_open_until", 0) or 0) <= time.time():
        raise AssertionError("Player theft should set the PvP-open timer.")

    shop_room = ctx.harness.create_test_room(key="TEST_THIEF_SHOP_ROOM")
    shop_room.db.is_shop = True
    shopkeeper = ctx.harness.create_test_object(
        key="TEST_THIEF_SHOPKEEPER",
        location=shop_room,
        typeclass="typeclasses.vendor.Vendor",
    )
    shopkeeper.db.is_shopkeeper = True
    shopkeeper.learn_skill("perception", {"rank": 15, "mindstate": 0})
    ctx.harness.create_test_object(
        key="silver ring",
        location=shopkeeper,
        weight=1,
        stealable=True,
    )

    thief.move_to(shop_room, quiet=True)
    ctx.room = shop_room
    _hide(thief)
    with _RollPatch([75, 10]):
        shop_result = resolve_theft_attempt(thief, shopkeeper, context={"requested_item": "silver ring"})
    shop_reward = apply_steal_reward(thief, shopkeeper, shop_result.get("item"))
    shop_heat = get_shop_heat(shopkeeper)
    if not shop_reward:
        raise AssertionError("Shop theft test should have produced a stolen item.")
    if shop_heat <= 0:
        raise AssertionError("Shop heat should increase after a theft attempt.")

    caught_target = ctx.harness.create_test_character(room=shop_room, key="TEST_THIEF_CAUGHT_TARGET")
    caught_target.db.is_npc = True
    caught_target.learn_skill("perception", {"rank": 140, "mindstate": 0})
    caught_target.db.coins = 30

    thief.move_to(shop_room, quiet=True)
    _hide(thief)
    thief.db.wanted_stub = False
    with _RollPatch([1, 100]):
        caught_result = resolve_theft_attempt(thief, caught_target)
    if not caught_result.get("caught"):
        raise AssertionError(f"Caught theft test should have produced a caught result: {caught_result}")
    if not bool(getattr(thief.db, "wanted_stub", False)):
        raise AssertionError("Caught theft should trigger the justice stub.")

    ctx.log({
        "actor_total": int(caught_result.get("actor_total", 0) or 0),
        "observer_total": int(caught_result.get("observer_total", 0) or 0),
        "thievery_pool_after_steal": thievery_after,
        "appraisal_pool_after_mark": appraisal_after,
        "perception_pool_after_mark": perception_after,
        "repeat_penalty": int(repeat_penalty or 0),
        "shop_heat": int(shop_heat or 0),
        "pvp_open_until": float(getattr(thief.db, "pvp_open_until", 0) or 0),
        "steal_roundtime_blocked": bool(steal_roundtime_messages),
    })

    return {
        "npc_command_coin_delta": npc_success_after - npc_success_before,
        "uncaught_success_hidden": bool(thief.is_hidden()),
        "observer_message_count": len(observer_messages),
        "repeat_penalty": repeat_penalty,
        "baseline_total": baseline_total,
        "repeated_total": repeated_total,
        "unmarked_total": unmarked_total,
        "marked_total": marked_total,
        "thievery_pool_after_steal": thievery_after,
        "appraisal_pool_after_mark": appraisal_after,
        "perception_pool_after_mark": perception_after,
        "player_pvp_open_until": float(getattr(thief.db, "pvp_open_until", 0) or 0),
        "shop_heat": shop_heat,
        "caught_result": caught_result,
        "steal_roundtime_blocked": True,
    }