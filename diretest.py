import argparse
import json
import os
import sys
import time
import traceback

from tools.diretest.core.artifacts import write_artifacts
from tools.diretest.core.runner import run_scenario
from tools.diretest.core.seed import set_seed


def _setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()

    import evennia

    if not bool(getattr(evennia, "_LOADED", False)):
        evennia._init()

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA busy_timeout = 30000")


def _create_temp_room(prefix):
    from evennia.utils.create import create_object

    suffix = str(int(time.time() * 1000))[-6:]
    room_name = f"{prefix}_{suffix}"
    room = create_object("typeclasses.rooms.Room", key=room_name, nohome=True)
    return room_name, room


def _cleanup_named_object(name):
    from evennia.utils.search import search_object

    for obj in list(search_object(name)):
        try:
            obj.delete()
        except Exception:
            pass


ONBOARDING_ROOM_NAMES = [
    "Intake Hall",
    "Lineup Platform",
    "Mirror Alcove",
    "Gear Rack Room",
    "Weapon Cage",
    "Training Yard",
    "Supply Shack",
    "Vendor Stall",
    "Breach Corridor",
    "Outer Gate",
]


def _get_or_create_tutorial_rooms(ObjectDB, create_object, created_objects):
    rooms = {}
    for room_name in ONBOARDING_ROOM_NAMES:
        room = None
        for candidate in ObjectDB.objects.filter(db_key__iexact=room_name):
            if getattr(getattr(candidate, "db", None), "is_tutorial", False):
                room = candidate
                break
        if room is None:
            room = create_object("typeclasses.rooms.Room", key=room_name, nohome=True)
            room.db.is_tutorial = True
            created_objects.append(room_name)
        rooms[room_name] = room
    return rooms


def _create_test_onboarding_character(create_object, rooms, created_objects, onboarding):
    character = create_object("typeclasses.characters.Character", key="DireTest Intake", location=rooms["Intake Hall"], home=rooms["Intake Hall"])
    created_objects.append(character.key)
    character.db.onboarding_state = onboarding._default_state()
    character.db.gender = None
    character.db.race = "human"
    character.db.injuries = {
        "left_arm": {"bleed": 2, "external": 6, "internal": 0, "bruise": 0, "max": 100, "vital": False, "tended": False, "tend": {}},
        "head": {"bleed": 0, "external": 0, "internal": 0, "bruise": 0, "max": 100, "vital": True, "tended": False, "tend": {}},
        "chest": {"bleed": 0, "external": 0, "internal": 0, "bruise": 0, "max": 100, "vital": True, "tended": False, "tend": {}},
    }
    character.db.coins = 50
    return character


def _default_test_name(requested_name):
    requested_name = str(requested_name or "DireTestHero").strip() or "DireTestHero"
    if requested_name != "DireTestHero":
        return requested_name
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    seed = int(time.time()) % (26 ** 4)
    suffix = ""
    for _ in range(4):
        suffix = alphabet[seed % 26] + suffix
        seed //= 26
    return f"Dire{suffix.title()}"


def _apply_onboarding_identity(character, rooms, onboarding, results):
    ok, message = onboarding.set_gender(character, "male")
    results.append({"step": "gender", "ok": ok, "message": message})

    character.move_to(rooms["Lineup Platform"], quiet=True, use_destination=False)
    ok, message = onboarding.select_race(character, "human")
    results.append({"step": "race", "ok": ok, "message": message})

    character.move_to(rooms["Mirror Alcove"], quiet=True, use_destination=False)
    for trait, value in {
        "hair style": "short",
        "hair color": "brown",
        "build": "average",
        "height": "average",
        "eyes": "gray",
    }.items():
        ok, message = onboarding.set_trait(character, trait, value)
    results.append({"step": "appearance", "ok": ok, "message": message})


def _equip_test_gear(character, create_object, created_objects):
    shirt = create_object("typeclasses.wearables.Wearable", key="diretest shirt", location=character, home=character)
    shirt.db.slot = "torso"
    shirt.db.weight = 1.0
    boots = create_object("typeclasses.wearables.Wearable", key="diretest boots", location=character, home=character)
    boots.db.slot = "feet"
    boots.db.weight = 1.5
    created_objects.extend([shirt.key, boots.key])
    character.equip_item(shirt)
    character.equip_item(boots)


def _create_test_weapon(character, create_object, created_objects):
    weapon = create_object("typeclasses.objects.Object", key="diretest sword", location=character, home=character)
    weapon.db.item_type = "weapon"
    weapon.db.weight = 3.0
    created_objects.append(weapon.key)
    return weapon


def _run_finish_sequence(character, rooms, create_object, created_objects, onboarding, results, final_name):
    character.move_to(rooms["Training Yard"], quiet=True, use_destination=False)
    goblin = create_object("typeclasses.npcs.NPC", key="diretest training goblin", location=rooms["Training Yard"], home=rooms["Training Yard"])
    goblin.db.is_npc = True
    goblin.db.is_tutorial_enemy = True
    goblin.db.onboarding_enemy_role = "training"
    goblin.db.hp = 0
    created_objects.append(goblin.key)
    onboarding.note_combat_start(character, goblin)
    onboarding.note_combat_win(character, goblin)
    results.append({"step": "combat", "ok": "combat" in set(onboarding.ensure_onboarding_state(character).get("completed_steps") or []), "message": "started and won training fight"})

    character.move_to(rooms["Supply Shack"], quiet=True, use_destination=False)
    character.apply_tend("left_arm", tender=character)
    character.heal_body_part("left_arm", 5)
    onboarding.note_healing_action(character, patient=character, part="left_arm")
    results.append({"step": "healing", "ok": "healing" in set(onboarding.ensure_onboarding_state(character).get("completed_steps") or []), "message": "tended bleeding arm"})

    character.move_to(rooms["Vendor Stall"], quiet=True, use_destination=False)
    onboarding.note_trade_action(character, "buy")
    onboarding.note_trade_action(character, "sell")
    results.append({"step": "economy", "ok": "economy" in set(onboarding.ensure_onboarding_state(character).get("completed_steps") or []), "message": "completed buy/sell loop"})

    character.move_to(rooms["Breach Corridor"], quiet=True, use_destination=False)
    onboarding.note_breach_progress(character, "start")
    breach_goblin = create_object("typeclasses.npcs.NPC", key="diretest breach goblin", location=rooms["Breach Corridor"], home=rooms["Breach Corridor"])
    breach_goblin.db.is_npc = True
    breach_goblin.db.is_tutorial_enemy = True
    breach_goblin.db.onboarding_enemy_role = "breach"
    breach_goblin.db.hp = 0
    created_objects.append(breach_goblin.key)
    onboarding.note_combat_win(character, breach_goblin)
    results.append({"step": "breach", "ok": "breach" in set(onboarding.ensure_onboarding_state(character).get("completed_steps") or []), "message": "cleared breach fight"})

    character.move_to(rooms["Outer Gate"], quiet=True, use_destination=False)
    ok, message = onboarding.set_final_name(character, final_name)
    results.append({"step": "name", "ok": ok, "message": message})


def _has_pending_mentor_correction(onboarding, character):
    state = onboarding.ensure_onboarding_state(character)
    return any(str(entry.get("role", "") or "") == "mentor" for entry in (state.get("pending_roleplay") or []))


def _has_recent_line(onboarding, character, text):
    needle = str(text or "").strip().lower()
    if not needle:
        return False
    return any(needle in str(line or "").lower() for line in onboarding.get_recent_lines(character))


def run_race_balance_scenario(args):
    _setup_django()

    from utils.diretest_race import build_cross_race_balance_report, build_race_impact_log, format_cross_race_balance_report

    room_name, room = _create_temp_room("diretest_race_balance")
    try:
        rows = build_cross_race_balance_report(
            room,
            profession=args.profession,
            sample_weight=args.sample_weight,
            base_xp=args.base_xp,
            cleanup=True,
        )
        output = {
            "scenario": "race-balance",
            "profession": args.profession,
            "sample_weight": float(args.sample_weight),
            "base_xp": int(args.base_xp),
            "rows": rows,
            "impact_log": build_race_impact_log(rows),
            "all_valid": all(row.get("validation_ok") for row in rows),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: race-balance")
            print(f"Profession: {args.profession}")
            print(f"Sample Weight: {float(args.sample_weight):.1f}")
            print(f"Base XP: {int(args.base_xp)}")
            print("")
            for line in format_cross_race_balance_report(rows):
                print(line)
            print("")
            print("Race Impact Log:")
            for entry in output["impact_log"]:
                print(
                    " | ".join(
                        [
                            entry["race_name"],
                            f"encumbrance_ratio={entry['encumbrance_ratio']:.2f}",
                            f"combat_xp={entry['xp_rate'].get('combat', 0.0):.2f}",
                            f"combat_effectiveness={json.dumps(entry['combat_effectiveness'], sort_keys=True)}",
                        ]
                    )
                )
            print("")
            print(f"Invariant Status: {'PASS' if output['all_valid'] else 'FAIL'}")
        return 0 if output["all_valid"] else 1
    finally:
        _cleanup_named_object(room_name)


def run_movement_scenario(args):
    _setup_django()

    def scenario(ctx):
        start_room = ctx.harness.create_test_room(key="TEST_MOVE_START")
        north_room = ctx.harness.create_test_room(key="TEST_MOVE_NORTH")
        ctx.harness.create_test_exit(start_room, north_room, "north", aliases=["n"])
        ctx.harness.create_test_exit(north_room, start_room, "south", aliases=["s"])

        character = ctx.harness.create_test_character(room=start_room, key="TEST_MOVE_CHAR")
        ctx.character = character
        ctx.room = start_room

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")
        ctx.cmd("look")
        ctx.cmd("north")
        ctx.cmd("look")

        movement_diff = ctx.diff_snapshots(0, 1)
        if not movement_diff["room_changed"]:
            raise AssertionError("Movement diff did not record a room change between the first two snapshots.")

        current_room = getattr(ctx.character, "location", None)
        if current_room != north_room:
            raise AssertionError("Movement scenario did not reach the expected destination room.")

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")
        return {
            "start_room": getattr(start_room, "key", None),
            "end_room": getattr(current_room, "key", None),
            "commands": list(ctx.command_log),
            "movement_diff": movement_diff,
            "snapshot_count": len(ctx.snapshots),
            "output_log": list(ctx.output_log),
        }

    return run_scenario(scenario, seed=args.seed, mode="direct", auto_snapshot=True, name="movement")


def run_inventory_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_INV_ROOM")
        character = ctx.harness.create_test_character(room=room, key="TEST_INV_CHAR")
        test_item = ctx.harness.create_test_object(
            key="TEST_INV_PACK",
            location=room,
            weight=2.5,
            desc="A weighted inventory test pack.",
        )

        ctx.character = character
        ctx.room = room

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")
        ctx.cmd("inventory")
        ctx.cmd("get TEST_INV_PACK")
        ctx.cmd("inventory")
        ctx.cmd("drop TEST_INV_PACK")
        ctx.cmd("inventory")

        pickup_diff = ctx.diff_snapshots(0, 1)
        drop_diff = ctx.diff_snapshots(1, 3)

        if pickup_diff["inventory_added"] != ["TEST_INV_PACK"]:
            raise AssertionError(f"Inventory pickup diff was not meaningful: {pickup_diff}")
        if pickup_diff["room_changed"]:
            raise AssertionError("Inventory pickup unexpectedly changed rooms.")
        if "TEST_INV_PACK" not in pickup_diff["room_contents_removed"]:
            raise AssertionError(f"Pickup diff did not record room-content removal: {pickup_diff}")

        if drop_diff["inventory_removed"] != ["TEST_INV_PACK"]:
            raise AssertionError(f"Inventory drop diff was not meaningful: {drop_diff}")
        if "TEST_INV_PACK" not in drop_diff["room_contents_added"]:
            raise AssertionError(f"Drop diff did not record room-content addition: {drop_diff}")

        carried_keys = [str(getattr(item, "key", "") or "") for item in list(getattr(ctx.character, "contents", []) or [])]
        room_keys = [str(getattr(item, "key", "") or "") for item in list(getattr(ctx.room, "contents", []) or [])]
        if "TEST_INV_PACK" in carried_keys:
            raise AssertionError("Inventory scenario ended with the test item still carried.")
        if "TEST_INV_PACK" not in room_keys:
            raise AssertionError("Inventory scenario ended without the dropped item in the room.")

        return {
            "commands": list(ctx.command_log),
            "pickup_diff": pickup_diff,
            "drop_diff": drop_diff,
            "snapshot_count": len(ctx.snapshots),
            "output_log": list(ctx.output_log),
            "item": getattr(test_item, "key", None),
        }

    return run_scenario(scenario, seed=args.seed, mode="direct", auto_snapshot=True, name="inventory")


def run_combat_basic_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_COMBAT_ROOM")
        attacker = ctx.harness.create_test_character(room=room, key="TEST_COMBAT_ATTACKER")
        defender = ctx.harness.create_test_character(room=room, key="TEST_COMBAT_DEFENDER")

        ctx.character = attacker
        ctx.room = room

        attacker.set_stat("agility", 40)
        attacker.set_stat("reflex", 40)
        defender.set_stat("agility", 1)
        defender.set_stat("reflex", 1)
        defender.set_hp(50)

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")
        ctx.cmd("target TEST_COMBAT_DEFENDER")
        ctx.snapshot("engaged")
        ctx.cmd("attack")
        ctx.snapshot("damaged")
        attacker.db.roundtime_end = 0
        ctx.cmd("disengage")
        ctx.snapshot("disengaged")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["initial", "engaged", "damaged", "disengaged"]
        if labels != expected_labels:
            raise AssertionError(f"Combat snapshot labels drifted: expected {expected_labels}, got {labels}")

        engaged_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("initial"), ctx.get_snapshot_by_label("engaged"))
        damaged_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("engaged"), ctx.get_snapshot_by_label("damaged"))
        disengaged_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("damaged"), ctx.get_snapshot_by_label("disengaged"))

        if not engaged_diff["target_assigned"]:
            raise AssertionError(f"Combat engagement did not assign a target: {engaged_diff}")
        if not engaged_diff["entered_combat"]:
            raise AssertionError(f"Combat engagement did not enter combat state: {engaged_diff}")
        if engaged_diff["target_after"] != "TEST_COMBAT_DEFENDER":
            raise AssertionError(f"Combat engagement targeted the wrong actor: {engaged_diff}")

        if damaged_diff["target_hp_delta"] is None or damaged_diff["target_hp_delta"] >= 0:
            raise AssertionError(f"Combat damage diff did not record target HP loss: {damaged_diff}")
        if not damaged_diff["in_combat_after"]:
            raise AssertionError(f"Combat damage snapshot lost combat state unexpectedly: {damaged_diff}")

        if not disengaged_diff["target_cleared"]:
            raise AssertionError(f"Combat disengage did not clear the target: {disengaged_diff}")
        if not disengaged_diff["exited_combat"]:
            raise AssertionError(f"Combat disengage did not exit combat state: {disengaged_diff}")

        return {
            "commands": list(ctx.command_log),
            "engaged_diff": engaged_diff,
            "damaged_diff": damaged_diff,
            "disengaged_diff": disengaged_diff,
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "output_log": list(ctx.output_log),
            "target_hp": int(getattr(defender.db, "hp", 0) or 0),
        }

    return run_scenario(scenario, seed=args.seed, mode="direct", auto_snapshot=False, name="combat-basic")


def run_death_loop_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_DEATH_ROOM")
        character = ctx.harness.create_test_character(room=room, key="TEST_DEATH_CHAR")
        keepsake = ctx.harness.create_test_object(
            key="TEST_DEATH_TOKEN",
            location=character,
            weight=1.0,
            item_value=12,
            value=12,
            desc="A token meant to survive a death-and-return loop.",
        )

        ctx.character = character
        ctx.room = room

        character.set_favor(10)
        character.db.coins = 37

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("alive")
        corpse = ctx.direct(character.at_death)
        if not corpse:
            raise AssertionError("Death loop did not create a corpse.")
        ctx.harness.track_object(corpse)
        ctx.snapshot("dead")
        ctx.cmd("depart full")
        ctx.cmd("depart confirm")
        ctx.snapshot("departed")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["alive", "dead", "departed"]
        if labels != expected_labels:
            raise AssertionError(f"Death-loop snapshot labels drifted: expected {expected_labels}, got {labels}")

        death_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("alive"), ctx.get_snapshot_by_label("dead"))
        depart_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("dead"), ctx.get_snapshot_by_label("departed"))

        if not death_diff["died"]:
            raise AssertionError(f"Death diff did not record a dead life-state transition: {death_diff}")
        if death_diff["character_coins_delta"] != -37:
            raise AssertionError(f"Death diff did not move carried coins off the character: {death_diff}")
        if death_diff["inventory_removed"] != ["TEST_DEATH_TOKEN"]:
            raise AssertionError(f"Death diff did not move carried items off the character: {death_diff}")
        if corpse.key not in death_diff["after_snapshot_created"]:
            raise AssertionError(f"Death diff did not record corpse creation: {death_diff}")

        if not depart_diff["revived"]:
            raise AssertionError(f"Depart diff did not record revival back to life: {depart_diff}")
        if depart_diff["character_coins_delta"] != 37:
            raise AssertionError(f"Depart diff did not restore kept coins: {depart_diff}")
        if depart_diff["inventory_added"] != ["TEST_DEATH_TOKEN"]:
            raise AssertionError(f"Depart diff did not restore carried items: {depart_diff}")
        if corpse.key not in depart_diff["after_snapshot_deleted"]:
            raise AssertionError(f"Depart diff did not record corpse cleanup: {depart_diff}")

        if character.is_dead():
            raise AssertionError("Death-loop scenario ended with the character still dead.")
        if int(getattr(character.db, "coins", 0) or 0) != 37:
            raise AssertionError("Death-loop scenario ended with the wrong carried coin count.")
        if keepsake.location != character:
            raise AssertionError("Death-loop scenario ended without the keepsake restored to the character.")

        return {
            "commands": list(ctx.command_log),
            "death_diff": death_diff,
            "depart_diff": depart_diff,
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "output_log": list(ctx.output_log),
            "corpse_key": getattr(corpse, "key", None),
            "coins": int(getattr(character.db, "coins", 0) or 0),
        }

    return run_scenario(scenario, seed=args.seed, mode="direct", auto_snapshot=False, name="death-loop")


def run_economy_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_ECON_ROOM")
        character = ctx.harness.create_test_character(room=room, key="TEST_ECON_CHAR")
        vendor = ctx.harness.create_test_object(key="merchant", location=room, typeclass="typeclasses.vendor.Vendor")
        vendor.db.vendor_type = "general"
        vendor.db.trade_difficulty = 1
        vendor.db.inventory = ["book"]

        sale_item = ctx.harness.create_test_object(
            key="TEST_ECON_TRINKET",
            location=character,
            weight=1.0,
            item_type="trinket",
            item_value=30,
            value=30,
            desc="A trade good meant to exercise the sell path.",
        )

        ctx.character = character
        ctx.room = room

        character.db.coins = 100
        character.set_stat("charisma", 40)
        character.update_skill("trading", rank=40, mindstate=0)
        character.update_skill("scholarship", rank=30, mindstate=0)

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")
        ctx.cmd("haggle merchant")
        ctx.snapshot("haggled")
        ctx.cmd("buy book")
        purchased_item = next(
            (
                item
                for item in list(getattr(character, "contents", []) or [])
                if str(getattr(item, "key", "") or "") == "study book"
            ),
            None,
        )
        if purchased_item is None:
            raise AssertionError("Economy scenario did not create the purchased inventory item.")
        ctx.harness.track_object(purchased_item)
        ctx.snapshot("bought")
        ctx.cmd("sell TEST_ECON_TRINKET")
        ctx.snapshot("sold")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["initial", "haggled", "bought", "sold"]
        if labels != expected_labels:
            raise AssertionError(f"Economy snapshot labels drifted: expected {expected_labels}, got {labels}")

        haggled_snapshot = ctx.get_snapshot_by_label("haggled")
        haggled_states = dict((haggled_snapshot.get("data", {}) or {}).get("character", {}).get("states", {}) or {})
        haggle_bonus = float(haggled_states.get("haggle_bonus", 0.0) or 0.0)
        if haggle_bonus <= 0.0:
            raise AssertionError(f"Economy scenario did not record a haggle bonus state: {haggled_states}")

        buy_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("haggled"), ctx.get_snapshot_by_label("bought"))
        sell_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("bought"), ctx.get_snapshot_by_label("sold"))

        if buy_diff["character_coins_delta"] != -20:
            raise AssertionError(f"Economy buy diff did not spend the expected coins: {buy_diff}")
        if buy_diff["inventory_added"] != ["study book"]:
            raise AssertionError(f"Economy buy diff did not add the purchased item: {buy_diff}")
        if buy_diff["room_changed"]:
            raise AssertionError(f"Economy buy unexpectedly changed rooms: {buy_diff}")

        if sell_diff["character_coins_delta"] != 15:
            raise AssertionError(f"Economy sell diff did not pay the expected vendor amount: {sell_diff}")
        if sell_diff["inventory_removed"] != ["TEST_ECON_TRINKET"]:
            raise AssertionError(f"Economy sell diff did not remove the sold item: {sell_diff}")
        if sale_item.key not in sell_diff["after_snapshot_deleted"]:
            raise AssertionError(f"Economy sell diff did not record sold-item deletion: {sell_diff}")

        if int(getattr(character.db, "coins", 0) or 0) != 95:
            raise AssertionError("Economy scenario ended with the wrong carried coin count.")
        if purchased_item.location != character:
            raise AssertionError("Economy scenario ended without the purchased item in inventory.")

        return {
            "commands": list(ctx.command_log),
            "buy_diff": buy_diff,
            "sell_diff": sell_diff,
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "output_log": list(ctx.output_log),
            "haggle_bonus": haggle_bonus,
            "coins": int(getattr(character.db, "coins", 0) or 0),
        }

    return run_scenario(scenario, seed=args.seed, mode="direct", auto_snapshot=False, name="economy")


def run_bank_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_BANK_ROOM")
        room.db.is_bank = True
        character = ctx.harness.create_test_character(room=room, key="TEST_BANK_CHAR")

        ctx.character = character
        ctx.room = room

        character.db.coins = 100
        character.db.bank_coins = 25

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")
        ctx.cmd("balance")
        ctx.cmd("deposit 40")
        ctx.snapshot("deposited")
        ctx.cmd("withdraw 15")
        ctx.snapshot("withdrawn")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["initial", "deposited", "withdrawn"]
        if labels != expected_labels:
            raise AssertionError(f"Bank snapshot labels drifted: expected {expected_labels}, got {labels}")

        deposit_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("initial"), ctx.get_snapshot_by_label("deposited"))
        withdraw_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("deposited"), ctx.get_snapshot_by_label("withdrawn"))

        if deposit_diff["character_coins_delta"] != -40 or deposit_diff["bank_coins_delta"] != 40:
            raise AssertionError(f"Bank deposit diff did not move funds correctly: {deposit_diff}")
        if withdraw_diff["character_coins_delta"] != 15 or withdraw_diff["bank_coins_delta"] != -15:
            raise AssertionError(f"Bank withdraw diff did not move funds correctly: {withdraw_diff}")

        if int(getattr(character.db, "coins", 0) or 0) != 75:
            raise AssertionError("Bank scenario ended with the wrong carried coin count.")
        if int(getattr(character.db, "bank_coins", 0) or 0) != 50:
            raise AssertionError("Bank scenario ended with the wrong bank coin count.")

        return {
            "commands": list(ctx.command_log),
            "deposit_diff": deposit_diff,
            "withdraw_diff": withdraw_diff,
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "output_log": list(ctx.output_log),
            "coins": int(getattr(character.db, "coins", 0) or 0),
            "bank_coins": int(getattr(character.db, "bank_coins", 0) or 0),
        }

    return run_scenario(scenario, seed=args.seed, mode="direct", auto_snapshot=False, name="bank")


def run_grave_recovery_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_GRAVE_ROOM")
        character = ctx.harness.create_test_character(room=room, key="TEST_GRAVE_CHAR")
        keepsake = ctx.harness.create_test_object(
            key="TEST_GRAVE_TOKEN",
            location=character,
            weight=1.0,
            item_value=12,
            value=12,
            desc="A token meant to survive corpse decay and grave recovery.",
        )

        ctx.character = character
        ctx.room = room

        character.set_favor(0)
        character.db.coins = 29

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("alive")
        corpse = ctx.direct(character.at_death)
        if not corpse:
            raise AssertionError("Grave-recovery scenario did not create a corpse.")
        ctx.harness.track_object(corpse)
        ctx.snapshot("dead")
        grave = ctx.direct(corpse.decay_to_grave)
        if not grave:
            raise AssertionError("Grave-recovery scenario did not decay the corpse into a grave.")
        ctx.harness.track_object(grave)
        ctx.snapshot("graved")
        ctx.cmd("depart grave")
        ctx.snapshot("departed")
        ctx.cmd("recover")
        ctx.snapshot("recovered")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["alive", "dead", "graved", "departed", "recovered"]
        if labels != expected_labels:
            raise AssertionError(f"Grave-recovery snapshot labels drifted: expected {expected_labels}, got {labels}")

        grave_decay_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("dead"), ctx.get_snapshot_by_label("graved"))
        depart_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("graved"), ctx.get_snapshot_by_label("departed"))
        recover_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("departed"), ctx.get_snapshot_by_label("recovered"))

        if grave.key not in grave_decay_diff["after_snapshot_created"]:
            raise AssertionError(f"Grave decay diff did not record grave creation: {grave_decay_diff}")
        if corpse.key not in grave_decay_diff["after_snapshot_deleted"]:
            raise AssertionError(f"Grave decay diff did not record corpse removal: {grave_decay_diff}")

        if not depart_diff["revived"]:
            raise AssertionError(f"Grave depart diff did not record revival: {depart_diff}")
        if depart_diff["inventory_added"] or depart_diff["character_coins_delta"] != 0:
            raise AssertionError(f"Grave depart unexpectedly restored belongings: {depart_diff}")

        if recover_diff["inventory_added"] != ["TEST_GRAVE_TOKEN"]:
            raise AssertionError(f"Grave recover diff did not restore the grave item: {recover_diff}")
        if recover_diff["character_coins_delta"] != 29:
            raise AssertionError(f"Grave recover diff did not restore grave coins: {recover_diff}")
        if grave.key not in recover_diff["after_snapshot_deleted"]:
            raise AssertionError(f"Grave recover diff did not record grave cleanup: {recover_diff}")

        if character.is_dead():
            raise AssertionError("Grave-recovery scenario ended with the character still dead.")
        if int(getattr(character.db, "coins", 0) or 0) != 29:
            raise AssertionError("Grave-recovery scenario ended with the wrong carried coin count.")
        if keepsake.location != character:
            raise AssertionError("Grave-recovery scenario ended without the grave item restored to the character.")

        return {
            "commands": list(ctx.command_log),
            "grave_decay_diff": grave_decay_diff,
            "depart_diff": depart_diff,
            "recover_diff": recover_diff,
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "output_log": list(ctx.output_log),
            "grave_key": getattr(grave, "key", None),
            "coins": int(getattr(character.db, "coins", 0) or 0),
        }

    return run_scenario(scenario, seed=args.seed, mode="direct", auto_snapshot=False, name="grave-recovery")


def run_onboarding_full_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object

    from systems import onboarding

    created_objects = []
    try:
        rooms = _get_or_create_tutorial_rooms(ObjectDB, create_object, created_objects)
        character = _create_test_onboarding_character(create_object, rooms, created_objects, onboarding)
        final_name = _default_test_name(args.name)
        results = []
        _apply_onboarding_identity(character, rooms, onboarding, results)

        character.move_to(rooms["Gear Rack Room"], quiet=True, use_destination=False)
        _equip_test_gear(character, create_object, created_objects)
        results.append({"step": "gear", "ok": "gear" in set(onboarding.ensure_onboarding_state(character).get("completed_steps") or []), "message": "wore starter gear"})

        character.move_to(rooms["Weapon Cage"], quiet=True, use_destination=False)
        weapon = _create_test_weapon(character, create_object, created_objects)
        onboarding.note_weapon_action(character, weapon)
        results.append({"step": "weapon", "ok": "weapon" in set(onboarding.ensure_onboarding_state(character).get("completed_steps") or []), "message": "wielded training weapon"})
        _run_finish_sequence(character, rooms, create_object, created_objects, onboarding, results, final_name)

        can_exit, exit_message = onboarding.can_exit_to_world(character)
        output = {
            "scenario": "onboarding_full",
            "name": final_name,
            "results": results,
            "can_exit": can_exit,
            "exit_message": exit_message,
            "tokens": int(onboarding.ensure_onboarding_state(character).get("tokens", 0) or 0),
            "completed_steps": list(onboarding.ensure_onboarding_state(character).get("completed_steps") or []),
            "all_valid": bool(can_exit) and all(result.get("ok") for result in results),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: onboarding_full")
            print(f"Name: {final_name}")
            print("")
            for result in results:
                print(f"[{ 'PASS' if result['ok'] else 'FAIL' }] {result['step']}: {result['message']}")
            print("")
            print(f"Completed Steps: {', '.join(output['completed_steps'])}")
            print(f"Tokens: {output['tokens']}")
            print(f"Exit Ready: {'PASS' if output['can_exit'] else 'FAIL'}")
            if exit_message:
                print(f"Exit Message: {exit_message}")
        return 0 if output["all_valid"] else 1
    finally:
        for name in reversed(created_objects):
            _cleanup_named_object(name)


def _run_onboarding_failure_case(args, case_name):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object

    from systems import onboarding

    created_objects = []
    try:
        rooms = _get_or_create_tutorial_rooms(ObjectDB, create_object, created_objects)
        character = _create_test_onboarding_character(create_object, rooms, created_objects, onboarding)
        final_name = _default_test_name(args.name)
        results = []
        _apply_onboarding_identity(character, rooms, onboarding, results)

        correction_ok = False
        objective = ""
        memory_moment_ok = False

        if case_name == "no_armor":
            character.move_to(rooms["Weapon Cage"], quiet=True, use_destination=False)
            weapon = _create_test_weapon(character, create_object, created_objects)
            blocked, _ = onboarding.note_weapon_action(character, weapon)
            correction_ok = (not blocked) and _has_pending_mentor_correction(onboarding, character)
            objective = onboarding.get_onboarding_objective(character)

            character.move_to(rooms["Gear Rack Room"], quiet=True, use_destination=False)
            _equip_test_gear(character, create_object, created_objects)
            results.append({"step": "gear", "ok": "gear" in set(onboarding.ensure_onboarding_state(character).get("completed_steps") or []), "message": objective})

            character.move_to(rooms["Weapon Cage"], quiet=True, use_destination=False)
            onboarding.note_weapon_action(character, weapon)
            results.append({"step": "weapon", "ok": "weapon" in set(onboarding.ensure_onboarding_state(character).get("completed_steps") or []), "message": "recovered after missing armor"})

        elif case_name == "no_attack":
            character.move_to(rooms["Gear Rack Room"], quiet=True, use_destination=False)
            _equip_test_gear(character, create_object, created_objects)
            character.move_to(rooms["Weapon Cage"], quiet=True, use_destination=False)
            weapon = _create_test_weapon(character, create_object, created_objects)
            onboarding.note_weapon_action(character, weapon)
            results.append({"step": "gear", "ok": True, "message": "wore starter gear"})
            results.append({"step": "weapon", "ok": True, "message": "wielded training weapon"})

            character.move_to(rooms["Training Yard"], quiet=True, use_destination=False)
            memory_moment_ok = onboarding.trigger_almost_failure_scene(character)
            correction_ok = memory_moment_ok and _has_recent_line(onboarding, character, "Stop listening. Start acting.")
            objective = onboarding.get_onboarding_objective(character)
            results.append({"step": "memory_moment", "ok": correction_ok, "message": "asserted Stop listening. Start acting."})

        elif case_name == "no_heal":
            character.move_to(rooms["Gear Rack Room"], quiet=True, use_destination=False)
            _equip_test_gear(character, create_object, created_objects)
            character.move_to(rooms["Weapon Cage"], quiet=True, use_destination=False)
            weapon = _create_test_weapon(character, create_object, created_objects)
            onboarding.note_weapon_action(character, weapon)
            character.move_to(rooms["Training Yard"], quiet=True, use_destination=False)
            goblin = create_object("typeclasses.npcs.NPC", key="diretest training goblin", location=rooms["Training Yard"], home=rooms["Training Yard"])
            goblin.db.is_npc = True
            goblin.db.is_tutorial_enemy = True
            goblin.db.onboarding_enemy_role = "training"
            goblin.db.hp = 0
            created_objects.append(goblin.key)
            onboarding.note_combat_start(character, goblin)
            onboarding.note_combat_win(character, goblin)
            character.move_to(rooms["Supply Shack"], quiet=True, use_destination=False)
            onboarding.note_hesitation(character, context="healing")
            correction_ok = _has_pending_mentor_correction(onboarding, character)
            objective = onboarding.get_onboarding_objective(character)
            results.append({"step": "combat", "ok": True, "message": "won training fight before delaying heal"})

        else:
            raise ValueError(f"Unknown onboarding failure case: {case_name}")

        _run_finish_sequence(character, rooms, create_object, created_objects, onboarding, results, final_name)
        can_exit, exit_message = onboarding.can_exit_to_world(character)
        output = {
            "scenario": f"onboarding_{case_name}",
            "name": final_name,
            "mentor_correction": correction_ok,
            "memory_moment": memory_moment_ok,
            "objective_after_failure": objective,
            "results": results,
            "can_exit": can_exit,
            "exit_message": exit_message,
            "all_valid": bool(correction_ok and objective and can_exit and all(result.get("ok") for result in results)),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"DireTest Scenario: onboarding_{case_name}")
            print(f"Name: {final_name}")
            print(f"Mentor Correction: {'PASS' if correction_ok else 'FAIL'}")
            print(f"Objective After Failure: {objective}")
            print("")
            for result in results:
                print(f"[{ 'PASS' if result['ok'] else 'FAIL' }] {result['step']}: {result['message']}")
            print("")
            print(f"Exit Ready: {'PASS' if can_exit else 'FAIL'}")
            if exit_message:
                print(f"Exit Message: {exit_message}")
        return 0 if output["all_valid"] else 1
    finally:
        for name in reversed(created_objects):
            _cleanup_named_object(name)


def run_onboarding_no_armor_scenario(args):
    return _run_onboarding_failure_case(args, "no_armor")


def run_onboarding_no_attack_scenario(args):
    return _run_onboarding_failure_case(args, "no_attack")


def run_onboarding_no_heal_scenario(args):
    return _run_onboarding_failure_case(args, "no_heal")


def _ensure_scenario_seed(args):
    seed = getattr(args, "seed", None)
    if seed is None:
        seed = int(time.time_ns() % 1000000000)
        print(f"DireTest seed: {seed}", file=sys.stderr)
    normalized = int(seed)
    args.seed = normalized
    set_seed(normalized)
    return normalized


def _build_run_id(args):
    scenario_name = str(getattr(args, "scenario_name", getattr(args, "command", "scenario")) or "scenario")
    return f"{scenario_name.replace(' ', '_').lower()}_direct_{int(args.seed)}"


def _is_runner_result(result):
    return isinstance(result, dict) and "artifact_dir" in result and "exit_code" in result


def _emit_runner_result(args, result):
    if bool(getattr(args, "json", False)):
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    scenario_result = dict(result.get("result", {}) or {})
    command_count = len(list(scenario_result.get("commands", []) or []))
    snapshot_count = int(scenario_result.get("snapshot_count", 0) or 0)

    print(f"DireTest Scenario: {str(getattr(args, 'scenario_name', 'scenario') or 'scenario')}")
    print(f"Seed: {int(result.get('seed', 0) or 0)}")
    print(f"Exit Code: {int(result.get('exit_code', 0))}")
    print(f"Artifact Dir: {result.get('artifact_dir')}")
    print(f"Commands Logged: {command_count}")
    print(f"Snapshots: {snapshot_count}")
    if result.get("traceback"):
        print("Traceback:")
        print(result.get("traceback"))


def _execute_cli_scenario(args):
    seed = _ensure_scenario_seed(args)
    traceback_text = ""
    exit_code = 1
    handler_result = None

    try:
        handler_result = args.handler(args)
        if _is_runner_result(handler_result):
            _emit_runner_result(args, handler_result)
            return int(handler_result.get("exit_code", 0))
        exit_code = int(handler_result)
        return exit_code
    except Exception:
        traceback_text = traceback.format_exc()
        raise
    finally:
        if _is_runner_result(handler_result):
            return
        write_artifacts(
            _build_run_id(args),
            {
                "scenario": {
                    "name": str(getattr(args, "scenario_name", "scenario") or "scenario"),
                    "mode": "direct",
                    "seed": seed,
                },
                "seed": seed,
                "command_log": [],
                "snapshots": [],
                "metrics": {
                    "exit_code": int(exit_code),
                },
                "traceback": traceback_text,
            },
        )


def build_parser():
    parser = argparse.ArgumentParser(prog="diretest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scenario_parser = subparsers.add_parser("scenario")
    scenario_subparsers = scenario_parser.add_subparsers(dest="scenario_name", required=True)

    race_balance_parser = scenario_subparsers.add_parser("race-balance")
    race_balance_parser.add_argument("--profession", default="commoner")
    race_balance_parser.add_argument("--sample-weight", type=float, default=80.0)
    race_balance_parser.add_argument("--base-xp", type=int, default=100)
    race_balance_parser.add_argument("--seed", type=int)
    race_balance_parser.add_argument("--json", action="store_true")
    race_balance_parser.set_defaults(handler=run_race_balance_scenario)

    movement_parser = scenario_subparsers.add_parser("movement")
    movement_parser.add_argument("--seed", type=int)
    movement_parser.add_argument("--json", action="store_true")
    movement_parser.set_defaults(handler=run_movement_scenario)

    inventory_parser = scenario_subparsers.add_parser("inventory")
    inventory_parser.add_argument("--seed", type=int)
    inventory_parser.add_argument("--json", action="store_true")
    inventory_parser.set_defaults(handler=run_inventory_scenario)

    combat_basic_parser = scenario_subparsers.add_parser("combat-basic")
    combat_basic_parser.add_argument("--seed", type=int)
    combat_basic_parser.add_argument("--json", action="store_true")
    combat_basic_parser.set_defaults(handler=run_combat_basic_scenario)

    death_loop_parser = scenario_subparsers.add_parser("death-loop")
    death_loop_parser.add_argument("--seed", type=int)
    death_loop_parser.add_argument("--json", action="store_true")
    death_loop_parser.set_defaults(handler=run_death_loop_scenario)

    economy_parser = scenario_subparsers.add_parser("economy")
    economy_parser.add_argument("--seed", type=int)
    economy_parser.add_argument("--json", action="store_true")
    economy_parser.set_defaults(handler=run_economy_scenario)

    bank_parser = scenario_subparsers.add_parser("bank")
    bank_parser.add_argument("--seed", type=int)
    bank_parser.add_argument("--json", action="store_true")
    bank_parser.set_defaults(handler=run_bank_scenario)

    grave_recovery_parser = scenario_subparsers.add_parser("grave-recovery")
    grave_recovery_parser.add_argument("--seed", type=int)
    grave_recovery_parser.add_argument("--json", action="store_true")
    grave_recovery_parser.set_defaults(handler=run_grave_recovery_scenario)

    onboarding_parser = scenario_subparsers.add_parser("onboarding_full")
    onboarding_parser.add_argument("--name", default="DireTestHero")
    onboarding_parser.add_argument("--seed", type=int)
    onboarding_parser.add_argument("--json", action="store_true")
    onboarding_parser.set_defaults(handler=run_onboarding_full_scenario)

    onboarding_no_armor_parser = scenario_subparsers.add_parser("onboarding_no_armor")
    onboarding_no_armor_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_armor_parser.add_argument("--seed", type=int)
    onboarding_no_armor_parser.add_argument("--json", action="store_true")
    onboarding_no_armor_parser.set_defaults(handler=run_onboarding_no_armor_scenario)

    onboarding_no_attack_parser = scenario_subparsers.add_parser("onboarding_no_attack")
    onboarding_no_attack_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_attack_parser.add_argument("--seed", type=int)
    onboarding_no_attack_parser.add_argument("--json", action="store_true")
    onboarding_no_attack_parser.set_defaults(handler=run_onboarding_no_attack_scenario)

    onboarding_no_heal_parser = scenario_subparsers.add_parser("onboarding_no_heal")
    onboarding_no_heal_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_heal_parser.add_argument("--seed", type=int)
    onboarding_no_heal_parser.add_argument("--json", action="store_true")
    onboarding_no_heal_parser.set_defaults(handler=run_onboarding_no_heal_scenario)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return _execute_cli_scenario(args)


if __name__ == "__main__":
    raise SystemExit(main())