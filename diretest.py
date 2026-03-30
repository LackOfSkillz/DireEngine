import argparse
import json
import os
import time


def _setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()

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


def build_parser():
    parser = argparse.ArgumentParser(prog="diretest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scenario_parser = subparsers.add_parser("scenario")
    scenario_subparsers = scenario_parser.add_subparsers(dest="scenario_name", required=True)

    race_balance_parser = scenario_subparsers.add_parser("race-balance")
    race_balance_parser.add_argument("--profession", default="commoner")
    race_balance_parser.add_argument("--sample-weight", type=float, default=80.0)
    race_balance_parser.add_argument("--base-xp", type=int, default=100)
    race_balance_parser.add_argument("--json", action="store_true")
    race_balance_parser.set_defaults(handler=run_race_balance_scenario)

    onboarding_parser = scenario_subparsers.add_parser("onboarding_full")
    onboarding_parser.add_argument("--name", default="DireTestHero")
    onboarding_parser.add_argument("--json", action="store_true")
    onboarding_parser.set_defaults(handler=run_onboarding_full_scenario)

    onboarding_no_armor_parser = scenario_subparsers.add_parser("onboarding_no_armor")
    onboarding_no_armor_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_armor_parser.add_argument("--json", action="store_true")
    onboarding_no_armor_parser.set_defaults(handler=run_onboarding_no_armor_scenario)

    onboarding_no_attack_parser = scenario_subparsers.add_parser("onboarding_no_attack")
    onboarding_no_attack_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_attack_parser.add_argument("--json", action="store_true")
    onboarding_no_attack_parser.set_defaults(handler=run_onboarding_no_attack_scenario)

    onboarding_no_heal_parser = scenario_subparsers.add_parser("onboarding_no_heal")
    onboarding_no_heal_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_heal_parser.add_argument("--json", action="store_true")
    onboarding_no_heal_parser.set_defaults(handler=run_onboarding_no_heal_scenario)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())