import argparse
from collections import Counter
from collections.abc import Mapping
import json
import os
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

from tools.diretest.core.diff import diff_snapshots as build_snapshot_diff
from tools.diretest.core.artifacts import write_artifacts
from tools.diretest.core.baselines import METRIC_SPECS, compare_named_baseline, load_named_baseline, save_named_baseline
from tools.diretest.core.failures import build_failure_summary
from tools.diretest.core.runner import run_scenario
from tools.diretest.core.seed import set_seed

SCENARIO_REGISTRY = {}


def register_scenario(name, metadata=None, aliases=None, **extra_metadata):
    scenario_name = str(name or "").strip()
    if not scenario_name:
        raise ValueError("Scenario name cannot be empty.")

    scenario_aliases = [str(alias or "").strip() for alias in list(aliases or []) if str(alias or "").strip()]
    scenario_metadata = dict(metadata or {})
    scenario_metadata.update(dict(extra_metadata or {}))

    def decorator(func):
        func.diretest_metadata = dict(getattr(func, "diretest_metadata", {}) or {}) | scenario_metadata
        func.diretest_scenario_name = scenario_name
        func.diretest_aliases = list(scenario_aliases)
        SCENARIO_REGISTRY[scenario_name] = func
        for alias in scenario_aliases:
            SCENARIO_REGISTRY[alias] = func
        return func

    return decorator


def get_scenario_handler(name):
    return SCENARIO_REGISTRY.get(str(name or "").strip())


def _get_registered_scenario(name):
    return get_scenario_handler(name)


def _load_json_file(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_snapshot_input(raw):
    if not raw:
        return None

    path_text = raw
    label = None
    if "::" in raw:
        path_text, label = raw.split("::", 1)

    payload = _load_json_file(path_text)
    if isinstance(payload, list):
        if label is None:
            if len(payload) == 1:
                payload = payload[0]
            else:
                raise ValueError("Snapshot list input requires a ::label selector when multiple entries exist.")
        else:
            for entry in payload:
                if str((entry or {}).get("label", "") or "") == label:
                    return entry
            raise KeyError(f"Snapshot label not found: {label}")

    if isinstance(payload, dict) and "data" in payload:
        return payload
    if isinstance(payload, dict):
        return {"label": str(label or payload.get("label", "") or Path(path_text).stem), "data": payload}
    raise TypeError("Snapshot file must contain a snapshot entry, snapshot data dict, or snapshot-entry list.")


def _load_snapshot_reference(raw):
    snapshot = _load_snapshot_input(raw)
    if snapshot is None:
        raise ValueError("Snapshot reference is required.")
    return snapshot


def _parse_seed_text(seed_text):
    raw = str(seed_text or "").strip()
    if raw.startswith("seed="):
        raw = raw.split("=", 1)[1]
    return int(raw or 0)


def _write_cli_failure_artifact(scenario_name, seed, failure_type, message, mode="direct", traceback_text=""):
    artifact_dir = write_artifacts(
        f"{str(scenario_name or 'scenario').replace(' ', '_').lower()}_{mode}_{int(seed or 0)}",
        {
            "scenario": {
                "name": str(scenario_name or "scenario"),
                "mode": str(mode or "direct"),
                "seed": int(seed or 0),
                "started_at": time.time(),
            },
            "seed": int(seed or 0),
            "command_log": [],
            "snapshots": [],
            "diffs": [],
            "metrics": {
                "exit_code": 1,
                "failure_type": str(failure_type or "scenario_failure"),
            },
            "failure_summary": build_failure_summary(
                failure_type=failure_type,
                message=message,
                scenario=str(scenario_name or "scenario"),
                seed=seed,
                mode=mode,
            ),
            "traceback": str(traceback_text or ""),
        },
    )
    return str(artifact_dir)


def _load_artifact_metadata(artifact_path):
    root = Path(artifact_path)
    scenario_payload = _load_json_file(root / "scenario.json")
    seed_value = _parse_seed_text((root / "seed.txt").read_text(encoding="utf-8"))
    return {
        "path": str(root),
        "scenario": str((scenario_payload or {}).get("name", "") or ""),
        "seed": int(seed_value),
        "mode": str((scenario_payload or {}).get("mode", "direct") or "direct"),
    }


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


def _print_lines(lines):
    for line in list(lines or []):
        print(line)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _format_ms_value(value):
    numeric = _safe_float(value, 0.0)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.1f}".rstrip("0").rstrip(".")


def _build_lag_summary_lines(metrics):
    lag = dict((metrics or {}).get("lag", {}) or {})
    status = str(lag.get("status", "ok") or "ok")
    if status == "ok":
        return []
    return [
        "Lag Summary:",
        f"  avg: {_format_ms_value(lag.get('avg_ms', 0.0))}ms",
        f"  max: {_format_ms_value(lag.get('max_ms', 0.0))}ms",
        f"  spikes: {int(lag.get('spike_count', 0) or 0)}",
        f"  status: {status.upper()}",
    ]


def _build_replay_lag_lines(metrics):
    comparison = dict((metrics or {}).get("replay_lag_comparison", {}) or {})
    delta = dict(comparison.get("delta", {}) or {})
    if not comparison:
        return []
    return [
        "Replay Lag Compare:",
        f"  status: {comparison.get('original_status', 'ok')} -> {comparison.get('current_status', 'ok')}",
        f"  avg delta: {_format_ms_value(delta.get('avg_ms', 0.0))}ms",
        f"  max delta: {_format_ms_value(delta.get('max_ms', 0.0))}ms",
        f"  spike delta: {int(round(_safe_float(delta.get('spike_count', 0.0), 0.0)))}",
    ]


def _build_performance_summary_line(metrics):
    payload = dict(metrics or {})
    command_count = int((payload.get("commands", {}) or {}).get("count", payload.get("command_count", 0)) or 0)
    scheduler_events = int((payload.get("scheduler", {}) or {}).get("events", payload.get("scheduler_events", 0)) or 0)
    max_command_time = _safe_float((payload.get("commands", {}) or {}).get("max_ms", payload.get("max_command_time_ms", 0.0)), 0.0)
    if not command_count and not scheduler_events and max_command_time <= 0.0:
        return ""
    return f"commands: {command_count} | scheduler: {scheduler_events} | max_cmd: {_format_ms_value(max_command_time)}ms"


def _build_benchmark_summary_lines(result_payload):
    benchmark = dict((result_payload or {}).get("benchmark", {}) or {})
    if not benchmark:
        return []
    return [
        "Benchmark Summary:",
        f"  legacy cmd: {_format_ms_value(benchmark.get('legacy_command_ms', 0.0))}ms",
        f"  scoped cmd: {_format_ms_value(benchmark.get('scoped_command_ms', 0.0))}ms",
        f"  cmd delta: {_format_ms_value(benchmark.get('command_delta_ms', 0.0))}ms",
        f"  legacy targets: {int(benchmark.get('legacy_target_count', 0) or 0)}",
        f"  scoped targets: {int(benchmark.get('scoped_target_count', 0) or 0)}",
        f"  target delta: {int(benchmark.get('target_delta', 0) or 0)}",
    ]


def _format_onboarding_output(output):
    lines = [
        "DireTest Scenario: onboarding_full",
        f"Name: {output.get('name', '')}",
        "",
    ]
    for result in list(output.get("results", []) or []):
        status = "PASS" if result.get("ok") else "FAIL"
        lines.append(f"[{status}] {result.get('step')}: {result.get('message')}")
    lines.extend(
        [
            "",
            f"Completed Steps: {', '.join(list(output.get('completed_steps', []) or []))}",
            f"Tokens: {int(output.get('tokens', 0) or 0)}",
            f"Exit Ready: {'PASS' if output.get('can_exit') else 'FAIL'}",
        ]
    )
    exit_message = str(output.get("exit_message", "") or "")
    if exit_message:
        lines.append(f"Exit Message: {exit_message}")
    duration_ms = int(output.get("duration_ms", 0) or 0)
    if duration_ms:
        lines.append(f"Duration Ms: {duration_ms}")
    return lines


def _emit_onboarding_output(output, as_json=False):
    if as_json:
        print(json.dumps(output, indent=2, sort_keys=True))
        return
    _print_lines(_format_onboarding_output(output))


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


@register_scenario("race-balance")
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


def _build_race_descriptor_snapshot(character):
    return {
        "name": getattr(character, "key", None),
        "race": getattr(getattr(character, "db", None), "race", None),
        "age": getattr(getattr(character, "db", None), "age", None),
        "age_bracket": character.get_age_bracket(),
        "descriptor": character.get_race_descriptor(),
        "appearance": character.return_appearance(character),
    }


@register_scenario("race-descriptor-basic")
def run_race_descriptor_basic_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_race_descriptor_basic")
    character = None
    try:
        character = create_race_test_character(room, "volgrin", key="diretest_race_descriptor_basic")
        character.db.age = 25
        output = _build_race_descriptor_snapshot(character)
        output["scenario"] = "race-descriptor-basic"
        output["ok"] = output["age_bracket"] == "adult" and "volgrin" in str(output["descriptor"] or "").lower()
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: race-descriptor-basic")
            print(f"Descriptor: {output['descriptor']}")
            print(f"Age Bracket: {output['age_bracket']}")
            print(f"Appearance Header: {str(output['appearance']).splitlines()[0]}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario("race-descriptor-age-shift")
def run_race_descriptor_age_shift_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_race_descriptor_age_shift")
    character = None
    try:
        character = create_race_test_character(room, "felari", key="diretest_race_descriptor_age_shift")
        character.db.age = 10
        child_snapshot = _build_race_descriptor_snapshot(character)
        character.db.age = 70
        elder_snapshot = _build_race_descriptor_snapshot(character)
        output = {
            "scenario": "race-descriptor-age-shift",
            "race": character.get_race(),
            "child": child_snapshot,
            "elder": elder_snapshot,
            "ok": child_snapshot["age_bracket"] == "child"
            and elder_snapshot["age_bracket"] == "elder"
            and child_snapshot["descriptor"] != elder_snapshot["descriptor"],
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: race-descriptor-age-shift")
            print(f"Child Descriptor: {child_snapshot['descriptor']}")
            print(f"Elder Descriptor: {elder_snapshot['descriptor']}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario("race-descriptor-no-race")
def run_race_descriptor_no_race_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    character_name = f"diretest_race_descriptor_no_race_{str(int(time.time() * 1000))[-6:]}"
    room_name, room = _create_temp_room("diretest_race_descriptor_no_race")
    character = None
    try:
        character = create_object("typeclasses.characters.Character", key=character_name, location=room, home=room)
        character.db.age = 25
        character.db.race = "unknown_race"
        output = {
            "scenario": "race-descriptor-no-race",
            "descriptor": character.get_race_descriptor(),
            "race_reference": character.get_race_reference(),
        }
        output["ok"] = output["descriptor"] == "an unidentified figure" and output["race_reference"] == "an unidentified figure"
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: race-descriptor-no-race")
            print(f"Descriptor: {output['descriptor']}")
            print(f"Race Reference: {output['race_reference']}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


def _capture_object_messages(*objects):
    captured = {}
    originals = {}

    for obj in objects:
        if not obj:
            continue
        captured[obj] = []
        originals[obj] = obj.msg

        def _build_capture(target):
            def _capture(text=None, **kwargs):
                payload = text
                if isinstance(payload, tuple) and payload:
                    payload = payload[0]
                captured[target].append(str(payload or ""))
                return None

            return _capture

        obj.msg = _build_capture(obj)

    return captured, originals


def _restore_object_messages(originals):
    for obj, original in dict(originals or {}).items():
        obj.msg = original


@register_scenario("language-basic")
def run_language_basic_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_basic")
    character = None
    try:
        character = create_race_test_character(room, "saurathi", key="diretest_language_basic")
        known_languages = list(character.get_known_languages())
        output = {
            "scenario": "language-basic",
            "race": character.get_race(),
            "known_languages": known_languages,
            "active_language": character.get_active_language(),
            "ok": set(known_languages) == {"common", "saurathi"} and character.get_active_language() == "common",
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-basic")
            print(f"Known Languages: {', '.join(known_languages)}")
            print(f"Active Language: {output['active_language']}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario("language-switch")
def run_language_switch_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_switch")
    character = None
    try:
        character = create_race_test_character(room, "lunari", key="diretest_language_switch")
        changed = character.set_language("lunari")
        output = {
            "scenario": "language-switch",
            "changed": bool(changed),
            "active_language": character.get_active_language(),
            "ok": bool(changed) and character.get_active_language() == "lunari",
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-switch")
            print(f"Active Language: {output['active_language']}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario("language-accent")
def run_language_accent_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_accent")
    speaker = None
    observer = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_language_speaker")
        observer = create_race_test_character(room, "human", key="diretest_language_observer")
        speaker.set_language("saurathi")

        captured, originals = _capture_object_messages(speaker, observer)
        speaker.execute_cmd("say sail south")
        speaker_messages = list(captured.get(speaker) or [])
        observer_messages = list(captured.get(observer) or [])
        transformed = any("ssail ssouth" in message.lower() for message in speaker_messages + observer_messages)
        output = {
            "scenario": "language-accent",
            "speaker_messages": speaker_messages,
            "observer_messages": observer_messages,
            "ok": transformed,
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-accent")
            if speaker_messages:
                print(f"Speaker Heard: {speaker_messages[0]}")
            if observer_messages:
                print(f"Observer Heard: {observer_messages[0]}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, observer):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("language-invalid")
def run_language_invalid_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

def run_e2e_full_lifecycle_all_races_scenario(args):
    _setup_django()

    from world.races import TEST_RACES

    results = []
    failures = []
    for index, race in enumerate(TEST_RACES):
        print(f"\n=== E2E Lifecycle: {race} ===")
        try:
            result = _run_e2e_full_lifecycle_for_race(race, index)
            results.append(result)
            print(f"[{race}] onboarding complete")
            print(f"[{race}] death triggered")
            print(f"[{race}] resurrected")
            print(f"[{race}] entered live game")
        except Exception as exc:
            failures.append({"race": str(race), "error": str(exc)})
            results.append({"race": str(race), "ok": False, "error": str(exc)})

    output = {
        "scenario": "e2e-full-lifecycle-all-races",
        "races": list(TEST_RACES),
        "results": results,
        "failures": failures,
        "ok": not failures,
    }

    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print("\nDireTest Scenario: e2e-full-lifecycle-all-races")
        print(f"Race Count: {len(TEST_RACES)}")
        for result in results:
            status = "PASS" if result.get("ok") else "FAIL"
            detail = result.get("landing_room") or result.get("error") or "ok"
            print(f"[{status}] {result.get('race')}: {detail}")
        print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
    return 0 if output["ok"] else 1
def run_language_comprehension_none_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_comprehension_none")
    speaker = None
    listener = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_comp_none_speaker")
        listener = create_race_test_character(room, "human", key="diretest_comp_none_listener")
        speaker.set_language("saurathi")

        captured, originals = _capture_object_messages(listener)
        speaker.execute_cmd("say sail south")
        messages = list(captured.get(listener) or [])
        perceived = messages[0] if messages else ""
        output = {
            "scenario": "language-comprehension-none",
            "listener_message": perceived,
            "ok": "ssail ssouth" not in perceived.lower() and any(symbol in perceived for symbol in ("?", "*", "#")),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-comprehension-none")
            print(f"Listener Heard: {perceived}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("language-comprehension-full")
def run_language_comprehension_full_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_comprehension_full")
    speaker = None
    listener = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_comp_full_speaker")
        listener = create_race_test_character(room, "saurathi", key="diretest_comp_full_listener")
        speaker.set_language("saurathi")

        captured, originals = _capture_object_messages(listener)
        speaker.execute_cmd("say sail south")
        messages = list(captured.get(listener) or [])
        perceived = messages[0] if messages else ""
        output = {
            "scenario": "language-comprehension-full",
            "listener_message": perceived,
            "ok": "ssail ssouth" in perceived.lower(),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-comprehension-full")
            print(f"Listener Heard: {perceived}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("language-comprehension-partial")
def run_language_comprehension_partial_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_comprehension_partial")
    speaker = None
    listener = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_comp_partial_speaker")
        listener = create_race_test_character(room, "human", key="diretest_comp_partial_listener")
        listener.db.language_comprehension_overrides = {"saurathi": 0.5}
        speaker.set_language("saurathi")

        captured, originals = _capture_object_messages(listener)
        speaker.execute_cmd("say sail south quickly")
        messages = list(captured.get(listener) or [])
        perceived = messages[0] if messages else ""
        lowered = perceived.lower()
        output = {
            "scenario": "language-comprehension-partial",
            "listener_message": perceived,
            "ok": "..." in perceived and any(word in lowered for word in ("ssail", "ssouth", "quickly")),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-comprehension-partial")
            print(f"Listener Heard: {perceived}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("language-learning-basic")
def run_language_learning_basic_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_learning_basic")
    speaker = None
    listener = None
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_learning_basic_speaker")
        listener = create_race_test_character(room, "human", key="diretest_learning_basic_listener")
        speaker.set_language("saurathi")

        before = listener.get_language_proficiency("saurathi")
        for _ in range(3):
            speaker.execute_cmd("say sail south")
        after = listener.get_language_proficiency("saurathi")
        output = {
            "scenario": "language-learning-basic",
            "before": before,
            "after": after,
            "ok": round(before, 3) == 0.0 and round(after, 3) == 0.03,
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-learning-basic")
            print(f"Before: {before:.3f}")
            print(f"After: {after:.3f}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        for obj in (speaker, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("language-learning-cap")
def run_language_learning_cap_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_learning_cap")
    character = None
    try:
        character = create_race_test_character(room, "human", key="diretest_learning_cap")
        character.db.languages = {"common": 1.0, "saurathi": 0.99}
        result = character.learn_language("saurathi", 0.5)
        output = {
            "scenario": "language-learning-cap",
            "proficiency": result,
            "ok": round(result, 3) == 1.0,
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-learning-cap")
            print(f"Proficiency: {result:.3f}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario("language-learning-comprehension")
def run_language_learning_comprehension_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_learning_comprehension")
    speaker = None
    listener = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_learning_comp_speaker")
        listener = create_race_test_character(room, "human", key="diretest_learning_comp_listener")
        speaker.set_language("saurathi")

        captured, originals = _capture_object_messages(listener)
        speaker.execute_cmd("say sail south quickly")
        initial_message = (captured.get(listener) or [""])[-1]
        captured[listener].clear()

        for _ in range(20):
            speaker.execute_cmd("say sail south quickly")

        improved_message = (captured.get(listener) or [""])[-1]
        lowered = improved_message.lower()
        output = {
            "scenario": "language-learning-comprehension",
            "initial_message": initial_message,
            "improved_message": improved_message,
            "proficiency": listener.get_language_proficiency("saurathi"),
            "ok": any(symbol in initial_message for symbol in ("?", "*", "#"))
            and "..." in improved_message
            and any(word in lowered for word in ("ssail", "ssouth", "quickly")),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-learning-comprehension")
            print(f"Initial Heard: {initial_message}")
            print(f"Improved Heard: {improved_message}")
            print(f"Proficiency: {output['proficiency']:.3f}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("language-learning-eavesdrop")
def run_language_learning_eavesdrop_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_language_learning_eavesdrop")
    speaker = None
    target = None
    listener = None
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_learning_eaves_speaker")
        target = create_race_test_character(room, "human", key="diretest_learning_eaves_target")
        listener = create_race_test_character(room, "human", key="diretest_learning_eaves_listener")
        speaker.set_language("saurathi")

        for _ in range(3):
            speaker.execute_cmd(f"whisper {target.key} = sail south")

        target_proficiency = target.get_language_proficiency("saurathi")
        listener_proficiency = listener.get_language_proficiency("saurathi")
        output = {
            "scenario": "language-learning-eavesdrop",
            "target_proficiency": target_proficiency,
            "listener_proficiency": listener_proficiency,
            "ok": round(target_proficiency, 3) == 0.03 and round(listener_proficiency, 3) == 0.015,
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: language-learning-eavesdrop")
            print(f"Target Proficiency: {target_proficiency:.3f}")
            print(f"Listener Proficiency: {listener_proficiency:.3f}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        for obj in (speaker, target, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("whisper-basic")
def run_whisper_basic_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_whisper_basic")
    speaker = None
    target = None
    bystander = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "human", key="diretest_whisper_speaker")
        target = create_race_test_character(room, "human", key="diretest_whisper_target")
        bystander = create_race_test_character(room, "human", key="diretest_whisper_bystander")

        captured, originals = _capture_object_messages(speaker, target, bystander)
        speaker.execute_cmd(f"whisper {target.key} = keep moving")
        speaker_messages = list(captured.get(speaker) or [])
        target_messages = list(captured.get(target) or [])
        bystander_messages = list(captured.get(bystander) or [])
        output = {
            "scenario": "whisper-basic",
            "speaker_messages": speaker_messages,
            "target_messages": target_messages,
            "bystander_messages": bystander_messages,
            "ok": bool(target_messages)
            and all("whispers to you" in message.lower() for message in target_messages)
            and all("you overhear" in message.lower() for message in bystander_messages),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: whisper-basic")
            if speaker_messages:
                print(f"Speaker Heard: {speaker_messages[0]}")
            if target_messages:
                print(f"Target Heard: {target_messages[0]}")
            print(f"Bystander Messages: {len(bystander_messages)}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, target, bystander):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("whisper-language")
def run_whisper_language_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_whisper_language")
    speaker = None
    target = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_whisper_lang_speaker")
        target = create_race_test_character(room, "human", key="diretest_whisper_lang_target")
        speaker.set_language("saurathi")

        captured, originals = _capture_object_messages(target)
        speaker.execute_cmd(f"whisper {target.key} = sail south")
        target_messages = list(captured.get(target) or [])
        heard = target_messages[0] if target_messages else ""
        output = {
            "scenario": "whisper-language",
            "target_message": heard,
            "ok": "ssail ssouth" not in heard.lower() and any(symbol in heard for symbol in ("?", "*", "#")),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: whisper-language")
            print(f"Target Heard: {heard}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("whisper-comprehension")
def run_whisper_comprehension_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_whisper_comprehension")
    speaker = None
    target = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_whisper_comp_speaker")
        target = create_race_test_character(room, "saurathi", key="diretest_whisper_comp_target")
        speaker.set_language("saurathi")

        captured, originals = _capture_object_messages(target)
        speaker.execute_cmd(f"whisper {target.key} = sail south")
        target_messages = list(captured.get(target) or [])
        heard = target_messages[0] if target_messages else ""
        output = {
            "scenario": "whisper-comprehension",
            "target_message": heard,
            "ok": "ssail ssouth" in heard.lower(),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: whisper-comprehension")
            print(f"Target Heard: {heard}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("whisper-invalid")
def run_whisper_invalid_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_whisper_invalid")
    character = None
    captured = {}
    originals = {}
    try:
        character = create_race_test_character(room, "human", key="diretest_whisper_invalid")
        captured, originals = _capture_object_messages(character)
        character.execute_cmd("whisper")
        messages = list(captured.get(character) or [])
        output = {
            "scenario": "whisper-invalid",
            "messages": messages,
            "ok": any("usage: whisper <target> = <message>" in message.lower() for message in messages),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: whisper-invalid")
            if messages:
                print(f"Message: {messages[0]}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario("eavesdrop-basic")
def run_eavesdrop_basic_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_eavesdrop_basic")
    speaker = None
    target = None
    listener = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "human", key="diretest_eavesdrop_speaker")
        target = create_race_test_character(room, "human", key="diretest_eavesdrop_target")
        listener = create_race_test_character(room, "human", key="diretest_eavesdrop_listener")

        captured, originals = _capture_object_messages(listener)
        speaker.execute_cmd(f"whisper {target.key} = keep moving")
        messages = list(captured.get(listener) or [])
        heard = messages[0] if messages else ""
        output = {
            "scenario": "eavesdrop-basic",
            "listener_message": heard,
            "ok": bool(messages) and "overhear" in heard.lower(),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: eavesdrop-basic")
            print(f"Listener Heard: {heard}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, target, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("eavesdrop-none")
def run_eavesdrop_none_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object
    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_eavesdrop_none")
    remote_room_name, remote_room = _create_temp_room("diretest_eavesdrop_none_remote")
    speaker = None
    target = None
    listener = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "human", key="diretest_eavesdrop_none_speaker")
        target = create_race_test_character(room, "human", key="diretest_eavesdrop_none_target")
        listener = create_race_test_character(remote_room, "human", key="diretest_eavesdrop_none_listener")

        captured, originals = _capture_object_messages(listener)
        speaker.execute_cmd(f"whisper {target.key} = keep moving")
        messages = list(captured.get(listener) or [])
        output = {
            "scenario": "eavesdrop-none",
            "listener_messages": messages,
            "ok": not messages,
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: eavesdrop-none")
            print(f"Listener Messages: {len(messages)}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, target, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(remote_room_name)


@register_scenario("eavesdrop-degraded")
def run_eavesdrop_degraded_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_eavesdrop_degraded")
    speaker = None
    target = None
    listener = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "human", key="diretest_eavesdrop_deg_speaker")
        target = create_race_test_character(room, "human", key="diretest_eavesdrop_deg_target")
        listener = create_race_test_character(room, "human", key="diretest_eavesdrop_deg_listener")

        captured, originals = _capture_object_messages(listener)
        speaker.execute_cmd(f"whisper {target.key} = keep moving quickly")
        messages = list(captured.get(listener) or [])
        heard = messages[0] if messages else ""
        lowered = heard.lower()
        output = {
            "scenario": "eavesdrop-degraded",
            "listener_message": heard,
            "ok": "keep moving quickly" not in lowered and "..." in heard,
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: eavesdrop-degraded")
            print(f"Listener Heard: {heard}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, target, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("eavesdrop-comprehension")
def run_eavesdrop_comprehension_scenario(args):
    _setup_django()

    from utils.diretest_race import create_race_test_character

    room_name, room = _create_temp_room("diretest_eavesdrop_comprehension")
    speaker = None
    target = None
    listener = None
    captured = {}
    originals = {}
    try:
        speaker = create_race_test_character(room, "saurathi", key="diretest_eavesdrop_comp_speaker")
        target = create_race_test_character(room, "saurathi", key="diretest_eavesdrop_comp_target")
        listener = create_race_test_character(room, "human", key="diretest_eavesdrop_comp_listener")
        speaker.set_language("saurathi")

        captured, originals = _capture_object_messages(listener)
        speaker.execute_cmd(f"whisper {target.key} = sail south quickly")
        messages = list(captured.get(listener) or [])
        heard = messages[0] if messages else ""
        lowered = heard.lower()
        output = {
            "scenario": "eavesdrop-comprehension",
            "listener_message": heard,
            "ok": bool(messages) and "ssail ssouth quickly" not in lowered and ("..." in heard or any(symbol in heard for symbol in ("?", "*", "#"))),
        }
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: eavesdrop-comprehension")
            print(f"Listener Heard: {heard}")
            print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
        return 0 if output["ok"] else 1
    finally:
        _restore_object_messages(originals)
        for obj in (speaker, target, listener):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


def _build_runner_namespace(seed, as_json=False, **extra):
    payload = {"seed": int(seed), "json": bool(as_json), "check_lag": False, "repro_artifact_path": None}
    payload.update(extra)
    return argparse.Namespace(**payload)


def _run_registered_scenario(args, scenario_func, *, auto_snapshot=False, name=None, mode="direct", scenario_metadata=None):
    scenario_metadata = dict(scenario_metadata or getattr(scenario_func, "diretest_metadata", {}) or {})
    fail_on_critical_lag = bool(scenario_metadata.get("fail_on_critical_lag", True))
    if not fail_on_critical_lag and not str(scenario_metadata.get("lag_policy_reason", "") or "").strip():
        raise ValueError(f"DireTest scenario '{name or getattr(scenario_func, 'diretest_scenario_name', 'scenario')}' disables critical-lag failure without a metadata reason.")
    return run_scenario(
        scenario_func,
        seed=args.seed,
        mode=mode,
        auto_snapshot=auto_snapshot,
        name=name,
        check_lag=bool(getattr(args, "check_lag", False)),
        compare_lag_artifact_path=getattr(args, "repro_artifact_path", None),
        fail_on_critical_lag=fail_on_critical_lag,
        scenario_metadata=scenario_metadata,
    )
    
@register_scenario("thief-counterplay")
def run_thief_counterplay_scenario(args):
    _setup_django()

    from tests.scenarios.thief_counterplay import scenario as counterplay_scenario

    return _run_registered_scenario(args, counterplay_scenario, name="thief-counterplay", mode="command")


@register_scenario("thief-burglary-justice")
def run_thief_burglary_justice_scenario(args):
    _setup_django()

    from tests.scenarios.thief_burglary_justice import scenario as burglary_justice_scenario

    return _run_registered_scenario(args, burglary_justice_scenario, name="thief-burglary-justice", mode="command")


@register_scenario("justice-arrest-basic")
def run_justice_arrest_basic_scenario(args):
    _setup_django()

    from tests.scenarios.justice_arrest_basic import scenario as justice_arrest_basic_scenario

    return _run_registered_scenario(args, justice_arrest_basic_scenario, name="justice-arrest-basic", mode="command")


@register_scenario("justice-enforcement-outcomes")
def run_justice_enforcement_outcomes_scenario(args):
    _setup_django()

    from tests.scenarios.justice_enforcement_outcomes import scenario as justice_enforcement_outcomes_scenario

    return _run_registered_scenario(args, justice_enforcement_outcomes_scenario, name="justice-enforcement-outcomes", mode="command")


@register_scenario("justice-guardhouse-flow")
def run_justice_guardhouse_flow_scenario(args):
    _setup_django()

    from tests.scenarios.justice_guardhouse_flow import scenario as justice_guardhouse_flow_scenario

    return _run_registered_scenario(args, justice_guardhouse_flow_scenario, name="justice-guardhouse-flow", mode="command")


@register_scenario("thief-caught-vs-uncaught")
def run_thief_caught_vs_uncaught_scenario(args):
    _setup_django()

    from tests.scenarios.thief_caught_vs_uncaught import scenario as thief_caught_vs_uncaught_scenario

    return _run_registered_scenario(args, thief_caught_vs_uncaught_scenario, name="thief-caught-vs-uncaught", mode="command")


@register_scenario("canon-seed-validation")
def run_canon_seed_validation_scenario(args):
    _setup_django()

    from tests.scenarios.canon_seed_validation import scenario as canon_seed_validation_scenario

    return _run_registered_scenario(args, canon_seed_validation_scenario, name="canon-seed-validation", mode="command")


@register_scenario("guard-ai-basic")
def run_guard_ai_basic_scenario(args):
    _setup_django()

    from tests.scenarios.guard_ai_basic import scenario as guard_ai_basic_scenario

    return _run_registered_scenario(args, guard_ai_basic_scenario, name="guard-ai-basic", mode="command")


def _run_interest_renew_dual_mode_benchmark(ctx):
    from commands.cmd_renew import CmdRenew
    from world.systems.engine_flags import set_flag
    from world.systems.interest import clear_subject_interest, sync_subject_interest
    from world.systems.metrics import snapshot_metrics

    room_a = ctx.harness.create_test_room(key="TEST_INTEREST_RENEW_A")
    room_b = ctx.harness.create_test_room(key="TEST_INTEREST_RENEW_B")
    room_c = ctx.harness.create_test_room(key="TEST_INTEREST_RENEW_C")
    ctx.harness.create_test_exit(room_a, room_b, "east", aliases=["e"])
    ctx.harness.create_test_exit(room_b, room_a, "west", aliases=["w"])
    ctx.harness.create_test_exit(room_b, room_c, "east", aliases=["e2"])
    ctx.harness.create_test_exit(room_c, room_b, "west", aliases=["w2"])

    caller = ctx.harness.create_test_character(room=room_a, key="TEST_INTEREST_RENEW_CALLER")
    ctx.character = caller
    ctx.room = room_a
    caller.db.renewed = False
    caller.renew_state = lambda target=caller: setattr(target.db, "renewed", True)

    local_targets = []
    nearby_targets = []
    far_targets = []

    for index in range(12):
        target = ctx.harness.create_test_object(key=f"TEST_RENEW_LOCAL_{index}", location=room_a)
        target.db.renewed = False
        target.renew_state = lambda target=target: setattr(target.db, "renewed", True)
        local_targets.append(target)
    for index in range(12):
        target = ctx.harness.create_test_object(key=f"TEST_RENEW_NEARBY_{index}", location=room_b)
        target.db.renewed = False
        target.renew_state = lambda target=target: setattr(target.db, "renewed", True)
        nearby_targets.append(target)
    for index in range(120):
        target = ctx.harness.create_test_object(key=f"TEST_RENEW_FAR_{index}", location=room_c)
        target.db.renewed = False
        target.renew_state = lambda target=target: setattr(target.db, "renewed", True)
        far_targets.append(target)

    all_targets = [caller, *local_targets, *nearby_targets, *far_targets]

    def run_renew_all():
        command = CmdRenew()
        command.caller = caller
        command.args = "all"
        command._is_admin = lambda: True
        command._get_renewable_global_targets = lambda: (list(all_targets), len(all_targets))
        command.func()

    def reset_renewed(targets):
        for target in list(targets or []):
            target.db.renewed = False

    for target in all_targets:
        if hasattr(target, "db"):
            target.db.renewed = False

    set_flag("interest_activation", False, actor="diretest-benchmark")
    ctx.direct(run_renew_all)
    legacy_command_ms = float(((ctx.metrics or {}).get("command_timing_entries", []) or [])[-1].get("ms", 0.0) or 0.0)
    legacy_renewed = [target.key for target in all_targets if bool(getattr(getattr(target, "db", None), "renewed", False))]

    reset_renewed(all_targets)
    set_flag("interest_activation", True, actor="diretest-benchmark")
    clear_subject_interest(caller)
    sync_subject_interest(caller)
    ctx.direct(run_renew_all)
    scoped_command_ms = float(((ctx.metrics or {}).get("command_timing_entries", []) or [])[-1].get("ms", 0.0) or 0.0)
    scoped_renewed = [target.key for target in all_targets if bool(getattr(getattr(target, "db", None), "renewed", False))]

    runtime_metrics = dict(snapshot_metrics() or {})
    target_select_entries = list(dict((runtime_metrics.get("events", {}) or {}).get("command.renew.target_select", {}) or {}).get("entries", []) or [])
    execute_entries = list(dict((runtime_metrics.get("events", {}) or {}).get("command.renew.execute", {}) or {}).get("entries", []) or [])

    legacy_select = next((entry for entry in target_select_entries if str(((entry or {}).get("metadata", {}) or {}).get("mode", "") or "") == "legacy-global"), None)
    scoped_select = next((entry for entry in target_select_entries if str(((entry or {}).get("metadata", {}) or {}).get("mode", "") or "") == "scoped"), None)
    if not legacy_select or not scoped_select:
        raise AssertionError(f"Interest renew benchmark did not record both selection modes: {runtime_metrics}")

    legacy_target_count = int((((legacy_select or {}).get("metadata", {}) or {}).get("target_count", 0) or 0))
    scoped_target_count = int((((scoped_select or {}).get("metadata", {}) or {}).get("target_count", 0) or 0))
    if legacy_target_count <= scoped_target_count:
        raise AssertionError(
            f"Interest renew benchmark did not reduce renew scope under activation: legacy={legacy_target_count} scoped={scoped_target_count}"
        )
    expected_scoped = 1 + len(local_targets) + len(nearby_targets)
    if scoped_target_count != expected_scoped:
        raise AssertionError(
            f"Interest renew benchmark renewed the wrong scoped target count: expected {expected_scoped}, got {scoped_target_count}"
        )

    benchmark = {
        "legacy_select_ms": float((legacy_select or {}).get("duration_ms", 0.0) or 0.0),
        "scoped_select_ms": float((scoped_select or {}).get("duration_ms", 0.0) or 0.0),
        "legacy_command_ms": legacy_command_ms,
        "scoped_command_ms": scoped_command_ms,
        "legacy_target_count": legacy_target_count,
        "scoped_target_count": scoped_target_count,
        "legacy_scanned_count": int((((legacy_select or {}).get("metadata", {}) or {}).get("scanned_count", 0) or 0)),
        "scoped_scanned_count": int((((scoped_select or {}).get("metadata", {}) or {}).get("scanned_count", 0) or 0)),
        "selection_delta_ms": float((legacy_select or {}).get("duration_ms", 0.0) or 0.0) - float((scoped_select or {}).get("duration_ms", 0.0) or 0.0),
        "command_delta_ms": legacy_command_ms - scoped_command_ms,
        "target_delta": legacy_target_count - scoped_target_count,
        "execute_event_count": len(execute_entries),
        "interest_active_object_peak": _safe_int((runtime_metrics.get("gauges", {}) or {}).get("interest.active_object_peak", 0), 0),
        "interest_source_count_peak": _safe_int((runtime_metrics.get("gauges", {}) or {}).get("interest.source_count.peak", 0), 0),
    }

    set_flag("interest_activation", False, actor="diretest-benchmark")
    return {
        "commands": list(ctx.command_log),
        "legacy_renewed_count": len(legacy_renewed),
        "scoped_renewed_count": len(scoped_renewed),
        "legacy_renewed": legacy_renewed,
        "scoped_renewed": scoped_renewed,
        "benchmark": benchmark,
        "output_log": list(ctx.output_log),
    }


def _build_onboarding_full_output(args):
    started_perf = time.perf_counter()
    _setup_django()

    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object

    from systems import onboarding

    created_objects = []
    try:
        rooms = _get_or_create_tutorial_rooms(ObjectDB, create_object, created_objects)
        character = _create_test_onboarding_character(create_object, rooms, created_objects, onboarding)
        final_name = _default_test_name(getattr(args, "name", "DireTestHero"))
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

        state = onboarding.ensure_onboarding_state(character)
        can_exit, exit_message = onboarding.can_exit_to_world(character)
        output = {
            "scenario": "onboarding_full",
            "name": final_name,
            "results": results,
            "can_exit": can_exit,
            "exit_message": exit_message,
            "tokens": int(state.get("tokens", 0) or 0),
            "completed_steps": list(state.get("completed_steps") or []),
            "all_valid": bool(can_exit) and all(result.get("ok") for result in results),
            "duration_ms": int(max(0, round((time.perf_counter() - started_perf) * 1000.0))),
        }
        return output
    finally:
        for name in reversed(created_objects):
            _cleanup_named_object(name)


def _summarize_combat_baseline(result):
    scenario_result = dict((result or {}).get("result", {}) or {})
    metrics = dict((result or {}).get("metrics", {}) or {})
    engaged_diff = dict(scenario_result.get("engaged_diff", {}) or {})
    damaged_diff = dict(scenario_result.get("damaged_diff", {}) or {})
    engaged_combat_changes = dict(engaged_diff.get("combat_changes", {}) or {})
    combat_changes = dict(damaged_diff.get("combat_changes", {}) or {})
    target_hp_after = combat_changes.get("target_hp_after")
    target_hp_before = combat_changes.get("target_hp_before")
    hit_damage = None
    if target_hp_before is not None and target_hp_after is not None:
        hit_damage = int(target_hp_before) - int(target_hp_after)
    return {
        "artifact_dir": str((result or {}).get("artifact_dir", "") or ""),
        "exit_code": _safe_int((result or {}).get("exit_code", 1), 1),
        "duration_ms": _safe_int(metrics.get("scenario_duration_ms", 0), 0),
        "command_count": _safe_int(metrics.get("command_count", 0), 0),
        "target_hp_before": target_hp_before,
        "target_hp_after": target_hp_after,
        "hit_damage": hit_damage,
        "entered_combat": bool(engaged_combat_changes.get("entered_combat", False)),
        "exited_combat": bool(scenario_result.get("disengaged_diff", {}).get("combat_changes", {}).get("exited_combat", False)),
        "roundtime_after_attack": combat_changes.get("roundtime_after"),
    }


def _summarize_economy_baseline(economy_result, bank_result):
    economy_payload = dict((economy_result or {}).get("result", {}) or {})
    economy_metrics = dict((economy_result or {}).get("metrics", {}) or {})
    bank_payload = dict((bank_result or {}).get("result", {}) or {})
    bank_metrics = dict((bank_result or {}).get("metrics", {}) or {})
    buy_diff = dict(economy_payload.get("buy_diff", {}) or {})
    sell_diff = dict(economy_payload.get("sell_diff", {}) or {})
    deposit_diff = dict(bank_payload.get("deposit_diff", {}) or {})
    withdraw_diff = dict(bank_payload.get("withdraw_diff", {}) or {})
    return {
        "vendor_trade": {
            "artifact_dir": str((economy_result or {}).get("artifact_dir", "") or ""),
            "exit_code": _safe_int((economy_result or {}).get("exit_code", 1), 1),
            "duration_ms": _safe_int(economy_metrics.get("scenario_duration_ms", 0), 0),
            "command_count": _safe_int(economy_metrics.get("command_count", 0), 0),
            "purchase_cost": abs(int(buy_diff.get("character_changes", {}).get("coins_delta", 0) or 0)),
            "sale_return": int(sell_diff.get("character_changes", {}).get("coins_delta", 0) or 0),
            "net_coin_delta": int(economy_metrics.get("coin_delta", 0) or 0),
            "haggle_bonus": float(economy_payload.get("haggle_bonus", 0.0) or 0.0),
        },
        "banking": {
            "artifact_dir": str((bank_result or {}).get("artifact_dir", "") or ""),
            "exit_code": _safe_int((bank_result or {}).get("exit_code", 1), 1),
            "duration_ms": _safe_int(bank_metrics.get("scenario_duration_ms", 0), 0),
            "command_count": _safe_int(bank_metrics.get("command_count", 0), 0),
            "deposit_to_bank": int(deposit_diff.get("character_changes", {}).get("bank_coins_delta", 0) or 0),
            "withdraw_to_hand": int(withdraw_diff.get("character_changes", {}).get("coins_delta", 0) or 0),
            "net_carried_coin_delta": int(bank_metrics.get("coin_delta", 0) or 0),
        },
    }


def _summarize_progression_baseline(onboarding_output):
    completed_steps = list(onboarding_output.get("completed_steps", []) or [])
    return {
        "scenario": "onboarding_full",
        "duration_ms": int(onboarding_output.get("duration_ms", 0) or 0),
        "completed_step_count": len(completed_steps),
        "completed_steps": completed_steps,
        "token_count": int(onboarding_output.get("tokens", 0) or 0),
        "exit_ready": bool(onboarding_output.get("can_exit", False)),
    }


def _emit_balance_baseline_output(report, as_json=False):
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    combat = dict((report.get("baselines", {}) or {}).get("combat_outcomes", {}) or {})
    economy = dict((report.get("baselines", {}) or {}).get("economy_flows", {}) or {})
    vendor_trade = dict(economy.get("vendor_trade", {}) or {})
    banking = dict(economy.get("banking", {}) or {})
    progression = dict((report.get("baselines", {}) or {}).get("progression_pacing", {}) or {})

    lines = [
        "DireTest Balance Baseline",
        f"Seed: {int(report.get('seed', 0) or 0)}",
        f"Exit Code: {int(report.get('exit_code', 0) or 0)}",
        f"Artifact Dir: {report.get('artifact_dir', '')}",
        "",
        "Combat Outcomes:",
        f"- Duration Ms: {int(combat.get('duration_ms', 0) or 0)}",
        f"- Commands: {int(combat.get('command_count', 0) or 0)}",
        f"- Hit Damage: {combat.get('hit_damage')}",
        f"- Target HP After Hit: {combat.get('target_hp_after')}",
        f"- Entered Combat: {combat.get('entered_combat')}",
        f"- Exited Combat: {combat.get('exited_combat')}",
        "",
        "Economy Flows:",
        f"- Vendor Purchase Cost: {int(vendor_trade.get('purchase_cost', 0) or 0)}",
        f"- Vendor Sale Return: {int(vendor_trade.get('sale_return', 0) or 0)}",
        f"- Vendor Net Coin Delta: {int(vendor_trade.get('net_coin_delta', 0) or 0)}",
        f"- Haggle Bonus: {float(vendor_trade.get('haggle_bonus', 0.0) or 0.0):.2f}",
        f"- Bank Deposit Delta: {int(banking.get('deposit_to_bank', 0) or 0)}",
        f"- Bank Withdraw Delta: {int(banking.get('withdraw_to_hand', 0) or 0)}",
        f"- Net Carried Coin Delta: {int(banking.get('net_carried_coin_delta', 0) or 0)}",
        "",
        "Progression Pacing:",
        f"- Onboarding Duration Ms: {int(progression.get('duration_ms', 0) or 0)}",
        f"- Completed Steps: {int(progression.get('completed_step_count', 0) or 0)}",
        f"- Tokens: {int(progression.get('token_count', 0) or 0)}",
        f"- Exit Ready: {progression.get('exit_ready')}",
        "",
        f"PASS: {'yes' if bool(report.get('all_valid', False)) else 'no'}",
    ]
    _print_lines(lines)


def _run_balance_baseline(seed, character_name):
    started_at = time.time()
    started_perf = time.perf_counter()
    command_log = [
        f"scenario combat-basic --seed {seed}",
        f"scenario economy --seed {seed}",
        f"scenario bank --seed {seed}",
        f"scenario onboarding_full --seed {seed} --name {str(character_name or 'DireTestHero')}",
    ]

    failure_type = None
    failure_message = ""
    traceback_text = ""
    combat_result = None
    economy_result = None
    bank_result = None
    onboarding_output = None
    exit_code = 0

    try:
        combat_result = run_combat_basic_scenario(_build_runner_namespace(seed))
        economy_result = run_economy_scenario(_build_runner_namespace(seed))
        bank_result = run_bank_scenario(_build_runner_namespace(seed))
        onboarding_output = _build_onboarding_full_output(_build_runner_namespace(seed, name=character_name))
    except Exception:
        exit_code = 1
        failure_type = "unexpected_exception"
        traceback_text = traceback.format_exc()
        failure_message = traceback_text.strip().splitlines()[-1]

    if combat_result and int(combat_result.get("exit_code", 0) or 0) != 0:
        exit_code = 1
        failure_type = failure_type or "unexpected_exception"
        failure_message = failure_message or "combat-basic baseline failed"
    if economy_result and int(economy_result.get("exit_code", 0) or 0) != 0:
        exit_code = 1
        failure_type = failure_type or "unexpected_exception"
        failure_message = failure_message or "economy baseline failed"
    if bank_result and int(bank_result.get("exit_code", 0) or 0) != 0:
        exit_code = 1
        failure_type = failure_type or "unexpected_exception"
        failure_message = failure_message or "bank baseline failed"
    if onboarding_output and not bool(onboarding_output.get("all_valid", False)):
        exit_code = 1
        failure_type = failure_type or "unexpected_exception"
        failure_message = failure_message or "onboarding progression baseline failed"

    report = {
        "scenario": "balance-baseline",
        "seed": seed,
        "all_valid": exit_code == 0,
        "baselines": {
            "combat_outcomes": _summarize_combat_baseline(combat_result or {}),
            "economy_flows": _summarize_economy_baseline(economy_result or {}, bank_result or {}),
            "progression_pacing": _summarize_progression_baseline(onboarding_output or {}),
        },
        "subruns": {
            "combat_basic_artifact": str((combat_result or {}).get("artifact_dir", "") or ""),
            "economy_artifact": str((economy_result or {}).get("artifact_dir", "") or ""),
            "bank_artifact": str((bank_result or {}).get("artifact_dir", "") or ""),
        },
    }

    duration_ms = int(max(0, round((time.perf_counter() - started_perf) * 1000.0)))
    artifact_dir = write_artifacts(
        f"balance-baseline_direct_{seed}",
        {
            "scenario": {
                "name": "balance-baseline",
                "mode": "direct",
                "seed": seed,
                "started_at": started_at,
            },
            "seed": seed,
            "command_log": command_log,
            "snapshots": [],
            "diffs": [],
            "metrics": {
                "exit_code": int(exit_code),
                "result": report,
                "failure_type": failure_type,
                "started_at": started_at,
                "ended_at": time.time(),
                "scenario_duration_ms": duration_ms,
            },
            "failure_summary": build_failure_summary(
                failure_type=failure_type,
                message=failure_message,
                scenario="balance-baseline",
                seed=seed,
                mode="direct",
            ),
            "traceback": traceback_text,
        },
    )
    report["artifact_dir"] = str(artifact_dir)
    report["exit_code"] = int(exit_code)
    report["duration_ms"] = duration_ms

    return report


def _format_metric_value(value):
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"
    if value is None:
        return "None"
    return str(value)


def _format_metric_delta(delta_value):
    if isinstance(delta_value, float) and not float(delta_value).is_integer():
        return f"{delta_value:+.4f}".rstrip("0").rstrip(".")
    return f"{int(delta_value):+d}"


def _format_baseline_metric_lines(metrics):
    lines = []
    payload = dict(metrics or {})
    for key, label in METRIC_SPECS:
        lines.append(f"- {label}: {_format_metric_value(payload.get(key))}")
    return lines


def _emit_baseline_save_output(record, baseline_path, report, as_json=False):
    payload = {
        "baseline": record,
        "baseline_path": str(baseline_path),
        "current_artifact_dir": str(report.get("artifact_dir", "") or ""),
        "exit_code": int(report.get("exit_code", 0) or 0),
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    lines = [
        "DireTest Baseline Saved",
        f"Name: {record.get('name', '')}",
        f"Seed: {int(record.get('seed', 0) or 0)}",
        f"Baseline File: {baseline_path}",
        f"Current Artifact: {report.get('artifact_dir', '')}",
        "",
        "Metrics:",
    ]
    lines.extend(_format_baseline_metric_lines(record.get("metrics", {})))
    _print_lines(lines)


def _emit_baseline_compare_output(name, baseline_path, compare_payload, as_json=False):
    if as_json:
        print(json.dumps(compare_payload, indent=2, sort_keys=True))
        return

    lines = [
        "DireTest Baseline Compare",
        f"Name: {name}",
        f"Baseline File: {baseline_path}",
        f"Saved Seed: {int((compare_payload.get('saved_baseline', {}) or {}).get('seed', 0) or 0)}",
        f"Current Seed: {int((compare_payload.get('current_report', {}) or {}).get('seed', 0) or 0)}",
        f"Current Artifact: {(compare_payload.get('current_report', {}) or {}).get('artifact_dir', '')}",
        "",
        "Deltas:",
    ]
    for entry in list(compare_payload.get("deltas", []) or []):
        label = str(entry.get("label", "metric") or "metric")
        if "delta" in entry:
            lines.append(
                f"- {label}: {_format_metric_delta(entry.get('delta', 0))} "
                f"(baseline {_format_metric_value(entry.get('baseline'))} -> current {_format_metric_value(entry.get('current'))})"
            )
        else:
            lines.append(
                f"- {label}: {_format_metric_value(entry.get('baseline'))} -> {_format_metric_value(entry.get('current'))}"
            )
    _print_lines(lines)


def _write_baseline_command_artifact(run_id, seed, command_log, result_payload, failure_type=None, failure_message="", traceback_text=""):
    duration_ms = _safe_int((result_payload or {}).get("duration_ms", 0), 0)
    return write_artifacts(
        run_id,
        {
            "scenario": {
                "name": str((result_payload or {}).get("scenario", run_id) or run_id),
                "mode": "direct",
                "seed": int(seed or 0),
                "started_at": time.time(),
            },
            "seed": int(seed or 0),
            "command_log": list(command_log or []),
            "snapshots": [],
            "diffs": [],
            "metrics": {
                "exit_code": _safe_int((result_payload or {}).get("exit_code", 0), 0),
                "result": result_payload,
                "failure_type": failure_type,
                "scenario_duration_ms": duration_ms,
            },
            "failure_summary": build_failure_summary(
                failure_type=failure_type,
                message=failure_message,
                scenario=str((result_payload or {}).get("scenario", run_id) or run_id),
                seed=seed,
                mode="direct",
            ),
            "traceback": traceback_text,
        },
    )


def _handle_balance_baseline_command(args):
    seed = _ensure_scenario_seed(args)
    report = _run_balance_baseline(seed, getattr(args, "name", "DireTestHero"))

    _emit_balance_baseline_output(report, as_json=bool(getattr(args, "json", False)))
    return int(report.get("exit_code", 0) or 0)


def _handle_baseline_save_command(args):
    seed = _ensure_scenario_seed(args)
    baseline_name = str(getattr(args, "baseline_name", "") or "").strip()
    report = _run_balance_baseline(seed, getattr(args, "character_name", "DireTestHero"))
    baseline_path, record = save_named_baseline(baseline_name, report)

    payload = {
        "scenario": "baseline-save",
        "baseline_name": record.get("name"),
        "baseline_path": str(baseline_path),
        "saved_baseline": record,
        "current_report": report,
        "exit_code": int(report.get("exit_code", 0) or 0),
        "duration_ms": int(report.get("duration_ms", 0) or 0),
    }
    artifact_dir = _write_baseline_command_artifact(
        f"baseline-save_{record.get('name', 'baseline')}_direct_{seed}",
        seed,
        [f"baseline save {baseline_name} --seed {seed}"],
        payload,
    )
    payload["artifact_dir"] = str(artifact_dir)

    _emit_baseline_save_output(record, baseline_path, report, as_json=bool(getattr(args, "json", False)))
    return int(payload.get("exit_code", 0) or 0)


def _handle_baseline_compare_command(args):
    seed = _ensure_scenario_seed(args)
    baseline_name = str(getattr(args, "baseline_name", "") or "").strip()

    try:
        baseline_path, saved_record = load_named_baseline(baseline_name)
    except FileNotFoundError as exc:
        artifact_dir = _write_cli_failure_artifact("baseline-compare", seed, "missing_baseline", str(exc), mode="direct")
        if bool(getattr(args, "json", False)):
            print(json.dumps({"exit_code": 1, "failure_type": "missing_baseline", "message": str(exc), "artifact_dir": artifact_dir}, indent=2, sort_keys=True))
        else:
            _print_lines([
                "DireTest Baseline Compare",
                f"Name: {baseline_name}",
                f"Artifact Dir: {artifact_dir}",
                f"FAIL: {exc}",
            ])
        return 1

    report = _run_balance_baseline(seed, getattr(args, "character_name", "DireTestHero"))
    comparison = compare_named_baseline(saved_record, report)
    payload = {
        "scenario": "baseline-compare",
        "baseline_name": str(saved_record.get("name", baseline_name) or baseline_name),
        "baseline_path": str(baseline_path),
        "saved_baseline": saved_record,
        "current_report": report,
        "deltas": list(comparison.get("deltas", []) or []),
        "current_metrics": dict(comparison.get("current_metrics", {}) or {}),
        "baseline_metrics": dict(comparison.get("baseline_metrics", {}) or {}),
        "exit_code": int(report.get("exit_code", 0) or 0),
        "duration_ms": int(report.get("duration_ms", 0) or 0),
    }
    artifact_dir = _write_baseline_command_artifact(
        f"baseline-compare_{saved_record.get('name', 'baseline')}_direct_{seed}",
        seed,
        [f"baseline compare {baseline_name} --seed {seed}"],
        payload,
    )
    payload["artifact_dir"] = str(artifact_dir)

    _emit_baseline_compare_output(payload.get("baseline_name", baseline_name), baseline_path, payload, as_json=bool(getattr(args, "json", False)))
    return int(payload.get("exit_code", 0) or 0)


@register_scenario("movement")
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
        if not movement_diff["room_changes"]["changed"]:
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

    return _run_registered_scenario(args, scenario, auto_snapshot=True, name="movement")


@register_scenario(
    "fishing-vertical-slice",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Fishing vertical slice now validates multi-step economy and world hooks; lag telemetry should be reported without masking behavioral regressions.",
    },
)
def run_fishing_vertical_slice_scenario(args):
    _setup_django()

    def scenario(ctx):
        import random as pyrandom

        from evennia.utils.create import create_object

        import world.systems.fishing_economy as fishing_economy
        import world.systems.fishing as fishing_system

        water_room = ctx.harness.create_test_room(key="TEST_FISHING_WATER")
        dry_room = ctx.harness.create_test_room(key="TEST_FISHING_DRY")
        ctx.harness.create_test_exit(water_room, dry_room, "north", aliases=["n"])
        ctx.harness.create_test_exit(dry_room, water_room, "south", aliases=["s"])

        water_room.db.fishable = True
        water_room.db.fish_group = "River 1"

        character = ctx.harness.create_test_character(room=water_room, key="TEST_FISHING_CHAR")
        ctx.character = character
        ctx.room = water_room
        character.ndb.fishing_debug = True
        character.ndb.fishing_debug_trace = []
        character.db.stats = {"reflex": 12, "discipline": 12}
        character.learn_skill("outdoorsmanship", {"rank": 60, "mindstate": 0})
        character.learn_skill("mechanical_lore", {"rank": 0, "mindstate": 0})
        character.learn_skill("scholarship", {"rank": 0, "mindstate": 0})

        supplier = create_object("typeclasses.fishing_supplier.FishingSupplier", key="Old Maren", location=water_room, home=water_room)
        create_object("typeclasses.weigh_station.WeighStation", key="dock scale", location=water_room, home=water_room)

        visible_npcs = [obj for obj in list(water_room.contents) if bool(getattr(getattr(obj, "db", None), "is_fishing_supplier", False))]
        if supplier not in visible_npcs:
            raise AssertionError("Fishing scenario did not place the supplier/buyer NPC in the fishing room.")
        if not bool(getattr(getattr(supplier, "db", None), "is_vendor", False)):
            raise AssertionError("Fishing scenario did not mark the supplier as a valid vendor target.")
        if "patient expression" not in str(getattr(getattr(supplier, "db", None), "desc", "") or "").lower():
            raise AssertionError("Fishing scenario did not preserve the supplier's dual-role description.")

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        outdoors_skill = character.exp_skills.get("outdoorsmanship")
        before_pool = float(getattr(outdoors_skill, "pool", 0.0) or 0.0)
        mechanical_skill = character.exp_skills.get("mechanical_lore")
        before_mechanical_pool = float(getattr(mechanical_skill, "pool", 0.0) or 0.0)
        output_index = len(ctx.output_log)

        original_delay = fishing_system.delay
        original_time = fishing_system.time.time
        original_random = fishing_system.random.random
        original_choice = fishing_system.random.choice
        original_randint = fishing_system.random.randint
        original_choose_weighted = fishing_system.choose_weighted_fish_profile
        original_nibble_chance = fishing_system.calculate_nibble_chance
        original_hookup_chance = fishing_system.calculate_hookup_chance
        original_timeout_tangle = fishing_system.calculate_timeout_tangle_chance
        original_resolve_struggle = fishing_system.resolve_struggle_outcome_data
        original_fishing_economy_time = fishing_economy.time.time
        current_time = {"value": 1000.0}
        scheduled = []

        class FakeDelayedTask:
            def __init__(self):
                self.cancelled = False

            def cancel(self):
                self.cancelled = True

        def fake_delay(seconds, callback, *cb_args, **cb_kwargs):
            task = FakeDelayedTask()
            scheduled.append(
                {
                    "seconds": float(seconds),
                    "callback": callback,
                    "callback_name": getattr(callback, "__name__", "callback"),
                    "args": cb_args,
                    "kwargs": cb_kwargs,
                    "task": task,
                }
            )
            return task

        def run_next(expected_seconds=None, callback_name=None, min_seconds=None, max_seconds=None):
            event_index = None
            for index, event in enumerate(list(scheduled)):
                task = event.get("task")
                if task is not None and bool(getattr(task, "cancelled", False)):
                    continue
                seconds = float(event.get("seconds", 0.0) or 0.0)
                if callback_name and str(event.get("callback_name", "") or "") != str(callback_name):
                    continue
                if expected_seconds is not None and abs(seconds - float(expected_seconds)) > 0.01:
                    continue
                if min_seconds is not None and seconds < float(min_seconds):
                    continue
                if max_seconds is not None and seconds > float(max_seconds):
                    continue
                event_index = index
                break
            if event_index is None:
                raise AssertionError(
                    f"Fishing scenario expected callback={callback_name or 'any'} seconds={expected_seconds} range=({min_seconds}, {max_seconds}), but found {scheduled}."
                )
            event = scheduled.pop(event_index)
            seconds = float(event.get("seconds", 0.0) or 0.0)
            current_time["value"] += seconds
            ctx.direct(event["callback"], *(event.get("args") or ()), **(event.get("kwargs") or {}))
            return seconds

        def assert_no_active_callback(callback_name):
            for event in list(scheduled):
                task = event.get("task")
                if task is not None and bool(getattr(task, "cancelled", False)):
                    continue
                if str(event.get("callback_name", "") or "") == str(callback_name):
                    raise AssertionError(f"Fishing scenario left an active {callback_name} callback behind: {scheduled}")
            return float(event.get("seconds", 0.0) or 0.0)

        try:
            fishing_system.delay = fake_delay
            fishing_system.time.time = lambda: float(current_time["value"])
            fishing_system.random.random = lambda: 0.0
            fishing_system.random.choice = lambda seq: list(seq)[0]
            fishing_system.random.randint = lambda _low, _high: 5
            fishing_economy.time.time = lambda: float(current_time["value"])

            river_rng = pyrandom.Random(1234)
            river_samples = [fishing_system.choose_weighted_fish_profile("River 1", rng=river_rng) for _ in range(80)]
            if any(sample.get("fish_group") != "river 1" for sample in river_samples):
                raise AssertionError(f"Fishing scenario found a non-river profile in River 1 selection: {river_samples[:5]}")
            river_trout = sum(1 for sample in river_samples if sample.get("key") == "silver_trout")
            river_carp = sum(1 for sample in river_samples if sample.get("key") == "mud_carp")
            if river_trout <= river_carp:
                raise AssertionError(f"Fishing scenario did not demonstrate weighted River 1 selection: trout={river_trout}, carp={river_carp}")

            ocean_rng = pyrandom.Random(4321)
            ocean_samples = [fishing_system.choose_weighted_fish_profile("Ocean", rng=ocean_rng) for _ in range(40)]
            if any(sample.get("fish_group") != "ocean" for sample in ocean_samples):
                raise AssertionError(f"Fishing scenario found a non-ocean profile in Ocean selection: {ocean_samples[:5]}")

            fallback_group = fishing_system.resolve_fish_group_data("Unknown Whirlpool")
            if fallback_group.get("key") != "river 1" or not bool(fallback_group.get("is_fallback")):
                raise AssertionError(f"Fishing scenario did not provide a safe fish-group fallback: {fallback_group}")

            ctx.cmd("pull")
            invalid_pull_output = list(ctx.output_log[output_index:])
            if not any("there's nothing on the line anymore" in str(line).lower() for line in invalid_pull_output):
                raise AssertionError(f"Fishing scenario did not reject pull outside the reaction window: {invalid_pull_output}")

            cast_hint_index = len(ctx.output_log)
            ctx.cmd("cast")
            cast_hint_output = list(ctx.output_log[cast_hint_index:])
            if not any("if you meant to fish, try 'fish'." in str(line).lower() for line in cast_hint_output):
                raise AssertionError(f"Fishing scenario did not offer the fishing hint on bare cast with no prepared spell: {cast_hint_output}")

            output_index = len(ctx.output_log)
            ctx.cmd("fish")
            no_bait_output = list(ctx.output_log[output_index:])
            if not any("fishing pole" in str(line).lower() or "hook and line" in str(line).lower() for line in no_bait_output):
                raise AssertionError(f"Fishing scenario did not block fishing without minimal gear: {no_bait_output}")
            if getattr(character.ndb, "fishing_session", None) is not None:
                raise AssertionError("Fishing without minimal gear should not create a lingering session.")

            bypass_result = ctx.direct(fishing_system.start_fishing_cast, character)
            bypass_output = list(ctx.output_log[len(ctx.output_log) - 2 :])
            if bypass_result is not False:
                raise AssertionError("Fishing scenario expected start_fishing_cast to fail without minimal gear.")
            if not any("fishing pole" in str(line).lower() or "hook and line" in str(line).lower() for line in bypass_output):
                raise AssertionError(f"Fishing scenario did not prove gear gating at the system layer: {bypass_output}")

            gear_redirect_index = len(ctx.output_log)
            ctx.cmd("get gear")
            gear_redirect_output = list(ctx.output_log[gear_redirect_index:])
            if not any("ask me for gear" in str(line).lower() for line in gear_redirect_output):
                raise AssertionError(f"Fishing scenario did not redirect direct gear pickup toward the supplier dialog: {gear_redirect_output}")

            gear_index = len(ctx.output_log)
            ctx.cmd("ask maren for gear")
            gear_output = list(ctx.output_log[gear_index:])
            if not any("old maren says" in str(line).lower() for line in gear_output):
                raise AssertionError(f"Fishing scenario did not resolve ask-for-gear through the NPC inquiry path: {gear_output}")
            if not any("presses them into your hands" in str(line).lower() for line in gear_output):
                raise AssertionError(f"Fishing scenario did not emit the staged handoff text for starter gear: {gear_output}")
            if not any("thread your catch onto this" in str(line).lower() for line in gear_output):
                raise AssertionError(f"Fishing scenario did not surface the fish-string handling hint: {gear_output}")

            initial_pole_count = len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_fishing_pole", False))])
            initial_bait_count = len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_bait", False))])
            initial_hook_count = len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_hook", False))])
            initial_line_count = len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_line", False))])
            initial_string_count = len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_fish_string", False))])
            if min(initial_pole_count, initial_bait_count, initial_hook_count, initial_line_count, initial_string_count) < 1:
                raise AssertionError("Fishing scenario did not receive the full starter fishing kit from Old Maren.")

            repeat_gear_index = len(ctx.output_log)
            ctx.cmd("ask maren for gear")
            repeat_gear_output = list(ctx.output_log[repeat_gear_index:])
            repeated_counts = {
                "pole": len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_fishing_pole", False))]),
                "bait": len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_bait", False))]),
                "hook": len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_hook", False))]),
                "line": len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_line", False))]),
                "string": len([obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_fish_string", False))]),
            }
            if repeated_counts != {
                "pole": initial_pole_count,
                "bait": initial_bait_count,
                "hook": initial_hook_count,
                "line": initial_line_count,
                "string": initial_string_count,
            }:
                raise AssertionError(f"Fishing scenario let Old Maren duplicate starter gear infinitely: {repeated_counts}")
            if not any("already have the basics" in str(line).lower() for line in repeat_gear_output):
                raise AssertionError(f"Fishing scenario did not explain the non-duplication behavior on a repeated gear request: {repeat_gear_output}")

            pole = next(obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_fishing_pole", False)))
            if float(getattr(getattr(pole, "db", None), "pole_rating", 0) or 0) != 10.0:
                raise AssertionError("Fishing scenario did not receive the expected starter fishing pole rating.")
            if bool(getattr(getattr(pole, "db", None), "line_tangled", True)):
                raise AssertionError("Fishing scenario expected the starter fishing pole to begin untangled.")

            invalid_bait_index = len(ctx.output_log)
            ctx.cmd("bait hook")
            invalid_bait_output = list(ctx.output_log[invalid_bait_index:])
            if not any("you can't use that as bait" in str(line).lower() for line in invalid_bait_output):
                raise AssertionError(f"Fishing scenario did not reject non-bait items cleanly: {invalid_bait_output}")

            pole.db.line_attached = False
            unrigged_bait_index = len(ctx.output_log)
            ctx.cmd("bait worm")
            unrigged_bait_output = list(ctx.output_log[unrigged_bait_index:])
            if not any("you need to rig your pole before baiting it" in str(line).lower() for line in unrigged_bait_output):
                raise AssertionError(f"Fishing scenario did not hard-gate baiting on rig state: {unrigged_bait_output}")
            if sum(1 for line in unrigged_bait_output if "rig your pole before baiting" in str(line).lower()) != 1:
                raise AssertionError(f"Fishing scenario emitted duplicate unrigged bait messaging: {unrigged_bait_output}")
            session = getattr(character.ndb, "fishing_session", None)
            if session is not None and bool(getattr(session, "baited", False)):
                raise AssertionError("Fishing scenario applied bait even though the pole was unrigged.")
            ctx.cmd("rig pole")

            worm = next(obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_bait", False)))
            spinner = create_object("typeclasses.items.bait.Bait", key="spinner", location=character, home=character)
            spinner.db.bait_type = "artificial_simple"
            spinner.db.bait_family = "artificial_simple"
            spinner.db.quality = 10
            spinner.db.bait_quality = 10
            spinner.db.bait_match_tags = ["shiny", "starter"]
            lure = create_object("typeclasses.items.bait.Bait", key="lure", location=character, home=character)
            lure.db.bait_type = "specialty_lure"
            lure.db.bait_family = "specialty_lure"
            lure.db.quality = 16
            lure.db.bait_quality = 16
            lure.db.bait_match_tags = ["saltwater", "deepwater", "specialty"]

            silver_trout = fishing_system.get_fish_profile("silver_trout")
            trial_session = fishing_system.FishingSession(character)
            better_nibble = fishing_system.calculate_nibble_chance(character, water_room, worm, silver_trout)
            weaker_nibble = fishing_system.calculate_nibble_chance(character, water_room, spinner, silver_trout)
            if better_nibble <= weaker_nibble:
                raise AssertionError(f"Fishing scenario did not show better bait improving nibble odds: worm={better_nibble}, spinner={weaker_nibble}")

            matched_hook = fishing_system.calculate_hookup_chance(character, trial_session, worm, silver_trout)
            mismatched_hook = fishing_system.calculate_hookup_chance(character, trial_session, lure, silver_trout)
            if matched_hook <= mismatched_hook:
                raise AssertionError(f"Fishing scenario did not show matched bait improving hook odds: matched={matched_hook}, mismatched={mismatched_hook}")

            lore_eff = fishing_system.calculate_lore_efficiency(character, fishing_system.resolve_bait_profile(lure))
            if lore_eff <= 0.0 or lore_eff >= 1.0:
                raise AssertionError(f"Fishing scenario did not keep advanced-bait lore friction mild and non-blocking: {lore_eff}")

            fishing_system.choose_weighted_fish_profile = lambda _room_or_group, rng=None: fishing_system.get_fish_profile("silver_trout")
            fishing_system.calculate_nibble_chance = lambda *_args, **_kwargs: 1.0

            output_index = len(ctx.output_log)
            ctx.cmd("fish")
            unbaited_output = list(ctx.output_log[output_index:])
            if not any("bait your hook" in str(line).lower() for line in unbaited_output):
                raise AssertionError(f"Fishing scenario did not enforce the baited state: {unbaited_output}")

            output_index = len(ctx.output_log)
            ctx.cmd("bait worm")
            bait_output = list(ctx.output_log[output_index:])
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "baited" or not bool(getattr(session, "baited", False)):
                raise AssertionError("Fishing scenario did not create a baited session.")
            if not any("bait your hook" in str(line).lower() for line in bait_output):
                raise AssertionError(f"Fishing scenario did not confirm baiting: {bait_output}")

            output_index = len(ctx.output_log)
            ctx.cmd("fish")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "cast":
                raise AssertionError("Fishing scenario did not enter the cast state before early-pull tangle validation.")
            ctx.cmd("pull")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "tangled":
                raise AssertionError("Fishing scenario did not convert an early pull into a tangled line state.")
            tangled_output = list(ctx.output_log[output_index:])
            if not any("tangle" in str(line).lower() for line in tangled_output):
                raise AssertionError(f"Fishing scenario did not emit tangled-line feedback on early pull: {tangled_output}")
            blocked_cast_index = len(ctx.output_log)
            ctx.cmd("fish")
            blocked_cast_output = list(ctx.output_log[blocked_cast_index:])
            if not any("tangled" in str(line).lower() for line in blocked_cast_output):
                raise AssertionError(f"Fishing scenario did not block casting while tangled: {blocked_cast_output}")
            untangle_after_early_pull_index = len(ctx.output_log)
            ctx.cmd("untangle pole")
            untangle_after_early_pull_output = list(ctx.output_log[untangle_after_early_pull_index:])
            if not any("line hangs clean" in str(line).lower() or "knots free" in str(line).lower() for line in untangle_after_early_pull_output):
                raise AssertionError(f"Fishing scenario did not require a manual untangle after an early-pull snarl: {untangle_after_early_pull_output}")
            ctx.cmd("bait worm")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "baited":
                raise AssertionError("Fishing scenario did not allow baiting after clearing a tangled line state.")
            assert_no_active_callback("_begin_nibble")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "baited":
                raise AssertionError("Fishing scenario let a stale nibble callback corrupt a re-baited session.")

            output_index = len(ctx.output_log)
            ctx.cmd("fish")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "cast":
                raise AssertionError("Fishing scenario did not enter the cast state.")

            bite_delay = run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
            if bite_delay < 4.0 or bite_delay > 10.0:
                raise AssertionError(f"Fishing scenario scheduled a River 1 bite outside the expected timing range: {bite_delay}")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "nibble" or float(getattr(session, "nibble_time", 0.0) or 0.0) <= 0.0:
                raise AssertionError("Fishing scenario did not enter the nibble phase with a reaction timestamp.")

            fishing_system.calculate_timeout_tangle_chance = lambda *_args, **_kwargs: 1.0
            timeout_delay = run_next(callback_name="_expire_nibble_window", min_seconds=2.5, max_seconds=4.5)
            if timeout_delay < 2.5 or timeout_delay > 4.5:
                raise AssertionError(f"Fishing scenario scheduled nibble expiry outside the expected timing variance: {timeout_delay}")
            timeout_output = list(ctx.output_log[output_index:])
            if not any("line goes still" in str(line).lower() for line in timeout_output):
                raise AssertionError(f"Fishing scenario did not emit missed-bite text: {timeout_output}")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "tangled":
                raise AssertionError("Fishing scenario did not promote missed-bite tangles into a real session state.")

            timeout_pull_index = len(ctx.output_log)
            ctx.cmd("pull")
            timeout_pull_output = list(ctx.output_log[timeout_pull_index:])
            if not any("tangled" in str(line).lower() for line in timeout_pull_output):
                raise AssertionError(f"Fishing scenario did not reject pull after timeout with tangled-state feedback: {timeout_pull_output}")

            ctx.cmd("untangle pole")
            ctx.cmd("bait worm")
            fishing_system.calculate_timeout_tangle_chance = original_timeout_tangle
            fishing_system.calculate_hookup_chance = lambda *_args, **_kwargs: 0.0
            output_index = len(ctx.output_log)
            ctx.cmd("fish")
            run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
            ctx.cmd("pull")
            failed_hook_output = list(ctx.output_log[output_index:])
            if not any("slips" in str(line).lower() or "twists free" in str(line).lower() for line in failed_hook_output):
                raise AssertionError(f"Fishing scenario did not exercise the failed hook branch: {failed_hook_output}")
            if getattr(character.ndb, "fishing_session", None) is not None:
                raise AssertionError("Fishing scenario did not clear the session after a failed hook attempt.")
            assert_no_active_callback("_expire_nibble_window")
            if getattr(character.ndb, "fishing_session", None) is not None:
                raise AssertionError("Fishing scenario let a stale nibble-timeout callback restore state after a failed hook.")

            ctx.cmd("bait worm")
            fishing_system.calculate_hookup_chance = lambda *_args, **_kwargs: 1.0
            fishing_system.resolve_struggle_outcome_data = lambda *_args, **_kwargs: {
                "outcome": "line_break",
                "pressure": 99.0,
                "break_score": 1.0,
                "landed_score": 0.0,
                "lost_score": 0.0,
            }
            output_index = len(ctx.output_log)
            ctx.cmd("fish")
            run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
            ctx.cmd("pull")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "hooked":
                raise AssertionError("Fishing scenario did not transition from nibble to hooked.")
            if not any("jerks violently" in str(line).lower() for line in list(ctx.output_log[output_index:])):
                raise AssertionError("Fishing scenario did not emit hooked-state feedback.")
            assert_no_active_callback("_expire_nibble_window")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "hooked":
                raise AssertionError("Fishing scenario let a stale nibble-timeout callback interrupt the hooked state.")
            run_next(expected_seconds=2.0, callback_name="_resolve_struggle_round")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "broken" or bool(getattr(character.ndb, "is_fishing", False)):
                raise AssertionError("Fishing scenario did not land in the broken-line state cleanly.")
            broken_output = list(ctx.output_log[output_index:])
            if not any("line snaps" in str(line).lower() or "tears the line" in str(line).lower() for line in broken_output):
                raise AssertionError(f"Fishing scenario did not emit broken-line messaging: {broken_output}")
            broken_cast_index = len(ctx.output_log)
            ctx.cmd("fish")
            broken_cast_output = list(ctx.output_log[broken_cast_index:])
            if not any("broken" in str(line).lower() for line in broken_cast_output):
                raise AssertionError(f"Fishing scenario did not block fishing while the line was broken: {broken_cast_output}")
            rig_index = len(ctx.output_log)
            ctx.cmd("rig pole")
            rig_output = list(ctx.output_log[rig_index:])
            if not any("rig the pole" in str(line).lower() or "set the hook and line" in str(line).lower() for line in rig_output):
                raise AssertionError(f"Fishing scenario did not let players rig a broken line back into working order: {rig_output}")
            if not bool(getattr(getattr(pole, "db", None), "line_attached", False)):
                raise AssertionError("Fishing scenario did not restore line attachment after rigging.")
            ctx.cmd("bait worm")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "baited":
                raise AssertionError("Fishing scenario did not let baiting reset the broken-line state.")

            pole.db.line_tangled = True
            untangle_index = len(ctx.output_log)
            ctx.cmd("untangle pole")
            untangle_output = list(ctx.output_log[untangle_index:])
            if not any("line hangs clean" in str(line).lower() or "knots free" in str(line).lower() for line in untangle_output):
                raise AssertionError(f"Fishing scenario did not let players clear a pole tangle manually: {untangle_output}")
            if bool(getattr(getattr(pole, "db", None), "line_tangled", False)):
                raise AssertionError("Fishing scenario did not clear the physical pole tangle state.")

            outcome_queue = [
                {"outcome": "still_fighting", "pressure": 40.0, "break_score": 0.1, "landed_score": 0.3, "lost_score": 0.2},
                {"outcome": "landed", "pressure": 34.0, "break_score": 0.1, "landed_score": 0.6, "lost_score": 0.1},
            ]

            def next_outcome(*_args, **_kwargs):
                if not outcome_queue:
                    raise AssertionError("Fishing scenario exhausted deterministic struggle outcomes.")
                return dict(outcome_queue.pop(0))

            fishing_system.resolve_struggle_outcome_data = next_outcome

            second_cast_output_index = len(ctx.output_log)
            ctx.cmd("fish")
            run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
            ctx.cmd("pull")
            assert_no_active_callback("_expire_nibble_window")

            already_fishing_output = list(ctx.output_log[second_cast_output_index:])
            if not any("jerks violently" in str(line).lower() for line in already_fishing_output):
                raise AssertionError("Fishing scenario did not reach the hooked state for the success path.")

            repeat_gate_index = len(ctx.output_log)
            ctx.cmd("fish")
            repeat_gate_output = list(ctx.output_log[repeat_gate_index:])
            if not any("already fishing" in str(line).lower() for line in repeat_gate_output):
                raise AssertionError(f"Fishing scenario did not gate repeated fish commands during an active hooked session: {repeat_gate_output}")

            ctx.cmd("pull")
            run_next(expected_seconds=2.0, callback_name="_resolve_struggle_round")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or session.state != "hooked" or int(getattr(session, "struggle_round", 0) or 0) < 1:
                raise AssertionError("Fishing scenario did not keep the fish in a multi-round struggle.")

            ctx.cmd("pull")
            run_next(expected_seconds=2.0, callback_name="_resolve_struggle_round")
            success_output = list(ctx.output_log[output_index:])
            if getattr(character.ndb, "fishing_session", None) is not None:
                raise AssertionError("Fishing scenario did not clear the session after a successful catch.")
            if not any("you catch a silver trout" in str(line).lower() for line in success_output):
                raise AssertionError(f"Fishing scenario did not land the hooked fish after the struggle loop: {success_output}")
            caught_fish = [obj for obj in list(character.contents) if getattr(obj, "db", None) and getattr(obj.db, "fish_profile_key", None)]
            stringed_fish = []
            for item in list(character.contents):
                if fishing_economy.is_fish_string(item):
                    stringed_fish.extend([entry for entry in list(getattr(item, "contents", []) or []) if getattr(entry, "db", None) and getattr(entry.db, "fish_profile_key", None)])
            all_caught_fish = list(caught_fish) + list(stringed_fish)
            if not any(getattr(obj, "key", "") == "silver trout" for obj in all_caught_fish):
                raise AssertionError("Fishing scenario did not place the landed fish into a valid carried or stringed location.")
            landed_fish = next(obj for obj in all_caught_fish if getattr(obj, "key", "") == "silver trout")
            if getattr(landed_fish, "location", None) != character:
                landed_fish.move_to(character, quiet=True, use_destination=False)
            if getattr(landed_fish.db, "fish_group", None) != "river 1" or int(getattr(landed_fish.db, "fish_difficulty", 0) or 0) <= 0:
                raise AssertionError("Fishing scenario did not stamp fish-group metadata onto the landed fish.")
            if int(getattr(landed_fish.db, "value", 0) or 0) <= 0 or int(getattr(landed_fish.db, "weight", 0) or 0) <= 0:
                raise AssertionError("Fishing scenario did not stamp weight and value metadata onto the landed fish.")
            if getattr(character.db, "fishing_leaderboard", None) is None:
                raise AssertionError("Fishing scenario did not update the heaviest-fish leaderboard stub.")

            look_index = len(ctx.output_log)
            ctx.cmd("look silver trout")
            look_output = list(ctx.output_log[look_index:])
            if not any("weight:" in str(line).lower() and "value:" in str(line).lower() for line in look_output):
                raise AssertionError(f"Fishing scenario did not expose fish metadata through look: {look_output}")

            weigh_index = len(ctx.output_log)
            ctx.cmd("weigh silver trout")
            weigh_output = list(ctx.output_log[weigh_index:])
            if not any("trophy:" in str(line).lower() and "weight:" in str(line).lower() for line in weigh_output):
                raise AssertionError(f"Fishing scenario did not expose fish metadata through weigh: {weigh_output}")

            fish_string = next(obj for obj in list(character.contents) if bool(getattr(getattr(obj, "db", None), "is_fish_string", False)))
            stow_index = len(ctx.output_log)
            ctx.cmd("stow silver trout in fish string")
            if getattr(landed_fish, "location", None) != fish_string:
                raise AssertionError("Fishing scenario did not allow stowing a fish onto a fish string.")
            stow_output = list(ctx.output_log[stow_index:])
            if not any("secure" in str(line).lower() or "stow" in str(line).lower() or "store" in str(line).lower() for line in stow_output):
                raise AssertionError(f"Fishing scenario did not emit fish-string placement feedback: {stow_output}")

            coins_before_sale = int(getattr(character.db, "coins", 0) or 0)
            expected_single_sale = fishing_economy.get_fish_vendor_sale_value(landed_fish, vendor=supplier)
            sale_index = len(ctx.output_log)
            ctx.cmd("sell silver trout")
            sale_output = list(ctx.output_log[sale_index:])
            coins_after_sale = int(getattr(character.db, "coins", 0) or 0)
            if coins_after_sale - coins_before_sale != expected_single_sale:
                raise AssertionError(
                    f"Fishing scenario did not pay the expected fish-buyer value for a single sale: expected={expected_single_sale}, got={coins_after_sale - coins_before_sale}"
                )
            if any(getattr(obj, "key", "") == "silver trout" for obj in list(fish_string.contents)):
                raise AssertionError("Fishing scenario did not remove the sold fish from the fish string.")
            if not any("old maren" in str(line).lower() or "i'll take it" in str(line).lower() or "fair catch" in str(line).lower() or "fine fish" in str(line).lower() for line in sale_output):
                raise AssertionError(f"Fishing scenario did not emit fish-buyer sale feedback: {sale_output}")

            knife = create_object("typeclasses.weapons.Weapon", key="skinning knife", location=character, home=character)
            original_is_wielding = character.is_wielding
            character.is_wielding = lambda name: str(name or "").strip().lower() == "skinning knife"
            processed_fish = create_object("typeclasses.items.fish.Fish", key="silver trout", location=character, home=character)
            processed_fish.db.fish_profile_key = "silver_trout"
            processed_fish.db.fish_type = "silver trout"
            processed_fish.db.fish_group = "river 1"
            processed_fish.db.weight = 5
            processed_fish.db.value = 16
            fishing_economy.set_fish_economy_metadata(processed_fish, fishing_system.get_fish_profile("silver_trout"), rng=pyrandom.Random(5555))
            processed_index = len(ctx.output_log)
            ctx.cmd("skin silver trout")
            processed_output = list(ctx.output_log[processed_index:])
            processed_goods = [obj for obj in list(character.contents) if str(getattr(getattr(obj, "db", None), "item_type", "") or "") in {"fish_meat", "fish_skin"}]
            if not processed_goods:
                raise AssertionError(f"Fishing scenario did not turn a caught fish into processed goods: {processed_output}")
            if any(obj == processed_fish for obj in list(character.contents)):
                raise AssertionError("Fishing scenario did not consume the source fish during cleaning.")
            if not any("saving meat and skin" in str(line).lower() or "finish with" in str(line).lower() for line in processed_output):
                raise AssertionError(f"Fishing scenario did not emit fish-processing feedback: {processed_output}")

            current_time["value"] += 5.0
            processed_sale_before = int(getattr(character.db, "coins", 0) or 0)
            expected_processed_sale = sum(fishing_economy.get_fish_vendor_sale_value(item, vendor=supplier) for item in processed_goods)
            processed_sale_index = len(ctx.output_log)
            ctx.cmd("sell fish")
            processed_sale_output = list(ctx.output_log[processed_sale_index:])
            processed_sale_after = int(getattr(character.db, "coins", 0) or 0)
            if processed_sale_after - processed_sale_before != expected_processed_sale:
                raise AssertionError(
                    f"Fishing scenario did not pay the expected processed-fish sale value: expected={expected_processed_sale}, got={processed_sale_after - processed_sale_before}, output={processed_sale_output}"
                )
            if not any(
                "salvage item" in str(line).lower() or "salvage items" in str(line).lower()
                for line in processed_sale_output
            ):
                raise AssertionError(f"Fishing scenario did not include processed goods in bulk fish-buyer sales: {processed_sale_output}")
            knife.delete()
            character.is_wielding = original_is_wielding

            character.db.profession = "empath"
            character.db.empath_strain = 0
            character.ndb.next_empath_strain_decay_at = 0.0
            if character.get_empath_strain() != 0:
                raise AssertionError("Fishing scenario did not start the empath strain check from zero.")
            character.apply_fishing_empath_strain("hook", amount=4, fish_profile=fishing_system.get_fish_profile("silver_trout"))
            if character.get_empath_strain() <= 0:
                raise AssertionError("Fishing scenario did not add empath strain from fishing events.")
            current_time["value"] += 25.0
            ctx.direct(character.process_empath_tick)
            if character.get_empath_strain() >= 4:
                raise AssertionError("Fishing scenario did not decay empath strain over time.")
            character.db.profession = "warrior"
            character.db.empath_strain = 0

            stone_profile = fishing_system.get_fish_profile("stone_perch")
            trophy_profile = dict(stone_profile)
            regular_fish = create_object("typeclasses.items.fish.Fish", key="stone perch", location=character, home=character)
            regular_fish.db.fish_profile_key = "stone_perch"
            regular_fish.db.fish_type = trophy_profile.get("display_name", "stone perch")
            regular_fish.db.fish_group = trophy_profile.get("fish_group", "river 1")
            regular_fish.db.weight = 5
            regular_fish.db.value = 14
            fishing_economy.set_fish_economy_metadata(regular_fish, trophy_profile, rng=pyrandom.Random(9999))

            class TrophyRng:
                def random(self):
                    return 0.0

                def uniform(self, low, high):
                    return max(float(low), min(float(high), 2.0))

            trophy_fish = create_object("typeclasses.items.fish.Fish", key="trophy stone perch", location=character, home=character)
            trophy_fish.db.fish_profile_key = "stone_perch"
            trophy_fish.db.fish_type = trophy_profile.get("display_name", "stone perch")
            trophy_fish.db.fish_group = trophy_profile.get("fish_group", "river 1")
            trophy_fish.db.weight = 5
            trophy_fish.db.value = 14
            fishing_economy.set_fish_economy_metadata(trophy_fish, trophy_profile, rng=TrophyRng())
            if not bool(getattr(trophy_fish.db, "is_trophy", False)):
                raise AssertionError("Fishing scenario did not flag a forced trophy fish.")
            if int(getattr(trophy_fish.db, "value", 0) or 0) <= int(getattr(regular_fish.db, "value", 0) or 0):
                raise AssertionError("Fishing scenario did not apply a trophy value multiplier.")

            trophy_look = trophy_fish.return_appearance(character)
            if "Trophy: Yes" not in str(trophy_look):
                raise AssertionError(f"Fishing scenario did not expose trophy status in fish inspection text: {trophy_look}")

            supplier.ndb.fish_buyer_throttle = {str(int(getattr(character, "id", 0) or 0)): current_time["value"] + float(fishing_economy.BUYER_RATE_LIMIT_SECONDS)}
            blocked_sale_index = len(ctx.output_log)
            ctx.cmd("sell trophy stone perch")
            blocked_sale_output = list(ctx.output_log[blocked_sale_index:])
            if not any("moment" in str(line).lower() or "wait" in str(line).lower() for line in blocked_sale_output):
                raise AssertionError(f"Fishing scenario did not rate-limit rapid fish-buyer sales: {blocked_sale_output}")

            current_time["value"] += 5.0
            trophy_sale_before = int(getattr(character.db, "coins", 0) or 0)
            expected_trophy_sale = fishing_economy.get_fish_vendor_sale_value(trophy_fish, vendor=supplier)
            trophy_sale_index = len(ctx.output_log)
            ctx.cmd("sell trophy stone perch")
            trophy_sale_output = list(ctx.output_log[trophy_sale_index:])
            trophy_sale_after = int(getattr(character.db, "coins", 0) or 0)
            if trophy_sale_after - trophy_sale_before != expected_trophy_sale:
                raise AssertionError(
                    f"Fishing scenario did not pay the expected trophy sale value: expected={expected_trophy_sale}, got={trophy_sale_after - trophy_sale_before}"
                )
            if not any("remarkable catch" in str(line).lower() for line in trophy_sale_output):
                raise AssertionError(f"Fishing scenario did not emit higher-tier buyer reaction text for a trophy fish: {trophy_sale_output}")

            rock = create_object("typeclasses.objects.Object", key="rock", location=character, home=character)
            rock.db.weight = 1
            bulk_string_fish = create_object("typeclasses.items.fish.Fish", key="mud carp", location=character, home=character)
            bulk_string_fish.db.fish_profile_key = "mud_carp"
            bulk_string_fish.db.fish_type = "mud carp"
            bulk_string_fish.db.fish_group = "river 1"
            bulk_string_fish.db.weight = 4
            bulk_string_fish.db.value = 9
            fishing_economy.set_fish_economy_metadata(bulk_string_fish, fishing_system.get_fish_profile("mud_carp"), rng=pyrandom.Random(2222))
            fish_string.store_item(bulk_string_fish)

            bulk_inventory_fish = create_object("typeclasses.items.fish.Fish", key="silver trout", location=character, home=character)
            bulk_inventory_fish.db.fish_profile_key = "silver_trout"
            bulk_inventory_fish.db.fish_type = "silver trout"
            bulk_inventory_fish.db.fish_group = "river 1"
            bulk_inventory_fish.db.weight = 5
            bulk_inventory_fish.db.value = 16
            fishing_economy.set_fish_economy_metadata(bulk_inventory_fish, fishing_system.get_fish_profile("silver_trout"), rng=pyrandom.Random(3333))

            current_time["value"] += float(fishing_economy.BUYER_RATE_LIMIT_SECONDS)
            expected_bulk_sale = sum(fishing_economy.get_fish_vendor_sale_value(fish, vendor=supplier) for fish in (bulk_string_fish, bulk_inventory_fish, regular_fish))
            bulk_sale_before = int(getattr(character.db, "coins", 0) or 0)
            bulk_sale_index = len(ctx.output_log)
            ctx.cmd("sell fish")
            bulk_sale_output = list(ctx.output_log[bulk_sale_index:])
            bulk_sale_after = int(getattr(character.db, "coins", 0) or 0)
            if bulk_sale_after - bulk_sale_before != expected_bulk_sale:
                raise AssertionError(
                    f"Fishing scenario did not pay the expected bulk fish total: expected={expected_bulk_sale}, got={bulk_sale_after - bulk_sale_before}, output={bulk_sale_output}"
                )
            if getattr(rock, "location", None) != character:
                raise AssertionError("Fishing scenario let sell fish consume non-fish inventory.")
            if any(fishing_economy.is_fish_item(obj) for obj in list(character.contents)):
                raise AssertionError("Fishing scenario did not clear carried fish after sell fish.")
            if any(fishing_economy.is_fish_item(obj) for obj in list(fish_string.contents)):
                raise AssertionError("Fishing scenario did not clear fish-string contents after sell fish.")
            if not any("sell 3 fish" in str(line).lower() for line in bulk_sale_output):
                raise AssertionError(f"Fishing scenario did not report the bulk fish summary: {bulk_sale_output}")

            ctx.cmd("north")
            no_vendor_sale_index = len(ctx.output_log)
            ctx.cmd("sell fish")
            no_vendor_sale_output = list(ctx.output_log[no_vendor_sale_index:])
            if not any("no vendor here" in str(line).lower() or "no one here is buying fish" in str(line).lower() for line in no_vendor_sale_output):
                raise AssertionError(f"Fishing scenario did not fail fish sales away from Old Maren: {no_vendor_sale_output}")
            ctx.cmd("south")

            fishing_system.resolve_struggle_outcome_data = lambda *_args, **_kwargs: {
                "outcome": "landed",
                "pressure": 32.0,
                "break_score": 0.0,
                "landed_score": 0.9,
                "lost_score": 0.0,
            }
            ctx.cmd("bait worm")
            auto_string_index = len(ctx.output_log)
            ctx.cmd("fish")
            run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
            ctx.cmd("pull")
            run_next(expected_seconds=2.0, callback_name="_resolve_struggle_round")
            auto_string_output = list(ctx.output_log[auto_string_index:])
            if not any("fish string" in str(line).lower() for line in auto_string_output):
                raise AssertionError(f"Fishing scenario did not report auto-stringing on a successful catch: {auto_string_output}")
            if not any(fishing_economy.is_fish_item(obj) for obj in list(fish_string.contents)):
                raise AssertionError("Fishing scenario did not place a newly caught fish onto the existing fish string.")

            for obj in list(fish_string.contents):
                obj.delete()
            fish_string.delete()
            original_can_receive = fishing_economy.can_receive_caught_fish
            fishing_economy.can_receive_caught_fish = lambda *_args, **_kwargs: False
            try:
                ctx.cmd("bait worm")
                overflow_index = len(ctx.output_log)
                ctx.cmd("fish")
                run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
                ctx.cmd("pull")
                run_next(expected_seconds=2.0, callback_name="_resolve_struggle_round")
            finally:
                fishing_economy.can_receive_caught_fish = original_can_receive
            overflow_output = list(ctx.output_log[overflow_index:])
            if not any("slips away" in str(line).lower() and "nowhere to secure" in str(line).lower() for line in overflow_output):
                raise AssertionError(f"Fishing scenario did not emit clear overflow-loss messaging: {overflow_output}")

            trace_entries = list(getattr(character.ndb, "fishing_debug_trace", []) or [])
            trace_events = [str(entry.get("event", "") or "") for entry in trace_entries]
            if "cast_started" not in trace_events or "hook_check" not in trace_events or "struggle_round" not in trace_events:
                raise AssertionError(f"Fishing scenario did not record expected debug trace events: {trace_events}")

            ctx.cmd("bait worm")
            output_index = len(ctx.output_log)
            ctx.cmd("fish")
            if not bool(getattr(character.ndb, "is_fishing", False)):
                raise AssertionError("Fishing scenario did not mark the cast as active before movement interruption.")
            ctx.cmd("north")
            interrupt_output = list(ctx.output_log[output_index:])
            if not any("disturb the line" in str(line).lower() for line in interrupt_output):
                raise AssertionError(f"Fishing scenario did not report movement interruption: {interrupt_output}")
            if getattr(character.ndb, "fishing_session", None) is not None:
                raise AssertionError("Fishing scenario did not clear the session on movement interruption.")
            if bool(getattr(character.ndb, "is_fishing", False)):
                raise AssertionError("Fishing scenario did not clear active fishing state on movement interruption.")
            assert_no_active_callback("_begin_nibble")
            if getattr(character.ndb, "fishing_session", None) is not None:
                raise AssertionError("Fishing scenario let a stale movement-interrupted callback recreate fishing state.")

            ctx.cmd("bait worm")
            ctx.cmd("south")
            ctx.cmd("fish")
            session = getattr(character.ndb, "fishing_session", None)
            if session is None or str(getattr(session, "state", "") or "") != "cast":
                raise AssertionError("Fishing scenario did not start an active cast before unpuppet cleanup validation.")
            ctx.direct(character.at_post_unpuppet)
            if getattr(character.ndb, "fishing_session", None) is not None or bool(getattr(character.ndb, "is_fishing", False)):
                raise AssertionError("Fishing scenario did not clear fishing state on unpuppet cleanup.")
            assert_no_active_callback("_begin_nibble")
            if getattr(character.ndb, "fishing_session", None) is not None:
                raise AssertionError("Fishing scenario let a stale unpuppet callback recreate fishing state.")
        finally:
            fishing_system.delay = original_delay
            fishing_system.time.time = original_time
            fishing_system.random.random = original_random
            fishing_system.random.choice = original_choice
            fishing_system.random.randint = original_randint
            fishing_system.choose_weighted_fish_profile = original_choose_weighted
            fishing_system.calculate_nibble_chance = original_nibble_chance
            fishing_system.calculate_hookup_chance = original_hookup_chance
            fishing_system.calculate_timeout_tangle_chance = original_timeout_tangle
            fishing_system.resolve_struggle_outcome_data = original_resolve_struggle
            fishing_economy.time.time = original_fishing_economy_time

        ctx.assert_invariant("character_exists")
        after_pool = float(getattr(character.exp_skills.get("outdoorsmanship"), "pool", 0.0) or 0.0)
        if after_pool <= before_pool:
            raise AssertionError(f"Fishing scenario did not grant Outdoorsmanship XP across the mechanics loop: before={before_pool}, after={after_pool}")
        after_mechanical_pool = float(getattr(character.exp_skills.get("mechanical_lore"), "pool", 0.0) or 0.0)
        if after_mechanical_pool <= before_mechanical_pool:
            raise AssertionError(
                f"Fishing scenario did not grant Mechanical Lore XP on bait usage: before={before_mechanical_pool}, after={after_mechanical_pool}"
            )
        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "outdoorsmanship_pool_before": before_pool,
            "outdoorsmanship_pool_after": after_pool,
            "mechanical_lore_pool_before": before_mechanical_pool,
            "mechanical_lore_pool_after": after_mechanical_pool,
            "coins": int(getattr(character.db, "coins", 0) or 0),
            "inventory": [getattr(obj, "key", "") for obj in list(character.contents)],
            "final_room": getattr(getattr(character, "location", None), "key", None),
            "debug_trace_events": [str(entry.get("event", "") or "") for entry in list(getattr(character.ndb, "fishing_debug_trace", []) or [])],
            "scheduled_callbacks_remaining": len(scheduled),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="fishing-vertical-slice",
        scenario_metadata=getattr(run_fishing_vertical_slice_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "fishing-junk-event-slice",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Fishing junk and event validation should report lag telemetry without masking weighted outcome or safe-zone regressions.",
    },
)
def run_fishing_junk_event_slice_scenario(args):
    _setup_django()

    def scenario(ctx):
        import random as pyrandom

        from evennia.utils.create import create_object

        import world.systems.fishing as fishing_system
        import world.systems.fishing_economy as fishing_economy

        water_room = ctx.harness.create_test_room(key="TEST_FISHING_JUNK_ROOM")
        water_room.db.fishable = True
        water_room.db.fish_group = "River 1"
        water_room.db.safe_zone = True

        character = ctx.harness.create_test_character(room=water_room, key="TEST_FISHING_JUNK_CHAR")
        ctx.character = character
        ctx.room = water_room
        character.db.stats = {"reflex": 14, "discipline": 14, "agility": 14}
        character.learn_skill("outdoorsmanship", {"rank": 70, "mindstate": 0})
        character.learn_skill("skinning", {"rank": 70, "mindstate": 0})

        supplier = create_object("typeclasses.fishing_supplier.FishingSupplier", key="Old Maren", location=water_room, home=water_room)
        create_object("typeclasses.weigh_station.WeighStation", key="dock scale", location=water_room, home=water_room)

        current_time = {"value": 1000.0}
        scheduled = []
        original_delay = fishing_system.delay
        original_time = fishing_system.time.time
        original_fishing_economy_time = fishing_economy.time.time
        original_roll_outcome = fishing_system.roll_fishing_outcome

        class FakeDelayedTask:
            def __init__(self):
                self.cancelled = False

            def cancel(self):
                self.cancelled = True

        def fake_delay(seconds, callback, *cb_args, **cb_kwargs):
            task = FakeDelayedTask()
            scheduled.append(
                {
                    "seconds": float(seconds),
                    "callback": callback,
                    "callback_name": getattr(callback, "__name__", "callback"),
                    "args": cb_args,
                    "kwargs": cb_kwargs,
                    "task": task,
                }
            )
            return task

        def run_next(expected_seconds=None, callback_name=None, min_seconds=None, max_seconds=None):
            for index, event in enumerate(list(scheduled)):
                task = event.get("task")
                if task is not None and bool(getattr(task, "cancelled", False)):
                    continue
                seconds = float(event.get("seconds", 0.0) or 0.0)
                if callback_name and str(event.get("callback_name", "") or "") != str(callback_name):
                    continue
                if expected_seconds is not None and abs(seconds - float(expected_seconds)) > 0.01:
                    continue
                if min_seconds is not None and seconds < float(min_seconds):
                    continue
                if max_seconds is not None and seconds > float(max_seconds):
                    continue
                scheduled.pop(index)
                current_time["value"] += seconds
                ctx.direct(event["callback"], *(event.get("args") or ()), **(event.get("kwargs") or {}))
                return seconds
            raise AssertionError(
                f"Fishing junk/event slice expected callback={callback_name or 'any'} seconds={expected_seconds} range=({min_seconds}, {max_seconds}), but found {scheduled}."
            )

        junk_item = None
        try:
            fishing_system.delay = fake_delay
            fishing_system.time.time = lambda: current_time["value"]
            fishing_economy.time.time = lambda: current_time["value"]

            river_one_common = {
                fishing_system.choose_weighted_junk_profile("River 1", "common", rng=pyrandom.Random(seed)).get("group")
                for seed in range(1, 8)
            }
            river_two_common = {
                fishing_system.choose_weighted_junk_profile("River 2", "common", rng=pyrandom.Random(seed)).get("group")
                for seed in range(10, 17)
            }
            ocean_interesting = {
                fishing_system.choose_weighted_junk_profile("Ocean", "interesting", rng=pyrandom.Random(seed)).get("group")
                for seed in range(20, 27)
            }
            event_profile = fishing_system.choose_weighted_junk_profile("River 1", "event", rng=pyrandom.Random(99))
            if river_one_common != {"River 1"} or river_two_common != {"River 2"} or ocean_interesting != {"Ocean"}:
                raise AssertionError("Fishing junk tables leaked entries across fish-group boundaries.")
            if str(event_profile.get("key", "") or "") != "violent_tug":
                raise AssertionError("Fishing event table did not produce the violent tug profile.")

            ctx.cmd("ask maren for gear")
            fishing_system.roll_fishing_outcome = lambda room_or_group, rng=None: {
                "category": "junk",
                "profile": fishing_system.choose_weighted_junk_profile(room_or_group, "interesting", rng=pyrandom.Random(5)),
            }
            coins_before_junk = int(getattr(character.db, "coins", 0) or 0)
            ctx.cmd("bait worm")
            ctx.cmd("fish")
            run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
            session = fishing_system.get_fishing_session(character, create=False)
            if session is None or session.state != "junk":
                raise AssertionError("Fishing junk slice did not enter the junk resolution state.")
            junk_output_index = len(ctx.output_log)
            ctx.cmd("pull")
            junk_output = " ".join(str(line) for line in list(ctx.output_log)[junk_output_index:])
            if "something unexpected" not in junk_output.lower():
                raise AssertionError("Fishing junk slice did not show the valuable-junk pull message.")
            junk_item = next((obj for obj in list(character.contents) if fishing_economy.is_junk_item(obj)), None)
            if junk_item is None:
                raise AssertionError("Fishing junk slice did not create a junk item on pull.")
            if int(getattr(junk_item.db, "value", 0) or 0) < 8:
                raise AssertionError("Fishing junk slice valuable salvage value was lower than expected.")
            current_time["value"] += 1.0
            sell_redirect_index = len(ctx.output_log)
            ctx.cmd(f"sell {junk_item.key} to maren")
            sell_redirect_output = list(ctx.output_log[sell_redirect_index:])
            if int(getattr(character.db, "coins", 0) or 0) <= coins_before_junk:
                raise AssertionError("Fishing junk slice did not let the supplier buy junk.")
            if not any("lucky pull" in str(line).lower() or "not much" in str(line).lower() for line in sell_redirect_output):
                raise AssertionError(f"Fishing junk slice did not support sell <item> to <npc> syntax cleanly: {sell_redirect_output}")

            pole = fishing_system.get_fishing_pole(character)
            fishing_system.roll_fishing_outcome = lambda room_or_group, rng=None: {
                "category": "event",
                "profile": fishing_system.choose_weighted_junk_profile(room_or_group, "event", rng=pyrandom.Random(7)),
            }
            prompt = fishing_system.get_event_choice_prompt(event_profile)
            if "pull harder" not in str(prompt.get("prompt", "") or "").lower():
                raise AssertionError("Fishing junk slice did not expose the future event choice hook prompt.")
            npcs_before = len([obj for obj in list(water_room.contents) if bool(getattr(getattr(obj, "db", None), "is_npc", False))])
            ctx.cmd("bait worm")
            ctx.cmd("fish")
            run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
            session = fishing_system.get_fishing_session(character, create=False)
            if session is None or session.state != "event":
                raise AssertionError("Fishing junk slice did not enter the violent tug event state.")
            ctx.cmd("pull")
            npcs_after = len([obj for obj in list(water_room.contents) if bool(getattr(getattr(obj, "db", None), "is_npc", False))])
            if npcs_after != npcs_before:
                raise AssertionError("Fishing junk slice spawned an uncontrolled NPC in a safe-zone event resolution.")
            if pole is None or bool(getattr(pole.db, "line_attached", True)):
                raise AssertionError("Fishing junk slice did not break the line on violent tug resolution.")
            if fishing_system.get_fishing_session(character, create=False) is not None:
                raise AssertionError("Fishing junk slice left a stale fishing session after resolving the event.")
            repair_output_index = len(ctx.output_log)
            ctx.cmd("rig pole")
            repair_output = " ".join(str(line) for line in list(ctx.output_log)[repair_output_index:])
            if "rig" not in repair_output.lower():
                raise AssertionError("Fishing junk slice did not allow the pole to be repaired after a violent tug event.")
        finally:
            fishing_system.delay = original_delay
            fishing_system.time.time = original_time
            fishing_economy.time.time = original_fishing_economy_time
            fishing_system.roll_fishing_outcome = original_roll_outcome

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "junk_vendor_accepts": bool(fishing_economy.is_fish_trade_item(junk_item)) if junk_item else False,
            "event_safe_zone": bool(getattr(getattr(water_room, "db", None), "safe_zone", False)),
            "scheduled_callbacks_remaining": len(scheduled),
            "supplier": getattr(supplier, "key", None),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="fishing-junk-event-slice",
        scenario_metadata=getattr(run_fishing_junk_event_slice_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "fishing-simulation-100",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "The long-form fishing balance simulation should emit lag telemetry and a report even on slower environments.",
    },
)
def run_fishing_simulation_100_scenario(args):
    _setup_django()

    def scenario(ctx):
        import builtins

        from evennia.utils.create import create_object

        import typeclasses.characters as character_typeclasses
        import world.systems.fishing as fishing_system
        import world.systems.fishing_economy as fishing_economy

        report_path = Path(__file__).resolve().parent / "docs" / "systems" / "fishingSimulationReport.md"

        def skill_snapshot(character, skill_name):
            skill = character.exp_skills.get(skill_name)
            if skill is None:
                return {"pool": 0.0, "mindstate": 0}
            return {
                "pool": float(getattr(skill, "pool", 0.0) or 0.0),
                "mindstate": int(getattr(skill, "mindstate", 0) or 0),
            }

        def fish_string_contents(character):
            fish_string = fishing_economy.find_fish_string(character)
            return fish_string, list(getattr(fish_string, "contents", []) or []) if fish_string else []

        def category_percentages(summary):
            total = max(1, int(summary.get("runs", 0) or 0))
            return {
                "fish": (float(summary["category_counts"].get("fish", 0)) / float(total)) * 100.0,
                "junk": (float(summary["junk_tiers"].get("common", 0)) / float(total)) * 100.0,
                "valuable_junk": (float(summary["junk_tiers"].get("interesting", 0)) / float(total)) * 100.0,
                "event": (float(summary["category_counts"].get("event", 0)) / float(total)) * 100.0,
            }

        def run_pass(pass_name, run_count):
            room = ctx.harness.create_test_room(key=f"TEST_FISHING_SIM_ROOM_{pass_name}")
            room.db.fishable = True
            room.db.fish_group = "River 1"
            room.db.safe_zone = True

            character = ctx.harness.create_test_character(room=room, key=f"TEST_FISHING_SIM_{pass_name}")
            ctx.character = character
            ctx.room = room
            character.ndb.fishing_debug = True
            character.ndb.fishing_debug_trace = []
            character.db.stats = {"reflex": 18, "discipline": 18, "agility": 16}
            character.set_profession("Ranger")
            character.learn_skill("outdoorsmanship", {"rank": 85, "mindstate": 0})
            character.learn_skill("skinning", {"rank": 75, "mindstate": 0})
            character.learn_skill("trading", {"rank": 45, "mindstate": 0})
            character.learn_skill("scholarship", {"rank": 30, "mindstate": 0})
            character.learn_skill("mechanical_lore", {"rank": 15, "mindstate": 0})

            supplier = create_object("typeclasses.fishing_supplier.FishingSupplier", key="Old Maren", location=room, home=room)
            create_object("typeclasses.weigh_station.WeighStation", key=f"dock scale {pass_name}", location=room, home=room)
            create_object("typeclasses.weapons.Weapon", key="skinning knife", location=character, home=character)
            character.is_wielding = lambda weapon_name: str(weapon_name or "").strip().lower() == "skinning knife"

            current_time = {"value": 2000.0}
            scheduled = []
            original_delay = fishing_system.delay
            original_time = fishing_system.time.time
            original_fishing_economy_time = fishing_economy.time.time
            original_hookup = fishing_system.calculate_hookup_chance
            original_timeout_tangle = fishing_system.calculate_timeout_tangle_chance
            original_resolve_struggle = fishing_system.resolve_struggle_outcome_data
            original_run_contest = character_typeclasses.run_contest
            original_print = builtins.print

            class FakeDelayedTask:
                def __init__(self):
                    self.cancelled = False

                def cancel(self):
                    self.cancelled = True

            def fake_delay(seconds, callback, *cb_args, **cb_kwargs):
                task = FakeDelayedTask()
                scheduled.append(
                    {
                        "seconds": float(seconds),
                        "callback": callback,
                        "callback_name": getattr(callback, "__name__", "callback"),
                        "args": cb_args,
                        "kwargs": cb_kwargs,
                        "task": task,
                    }
                )
                return task

            def run_next(expected_seconds=None, callback_name=None, min_seconds=None, max_seconds=None):
                for index, event in enumerate(list(scheduled)):
                    task = event.get("task")
                    if task is not None and bool(getattr(task, "cancelled", False)):
                        continue
                    seconds = float(event.get("seconds", 0.0) or 0.0)
                    if callback_name and str(event.get("callback_name", "") or "") != str(callback_name):
                        continue
                    if expected_seconds is not None and abs(seconds - float(expected_seconds)) > 0.01:
                        continue
                    if min_seconds is not None and seconds < float(min_seconds):
                        continue
                    if max_seconds is not None and seconds > float(max_seconds):
                        continue
                    scheduled.pop(index)
                    current_time["value"] += seconds
                    ctx.direct(event["callback"], *(event.get("args") or ()), **(event.get("kwargs") or {}))
                    return seconds
                raise AssertionError(
                    f"Fishing simulation expected callback={callback_name or 'any'} seconds={expected_seconds} range=({min_seconds}, {max_seconds}), but found {scheduled}."
                )

            summary = {
                "pass_name": pass_name,
                "runs": int(run_count),
                "category_counts": Counter(),
                "junk_tiers": Counter(),
                "fish_counts": Counter(),
                "junk_counts": Counter(),
                "failure_counts": Counter(),
                "line_breaks": 0,
                "violent_tugs": 0,
                "gear_damage_events": 0,
                "sales_total": 0,
                "sales_by_category": Counter(),
                "outdoorsmanship_pool_gain": 0.0,
                "skinning_pool_gain": 0.0,
                "mindstate_start": {
                    "outdoorsmanship": skill_snapshot(character, "outdoorsmanship")["mindstate"],
                    "skinning": skill_snapshot(character, "skinning")["mindstate"],
                },
                "bite_delays": [],
                "run_records": [],
            }

            try:
                fishing_system.delay = fake_delay
                fishing_system.time.time = lambda: current_time["value"]
                fishing_economy.time.time = lambda: current_time["value"]
                fishing_system.calculate_hookup_chance = lambda *a, **kw: 1.0
                fishing_system.calculate_timeout_tangle_chance = lambda *a, **kw: 0.0
                fishing_system.resolve_struggle_outcome_data = lambda actor, session, fish_profile, bait_item, rng=None: {
                    "outcome": "landed",
                    "pressure": 0.0,
                    "landed_score": 1.0,
                    "lost_score": 0.0,
                    "break_score": 0.0,
                }
                character_typeclasses.run_contest = lambda *a, **kw: {"outcome": "success"}
                builtins.print = lambda *a, **kw: None

                for run_index in range(1, run_count + 1):
                    outdoors_before = skill_snapshot(character, "outdoorsmanship")
                    skinning_before = skill_snapshot(character, "skinning")
                    coins_before = int(getattr(character.db, "coins", 0) or 0)
                    record = {
                        "run": run_index,
                        "outcome": None,
                        "fish": None,
                        "junk": None,
                        "sale_value": 0,
                        "failure": None,
                        "line_break": False,
                        "violent_tug": False,
                    }

                    fishing_system.reset_fishing_session(character)
                    ctx.cmd("ask maren for gear")
                    pole = fishing_system.get_fishing_pole(character)
                    if pole is not None:
                        pole.db.line_attached = True
                        pole.db.hook_attached = True
                        pole.db.line_tangled = False
                    ctx.cmd("rig pole")
                    ctx.cmd("bait worm")
                    ctx.cmd("fish")
                    bite_delay = run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
                    summary["bite_delays"].append(float(bite_delay))
                    record["bite_delay"] = float(bite_delay)

                    session = fishing_system.get_fishing_session(character, create=False)
                    if session is None:
                        record["failure"] = "missing_session"
                        summary["failure_counts"]["missing_session"] += 1
                        summary["run_records"].append(record)
                        scheduled.clear()
                        continue

                    category = str(getattr(session, "outcome_type", session.state) or session.state)
                    if category == "junk":
                        record["outcome"] = "junk"
                        ctx.cmd("pull")
                        junk_item = next((obj for obj in list(character.contents) if fishing_economy.is_junk_item(obj)), None)
                        if junk_item is None:
                            record["failure"] = "missing_junk"
                            summary["failure_counts"]["missing_junk"] += 1
                        else:
                            tier = str(getattr(junk_item.db, "junk_tier", "common") or "common")
                            record["junk"] = str(getattr(junk_item, "key", "junk") or "junk")
                            summary["category_counts"]["junk"] += 1
                            summary["junk_tiers"][tier] += 1
                            summary["junk_counts"][record["junk"]] += 1
                            current_time["value"] += 1.0
                            ctx.cmd(f"sell {junk_item.key}")
                    elif category == "event":
                        record["outcome"] = "event"
                        summary["category_counts"]["event"] += 1
                        summary["violent_tugs"] += 1
                        pole = fishing_system.get_fishing_pole(character)
                        ctx.cmd("pull")
                        line_attached = bool(getattr(getattr(pole, "db", None), "line_attached", False)) if pole is not None else False
                        if not line_attached:
                            record["line_break"] = True
                            summary["line_breaks"] += 1
                            summary["gear_damage_events"] += 1
                        record["violent_tug"] = True
                    else:
                        record["outcome"] = "fish"
                        ctx.cmd("pull")
                        run_next(expected_seconds=2.0, callback_name="_resolve_struggle_round")
                        fish_string, string_contents = fish_string_contents(character)
                        fish_item = next((obj for obj in list(character.contents) if fishing_economy.is_fish_item(obj)), None)
                        if fish_item is None and string_contents:
                            fish_item = string_contents[0]
                            ctx.cmd(f"get {fish_item.key} from fish string")
                        if fish_item is None:
                            record["failure"] = "missing_fish"
                            summary["failure_counts"]["missing_fish"] += 1
                        else:
                            species = str(getattr(fish_item, "key", "fish") or "fish")
                            record["fish"] = species
                            summary["category_counts"]["fish"] += 1
                            summary["fish_counts"][species] += 1
                            ctx.cmd(f"skin {species}")
                            current_time["value"] += 1.0
                            ctx.cmd("sell fish")

                    record["sale_value"] = int(getattr(character.db, "coins", 0) or 0) - coins_before
                    if record["sale_value"] > 0:
                        summary["sales_total"] += record["sale_value"]
                        summary["sales_by_category"][record["outcome"] or "unknown"] += record["sale_value"]

                    outdoors_after = skill_snapshot(character, "outdoorsmanship")
                    skinning_after = skill_snapshot(character, "skinning")
                    summary["outdoorsmanship_pool_gain"] += outdoors_after["pool"] - outdoors_before["pool"]
                    summary["skinning_pool_gain"] += skinning_after["pool"] - skinning_before["pool"]
                    summary["run_records"].append(record)
                    scheduled.clear()
                    current_time["value"] += 0.5

                summary["mindstate_end"] = {
                    "outdoorsmanship": skill_snapshot(character, "outdoorsmanship")["mindstate"],
                    "skinning": skill_snapshot(character, "skinning")["mindstate"],
                }
                summary["coins"] = int(getattr(character.db, "coins", 0) or 0)
                summary["scheduled_callbacks_remaining"] = len(scheduled)
                summary["supplier"] = getattr(supplier, "key", None)
            finally:
                fishing_system.delay = original_delay
                fishing_system.time.time = original_time
                fishing_economy.time.time = original_fishing_economy_time
                fishing_system.calculate_hookup_chance = original_hookup
                fishing_system.calculate_timeout_tangle_chance = original_timeout_tangle
                fishing_system.resolve_struggle_outcome_data = original_resolve_struggle
                character_typeclasses.run_contest = original_run_contest
                builtins.print = original_print

            return summary

        pass_one = run_pass("A", 100)
        pass_two = run_pass("B", 100)
        expected = {"fish": 64.0, "junk": 28.0, "valuable_junk": 6.0, "event": 2.0}
        pass_one_pct = category_percentages(pass_one)
        pass_two_pct = category_percentages(pass_two)
        average_pct = {
            key: (pass_one_pct[key] + pass_two_pct[key]) / 2.0
            for key in ["fish", "junk", "valuable_junk", "event"]
        }
        variance = {
            key: abs(pass_one_pct[key] - pass_two_pct[key])
            for key in ["fish", "junk", "valuable_junk", "event"]
        }
        combined_bite_delays = list(pass_one.get("bite_delays", []) or []) + list(pass_two.get("bite_delays", []) or [])
        bite_timing = {
            "avg": (sum(combined_bite_delays) / len(combined_bite_delays)) if combined_bite_delays else 0.0,
            "min": min(combined_bite_delays) if combined_bite_delays else 0.0,
            "max": max(combined_bite_delays) if combined_bite_delays else 0.0,
        }

        junk_issue = "No."
        if average_pct["junk"] > 35.0:
            junk_issue = "Yes. Common junk is showing up too often."
        elif average_pct["junk"] < 22.0:
            junk_issue = "Yes. Common junk is too rare to feel present."

        valuable_issue = "No."
        if average_pct["valuable_junk"] > 9.0:
            valuable_issue = "Yes. Valuable junk is too generous."
        elif average_pct["valuable_junk"] < 3.0:
            valuable_issue = "Yes. Valuable junk is too rare to notice."

        event_issue = "Yes."
        if average_pct["event"] > 4.0:
            event_issue = "No. Violent tug events are too common."
        elif average_pct["event"] < 1.0:
            event_issue = "No. Violent tug events are too rare to register."

        report_lines = [
            "# Fishing Simulation Report",
            "",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "Scenario: fishing-simulation-100",
            "Runs per pass: 100",
            "Passes: 2",
            "Fish group: River 1",
            "Location safety: safe-zone enabled",
            "",
            "## Expected Distribution",
            f"- Fish: {expected['fish']:.1f}%",
            f"- Common junk: {expected['junk']:.1f}%",
            f"- Valuable junk: {expected['valuable_junk']:.1f}%",
            f"- Event: {expected['event']:.1f}%",
            "",
            "## Pass A",
            f"- Fish: {pass_one['category_counts'].get('fish', 0)} ({pass_one_pct['fish']:.1f}%)",
            f"- Common junk: {pass_one['junk_tiers'].get('common', 0)} ({pass_one_pct['junk']:.1f}%)",
            f"- Valuable junk: {pass_one['junk_tiers'].get('interesting', 0)} ({pass_one_pct['valuable_junk']:.1f}%)",
            f"- Event: {pass_one['category_counts'].get('event', 0)} ({pass_one_pct['event']:.1f}%)",
            f"- Total value sold: {pass_one['sales_total']} coins",
            f"- Average sale per run: {pass_one['sales_total'] / max(1, pass_one['runs']):.2f} coins",
            f"- Outdoorsmanship pool gain: {pass_one['outdoorsmanship_pool_gain']:.2f}",
            f"- Skinning pool gain: {pass_one['skinning_pool_gain']:.2f}",
            f"- Mindstates: outdoorsmanship {pass_one['mindstate_start']['outdoorsmanship']} -> {pass_one['mindstate_end']['outdoorsmanship']}, skinning {pass_one['mindstate_start']['skinning']} -> {pass_one['mindstate_end']['skinning']}",
            f"- Violent tug line breaks: {pass_one['line_breaks']}",
            f"- Failure count: {sum(pass_one['failure_counts'].values())}",
            "",
            "## Pass B",
            f"- Fish: {pass_two['category_counts'].get('fish', 0)} ({pass_two_pct['fish']:.1f}%)",
            f"- Common junk: {pass_two['junk_tiers'].get('common', 0)} ({pass_two_pct['junk']:.1f}%)",
            f"- Valuable junk: {pass_two['junk_tiers'].get('interesting', 0)} ({pass_two_pct['valuable_junk']:.1f}%)",
            f"- Event: {pass_two['category_counts'].get('event', 0)} ({pass_two_pct['event']:.1f}%)",
            f"- Total value sold: {pass_two['sales_total']} coins",
            f"- Average sale per run: {pass_two['sales_total'] / max(1, pass_two['runs']):.2f} coins",
            f"- Outdoorsmanship pool gain: {pass_two['outdoorsmanship_pool_gain']:.2f}",
            f"- Skinning pool gain: {pass_two['skinning_pool_gain']:.2f}",
            f"- Mindstates: outdoorsmanship {pass_two['mindstate_start']['outdoorsmanship']} -> {pass_two['mindstate_end']['outdoorsmanship']}, skinning {pass_two['mindstate_start']['skinning']} -> {pass_two['mindstate_end']['skinning']}",
            f"- Violent tug line breaks: {pass_two['line_breaks']}",
            f"- Failure count: {sum(pass_two['failure_counts'].values())}",
            "",
            "## Catch Breakdown",
            f"- Pass A fish: {dict(pass_one['fish_counts'])}",
            f"- Pass A junk: {dict(pass_one['junk_counts'])}",
            f"- Pass B fish: {dict(pass_two['fish_counts'])}",
            f"- Pass B junk: {dict(pass_two['junk_counts'])}",
            "",
            "## Distribution Comparison",
            f"- Fish actual vs expected: {average_pct['fish']:.1f}% vs {expected['fish']:.1f}%",
            f"- Common junk actual vs expected: {average_pct['junk']:.1f}% vs {expected['junk']:.1f}%",
            f"- Valuable junk actual vs expected: {average_pct['valuable_junk']:.1f}% vs {expected['valuable_junk']:.1f}%",
            f"- Event actual vs expected: {average_pct['event']:.1f}% vs {expected['event']:.1f}%",
            f"- Pass variance: {variance}",
            "",
            "## Bite Timing",
            f"- Avg: {bite_timing['avg']:.1f}s",
            f"- Min: {bite_timing['min']:.1f}s",
            f"- Max: {bite_timing['max']:.1f}s",
            "",
            "## Balance Answers",
            f"- Is junk too frequent? {junk_issue}",
            f"- Are valuable junk items too generous? {valuable_issue}",
            f"- Are violent tug events noticeable but not annoying? {event_issue}",
            f"- Stable across rerun? {'Yes.' if max(variance.values()) <= 10.0 else 'No. Variance exceeded the acceptable 10% band.'}",
            "",
            "## Safety",
            f"- Total violent tug events: {pass_one['violent_tugs'] + pass_two['violent_tugs']}",
            f"- Total line breaks: {pass_one['line_breaks'] + pass_two['line_breaks']}",
            f"- Total gear damage events: {pass_one['gear_damage_events'] + pass_two['gear_damage_events']}",
            f"- Total failures: {sum(pass_one['failure_counts'].values()) + sum(pass_two['failure_counts'].values())}",
        ]
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "pass_one": pass_one,
            "pass_two": pass_two,
            "expected_distribution": expected,
            "average_distribution": average_pct,
            "bite_timing": bite_timing,
            "variance": variance,
            "report_path": str(report_path),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="fishing-simulation-100",
        scenario_metadata=getattr(run_fishing_simulation_100_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "fishing-help",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Help output verification should still emit lag telemetry without turning formatting checks into environment failures.",
    },
)
def run_fishing_help_scenario(args):
    _setup_django()

    def scenario(ctx):
        import inspect

        from evennia.utils.create import create_object

        from commands.cmd_ask import CmdAsk
        from commands.cmd_fishing import CmdBait, CmdFish, CmdPull, CmdRig, CmdUntangle
        from commands.cmd_help import CmdHelp
        from commands.cmd_inventory import CmdInventory
        from commands.cmd_sell import CmdSell
        from commands.cmd_skin import CmdSkin
        import world.systems.fishing as fishing_system
        import world.systems.fishing_economy as fishing_economy
        from world.help_entries import HELP_ENTRY_DICTS

        room = ctx.harness.create_test_room(key="TEST_FISHING_HELP_ROOM")
        room.db.fishable = True
        room.db.fish_group = "River 1"
        character = ctx.harness.create_test_character(room=room, key="TEST_FISHING_HELP_CHAR")
        ctx.character = character
        ctx.room = room

        supplier = create_object("typeclasses.fishing_supplier.FishingSupplier", key="Old Maren", location=room, home=room)

        fishing_entry = next((entry for entry in list(HELP_ENTRY_DICTS or []) if str(entry.get("key", "") or "").strip().lower() == "fishing"), None)
        if not fishing_entry:
            raise AssertionError("Fishing help entry was not registered in HELP_ENTRY_DICTS.")
        fishing_help_output = str(fishing_entry.get("text", "") or "")
        if "fishing is a survival activity" not in fishing_help_output.lower():
            raise AssertionError(f"Fishing help entry did not include the expected overview text: {fishing_help_output}")
        for required_line in [
            "ask maren for gear",
            "rig pole",
            "untangle pole",
            "bait <item>",
            "fish",
            "pull",
            "inventory",
            "skin <fish>",
            "sell <item>",
            "sell fish",
        ]:
            if required_line not in fishing_help_output.lower():
                raise AssertionError(f"Fishing help omitted expected command syntax '{required_line}': {fishing_help_output}")

        help_func_source = inspect.getsource(CmdHelp.func)
        if 'query == "fish"' not in help_func_source or 'self.args = "fishing"' not in help_func_source:
            raise AssertionError("CmdHelp.func does not redirect 'help fish' to the fishing guide.")

        survival_entry = next((entry for entry in list(HELP_ENTRY_DICTS or []) if str(entry.get("key", "") or "").strip().lower() == "fieldcraft"), None)
        survival_help_output = str((survival_entry or {}).get("text", "") or "")
        if "help fishing" not in survival_help_output.lower():
            raise AssertionError(f"Help survival did not cross-reference fishing: {survival_help_output}")

        expected_commands = {
            "ask": CmdAsk.key,
            "fish": CmdFish.key,
            "bait": CmdBait.key,
            "pull": CmdPull.key,
            "rig": CmdRig.key,
            "untangle": CmdUntangle.key,
            "sell": CmdSell.key,
            "skin": CmdSkin.key,
            "inventory": CmdInventory.key,
        }
        if any(str(value or "").strip().lower() != name for name, value in expected_commands.items()):
            raise AssertionError(f"One or more documented fishing commands no longer match their expected keys: {expected_commands}")

        captured = []
        original_msg = character.msg

        def capture_msg(text=None, **kwargs):
            if text is not None:
                captured.append(str(text))
            return original_msg(text=text, **kwargs)

        def run_handler(command_cls, args=""):
            start_index = len(captured)
            command = command_cls()
            command.caller = character
            command.args = str(args or "")
            command.raw_string = f"{getattr(command, 'key', '')} {command.args}".strip()
            command.func()
            return list(captured[start_index:])

        current_time = {"value": 1000.0}
        scheduled = []
        original_delay = fishing_system.delay
        original_time = fishing_system.time.time
        original_fishing_economy_time = fishing_economy.time.time
        original_roll_outcome = fishing_system.roll_fishing_outcome
        original_hookup = fishing_system.calculate_hookup_chance
        original_resolve_struggle = fishing_system.resolve_struggle_outcome_data

        class FakeDelayedTask:
            def __init__(self):
                self.cancelled = False

            def cancel(self):
                self.cancelled = True

        def fake_delay(seconds, callback, *cb_args, **cb_kwargs):
            task = FakeDelayedTask()
            scheduled.append({
                "seconds": float(seconds),
                "callback": callback,
                "callback_name": getattr(callback, "__name__", "callback"),
                "args": cb_args,
                "kwargs": cb_kwargs,
                "task": task,
            })
            return task

        def run_next(expected_seconds=None, callback_name=None, min_seconds=None, max_seconds=None):
            for index, event in enumerate(list(scheduled)):
                task = event.get("task")
                if task is not None and bool(getattr(task, "cancelled", False)):
                    continue
                seconds = float(event.get("seconds", 0.0) or 0.0)
                if callback_name and str(event.get("callback_name", "") or "") != str(callback_name):
                    continue
                if expected_seconds is not None and abs(seconds - float(expected_seconds)) > 0.01:
                    continue
                if min_seconds is not None and seconds < float(min_seconds):
                    continue
                if max_seconds is not None and seconds > float(max_seconds):
                    continue
                scheduled.pop(index)
                current_time["value"] += seconds
                ctx.direct(event["callback"], *(event.get("args") or ()), **(event.get("kwargs") or {}))
                return seconds
            raise AssertionError(
                f"Fishing help scenario expected callback={callback_name or 'any'} seconds={expected_seconds} range=({min_seconds}, {max_seconds}), but found {scheduled}."
            )

        try:
            character.msg = capture_msg
            fishing_system.delay = fake_delay
            fishing_system.time.time = lambda: current_time["value"]
            fishing_economy.time.time = lambda: current_time["value"]
            fishing_system.roll_fishing_outcome = lambda room_or_group, rng=None: {
                "category": "fish",
                "profile": fishing_system.get_fish_profile("silver_trout"),
            }
            fishing_system.calculate_hookup_chance = lambda *a, **kw: 1.0
            fishing_system.resolve_struggle_outcome_data = lambda actor, session, fish_profile, bait_item, rng=None: {
                "outcome": "landed",
                "pressure": 0.0,
                "landed_score": 1.0,
                "lost_score": 0.0,
                "break_score": 0.0,
            }

            ask_output = run_handler(CmdAsk, "maren for gear")
            if not any("start with the pole" in line.lower() for line in ask_output):
                raise AssertionError(f"Ask maren for gear did not return the expected starter response: {ask_output}")

            pole = fishing_system.get_fishing_pole(character)
            if pole is None:
                raise AssertionError("Fishing help scenario did not receive a fishing pole from Old Maren.")
            pole.db.line_attached = False
            pole.db.hook_attached = False
            rig_output = run_handler(CmdRig, "pole")
            if not bool(getattr(pole.db, "line_attached", False)) or not bool(getattr(pole.db, "hook_attached", False)):
                raise AssertionError(f"Rig pole did not restore missing line and hook state: {rig_output}")

            pole.db.line_tangled = True
            untangle_output = run_handler(CmdUntangle, "pole")
            if bool(getattr(pole.db, "line_tangled", False)):
                raise AssertionError(f"Untangle pole did not clear the tangle state: {untangle_output}")

            bait_output = run_handler(CmdBait, "worm")
            session = fishing_system.get_fishing_session(character, create=False)
            if session is None or int(getattr(session, "bait_item_id", 0) or 0) <= 0:
                raise AssertionError(f"Bait worm did not attach bait to the fishing session: {bait_output}")

            fish_output = run_handler(CmdFish)
            if not any("cast your line" in line.lower() for line in fish_output):
                raise AssertionError(f"Fish did not start the cast flow: {fish_output}")
            run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)

            pull_output = run_handler(CmdPull)
            if not any("haul back" in line.lower() or "slight tug" in line.lower() for line in list(captured) + pull_output):
                raise AssertionError(f"Pull did not react to the fishing bite/hook flow: {pull_output}")
            run_next(expected_seconds=2.0, callback_name="_resolve_struggle_round")

            inventory_output = run_handler(CmdInventory)
            if not any("you are carrying" in line.lower() for line in inventory_output):
                raise AssertionError(f"Inventory did not render carrying output: {inventory_output}")

            fish_item = next((obj for obj in list(character.contents) if fishing_economy.is_fish_item(obj)), None)
            if fish_item is None:
                fish_string = fishing_economy.find_fish_string(character)
                fish_item = next((obj for obj in list(getattr(fish_string, "contents", []) or []) if fishing_economy.is_fish_item(obj)), None) if fish_string else None
                if fish_item is not None:
                    fish_item.move_to(character, quiet=True)
            if fish_item is None:
                raise AssertionError("Fishing help scenario did not produce a fish item to validate skinning.")

            knife = create_object("typeclasses.weapons.Weapon", key="skinning knife", location=character, home=character)
            original_is_wielding = getattr(character, "is_wielding", None)
            character.is_wielding = lambda weapon_name: str(weapon_name or "").strip().lower() == "skinning knife"
            skin_output = run_handler(CmdSkin, getattr(fish_item, "key", "silver trout"))
            processed_goods = [obj for obj in list(character.contents) if str(getattr(getattr(obj, "db", None), "item_type", "") or "") in {"fish_meat", "fish_skin"}]
            if not processed_goods:
                raise AssertionError(f"Skin <fish> did not create processed fish goods: {skin_output}")

            coins_before_sale = int(getattr(character.db, "coins", 0) or 0)
            sell_output = run_handler(CmdSell, "fish")
            coins_after_sale = int(getattr(character.db, "coins", 0) or 0)
            if coins_after_sale <= coins_before_sale:
                raise AssertionError(f"Sell fish did not pay out for processed fishing goods: {sell_output}")

            if original_is_wielding is not None:
                character.is_wielding = original_is_wielding
            else:
                delattr(character, "is_wielding")
            knife.delete()
        finally:
            character.msg = original_msg
            fishing_system.delay = original_delay
            fishing_system.time.time = original_time
            fishing_economy.time.time = original_fishing_economy_time
            fishing_system.roll_fishing_outcome = original_roll_outcome
            fishing_system.calculate_hookup_chance = original_hookup
            fishing_system.resolve_struggle_outcome_data = original_resolve_struggle

        return {
            "commands": list(expected_commands.keys()),
            "output_log": list(ctx.output_log),
            "fishing_help_excerpt": fishing_help_output[:1200],
            "fish_help_excerpt": help_func_source[:400],
            "survival_help_excerpt": survival_help_output[:800],
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="fishing-help",
        scenario_metadata=getattr(run_fishing_help_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "fishing-borrowed-gear-exit",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Borrowed-gear exit cleanup should report lag telemetry without masking return-logic regressions.",
    },
)
def run_fishing_borrowed_gear_exit_scenario(args):
    _setup_django()

    def scenario(ctx):
        from evennia.utils.create import create_object

        import world.systems.fishing as fishing_system

        water_room = ctx.harness.create_test_room(key="TEST_BORROWED_GEAR_WATER")
        west_room = ctx.harness.create_test_room(key="TEST_BORROWED_GEAR_WEST")
        south_room = ctx.harness.create_test_room(key="TEST_BORROWED_GEAR_SOUTH")
        ctx.harness.create_test_exit(water_room, west_room, "west", aliases=["w"])
        ctx.harness.create_test_exit(water_room, south_room, "south", aliases=["s"])

        water_room.db.fishable = True
        water_room.db.fish_group = "River 1"
        water_room.db.borrowed_gear_return_room = True

        character = ctx.harness.create_test_character(room=water_room, key="TEST_BORROWED_GEAR_CHAR")
        ctx.character = character
        ctx.room = water_room
        create_object("typeclasses.fishing_supplier.FishingSupplier", key="Old Maren", location=water_room, home=water_room)

        scheduled = []
        original_delay = fishing_system.delay

        class FakeDelayedTask:
            def __init__(self):
                self.cancelled = False

            def cancel(self):
                self.cancelled = True

        def fake_delay(seconds, callback, *cb_args, **cb_kwargs):
            task = FakeDelayedTask()
            scheduled.append(
                {
                    "seconds": float(seconds),
                    "callback": callback,
                    "callback_name": getattr(callback, "__name__", "callback"),
                    "args": cb_args,
                    "kwargs": cb_kwargs,
                    "task": task,
                }
            )
            return task

        def run_next(expected_seconds=None, callback_name=None):
            for index, event in enumerate(list(scheduled)):
                task = event.get("task")
                if task is not None and bool(getattr(task, "cancelled", False)):
                    continue
                seconds = float(event.get("seconds", 0.0) or 0.0)
                if callback_name and str(event.get("callback_name", "") or "") != str(callback_name):
                    continue
                if expected_seconds is not None and abs(seconds - float(expected_seconds)) > 0.01:
                    continue
                scheduled.pop(index)
                ctx.direct(event["callback"], *(event.get("args") or ()), **(event.get("kwargs") or {}))
                return
            raise AssertionError(f"Borrowed gear exit scenario expected callback={callback_name or 'any'} seconds={expected_seconds}, but found {scheduled}.")

        fishing_system.delay = fake_delay

        try:
            gear_index = len(ctx.output_log)
            ctx.cmd("ask maren for gear")
            gear_output = list(ctx.output_log[gear_index:])
            if any("return the borrowed fishing gear" in str(line).lower() for line in gear_output):
                raise AssertionError(f"Borrowed gear return triggered inside the starter room: {gear_output}")

            borrowed_items = fishing_system.get_borrowed_items(character)
            borrowed_names = sorted(str(getattr(item, "key", "") or "") for item in borrowed_items)
            if borrowed_names != ["fish string", "fishing pole", "hook", "line", "worm"]:
                raise AssertionError(f"Starter kit did not mark the expected borrowed items: {borrowed_names}")
            flavored_line = fishing_system.format_borrowed_return_message("west", paused=True)
            if "pause long enough" not in flavored_line.lower() or "west" not in flavored_line.lower():
                raise AssertionError(f"Borrowed return flavor helper did not build the optional pause message correctly: {flavored_line}")
            for item in borrowed_items:
                if not fishing_system.is_borrowed(item):
                    raise AssertionError(f"Borrowed helper failed to identify Maren's starter item: {item}")
                if str(getattr(getattr(item, "db", None), "borrowed_source", "") or "") != "maren":
                    raise AssertionError(f"Borrowed item missing the expected source tag: {item} / {getattr(item.db, 'borrowed_source', None)}")

            real_pole = create_object("typeclasses.items.fishing_pole.FishingPole", key="bought fishing pole", location=character, home=character)
            river_rock = create_object("typeclasses.objects.Object", key="river rock", location=character, home=character)
            river_rock.db.weight = 1
            if fishing_system.is_borrowed(real_pole) or fishing_system.is_borrowed(river_rock):
                raise AssertionError("Borrowed helper incorrectly marked non-borrowed items as starter gear.")

            ctx.cmd("bait worm")
            ctx.cmd("fish")
            if not bool(getattr(character.ndb, "is_fishing", False)):
                raise AssertionError("Borrowed gear exit scenario did not enter an active fishing state before movement.")

            borrowed_pole = next((item for item in list(character.contents) if bool(getattr(getattr(item, "db", None), "is_fishing_pole", False)) and fishing_system.is_borrowed(item)), None)
            if borrowed_pole is None:
                raise AssertionError("Borrowed gear exit scenario lost track of the borrowed fishing pole.")
            borrowed_pole.db.line_attached = False

            exit_index = len(ctx.output_log)
            ctx.cmd("west")
            exit_output = list(ctx.output_log[exit_index:])
            if getattr(character, "location", None) != west_room:
                raise AssertionError("Borrowed gear exit scenario did not move the character through the requested exit.")
            if not any("disturb the line" in str(line).lower() for line in exit_output):
                raise AssertionError(f"Borrowed gear exit scenario did not cancel fishing on move: {exit_output}")
            return_lines = [line for line in exit_output if "return the borrowed fishing gear" in str(line).lower()]
            if len(return_lines) != 1:
                raise AssertionError(f"Borrowed gear exit scenario emitted the return line {len(return_lines)} times instead of once: {exit_output}")
            if "west" not in str(return_lines[0]).lower():
                raise AssertionError(f"Borrowed gear exit scenario did not report the correct exit direction: {return_lines}")

            run_next(expected_seconds=0.0, callback_name="_finalize_borrowed_return_cleanup")

            if fishing_system.get_borrowed_items(character):
                raise AssertionError("Borrowed gear exit scenario did not remove all remaining borrowed kit items.")
            if getattr(character.ndb, "fishing_session", None) is not None or bool(getattr(character.ndb, "is_fishing", False)):
                raise AssertionError("Borrowed gear exit scenario left a ghost fishing session behind after movement.")
            if getattr(real_pole, "location", None) != character or getattr(river_rock, "location", None) != character:
                raise AssertionError("Borrowed gear exit scenario removed non-borrowed player items.")

            for room in (water_room, west_room, south_room):
                for item in list(getattr(room, "contents", []) or []):
                    if fishing_system.is_borrowed(item):
                        item.delete()

            return {
                "output_log": list(ctx.output_log),
                "return_message": str(return_lines[0]),
                "kept_items": [obj.key for obj in list(character.contents)],
            }
        finally:
            fishing_system.delay = original_delay

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="fishing-borrowed-gear-exit",
        scenario_metadata=getattr(run_fishing_borrowed_gear_exit_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "fishing-borrowed-gear-full-loop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Borrowed-gear full-loop verification should report lag telemetry without turning starter-loop cleanup into an environment failure.",
    },
)
def run_fishing_borrowed_gear_full_loop_scenario(args):
    _setup_django()

    def scenario(ctx):
        from evennia.utils.create import create_object

        import world.systems.fishing as fishing_system
        import world.systems.fishing_economy as fishing_economy

        water_room = ctx.harness.create_test_room(key="TEST_BORROWED_FULL_LOOP_WATER")
        south_room = ctx.harness.create_test_room(key="TEST_BORROWED_FULL_LOOP_SOUTH")
        ctx.harness.create_test_exit(water_room, south_room, "south", aliases=["s"])

        water_room.db.fishable = True
        water_room.db.fish_group = "River 1"
        water_room.db.borrowed_gear_return_room = True

        character = ctx.harness.create_test_character(room=water_room, key="TEST_BORROWED_FULL_LOOP_CHAR")
        ctx.character = character
        ctx.room = water_room
        create_object("typeclasses.fishing_supplier.FishingSupplier", key="Old Maren", location=water_room, home=water_room)

        current_time = {"value": 1000.0}
        scheduled = []
        original_delay = fishing_system.delay
        original_time = fishing_system.time.time
        original_roll_outcome = fishing_system.roll_fishing_outcome
        original_hookup = fishing_system.calculate_hookup_chance
        original_resolve_struggle = fishing_system.resolve_struggle_outcome_data

        class FakeDelayedTask:
            def __init__(self):
                self.cancelled = False

            def cancel(self):
                self.cancelled = True

        def fake_delay(seconds, callback, *cb_args, **cb_kwargs):
            task = FakeDelayedTask()
            scheduled.append(
                {
                    "seconds": float(seconds),
                    "callback": callback,
                    "callback_name": getattr(callback, "__name__", "callback"),
                    "args": cb_args,
                    "kwargs": cb_kwargs,
                    "task": task,
                }
            )
            return task

        def run_next(expected_seconds=None, callback_name=None, min_seconds=None, max_seconds=None):
            for index, event in enumerate(list(scheduled)):
                task = event.get("task")
                if task is not None and bool(getattr(task, "cancelled", False)):
                    continue
                seconds = float(event.get("seconds", 0.0) or 0.0)
                if callback_name and str(event.get("callback_name", "") or "") != str(callback_name):
                    continue
                if expected_seconds is not None and abs(seconds - float(expected_seconds)) > 0.01:
                    continue
                if min_seconds is not None and seconds < float(min_seconds):
                    continue
                if max_seconds is not None and seconds > float(max_seconds):
                    continue
                scheduled.pop(index)
                current_time["value"] += seconds
                ctx.direct(event["callback"], *(event.get("args") or ()), **(event.get("kwargs") or {}))
                return seconds
            raise AssertionError(
                f"Borrowed full-loop scenario expected callback={callback_name or 'any'} seconds={expected_seconds} range=({min_seconds}, {max_seconds}), but found {scheduled}."
            )

        try:
            fishing_system.delay = fake_delay
            fishing_system.time.time = lambda: current_time["value"]
            fishing_system.roll_fishing_outcome = lambda room_or_group, rng=None: {
                "category": "fish",
                "profile": fishing_system.get_fish_profile("silver_trout"),
            }
            fishing_system.calculate_hookup_chance = lambda *a, **kw: 1.0
            fishing_system.resolve_struggle_outcome_data = lambda actor, session, fish_profile, bait_item, rng=None: {
                "outcome": "landed",
                "pressure": 0.0,
                "landed_score": 1.0,
                "lost_score": 0.0,
                "break_score": 0.0,
            }

            ctx.cmd("ask maren for gear")
            if len(fishing_system.get_borrowed_items(character)) < 5:
                raise AssertionError("Borrowed full-loop scenario did not receive the complete borrowed starter kit.")

            junk_item = create_object("typeclasses.objects.Object", key="river salvage", location=character, home=character)
            junk_item.db.is_junk = True
            junk_item.db.item_type = "junk"
            junk_item.db.value = 7
            junk_item.db.weight = 1
            processed_item = create_object("typeclasses.objects.Object", key="cleaned fish skin", location=character, home=character)
            processed_item.db.item_type = "fish_skin"
            processed_item.db.value = 5
            processed_item.db.weight = 1

            ctx.cmd("bait worm")
            ctx.cmd("fish")
            run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
            ctx.cmd("pull")
            run_next(expected_seconds=2.0, callback_name="_resolve_struggle_round")

            fish_string = next((obj for obj in list(character.contents) if fishing_economy.is_fish_string(obj) and fishing_system.is_borrowed(obj)), None)
            if fish_string is None:
                raise AssertionError("Borrowed full-loop scenario did not retain the borrowed fish string before exit.")
            landed_fish = next((obj for obj in list(getattr(fish_string, "contents", []) or []) if fishing_economy.is_fish_item(obj)), None)
            if landed_fish is None:
                landed_fish = next((obj for obj in list(character.contents) if fishing_economy.is_fish_item(obj)), None)
            if landed_fish is None:
                raise AssertionError("Borrowed full-loop scenario did not land a fish before exit.")

            exit_index = len(ctx.output_log)
            ctx.cmd("south")
            exit_output = list(ctx.output_log[exit_index:])
            return_lines = [line for line in exit_output if "return the borrowed fishing gear" in str(line).lower()]
            if len(return_lines) != 1:
                raise AssertionError(f"Borrowed full-loop scenario emitted the return line {len(return_lines)} times instead of once: {exit_output}")
            if "south" not in str(return_lines[0]).lower():
                raise AssertionError(f"Borrowed full-loop scenario did not report the correct exit direction: {return_lines}")
            run_next(expected_seconds=0.0, callback_name="_finalize_borrowed_return_cleanup")
            if getattr(character, "location", None) != south_room:
                raise AssertionError("Borrowed full-loop scenario did not move the character through the south exit.")
            if fishing_system.get_borrowed_items(character):
                raise AssertionError("Borrowed full-loop scenario left borrowed starter gear in inventory after exit.")
            if getattr(landed_fish, "location", None) != character:
                raise AssertionError("Borrowed full-loop scenario did not preserve the caught fish when returning the borrowed fish string.")
            if getattr(junk_item, "location", None) != character:
                raise AssertionError("Borrowed full-loop scenario incorrectly removed kept junk on exit.")
            if getattr(processed_item, "location", None) != character:
                raise AssertionError("Borrowed full-loop scenario incorrectly removed processed goods on exit.")

            for room in (water_room, south_room):
                for item in list(getattr(room, "contents", []) or []):
                    if fishing_system.is_borrowed(item):
                        item.delete()

            return {
                "output_log": list(ctx.output_log),
                "kept_items": [obj.key for obj in list(character.contents)],
            }
        finally:
            fishing_system.delay = original_delay
            fishing_system.time.time = original_time
            fishing_system.roll_fishing_outcome = original_roll_outcome
            fishing_system.calculate_hookup_chance = original_hookup
            fishing_system.resolve_struggle_outcome_data = original_resolve_struggle

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="fishing-borrowed-gear-full-loop",
        scenario_metadata=getattr(run_fishing_borrowed_gear_full_loop_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "rt-timing",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural roundtime validation should still emit lag telemetry without failing on environment-specific latency.",
    },
)
def run_rt_timing_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.scheduler import flush_due, get_scheduler_snapshot

        room = ctx.harness.create_test_room(key="TEST_RT_ROOM")
        character = ctx.harness.create_test_character(room=room, key="TEST_RT_CHAR")

        ctx.character = character
        ctx.room = room

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")
        ctx.direct(character.set_roundtime, 2.0)
        ctx.snapshot("triggered")
        if float(character.db.roundtime_end or 0.0) <= time.time():
            raise AssertionError("RT scenario did not apply roundtime.")
        if int((get_scheduler_snapshot() or {}).get("active_job_count", 0) or 0) <= 0:
            raise AssertionError("RT scenario did not register a scheduler job for roundtime expiry.")

        output_count_before_block = len(list(ctx.output_log or []))
        ctx.cmd("advance")
        ctx.snapshot("blocked")
        blocked_output = " ".join(list(ctx.output_log or [])[output_count_before_block:])
        if "must wait" not in blocked_output.lower():
            raise AssertionError("RT scenario did not block command execution during roundtime.")

        remaining = float(character.get_remaining_roundtime() or 0.0)
        if remaining > 0.0:
            time.sleep(min(remaining + 0.05, 1.5))
        ctx.direct(flush_due)
        if character.get_remaining_roundtime() > 0:
            raise AssertionError("RT scenario did not expire roundtime.")

        output_count_before_recovery = len(list(ctx.output_log or []))
        ctx.cmd("advance")
        ctx.snapshot("recovered")
        recovered_output = " ".join(list(ctx.output_log or [])[output_count_before_recovery:])
        if "must wait" in recovered_output.lower():
            raise AssertionError("RT scenario did not allow command execution after roundtime expiry.")
        if "advance toward what" not in recovered_output.lower():
            raise AssertionError("RT scenario did not reach the normal non-blocked advance path after roundtime expiry.")

        return {
            "commands": list(ctx.command_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "output_log": list(ctx.output_log),
            "remaining_roundtime": character.get_remaining_roundtime(),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="rt-timing",
        scenario_metadata=getattr(run_rt_timing_scenario, "diretest_metadata", {}),
    )


@register_scenario("inventory")
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

        if pickup_diff["inventory_changes"]["added"] != ["TEST_INV_PACK"]:
            raise AssertionError(f"Inventory pickup diff was not meaningful: {pickup_diff}")
        if pickup_diff["room_changes"]["changed"]:
            raise AssertionError("Inventory pickup unexpectedly changed rooms.")
        if "TEST_INV_PACK" not in pickup_diff["room_changes"]["contents_removed"]:
            raise AssertionError(f"Pickup diff did not record room-content removal: {pickup_diff}")

        if drop_diff["inventory_changes"]["removed"] != ["TEST_INV_PACK"]:
            raise AssertionError(f"Inventory drop diff was not meaningful: {drop_diff}")
        if "TEST_INV_PACK" not in drop_diff["room_changes"]["contents_added"]:
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

    return _run_registered_scenario(args, scenario, auto_snapshot=True, name="inventory")


@register_scenario(
    "empath-core-loop",
    aliases=["empath_core_loop"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath loop regression coverage validates command and wound-transfer behavior; emit lag telemetry without failing on environment-specific latency.",
        "tags": ["core", "empath", "smoke"],
    },
)
def run_empath_core_loop_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_PATIENT")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        empath.db.wounds = {"vitality": 0, "bleeding": 0}
        empath.db.empath_shock = 0
        patient.db.wounds = {"vitality": 60, "bleeding": 30}

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")

        output_index = len(ctx.output_log)
        ctx.cmd("touch TEST_EMPATH_PATIENT")
        touch_output = list(ctx.output_log[output_index:])
        ctx.snapshot("touched")

        link_state = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        linked_target = int(link_state.get("target_id", 0) or 0) if link_state else 0
        if linked_target != int(getattr(patient, "id", 0) or 0):
            raise AssertionError(f"Empath touch did not lock the patient link: {linked_target} vs {getattr(patient, 'id', None)}")
        if int(link_state.get("strength", 0) or 0) != 60 or int(link_state.get("stability", 0) or 0) != 80:
            raise AssertionError(f"Empath touch should create a weak touch link, got {link_state}")
        if not any("sense the condition of your patient" in str(line).lower() for line in touch_output):
            raise AssertionError(f"Empath touch did not emit the expected feedback: {touch_output}")

        away_room = ctx.harness.create_test_room(key="TEST_EMPATH_AWAY_ROOM")
        output_index = len(ctx.output_log)
        ctx.direct(lambda: empath.move_to(away_room, quiet=False))
        move_output = list(ctx.output_log[output_index:])
        ctx.snapshot("moved_away")

        lingering_link = empath.get_empath_link_state(require_local=False, emit_break_messages=False)
        if lingering_link:
            raise AssertionError(f"Empath link should break when the healer moves away: {lingering_link}")
        if not any("distance tears" in str(line).lower() for line in move_output):
            raise AssertionError(f"Empath movement did not emit the expected break message: {move_output}")

        output_index = len(ctx.output_log)
        empath.ndb.next_empath_feedback_at = 0
        ctx.direct(empath.process_empath_tick)
        post_move_feedback_output = list(ctx.output_log[output_index:])
        ctx.snapshot("post_move_tick")
        if any("your senses are clear." in str(line).lower() for line in post_move_feedback_output):
            raise AssertionError(f"Empath feedback should stop after moving out of touch range: {post_move_feedback_output}")

        ctx.direct(lambda: empath.move_to(room, quiet=True))
        ctx.cmd("touch TEST_EMPATH_PATIENT")

        output_index = len(ctx.output_log)
        ctx.cmd("assess")
        assess_output = list(ctx.output_log[output_index:])
        ctx.snapshot("assessed")

        assess_text = " ".join(str(line) for line in assess_output)
        if "Vitality: 60%" not in assess_text or "Bleeding: 30%" not in assess_text:
            raise AssertionError(f"Empath assess did not report the expected precise wound values: {assess_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("take bleeding")
        take_bleeding_output = list(ctx.output_log[output_index:])
        ctx.snapshot("took_bleeding")

        patient_after_bleeding = dict(getattr(patient.db, "wounds", {}) or {})
        empath_after_bleeding = dict(getattr(empath.db, "wounds", {}) or {})
        dangerous_bleeding_threshold = 12
        if int(patient_after_bleeding.get("bleeding", 0) or 0) != 18:
            raise AssertionError(f"Empath bleeding transfer did not reduce patient bleeding by the default chunk: {patient_after_bleeding}")
        if int(empath_after_bleeding.get("bleeding", 0) or 0) < dangerous_bleeding_threshold:
            raise AssertionError(f"Empath bleeding transfer did not leave the healer carrying meaningful self-risk: {empath_after_bleeding}")
        if not any("lessen the burden" in str(line).lower() or "draw the injury into yourself" in str(line).lower() for line in take_bleeding_output):
            raise AssertionError(f"Empath take bleeding did not emit the transfer message: {take_bleeding_output}")

        output_index = len(ctx.output_log)
        hp_before_vitality = int(getattr(empath.db, "hp", 0) or 0)
        ctx.cmd("take vitality 20")
        take_vitality_output = list(ctx.output_log[output_index:])
        ctx.snapshot("took_vitality")

        patient_after_vitality = dict(getattr(patient.db, "wounds", {}) or {})
        empath_after_vitality = dict(getattr(empath.db, "wounds", {}) or {})
        hp_after_vitality = int(getattr(empath.db, "hp", 0) or 0)
        if int(patient_after_vitality.get("vitality", 0) or 0) != 48:
            raise AssertionError(f"Empath vitality transfer did not reduce patient vitality correctly: {patient_after_vitality}")
        if int(empath_after_vitality.get("vitality", 0) or 0) <= 0:
            raise AssertionError(f"Empath vitality transfer did not accumulate transferred damage on the healer: {empath_after_vitality}")
        if int(empath_after_vitality.get("bleeding", 0) or 0) != int(empath_after_bleeding.get("bleeding", 0) or 0):
            raise AssertionError(f"Empath vitality transfer unexpectedly reset or altered carried bleeding: {empath_after_vitality}")
        if hp_after_vitality >= hp_before_vitality:
            raise AssertionError(f"Empath vitality transfer did not apply any HP cost: before={hp_before_vitality}, after={hp_after_vitality}")
        if not any("living force" in str(line).lower() for line in take_vitality_output):
            raise AssertionError(f"Empath take vitality did not emit the transfer message: {take_vitality_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("mend self")
        mend_output = list(ctx.output_log[output_index:])
        ctx.snapshot("mended")

        empath_after_mend = dict(getattr(empath.db, "wounds", {}) or {})
        if int(empath_after_mend.get("vitality", 0) or 0) >= int(empath_after_vitality.get("vitality", 0) or 0):
            raise AssertionError(f"Empath mend did not reduce vitality by the expected placeholder amount: {empath_after_mend}")
        if int(empath_after_mend.get("bleeding", 0) or 0) != max(0, int(empath_after_bleeding.get("bleeding", 0) or 0) - 5):
            raise AssertionError(f"Empath mend did not reduce bleeding by the expected placeholder amount: {empath_after_mend}")
        if int(empath_after_mend.get("vitality", 0) or 0) <= 0 and int(empath_after_mend.get("bleeding", 0) or 0) <= 0:
            raise AssertionError(f"Empath mend reset the loop instead of leaving carried risk in place: {empath_after_mend}")
        if not any("focus inward, stabilizing your condition" in str(line).lower() for line in mend_output):
            raise AssertionError(f"Empath mend did not emit the expected feedback: {mend_output}")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["initial", "touched", "moved_away", "post_move_tick", "assessed", "took_bleeding", "took_vitality", "mended"]
        if labels != expected_labels:
            raise AssertionError(f"Empath core-loop snapshot labels drifted: expected {expected_labels}, got {labels}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "touch_output": touch_output,
            "move_output": move_output,
            "post_move_feedback_output": post_move_feedback_output,
            "assess_output": assess_output,
            "take_bleeding_output": take_bleeding_output,
            "take_vitality_output": take_vitality_output,
            "mend_output": mend_output,
            "dangerous_bleeding_threshold": dangerous_bleeding_threshold,
            "patient_after_bleeding": patient_after_bleeding,
            "empath_after_bleeding": empath_after_bleeding,
            "patient_after_vitality": patient_after_vitality,
            "empath_after_vitality": empath_after_vitality,
            "empath_after_mend": empath_after_mend,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-core-loop",
        scenario_metadata=getattr(run_empath_core_loop_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-triage-pressure",
    aliases=["empath_triage_pressure"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath pressure coverage validates decay, overload, and queue ordering under room triage load.",
        "tags": ["core", "empath"],
    },
)
def run_empath_triage_pressure_scenario(args):
    _setup_django()

    def scenario(ctx):
        from typeclasses.characters import EMPATH_SHOCK_THRESHOLDS

        room = ctx.harness.create_test_room(key="TEST_EMPATH_TRIAGE_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_TRIAGE_HEALER")
        critical = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_CRITICAL")
        injured = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_INJURED")
        house_healer = ctx.harness.create_test_character(room=room, key="TEST_HOUSE_HEALER")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 50)
        empath.db.wounds = {"vitality": 55, "bleeding": 18, "fatigue": 42, "poison": 0, "disease": 0, "trauma": 0}
        empath.db.empath_shock = int(EMPATH_SHOCK_THRESHOLDS["dull"])
        empath.db.last_perceive_time = 0.0

        critical.db.wounds = {"vitality": 72, "bleeding": 34, "fatigue": 0, "poison": 0, "disease": 0, "trauma": 0}
        critical.db.last_medical_decay_at = time.time() - 20.0
        critical.db.last_tip_amount = 25
        critical.db.last_tip_time = time.time()

        injured.db.wounds = {"vitality": 26, "bleeding": 8, "fatigue": 0, "poison": 0, "disease": 0, "trauma": 0}
        injured.db.last_medical_decay_at = time.time() - 20.0

        house_healer.db.is_house_healer = True
        house_healer.db.wounds = {"vitality": 95, "bleeding": 95, "fatigue": 0, "poison": 0, "disease": 0, "trauma": 0}

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        before_critical = dict(getattr(critical.db, "wounds", {}) or {})
        output_index = len(ctx.output_log)
        ctx.direct(lambda: critical.process_medical_decay(now=time.time()))
        decay_output = list(ctx.output_log[output_index:])
        after_critical = dict(getattr(critical.db, "wounds", {}) or {})
        if int(after_critical.get("vitality", 0) or 0) <= int(before_critical.get("vitality", 0) or 0):
            raise AssertionError(f"Critical patient did not worsen under medical decay: before={before_critical}, after={after_critical}")
        if not any(
            "slipping away" in str(line).lower()
            or "condition is worsening" in str(line).lower()
            or "senses snag" in str(line).lower()
            for line in decay_output
        ):
            raise AssertionError(f"Critical decay did not emit patient pressure messaging: {decay_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("perceive health")
        perceive_output = list(ctx.output_log[output_index:])
        perceive_text = " ".join(str(line) for line in perceive_output).lower()
        if "your senses are unclear." not in perceive_text:
            raise AssertionError(f"Dull-shock perceive should still work with degraded messaging: {perceive_output}")
        if "test_empath_critical: fading" not in perceive_text:
            raise AssertionError(f"Dull-shock room perceive should blur severe cases instead of blocking: {perceive_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("queue")
        queue_output = list(ctx.output_log[output_index:])
        queue_text = "\n".join(str(line) for line in queue_output)
        if "TEST_EMPATH_CRITICAL: critical [generous]" not in queue_text:
            raise AssertionError(f"Queue should surface the critical patient first with generous label: {queue_output}")
        if "TEST_EMPATH_INJURED: injured [known]" not in queue_text:
            raise AssertionError(f"Queue should retain known context for previously scanned patients: {queue_output}")
        if "TEST_HOUSE_HEALER" in queue_text:
            raise AssertionError(f"Queue should exclude house-healer NPCs from triage ordering: {queue_output}")
        critical_index = queue_text.find("TEST_EMPATH_CRITICAL")
        injured_index = queue_text.find("TEST_EMPATH_INJURED")
        if critical_index == -1 or injured_index == -1 or critical_index > injured_index:
            raise AssertionError(f"Queue ordering drifted; critical patient should sort ahead of injured: {queue_output}")

        ctx.cmd("touch TEST_EMPATH_CRITICAL")
        output_index = len(ctx.output_log)
        ctx.cmd("take bleeding 20")
        transfer_output = list(ctx.output_log[output_index:])
        overload_until = float(getattr(empath.db, "empath_overload_until", 0.0) or 0.0)
        if overload_until <= time.time():
            raise AssertionError(f"Extreme transfer load should trigger empath overload lockout: wounds={getattr(empath.db, 'wounds', {})}")
        if not any("reeling" in str(line).lower() or "taken too much" in str(line).lower() for line in transfer_output):
            raise AssertionError(f"Overload transfer should emit warning or collapse messaging: {transfer_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("shift TEST_EMPATH_INJURED arm")
        shift_output = list(ctx.output_log[output_index:])
        if not any("senses still reel" in str(line).lower() for line in shift_output):
            raise AssertionError(f"Overload lockout should block further transfers immediately after overload: {shift_output}")

        return {
            "decay_output": decay_output,
            "perceive_output": perceive_output,
            "queue_output": queue_output,
            "transfer_output": transfer_output,
            "shift_output": shift_output,
            "critical_after_decay": json.loads(json.dumps(after_critical, default=str)),
            "empath_wounds": json.loads(json.dumps(dict(getattr(empath.db, "wounds", {}) or {}), default=str)),
            "overload_until": overload_until,
            "triage_context": json.loads(json.dumps(dict(getattr(empath.db, "empath_triage_context", {}) or {}), default=str)),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-triage-pressure",
        scenario_metadata=getattr(run_empath_triage_pressure_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-circle-formation",
    aliases=["empath_circle_formation"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Shock-circle formation coverage validates invite, accept, leave, and consistent shared state.",
        "tags": ["core", "empath"],
    },
)
def run_empath_circle_formation_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_CIRCLE_FORM_ROOM")
        leader = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_CIRCLE_LEADER")
        second = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_CIRCLE_SECOND")
        third = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_CIRCLE_THIRD")

        for member in (leader, second, third):
            member.set_profession("empath")

        ok, message = leader.invite_empath_circle_member(second)
        if not ok:
            raise AssertionError(f"Leader should be able to invite second empath: {message}")
        ok, message = second.accept_empath_circle_invite(leader)
        if not ok:
            raise AssertionError(f"Second empath should be able to accept the invite: {message}")
        ok, message = leader.invite_empath_circle_member(third)
        if not ok:
            raise AssertionError(f"Leader should be able to invite third empath: {message}")
        ok, message = third.accept_empath_circle_invite(leader)
        if not ok:
            raise AssertionError(f"Third empath should be able to accept the invite: {message}")

        expected_ids = sorted([int(leader.id), int(second.id), int(third.id)])
        for member in (leader, second, third):
            member_ids = sorted(member.get_empath_circle_member_ids(include_self=True))
            if member_ids != expected_ids:
                raise AssertionError(f"Circle state should be consistent across all members: member={member.key}, ids={member_ids}, expected={expected_ids}")

        status_lines = leader.get_empath_circle_status_lines()
        status_text = " ".join(status_lines)
        if "Shock Circle Leader" not in status_text or "unknown" not in status_text:
            raise AssertionError(f"Circle status should show the leader and soft reputation labels: {status_lines}")

        ok, message = third.leave_empath_circle()
        if not ok:
            raise AssertionError(f"Third empath should be able to leave the circle: {message}")
        remaining_ids = sorted([int(leader.id), int(second.id)])
        for member in (leader, second):
            member_ids = sorted(member.get_empath_circle_member_ids(include_self=True))
            if member_ids != remaining_ids:
                raise AssertionError(f"Circle should recalculate after a member leaves: member={member.key}, ids={member_ids}, expected={remaining_ids}")

        return {
            "status_lines": status_lines,
            "leader_circle": leader.get_empath_circle_member_ids(include_self=True),
            "second_circle": second.get_empath_circle_member_ids(include_self=True),
            "third_circle": third.get_empath_circle_member_ids(include_self=True),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-circle-formation",
        scenario_metadata=getattr(run_empath_circle_formation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-circle-shock-distribution",
    aliases=["empath_circle_shock_distribution"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Shock-circle distribution coverage validates shared shock burden and conservation of total shock.",
        "tags": ["core", "empath"],
    },
)
def run_empath_circle_shock_distribution_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_CIRCLE_SHOCK_ROOM")
        leader = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_LEADER")
        partner = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_PARTNER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_PATIENT")

        leader.set_profession("empath")
        partner.set_profession("empath")
        patient.db.wounds = {"vitality": 80, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}

        ok, message = leader.invite_empath_circle_member(partner)
        if not ok:
            raise AssertionError(f"Leader could not invite circle partner: {message}")
        ok, message = partner.accept_empath_circle_invite(leader)
        if not ok:
            raise AssertionError(f"Partner could not accept circle invite: {message}")

        ctx.character = leader
        ctx.cmd("link TEST_EMPATH_SHOCK_PATIENT")

        before_total = leader.get_empath_shock() + partner.get_empath_shock()
        ok, message = leader.take_empath_wound("vitality", "20")
        if not ok:
            raise AssertionError(f"Vitality transfer should succeed for shock distribution coverage: {message}")
        after_leader = leader.get_empath_shock()
        after_partner = partner.get_empath_shock()
        total_delta = (after_leader + after_partner) - before_total
        if after_leader <= 0 or after_partner <= 0:
            raise AssertionError(f"Shock circle should spread some burden onto both empaths: leader={after_leader}, partner={after_partner}")
        if total_delta != 6:
            raise AssertionError(f"Shock distribution should preserve total shock burden: total_delta={total_delta}")

        return {
            "leader_shock": after_leader,
            "partner_shock": after_partner,
            "total_delta": total_delta,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-circle-shock-distribution",
        scenario_metadata=getattr(run_empath_circle_shock_distribution_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-circle-cascade-failure",
    aliases=["empath_circle_cascade_failure"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Cascade coverage validates multi-overload behavior when multiple circle members are already near collapse.",
        "tags": ["core", "empath"],
    },
)
def run_empath_circle_cascade_failure_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_CASCADE_ROOM")
        leader = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_CASCADE_LEADER")
        second = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_CASCADE_SECOND")
        third = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_CASCADE_THIRD")

        for member in (leader, second, third):
            member.set_profession("empath")
            member.db.empath_shock = 65
            member.db.wounds = {"vitality": 55, "bleeding": 0, "fatigue": 60, "poison": 0, "disease": 0}

        leader.invite_empath_circle_member(second)
        second.accept_empath_circle_invite(leader)
        leader.invite_empath_circle_member(third)
        third.accept_empath_circle_invite(leader)

        output_index = len(ctx.output_log)
        shares = ctx.direct(lambda: leader.distribute_circle_shock(12, source="cascade_test"))
        output = list(ctx.output_log[output_index:])
        overload_count = sum(1 for member in (leader, second, third) if float(getattr(member.db, "empath_overload_until", 0.0) or 0.0) > time.time())
        if sum(int(value or 0) for value in shares.values()) != 12:
            raise AssertionError(f"Cascade test should preserve total shared shock: {shares}")
        if overload_count < 2:
            raise AssertionError(f"Cascade pressure should overload multiple empaths near the limit: overload_count={overload_count}")

        return {
            "shares": shares,
            "output": output,
            "overload_count": overload_count,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-circle-cascade-failure",
        scenario_metadata=getattr(run_empath_circle_cascade_failure_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-cooperative-efficiency",
    aliases=["empath_cooperative_efficiency"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Cooperative efficiency coverage validates that split roles outperform solo triage while overlapping handling remains risky.",
        "tags": ["core", "empath"],
    },
)
def run_empath_cooperative_efficiency_scenario(args):
    _setup_django()

    def scenario(ctx):
        solo_room = ctx.harness.create_test_room(key="TEST_EMPATH_SOLO_ROOM")
        team_room = ctx.harness.create_test_room(key="TEST_EMPATH_TEAM_ROOM")

        solo = ctx.harness.create_test_character(room=solo_room, key="TEST_EMPATH_SOLO")
        team_lead = ctx.harness.create_test_character(room=team_room, key="TEST_EMPATH_TEAM_LEAD")
        team_support = ctx.harness.create_test_character(room=team_room, key="TEST_EMPATH_TEAM_SUPPORT")
        solo_patient = ctx.harness.create_test_character(room=solo_room, key="TEST_EMPATH_SOLO_PATIENT")
        team_patient = ctx.harness.create_test_character(room=team_room, key="TEST_EMPATH_TEAM_PATIENT")

        for member in (solo, team_lead, team_support):
            member.set_profession("empath")

        solo_patient.db.wounds = {"vitality": 72, "bleeding": 26, "fatigue": 0, "poison": 0, "disease": 0}
        team_patient.db.wounds = {"vitality": 72, "bleeding": 26, "fatigue": 0, "poison": 0, "disease": 0}

        ctx.character = solo
        ctx.cmd("link TEST_EMPATH_SOLO_PATIENT")
        solo.take_empath_wound("vitality", "20")
        solo_patient.process_medical_decay(now=time.time() + 13.0)

        team_lead.invite_empath_circle_member(team_support)
        team_support.accept_empath_circle_invite(team_lead)
        ctx.character = team_lead
        ctx.cmd("link TEST_EMPATH_TEAM_PATIENT")
        team_support.stabilize_empath_target(team_patient)
        team_lead.take_empath_wound("vitality", "20")
        team_patient.process_medical_decay(now=time.time() + 13.0)

        solo_state = solo_patient.get_medical_severity_state()
        team_state = team_patient.get_medical_severity_state()
        pressure = team_lead.get_empath_transfer_pressure(team_patient)
        if {"stable": 0, "injured": 1, "badly_injured": 2, "critical": 3}.get(team_state, 0) > {"stable": 0, "injured": 1, "badly_injured": 2, "critical": 3}.get(solo_state, 0):
            raise AssertionError(f"Cooperative triage should not leave the team patient worse off than the solo patient: solo={solo_state}, team={team_state}")
        if not bool(pressure.get("shared_circle", False)):
            raise AssertionError(f"Cooperative triage should preserve circle context while handling the patient: {pressure}")
        if team_lead.get_empath_shock() >= solo.get_empath_shock():
            raise AssertionError(f"Circle sharing should leave the lead empath carrying less shock than the solo empath: solo={solo.get_empath_shock()}, team={team_lead.get_empath_shock()}")

        return {
            "solo_state": solo_state,
            "team_state": team_state,
            "team_pressure": {
                "other_handler_count": int(pressure.get("other_handler_count", 0) or 0),
                "shared_circle": bool(pressure.get("shared_circle", False)),
                "efficiency_modifier": float(pressure.get("efficiency_modifier", 1.0) or 1.0),
                "instability_multiplier": float(pressure.get("instability_multiplier", 1.0) or 1.0),
            },
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-cooperative-efficiency",
        scenario_metadata=getattr(run_empath_cooperative_efficiency_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-reputation-drift",
    aliases=["empath_reputation_drift"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Reputation drift coverage validates that helping critical patients improves standing while neglect under visible pressure degrades it.",
        "tags": ["core", "empath"],
    },
)
def run_empath_reputation_drift_scenario(args):
    _setup_django()

    def scenario(ctx):
        help_room = ctx.harness.create_test_room(key="TEST_EMPATH_REPUTATION_HELP_ROOM")
        neglect_room = ctx.harness.create_test_room(key="TEST_EMPATH_REPUTATION_NEGLECT_ROOM")
        helper = ctx.harness.create_test_character(room=help_room, key="TEST_EMPATH_HELPER")
        observer = ctx.harness.create_test_character(room=neglect_room, key="TEST_EMPATH_OBSERVER")
        helped_patient = ctx.harness.create_test_character(room=help_room, key="TEST_EMPATH_REPUTATION_HELPED")
        ignored_patient = ctx.harness.create_test_character(room=neglect_room, key="TEST_EMPATH_REPUTATION_IGNORED")

        helper.set_profession("empath")
        observer.set_profession("empath")
        helped_patient.db.wounds = {"vitality": 74, "bleeding": 28, "fatigue": 0, "poison": 0, "disease": 0}
        helped_patient.db.last_medical_decay_at = time.time() - 20.0
        helped_patient.db.last_critical_warning_at = time.time() - 30.0
        ignored_patient.db.wounds = {"vitality": 74, "bleeding": 28, "fatigue": 0, "poison": 0, "disease": 0}
        ignored_patient.db.last_medical_decay_at = time.time() - 20.0
        ignored_patient.db.last_critical_warning_at = time.time() - 30.0

        helper.create_empath_link(helped_patient, link_type="direct")
        helper.take_empath_wound("vitality", "20")
        if helper.get_empath_reputation_label() not in {"unknown", "trusted"}:
            raise AssertionError(f"Helper reputation label should remain sensible after positive action: {helper.get_empath_reputation_label()}")

        before_helper = int(getattr(helper.db, "empath_reputation_score", 0) or 0)
        before_observer = int(getattr(observer.db, "empath_reputation_score", 0) or 0)
        helped_patient.process_medical_decay(now=time.time())
        ignored_patient.process_medical_decay(now=time.time())
        after_helper = int(getattr(helper.db, "empath_reputation_score", 0) or 0)
        after_observer = int(getattr(observer.db, "empath_reputation_score", 0) or 0)
        if after_helper < before_helper:
            raise AssertionError(f"Active helper should not lose reputation while handling the critical patient: before={before_helper}, after={after_helper}")
        if after_observer >= before_observer:
            raise AssertionError(f"Ignoring a visible critical patient should reduce reputation: before={before_observer}, after={after_observer}")

        return {
            "helper_score": after_helper,
            "observer_score": after_observer,
            "helper_label": helper.get_empath_reputation_label(),
            "observer_label": observer.get_empath_reputation_label(),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-reputation-drift",
        scenario_metadata=getattr(run_empath_reputation_drift_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-group-survival",
    aliases=["empath_group_survival"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Group survival coverage validates that two coordinated empaths outperform one empath across multiple patients.",
        "tags": ["core", "empath"],
    },
)
def run_empath_group_survival_scenario(args):
    _setup_django()

    def _count_critical(patients):
        return sum(1 for patient in patients if patient.get_medical_severity_state() == "critical")

    def scenario(ctx):
        solo_room = ctx.harness.create_test_room(key="TEST_EMPATH_GROUP_SOLO_ROOM")
        team_room = ctx.harness.create_test_room(key="TEST_EMPATH_GROUP_TEAM_ROOM")

        solo = ctx.harness.create_test_character(room=solo_room, key="TEST_EMPATH_GROUP_SOLO")
        team_a = ctx.harness.create_test_character(room=team_room, key="TEST_EMPATH_GROUP_A")
        team_b = ctx.harness.create_test_character(room=team_room, key="TEST_EMPATH_GROUP_B")
        for healer in (solo, team_a, team_b):
            healer.set_profession("empath")

        solo_patients = [ctx.harness.create_test_character(room=solo_room, key=f"TEST_EMPATH_SOLO_PATIENT_{index}") for index in range(1, 4)]
        team_patients = [ctx.harness.create_test_character(room=team_room, key=f"TEST_EMPATH_TEAM_PATIENT_{index}") for index in range(1, 4)]
        for patient in solo_patients + team_patients:
            patient.db.wounds = {"vitality": 70, "bleeding": 24, "fatigue": 0, "poison": 0, "disease": 0}
            patient.db.last_medical_decay_at = time.time() - 20.0

        ctx.character = solo
        ctx.cmd("link TEST_EMPATH_SOLO_PATIENT_1")
        solo.take_empath_wound("vitality", "20")
        solo.stabilize_empath_target(solo_patients[1])
        for patient in solo_patients:
            patient.process_medical_decay(now=time.time())

        team_a.invite_empath_circle_member(team_b)
        team_b.accept_empath_circle_invite(team_a)
        ctx.character = team_a
        ctx.cmd("link TEST_EMPATH_TEAM_PATIENT_1")
        team_a.take_empath_wound("vitality", "20")
        team_a.stabilize_empath_target(team_patients[1])
        ctx.character = team_b
        ctx.cmd("link TEST_EMPATH_TEAM_PATIENT_2")
        team_b.take_empath_wound("vitality", "20")
        team_b.stabilize_empath_target(team_patients[2])
        for patient in team_patients:
            patient.process_medical_decay(now=time.time())

        solo_critical = _count_critical(solo_patients)
        team_critical = _count_critical(team_patients)
        if team_critical >= solo_critical:
            raise AssertionError(f"Two empaths should leave fewer critical patients than one: solo={solo_critical}, team={team_critical}")

        return {
            "solo_critical": solo_critical,
            "team_critical": team_critical,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-group-survival",
        scenario_metadata=getattr(run_empath_group_survival_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-failure-cascade-stability",
    aliases=["empath_failure_cascade_stability"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Failure stability coverage validates that circle cascade overloads recover cleanly without infinite loops or unrecoverable state corruption.",
        "tags": ["core", "empath"],
    },
)
def run_empath_failure_cascade_stability_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_FAILURE_STABILITY_ROOM")
        leader = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_FAILURE_LEADER")
        second = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_FAILURE_SECOND")
        third = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_FAILURE_THIRD")

        for member in (leader, second, third):
            member.set_profession("empath")
            member.db.empath_shock = 68
            member.db.wounds = {"vitality": 58, "bleeding": 0, "fatigue": 62, "poison": 0, "disease": 0}

        leader.invite_empath_circle_member(second)
        second.accept_empath_circle_invite(leader)
        leader.invite_empath_circle_member(third)
        third.accept_empath_circle_invite(leader)

        leader.distribute_circle_shock(14, source="stability_test")
        for member in (leader, second, third):
            member.db.empath_overload_until = time.time() - 1.0
        tick_changed = leader.process_empath_tick()
        ok, message = second.leave_empath_circle()
        if not ok:
            raise AssertionError(f"Members should still be able to leave after a cascade recovery window: {message}")
        if sorted(leader.validate_empath_circle_state(sync_members=True, emit_message=False)) != sorted([int(leader.id), int(third.id)]):
            raise AssertionError("Circle should remain coherent after cascade recovery and a member leaving.")

        return {
            "tick_changed": bool(tick_changed),
            "leader_circle": leader.get_empath_circle_member_ids(include_self=True),
            "third_circle": third.get_empath_circle_member_ids(include_self=True),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-failure-cascade-stability",
        scenario_metadata=getattr(run_empath_failure_cascade_stability_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-link-state-compat",
    aliases=["empath_link_state_compat"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath link compatibility coverage validates that persisted link mappings still resolve through the current link helpers and command flow.",
        "tags": ["core", "empath"],
    },
)
def run_empath_link_state_compat_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_LINK_COMPAT_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_LINK_COMPAT_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_LINK_COMPAT_PATIENT")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        patient.db.wounds = {"vitality": 0, "bleeding": 20, "fatigue": 0, "poison": 0, "disease": 0}
        empath.db.empath_link = {
            "target_id": int(patient.id),
            "type": "touch",
            "strength": 60,
            "stability": 80,
            "created_at": time.time(),
        }

        resolved_target = empath.get_empath_link_target(getattr(empath.db, "empath_link", None))
        if resolved_target != patient:
            raise AssertionError(f"Persisted empath link mapping did not resolve back to the patient: {resolved_target}")

        ctx.snapshot("initial")
        output_index = len(ctx.output_log)
        ctx.cmd("take bleeding")
        take_output = list(ctx.output_log[output_index:])
        ctx.snapshot("took_bleeding")

        patient_bleeding = int(patient.get_empath_wound("bleeding") or 0)
        empath_bleeding = int(empath.get_empath_wound("bleeding") or 0)
        if patient_bleeding >= 20:
            raise AssertionError(f"Take bleeding did not resolve through the stored link state: {patient_bleeding}")
        if empath_bleeding <= 0:
            raise AssertionError(f"Take bleeding did not place any burden on the empath: {empath_bleeding}")
        if not any("draw the injury into yourself" in str(line).lower() or "lessen the burden" in str(line).lower() for line in take_output):
            raise AssertionError(f"Take bleeding through persisted link state did not emit transfer messaging: {take_output}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "resolved_target_id": int(getattr(resolved_target, "id", 0) or 0),
            "patient_bleeding": patient_bleeding,
            "empath_bleeding": empath_bleeding,
            "take_output": take_output,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-link-state-compat",
        scenario_metadata=getattr(run_empath_link_state_compat_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-vitality-transfer",
    aliases=["empath_vitality_transfer"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath vitality-transfer regression coverage validates HP cost, overdraw, unity lockout, and partial lockout without depending on wall-clock timing.",
        "tags": ["core", "empath"],
    },
)
def run_empath_vitality_transfer_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_VITALITY_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_VITALITY_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_VITALITY_PATIENT")
        partner = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_VITALITY_PARTNER")
        fatalist = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_VITALITY_FATALIST")
        fatal_patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_VITALITY_FATAL_PATIENT")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        fatalist.set_profession("empath")
        empath.db.max_hp = 100
        empath.db.hp = 100
        fatalist.db.max_hp = 100
        fatalist.db.hp = 10
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        patient.db.wounds = {"vitality": 80, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        partner.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        fatalist.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        fatal_patient.db.wounds = {"vitality": 40, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}

        profile = empath.get_empath_transfer_profile("vitality")
        mitigation = empath.get_empath_mitigation()
        expected_hp_cost = max(1, int(20 * float(profile.get("hp_ratio", 0.5) or 0.5)))
        expected_fatigue = max(1, int(20 * float(profile.get("fatigue_ratio", 0.35) or 0.35)))
        expected_shock = max(1, int(20 * float(profile.get("shock_ratio", 0.3) or 0.3)))
        expected_vitality_take = max(1, int(20 * mitigation))

        ctx.snapshot("initial")
        ctx.cmd("link TEST_EMPATH_VITALITY_PATIENT")
        ctx.cmd("unity TEST_EMPATH_VITALITY_PARTNER")
        ctx.snapshot("unified")

        partial_output_index = len(ctx.output_log)
        ctx.cmd("take 25%")
        partial_output = list(ctx.output_log[partial_output_index:])
        ctx.snapshot("partial_blocked")

        if patient.get_empath_wound("vitality") != 80 or empath.get_empath_wound("vitality") != 0 or partner.get_empath_wound("vitality") != 0:
            raise AssertionError("Generic partial transfer should not resolve onto vitality.")
        if not any("no wound you can draw that way" in str(line).lower() for line in partial_output):
            raise AssertionError(f"Vitality partial lockout did not emit the expected failure: {partial_output}")

        hp_before = int(getattr(empath.db, "hp", 0) or 0)
        shock_before = int(empath.get_empath_shock() or 0)
        fatigue_before = int(empath.get_empath_wound("fatigue") or 0)
        total_before = patient.get_empath_wound("vitality") + empath.get_empath_wound("vitality") + partner.get_empath_wound("vitality")

        take_output_index = len(ctx.output_log)
        ctx.cmd("take vitality 20")
        take_output = list(ctx.output_log[take_output_index:])
        ctx.snapshot("vitality_taken")

        hp_after = int(getattr(empath.db, "hp", 0) or 0)
        shock_after = int(empath.get_empath_shock() or 0)
        fatigue_after = int(empath.get_empath_wound("fatigue") or 0)
        patient_vitality = patient.get_empath_wound("vitality")
        empath_vitality = empath.get_empath_wound("vitality")
        partner_vitality = partner.get_empath_wound("vitality")
        total_after = patient_vitality + empath_vitality + partner_vitality

        if patient_vitality != 60:
            raise AssertionError(f"Vitality transfer did not reduce the patient by the full amount: {patient_vitality}")
        if empath_vitality != expected_vitality_take:
            raise AssertionError(f"Vitality transfer did not add the full burden to the empath: {empath_vitality}")
        if partner_vitality != 0:
            raise AssertionError(f"Vitality transfer should bypass unity smoothing entirely: {partner_vitality}")
        if hp_after != hp_before - expected_hp_cost:
            raise AssertionError(f"Vitality HP cost should scale with effective amount: before={hp_before}, after={hp_after}, expected={expected_hp_cost}")
        if fatigue_after != fatigue_before + expected_fatigue:
            raise AssertionError(f"Vitality fatigue spike was incorrect: before={fatigue_before}, after={fatigue_after}, expected={expected_fatigue}")
        if shock_after != shock_before + expected_shock:
            raise AssertionError(f"Vitality shock spike was incorrect: before={shock_before}, after={shock_after}, expected={expected_shock}")
        if total_before - total_after != 20 - expected_vitality_take:
            raise AssertionError(f"Vitality burden conservation drifted: before={total_before}, after={total_after}")
        if not any("living force" in str(line).lower() for line in take_output):
            raise AssertionError(f"Vitality transfer did not emit the danger message: {take_output}")

        patient.set_empath_wound("vitality", 100)
        overdraw_output_index = len(ctx.output_log)
        ctx.cmd("take vitality all")
        overdraw_output = list(ctx.output_log[overdraw_output_index:])
        ctx.snapshot("overdrawn")

        if not empath.is_empath_overdrawn():
            raise AssertionError("Vitality transfer should be able to trigger existing overdraw state.")
        if partner.get_empath_wound("vitality") != 0:
            raise AssertionError("Unity partner should still receive no vitality burden after an overdraw transfer.")
        if not any("taken too much" in str(line).lower() for line in overdraw_output):
            raise AssertionError(f"Overdraw warning did not fire after a large vitality transfer: {overdraw_output}")

        direct_ok, direct_message = empath.take_empath_wound("vitality", requested_fraction=0.25)
        direct_text = str(direct_message).lower()
        if direct_ok or ("life force" not in direct_text and "senses still reel" not in direct_text):
            raise AssertionError(f"Direct partial vitality lockout failed: ok={direct_ok}, message={direct_message}")

        link_ok, _link_state = fatalist.create_empath_link(fatal_patient, link_type="direct")
        if not link_ok:
            raise AssertionError("Failed to create a direct vitality link for lethal-transfer coverage.")
        death_ok, death_message = fatalist.take_empath_wound("vitality", "all")
        if not death_ok:
            raise AssertionError(f"Lethal vitality transfer unexpectedly failed: {death_message}")
        if int(getattr(fatalist.db, "hp", 0) or 0) != 0 or not bool(getattr(fatalist.db, "is_dead", False)):
            raise AssertionError(f"Vitality HP damage did not flow through the death pipeline: hp={getattr(fatalist.db, 'hp', None)}, dead={getattr(fatalist.db, 'is_dead', None)}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "partial_output": partial_output,
            "take_output": take_output,
            "overdraw_output": overdraw_output,
            "patient_vitality": patient_vitality,
            "empath_vitality": empath_vitality,
            "partner_vitality": partner_vitality,
            "hp_before": hp_before,
            "hp_after": hp_after,
            "shock_before": shock_before,
            "shock_after": shock_after,
            "fatigue_before": fatigue_before,
            "fatigue_after": fatigue_after,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-vitality-transfer",
        scenario_metadata=getattr(run_empath_vitality_transfer_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-completion-pass",
    aliases=["empath_completion_pass"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath completion coverage validates mitigation, scars, center scaling, link borrowing, channel pulse, stabilize scaling, and guild-zone effects without depending on real-time waits.",
        "tags": ["core", "empath"],
    },
)
def run_empath_completion_pass_scenario(args):
    _setup_django()

    def scenario(ctx):
        triage_room = ctx.harness.create_test_room(key="TEST_EMPATH_TRIAGE_ROOM")
        recovery_room = ctx.harness.create_test_room(key="TEST_EMPATH_RECOVERY_ROOM")
        training_room = ctx.harness.create_test_room(key="TEST_EMPATH_TRAINING_ROOM")
        triage_room.tags.add("empath_zone_triage")
        triage_room.db.empath_zone = "triage"
        recovery_room.tags.add("empath_zone_recovery")
        recovery_room.db.empath_zone = "recovery"
        training_room.tags.add("empath_zone_training")
        training_room.db.empath_zone = "training"

        empath = ctx.harness.create_test_character(room=triage_room, key="TEST_EMPATH_COMPLETION_HEALER")
        patient = ctx.harness.create_test_character(room=triage_room, key="TEST_EMPATH_COMPLETION_PATIENT")

        ctx.character = empath
        ctx.room = triage_room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        empath.update_skill("empathy", rank=100, mindstate=0)
        empath.update_skill("first_aid", rank=80, mindstate=0)
        empath.update_skill("attunement", rank=60, mindstate=0)
        patient.update_skill("scholarship", rank=60, mindstate=0)
        empath.db.max_hp = 100
        empath.db.hp = 100
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        patient.db.wounds = {"vitality": 20, "bleeding": 20, "fatigue": 0, "poison": 0, "disease": 40}

        ctx.snapshot("initial")
        ctx.cmd("link TEST_EMPATH_COMPLETION_PATIENT")
        ctx.snapshot("linked")

        mitigation_output_index = len(ctx.output_log)
        ctx.cmd("take disease 20")
        mitigation_output = list(ctx.output_log[mitigation_output_index:])
        ctx.snapshot("mitigated")

        if patient.get_empath_wound("disease") != 20:
            raise AssertionError(f"Mitigation pass did not remove the full effective amount from the patient: {patient.db.wounds}")
        if empath.get_empath_wound("disease") != 16:
            raise AssertionError(f"Mitigation pass did not reduce empath intake according to skill: {empath.db.wounds}")
        if empath.get_empath_wound("fatigue") != 5:
            raise AssertionError(f"Mitigation pass should apply the current disease-transfer fatigue cost: {empath.db.wounds}")
        if not any("lessen the burden" in str(line).lower() for line in mitigation_output):
            raise AssertionError(f"Mitigation message did not surface: {mitigation_output}")

        focus_output_index = len(ctx.output_log)
        ctx.cmd("link focus scholarship")
        focus_output = list(ctx.output_log[focus_output_index:])
        ctx.snapshot("focused")

        if empath.get_skill("scholarship") != 12:
            raise AssertionError(f"Borrowed link focus did not apply the expected bonus: {empath.get_skill('scholarship')}")
        if not any("scholarship" in str(line).lower() for line in focus_output):
            raise AssertionError(f"Link focus did not emit expected feedback: {focus_output}")

        empath.move_to(training_room, quiet=True, use_destination=False)
        patient.move_to(training_room, quiet=True, use_destination=False)
        ctx.room = training_room
        link_ok, _link_lines = empath.link_empath_target(patient)
        if not link_ok:
            raise AssertionError("Empath link should be restorable after moving together into the training room.")
        focus_ok, focus_message = empath.set_empath_link_focus("scholarship")
        if not focus_ok:
            raise AssertionError(f"Empath link focus should be restorable in the training room: {focus_message}")
        link_state = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        updated_link = dict(link_state)
        updated_link["link_bonus_tick_at"] = time.time() - 1.0
        empath.set_empath_link_state(updated_link, sync=True)
        fatigue_before_focus_upkeep = empath.get_empath_wound("fatigue")
        empath.process_empath_tick()
        fatigue_after_focus_upkeep = empath.get_empath_wound("fatigue")
        ctx.snapshot("focus_upkeep")

        if fatigue_after_focus_upkeep - fatigue_before_focus_upkeep != 2:
            raise AssertionError(f"Training-room link upkeep should be reduced to 2 fatigue, got {fatigue_after_focus_upkeep - fatigue_before_focus_upkeep}")

        channel_output_index = len(ctx.output_log)
        ctx.cmd("channel bleeding")
        channel_output = list(ctx.output_log[channel_output_index:])
        channel_state = dict(empath.get_state("empath_channel") or {})
        channel_state["next_pulse_at"] = time.time() - 1.0
        empath.set_state("empath_channel", channel_state)
        updated_link = dict(empath.get_empath_link_state(require_local=True, emit_break_messages=False))
        updated_link["link_bonus_tick_at"] = time.time() + 30.0
        empath.set_empath_link_state(updated_link, sync=True)
        patient_bleeding_before = patient.get_empath_wound("bleeding")
        fatigue_before_channel = empath.get_empath_wound("fatigue")
        empath.process_empath_tick()
        fatigue_after_channel = empath.get_empath_wound("fatigue")
        patient_bleeding_after = patient.get_empath_wound("bleeding")
        channel_state_after = empath.get_state("empath_channel") or {}
        ctx.snapshot("channeled")

        if not any("sustained channel" in str(line).lower() for line in channel_output):
            raise AssertionError(f"Channel did not emit its start message: {channel_output}")
        if patient_bleeding_after >= patient_bleeding_before:
            raise AssertionError(f"Channel pulse did not transfer any bleeding: before={patient_bleeding_before}, after={patient_bleeding_after}")
        if fatigue_after_channel - fatigue_before_channel != 2:
            raise AssertionError(f"Training-room channel strain should be reduced to 2 fatigue on the first pulse, got {fatigue_after_channel - fatigue_before_channel}")
        if int(channel_state_after.get("pulse_count", 0) or 0) != 1:
            raise AssertionError(f"Channel pulse count did not advance: {channel_state_after}")

        stop_output_index = len(ctx.output_log)
        ctx.cmd("channel stop")
        stop_output = list(ctx.output_log[stop_output_index:])
        if empath.get_state("empath_channel"):
            raise AssertionError("Channel stop should clear the active channel state.")
        if not any("let the sustained channel go" in str(line).lower() for line in stop_output):
            raise AssertionError(f"Channel stop did not emit the expected feedback: {stop_output}")

        empath.move_to(recovery_room, quiet=True, use_destination=False)
        patient.move_to(recovery_room, quiet=True, use_destination=False)
        ctx.room = recovery_room
        empath.db.empath_shock = 40
        fatigue_before_center = empath.get_empath_wound("fatigue")
        center_output_index = len(ctx.output_log)
        ctx.cmd("center")
        center_output = list(ctx.output_log[center_output_index:])
        ctx.snapshot("centered")

        if empath.get_empath_shock() != 17:
            raise AssertionError(f"Recovery-room center should reduce shock by 23, got {empath.get_empath_shock()}")
        if empath.get_empath_wound("fatigue") - fatigue_before_center != 7:
            raise AssertionError(f"Recovery-room center should cost 7 fatigue, got {empath.get_empath_wound('fatigue') - fatigue_before_center}")
        if not any("regaining clarity" in str(line).lower() for line in center_output):
            raise AssertionError(f"Center did not emit the expected recovery message: {center_output}")

        patient.apply_damage("head", 30, "slice")
        patient.apply_damage("head", 20, "slice")
        head_scars_before = patient.get_part_scar_count("head")
        patient.heal_body_part("head", 100)
        if patient.get_part_scar_count("head") != head_scars_before or head_scars_before <= 0:
            raise AssertionError(f"Scars should persist after normal healing: before={head_scars_before}, after={patient.get_part_scar_count('head')}")

        empath.move_to(triage_room, quiet=True, use_destination=False)
        patient.move_to(triage_room, quiet=True, use_destination=False)
        triage_room.tags.add("empath_zone_triage")
        triage_room.db.empath_zone = "triage"
        patient.get_body_part("head")["internal"] = 30
        patient.get_body_part("chest")["internal"] = 35
        patient.get_body_part("left_arm")["internal"] = 28
        patient.get_body_part("head")["bleed"] = 1
        patient.get_body_part("chest")["bleed"] = 1
        patient.get_body_part("left_arm")["bleed"] = 1
        stabilize_output_index = len(ctx.output_log)
        ctx.cmd("stabilize TEST_EMPATH_COMPLETION_PATIENT")
        stabilize_output = list(ctx.output_log[stabilize_output_index:])
        ctx.snapshot("stabilized")

        tended_parts = [part for part in ("head", "chest", "left_arm") if patient.is_tended(part)]
        if len(tended_parts) != 3:
            raise AssertionError(f"Triage-room stabilize should tend three parts, got {tended_parts}")
        if float(getattr(patient.db, "stability_strength", 0.0) or 0.0) <= 0.0:
            raise AssertionError("Stabilize should store a positive stability strength.")
        if not any("steady their condition" in str(line).lower() for line in stabilize_output):
            raise AssertionError(f"Stabilize did not emit the expected message: {stabilize_output}")

        scar_heal_output_index = len(ctx.output_log)
        ctx.cmd("heal scars TEST_EMPATH_COMPLETION_PATIENT")
        scar_heal_output = list(ctx.output_log[scar_heal_output_index:])
        ctx.snapshot("scar_healed")

        if patient.get_part_scar_count("head") != max(0, head_scars_before - 1):
            raise AssertionError(f"Heal scars should reduce the highest scar count by one: before={head_scars_before}, after={patient.get_part_scar_count('head')}")
        if not any("old scarring" in str(line).lower() for line in scar_heal_output):
            raise AssertionError(f"Heal scars did not emit the expected feedback: {scar_heal_output}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "mitigation_output": mitigation_output,
            "focus_output": focus_output,
            "channel_output": channel_output,
            "center_output": center_output,
            "stabilize_output": stabilize_output,
            "scar_heal_output": scar_heal_output,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-completion-pass",
        scenario_metadata=getattr(run_empath_completion_pass_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-learning-unification",
    aliases=["empath_learning_unification"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath learning unification coverage validates transient pools and legacy mindstate isolation without depending on wall-clock waits.",
        "tags": ["core", "empath", "exp"],
    },
)
def run_empath_learning_unification_scenario(args):
    _setup_django()

    def scenario(ctx):
        from evennia.utils.create import create_object
        from typeclasses.study_item import StudyItem

        training_room = ctx.harness.create_test_room(key="TEST_EMPATH_LEARNING_ROOM")
        healer = ctx.harness.create_test_character(room=training_room, key="TEST_EMPATH_LEARNING_HEALER")
        patient = ctx.harness.create_test_character(room=training_room, key="TEST_EMPATH_LEARNING_PATIENT")
        empath_patient = ctx.harness.create_test_character(room=training_room, key="TEST_EMPATH_LEARNING_EMPATH_PATIENT")
        animal = ctx.harness.create_test_character(room=training_room, key="TEST_EMPATH_LEARNING_ANIMAL")

        ctx.character = healer
        ctx.room = training_room

        healer.set_profession("empath")
        _diretest_set_progression_rank(healer, "empathy", 20)
        empath_patient.set_profession("empath")
        healer.db.empath_rank = 20
        healer.db.empath_training_stage = 0
        healer.db.empath_shock = 0
        healer.update_skill("empathy", rank=120, mindstate=0)
        healer.update_skill("first_aid", rank=90, mindstate=0)
        healer.update_skill("scholarship", rank=80, mindstate=0)
        patient.update_skill("scholarship", rank=10, mindstate=0)

        animal.db.desc = "A simple animal with little resistance to empathic influence."
        animal.db.creature_type = "animal"
        animal.db.stats = dict(animal.db.stats or {})
        animal.db.stats["discipline"] = 4
        animal.db.stats["intelligence"] = 4

        for wound_key, wound_value in {"vitality": 30, "bleeding": 25, "fatigue": 0, "poison": 20, "disease": 20, "trauma": 0}.items():
            patient.set_empath_wound(wound_key, wound_value)
            empath_patient.set_empath_wound(wound_key, wound_value)
        for skill_name in ("empathy", "first_aid", "scholarship"):
            healer.update_skill(skill_name, rank=healer.get_skill_rank(skill_name), mindstate=0)

        empathy_skill = healer.exp_skills.get("empathy")
        first_aid_skill = healer.exp_skills.get("first_aid")
        scholarship_skill = healer.exp_skills.get("scholarship")
        if empathy_skill.skillset != "primary":
            raise AssertionError(f"Empathy should use primary transient tier, got {empathy_skill.skillset}")
        if first_aid_skill.skillset != "secondary":
            raise AssertionError(f"First Aid should use secondary transient tier, got {first_aid_skill.skillset}")
        if scholarship_skill.skillset != "secondary":
            raise AssertionError(f"Scholarship should use secondary transient tier, got {scholarship_skill.skillset}")

        ok, _link_state = healer.link_empath_target(patient)
        if not ok:
            raise AssertionError("Link creation should succeed for the baseline patient.")
        link_pool = healer.exp_skills.get("empathy").pool
        if link_pool <= 0:
            raise AssertionError("Linking should award transient empathy pool.")
        if healer.db.skills.get("empathy", {}).get("mindstate", 0) != 0:
            raise AssertionError("Linking should not write legacy empathy mindstate.")

        before_perceive = healer.exp_skills.get("empathy").pool
        ok, _lines = healer.perceive_empath_target(patient)
        if not ok or healer.exp_skills.get("empathy").pool <= before_perceive:
            raise AssertionError("Perceive target should award a small empathy gain through transient EXP.")

        before_manipulate = healer.exp_skills.get("empathy").pool
        ok, message = healer.manipulate_empath_target(animal)
        if not ok:
            raise AssertionError(f"Manipulate should succeed against the test animal: {message}")
        if healer.exp_skills.get("empathy").pool <= before_manipulate:
            raise AssertionError("Manipulate should award empathy through transient EXP.")

        ok, _link_state = healer.link_empath_target(patient)
        if not ok:
            raise AssertionError("Link creation should succeed before vitality transfer.")
        before_vitality = healer.exp_skills.get("empathy").pool
        ok, message = healer.take_empath_wound("vitality", "10")
        if not ok:
            raise AssertionError(f"Vitality transfer should succeed: {message}")
        vitality_gain = healer.exp_skills.get("empathy").pool - before_vitality
        if vitality_gain <= 0:
            raise AssertionError("Vitality transfer should award empathy pool.")

        patient.set_empath_wound("poison", 20)
        ok, _link_state = healer.link_empath_target(patient)
        if not ok:
            raise AssertionError("Link creation should succeed before poison transfer.")
        before_poison = healer.exp_skills.get("empathy").pool
        ok, message = healer.take_empath_wound("poison", "10")
        if not ok:
            raise AssertionError(f"Poison transfer should succeed: {message}")
        poison_gain = healer.exp_skills.get("empathy").pool - before_poison
        if poison_gain <= 0:
            raise AssertionError("Poison transfer should award empathy pool.")

        patient.get_body_part("head")["external"] = 9
        patient.get_body_part("head")["internal"] = 4
        patient.get_body_part("chest")["external"] = 0
        patient.get_body_part("chest")["internal"] = 0
        ok, _link_state = healer.link_empath_target(patient)
        if not ok:
            raise AssertionError("Link creation should succeed before shift testing.")
        before_shift = healer.exp_skills.get("empathy").pool
        with patch("typeclasses.characters.random.random", return_value=0.5):
            ok, message = healer.shift_empath_injury(patient, "torso")
        if not ok:
            raise AssertionError(f"Shift should succeed on a linked patient: {message}")
        shift_gain = healer.exp_skills.get("empathy").pool - before_shift
        if shift_gain <= 0:
            raise AssertionError("Shift should award empathy pool.")
        if healer.db.skills.get("empathy", {}).get("mindstate", 0) != 0:
            raise AssertionError("Shift should not update legacy empathy mindstate.")

        empath_patient.set_empath_wound("poison", 20)
        ok, _link_state = healer.link_empath_target(empath_patient)
        if not ok:
            raise AssertionError("Link creation should succeed before empath-target transfer.")
        before_empath_target = healer.exp_skills.get("empathy").pool
        ok, message = healer.take_empath_wound("poison", "10")
        if not ok:
            raise AssertionError(f"Transfer from another empath should still function: {message}")
        empath_target_gain = healer.exp_skills.get("empathy").pool - before_empath_target
        if empath_target_gain <= 0:
            raise AssertionError("Healing another empath should still award empathy pool.")
        if healer.db.skills.get("empathy", {}).get("mindstate", 0) != 0:
            raise AssertionError("Empathy actions should no longer update legacy empathy mindstate.")

        patient.get_body_part("head")["bleed"] = 3
        patient.get_body_part("head")["internal"] = 28
        ok, message = healer.stabilize_empath_target(patient)
        if not ok:
            raise AssertionError(f"Stabilize should succeed on a bleeding patient: {message}")
        tend_state = dict((patient.get_body_part("head") or {}).get("tend") or {})
        if float(tend_state.get("xp_window_until", 0.0) or 0.0) <= time.time():
            raise AssertionError("Valid tending should start a First Aid training window.")
        tend_state["xp_next_at"] = time.time() - 1.0
        patient.get_body_part("head")["tend"] = tend_state
        before_first_aid = healer.exp_skills.get("first_aid").pool
        patient.process_bleed()
        first_aid_gain = healer.exp_skills.get("first_aid").pool - before_first_aid
        if first_aid_gain <= 0:
            raise AssertionError("Timed tend pulse should award First Aid transient EXP.")
        if healer.db.skills.get("first_aid", {}).get("mindstate", 0) != 0:
            raise AssertionError("Timed tend pulses should not update legacy First Aid mindstate.")

        anatomy_book = create_object(StudyItem, key="anatomy chart", location=healer, home=healer)
        anatomy_book.db.anatomy_study = True
        anatomy_book.db.study_tags = ["anatomy"]
        anatomy_book.db.difficulty = 12
        before_scholarship = healer.exp_skills.get("scholarship").pool
        before_first_aid_study = healer.exp_skills.get("first_aid").pool
        before_empathy_study = healer.exp_skills.get("empathy").pool
        if not healer.study_item(anatomy_book):
            raise AssertionError("Anatomy study should succeed for the test healer.")
        scholarship_gain = healer.exp_skills.get("scholarship").pool - before_scholarship
        first_aid_study_gain = healer.exp_skills.get("first_aid").pool - before_first_aid_study
        empathy_study_gain = healer.exp_skills.get("empathy").pool - before_empathy_study
        if scholarship_gain <= 0 or first_aid_study_gain <= 0:
            raise AssertionError(
                f"Anatomy study should train scholarship and first aid: scholarship={scholarship_gain}, first_aid={first_aid_study_gain}"
            )
        if not (0 < empathy_study_gain < scholarship_gain and empathy_study_gain < first_aid_study_gain):
            raise AssertionError(
                f"Anatomy study should only give a tiny empathy gain: empathy={empathy_study_gain}, scholarship={scholarship_gain}, first_aid={first_aid_study_gain}"
            )
        if healer.db.skills.get("scholarship", {}).get("mindstate", 0) != 0:
            raise AssertionError("Scholarship transient study should not update legacy mindstate.")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "link_pool": link_pool,
            "vitality_gain": vitality_gain,
            "poison_gain": poison_gain,
            "shift_gain": shift_gain,
            "empath_target_gain": empath_target_gain,
            "first_aid_gain": first_aid_gain,
            "scholarship_gain": scholarship_gain,
            "first_aid_study_gain": first_aid_study_gain,
            "empathy_study_gain": empathy_study_gain,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-learning-unification",
        scenario_metadata=getattr(run_empath_learning_unification_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-perceive-cooldown",
    aliases=["empath_perceive_cooldown"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Perceive cooldown coverage validates command throttling and normalized room/target output without depending on real waits.",
        "tags": ["core", "empath"],
    },
)
def run_empath_perceive_cooldown_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_PERCEIVE_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_PERCEIVE_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_PERCEIVE_PATIENT")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 20)
        empath.db.last_perceive_time = 0.0
        patient.set_empath_wound("vitality", 35)
        patient.set_empath_wound("bleeding", 18)
        patient.set_empath_wound("poison", 0)
        patient.set_empath_wound("disease", 0)

        output_index = len(ctx.output_log)
        ctx.cmd("perceive")
        first_room_output = list(ctx.output_log[output_index:])
        if not any("TEST_EMPATH_PERCEIVE_PATIENT: injured" in str(line) for line in first_room_output):
            raise AssertionError(f"Perceive room scan did not emit the expected compressed severity output: {first_room_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("perceive TEST_EMPATH_PERCEIVE_PATIENT")
        blocked_output = list(ctx.output_log[output_index:])
        if not any("must wait before perceiving again" in str(line).lower() for line in blocked_output):
            raise AssertionError(f"Perceive cooldown did not block the second immediate use: {blocked_output}")

        empath.db.last_perceive_time = time.time() - 21.0
        output_index = len(ctx.output_log)
        ctx.cmd("perceive TEST_EMPATH_PERCEIVE_PATIENT")
        target_output = list(ctx.output_log[output_index:])
        target_text = " ".join(str(line) for line in target_output)
        for expected in ["Target: TEST_EMPATH_PERCEIVE_PATIENT", "Vitality: unstable", "Wounds: bleeding 18%"]:
            if expected not in target_text:
                raise AssertionError(f"Perceive target did not emit the normalized output structure: {target_output}")

        return {
            "commands": list(ctx.command_log),
            "first_room_output": first_room_output,
            "blocked_output": blocked_output,
            "target_output": target_output,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-perceive-cooldown",
        scenario_metadata=getattr(run_empath_perceive_cooldown_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-shock-transfer",
    aliases=["empath_shock_transfer"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Shock transfer coverage validates linked transfer, overflow capping, and connection enforcement without real-time waits.",
        "tags": ["core", "empath", "shock"],
    },
)
def run_empath_shock_transfer_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_SHOCK_TRANSFER_ROOM")
        healer = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_TRANSFER_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_TRANSFER_PATIENT")

        ctx.character = healer
        ctx.room = room

        healer.set_profession("empath")
        patient.set_profession("empath")
        healer.update_skill("empathy", rank=120, mindstate=0)
        healer.db.empath_shock = 10
        patient.db.empath_shock = 30

        ctx.cmd("touch TEST_EMPATH_SHOCK_TRANSFER_PATIENT")
        output_index = len(ctx.output_log)
        ctx.cmd("take shock TEST_EMPATH_SHOCK_TRANSFER_PATIENT")
        first_take_output = list(ctx.output_log[output_index:])
        if healer.get_empath_shock() != 40 or patient.get_empath_shock() != 0:
            raise AssertionError(
                f"Shock transfer did not move the expected values: healer={healer.get_empath_shock()} patient={patient.get_empath_shock()}"
            )
        if not any("take on the strain" in str(line).lower() for line in first_take_output):
            raise AssertionError(f"Shock transfer did not emit the expected empath message: {first_take_output}")

        healer.db.empath_shock = 78
        patient.db.empath_shock = 20
        output_index = len(ctx.output_log)
        ctx.cmd("take shock TEST_EMPATH_SHOCK_TRANSFER_PATIENT")
        overflow_output = list(ctx.output_log[output_index:])
        if healer.get_empath_shock() != 98 or patient.get_empath_shock() != 0:
            raise AssertionError(
                f"Shock overflow handling did not cap and partially transfer as expected: healer={healer.get_empath_shock()} patient={patient.get_empath_shock()}"
            )
        if not any("take on the strain" in str(line).lower() for line in overflow_output):
            raise AssertionError(f"Shock overflow did not emit the capped transfer message: {overflow_output}")

        healer.db.empath_shock = 20
        healer.break_empath_link(reason="collapse", emit_message=False)
        output_index = len(ctx.output_log)
        ctx.cmd("take shock TEST_EMPATH_SHOCK_TRANSFER_PATIENT")
        unlinked_output = list(ctx.output_log[output_index:])
        if not any("properly connected to transfer shock" in str(line).lower() for line in unlinked_output):
            raise AssertionError(f"Shock transfer should require a valid connection: {unlinked_output}")

        return {
            "commands": list(ctx.command_log),
            "first_take_output": first_take_output,
            "overflow_output": overflow_output,
            "unlinked_output": unlinked_output,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-shock-transfer",
        scenario_metadata=getattr(run_empath_shock_transfer_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-shift-structure",
    aliases=["empath_shift_structure"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Shift structure coverage validates wound relocation while preserving total severity.",
        "tags": ["core", "empath"],
    },
)
def run_empath_shift_structure_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_SHIFT_ROOM")
        healer = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHIFT_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHIFT_PATIENT")

        ctx.character = healer
        ctx.room = room

        healer.set_profession("empath")
        _diretest_set_progression_rank(healer, "empathy", 20)
        injuries = dict(patient.db.injuries or {})
        injuries["left_arm"] = {**dict(injuries.get("left_arm") or {}), "external": 8, "internal": 5, "bleed": 2}
        injuries["chest"] = {**dict(injuries.get("chest") or {}), "external": 0, "internal": 0, "bleed": 0}
        patient.db.injuries = injuries

        total_before = sum(int((patient.get_body_part(part) or {}).get(field, 0) or 0) for part in ("left_arm", "chest") for field in ("external", "internal", "bleed"))
        ctx.cmd("touch TEST_EMPATH_SHIFT_PATIENT")
        with patch("typeclasses.characters.random.random", return_value=0.5):
            ok, message = healer.shift_empath_injury(patient, "torso")
        shift_output = [message]
        if not ok:
            raise AssertionError(f"Shift should succeed on a connected patient: {message}")

        head_after = patient.get_body_part("left_arm") or {}
        chest_after = patient.get_body_part("chest") or {}
        total_after = sum(int((patient.get_body_part(part) or {}).get(field, 0) or 0) for part in ("left_arm", "chest") for field in ("external", "internal", "bleed"))
        if total_before != total_after:
            raise AssertionError(f"Shift changed total injury severity: before={total_before} after={total_after}")
        if any(int(head_after.get(field, 0) or 0) > 0 for field in ("external", "internal", "bleed")):
            raise AssertionError(f"Shift should move the worst wound off the source location: {head_after}")
        if sum(int(chest_after.get(field, 0) or 0) for field in ("external", "internal", "bleed")) != total_before:
            raise AssertionError(f"Shift should relocate the wound to the destination location: {chest_after}")
        if not any("shift the worst of" in str(line).lower() for line in shift_output):
            raise AssertionError(f"Shift did not emit the expected success message: {shift_output}")

        return {
            "commands": list(ctx.command_log),
            "shift_output": shift_output,
            "head_after": {
                "external": int((head_after or {}).get("external", 0) or 0),
                "internal": int((head_after or {}).get("internal", 0) or 0),
                "bleed": int((head_after or {}).get("bleed", 0) or 0),
            },
            "chest_after": {
                "external": int((chest_after or {}).get("external", 0) or 0),
                "internal": int((chest_after or {}).get("internal", 0) or 0),
                "bleed": int((chest_after or {}).get("bleed", 0) or 0),
            },
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-shift-structure",
        scenario_metadata=getattr(run_empath_shift_structure_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-service-foundation",
    aliases=["empath_service_foundation"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Service foundation coverage validates request healing, tipping, and study anatomy command hooks.",
        "tags": ["core", "empath"],
    },
)
def run_empath_service_foundation_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_SERVICE_ROOM")
        healer = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SERVICE_PATIENT")
        house_healer = ctx.harness.create_test_object(key="TEST_EMPATH_HOUSE_HEALER", location=room, typeclass="typeclasses.npcs.HealerNPC")
        chart = ctx.harness.create_test_object(key="anatomy chart", location=healer, typeclass="typeclasses.study_item.StudyItem")

        ctx.character = healer
        ctx.room = room

        healer.set_profession("empath")
        _diretest_set_progression_rank(healer, "empathy", 20)
        healer.db.coins = 100
        healer.db.total_tips = 0
        healer.update_skill("scholarship", rank=80, mindstate=0)
        healer.update_skill("first_aid", rank=70, mindstate=0)
        healer.update_skill("empathy", rank=90, mindstate=0)
        healer.set_empath_wound("vitality", 25)
        healer.set_empath_wound("bleeding", 15)
        chart.db.anatomy_study = True
        chart.db.study_tags = ["anatomy"]
        chart.db.difficulty = 12

        output_index = len(ctx.output_log)
        ctx.cmd("request healing")
        request_output = list(ctx.output_log[output_index:])
        if not any("type request healing confirm" in str(line).lower() for line in request_output):
            raise AssertionError(f"Request healing did not create the expected confirmation prompt: {request_output}")

        coins_before_heal = int(healer.db.coins or 0)
        output_index = len(ctx.output_log)
        ctx.cmd("request healing confirm")
        confirm_output = list(ctx.output_log[output_index:])
        if healer.get_empath_wound("vitality") != 0 or healer.get_empath_wound("bleeding") != 0:
            raise AssertionError(f"Request healing confirm did not resolve the player's wounds: {dict(healer.db.wounds or {})}")
        if int(healer.db.coins or 0) >= coins_before_heal:
            raise AssertionError(f"Request healing confirm did not deduct the flat fee: before={coins_before_heal} after={healer.db.coins}")
        if not any("finishes the work without ceremony" in str(line).lower() for line in confirm_output):
            raise AssertionError(f"Request healing confirm did not emit the healer resolution text: {confirm_output}")

        coins_before_tip = int(healer.db.coins or 0)
        output_index = len(ctx.output_log)
        ctx.cmd("tip 25")
        tip_output = list(ctx.output_log[output_index:])
        if int(healer.db.coins or 0) != coins_before_tip - 25:
            raise AssertionError(f"Tip did not deduct coins correctly: before={coins_before_tip} after={healer.db.coins}")
        if int(healer.db.total_tips or 0) != 25:
            raise AssertionError(f"Tip did not update total_tips correctly: {healer.db.total_tips}")
        if not any("thoughtful gesture" in str(line).lower() for line in tip_output):
            raise AssertionError(f"Tip did not emit the favorable healer feedback: {tip_output}")

        before_scholarship = healer.exp_skills.get("scholarship").pool
        before_first_aid = healer.exp_skills.get("first_aid").pool
        before_empathy = healer.exp_skills.get("empathy").pool
        output_index = len(ctx.output_log)
        ctx.cmd("study anatomy anatomy chart")
        study_output = list(ctx.output_log[output_index:])
        scholarship_gain = healer.exp_skills.get("scholarship").pool - before_scholarship
        first_aid_gain = healer.exp_skills.get("first_aid").pool - before_first_aid
        empathy_gain = healer.exp_skills.get("empathy").pool - before_empathy
        if scholarship_gain <= 0 or first_aid_gain <= 0 or empathy_gain <= 0:
            raise AssertionError(
                f"Study anatomy should train scholarship, first aid, and empathy: scholarship={scholarship_gain} first_aid={first_aid_gain} empathy={empathy_gain}"
            )
        if not any("gain some insight" in str(line).lower() for line in study_output):
            raise AssertionError(f"Study anatomy did not use the expected study feedback path: {study_output}")

        return {
            "commands": list(ctx.command_log),
            "request_output": request_output,
            "confirm_output": confirm_output,
            "tip_output": tip_output,
            "study_output": study_output,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-service-foundation",
        scenario_metadata=getattr(run_empath_service_foundation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-poison-loop",
    aliases=["empath_poison_loop"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath poison-loop regression coverage validates poison, disease, perceive, and purge behavior without failing on environment-specific latency.",
        "tags": ["core", "empath"],
    },
)
def run_empath_poison_loop_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.wounds import apply_poison_tick

        room = ctx.harness.create_test_room(key="TEST_EMPATH_POISON_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_POISON_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_POISON_PATIENT")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 20)
        empath.db.wounds = {"vitality": 10, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 20}
        empath.db.empath_shock = 0
        patient.db.wounds = {"vitality": 50, "bleeding": 40, "fatigue": 0, "poison": 30, "disease": 20}

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")

        output_index = len(ctx.output_log)
        ctx.cmd("perceive health")
        perceive_health_output = list(ctx.output_log[output_index:])
        ctx.snapshot("perceived_room")
        perceive_health_text = " ".join(str(line) for line in perceive_health_output)
        if "TEST_EMPATH_POISON_PATIENT: injured" not in perceive_health_text and "TEST_EMPATH_POISON_PATIENT: critical" not in perceive_health_text:
            raise AssertionError(f"Perceive health did not produce the expected room scan signal: {perceive_health_output}")

        output_index = len(ctx.output_log)
        empath.db.last_perceive_time = time.time() - 21.0
        ctx.cmd("perceive TEST_EMPATH_POISON_PATIENT")
        perceive_target_output = list(ctx.output_log[output_index:])
        ctx.snapshot("perceived_target")
        perceive_target_text = " ".join(str(line) for line in perceive_target_output)
        for expected in ["Target: TEST_EMPATH_POISON_PATIENT", "Vitality: unstable", "Wounds: bleeding 40%, poison 30%, disease 20%"]:
            if expected not in perceive_target_text:
                raise AssertionError(f"Perceive target did not produce the expected structured output: {perceive_target_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("touch TEST_EMPATH_POISON_PATIENT")
        touch_output = list(ctx.output_log[output_index:])
        ctx.snapshot("touched")
        link_state = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if int(link_state.get("strength", 0) or 0) != 60 or int(link_state.get("stability", 0) or 0) != 80:
            raise AssertionError(f"Empath touch should create the expected weak link in poison loop: {link_state}")
        if not any("sense the condition of your patient" in str(line).lower() for line in touch_output):
            raise AssertionError(f"Empath touch did not emit the expected feedback: {touch_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("assess")
        assess_output = list(ctx.output_log[output_index:])
        ctx.snapshot("assessed")
        assess_text = " ".join(str(line) for line in assess_output)
        for expected in ["Vitality: 50%", "Bleeding: 40%", "Poison: 30%", "Disease: 20%"]:
            if expected not in assess_text:
                raise AssertionError(f"Empath assess did not include expected exact wound values: {assess_output}")

        vitality_before_poison_take = int((empath.db.wounds or {}).get("vitality", 0) or 0)
        output_index = len(ctx.output_log)
        ctx.cmd("take poison")
        take_poison_output = list(ctx.output_log[output_index:])
        ctx.snapshot("took_poison")

        patient_after_poison = dict(getattr(patient.db, "wounds", {}) or {})
        empath_after_poison = dict(getattr(empath.db, "wounds", {}) or {})
        if int(patient_after_poison.get("poison", 0) or 0) != 18:
            raise AssertionError(f"Poison transfer did not reduce patient poison correctly: {patient_after_poison}")
        if int(empath_after_poison.get("poison", 0) or 0) != 12:
            raise AssertionError(f"Poison transfer did not load poison onto the Empath correctly: {empath_after_poison}")
        expected_vitality_after_poison = vitality_before_poison_take + int(12 * 0.3)
        if int(empath_after_poison.get("vitality", 0) or 0) != expected_vitality_after_poison:
            raise AssertionError(f"Poison transfer did not apply the immediate vitality spike: {empath_after_poison}")
        if not any("draw the injury into yourself" in str(line).lower() for line in take_poison_output):
            raise AssertionError(f"Take poison did not emit the transfer message: {take_poison_output}")

        vitality_before_tick = int((empath.db.wounds or {}).get("vitality", 0) or 0)
        tick_damage = ctx.direct(apply_poison_tick, empath)
        ctx.snapshot("poison_ticked")
        vitality_after_tick = int((empath.db.wounds or {}).get("vitality", 0) or 0)
        if int(tick_damage or 0) <= 0 or vitality_after_tick <= vitality_before_tick:
            raise AssertionError(f"Poison tick did not increase vitality damage as required: damage={tick_damage}, before={vitality_before_tick}, after={vitality_after_tick}")

        output_index = len(ctx.output_log)
        ctx.cmd("take bleeding")
        take_bleeding_output = list(ctx.output_log[output_index:])
        ctx.snapshot("took_bleeding")

        patient_after_bleeding = dict(getattr(patient.db, "wounds", {}) or {})
        empath_after_bleeding = dict(getattr(empath.db, "wounds", {}) or {})
        if int(patient_after_bleeding.get("bleeding", 0) or 0) != 28:
            raise AssertionError(f"Bleeding transfer did not reduce patient bleeding correctly: {patient_after_bleeding}")
        if int(empath_after_bleeding.get("bleeding", 0) or 0) != 16:
            raise AssertionError(f"Bleeding transfer did not preserve the dangerous self-spike behavior: {empath_after_bleeding}")
        if not any("draw the injury into yourself" in str(line).lower() for line in take_bleeding_output):
            raise AssertionError(f"Take bleeding did not emit the transfer message: {take_bleeding_output}")

        vitality_before_mend = int((empath.db.wounds or {}).get("vitality", 0) or 0)
        bleeding_before_mend = int((empath.db.wounds or {}).get("bleeding", 0) or 0)
        output_index = len(ctx.output_log)
        ctx.cmd("mend self")
        mend_output = list(ctx.output_log[output_index:])
        ctx.snapshot("mended")

        empath_after_mend = dict(getattr(empath.db, "wounds", {}) or {})
        if int(empath_after_mend.get("vitality", 0) or 0) != max(0, vitality_before_mend - 8):
            raise AssertionError(f"Disease penalty did not reduce vitality healing to the expected amount: before={vitality_before_mend}, after={empath_after_mend}")
        if int(empath_after_mend.get("bleeding", 0) or 0) != max(0, bleeding_before_mend - 4):
            raise AssertionError(f"Disease penalty did not reduce bleeding healing to the expected amount: before={bleeding_before_mend}, after={empath_after_mend}")
        if not any("focus inward, stabilizing your condition" in str(line).lower() for line in mend_output):
            raise AssertionError(f"Mend self did not emit the expected feedback: {mend_output}")

        fatigue_before_purge = int((empath.db.wounds or {}).get("fatigue", 0) or 0)
        poison_before_purge = int((empath.db.wounds or {}).get("poison", 0) or 0)
        output_index = len(ctx.output_log)
        ctx.cmd("purge poison")
        purge_output = list(ctx.output_log[output_index:])
        ctx.snapshot("purged")

        empath_after_purge = dict(getattr(empath.db, "wounds", {}) or {})
        if int(empath_after_purge.get("poison", 0) or 0) != max(0, poison_before_purge - 15):
            raise AssertionError(f"Purge poison did not reduce poison by the locked amount: before={poison_before_purge}, after={empath_after_purge}")
        if int(empath_after_purge.get("fatigue", 0) or 0) != fatigue_before_purge + 10:
            raise AssertionError(f"Purge poison did not apply the fatigue cost: before={fatigue_before_purge}, after={empath_after_purge}")
        if not any("force the corruption from your body" in str(line).lower() for line in purge_output):
            raise AssertionError(f"Purge poison did not emit the expected feedback: {purge_output}")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["initial", "perceived_room", "perceived_target", "touched", "assessed", "took_poison", "poison_ticked", "took_bleeding", "mended", "purged"]
        if labels != expected_labels:
            raise AssertionError(f"Empath poison-loop snapshot labels drifted: expected {expected_labels}, got {labels}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "perceive_health_output": perceive_health_output,
            "perceive_target_output": perceive_target_output,
            "assess_output": assess_output,
            "take_poison_output": take_poison_output,
            "take_bleeding_output": take_bleeding_output,
            "mend_output": mend_output,
            "purge_output": purge_output,
            "tick_damage": tick_damage,
            "patient_after_poison": patient_after_poison,
            "empath_after_poison": empath_after_poison,
            "patient_after_bleeding": patient_after_bleeding,
            "empath_after_bleeding": empath_after_bleeding,
            "empath_after_mend": empath_after_mend,
            "empath_after_purge": empath_after_purge,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-poison-loop",
        scenario_metadata=getattr(run_empath_poison_loop_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-shock-lockout",
    aliases=["empath_shock_lockout"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath shock lockout coverage validates offensive shock gain, automatic link breakage, and center-based recovery without failing on environment-specific latency.",
        "tags": ["core", "empath", "shock", "smoke"],
    },
)
def run_empath_shock_lockout_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_SHOCK_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_PATIENT")
        foe_one = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_FOE_ONE")
        foe_two = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SHOCK_FOE_TWO")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        empath.db.empath_shock = 0
        patient.db.wounds = {"vitality": 40, "bleeding": 15, "fatigue": 0, "poison": 0, "disease": 0}

        empath.set_stat("agility", 40)
        empath.set_stat("reflex", 40)
        foe_one.set_stat("agility", 1)
        foe_one.set_stat("reflex", 1)
        foe_two.set_stat("agility", 1)
        foe_two.set_stat("reflex", 1)
        foe_one.set_hp(1)
        foe_two.set_hp(1)

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")

        output_index = len(ctx.output_log)
        ctx.cmd("touch TEST_EMPATH_SHOCK_PATIENT")
        touch_before_output = list(ctx.output_log[output_index:])
        ctx.snapshot("linked")
        link_state = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if int(link_state.get("target_id", 0) or 0) != int(getattr(patient, "id", 0) or 0):
            raise AssertionError(f"Empath did not establish the initial patient link: {link_state}")

        empath.register_empath_offensive_action(target=foe_one, context="attack", amount=15)
        empath.register_empath_offensive_action(target=foe_one, context="kill", amount=30)
        ctx.snapshot("first_kill")
        shock_after_first = empath.get_empath_shock()
        if shock_after_first != 45:
            raise AssertionError(f"First empath kill should apply 45 shock total, got {shock_after_first}")

        empath.register_empath_offensive_action(target=foe_two, context="attack", amount=15)
        empath.register_empath_offensive_action(target=foe_two, context="kill", amount=30)
        ctx.snapshot("second_kill")
        shock_after_second = empath.get_empath_shock()
        if shock_after_second < 80:
            raise AssertionError(f"Second empath kill should push shock into lockout, got {shock_after_second}")
        if empath.get_empath_link_state(require_local=False, emit_break_messages=False):
            raise AssertionError("Empath link should break automatically once shock reaches disconnection.")

        output_index = len(ctx.output_log)
        ctx.cmd("touch TEST_EMPATH_SHOCK_PATIENT")
        touch_fail_output = list(ctx.output_log[output_index:])
        ctx.snapshot("touch_locked")
        if not any("cut off from others" in str(line).lower() for line in touch_fail_output):
            raise AssertionError(f"Touch should fail from shock lockout: {touch_fail_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("perceive health")
        perceive_fail_output = list(ctx.output_log[output_index:])
        ctx.snapshot("perceive_locked")
        if not any("you sense nothing" in str(line).lower() for line in perceive_fail_output):
            raise AssertionError(f"Perceive should return nothing while disconnected: {perceive_fail_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("take vitality 10")
        take_fail_output = list(ctx.output_log[output_index:])
        ctx.snapshot("take_locked")
        if not any("cut off from others" in str(line).lower() for line in take_fail_output):
            raise AssertionError(f"Take should fail from shock lockout before link validation: {take_fail_output}")

        empath.db.in_combat = False
        empath.db.target = None
        output_index = len(ctx.output_log)
        ctx.cmd("center")
        center_output = list(ctx.output_log[output_index:])
        ctx.snapshot("centered")
        if empath.get_empath_shock() >= 80:
            raise AssertionError(f"Center should reduce shock below lockout threshold, got {empath.get_empath_shock()}")
        if int((empath.db.wounds or {}).get("fatigue", 0) or 0) != 10:
            raise AssertionError(f"Center should apply the locked fatigue cost, got {empath.db.wounds}")
        if not any("regaining clarity" in str(line).lower() for line in center_output):
            raise AssertionError(f"Center did not emit the expected recovery message: {center_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("touch TEST_EMPATH_SHOCK_PATIENT")
        touch_after_output = list(ctx.output_log[output_index:])
        ctx.snapshot("relinked")
        relink_state = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if int(relink_state.get("target_id", 0) or 0) != int(getattr(patient, "id", 0) or 0):
            raise AssertionError("Empath should be able to relink after centering below the disconnection threshold.")
        if not any("sense the condition of your patient" in str(line).lower() for line in touch_after_output):
            raise AssertionError(f"Touch should work again after recovery: {touch_after_output}")

        labels = ctx.get_snapshot_labels()
        expected_labels = [
            "initial",
            "linked",
            "first_kill",
            "second_kill",
            "touch_locked",
            "perceive_locked",
            "take_locked",
            "centered",
            "relinked",
        ]
        if labels != expected_labels:
            raise AssertionError(f"Empath shock-lockout snapshot labels drifted: expected {expected_labels}, got {labels}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "shock_after_first": shock_after_first,
            "shock_after_second": shock_after_second,
            "shock_after_center": empath.get_empath_shock(),
            "touch_before_output": touch_before_output,
            "touch_fail_output": touch_fail_output,
            "perceive_fail_output": perceive_fail_output,
            "take_fail_output": take_fail_output,
            "center_output": center_output,
            "touch_after_output": touch_after_output,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-shock-lockout",
        scenario_metadata=getattr(run_empath_shock_lockout_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-link-stability",
    aliases=["empath_link_stability"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath link stability coverage validates direct-link strength, stability decay, and large-transfer strain without failing on environment-specific latency.",
        "tags": ["core", "empath", "link"],
    },
)
def run_empath_link_stability_scenario(args):
    _setup_django()

    def _serialize_link_state(state):
        if not state:
            return None
        return {
            "target": getattr(state.get("target"), "key", None),
            "target_id": int(state.get("target_id", 0) or 0),
            "type": state.get("type"),
            "strength": int(state.get("strength", 0) or 0),
            "stability": int(state.get("stability", 0) or 0),
            "condition": state.get("condition"),
        }

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_LINK_STABILITY_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_LINK_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_LINK_PATIENT")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        empath.db.empath_shock = 0
        patient.db.wounds = {"vitality": 70, "bleeding": 70, "fatigue": 0, "poison": 0, "disease": 0}

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")

        output_index = len(ctx.output_log)
        ctx.cmd("link TEST_EMPATH_LINK_PATIENT")
        link_output = list(ctx.output_log[output_index:])
        ctx.snapshot("linked")

        initial_link = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if not initial_link or initial_link.get("type") != "direct" or int(initial_link.get("strength", 0) or 0) != 100 or int(initial_link.get("stability", 0) or 0) != 100:
            raise AssertionError(f"Direct link was not created as expected: {initial_link}")
        if not any("shape of their suffering" in str(line).lower() for line in link_output):
            raise AssertionError(f"Link command did not emit the expected direct-link messaging: {link_output}")

        ctx.cmd("take bleeding 20")
        ctx.snapshot("took_bleeding_20")
        after_first = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        direct_small_cost = empath.get_empath_link_stability_cost("direct", "small_transfer")
        direct_large_cost = empath.get_empath_link_stability_cost("direct", "large_transfer")
        expected_after_first = 100 - direct_small_cost
        if not after_first or int(after_first.get("stability", 0) or 0) != expected_after_first:
            raise AssertionError(f"Direct small-transfer strain should reduce stability by the configured small-transfer cost: {after_first}")

        ctx.cmd("take vitality 30")
        ctx.snapshot("took_vitality_30")
        after_second = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        expected_after_second = expected_after_first - direct_small_cost
        if not after_second or int(after_second.get("stability", 0) or 0) >= int(after_first.get("stability", 0) or 0):
            raise AssertionError(f"Vitality transfers should only consume the configured small-transfer stability cost: {after_second}")

        output_index = len(ctx.output_log)
        ctx.cmd("take bleeding 30")
        third_output = list(ctx.output_log[output_index:])
        ctx.snapshot("took_bleeding_30")
        after_third = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if not after_third:
            raise AssertionError("Direct link should still exist but be badly worn after the locked sequence.")
        if int(after_third.get("stability", 0) or 0) >= int(after_second.get("stability", 0) or 0):
            third_text = " ".join(str(line) for line in third_output).lower()
            if "senses still reel" not in third_text and "reeling from the last transfer" not in third_text:
                raise AssertionError(f"Repeated bleeding transfers should either strain the link further or be blocked by overload lockout: state={after_third}, output={third_output}")
        if int(after_third.get("stability", 0) or 0) >= 100:
            raise AssertionError(f"Link stability should weaken under repeated strain: {after_third}")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["initial", "linked", "took_bleeding_20", "took_vitality_30", "took_bleeding_30"]
        if labels != expected_labels:
            raise AssertionError(f"Empath link-stability snapshot labels drifted: expected {expected_labels}, got {labels}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "initial_link": _serialize_link_state(initial_link),
            "after_first": _serialize_link_state(after_first),
            "after_second": _serialize_link_state(after_second),
            "after_third": _serialize_link_state(after_third),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-link-stability",
        scenario_metadata=getattr(run_empath_link_stability_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-link-separation",
    aliases=["empath_link_separation"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath link separation coverage validates automatic link breakage when a patient leaves the room without failing on environment-specific latency.",
        "tags": ["core", "empath", "link"],
    },
)
def run_empath_link_separation_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_LINK_SEPARATION_ROOM")
        far_room = ctx.harness.create_test_room(key="TEST_EMPATH_LINK_FAR_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SEPARATION_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_SEPARATION_PATIENT")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        patient.db.wounds = {"vitality": 45, "bleeding": 20, "fatigue": 0, "poison": 0, "disease": 0}

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")
        ctx.cmd("link TEST_EMPATH_SEPARATION_PATIENT")
        ctx.snapshot("linked")

        patient.move_to(far_room, quiet=True, use_destination=False)

        output_index = len(ctx.output_log)
        ctx.cmd("assess")
        assess_output = list(ctx.output_log[output_index:])
        ctx.snapshot("assess_after_move")
        if not any("distance tears your connection apart" in str(line).lower() for line in assess_output):
            raise AssertionError(f"Assess should break the link cleanly on separation: {assess_output}")
        if empath.get_empath_link_state(require_local=False, emit_break_messages=False):
            raise AssertionError("Link should be cleared after the target leaves the room.")

        output_index = len(ctx.output_log)
        ctx.cmd("take vitality 10")
        take_output = list(ctx.output_log[output_index:])
        ctx.snapshot("take_after_move")
        if not any("not linked to a patient" in str(line).lower() for line in take_output):
            raise AssertionError(f"Take should fail cleanly after separation breaks the link: {take_output}")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["initial", "linked", "assess_after_move", "take_after_move"]
        if labels != expected_labels:
            raise AssertionError(f"Empath link-separation snapshot labels drifted: expected {expected_labels}, got {labels}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "assess_output": assess_output,
            "take_output": take_output,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-link-separation",
        scenario_metadata=getattr(run_empath_link_separation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-link-vs-shock",
    aliases=["empath_link_vs_shock"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath link-vs-shock coverage validates forced link loss and post-center partial recovery without failing on environment-specific latency.",
        "tags": ["core", "empath", "link", "shock"],
    },
)
def run_empath_link_vs_shock_scenario(args):
    _setup_django()

    def _serialize_link_state(state):
        if not state:
            return None
        return {
            "target": getattr(state.get("target"), "key", None),
            "target_id": int(state.get("target_id", 0) or 0),
            "type": state.get("type"),
            "strength": int(state.get("strength", 0) or 0),
            "stability": int(state.get("stability", 0) or 0),
            "condition": state.get("condition"),
        }

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_LINK_SHOCK_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_LINK_SHOCK_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_LINK_SHOCK_PATIENT")
        foe_one = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_LINK_SHOCK_FOE_ONE")
        foe_two = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_LINK_SHOCK_FOE_TWO")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        empath.db.empath_shock = 0
        patient.db.wounds = {"vitality": 35, "bleeding": 20, "fatigue": 0, "poison": 0, "disease": 0}

        empath.set_stat("agility", 40)
        empath.set_stat("reflex", 40)
        foe_one.set_stat("agility", 1)
        foe_one.set_stat("reflex", 1)
        foe_two.set_stat("agility", 1)
        foe_two.set_stat("reflex", 1)
        foe_one.set_hp(1)
        foe_two.set_hp(1)

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("initial")
        ctx.cmd("link TEST_EMPATH_LINK_SHOCK_PATIENT")
        ctx.snapshot("linked")

        initial_link = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if not initial_link or initial_link.get("type") != "direct":
            raise AssertionError(f"Expected an active direct link before shock buildup: {initial_link}")

        empath.register_empath_offensive_action(target=foe_one, context="attack", amount=15)
        empath.register_empath_offensive_action(target=foe_one, context="kill", amount=30)
        ctx.snapshot("first_kill")

        empath.register_empath_offensive_action(target=foe_two, context="attack", amount=15)
        empath.register_empath_offensive_action(target=foe_two, context="kill", amount=30)
        ctx.snapshot("second_kill")

        if empath.get_empath_shock() < 80:
            raise AssertionError(f"Shock should reach disconnected after the locked offensive sequence, got {empath.get_empath_shock()}")
        if empath.get_empath_link_state(require_local=False, emit_break_messages=False):
            raise AssertionError("Direct link should be forcibly cleared by disconnected shock.")

        output_index = len(ctx.output_log)
        ctx.cmd("link TEST_EMPATH_LINK_SHOCK_PATIENT")
        link_fail_output = list(ctx.output_log[output_index:])
        ctx.snapshot("link_locked")
        if not any("cut off from others" in str(line).lower() for line in link_fail_output):
            raise AssertionError(f"Link should remain blocked while disconnected: {link_fail_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("perceive TEST_EMPATH_LINK_SHOCK_PATIENT")
        perceive_fail_output = list(ctx.output_log[output_index:])
        ctx.snapshot("perceive_locked")
        if not any("you sense nothing" in str(line).lower() for line in perceive_fail_output):
            raise AssertionError(f"Perceive target should remain blocked while disconnected: {perceive_fail_output}")

        empath.db.in_combat = False
        empath.db.target = None
        ctx.cmd("center")
        ctx.snapshot("centered")
        if empath.get_empath_shock() <= 0 or empath.get_empath_shock() >= 80:
            raise AssertionError(f"Center should restore access without acting as a full reset, got {empath.get_empath_shock()}")

        output_index = len(ctx.output_log)
        ctx.cmd("link TEST_EMPATH_LINK_SHOCK_PATIENT")
        link_after_output = list(ctx.output_log[output_index:])
        ctx.snapshot("relinked")
        relink_state = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if not relink_state or relink_state.get("type") != "direct":
            raise AssertionError(f"Direct link should be available again after center restores partial access: {relink_state}")
        if not any("shape of their suffering" in str(line).lower() for line in link_after_output):
            raise AssertionError(f"Direct link should work again after recovery: {link_after_output}")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["initial", "linked", "first_kill", "second_kill", "link_locked", "perceive_locked", "centered", "relinked"]
        if labels != expected_labels:
            raise AssertionError(f"Empath link-vs-shock snapshot labels drifted: expected {expected_labels}, got {labels}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "initial_link": _serialize_link_state(initial_link),
            "relink_state": _serialize_link_state(relink_state),
            "link_fail_output": link_fail_output,
            "perceive_fail_output": perceive_fail_output,
            "link_after_output": link_after_output,
            "shock_after_center": empath.get_empath_shock(),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-link-vs-shock",
        scenario_metadata=getattr(run_empath_link_vs_shock_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-persistent-link",
    aliases=["empath_persistent_link"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath persistent-link coverage validates endurance-vs-throughput tradeoffs and clean separation failure without failing on environment-specific latency.",
        "tags": ["core", "empath", "link"],
    },
)
def run_empath_persistent_link_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_PERSISTENT_ROOM")
        far_room = ctx.harness.create_test_room(key="TEST_EMPATH_PERSISTENT_FAR_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_PERSISTENT_HEALER")
        direct_patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_DIRECT_PATIENT")
        persistent_patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_PERSISTENT_PATIENT")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        direct_patient.db.wounds = {"vitality": 40, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        persistent_patient.db.wounds = {"vitality": 40, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}

        ctx.snapshot("initial")
        ctx.cmd("link TEST_EMPATH_DIRECT_PATIENT")
        ctx.snapshot("direct_linked")
        ctx.cmd("take vitality 10")
        ctx.cmd("take vitality 10")
        ctx.cmd("take vitality 10")
        ctx.snapshot("direct_strain")
        direct_link = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        direct_empath_vitality = empath.get_empath_wound("vitality")
        direct_remaining = direct_patient.get_empath_wound("vitality")

        ctx.cmd("release")
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        ctx.cmd("link persistent TEST_EMPATH_PERSISTENT_PATIENT")
        ctx.snapshot("persistent_linked")
        ctx.cmd("take vitality 10")
        ctx.cmd("take vitality 10")
        ctx.cmd("take vitality 10")
        ctx.snapshot("persistent_strain")
        persistent_link = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        persistent_empath_vitality = empath.get_empath_wound("vitality")
        persistent_remaining = persistent_patient.get_empath_wound("vitality")

        if int(direct_link.get("stability", 0) or 0) != 82:
            raise AssertionError(f"Direct link should end at 82 stability after three small transfers: {direct_link}")
        if int(persistent_link.get("stability", 0) or 0) != 108:
            raise AssertionError(f"Persistent link should last longer under small repeated strain: {persistent_link}")
        if persistent_empath_vitality >= direct_empath_vitality:
            raise AssertionError(
                f"Persistent link should carry slightly less throughput than direct: direct={direct_empath_vitality}, persistent={persistent_empath_vitality}"
            )
        if persistent_remaining <= direct_remaining:
            raise AssertionError(
                f"Persistent link should leave more wound on the patient than direct throughput: direct={direct_remaining}, persistent={persistent_remaining}"
            )

        persistent_patient.move_to(far_room, quiet=True, use_destination=False)
        output_index = len(ctx.output_log)
        ctx.cmd("assess")
        assess_output = list(ctx.output_log[output_index:])
        ctx.snapshot("persistent_separated")
        if not any("distance tears your connection apart" in str(line).lower() for line in assess_output):
            raise AssertionError(f"Persistent link should still fail on separation: {assess_output}")
        if empath.get_empath_link_state(require_local=False, emit_break_messages=False):
            raise AssertionError("Persistent link should clear after separation.")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "direct_link": {"stability": int(direct_link.get("stability", 0) or 0), "strength": int(direct_link.get("strength", 0) or 0)},
            "persistent_link": {"stability": int(persistent_link.get("stability", 0) or 0), "strength": int(persistent_link.get("strength", 0) or 0)},
            "direct_empath_vitality": direct_empath_vitality,
            "persistent_empath_vitality": persistent_empath_vitality,
            "direct_remaining": direct_remaining,
            "persistent_remaining": persistent_remaining,
            "assess_output": assess_output,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-persistent-link",
        scenario_metadata=getattr(run_empath_persistent_link_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-unity-burden",
    aliases=["empath_unity_burden"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath unity-burden coverage validates partial smoothing without creating free group healing.",
        "tags": ["core", "empath", "unity"],
    },
)
def run_empath_unity_burden_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_UNITY_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNITY_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNITY_PATIENT")
        partner = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNITY_PARTNER")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        patient.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 40}
        partner.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}

        ctx.snapshot("initial")
        ctx.cmd("link TEST_EMPATH_UNITY_PATIENT")
        ctx.cmd("unity TEST_EMPATH_UNITY_PARTNER")
        ctx.snapshot("unified")
        unity_before = empath.get_empath_unity_state()
        ctx.cmd("take disease 20")
        ctx.snapshot("took_with_unity")

        unity_after = empath.get_empath_unity_state()
        empath_disease = empath.get_empath_wound("disease")
        patient_disease = patient.get_empath_wound("disease")
        partner_disease = partner.get_empath_wound("disease")

        if patient_disease != 20:
            raise AssertionError(f"Primary patient should lose the full requested burden: {patient_disease}")
        if partner_disease != 3:
            raise AssertionError(f"Unity should smooth only a small share onto the secondary target: {partner_disease}")
        if empath_disease <= partner_disease or empath_disease <= 0:
            raise AssertionError(f"Empath should still take the majority of the burden: {empath_disease}")
        if not unity_before or not unity_after or int(unity_before.get("stability", 0) or 0) != 80 or int(unity_after.get("stability", 0) or 0) != 65:
            raise AssertionError(f"Unity stability should decay by 15 on assisted transfer: before={unity_before}, after={unity_after}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "unity_before": {"stability": int(unity_before.get("stability", 0) or 0), "condition": unity_before.get("condition")},
            "unity_after": {"stability": int(unity_after.get("stability", 0) or 0), "condition": unity_after.get("condition")},
            "empath_disease": empath_disease,
            "patient_disease": patient_disease,
            "partner_disease": partner_disease,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-unity-burden",
        scenario_metadata=getattr(run_empath_unity_burden_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-redirect-strain",
    aliases=["empath_redirect_strain"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath redirect-strain coverage validates conduit strain, stability loss, and large-redirect shock without failing on environment-specific latency.",
        "tags": ["core", "empath", "unity", "redirect"],
    },
)
def run_empath_redirect_strain_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_REDIRECT_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_REDIRECT_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_REDIRECT_PATIENT")
        partner = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_REDIRECT_PARTNER")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        empath.db.empath_shock = 0
        patient.db.wounds = {"vitality": 40, "bleeding": 40, "fatigue": 0, "poison": 0, "disease": 0}
        partner.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}

        ctx.cmd("link TEST_EMPATH_REDIRECT_PATIENT")
        ctx.cmd("unity TEST_EMPATH_REDIRECT_PARTNER")
        ctx.snapshot("unified")
        ctx.cmd("redirect vitality 20 TEST_EMPATH_REDIRECT_PARTNER")
        ctx.snapshot("redirected_vitality")
        ctx.cmd("redirect bleeding 30 TEST_EMPATH_REDIRECT_PARTNER")
        ctx.snapshot("redirected_bleeding")

        link_after = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        unity_after = empath.get_empath_unity_state()
        if patient.get_empath_wound("vitality") != 20 or partner.get_empath_wound("vitality") != 20:
            raise AssertionError("Vitality redirect should move the wound between the pair.")
        if patient.get_empath_wound("bleeding") != 10 or partner.get_empath_wound("bleeding") != 30:
            raise AssertionError("Bleeding redirect should move the wound between the pair.")
        if empath.get_empath_wound("vitality") != 5:
            raise AssertionError(f"Vitality redirect should inflict conduit strain on the empath: {empath.get_empath_wound('vitality')}")
        if empath.get_empath_wound("bleeding") != 10:
            raise AssertionError(f"Bleeding redirect should inflict conduit bleeding strain on the empath: {empath.get_empath_wound('bleeding')}")
        if int(link_after.get("stability", 0) or 0) != 60:
            raise AssertionError(f"Two redirects should strip 40 link stability total: {link_after}")
        if int(unity_after.get("stability", 0) or 0) != 40:
            raise AssertionError(f"Two redirects should strip 40 unity stability total: {unity_after}")
        if empath.get_empath_shock() != 5:
            raise AssertionError(f"Large redirect should add 5 shock: {empath.get_empath_shock()}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "link_after": {"stability": int(link_after.get("stability", 0) or 0), "condition": link_after.get("condition")},
            "unity_after": {"stability": int(unity_after.get("stability", 0) or 0), "condition": unity_after.get("condition")},
            "empath_vitality": empath.get_empath_wound("vitality"),
            "empath_bleeding": empath.get_empath_wound("bleeding"),
            "shock": empath.get_empath_shock(),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-redirect-strain",
        scenario_metadata=getattr(run_empath_redirect_strain_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-unity-breaks-on-shock",
    aliases=["empath_unity_breaks_on_shock"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath unity-breaks-on-shock coverage validates central cleanup and post-center partial recovery without failing on environment-specific latency.",
        "tags": ["core", "empath", "unity", "shock"],
    },
)
def run_empath_unity_breaks_on_shock_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_UNITY_SHOCK_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNITY_SHOCK_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNITY_SHOCK_PATIENT")
        partner = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNITY_SHOCK_PARTNER")
        foe_one = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNITY_SHOCK_FOE_ONE")
        foe_two = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNITY_SHOCK_FOE_TWO")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        empath.db.empath_shock = 0

        ctx.cmd("link persistent TEST_EMPATH_UNITY_SHOCK_PATIENT")
        ctx.cmd("unity TEST_EMPATH_UNITY_SHOCK_PARTNER")
        ctx.snapshot("unified")

        empath.register_empath_offensive_action(target=foe_one, context="attack", amount=15)
        empath.register_empath_offensive_action(target=foe_one, context="kill", amount=30)
        empath.register_empath_offensive_action(target=foe_two, context="attack", amount=15)
        empath.register_empath_offensive_action(target=foe_two, context="kill", amount=30)
        ctx.snapshot("disconnected")

        if empath.get_empath_shock() < 80:
            raise AssertionError(f"Shock should reach disconnected: {empath.get_empath_shock()}")
        if empath.get_empath_link_state(require_local=False, emit_break_messages=False):
            raise AssertionError("Base link should clear on disconnected shock.")
        if empath.get_empath_unity_state():
            raise AssertionError("Unity should clear on disconnected shock.")

        output_index = len(ctx.output_log)
        ctx.cmd("touch TEST_EMPATH_UNITY_SHOCK_PATIENT")
        touch_fail_output = list(ctx.output_log[output_index:])
        ctx.snapshot("touch_locked")
        if not any("cut off from others" in str(line).lower() for line in touch_fail_output):
            raise AssertionError(f"Touch should be blocked while disconnected: {touch_fail_output}")

        output_index = len(ctx.output_log)
        ctx.cmd("redirect vitality 10 TEST_EMPATH_UNITY_SHOCK_PARTNER")
        redirect_fail_output = list(ctx.output_log[output_index:])
        ctx.snapshot("redirect_locked")
        if not any("cut off from others" in str(line).lower() for line in redirect_fail_output):
            raise AssertionError(f"Redirect should be blocked while disconnected: {redirect_fail_output}")

        empath.db.in_combat = False
        empath.db.target = None
        ctx.cmd("center")
        ctx.snapshot("centered")
        if empath.get_empath_shock() <= 0 or empath.get_empath_shock() >= 80:
            raise AssertionError(f"Center should restore partial access without fully resetting shock: {empath.get_empath_shock()}")

        output_index = len(ctx.output_log)
        ctx.cmd("link persistent TEST_EMPATH_UNITY_SHOCK_PATIENT")
        relink_output = list(ctx.output_log[output_index:])
        ctx.snapshot("relinked")
        relink_state = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if not relink_state or relink_state.get("type") != "persistent":
            raise AssertionError(f"Persistent link should be available again after centering below disconnected: {relink_state}")
        if not any("deeper, longer-held connection" in str(line).lower() for line in relink_output):
            raise AssertionError(f"Persistent relink messaging drifted: {relink_output}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "touch_fail_output": touch_fail_output,
            "redirect_fail_output": redirect_fail_output,
            "relink_output": relink_output,
            "shock_after_center": empath.get_empath_shock(),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-unity-breaks-on-shock",
        scenario_metadata=getattr(run_empath_unity_breaks_on_shock_scenario, "diretest_metadata", {}),
    )


def _diretest_set_progression_rank(character, skill_name, rank):
    if not hasattr(character, "_sync_exp_skill_state") or not hasattr(character, "_persist_exp_skill_state"):
        raise AssertionError("Character is missing EXP skill helpers needed by DireTest progression scenarios.")
    skill = character._sync_exp_skill_state(skill_name, legacy_entry={})
    skill.rank = max(0, int(rank or 0))
    skill.rank_progress = 0.0
    skill.pool = 0.0
    skill.last_trained = 0.0
    character._persist_exp_skill_state(skill)
    store = dict(getattr(character.db, "exp_skill_state", {}) or {})
    store[str(skill_name)] = {
        "rank": int(skill.rank or 0),
        "rank_progress": float(skill.rank_progress or 0.0),
        "pool": float(skill.pool or 0.0),
        "skillset": str(getattr(skill, "skillset", "primary") or "primary"),
        "mindstate": int(getattr(skill, "mindstate", 0) or 0),
        "last_trained": float(skill.last_trained or 0.0),
    }
    character.db.exp_skill_state = store
    return skill


def _diretest_get_progression_snapshot(character, skill_name="empathy"):
    store = dict(getattr(character.db, "exp_skill_state", {}) or {})
    entry = dict(store.get(skill_name, {}) or {})
    return {
        "rank": int(entry.get("rank", 0) or 0),
        "rank_progress": float(entry.get("rank_progress", 0.0) or 0.0),
        "pool": float(entry.get("pool", 0.0) or 0.0),
        "last_trained": float(entry.get("last_trained", 0.0) or 0.0),
    }


@register_scenario(
    "empath-circle-progression",
    aliases=["empath_circle_progression"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath circle progression coverage validates manual-only circling, transient-rank checks, and advance-command delegation without depending on wall-clock timing.",
        "tags": ["core", "empath", "circles"],
    },
)
def run_empath_circle_progression_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_CIRCLE_ROOM")
        room.db.empath_circle_room = True
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_CIRCLE_HEALER")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        empath.db.circle = 1
        empath.db.skills = {"empathy": {"rank": 500, "mindstate": 0}}
        _diretest_set_progression_rank(empath, "empathy", 0)

        blocked_output_index = len(ctx.output_log)
        ctx.cmd("circle advance")
        blocked_output = list(ctx.output_log[blocked_output_index:])
        ctx.snapshot("blocked")

        if empath.get_circle() != 1:
            raise AssertionError(f"Circle should remain unchanged when transient empathy rank is below requirement: {empath.get_circle()}")
        if not any("not yet ready to circle" in str(line).lower() for line in blocked_output):
            raise AssertionError(f"Blocked circle attempt did not emit the expected failure line: {blocked_output}")
        if not any("empathy 0/10" in str(line).lower() for line in blocked_output):
            raise AssertionError(f"Blocked circle attempt did not report transient empathy requirements: {blocked_output}")

        _diretest_set_progression_rank(empath, "empathy", 40)
        if empath.get_circle() != 1:
            raise AssertionError("Empathy rank should not auto-advance circle state.")

        advanced_output_index = len(ctx.output_log)
        ctx.cmd("advance")
        advanced_output = list(ctx.output_log[advanced_output_index:])
        ctx.snapshot("advanced")

        if empath.get_circle() != 2:
            raise AssertionError(f"Advance should move the empath to the next circle only: {empath.get_circle()}")
        if not any("advance to empath circle 2" in str(line).lower() for line in advanced_output):
            raise AssertionError(f"Advance delegation did not emit the expected circling success line: {advanced_output}")

        status_output_index = len(ctx.output_log)
        ctx.cmd("circle")
        status_output = list(ctx.output_log[status_output_index:])
        ctx.snapshot("status")

        if not any("empath circle: 2" in str(line).lower() for line in status_output):
            raise AssertionError(f"Circle status did not report the updated circle: {status_output}")
        if not any("empathy rank: 40" in str(line).lower() for line in status_output):
            raise AssertionError(f"Circle status did not report the transient empathy rank: {status_output}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "blocked_output": blocked_output,
            "advanced_output": advanced_output,
            "status_output": status_output,
            "circle": empath.get_circle(),
            "progression_rank": empath.get_progression_skill_rank("empathy"),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-circle-progression",
        scenario_metadata=getattr(run_empath_circle_progression_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "empath-unlock-separation",
    aliases=["empath_unlock_separation"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Empath unlock separation coverage validates that circle state does not bypass transient empathy unlocks and that locked actions do not train empathy.",
        "tags": ["core", "empath", "circles", "unlocks"],
    },
)
def run_empath_unlock_separation_scenario(args):
    _setup_django()

    def scenario(ctx):
        room = ctx.harness.create_test_room(key="TEST_EMPATH_UNLOCK_ROOM")
        empath = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNLOCK_HEALER")
        patient = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNLOCK_PATIENT")
        partner = ctx.harness.create_test_character(room=room, key="TEST_EMPATH_UNLOCK_PARTNER")

        ctx.character = empath
        ctx.room = room

        empath.set_profession("empath")
        empath.db.circle = 30
        empath.db.skills = {"empathy": {"rank": 500, "mindstate": 0}}
        _diretest_set_progression_rank(empath, "empathy", 0)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}
        patient.db.wounds = {"vitality": 40, "bleeding": 20, "fatigue": 0, "poison": 30, "disease": 20}
        partner.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0}

        ctx.cmd("touch TEST_EMPATH_UNLOCK_PATIENT")
        ctx.snapshot("touched")

        blocked_state_before = _diretest_get_progression_snapshot(empath)
        blocked_output_index = len(ctx.output_log)
        ctx.cmd("take poison")
        blocked_take_output = list(ctx.output_log[blocked_output_index:])
        ctx.snapshot("blocked_take")
        blocked_state_after = _diretest_get_progression_snapshot(empath)

        if patient.get_empath_wound("poison") != 30:
            raise AssertionError("Locked poison transfer should not alter the patient's poison burden.")
        if blocked_state_before != blocked_state_after:
            raise AssertionError(f"Locked poison transfer should not train empathy: before={blocked_state_before}, after={blocked_state_after}")
        if not any("not yet ready to take poison" in str(line).lower() for line in blocked_take_output):
            raise AssertionError(f"Locked poison transfer did not emit the expected unlock message: {blocked_take_output}")

        blocked_link_output_index = len(ctx.output_log)
        ctx.cmd("link persistent TEST_EMPATH_UNLOCK_PATIENT")
        blocked_link_output = list(ctx.output_log[blocked_link_output_index:])
        if not any("not yet ready to hold a persistent empathic link" in str(line).lower() for line in blocked_link_output):
            raise AssertionError(f"High circle should not bypass the persistent-link unlock: {blocked_link_output}")

        blocked_perceive_output_index = len(ctx.output_log)
        ctx.cmd("perceive health")
        blocked_perceive_output = list(ctx.output_log[blocked_perceive_output_index:])
        if not any("not yet ready to read nearby life forces clearly" in str(line).lower() for line in blocked_perceive_output):
            raise AssertionError(f"Perceive health should stay locked below its empathy threshold: {blocked_perceive_output}")

        _diretest_set_progression_rank(empath, "empathy", 39)
        mitigation_before = empath.get_empath_mitigation()
        if mitigation_before != 1.0:
            raise AssertionError(f"Wound reduction should stay disabled below empathy 40: {mitigation_before}")

        _diretest_set_progression_rank(empath, "empathy", 40)
        mitigation_after = empath.get_empath_mitigation()
        if mitigation_after >= 1.0:
            raise AssertionError(f"Wound reduction should activate at empathy 40: {mitigation_after}")

        unlocked_state_before = _diretest_get_progression_snapshot(empath)
        unlocked_take_output_index = len(ctx.output_log)
        ctx.cmd("take poison")
        unlocked_take_output = list(ctx.output_log[unlocked_take_output_index:])
        ctx.snapshot("unlocked_take")
        unlocked_state_after = _diretest_get_progression_snapshot(empath)

        if patient.get_empath_wound("poison") >= 30:
            raise AssertionError("Unlocked poison transfer should reduce the patient's poison burden.")
        if unlocked_state_after["last_trained"] <= unlocked_state_before["last_trained"]:
            raise AssertionError(f"Unlocked poison transfer should train empathy: before={unlocked_state_before}, after={unlocked_state_after}")
        if not any("draw the injury into yourself" in str(line).lower() or "lessen the burden" in str(line).lower() for line in unlocked_take_output):
            raise AssertionError(f"Unlocked poison transfer did not emit the expected transfer messaging: {unlocked_take_output}")

        persistent_output_index = len(ctx.output_log)
        ctx.cmd("link persistent TEST_EMPATH_UNLOCK_PATIENT")
        persistent_output = list(ctx.output_log[persistent_output_index:])
        persistent_state = empath.get_empath_link_state(require_local=True, emit_break_messages=False)
        if str(persistent_state.get("type") or "") != "persistent":
            raise AssertionError(f"Persistent link should unlock once empathy threshold is met: {persistent_state}")

        ctx.cmd("link TEST_EMPATH_UNLOCK_PATIENT")
        unity_output_index = len(ctx.output_log)
        ctx.cmd("unity TEST_EMPATH_UNLOCK_PARTNER")
        unity_output = list(ctx.output_log[unity_output_index:])
        if not empath.get_empath_unity_state():
            raise AssertionError(f"Unity should unlock once empathy threshold is met: {unity_output}")

        channel_output_index = len(ctx.output_log)
        ctx.cmd("channel poison")
        channel_output = list(ctx.output_log[channel_output_index:])
        if not empath.get_state("empath_channel"):
            raise AssertionError(f"Channel should unlock once empathy threshold is met: {channel_output}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_labels": ctx.get_snapshot_labels(),
            "blocked_take_output": blocked_take_output,
            "blocked_link_output": blocked_link_output,
            "blocked_perceive_output": blocked_perceive_output,
            "unlocked_take_output": unlocked_take_output,
            "persistent_output": persistent_output,
            "unity_output": unity_output,
            "channel_output": channel_output,
            "mitigation_before": mitigation_before,
            "mitigation_after": mitigation_after,
            "blocked_state_before": blocked_state_before,
            "blocked_state_after": blocked_state_after,
            "unlocked_state_before": unlocked_state_before,
            "unlocked_state_after": unlocked_state_after,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="empath-unlock-separation",
        scenario_metadata=getattr(run_empath_unlock_separation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "combat-basic",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural combat sanity validation should report lag without failing on environment-specific latency.",
    },
)
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

        if not engaged_diff["combat_changes"]["target_assigned"]:
            raise AssertionError(f"Combat engagement did not assign a target: {engaged_diff}")
        if not engaged_diff["combat_changes"]["entered_combat"]:
            raise AssertionError(f"Combat engagement did not enter combat state: {engaged_diff}")
        if engaged_diff["combat_changes"]["target_after"] != "TEST_COMBAT_DEFENDER":
            raise AssertionError(f"Combat engagement targeted the wrong actor: {engaged_diff}")

        if damaged_diff["combat_changes"]["target_hp_delta"] is None or damaged_diff["combat_changes"]["target_hp_delta"] >= 0:
            raise AssertionError(f"Combat damage diff did not record target HP loss: {damaged_diff}")
        if not damaged_diff["combat_changes"]["in_combat_after"]:
            raise AssertionError(f"Combat damage snapshot lost combat state unexpectedly: {damaged_diff}")

        if not disengaged_diff["combat_changes"]["target_cleared"]:
            raise AssertionError(f"Combat disengage did not clear the target: {disengaged_diff}")
        if not disengaged_diff["combat_changes"]["exited_combat"]:
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

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="combat-basic",
        scenario_metadata=getattr(run_combat_basic_scenario, "diretest_metadata", {}),
    )


@register_scenario("death-loop")
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
        _run_depart_command(character, "")
        _run_depart_command(character, "confirm")
        ctx.snapshot("departed")
        _run_recover_command(character)
        ctx.snapshot("recovered")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["alive", "dead", "departed", "recovered"]
        if labels != expected_labels:
            raise AssertionError(f"Death-loop snapshot labels drifted: expected {expected_labels}, got {labels}")

        death_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("alive"), ctx.get_snapshot_by_label("dead"))
        depart_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("dead"), ctx.get_snapshot_by_label("departed"))
        recover_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("departed"), ctx.get_snapshot_by_label("recovered"))

        if not death_diff["character_changes"]["died"]:
            raise AssertionError(f"Death diff did not record a dead life-state transition: {death_diff}")
        if death_diff["character_changes"]["coins_delta"] != -37:
            raise AssertionError(f"Death diff did not move carried coins off the character: {death_diff}")
        if death_diff["inventory_changes"]["removed"] != ["TEST_DEATH_TOKEN"]:
            raise AssertionError(f"Death diff did not move carried items off the character: {death_diff}")
        if corpse.key not in death_diff["object_delta_changes"]["created"]:
            raise AssertionError(f"Death diff did not record corpse creation: {death_diff}")

        if not depart_diff["character_changes"]["revived"]:
            raise AssertionError(f"Depart diff did not record revival back to life: {depart_diff}")
        if depart_diff["character_changes"]["coins_delta"] != 0:
            raise AssertionError(f"Depart diff unexpectedly restored grave coins: {depart_diff}")
        if depart_diff["inventory_changes"]["added"]:
            raise AssertionError(f"Depart diff unexpectedly restored grave items: {depart_diff}")
        if corpse.key not in depart_diff["object_delta_changes"]["deleted"]:
            raise AssertionError(f"Depart diff did not record corpse cleanup: {depart_diff}")
        if "grave of TEST_DEATH_CHAR" not in depart_diff["room_changes"]["contents_added"]:
            raise AssertionError(f"Depart diff did not record grave creation: {depart_diff}")

        if recover_diff["character_changes"]["coins_delta"] <= 0:
            raise AssertionError(f"Recover diff did not restore any grave coins: {recover_diff}")
        if recover_diff["inventory_changes"]["added"] != ["TEST_DEATH_TOKEN"]:
            raise AssertionError(f"Recover diff did not restore the grave item: {recover_diff}")

        if character.is_dead():
            raise AssertionError("Death-loop scenario ended with the character still dead.")
        if int(getattr(character.db, "coins", 0) or 0) <= 0:
            raise AssertionError("Death-loop scenario ended without recovered grave coins.")
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

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="death-loop")


@register_scenario(
    "death-depart-basic",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates the simplified dead-only depart confirm flow and corpse cleanup.",
    },
)
def run_death_depart_basic_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object
    from evennia.utils.search import search_object

    room_name, room = _create_temp_room("diretest_death_depart_basic")
    safe_name, safe_room = _create_temp_room("diretest_death_depart_safe")
    character = None
    observer = None
    originals = {}

    try:
        character = create_object("typeclasses.characters.Character", key="TEST_DEPART_BASIC", location=room, home=safe_room)
        observer = create_object("typeclasses.characters.Character", key="TEST_DEPART_OBSERVER", location=room, home=room)
        for obj in (character, observer):
            obj.ensure_core_defaults()
        character.set_favor(3)
        character.set_hp(0)
        corpse = character.get_death_corpse()
        if not corpse:
            raise AssertionError("Depart basic scenario did not create a corpse.")

        captured, originals = _capture_object_messages(character, observer)
        _run_depart_command(character, "")
        prompt_text = "\n".join(captured.get(character) or [])
        if "Are you sure you wish to depart? This will forfeit your body." not in prompt_text:
            raise AssertionError(f"Depart basic scenario missed the confirmation prompt: {prompt_text}")
        captured[character].clear()
        captured[observer].clear()
        _run_depart_command(character, "confirm")

        player_text = "\n".join(captured.get(character) or [])
        observer_text = "\n".join(captured.get(observer) or [])
        if character.is_dead():
            raise AssertionError("Depart basic scenario left the character dead.")
        if getattr(character.location, "id", None) != getattr(safe_room, "id", None):
            raise AssertionError("Depart basic scenario did not move the character to the safe location.")
        if search_object(f"#{int(corpse.id or 0)}"):
            raise AssertionError("Depart basic scenario did not remove the corpse.")
        if "You release your hold on the body and move on." not in player_text:
            raise AssertionError(f"Depart basic scenario missed the depart completion message: {player_text}")
        if "The body grows still as whatever remained departs." not in observer_text:
            raise AssertionError(f"Depart basic scenario missed the room departure message: {observer_text}")

        print(json.dumps({
            "scenario": "death-depart-basic",
            "corpse_removed": True,
            "moved_to_safe_room": True,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        for obj in (character, observer):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "death-revive-blocked-after-depart",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that depart removes the revive target and prevents a later revive attempt from succeeding.",
    },
)
def run_death_revive_blocked_after_depart_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_revive_blocked")
    safe_name, safe_room = _create_temp_room("diretest_death_revive_safe")
    cleric = None
    target = None

    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_DEPART_CLERIC", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_DEPART_TARGET", location=room, home=safe_room)
        for obj in (cleric, target):
            obj.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(3)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        _run_depart_command(target, "")
        _run_depart_command(target, "confirm")
        ok, message = cleric.start_cleric_revive(corpse)
        if ok:
            raise AssertionError("Revive-blocked-after-depart scenario unexpectedly allowed a revive attempt.")

        print(json.dumps({
            "scenario": "death-revive-blocked-after-depart",
            "message": str(message or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "death-sting-applied",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that a completed depart leaves a minimum counted Death's Sting consequence.",
    },
)
def run_death_sting_applied_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_sting_applied")
    safe_name, safe_room = _create_temp_room("diretest_death_sting_safe")
    character = None

    try:
        character = create_object("typeclasses.characters.Character", key="TEST_DEATH_STING", location=room, home=safe_room)
        character.ensure_core_defaults()
        character.set_favor(2)
        character.set_hp(0)
        _run_depart_command(character, "")
        _run_depart_command(character, "confirm")
        if int(getattr(character.db, "death_sting", 0) or 0) < 1:
            raise AssertionError("Death-sting-applied scenario did not leave a minimum sting count.")

        print(json.dumps({
            "scenario": "death-sting-applied",
            "recovery_label": str(getattr(character.db, "death_sting_recovery_label", "") or ""),
            "sting": int(getattr(character.db, "death_sting", 0) or 0),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "death-sting-recovery-severity",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Compares low and high Death's Sting counts to validate harsher recovery effects at higher severity.",
    },
)
def run_death_sting_recovery_severity_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_sting_recovery")
    safe_name, safe_room = _create_temp_room("diretest_death_sting_recovery_safe")
    light = None
    severe = None

    try:
        light = create_object("typeclasses.characters.Character", key="TEST_DEATH_STING_LIGHT", location=room, home=safe_room)
        severe = create_object("typeclasses.characters.Character", key="TEST_DEATH_STING_SEVERE", location=room, home=safe_room)
        for obj in (light, severe):
            obj.ensure_core_defaults()
            obj.set_favor(2)

        light.set_hp(0)
        _run_depart_command(light, "")
        _run_depart_command(light, "confirm")

        severe.db.death_sting = 4
        severe.set_hp(0)
        _run_depart_command(severe, "")
        _run_depart_command(severe, "confirm")

        light_label = str(getattr(light.db, "death_sting_recovery_label", "") or "")
        severe_label = str(getattr(severe.db, "death_sting_recovery_label", "") or "")
        light_cap = float(getattr(light.db, "death_sting_hp_cap_ratio", 1.0) or 1.0)
        severe_cap = float(getattr(severe.db, "death_sting_hp_cap_ratio", 1.0) or 1.0)
        if light_label != "light":
            raise AssertionError(f"Death-sting-recovery-severity scenario produced the wrong light label: {light_label}")
        if severe_label != "severe":
            raise AssertionError(f"Death-sting-recovery-severity scenario produced the wrong severe label: {severe_label}")
        if severe_cap >= light_cap:
            raise AssertionError(f"Death-sting-recovery-severity scenario did not produce a harsher HP cap for severe sting: light={light_cap}, severe={severe_cap}")

        print(json.dumps({
            "scenario": "death-sting-recovery-severity",
            "light_cap": light_cap,
            "severe_cap": severe_cap,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (light, severe):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "death-favor-softens-sting",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Compares zero favor and anchored favor departures to validate favor-softened penalties without removing consequence.",
    },
)
def run_death_favor_softens_sting_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_favor_softens")
    safe_name, safe_room = _create_temp_room("diretest_death_favor_safe")
    low = None
    high = None

    try:
        low = create_object("typeclasses.characters.Character", key="TEST_DEATH_FAVOR_LOW", location=room, home=safe_room)
        high = create_object("typeclasses.characters.Character", key="TEST_DEATH_FAVOR_HIGH", location=room, home=safe_room)
        for obj in (low, high):
            obj.ensure_core_defaults()
        low.set_favor(0)
        high.set_favor(4)

        low.set_hp(0)
        _run_depart_command(low, "")
        _run_depart_command(low, "confirm")
        high.set_hp(0)
        _run_depart_command(high, "")
        _run_depart_command(high, "confirm")

        low_severity = float(getattr(low.db, "death_sting_severity", 0.0) or 0.0)
        high_severity = float(getattr(high.db, "death_sting_severity", 0.0) or 0.0)
        if high_severity >= low_severity:
            raise AssertionError(f"Death-favor-softens-sting scenario did not reduce the sting with favor: low={low_severity}, high={high_severity}")
        if high_severity <= 0.0:
            raise AssertionError("Death-favor-softens-sting scenario removed the death penalty entirely.")

        print(json.dumps({
            "scenario": "death-favor-softens-sting",
            "high_favor_severity": high_severity,
            "low_favor_severity": low_severity,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (low, high):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "death-no-double-sting",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that a failed revive attempt followed by depart only counts one death penalty for that death cycle.",
    },
)
def run_death_no_double_sting_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_no_double_sting")
    safe_name, safe_room = _create_temp_room("diretest_death_no_double_safe")
    cleric = None
    target = None

    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_NO_DOUBLE_CLERIC", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_NO_DOUBLE_TARGET", location=room, home=safe_room)
        for obj in (cleric, target):
            obj.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(0)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        baseline_sting = int(getattr(target.db, "death_sting", 0) or 0)
        ok, message = cleric.start_cleric_revive(corpse)
        if ok:
            raise AssertionError("Death-no-double-sting scenario unexpectedly allowed revive without favor.")
        _run_depart_command(target, "")
        _run_depart_command(target, "confirm")
        if int(getattr(target.db, "death_sting", 0) or 0) != baseline_sting:
            raise AssertionError(f"Death-no-double-sting scenario applied the penalty twice: baseline={baseline_sting}, after={getattr(target.db, 'death_sting', 0)}")

        print(json.dumps({
            "scenario": "death-no-double-sting",
            "message": str(message or ""),
            "sting": int(getattr(target.db, "death_sting", 0) or 0),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "death-revive-interrupted-then-depart",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses a fake pending revive to confirm depart is blocked mid-cast but succeeds once the revive breaks.",
    },
)
def run_death_revive_interrupted_then_depart_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_revive_interrupt")
    safe_name, safe_room = _create_temp_room("diretest_death_revive_interrupt_safe")
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        room.db.is_shrine = True
        cleric = create_object("typeclasses.characters.Character", key="TEST_INTERRUPT_DEPART_CLERIC", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_INTERRUPT_DEPART_TARGET", location=room, home=safe_room)
        for obj in (cleric, target):
            obj.ensure_core_defaults()
        cleric.set_profession("cleric")
        cleric.set_devotion(100)
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))

        ok, message = cleric.start_cleric_revive(corpse)
        if not ok:
            raise AssertionError(message)
        departed, depart_message = target.depart_self(mode="standard")
        if departed:
            raise AssertionError("Death-revive-interrupted-then-depart scenario allowed depart during an active revive.")
        cleric.cancel_pending_cleric_ritual(message=None, emit_message=False)
        departed, depart_message = target.depart_self(mode="standard")
        if not departed:
            raise AssertionError(f"Death-revive-interrupted-then-depart scenario failed after the interrupt: {depart_message}")

        print(json.dumps({
            "scenario": "death-revive-interrupted-then-depart",
            "blocked_message": str(message or ""),
            "depart_message": str(depart_message or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "death-depart-corpse-missing",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that depart still succeeds cleanly when the corpse has already been removed.",
    },
)
def run_death_depart_corpse_missing_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_corpse_missing")
    safe_name, safe_room = _create_temp_room("diretest_death_corpse_missing_safe")
    character = None

    try:
        character = create_object("typeclasses.characters.Character", key="TEST_DEPART_NO_CORPSE", location=room, home=safe_room)
        character.ensure_core_defaults()
        character.set_favor(2)
        character.set_hp(0)
        corpse = character.get_death_corpse()
        if corpse:
            corpse.db.is_corpse = False
            character.clear_death_corpse_link()
        _run_depart_command(character, "")
        _run_depart_command(character, "confirm")
        if character.is_dead():
            raise AssertionError("Death-depart-corpse-missing scenario left the character dead.")

        print(json.dumps({
            "scenario": "death-depart-corpse-missing",
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "death-reconnect-dead-state",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that reconnecting while dead keeps the dead state and surfaces the revive-or-depart prompt.",
    },
)
def run_death_reconnect_dead_state_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_reconnect")
    character = None
    originals = {}

    try:
        character = create_object("typeclasses.characters.Character", key="TEST_DEATH_RECONNECT", location=room, home=room)
        character.ensure_core_defaults()
        character.set_favor(2)
        character.set_hp(0)
        captured, originals = _capture_object_messages(character)
        character.at_post_puppet()
        output = "\n".join(captured.get(character) or [])
        if not character.is_dead():
            raise AssertionError("Death-reconnect-dead-state scenario unexpectedly revived the character on reconnect.")
        if "You are dead. You must wait for resurrection or type DEPART to let go." not in output:
            raise AssertionError(f"Death-reconnect-dead-state scenario missed the reconnect dead-state reminder: {output}")

        print(json.dumps({
            "scenario": "death-reconnect-dead-state",
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario(
    "death-depart-final-integration",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Runs the simple failure path of death, failed revive, and confirmed depart to validate the finished branch end-to-end.",
    },
)
def run_death_depart_final_integration_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_death_final")
    safe_name, safe_room = _create_temp_room("diretest_death_final_safe")
    cleric = None
    target = None

    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_DEATH_FINAL_CLERIC", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_DEATH_FINAL_TARGET", location=room, home=safe_room)
        for obj in (cleric, target):
            obj.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(0)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        ok, message = cleric.start_cleric_revive(corpse)
        if ok:
            raise AssertionError("Death-depart-final-integration scenario unexpectedly allowed revive without favor.")
        _run_depart_command(target, "")
        _run_depart_command(target, "confirm")
        if target.is_dead():
            raise AssertionError("Death-depart-final-integration scenario left the target dead.")
        if target.get_death_corpse() is not None:
            raise AssertionError("Death-depart-final-integration scenario left a corpse link behind.")
        if int(getattr(target.db, "death_sting", 0) or 0) < 1:
            raise AssertionError("Death-depart-final-integration scenario did not apply the death sting.")

        print(json.dumps({
            "scenario": "death-depart-final-integration",
            "revive_message": str(message or ""),
            "sting": int(getattr(target.db, "death_sting", 0) or 0),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


def _build_fake_delay_queue():
    scheduled = []

    class FakeDelayedTask:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    def fake_delay(seconds, callback, *cb_args, **cb_kwargs):
        task = FakeDelayedTask()
        scheduled.append({"seconds": float(seconds), "callback": callback, "args": cb_args, "kwargs": cb_kwargs, "task": task})
        return task

    return scheduled, fake_delay


def _run_fake_delay_queue(scheduled):
    while scheduled:
        event = scheduled.pop(0)
        event["callback"](*event["args"], **event["kwargs"])


def _run_cleric_ritual_chain(cleric, corpse, scheduled, stages):
    completed = []
    for stage in stages:
        ok, message = cleric.start_cleric_corpse_ritual(corpse, stage)
        if not ok:
            raise AssertionError(f"Cleric ritual stage '{stage}' failed unexpectedly: {message}")
        _run_fake_delay_queue(scheduled)
        completed.append(stage)
    return completed


def _run_depart_command(character, args=""):
    from commands.cmd_depart import CmdDepart

    cmd = CmdDepart()
    cmd.caller = character
    cmd.args = str(args or "")
    cmd.cmdstring = "depart"
    cmd.func()


def _run_pray_command(character, args=""):
    from commands.cmd_pray import CmdPray

    cmd = CmdPray()
    cmd.caller = character
    cmd.args = str(args or "")
    cmd.cmdstring = "pray"
    cmd.func()


def _run_recover_command(character, args=""):
    from commands.cmd_recover import CmdRecover

    cmd = CmdRecover()
    cmd.caller = character
    cmd.args = str(args or "")
    cmd.cmdstring = "recover"
    cmd.func()


@register_scenario(
    "cleric-revive-loop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate the revive flow deterministically.",
    },
)
def run_cleric_revive_loop_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object
    from evennia.utils.search import search_object

    room_name, room = _create_temp_room("diretest_cleric_revive")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        if not corpse:
            raise AssertionError("Revive loop scenario did not create a corpse.")
        if int(getattr(corpse.db, "favor_snapshot", 0) or 0) < 1:
            raise AssertionError("Revive loop scenario expected a favor snapshot on the corpse.")
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))
        if str(getattr(corpse.db, "ritual_state", "") or "") != "bound":
            raise AssertionError("Revive loop scenario did not complete the full ritual chain before revive.")
        ok, message = cleric.start_cleric_revive(corpse)
        if not ok:
            raise AssertionError(message)
        if not scheduled:
            raise AssertionError("Revive loop scenario did not schedule a delayed revive.")
        _run_fake_delay_queue(scheduled)
        if target.is_dead():
            raise AssertionError("Revive loop scenario left the target dead.")
        if int(getattr(target.db, "hp", 0) or 0) != 60:
            raise AssertionError("Revive loop scenario did not restore the target with the best-quality HP result.")
        if str(getattr(target.db, "recovery_state", "") or "") != "revived_best":
            raise AssertionError("Revive loop scenario did not mark the best-quality recovery state.")
        if int(getattr(cleric.db, "devotion_current", 0) or 0) != 35:
            raise AssertionError("Revive loop scenario did not consume the expected devotion across the full rite.")
        if int(getattr(target.db, "favor_current", 0) or 0) != 1:
            raise AssertionError("Revive loop scenario did not spend exactly one favor on a successful return.")
        if search_object(f"#{int(getattr(corpse, 'id', 0) or 0)}"):
            raise AssertionError("Revive loop scenario did not consume the corpse.")
        print(json.dumps({
            "scenario": "cleric-revive-loop",
            "devotion_after": int(getattr(cleric.db, "devotion_current", 0) or 0),
            "favor_after": int(getattr(target.db, "favor_current", 0) or 0),
            "hp_after": int(getattr(target.db, "hp", 0) or 0),
            "recovery_state": str(getattr(target.db, "recovery_state", "") or ""),
            "ritual_state": "bound",
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-revive-interrupt",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate revive interruption deterministically.",
    },
)
def run_cleric_revive_interrupt_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_interrupt")
    other_room_name, other_room = _create_temp_room("diretest_cleric_interrupt_other")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_INTERRUPTER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_INTERRUPT_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))
        ok, message = cleric.start_cleric_revive(corpse)
        if not ok:
            raise AssertionError(message)
        cleric.move_to(other_room, quiet=True)
        if not scheduled:
            raise AssertionError("Revive interrupt scenario did not schedule a delayed revive.")
        _run_fake_delay_queue(scheduled)
        if not target.is_dead():
            raise AssertionError("Revive interrupt scenario revived the target after interruption.")
        print(json.dumps({
            "scenario": "cleric-revive-interrupt",
            "cleric_room": getattr(getattr(cleric, "location", None), "key", None),
            "ritual_state": str(getattr(corpse.db, "ritual_state", "") or ""),
            "target_dead": bool(target.is_dead()),
            "corpse_present": bool(target.get_death_corpse()),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(other_room_name)


@register_scenario(
    "cleric-devotion-gating",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that ritual startup fails cleanly when devotion is empty.",
    },
)
def run_cleric_devotion_gating_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_devotion_gating")
    room.db.is_shrine = True
    cleric = None
    target = None
    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_DEVOTION_GATE", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_DEVOTION_GATE_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        cleric.set_devotion(0)
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        ok, message = cleric.prepare_corpse(corpse)
        if ok:
            raise AssertionError("Devotion-gating scenario unexpectedly allowed ritual startup at zero devotion.")
        expected = "You do not have the devotion required to continue the rite."
        if str(message or "") != expected:
            raise AssertionError(f"Devotion-gating scenario returned the wrong failure message: {message}")
        print(json.dumps({
            "scenario": "cleric-devotion-gating",
            "devotion": int(getattr(cleric.db, "devotion_current", 0) or 0),
            "favor_snapshot": int(getattr(corpse.db, "favor_snapshot", 0) or 0),
            "message": str(message or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-devotion-consumption",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate devotion is charged at ritual start.",
    },
)
def run_cleric_devotion_consumption_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_devotion_consumption")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_DEVOTION_SPEND", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_DEVOTION_SPEND_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        cleric.set_devotion(100)
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        ok, message = cleric.prepare_corpse(corpse)
        if not ok:
            raise AssertionError(message)
        if int(getattr(cleric.db, "devotion_current", 0) or 0) != 95:
            raise AssertionError("Devotion-consumption scenario did not charge prepare at ritual start.")
        _run_fake_delay_queue(scheduled)
        ok, message = cleric.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        if int(getattr(cleric.db, "devotion_current", 0) or 0) != 85:
            raise AssertionError("Devotion-consumption scenario did not charge stabilize at ritual start.")
        print(json.dumps({
            "scenario": "cleric-devotion-consumption",
            "after_prepare": 95,
            "after_stabilize": int(getattr(cleric.db, "devotion_current", 0) or 0),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-interruption-consequences",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate interruption regression and failure tracking.",
    },
)
def run_cleric_ritual_interruption_consequences_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_interrupt_consequence")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_INTERRUPT_CONSEQUENCE", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_INTERRUPT_CONSEQUENCE_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare",))
        ok, message = cleric.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        cleric.set_hp(int(getattr(cleric.db, "hp", 100) or 100) - 1)
        _run_fake_delay_queue(scheduled)
        if str(getattr(corpse.db, "ritual_state", "") or "") != "prepared":
            raise AssertionError("Interruption-consequences scenario did not regress stabilize back to prepared.")
        if int(getattr(corpse.db, "ritual_failures", 0) or 0) != 1:
            raise AssertionError("Interruption-consequences scenario did not increment ritual_failures.")
        print(json.dumps({
            "scenario": "cleric-ritual-interruption-consequences",
            "ritual_failures": int(getattr(corpse.db, "ritual_failures", 0) or 0),
            "ritual_quality": int(getattr(corpse.db, "ritual_quality", 0) or 0),
            "ritual_state": str(getattr(corpse.db, "ritual_state", "") or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-multiple-failures",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses repeated interruptions to validate escalation, memory instability, and revive lockout.",
    },
)
def run_cleric_ritual_multiple_failures_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_multiple_failures")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MULTI_FAIL", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MULTI_FAIL_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare",))
        for attempt in range(3):
            ok, message = cleric.start_cleric_corpse_ritual(corpse, "stabilize")
            if not ok:
                raise AssertionError(message)
            cleric.set_hp(int(getattr(cleric.db, "hp", 100) or 100) - 1)
            _run_fake_delay_queue(scheduled)
        if int(getattr(corpse.db, "ritual_failures", 0) or 0) != 3:
            raise AssertionError("Multiple-failures scenario did not accumulate three ritual failures.")
        if bool(getattr(corpse.db, "memory_stable", False)):
            raise AssertionError("Multiple-failures scenario did not break memory stability after repeated failures.")
        if bool(getattr(corpse.db, "is_valid_for_revive", True)):
            raise AssertionError("Multiple-failures scenario did not lock the corpse out after three failures.")
        print(json.dumps({
            "scenario": "cleric-ritual-multiple-failures",
            "memory_stable": bool(getattr(corpse.db, "memory_stable", False)),
            "ritual_failures": int(getattr(corpse.db, "ritual_failures", 0) or 0),
            "revive_valid": bool(getattr(corpse.db, "is_valid_for_revive", True)),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-quality-scaling",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses paired deterministic revives to validate best-quality and degraded-quality outcomes.",
    },
)
def run_cleric_ritual_quality_scaling_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_quality_scaling")
    room.db.is_shrine = True
    perfect_cleric = None
    partial_cleric = None
    perfect_target = None
    partial_target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        perfect_cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_QUALITY_PERFECT", location=room, home=room)
        perfect_target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_QUALITY_PERFECT_TARGET", location=room, home=room)
        partial_cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_QUALITY_PARTIAL", location=room, home=room)
        partial_target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_QUALITY_PARTIAL_TARGET", location=room, home=room)
        for obj in (perfect_cleric, perfect_target, partial_cleric, partial_target):
            obj.ensure_core_defaults()
        perfect_cleric.set_profession("cleric")
        partial_cleric.set_profession("cleric")
        perfect_target.set_favor(2)
        partial_target.set_favor(2)
        perfect_target.set_hp(0)
        partial_target.set_hp(0)

        perfect_corpse = perfect_target.get_death_corpse()
        partial_corpse = partial_target.get_death_corpse()

        _run_cleric_ritual_chain(perfect_cleric, perfect_corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))
        ok, message = perfect_cleric.start_cleric_revive(perfect_corpse)
        if not ok:
            raise AssertionError(message)
        _run_fake_delay_queue(scheduled)

        _run_cleric_ritual_chain(partial_cleric, partial_corpse, scheduled, ("prepare",))
        ok, message = partial_cleric.start_cleric_corpse_ritual(partial_corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        partial_cleric.set_hp(int(getattr(partial_cleric.db, "hp", 100) or 100) - 1)
        _run_fake_delay_queue(scheduled)
        _run_cleric_ritual_chain(partial_cleric, partial_corpse, scheduled, ("stabilize", "restore", "bind"))
        ok, message = partial_cleric.start_cleric_revive(partial_corpse)
        if not ok:
            raise AssertionError(message)
        _run_fake_delay_queue(scheduled)

        perfect_hp = int(getattr(perfect_target.db, "hp", 0) or 0)
        partial_hp = int(getattr(partial_target.db, "hp", 0) or 0)
        perfect_state = str(getattr(perfect_target.db, "recovery_state", "") or "")
        partial_state = str(getattr(partial_target.db, "recovery_state", "") or "")
        if perfect_state != "revived_best":
            raise AssertionError("Quality-scaling scenario did not produce the best outcome for the perfect chain.")
        if partial_state == perfect_state:
            raise AssertionError("Quality-scaling scenario did not worsen the partial-chain recovery state.")
        if partial_hp >= perfect_hp:
            raise AssertionError("Quality-scaling scenario did not worsen the partial-chain HP result.")
        print(json.dumps({
            "scenario": "cleric-ritual-quality-scaling",
            "partial_hp": partial_hp,
            "partial_state": partial_state,
            "perfect_hp": perfect_hp,
            "perfect_state": perfect_state,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (perfect_cleric, perfect_target, partial_cleric, partial_target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "corpse-wound-pipeline",
    aliases=["corpse_wound_pipeline"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses direct corpse prep and fake delayed callbacks to validate corpse-authoritative wound inheritance through resurrection.",
        "tags": ["death", "empath", "cleric", "resurrection"],
    },
)
def run_corpse_wound_pipeline_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_corpse_wound_pipeline")
    room.db.is_shrine = True
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()
    cleric = None
    empath = None
    prepared_target = None
    raw_target = None

    def _seed_wounds(target):
        target.ensure_core_defaults()
        target.db.wounds = target.normalize_empath_wounds(
            {
                "vitality": 75,
                "bleeding": 45,
                "poison": 0,
                "disease": 0,
                "fatigue": 0,
                "trauma": 0,
            }
        )
        injuries = dict(getattr(target.db, "injuries", {}) or {})
        injuries["left_arm"] = dict(injuries.get("left_arm", {}) or {})
        injuries["left_arm"]["external"] = 10
        injuries["left_arm"]["internal"] = 0
        injuries["left_arm"]["bruise"] = 0
        injuries["left_arm"]["bleed"] = 5
        injuries["chest"] = dict(injuries.get("chest", {}) or {})
        injuries["chest"]["external"] = 18
        injuries["chest"]["internal"] = 55
        injuries["chest"]["bruise"] = 0
        injuries["chest"]["bleed"] = 5
        target.db.injuries = injuries
        target.sync_resources_from_empath_wounds()
        target.update_bleed_state()

    def _run_pending_revive_without_cleanup():
        if not scheduled:
            raise AssertionError("Corpse-wound pipeline scenario expected a queued revive callback.")
        event = scheduled.pop(0)
        nested_delay = character_module.delay

        def _suppress_cleanup(_seconds, _callback, *args, **kwargs):
            return None

        character_module.delay = _suppress_cleanup
        try:
            event["callback"](*event["args"], **event["kwargs"])
        finally:
            character_module.delay = nested_delay

    try:
        character_module.delay = fake_delay

        cleric = create_object("typeclasses.characters.Character", key="TEST_CORPSE_PIPELINE_CLERIC", location=room, home=room)
        empath = create_object("typeclasses.characters.Character", key="TEST_CORPSE_PIPELINE_EMPATH", location=room, home=room)
        prepared_target = create_object("typeclasses.characters.Character", key="TEST_CORPSE_PIPELINE_PREPPED", location=room, home=room)
        raw_target = create_object("typeclasses.characters.Character", key="TEST_CORPSE_PIPELINE_RAW", location=room, home=room)

        for obj in (cleric, empath, prepared_target, raw_target):
            obj.ensure_core_defaults()

        cleric.set_profession("cleric")
        cleric.set_devotion(500)
        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)

        for target in (prepared_target, raw_target):
            target.set_favor(5)
            _seed_wounds(target)
            target.set_hp(0)

        prepared_corpse = prepared_target.get_death_corpse()
        raw_corpse = raw_target.get_death_corpse()
        if not prepared_corpse or not raw_corpse:
            raise AssertionError("Corpse-wound pipeline scenario failed to create death corpses.")

        prepared_snapshot = prepared_corpse.get_corpse_wounds()
        if int(prepared_snapshot.get("injuries", {}).get("chest", {}).get("internal", 0) or 0) != 55:
            raise AssertionError(f"Corpse did not inherit the chest internal wound state: {prepared_snapshot}")
        if int(prepared_snapshot.get("injuries", {}).get("left_arm", {}).get("bleed", 0) or 0) != 5:
            raise AssertionError(f"Corpse did not inherit the arm bleed state: {prepared_snapshot}")

        ok, cleric_assess_lines = cleric.assess_cleric_corpse(prepared_corpse)
        if not ok:
            raise AssertionError(cleric_assess_lines)
        if not any("may not survive the rite" in str(line).lower() for line in cleric_assess_lines):
            raise AssertionError(f"Cleric assess did not warn about lethal corpse state: {cleric_assess_lines}")

        ok, empath_assess_lines = empath.assess_empath_corpse(prepared_corpse)
        if not ok:
            raise AssertionError(empath_assess_lines)
        if not any("Bleeding: 45%" in str(line) for line in empath_assess_lines):
            raise AssertionError(f"Empath corpse assess did not report precise wound values: {empath_assess_lines}")

        ok, touch_message = empath.touch_empath_target(prepared_corpse)
        if not ok:
            raise AssertionError(touch_message)

        ok, bleed_message = empath.take_empath_wound("bleeding", selector="arm")
        if not ok:
            raise AssertionError(bleed_message)
        after_bleed = prepared_corpse.get_corpse_wounds()
        if int(after_bleed.get("injuries", {}).get("left_arm", {}).get("bleed", 0) or 0) != 0:
            raise AssertionError(f"Empath corpse transfer did not clear the arm bleed burden: {after_bleed}")
        if int(after_bleed.get("injuries", {}).get("chest", {}).get("bleed", 0) or 0) != 5:
            raise AssertionError(f"Empath corpse transfer altered the wrong bleed location: {after_bleed}")

        ok, vitality_message = empath.take_empath_wound("vitality", selector="chest")
        if not ok:
            raise AssertionError(vitality_message)
        after_prep = prepared_corpse.get_corpse_wounds()
        if int(after_prep.get("injuries", {}).get("chest", {}).get("internal", 0) or 0) >= 40:
            raise AssertionError(f"Empath corpse transfer did not reduce lethal internal injury load: {after_prep}")
        if not cleric.is_corpse_revive_survivable(prepared_corpse):
            raise AssertionError(f"Prepared corpse should be survivable before the rite completes: {after_prep}")
        if cleric.is_corpse_revive_survivable(raw_corpse):
            raise AssertionError("Untreated corpse unexpectedly passed the survivability check.")

        _run_cleric_ritual_chain(cleric, prepared_corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))
        ok, revive_message = cleric.start_cleric_revive(prepared_corpse)
        if not ok:
            raise AssertionError(revive_message)
        _run_pending_revive_without_cleanup()

        cleric.set_devotion(500)
        _run_cleric_ritual_chain(cleric, raw_corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))
        ok, raw_revive_message = cleric.start_cleric_revive(raw_corpse)
        if not ok:
            raise AssertionError(raw_revive_message)
        _run_pending_revive_without_cleanup()

        prepared_internal = int(prepared_target.db.injuries["chest"].get("internal", 0) or 0)
        raw_internal = int(raw_target.db.injuries["chest"].get("internal", 0) or 0)
        prepared_arm_bleed = int(prepared_target.db.injuries["left_arm"].get("bleed", 0) or 0)
        raw_arm_bleed = int(raw_target.db.injuries["left_arm"].get("bleed", 0) or 0)
        if prepared_internal >= raw_internal:
            raise AssertionError(f"Revive did not inherit the prepared corpse's reduced chest burden: prepared={prepared_internal}, raw={raw_internal}")
        if prepared_arm_bleed >= raw_arm_bleed:
            raise AssertionError(f"Revive did not inherit the prepared corpse's reduced arm bleed: prepared={prepared_arm_bleed}, raw={raw_arm_bleed}")

        for _ in range(8):
            if not prepared_target.is_dead():
                prepared_target.process_bleed()
            if not raw_target.is_dead():
                raw_target.process_bleed()

        if prepared_target.is_dead():
            raise AssertionError("Prepared corpse path still redied during the post-res bleed window.")
        if not raw_target.is_dead():
            raise AssertionError("Untreated corpse path should still fail the post-res bleed window.")

        print(json.dumps({
            "scenario": "corpse-wound-pipeline",
            "prepared_internal": prepared_internal,
            "raw_internal": raw_internal,
            "prepared_arm_bleed": prepared_arm_bleed,
            "raw_arm_bleed": raw_arm_bleed,
            "prepared_post_bleed_dead": prepared_target.is_dead(),
            "raw_post_bleed_dead": raw_target.is_dead(),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, empath, prepared_target, raw_target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


def _seed_resurrection_contract_wounds(target, vitality, bleeding, chest_internal, chest_bleed, chest_external=18, arm_bleed=0):
    target.ensure_core_defaults()
    target.db.wounds = target.normalize_empath_wounds(
        {
            "vitality": vitality,
            "bleeding": bleeding,
            "poison": 0,
            "disease": 0,
            "fatigue": 0,
            "trauma": 0,
        }
    )
    injuries = dict(getattr(target.db, "injuries", {}) or {})
    injuries["left_arm"] = dict(injuries.get("left_arm", {}) or {})
    injuries["left_arm"]["external"] = 10
    injuries["left_arm"]["internal"] = 0
    injuries["left_arm"]["bruise"] = 0
    injuries["left_arm"]["bleed"] = arm_bleed
    injuries["chest"] = dict(injuries.get("chest", {}) or {})
    injuries["chest"]["external"] = chest_external
    injuries["chest"]["internal"] = chest_internal
    injuries["chest"]["bruise"] = 0
    injuries["chest"]["bleed"] = chest_bleed
    target.db.injuries = injuries
    target.sync_resources_from_empath_wounds()
    target.update_bleed_state()


def _run_pending_revive_without_cleanup(scheduled, character_module):
    if not scheduled:
        raise AssertionError("Expected a queued revive callback.")
    event = scheduled.pop(0)
    nested_delay = character_module.delay

    def _suppress_cleanup(_seconds, _callback, *args, **kwargs):
        return None

    character_module.delay = _suppress_cleanup
    try:
        event["callback"](*event["args"], **event["kwargs"])
    finally:
        character_module.delay = nested_delay


def _run_resurrection_contract_case(case_key, wound_profile, prep_actions=None, post_ticks=6):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room(f"diretest_{case_key}")
    room.db.is_shrine = True
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()
    cleric = None
    empath = None
    patient = None
    corpse = None
    try:
        character_module.delay = fake_delay

        cleric = create_object("typeclasses.characters.Character", key=f"TEST_{case_key.upper()}_CLERIC", location=room, home=room)
        empath = create_object("typeclasses.characters.Character", key=f"TEST_{case_key.upper()}_EMPATH", location=room, home=room)
        patient = create_object("typeclasses.characters.Character", key=f"TEST_{case_key.upper()}_PATIENT", location=room, home=room)

        for obj in (cleric, empath, patient):
            obj.ensure_core_defaults()

        cleric.set_profession("cleric")
        cleric.set_devotion(500)
        empath.set_profession("empath")
        _diretest_set_progression_rank(empath, "empathy", 40)
        patient.set_favor(5)

        _seed_resurrection_contract_wounds(patient, **wound_profile)
        patient.set_hp(0)

        corpse = patient.get_death_corpse()
        if not corpse:
            raise AssertionError(f"{case_key} scenario failed to create a corpse.")

        if prep_actions:
            ok, touch_message = empath.touch_empath_target(corpse)
            if not ok:
                raise AssertionError(touch_message)
            for wound_key, selector in prep_actions:
                ok, action_message = empath.take_empath_wound(wound_key, selector=selector)
                if not ok:
                    raise AssertionError(action_message)

        band_before = cleric.get_corpse_revive_survivability_band(corpse)
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))
        ok, revive_message = cleric.start_cleric_revive(corpse)
        if not ok:
            raise AssertionError(revive_message)
        _run_pending_revive_without_cleanup(scheduled, character_module)

        starting_hp = int(getattr(patient.db, "hp", 0) or 0)
        tick_results = []
        for tick in range(1, post_ticks + 1):
            if not patient.is_dead():
                patient.process_bleed()
            tick_results.append(
                {
                    "tick": tick,
                    "dead": bool(patient.is_dead()),
                    "hp": int(getattr(patient.db, "hp", 0) or 0),
                }
            )

        return {
            "band_before": band_before,
            "starting_hp": starting_hp,
            "tick_results": tick_results,
            "patient_dead": bool(patient.is_dead()),
        }
    finally:
        character_module.delay = original_delay
        for obj in (cleric, empath, patient):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "resurrection-bad-prep-redie",
    aliases=["resurrection_bad_prep_redie"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that an untreated corpse can be revived with favor but still redies from ongoing wounds.",
        "tags": ["death", "empath", "cleric", "resurrection"],
    },
)
def run_resurrection_bad_prep_redie_scenario(args):
    result = _run_resurrection_contract_case(
        "resurrection_bad_prep_redie",
        {
            "vitality": 75,
            "bleeding": 45,
            "chest_internal": 55,
            "chest_bleed": 5,
            "arm_bleed": 5,
        },
        prep_actions=[],
        post_ticks=4,
    )
    if result["band_before"] != "unsafe":
        raise AssertionError(f"Bad prep case should stay unsafe before revive: {result}")
    if not result["patient_dead"]:
        raise AssertionError(f"Bad prep case should redie within a few ticks: {result}")
    print(json.dumps({"scenario": "resurrection-bad-prep-redie", "ok": True, **result}, indent=2, sort_keys=True))
    return 0


@register_scenario(
    "resurrection-good-prep-survives",
    aliases=["resurrection_good_prep_survives"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that enough empath prep makes the corpse stable enough to survive after revival.",
        "tags": ["death", "empath", "cleric", "resurrection"],
    },
)
def run_resurrection_good_prep_survives_scenario(args):
    result = _run_resurrection_contract_case(
        "resurrection_good_prep_survives",
        {
            "vitality": 75,
            "bleeding": 45,
            "chest_internal": 55,
            "chest_bleed": 5,
            "arm_bleed": 5,
        },
        prep_actions=[("bleeding", "arm"), ("vitality", "chest")],
        post_ticks=8,
    )
    if result["band_before"] not in {"stable", "critical"}:
        raise AssertionError(f"Good prep case should be survivable before revive: {result}")
    if result["patient_dead"]:
        raise AssertionError(f"Good prep case should survive the post-revive window: {result}")
    print(json.dumps({"scenario": "resurrection-good-prep-survives", "ok": True, **result}, indent=2, sort_keys=True))
    return 0


@register_scenario(
    "resurrection-borderline-needs-care",
    aliases=["resurrection_borderline_needs_care"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates the borderline case: the patient survives the first guarded tick but still requires immediate intervention.",
        "tags": ["death", "empath", "cleric", "resurrection"],
    },
)
def run_resurrection_borderline_needs_care_scenario(args):
    result = _run_resurrection_contract_case(
        "resurrection_borderline_needs_care",
        {
            "vitality": 55,
            "bleeding": 18,
            "chest_internal": 25,
            "chest_bleed": 8,
            "arm_bleed": 0,
        },
        prep_actions=[],
        post_ticks=5,
    )
    tick_results = result["tick_results"]
    if result["band_before"] != "critical":
        raise AssertionError(f"Borderline case should read as critical before revive: {result}")
    if not tick_results or tick_results[0]["dead"]:
        raise AssertionError(f"Borderline case should survive the first post-revive tick: {result}")
    if tick_results[0]["hp"] >= result["starting_hp"]:
        raise AssertionError(f"Borderline case should worsen immediately without intervention: {result}")
    if not result["patient_dead"]:
        raise AssertionError(f"Borderline case should eventually fail without intervention: {result}")
    print(json.dumps({"scenario": "resurrection-borderline-needs-care", "ok": True, **result}, indent=2, sort_keys=True))
    return 0


@register_scenario(
    "resurrection-stabilization-decay",
    aliases=["resurrection_stabilization_decay"],
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates staged corpse decay penalties, multi-empath corpse prep stacking, and the one-tick post-res death guard.",
        "tags": ["death", "empath", "cleric", "resurrection"],
    },
)
def run_resurrection_stabilization_decay_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_resurrection_stabilization_decay")
    room.db.is_shrine = True
    cleric = None
    empath_one = None
    empath_two = None
    patient = None
    corpse = None
    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_RES_STAB_DECAY_CLERIC", location=room, home=room)
        empath_one = create_object("typeclasses.characters.Character", key="TEST_RES_STAB_DECAY_EMPATH_ONE", location=room, home=room)
        empath_two = create_object("typeclasses.characters.Character", key="TEST_RES_STAB_DECAY_EMPATH_TWO", location=room, home=room)
        patient = create_object("typeclasses.characters.Character", key="TEST_RES_STAB_DECAY_PATIENT", location=room, home=room)
        corpse = create_object("typeclasses.corpse.Corpse", key="TEST_RES_STAB_DECAY_CORPSE", location=room, home=room)

        for obj in (cleric, empath_one, empath_two, patient):
            obj.ensure_core_defaults()

        cleric.set_profession("cleric")
        empath_one.set_profession("empath")
        empath_two.set_profession("empath")

        corpse.db.owner_id = int(patient.id or 0)
        corpse.db.corpse_owner_id = int(patient.id or 0)
        corpse.db.owner_name = patient.key
        corpse.db.recovery_allowed = [int(entry.id or 0) for entry in (patient, cleric, empath_one, empath_two)]
        corpse.set_corpse_wounds(
            {
                "empath": {"vitality": 80, "bleeding": 30},
                "injuries": {
                    "chest": {"external": 20, "internal": 60, "bruise": 0, "bleed": 8, "scar": 0},
                    "left_arm": {"external": 10, "internal": 0, "bruise": 0, "bleed": 4, "scar": 0},
                },
            }
        )
        now = time.time()
        corpse.db.time_of_death = now - 700
        corpse.db.death_timestamp = now - 700
        corpse.db.decay_end_time = now + 500
        corpse.db.decay_time = now + 500

        decay_stage = corpse.get_decay_stage() if hasattr(corpse, "get_decay_stage") else -1
        if decay_stage != 2:
            raise AssertionError(f"Expected a stage-2 corpse, got {decay_stage}.")
        if cleric.get_corpse_revive_survivability_band(corpse) != "unsafe":
            raise AssertionError("Stage-2 decay penalties should push this corpse into the unsafe band.")

        ok, touch_result = empath_one.touch_empath_target(corpse)
        if not ok:
            raise AssertionError(touch_result)
        ok, first_take = empath_one.take_empath_wound("bleeding", amount_spec="all")
        if not ok:
            raise AssertionError(first_take)
        ok, second_take = empath_one.take_empath_wound("vitality", selector="chest")
        if not ok:
            raise AssertionError(second_take)
        remaining_one = corpse.get_empath_prep_remaining(empath_one) if hasattr(corpse, "get_empath_prep_remaining") else -1
        if remaining_one != 0:
            raise AssertionError(f"First empath should hit the corpse prep cap, remaining={remaining_one}.")

        ok, touch_result_two = empath_two.touch_empath_target(corpse)
        if not ok:
            raise AssertionError(touch_result_two)
        remaining_two = corpse.get_empath_prep_remaining(empath_two) if hasattr(corpse, "get_empath_prep_remaining") else -1
        if remaining_two <= 0:
            raise AssertionError("Second empath should still have prep budget available.")
        ok, third_take = empath_two.take_empath_wound("vitality", selector="chest")
        if not ok:
            raise AssertionError(third_take)

        patient.revive_from_death(via="resurrection")
        patient.db.injuries = {"chest": {"bleed": 12, "internal": 40, "external": 0, "bruise": 0, "scar": 0}}
        patient.db.hp = 1
        patient.begin_resurrection_stabilization("critical")
        patient.process_bleed()
        if patient.is_dead():
            raise AssertionError("The first post-res bleed tick should be suppressed by the death guard.")
        if int(getattr(patient.db, "hp", 0) or 0) != 1:
            raise AssertionError(f"The death guard should clamp HP to 1, got {patient.db.hp}.")

        print(json.dumps({
            "scenario": "resurrection-stabilization-decay",
            "decay_stage": decay_stage,
            "survivability_band": cleric.get_corpse_revive_survivability_band(corpse),
            "first_empath_remaining": remaining_one,
            "second_empath_remaining": remaining_two,
            "death_guard_hp": int(getattr(patient.db, "hp", 0) or 0),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (corpse, cleric, empath_one, empath_two, patient):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-group-speed-quality",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate cooperative speed reduction and additive quality gains.",
    },
)
def run_cleric_group_speed_quality_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_group_speed_quality")
    room.db.is_shrine = True
    cleric_one = None
    cleric_two = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric_one = create_object("typeclasses.characters.Character", key="TEST_CLERIC_GROUP_SPEED_ONE", location=room, home=room)
        cleric_two = create_object("typeclasses.characters.Character", key="TEST_CLERIC_GROUP_SPEED_TWO", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_GROUP_SPEED_TARGET", location=room, home=room)
        for obj in (cleric_one, cleric_two, target):
            obj.ensure_core_defaults()
        cleric_one.set_profession("cleric")
        cleric_two.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()

        ok, message = cleric_one.prepare_corpse(corpse)
        if not ok:
            raise AssertionError(message)
        _run_fake_delay_queue(scheduled)

        ok, message = cleric_one.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        ok, message = cleric_two.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        if len(scheduled) != 2:
            raise AssertionError(f"Group-speed scenario expected two queued stabilize actions, got {len(scheduled)}.")
        delays = [float(event.get("seconds", 0.0) or 0.0) for event in scheduled]
        if min(delays) >= max(delays):
            raise AssertionError(f"Group-speed scenario did not reduce any stabilize delay: {delays}")

        _run_fake_delay_queue(scheduled)

        participants = list(getattr(corpse.db, "ritual_participants", []) or [])
        stage_contributors = dict(getattr(corpse.db, "stage_contributors", {}) or {})
        ritual_quality = int(getattr(corpse.db, "ritual_quality", 0) or 0)
        if str(getattr(corpse.db, "ritual_state", "") or "") != "stabilized":
            raise AssertionError("Group-speed scenario did not leave the corpse stabilized.")
        if len(participants) != 2:
            raise AssertionError(f"Group-speed scenario did not track both ritual participants: {participants}")
        if len(list(stage_contributors.get("stabilize", []) or [])) != 2:
            raise AssertionError(f"Group-speed scenario did not track both stabilize contributors: {stage_contributors}")
        if ritual_quality < 5:
            raise AssertionError(f"Group-speed scenario did not accumulate the expected group quality: {ritual_quality}")

        print(json.dumps({
            "scenario": "cleric-group-speed-quality",
            "delays": delays,
            "participants": len(participants),
            "ritual_quality": ritual_quality,
            "stabilize_contributors": len(list(stage_contributors.get("stabilize", []) or [])),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric_one, cleric_two, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-group-interruption-mitigation",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses paired stabilize attempts to validate that one interruption does not knock the whole group ritual backward.",
    },
)
def run_cleric_group_interruption_mitigation_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_group_interrupt")
    room.db.is_shrine = True
    cleric_one = None
    cleric_two = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric_one = create_object("typeclasses.characters.Character", key="TEST_CLERIC_GROUP_INTERRUPT_ONE", location=room, home=room)
        cleric_two = create_object("typeclasses.characters.Character", key="TEST_CLERIC_GROUP_INTERRUPT_TWO", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_GROUP_INTERRUPT_TARGET", location=room, home=room)
        for obj in (cleric_one, cleric_two, target):
            obj.ensure_core_defaults()
        cleric_one.set_profession("cleric")
        cleric_two.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()

        _run_cleric_ritual_chain(cleric_one, corpse, scheduled, ("prepare",))
        ok, message = cleric_one.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        ok, message = cleric_two.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        cleric_one.set_hp(int(getattr(cleric_one.db, "hp", 100) or 100) - 1)
        _run_fake_delay_queue(scheduled)

        ritual_state = str(getattr(corpse.db, "ritual_state", "") or "")
        ritual_failures = int(getattr(corpse.db, "ritual_failures", 0) or 0)
        stabilize_contributors = list((getattr(corpse.db, "stage_contributors", {}) or {}).get("stabilize", []) or [])
        if ritual_state != "stabilized":
            raise AssertionError(f"Group interruption scenario regressed the corpse instead of preserving progress: {ritual_state}")
        if ritual_failures != 1:
            raise AssertionError(f"Group interruption scenario did not record exactly one failure: {ritual_failures}")
        if len(stabilize_contributors) != 1:
            raise AssertionError(f"Group interruption scenario recorded the wrong stabilize contributors: {stabilize_contributors}")

        print(json.dumps({
            "scenario": "cleric-group-interruption-mitigation",
            "ritual_failures": ritual_failures,
            "ritual_state": ritual_state,
            "stabilize_contributors": len(stabilize_contributors),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric_one, cleric_two, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-specialization-light",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses repeated prepare actions across fresh corpses to validate soft specialization unlocks and discounted costs.",
    },
)
def run_cleric_specialization_light_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_specialization_light")
    room.db.is_shrine = True
    cleric = None
    target_one = None
    target_two = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_SPECIALIZATION", location=room, home=room)
        target_one = create_object("typeclasses.characters.Character", key="TEST_CLERIC_SPECIALIZATION_TARGET_ONE", location=room, home=room)
        target_two = create_object("typeclasses.characters.Character", key="TEST_CLERIC_SPECIALIZATION_TARGET_TWO", location=room, home=room)
        for obj in (cleric, target_one, target_two):
            obj.ensure_core_defaults()
        cleric.set_profession("cleric")
        cleric.set_devotion(100)
        target_one.set_favor(2)
        target_two.set_favor(2)
        target_one.set_hp(0)
        target_two.set_hp(0)
        corpse_one = target_one.get_death_corpse()
        corpse_two = target_two.get_death_corpse()

        ok, message = cleric.prepare_corpse(corpse_one)
        if not ok:
            raise AssertionError(message)
        devotion_after_first = int(getattr(cleric.db, "devotion_current", 0) or 0)
        _run_fake_delay_queue(scheduled)
        ok, message = cleric.prepare_corpse(corpse_two)
        if not ok:
            raise AssertionError(message)
        devotion_after_second = int(getattr(cleric.db, "devotion_current", 0) or 0)
        specialization = str(getattr(cleric.db, "specialization", "") or "")
        if devotion_after_first != 95:
            raise AssertionError(f"Specialization scenario charged the wrong first prepare cost: {devotion_after_first}")
        if devotion_after_second != 91:
            raise AssertionError(f"Specialization scenario did not apply the discounted second prepare cost: {devotion_after_second}")
        if specialization != "stabilizer":
            raise AssertionError(f"Specialization scenario unlocked the wrong specialization: {specialization}")
        if "Your practice settles into the patterns of stabilization." not in str(message or ""):
            raise AssertionError(f"Specialization scenario did not surface the unlock message: {message}")

        print(json.dumps({
            "scenario": "cleric-specialization-light",
            "devotion_after_first": devotion_after_first,
            "devotion_after_second": devotion_after_second,
            "specialization": specialization,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target_one, target_two):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-specialization-score-output",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates cleric score output shows specialization labels without exposing mechanics.",
    },
)
def run_cleric_specialization_score_output_scenario(args):
    _setup_django()

    from commands.cmd_stats import CmdStats
    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_specialization_score")
    cleric = None
    originals = {}

    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_SCORE_SPEC", location=room, home=room)
        cleric.ensure_core_defaults()
        cleric.set_profession("cleric")

        captured, originals = _capture_object_messages(cleric)
        cases = (
            (None, "Specialization: None"),
            ("stabilizer", "Specialization: Stabilizer"),
            ("restorer", "Specialization: Restorer"),
            ("binder", "Specialization: Binder"),
        )
        results = []

        for specialization, expected_line in cases:
            cleric.db.specialization = specialization
            captured[cleric].clear()
            cmd = CmdStats()
            cmd.caller = cleric
            cmd.args = ""
            cmd.cmdstring = "score"
            cmd.func()
            output = "\n".join(captured.get(cleric) or [])
            if expected_line not in output:
                raise AssertionError(f"Score specialization scenario did not report '{expected_line}': {output}")
            results.append(expected_line)

        print(json.dumps({
            "scenario": "cleric-specialization-score-output",
            "lines": results,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        if cleric:
            try:
                cleric.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-specialization-unlock-behavior",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses repeated stabilize work across fresh corpses to validate one-time specialization unlock messaging.",
    },
)
def run_cleric_specialization_unlock_behavior_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_specialization_unlock")
    room.db.is_shrine = True
    cleric = None
    targets = []
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_UNLOCK", location=room, home=room)
        cleric.ensure_core_defaults()
        cleric.set_profession("cleric")
        cleric.set_devotion(100)

        stabilize_messages = []
        for index in range(1, 4):
            target = create_object("typeclasses.characters.Character", key=f"TEST_CLERIC_UNLOCK_TARGET_{index}", location=room, home=room)
            target.ensure_core_defaults()
            target.set_favor(2)
            target.set_hp(0)
            corpse = target.get_death_corpse()
            corpse.db.ritual_state = "prepared"
            ok, message = cleric.start_cleric_corpse_ritual(corpse, "stabilize")
            if not ok:
                raise AssertionError(message)
            stabilize_messages.append(str(message or ""))
            _run_fake_delay_queue(scheduled)
            targets.append(target)

        unlock_line = "Your practice settles into the patterns of stabilization."
        if unlock_line in stabilize_messages[0]:
            raise AssertionError(f"Unlock behavior scenario announced specialization too early: {stabilize_messages[0]}")
        if unlock_line not in stabilize_messages[1]:
            raise AssertionError(f"Unlock behavior scenario missed the unlock message: {stabilize_messages[1]}")
        if unlock_line in stabilize_messages[2]:
            raise AssertionError(f"Unlock behavior scenario repeated the unlock message after it was announced: {stabilize_messages[2]}")
        if str(getattr(cleric.db, "specialization", "") or "") != "stabilizer":
            raise AssertionError(f"Unlock behavior scenario unlocked the wrong specialization: {getattr(cleric.db, 'specialization', '')}")
        if not bool(getattr(cleric.db, "specialization_announced", False)):
            raise AssertionError("Unlock behavior scenario did not set specialization_announced.")

        print(json.dumps({
            "scenario": "cleric-specialization-unlock-behavior",
            "messages": stabilize_messages,
            "ok": True,
            "specialization": str(getattr(cleric.db, "specialization", "") or ""),
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in [cleric, *targets]:
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-specialization-match-feedback",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses matching and non-matching ritual stages to validate subtle specialization feedback without leaking numeric effects.",
    },
)
def run_cleric_specialization_match_feedback_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_specialization_feedback")
    room.db.is_shrine = True
    cleric = None
    targets = []
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()
    originals = {}

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MATCH_SPEC", location=room, home=room)
        cleric.ensure_core_defaults()
        cleric.set_profession("cleric")
        cleric.db.specialization = "stabilizer"
        cleric.db.specialization_announced = True

        target_match = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MATCH_TARGET", location=room, home=room)
        target_nonmatch = create_object("typeclasses.characters.Character", key="TEST_CLERIC_NONMATCH_TARGET", location=room, home=room)
        for target in (target_match, target_nonmatch):
            target.ensure_core_defaults()
            target.set_favor(2)
            target.set_hp(0)
            targets.append(target)

        captured, originals = _capture_object_messages(cleric)

        corpse_match = target_match.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse_match, scheduled, ("prepare",))
        captured[cleric].clear()
        ok, message = cleric.start_cleric_corpse_ritual(corpse_match, "stabilize")
        if not ok:
            raise AssertionError(message)
        _run_fake_delay_queue(scheduled)
        match_text = "\n".join(captured.get(cleric) or [])
        if "Your practiced hands steady the work." not in match_text:
            raise AssertionError(f"Match feedback scenario missed the matching specialization text: {match_text}")

        corpse_nonmatch = target_nonmatch.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse_nonmatch, scheduled, ("prepare", "stabilize"))
        captured[cleric].clear()
        ok, message = cleric.start_cleric_corpse_ritual(corpse_nonmatch, "restore")
        if not ok:
            raise AssertionError(message)
        _run_fake_delay_queue(scheduled)
        nonmatch_text = "\n".join(captured.get(cleric) or [])
        if "Your practiced hands steady the work." in nonmatch_text or "The rite comes more naturally to you." in nonmatch_text or "Your focus aligns cleanly with the ritual." in nonmatch_text:
            raise AssertionError(f"Match feedback scenario reported specialization text for a non-matching stage: {nonmatch_text}")

        print(json.dumps({
            "scenario": "cleric-specialization-match-feedback",
            "match_feedback": True,
            "nonmatch_feedback": False,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        character_module.delay = original_delay
        for obj in [cleric, *targets]:
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-assess-visibility",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates readable assess summaries for each ritual state without exposing raw quality values.",
    },
)
def run_cleric_assess_visibility_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_assess_visibility")
    room.db.is_shrine = True
    cleric = None
    targets = []

    state_cases = (
        ("prepared", "The rite is ready for stabilization.", 1, 1, {"prepare": 1, "stabilize": 0, "restore": 0, "bind": 0}),
        ("stabilized", "The rite is ready for restoration.", 4, 1, {"prepare": 1, "stabilize": 2, "restore": 0, "bind": 0}),
        ("restored", "The rite is ready for binding.", 7, 1, {"prepare": 1, "stabilize": 2, "restore": 1, "bind": 0}),
        ("bound", "The final rite may now be attempted.", 12, 2, {"prepare": 1, "stabilize": 2, "restore": 1, "bind": 1}),
    )

    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_ASSESS", location=room, home=room)
        cleric.ensure_core_defaults()
        cleric.set_profession("cleric")

        results = []
        quality_expectations = {1: "Poor", 4: "Unsteady", 7: "Strong", 12: "Excellent"}

        for index, (state, readiness_line, quality_value, failure_count, stage_counts) in enumerate(state_cases, start=1):
            target = create_object("typeclasses.characters.Character", key=f"TEST_CLERIC_ASSESS_TARGET_{index}", location=room, home=room)
            target.ensure_core_defaults()
            target.set_favor(2)
            target.set_hp(0)
            corpse = target.get_death_corpse()
            if not corpse:
                raise AssertionError(f"Assess-visibility scenario did not create corpse for {state}.")
            corpse.db.ritual_state = state
            corpse.db.soul_bound = state == "bound"
            corpse.db.memory_stable = state in {"restored", "bound"}
            corpse.db.stabilized = state in {"stabilized", "restored", "bound"}
            corpse.db.ritual_quality = quality_value
            corpse.db.ritual_failures = failure_count
            corpse.db.memory_time = time.time() + 600
            corpse.db.ritual_participants = [int(cleric.id or 0), int(target.id or 0)] if state in {"stabilized", "bound"} else [int(cleric.id or 0)]
            corpse.db.stage_contributors = {
                "prepare": [int(cleric.id or 0)] if stage_counts["prepare"] else [],
                "stabilize": [int(cleric.id or 0), int(target.id or 0)] if stage_counts["stabilize"] >= 2 else ([int(cleric.id or 0)] if stage_counts["stabilize"] else []),
                "restore": [int(cleric.id or 0)] if stage_counts["restore"] else [],
                "bind": [int(cleric.id or 0)] if stage_counts["bind"] else [],
            }

            ok, lines = cleric.assess_cleric_corpse(corpse)
            if not ok:
                raise AssertionError(f"Assess-visibility scenario failed to assess {state}: {lines}")
            text = "\n".join(lines)
            if f"Ritual State: {state.title()}" not in text:
                raise AssertionError(f"Assess-visibility scenario did not report the ritual state for {state}: {text}")
            if f"Failures: {failure_count}" not in text:
                raise AssertionError(f"Assess-visibility scenario did not report the failure count for {state}: {text}")
            if f"Quality: {quality_expectations[quality_value]}" not in text:
                raise AssertionError(f"Assess-visibility scenario did not report the quality label for {state}: {text}")
            if readiness_line not in text:
                raise AssertionError(f"Assess-visibility scenario did not report the readiness line for {state}: {text}")
            if "Named Contributors:" not in text:
                raise AssertionError(f"Assess-visibility scenario did not expose named contributors to a participant for {state}: {text}")
            ritual_state_index = lines.index(next(line for line in lines if line.startswith("Ritual State:")))
            contributors_index = lines.index("Contributors:")
            readiness_index = lines.index(readiness_line)
            if not (ritual_state_index < contributors_index < readiness_index):
                raise AssertionError(f"Assess-visibility scenario produced the wrong output order for {state}: {lines}")
            results.append({
                "state": state,
                "quality": quality_expectations[quality_value],
                "readiness": readiness_line,
            })
            targets.append(target)

        print(json.dumps({
            "scenario": "cleric-assess-visibility",
            "results": results,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in [cleric, *targets]:
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-assess-blockers",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates explicit assess blocker messaging for favor, memory, location, and binding failures.",
    },
)
def run_cleric_assess_blockers_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_assess_blockers")
    room.db.is_shrine = True
    cleric = None
    targets = []

    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_ASSESS_BLOCKERS", location=room, home=room)
        cleric.ensure_core_defaults()
        cleric.set_profession("cleric")

        cases = []

        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_BLOCKER_FAVOR", location=room, home=room)
        target.ensure_core_defaults()
        target.set_favor(0)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        corpse.db.ritual_state = "bound"
        corpse.db.soul_bound = True
        corpse.db.memory_stable = True
        corpse.db.memory_time = time.time() + 600
        cases.append((corpse, "No favor remains to guide the soul."))
        targets.append(target)

        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_BLOCKER_MEMORY", location=room, home=room)
        target.ensure_core_defaults()
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        corpse.db.ritual_state = "bound"
        corpse.db.soul_bound = True
        corpse.db.memory_stable = False
        corpse.db.memory_time = time.time() - 1
        corpse.db.memory_faded = True
        cases.append((corpse, "The corpse's memory has faded."))
        targets.append(target)

        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_BLOCKER_PLACE", location=room, home=room)
        target.ensure_core_defaults()
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        corpse.db.ritual_state = "bound"
        corpse.db.soul_bound = True
        corpse.db.memory_stable = True
        corpse.db.memory_time = time.time() + 600
        cases.append((corpse, "This place is not suitable for the final rite."))
        targets.append(target)

        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_BLOCKER_BIND", location=room, home=room)
        target.ensure_core_defaults()
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        corpse.db.ritual_state = "restored"
        corpse.db.soul_bound = False
        corpse.db.memory_stable = True
        corpse.db.memory_time = time.time() + 600
        cases.append((corpse, "The soul has not yet been bound."))
        targets.append(target)

        results = []
        for index, (corpse, expected_blocker) in enumerate(cases):
            room.db.is_shrine = index != 2
            ok, lines = cleric.assess_cleric_corpse(corpse)
            if not ok:
                raise AssertionError(f"Assess-blockers scenario could not assess corpse: {lines}")
            text = "\n".join(lines)
            if expected_blocker not in text:
                raise AssertionError(f"Assess-blockers scenario did not report '{expected_blocker}': {text}")
            results.append(expected_blocker)

        print(json.dumps({
            "scenario": "cleric-assess-blockers",
            "blockers": results,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        room.db.is_shrine = True
        for obj in [cleric, *targets]:
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-start-join-messaging",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate first-actor start messaging, join messaging, and duplicate join suppression.",
    },
)
def run_cleric_ritual_start_join_messaging_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_start_join_messaging")
    room.db.is_shrine = True
    cleric_a = None
    cleric_b = None
    observer = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()
    originals = {}

    try:
        character_module.delay = fake_delay
        cleric_a = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MSG_A", location=room, home=room)
        cleric_b = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MSG_B", location=room, home=room)
        observer = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MSG_OBSERVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MSG_TARGET", location=room, home=room)
        for obj in (cleric_a, cleric_b, observer, target):
            obj.ensure_core_defaults()
        cleric_a.set_profession("cleric")
        cleric_b.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()

        captured, originals = _capture_object_messages(cleric_a, cleric_b, observer, target)
        _run_cleric_ritual_chain(cleric_a, corpse, scheduled, ("prepare",))
        for bucket in captured.values():
            bucket.clear()

        ok, message = cleric_a.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        start_text = "\n".join(captured.get(observer) or [])
        if "TEST_CLERIC_MSG_A begins a stabilization vigil." not in start_text:
            raise AssertionError(f"Start/join messaging scenario missed the first-actor start message: {start_text}")

        for bucket in captured.values():
            bucket.clear()
        ok, message = cleric_b.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        join_text = "\n".join(captured.get(observer) or [])
        if "TEST_CLERIC_MSG_B joins the stabilization rite." not in join_text:
            raise AssertionError(f"Start/join messaging scenario missed the join message: {join_text}")
        if "Another set of practiced hands strengthens the ritual." not in join_text:
            raise AssertionError(f"Start/join messaging scenario missed the reinforcement message: {join_text}")

        for bucket in captured.values():
            bucket.clear()
        cleric_b.cancel_pending_cleric_ritual(message=None, emit_message=False)
        ok, message = cleric_b.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        retry_text = "\n".join(captured.get(observer) or [])
        if retry_text.strip():
            raise AssertionError(f"Start/join messaging scenario emitted duplicate join spam on retry: {retry_text}")

        print(json.dumps({
            "scenario": "cleric-ritual-start-join-messaging",
            "start_message": True,
            "join_message": True,
            "retry_suppressed": True,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        character_module.delay = original_delay
        for obj in (cleric_a, cleric_b, observer, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-interruption-locality",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses paired stabilize attempts to validate localized interruption messaging without false global failure text.",
    },
)
def run_cleric_ritual_interruption_locality_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_interrupt_locality")
    room.db.is_shrine = True
    cleric_a = None
    cleric_b = None
    observer = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()
    originals = {}

    try:
        character_module.delay = fake_delay
        cleric_a = create_object("typeclasses.characters.Character", key="TEST_CLERIC_INTERRUPT_A", location=room, home=room)
        cleric_b = create_object("typeclasses.characters.Character", key="TEST_CLERIC_INTERRUPT_B", location=room, home=room)
        observer = create_object("typeclasses.characters.Character", key="TEST_CLERIC_INTERRUPT_OBSERVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_INTERRUPT_TARGET", location=room, home=room)
        for obj in (cleric_a, cleric_b, observer, target):
            obj.ensure_core_defaults()
        cleric_a.set_profession("cleric")
        cleric_b.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()

        captured, originals = _capture_object_messages(cleric_a, cleric_b, observer, target)
        _run_cleric_ritual_chain(cleric_a, corpse, scheduled, ("prepare",))
        for bucket in captured.values():
            bucket.clear()

        ok, message = cleric_a.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        ok, message = cleric_b.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        cleric_b.set_hp(int(getattr(cleric_b.db, "hp", 100) or 100) - 1)
        _run_fake_delay_queue(scheduled)

        observer_text = "\n".join(captured.get(observer) or [])
        actor_text = "\n".join(captured.get(cleric_b) or [])
        if "TEST_CLERIC_INTERRUPT_B's part of the rite falters." not in observer_text:
            raise AssertionError(f"Interruption-locality scenario missed the localized room failure message: {observer_text}")
        if "The ritual slips backward under the strain." in observer_text:
            raise AssertionError(f"Interruption-locality scenario reported a global regression when progress should have held: {observer_text}")
        if "The rite holds, but your part in it is lost." not in actor_text:
            raise AssertionError(f"Interruption-locality scenario missed the interrupted actor feedback: {actor_text}")
        if str(getattr(corpse.db, "ritual_state", "") or "") != "stabilized":
            raise AssertionError(f"Interruption-locality scenario regressed the corpse unexpectedly: {getattr(corpse.db, 'ritual_state', '')}")

        print(json.dumps({
            "scenario": "cleric-ritual-interruption-locality",
            "localized_failure": True,
            "global_regression_avoided": True,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        character_module.delay = original_delay
        for obj in (cleric_a, cleric_b, observer, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-progression-messaging",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses a single prepare completion to validate stage completion, readiness, and dead-owner sensory messaging.",
    },
)
def run_cleric_ritual_progression_messaging_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_progression_messaging")
    room.db.is_shrine = True
    cleric = None
    observer = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()
    originals = {}

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_PROGRESS", location=room, home=room)
        observer = create_object("typeclasses.characters.Character", key="TEST_CLERIC_PROGRESS_OBSERVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_PROGRESS_TARGET", location=room, home=room)
        for obj in (cleric, observer, target):
            obj.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()

        captured, originals = _capture_object_messages(cleric, observer, target)
        ok, message = cleric.prepare_corpse(corpse)
        if not ok:
            raise AssertionError(message)
        _run_fake_delay_queue(scheduled)

        observer_text = "\n".join(captured.get(observer) or [])
        owner_text = "\n".join(captured.get(target) or [])
        if "The body settles into ritual readiness." not in observer_text:
            raise AssertionError(f"Progression-messaging scenario missed the stage completion message: {observer_text}")
        if "The rite is ready for stabilization." not in observer_text:
            raise AssertionError(f"Progression-messaging scenario missed the readiness cue: {observer_text}")
        if "You feel distant hands preparing your body." not in owner_text:
            raise AssertionError(f"Progression-messaging scenario missed the dead-owner sensory feedback: {owner_text}")

        print(json.dumps({
            "scenario": "cleric-ritual-progression-messaging",
            "completion_message": True,
            "readiness_message": True,
            "owner_feedback": True,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        character_module.delay = original_delay
        for obj in (cleric, observer, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-antispam",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses rapid repeated join retries to validate the anti-spam guard for ritual room messaging.",
    },
)
def run_cleric_ritual_antispam_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_antispam")
    room.db.is_shrine = True
    cleric_a = None
    cleric_b = None
    observer = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()
    originals = {}

    try:
        character_module.delay = fake_delay
        cleric_a = create_object("typeclasses.characters.Character", key="TEST_CLERIC_SPAM_A", location=room, home=room)
        cleric_b = create_object("typeclasses.characters.Character", key="TEST_CLERIC_SPAM_B", location=room, home=room)
        observer = create_object("typeclasses.characters.Character", key="TEST_CLERIC_SPAM_OBSERVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_SPAM_TARGET", location=room, home=room)
        for obj in (cleric_a, cleric_b, observer, target):
            obj.ensure_core_defaults()
        cleric_a.set_profession("cleric")
        cleric_b.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()

        captured, originals = _capture_object_messages(cleric_a, cleric_b, observer, target)
        _run_cleric_ritual_chain(cleric_a, corpse, scheduled, ("prepare",))
        for bucket in captured.values():
            bucket.clear()

        ok, message = cleric_a.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        for _attempt in range(3):
            ok, message = cleric_b.start_cleric_corpse_ritual(corpse, "stabilize")
            if not ok:
                raise AssertionError(message)
            cleric_b.cancel_pending_cleric_ritual(message=None, emit_message=False)
        observer_text = "\n".join(captured.get(observer) or [])
        join_count = observer_text.count("TEST_CLERIC_SPAM_B joins the stabilization rite.")
        reinforce_count = observer_text.count("Another set of practiced hands strengthens the ritual.")
        if join_count != 1 or reinforce_count != 1:
            raise AssertionError(f"Antispam scenario allowed ritual room messages to flood output: joins={join_count}, reinforce={reinforce_count}, text={observer_text}")

        print(json.dumps({
            "scenario": "cleric-ritual-antispam",
            "join_count": join_count,
            "reinforce_count": reinforce_count,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        character_module.delay = original_delay
        for obj in (cleric_a, cleric_b, observer, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-failure-reduces-quality",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses an interrupted retry chain to validate quality loss and clamping.",
    },
)
def run_cleric_ritual_failure_reduces_quality_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_quality_loss")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_QUALITY_LOSS", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_QUALITY_LOSS_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare",))
        ok, message = cleric.start_cleric_corpse_ritual(corpse, "stabilize")
        if not ok:
            raise AssertionError(message)
        cleric.set_hp(int(getattr(cleric.db, "hp", 100) or 100) - 1)
        _run_fake_delay_queue(scheduled)
        if int(getattr(corpse.db, "ritual_quality", 0) or 0) != 0:
            raise AssertionError("Failure-quality scenario did not clamp ritual_quality at zero after interruption.")
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("stabilize", "restore", "bind"))
        if int(getattr(corpse.db, "ritual_quality", 0) or 0) != 8:
            raise AssertionError("Failure-quality scenario did not preserve the reduced quality after retrying the chain.")
        print(json.dumps({
            "scenario": "cleric-ritual-failure-reduces-quality",
            "ritual_failures": int(getattr(corpse.db, "ritual_failures", 0) or 0),
            "ritual_quality": int(getattr(corpse.db, "ritual_quality", 0) or 0),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-unprepared-revive",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that revive fails immediately on an unprepared corpse.",
    },
)
def run_cleric_ritual_unprepared_revive_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_unprepared_revive")
    room.db.is_shrine = True
    cleric = None
    target = None
    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_UNPREPARED_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_UNPREPARED_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        ok, message = cleric.start_cleric_revive(corpse)
        if ok:
            raise AssertionError("Unprepared-revive scenario unexpectedly allowed revive startup.")
        expected = "The body is not prepared for the rite."
        if str(message or "") != expected:
            raise AssertionError(f"Unprepared-revive scenario returned the wrong failure message: {message}")
        print(json.dumps({
            "scenario": "cleric-ritual-unprepared-revive",
            "message": str(message or ""),
            "ritual_state": str(getattr(corpse.db, "ritual_state", "") or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-prepare",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate preparation completion and idempotency.",
    },
)
def run_cleric_ritual_prepare_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_prepare")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_PREPARE_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_PREPARE_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        ok, message = cleric.prepare_corpse(corpse)
        if not ok:
            raise AssertionError(message)
        _run_fake_delay_queue(scheduled)
        if str(getattr(corpse.db, "ritual_state", "") or "") != "prepared":
            raise AssertionError("Prepare scenario did not transition the corpse to prepared.")
        if int(getattr(corpse.db, "prepared_by", 0) or 0) != int(getattr(cleric, "id", 0) or 0):
            raise AssertionError("Prepare scenario did not stamp prepared_by.")
        second_ok, second_message = cleric.prepare_corpse(corpse)
        if second_ok:
            raise AssertionError("Prepare scenario unexpectedly allowed a second preparation.")
        if str(second_message or "") != "The body is already prepared for the rite.":
            raise AssertionError(f"Prepare scenario returned the wrong idempotency message: {second_message}")
        print(json.dumps({
            "scenario": "cleric-ritual-prepare",
            "ritual_state": str(getattr(corpse.db, "ritual_state", "") or ""),
            "prepared_by": int(getattr(corpse.db, "prepared_by", 0) or 0),
            "second_message": str(second_message or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-restore-flow",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate prepare/stabilize/restore state transitions.",
    },
)
def run_cleric_ritual_restore_flow_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_restore_flow")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_RESTORE_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_RESTORE_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare", "stabilize", "restore"))
        if str(getattr(corpse.db, "ritual_state", "") or "") != "restored":
            raise AssertionError("Restore-flow scenario did not end in restored state.")
        if not bool(getattr(corpse.db, "memory_stable", False)):
            raise AssertionError("Restore-flow scenario did not set memory_stable.")
        if not bool(getattr(corpse.db, "stabilized", False)):
            raise AssertionError("Restore-flow scenario did not preserve stabilized state.")
        print(json.dumps({
            "scenario": "cleric-ritual-restore-flow",
            "ritual_state": str(getattr(corpse.db, "ritual_state", "") or ""),
            "memory_stable": bool(getattr(corpse.db, "memory_stable", False)),
            "stabilized": bool(getattr(corpse.db, "stabilized", False)),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-ritual-missing-step",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates that later ritual stages and revive fail clearly when steps are skipped.",
    },
)
def run_cleric_ritual_missing_step_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_missing_step")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MISSING_STEP_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_MISSING_STEP_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        prepare_ok, prepare_message = cleric.prepare_corpse(corpse)
        if not prepare_ok:
            raise AssertionError(prepare_message)
        _run_fake_delay_queue(scheduled)
        restore_ok, restore_message = cleric.start_cleric_corpse_ritual(corpse, "restore")
        if restore_ok:
            raise AssertionError("Missing-step scenario unexpectedly allowed restore before stabilization.")
        if str(restore_message or "") != "The body must be stabilized before its memories can be restored.":
            raise AssertionError(f"Missing-step scenario returned the wrong restore failure message: {restore_message}")
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("stabilize", "restore"))
        revive_ok, revive_message = cleric.start_cleric_revive(corpse)
        if revive_ok:
            raise AssertionError("Missing-step scenario unexpectedly allowed revive before binding.")
        if str(revive_message or "") != "The soul has not been secured.":
            raise AssertionError(f"Missing-step scenario returned the wrong revive failure message: {revive_message}")
        print(json.dumps({
            "scenario": "cleric-ritual-missing-step",
            "restore_message": str(restore_message or ""),
            "revive_message": str(revive_message or ""),
            "ritual_state": str(getattr(corpse.db, "ritual_state", "") or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-revive-zero-favor",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates revive rejection before any delayed callback is scheduled.",
    },
)
def run_cleric_revive_zero_favor_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_zero_favor")
    room.db.is_shrine = True
    cleric = None
    target = None
    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_ZERO_FAVOR_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_ZERO_FAVOR_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(0)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        if not corpse:
            raise AssertionError("Zero-favor scenario did not create a corpse.")
        corpse.db.ritual_state = "bound"
        corpse.db.soul_bound = True
        corpse.db.memory_stable = True
        ok, message = cleric.start_cleric_revive(corpse)
        if ok:
            raise AssertionError("Zero-favor scenario unexpectedly allowed revive startup.")
        expected = "There is not enough lingering favor to revive them."
        if str(message or "") != expected:
            raise AssertionError(f"Zero-favor scenario returned the wrong failure message: {message}")
        print(json.dumps({
            "scenario": "cleric-revive-zero-favor",
            "corpse_favor_snapshot": int(getattr(corpse.db, "favor_snapshot", 0) or 0),
            "message": str(message or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "favor-clamp",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Exercises the normalized favor setter directly to keep clamp validation deterministic.",
    },
)
def run_favor_clamp_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_favor_clamp")
    character = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_FAVOR_CLAMP", location=room, home=room)
        character.ensure_core_defaults()
        character.set_favor(99)
        high = character.get_favor()
        character.set_favor(-5)
        low = character.get_favor()
        if high != 5:
            raise AssertionError(f"Favor-clamp scenario failed to clamp high values: {high}")
        if low != 0:
            raise AssertionError(f"Favor-clamp scenario failed to clamp low values: {low}")
        print(json.dumps({
            "scenario": "favor-clamp",
            "high": high,
            "low": low,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario(
    "favor-pray-loop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Patches time to validate the simplified pray cooldown, max state, and dead/combat blockers deterministically.",
    },
)
def run_favor_pray_loop_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_favor_pray")
    character = None
    opponent = None
    originals = {}
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_FAVOR_PRAY", location=room, home=room)
        opponent = create_object("typeclasses.characters.Character", key="TEST_FAVOR_PRAY_FOE", location=room, home=room)
        character.ensure_core_defaults()
        opponent.ensure_core_defaults()
        character.set_favor(1)
        character.db.last_pray_time = 0.0
        captured, originals = _capture_object_messages(character)
        with patch("typeclasses.characters.time.time", return_value=1000.0):
            _run_pray_command(character)
            if int(getattr(character.db, "favor_current", 0) or 0) != 2:
                raise AssertionError("Favor-pray-loop scenario did not gain favor on the first prayer.")
        first_output = "\n".join(captured.get(character) or [])
        if "Favor rises to 2/5" not in first_output:
            raise AssertionError(f"Favor-pray-loop scenario missed the first success message: {first_output}")
        captured[character].clear()
        with patch("typeclasses.characters.time.time", return_value=1001.0):
            _run_pray_command(character)
        second_output = "\n".join(captured.get(character) or [])
        if "Wait 59s" not in second_output:
            raise AssertionError(f"Favor-pray-loop scenario did not enforce cooldown messaging: {second_output}")
        captured[character].clear()
        with patch("typeclasses.characters.time.time", return_value=1061.0):
            _run_pray_command(character)
            if int(getattr(character.db, "favor_current", 0) or 0) != 3:
                raise AssertionError("Favor-pray-loop scenario did not allow prayer after the cooldown expired.")
        character.set_favor(5)
        captured[character].clear()
        with patch("typeclasses.characters.time.time", return_value=1122.0):
            _run_pray_command(character)
        full_output = "\n".join(captured.get(character) or [])
        if "already full" not in full_output:
            raise AssertionError(f"Favor-pray-loop scenario missed the full-favor message: {full_output}")
        character.set_favor(3)
        character.db.last_pray_time = 0.0
        character.set_target(opponent)
        captured[character].clear()
        with patch("typeclasses.characters.time.time", return_value=1183.0):
            _run_pray_command(character)
        combat_output = "\n".join(captured.get(character) or [])
        if "middle of combat" not in combat_output:
            raise AssertionError(f"Favor-pray-loop scenario missed the combat blocker: {combat_output}")
        character.set_target(None)
        character.set_hp(0)
        captured[character].clear()
        with patch("typeclasses.characters.time.time", return_value=1244.0):
            _run_pray_command(character)
        dead_output = "\n".join(captured.get(character) or [])
        if "beyond such concerns" not in dead_output:
            raise AssertionError(f"Favor-pray-loop scenario missed the dead-state blocker: {dead_output}")
        print(json.dumps({
            "scenario": "favor-pray-loop",
            "favor_after_successes": 3,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        for obj in (character, opponent):
            if not obj:
                continue
            try:
                obj.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario(
    "favor-decay",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Moves stored favor across multiple decay intervals without depending on background tick scheduling.",
    },
)
def run_favor_decay_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_favor_decay")
    character = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_FAVOR_DECAY", location=room, home=room)
        character.ensure_core_defaults()
        character.set_favor(4)
        character.db.last_favor_decay_at = 1000.0
        with patch("typeclasses.characters.time.time", return_value=6401.0):
            favor_after = character.get_favor()
        if favor_after != 1:
            raise AssertionError(f"Favor-decay scenario did not decay to the floor of 1: {favor_after}")
        print(json.dumps({
            "scenario": "favor-decay",
            "favor_after": favor_after,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)


@register_scenario(
    "death-depart-keeps-favor",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates the simplified loop rule that depart keeps stored favor while revive is the spend path.",
    },
)
def run_death_depart_keeps_favor_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_depart_keeps_favor")
    safe_name, safe_room = _create_temp_room("diretest_depart_keeps_favor_safe")
    character = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_DEPART_KEEP_FAVOR", location=room, home=safe_room)
        character.ensure_core_defaults()
        character.set_favor(3)
        character.set_hp(0)
        corpse = character.get_death_corpse()
        if not corpse:
            raise AssertionError("Death-depart-keeps-favor scenario did not create a corpse.")
        snapshot = int(getattr(corpse.db, "favor_snapshot", 0) or 0)
        _run_depart_command(character)
        _run_depart_command(character, "confirm")
        if character.is_dead():
            raise AssertionError("Death-depart-keeps-favor scenario left the character dead after depart.")
        if character.get_favor() != 3:
            raise AssertionError(f"Death-depart-keeps-favor scenario spent favor on depart: {character.get_favor()}")
        if snapshot != 3:
            raise AssertionError(f"Death-depart-keeps-favor scenario stored the wrong favor snapshot: {snapshot}")
        print(json.dumps({
            "scenario": "death-depart-keeps-favor",
            "favor_after": character.get_favor(),
            "favor_snapshot": snapshot,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-creation",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates depart-driven grave creation, item transfer, and coin storage without relying on the older corpse decay flow.",
    },
)
def run_grave_creation_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_grave_creation")
    safe_name, safe_room = _create_temp_room("diretest_grave_creation_safe")
    character = None
    token = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_GRAVE_CREATION", location=room, home=safe_room)
        character.ensure_core_defaults()
        token = create_object("typeclasses.objects.Object", key="TEST_GRAVE_ITEM", location=character, home=character)
        token.db.weight = 1.0
        character.db.coins = 50
        character.set_favor(1)
        character.set_hp(0)
        _run_depart_command(character)
        _run_depart_command(character, "confirm")
        grave = next((obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(character.id or 0)), None)
        if not grave:
            raise AssertionError("Grave-creation scenario did not leave a grave behind.")
        if token.location != grave:
            raise AssertionError("Grave-creation scenario did not move the item into the grave.")
        if int(getattr(grave.db, "stored_coins", 0) or 0) >= 50:
            raise AssertionError("Grave-creation scenario did not apply any coin loss to the grave.")
        if int(getattr(character.db, "coins", 0) or 0) != 0:
            raise AssertionError("Grave-creation scenario left coins on the character after depart.")
        print(json.dumps({
            "scenario": "grave-creation",
            "grave_coins": int(getattr(grave.db, "stored_coins", 0) or 0),
            "grave_item_count": len(list(grave.contents)),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-recovery-direct",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Exercises the new depart-to-grave and recover loop end-to-end with the direct command path.",
    },
)
def run_grave_recovery_direct_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object
    from evennia.utils.search import search_object

    room_name, room = _create_temp_room("diretest_grave_recovery_direct")
    safe_name, safe_room = _create_temp_room("diretest_grave_recovery_direct_safe")
    character = None
    token = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_GRAVE_RECOVER", location=room, home=safe_room)
        character.ensure_core_defaults()
        token = create_object("typeclasses.objects.Object", key="TEST_GRAVE_RECOVER_ITEM", location=character, home=character)
        token.db.weight = 1.0
        character.db.coins = 40
        character.set_hp(0)
        _run_depart_command(character)
        _run_depart_command(character, "confirm")
        grave = next((obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(character.id or 0)), None)
        if not grave:
            raise AssertionError("Grave-recovery-direct scenario did not create a grave.")
        expected_coins = int(getattr(grave.db, "stored_coins", 0) or 0)
        character.move_to(room, quiet=True)
        _run_recover_command(character, grave.key)
        if token.location != character:
            raise AssertionError("Grave-recovery-direct scenario did not restore the grave item.")
        if int(getattr(character.db, "coins", 0) or 0) != expected_coins:
            raise AssertionError("Grave-recovery-direct scenario did not restore the grave coins.")
        if search_object(f"#{int(getattr(grave, 'id', 0) or 0)}"):
            raise AssertionError("Grave-recovery-direct scenario did not remove the emptied grave.")
        print(json.dumps({
            "scenario": "grave-recovery-direct",
            "recovered_coins": expected_coins,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-nonowner-blocked",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Confirms visible graves remain owner-only for retrieval.",
    },
)
def run_grave_nonowner_blocked_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_grave_blocked")
    safe_name, safe_room = _create_temp_room("diretest_grave_blocked_safe")
    owner = None
    intruder = None
    originals = {}
    try:
        owner = create_object("typeclasses.characters.Character", key="TEST_GRAVE_OWNER", location=room, home=safe_room)
        intruder = create_object("typeclasses.characters.Character", key="TEST_GRAVE_INTRUDER", location=room, home=room)
        owner.ensure_core_defaults()
        intruder.ensure_core_defaults()
        create_object("typeclasses.objects.Object", key="TEST_GRAVE_OWNER_ITEM", location=owner, home=owner).db.weight = 1.0
        owner.db.coins = 20
        owner.set_hp(0)
        _run_depart_command(owner)
        _run_depart_command(owner, "confirm")
        grave = next((obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(owner.id or 0)), None)
        if not grave:
            raise AssertionError("Grave-nonowner-blocked scenario did not create a grave.")
        captured, originals = _capture_object_messages(intruder)
        _run_recover_command(intruder, grave.key)
        output = "\n".join(captured.get(intruder) or [])
        if "permission" not in output.lower():
            raise AssertionError(f"Grave-nonowner-blocked scenario returned the wrong blocker message: {output}")
        if not list(grave.contents):
            raise AssertionError("Grave-nonowner-blocked scenario allowed the intruder to empty the grave.")
        print(json.dumps({
            "scenario": "grave-nonowner-blocked",
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        _restore_object_messages(originals)
        for obj in (owner, intruder):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-partial-recovery",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses weight pressure to confirm partial grave recovery leaves remainder behind.",
    },
)
def run_grave_partial_recovery_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_grave_partial")
    safe_name, safe_room = _create_temp_room("diretest_grave_partial_safe")
    character = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_GRAVE_PARTIAL", location=room, home=safe_room)
        character.ensure_core_defaults()
        for key in ("TEST_PARTIAL_ONE", "TEST_PARTIAL_TWO"):
            item = create_object("typeclasses.objects.Object", key=key, location=character, home=character)
            item.db.weight = 1.0
        character.set_hp(0)
        _run_depart_command(character)
        _run_depart_command(character, "confirm")
        grave = next((obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(character.id or 0)), None)
        if not grave:
            raise AssertionError("Grave-partial-recovery scenario did not create a grave.")
        filler = create_object("typeclasses.objects.Object", key="TEST_PARTIAL_FILLER", location=character, home=character)
        filler.db.weight = max(0.0, character.get_max_carry_weight() - 1.2)
        character.move_to(room, quiet=True)
        _run_recover_command(character, grave.key)
        tracked_keys = {"TEST_PARTIAL_ONE", "TEST_PARTIAL_TWO"}
        carried = sorted(item.key for item in list(character.contents) if str(getattr(item, "key", "")) in tracked_keys)
        remaining = sorted(item.key for item in list(grave.contents) if str(getattr(item, "key", "")) in tracked_keys)
        if len(carried) != 1 or len(remaining) != 1:
            raise AssertionError(f"Grave-partial-recovery scenario did not split the recovery as expected: carried={carried}, remaining={remaining}")
        print(json.dumps({
            "scenario": "grave-partial-recovery",
            "carried": carried,
            "remaining": remaining,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-loss-scaling",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Compares low favor, high favor, and severe sting departures to validate coin loss scaling.",
    },
)
def run_grave_loss_scaling_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_grave_loss_scaling")
    safe_name, safe_room = _create_temp_room("diretest_grave_loss_scaling_safe")
    low = None
    high = None
    severe = None
    try:
        low = create_object("typeclasses.characters.Character", key="TEST_GRAVE_LOW", location=room, home=safe_room)
        high = create_object("typeclasses.characters.Character", key="TEST_GRAVE_HIGH", location=room, home=safe_room)
        severe = create_object("typeclasses.characters.Character", key="TEST_GRAVE_SEVERE", location=room, home=safe_room)
        for obj in (low, high, severe):
            obj.ensure_core_defaults()
            obj.set_favor(0)
        high.set_favor(3)
        severe.db.death_sting = 4
        low_lost, low_coins = low.calculate_depart_coin_loss(100)
        _, high_coins = high.calculate_depart_coin_loss(100)
        _, severe_coins = severe.calculate_depart_coin_loss(100)
        if high_coins <= low_coins:
            raise AssertionError(f"Grave-loss-scaling scenario did not reduce loss for high favor: low={low_coins}, high={high_coins}")
        if severe_coins >= low_coins:
            raise AssertionError(f"Grave-loss-scaling scenario did not increase loss for severe sting: low={low_coins}, severe={severe_coins}")
        print(json.dumps({
            "scenario": "grave-loss-scaling",
            "low_lost": low_lost,
            "low_coins": low_coins,
            "high_favor_coins": high_coins,
            "severe_sting_coins": severe_coins,
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (low, high, severe):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-expiry",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Forces grave expiry through the direct helper so item loss remains deterministic in test.",
    },
)
def run_grave_expiry_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object
    from evennia.utils.search import search_object

    room_name, room = _create_temp_room("diretest_grave_expiry")
    safe_name, safe_room = _create_temp_room("diretest_grave_expiry_safe")
    character = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_GRAVE_EXPIRY", location=room, home=safe_room)
        character.ensure_core_defaults()
        item = create_object("typeclasses.objects.Object", key="TEST_GRAVE_EXPIRY_ITEM", location=character, home=character)
        item.db.weight = 1.0
        character.db.coins = 10
        character.set_hp(0)
        _run_depart_command(character)
        _run_depart_command(character, "confirm")
        grave = next((obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(character.id or 0)), None)
        if not grave:
            raise AssertionError("Grave-expiry scenario did not create a grave.")
        grave.process_expiry(now=float(getattr(grave.db, "expires_at", 0.0) or 0.0) + 1.0)
        if search_object(f"#{int(getattr(grave, 'id', 0) or 0)}"):
            raise AssertionError("Grave-expiry scenario did not remove the grave after expiry.")
        print(json.dumps({
            "scenario": "grave-expiry",
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-multiple",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Confirms the simpler multiple-graves policy by departing twice without recovery.",
    },
)
def run_grave_multiple_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_grave_multiple")
    safe_name, safe_room = _create_temp_room("diretest_grave_multiple_safe")
    character = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_GRAVE_MULTI", location=room, home=safe_room)
        character.ensure_core_defaults()
        for index in (1, 2):
            item = create_object("typeclasses.objects.Object", key=f"TEST_GRAVE_MULTI_{index}", location=character, home=character)
            item.db.weight = 1.0
            character.set_hp(0)
            _run_depart_command(character)
            _run_depart_command(character, "confirm")
            character.move_to(room, quiet=True)
        graves = [obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(character.id or 0)]
        if len(graves) != 2:
            raise AssertionError(f"Grave-multiple scenario expected two active graves, found {len(graves)}")
        print(json.dumps({
            "scenario": "grave-multiple",
            "grave_count": len(graves),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-revive-vs-depart",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Pairs a successful cleric revive with a depart to ensure only depart leaves a grave.",
    },
)
def run_grave_revive_vs_depart_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_grave_revive_vs_depart")
    safe_name, safe_room = _create_temp_room("diretest_grave_revive_vs_depart_safe")
    cleric = None
    revived = None
    departed = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()
    try:
        room.db.is_shrine = True
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_GRAVE_REVIVE_CLERIC", location=room, home=room)
        revived = create_object("typeclasses.characters.Character", key="TEST_GRAVE_REVIVED", location=room, home=safe_room)
        departed = create_object("typeclasses.characters.Character", key="TEST_GRAVE_DEPARTED", location=room, home=safe_room)
        for obj in (cleric, revived, departed):
            obj.ensure_core_defaults()
        cleric.set_profession("cleric")
        revived.set_favor(2)
        revived.set_hp(0)
        corpse = revived.get_death_corpse()
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))
        ok, message = cleric.start_cleric_revive(corpse)
        if not ok:
            raise AssertionError(message)
        _run_fake_delay_queue(scheduled)
        departed.set_hp(0)
        _run_depart_command(departed)
        _run_depart_command(departed, "confirm")
        revived_graves = [obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(revived.id or 0)]
        departed_graves = [obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(departed.id or 0)]
        if revived_graves:
            raise AssertionError("Grave-revive-vs-depart scenario incorrectly created a grave on successful revive.")
        if not departed_graves:
            raise AssertionError("Grave-revive-vs-depart scenario failed to create a grave on depart.")
        print(json.dumps({
            "scenario": "grave-revive-vs-depart",
            "depart_graves": len(departed_graves),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, revived, departed):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-reconnect-recovery",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Checks that a grave persists across reconnect and remains recoverable afterwards.",
    },
)
def run_grave_reconnect_recovery_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_grave_reconnect")
    safe_name, safe_room = _create_temp_room("diretest_grave_reconnect_safe")
    character = None
    try:
        character = create_object("typeclasses.characters.Character", key="TEST_GRAVE_RECONNECT", location=room, home=safe_room)
        character.ensure_core_defaults()
        item = create_object("typeclasses.objects.Object", key="TEST_GRAVE_RECONNECT_ITEM", location=character, home=character)
        item.db.weight = 1.0
        character.db.coins = 12
        character.set_hp(0)
        _run_depart_command(character)
        _run_depart_command(character, "confirm")
        grave = next((obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(character.id or 0)), None)
        if not grave:
            raise AssertionError("Grave-reconnect-recovery scenario did not create a grave.")
        character.at_post_puppet()
        character.move_to(room, quiet=True)
        _run_recover_command(character, grave.key)
        if item.location != character:
            raise AssertionError("Grave-reconnect-recovery scenario did not restore the item after reconnect.")
        print(json.dumps({
            "scenario": "grave-reconnect-recovery",
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)


@register_scenario(
    "grave-full-loop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Runs the simplified survival loop twice: pray, die, depart, recover, then repeat with a fresh grave.",
    },
)
def run_grave_full_loop_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_grave_full_loop")
    safe_name, safe_room = _create_temp_room("diretest_grave_full_loop_safe")
    shrine_name, shrine = _create_temp_room("diretest_grave_full_loop_shrine")
    character = None
    try:
        shrine.db.is_shrine = True
        character = create_object("typeclasses.characters.Character", key="TEST_GRAVE_FULL_LOOP", location=shrine, home=safe_room)
        character.ensure_core_defaults()
        with patch("typeclasses.characters.time.time", return_value=1000.0):
            _run_pray_command(character)
        if int(getattr(character.db, "favor_current", 0) or 0) < 2:
            raise AssertionError("Grave-full-loop scenario did not gain favor from prayer.")
        first_item = create_object("typeclasses.objects.Object", key="TEST_GRAVE_LOOP_ONE", location=character, home=character)
        first_item.db.weight = 1.0
        character.db.coins = 25
        character.move_to(room, quiet=True)
        character.set_hp(0)
        _run_depart_command(character)
        _run_depart_command(character, "confirm")
        first_grave = next((obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(character.id or 0)), None)
        if not first_grave:
            raise AssertionError("Grave-full-loop scenario did not create the first grave.")
        character.move_to(room, quiet=True)
        _run_recover_command(character, first_grave.key)
        second_item = create_object("typeclasses.objects.Object", key="TEST_GRAVE_LOOP_TWO", location=character, home=character)
        second_item.db.weight = 1.0
        character.db.coins = 18
        character.set_hp(0)
        _run_depart_command(character)
        _run_depart_command(character, "confirm")
        second_graves = [obj for obj in list(room.contents) if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(character.id or 0)]
        if len(second_graves) != 1:
            raise AssertionError(f"Grave-full-loop scenario expected one active grave after recovery and second death, found {len(second_graves)}")
        print(json.dumps({
            "scenario": "grave-full-loop",
            "favor_after_pray": int(getattr(character.db, "favor_current", 0) or 0),
            "active_graves": len(second_graves),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        if character:
            try:
                character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        _cleanup_named_object(safe_name)
        _cleanup_named_object(shrine_name)


@register_scenario(
    "cleric-revive-expired-corpse",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates revive rejection after the corpse memory/decay window has expired.",
    },
)
def run_cleric_revive_expired_corpse_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_expired_corpse")
    room.db.is_shrine = True
    cleric = None
    target = None
    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_EXPIRED_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_EXPIRED_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        if not corpse:
            raise AssertionError("Expired-corpse scenario did not create a corpse.")
        corpse.db.ritual_state = "bound"
        corpse.db.soul_bound = True
        corpse.db.memory_stable = True
        corpse.db.decay_time = time.time() - 1
        corpse.db.decay_end_time = corpse.db.decay_time
        corpse.db.memory_time = time.time() - 1
        corpse.db.memory_faded = True
        ok, message = cleric.start_cleric_revive(corpse)
        if ok:
            raise AssertionError("Expired-corpse scenario unexpectedly allowed revive startup.")
        expected = "The corpse's memory has faded beyond recall."
        if str(message or "") != expected:
            raise AssertionError(f"Expired-corpse scenario returned the wrong failure message: {message}")
        print(json.dumps({
            "scenario": "cleric-revive-expired-corpse",
            "decay_remaining": float(corpse.get_decay_remaining() if hasattr(corpse, "get_decay_remaining") else 0.0),
            "memory_remaining": float(corpse.get_memory_remaining() if hasattr(corpse, "get_memory_remaining") else 0.0),
            "message": str(message or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-revive-wrong-location",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates revive rejection outside shrine and consecrated rooms.",
    },
)
def run_cleric_revive_wrong_location_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_wrong_location")
    cleric = None
    target = None
    try:
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_WRONG_ROOM_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_WRONG_ROOM_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        if not corpse:
            raise AssertionError("Wrong-location scenario did not create a corpse.")
        corpse.db.ritual_state = "bound"
        corpse.db.soul_bound = True
        corpse.db.memory_stable = True
        ok, message = cleric.start_cleric_revive(corpse)
        if ok:
            raise AssertionError("Wrong-location scenario unexpectedly allowed revive startup.")
        expected = "You can only revive someone in a shrine or consecrated place."
        if str(message or "") != expected:
            raise AssertionError(f"Wrong-location scenario returned the wrong failure message: {message}")
        print(json.dumps({
            "scenario": "cleric-revive-wrong-location",
            "room_is_shrine": bool(getattr(room.db, "is_shrine", False)),
            "room_is_consecrated": bool(getattr(room.db, "consecrated", False)),
            "message": str(message or ""),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario(
    "cleric-revive-mid-delay-expiry",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Uses fake delayed callbacks to validate corpse invalidation during the revive delay.",
    },
)
def run_cleric_revive_mid_delay_expiry_scenario(args):
    _setup_django()

    import typeclasses.characters as character_module

    from evennia.utils.create import create_object

    room_name, room = _create_temp_room("diretest_cleric_mid_delay_expiry")
    room.db.is_shrine = True
    cleric = None
    target = None
    original_delay = character_module.delay
    scheduled, fake_delay = _build_fake_delay_queue()

    try:
        character_module.delay = fake_delay
        cleric = create_object("typeclasses.characters.Character", key="TEST_CLERIC_DELAY_EXPIRY_REVIVER", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key="TEST_CLERIC_DELAY_EXPIRY_TARGET", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        target.set_favor(2)
        target.set_hp(0)
        corpse = target.get_death_corpse()
        if not corpse:
            raise AssertionError("Mid-delay expiry scenario did not create a corpse.")
        _run_cleric_ritual_chain(cleric, corpse, scheduled, ("prepare", "stabilize", "restore", "bind"))
        ok, message = cleric.start_cleric_revive(corpse)
        if not ok:
            raise AssertionError(message)
        corpse.db.is_valid_for_revive = False
        corpse.db.irrecoverable = True
        if not scheduled:
            raise AssertionError("Mid-delay expiry scenario did not schedule a delayed revive.")
        while scheduled:
            event = scheduled.pop(0)
            event["callback"](*event["args"], **event["kwargs"])
        if not target.is_dead():
            raise AssertionError("Mid-delay expiry scenario revived the target even though the corpse invalidated during the delay.")
        if not target.get_death_corpse():
            raise AssertionError("Mid-delay expiry scenario lost the corpse link after a failed completion.")
        print(json.dumps({
            "scenario": "cleric-revive-mid-delay-expiry",
            "target_dead": bool(target.is_dead()),
            "corpse_valid": bool(getattr(corpse.db, "is_valid_for_revive", False)),
            "corpse_irrecoverable": bool(getattr(corpse.db, "irrecoverable", False)),
            "ok": True,
        }, indent=2, sort_keys=True))
        return 0
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass
        _cleanup_named_object(room_name)


@register_scenario("economy")
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

        if buy_diff["character_changes"]["coins_delta"] != -20:
            raise AssertionError(f"Economy buy diff did not spend the expected coins: {buy_diff}")
        if buy_diff["inventory_changes"]["added"] != ["study book"]:
            raise AssertionError(f"Economy buy diff did not add the purchased item: {buy_diff}")
        if buy_diff["room_changes"]["changed"]:
            raise AssertionError(f"Economy buy unexpectedly changed rooms: {buy_diff}")

        if sell_diff["character_changes"]["coins_delta"] != 15:
            raise AssertionError(f"Economy sell diff did not pay the expected vendor amount: {sell_diff}")
        if sell_diff["inventory_changes"]["removed"] != ["TEST_ECON_TRINKET"]:
            raise AssertionError(f"Economy sell diff did not remove the sold item: {sell_diff}")
        if sale_item.key not in sell_diff["object_delta_changes"]["deleted"]:
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

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="economy")


@register_scenario("bank")
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

        if deposit_diff["character_changes"]["coins_delta"] != -40 or deposit_diff["character_changes"]["bank_coins_delta"] != 40:
            raise AssertionError(f"Bank deposit diff did not move funds correctly: {deposit_diff}")
        if withdraw_diff["character_changes"]["coins_delta"] != 15 or withdraw_diff["character_changes"]["bank_coins_delta"] != -15:
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

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="bank")


@register_scenario(
    "grave-recovery",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Validates the depart-created grave and recovery loop through the older snapshot harness.",
    },
)
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
        _run_depart_command(character, "")
        _run_depart_command(character, "confirm")
        grave = character.get_owned_grave(location=room) if hasattr(character, "get_owned_grave") else None
        if not grave:
            raise AssertionError("Grave-recovery scenario did not create a grave on depart.")
        ctx.harness.track_object(grave)
        ctx.snapshot("departed")
        _run_recover_command(character, grave.key)
        ctx.snapshot("recovered")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["alive", "dead", "departed", "recovered"]
        if labels != expected_labels:
            raise AssertionError(f"Grave-recovery snapshot labels drifted: expected {expected_labels}, got {labels}")

        depart_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("dead"), ctx.get_snapshot_by_label("departed"))
        recover_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("departed"), ctx.get_snapshot_by_label("recovered"))

        if not depart_diff["character_changes"]["revived"]:
            raise AssertionError(f"Grave depart diff did not record revival: {depart_diff}")
        if depart_diff["inventory_changes"]["added"] or depart_diff["character_changes"]["coins_delta"] != 0:
            raise AssertionError(f"Grave depart unexpectedly restored belongings: {depart_diff}")
        if grave.key not in depart_diff["room_changes"]["contents_added"]:
            raise AssertionError(f"Grave depart diff did not record grave creation: {depart_diff}")

        if recover_diff["inventory_changes"]["added"] != ["TEST_GRAVE_TOKEN"]:
            raise AssertionError(f"Grave recover diff did not restore the grave item: {recover_diff}")
        if recover_diff["character_changes"]["coins_delta"] <= 0:
            raise AssertionError(f"Grave recover diff did not restore grave coins: {recover_diff}")
        if grave.key not in recover_diff["object_delta_changes"]["deleted"]:
            raise AssertionError(f"Grave recover diff did not record grave cleanup: {recover_diff}")

        if character.is_dead():
            raise AssertionError("Grave-recovery scenario ended with the character still dead.")
        if int(getattr(character.db, "coins", 0) or 0) <= 0:
            raise AssertionError("Grave-recovery scenario ended without recovered grave coins.")
        if keepsake.location != character:
            raise AssertionError("Grave-recovery scenario ended without the grave item restored to the character.")

        return {
            "commands": list(ctx.command_log),
            "depart_diff": depart_diff,
            "recover_diff": recover_diff,
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "output_log": list(ctx.output_log),
            "grave_key": getattr(grave, "key", None),
            "coins": int(getattr(character.db, "coins", 0) or 0),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="grave-recovery",
        scenario_metadata=getattr(run_grave_recovery_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "trap-expiry",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural trap-expiry scheduling validation should report lag without failing on environment-specific latency.",
    },
)
def run_trap_expiry_scenario(args):
    _setup_django()

    def scenario(ctx):
        from evennia.objects.models import ObjectDB

        from world.systems.scheduler import flush_due, get_scheduler_snapshot

        room = ctx.harness.create_test_room(key="TEST_TRAP_ROOM")
        character = ctx.harness.create_test_character(room=room, key="TEST_TRAP_CHAR")
        device = ctx.harness.create_test_object(
            key="TEST_TRAP_DEVICE",
            location=character,
            typeclass="typeclasses.trap_device.TrapDevice",
        )

        ctx.character = character
        ctx.room = room
        ctx.harness.track_object(device)

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        ctx.snapshot("carried")
        device.db.expire_time = 0.1
        ctx.direct(character.deploy_trap)
        if device.location != room:
            raise AssertionError("Trap-expiry scenario did not deploy the trap into the room.")
        ctx.snapshot("deployed")

        scheduler_snapshot = get_scheduler_snapshot() or {}
        active_jobs = list(scheduler_snapshot.get("active_jobs", []) or [])
        trap_key = device._get_expiry_schedule_key() if hasattr(device, "_get_expiry_schedule_key") else None
        if not any(job.get("key") == trap_key and job.get("system") == "world.trap_expiry" for job in active_jobs):
            raise AssertionError(f"Trap-expiry scenario did not register trap scheduler metadata: {scheduler_snapshot}")

        deleted = False
        for _ in range(5):
            time.sleep(0.15)
            ctx.direct(flush_due)
            if not ObjectDB.objects.filter(id=int(getattr(device, "id", 0) or 0)).exists():
                deleted = True
                break
        if not deleted:
            raise AssertionError("Trap-expiry scenario did not delete the trap via scheduler expiry.")
        ctx.snapshot("expired")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["carried", "deployed", "expired"]
        if labels != expected_labels:
            raise AssertionError(f"Trap-expiry snapshot labels drifted: expected {expected_labels}, got {labels}")

        expire_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("deployed"), ctx.get_snapshot_by_label("expired"))
        if device.key not in expire_diff["object_delta_changes"]["deleted"]:
            raise AssertionError(f"Trap-expiry diff did not record trap deletion: {expire_diff}")

        return {
            "commands": list(ctx.command_log),
            "expire_diff": expire_diff,
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "output_log": list(ctx.output_log),
            "trap_key": trap_key,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="trap-expiry",
        scenario_metadata=getattr(run_trap_expiry_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "ticker-execution",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural shared-ticker execution validation should report lag without failing on environment-specific latency.",
    },
)
def run_ticker_execution_scenario(args):
    _setup_django()

    def scenario(ctx):
        from server.conf.at_server_startstop import process_learning_tick
        from world.systems.metrics import snapshot_metrics
        from world.systems.timing_audit import collect_timing_audit, register_ticker_metadata

        room = ctx.harness.create_test_room(key="TEST_TICKER_ROOM")
        character = ctx.harness.create_test_character(room=room, key="TEST_TICKER_CHAR")

        ctx.character = character
        ctx.room = room

        ctx.assert_invariant("character_exists")
        ctx.assert_invariant("valid_room_state")

        character.ensure_skill_defaults()
        skills = dict(character.db.skills or {})
        athletics = dict(skills.get("athletics", {}) or {})
        athletics["rank"] = max(1, int(athletics.get("rank", 1) or 1))
        athletics["mindstate"] = 20
        skills["athletics"] = athletics
        character.db.skills = skills

        register_ticker_metadata(
            10,
            process_learning_tick,
            idstring="global_learning_tick",
            persistent=True,
            system="world.learning_tick",
            reason="Frequency-separated learning and teaching pulse processing.",
        )

        before_skill = dict((character.db.skills or {}).get("athletics", {}) or {})
        ctx.snapshot("before")
        ctx.direct(process_learning_tick)
        ctx.snapshot("after")

        after_skill = dict((character.db.skills or {}).get("athletics", {}) or {})

        runtime_metrics = dict(snapshot_metrics() or {})
        ticker_stats = dict((runtime_metrics.get("events", {}) or {}).get("ticker.execute", {}) or {})
        ticker_entries = list(ticker_stats.get("entries", []) or [])
        if not any(str(((entry or {}).get("metadata", {}) or {}).get("ticker", "") or "") == "process_learning_tick" for entry in ticker_entries):
            raise AssertionError(f"Ticker-execution scenario did not record ticker.execute for process_learning_tick: {runtime_metrics}")

        audit_payload = dict(collect_timing_audit() or {})
        ticker_payload = dict(audit_payload.get("tickers", {}) or {})
        performance = dict((ticker_payload.get("performance", {}) or {}).get("process_learning_tick", {}) or {})
        if int(performance.get("count", 0) or 0) <= 0:
            raise AssertionError(f"Ticker-execution scenario did not surface per-ticker performance: {audit_payload}")
        registrations = list(ticker_payload.get("registered_tickers", []) or [])
        if not any(
            str((record or {}).get("idstring", "") or "") == "global_learning_tick"
            and str((record or {}).get("system", "") or "") == "world.learning_tick"
            for record in registrations
        ):
            raise AssertionError(f"Ticker-execution scenario did not surface learning ticker registration metadata: {audit_payload}")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["before", "after"]
        if labels != expected_labels:
            raise AssertionError(f"Ticker-execution snapshot labels drifted: expected {expected_labels}, got {labels}")

        return {
            "commands": list(ctx.command_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": labels,
            "output_log": list(ctx.output_log),
            "before_skill": before_skill,
            "after_skill": after_skill,
            "learning_state_changed": before_skill != after_skill,
            "ticker_performance": performance,
            "registered_ticker_count": int(ticker_payload.get("registered_ticker_count", 0) or 0),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="ticker-execution",
        scenario_metadata=getattr(run_ticker_execution_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-renew-benchmark",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Interest activation benchmark should report timing deltas without failing on environment-specific latency.",
    },
)
def run_interest_renew_benchmark_scenario(args):
    _setup_django()

    def scenario(ctx):
        return _run_interest_renew_dual_mode_benchmark(ctx)

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-renew-benchmark",
        scenario_metadata=getattr(run_interest_renew_benchmark_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-dual-mode-compare",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Dual-mode activation comparison should report timing deltas without failing on environment-specific latency.",
    },
)
def run_interest_dual_mode_compare_scenario(args):
    _setup_django()

    def scenario(ctx):
        payload = dict(_run_interest_renew_dual_mode_benchmark(ctx) or {})
        benchmark = dict(payload.get("benchmark", {}) or {})
        return {
            **payload,
            "comparison": {
                "correctness": {
                    "legacy_target_count": _safe_int(benchmark.get("legacy_target_count", 0), 0),
                    "scoped_target_count": _safe_int(benchmark.get("scoped_target_count", 0), 0),
                    "target_delta": _safe_int(benchmark.get("target_delta", 0), 0),
                },
                "timing": {
                    "legacy_select_ms": _safe_float(benchmark.get("legacy_select_ms", 0.0), 0.0),
                    "scoped_select_ms": _safe_float(benchmark.get("scoped_select_ms", 0.0), 0.0),
                    "selection_delta_ms": _safe_float(benchmark.get("selection_delta_ms", 0.0), 0.0),
                    "legacy_command_ms": _safe_float(benchmark.get("legacy_command_ms", 0.0), 0.0),
                    "scoped_command_ms": _safe_float(benchmark.get("scoped_command_ms", 0.0), 0.0),
                    "command_delta_ms": _safe_float(benchmark.get("command_delta_ms", 0.0), 0.0),
                },
                "performance": {
                    "legacy_scanned_count": _safe_int(benchmark.get("legacy_scanned_count", 0), 0),
                    "scoped_scanned_count": _safe_int(benchmark.get("scoped_scanned_count", 0), 0),
                    "interest_active_object_peak": _safe_int(benchmark.get("interest_active_object_peak", 0), 0),
                    "interest_source_count_peak": _safe_int(benchmark.get("interest_source_count_peak", 0), 0),
                },
            },
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-dual-mode-compare",
        scenario_metadata=getattr(run_interest_dual_mode_compare_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-zone-activation",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural zone-activation validation should report lag without failing on environment-specific latency.",
    },
)
def run_interest_zone_activation_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.engine_flags import set_flag
        from world.systems.interest import clear_subject_interest, get_activation_sources, get_zone_rooms, is_active, sync_subject_interest

        zone_a = ctx.harness.create_test_room(key="TEST_ZONE_A")
        zone_b = ctx.harness.create_test_room(key="TEST_ZONE_B")
        other_zone = ctx.harness.create_test_room(key="TEST_ZONE_OTHER")
        for room in (zone_a, zone_b):
            room.tags.add("test-zone-alpha", category="build")
        other_zone.tags.add("test-zone-beta", category="build")

        caller = ctx.harness.create_test_character(room=zone_a, key="TEST_ZONE_CALLER")
        zone_obj = ctx.harness.create_test_object(key="TEST_ZONE_OBJ", location=zone_b)
        outside_obj = ctx.harness.create_test_object(key="TEST_ZONE_OUTSIDE", location=other_zone)

        ctx.character = caller
        ctx.room = zone_a

        set_flag("interest_activation", True, actor="diretest-zone")
        sync_subject_interest(caller)

        zone_rooms = [getattr(room, "key", None) for room in get_zone_rooms(zone_a)]
        if sorted(zone_rooms) != ["TEST_ZONE_A", "TEST_ZONE_B"]:
            raise AssertionError(f"Zone activation resolved the wrong rooms: {zone_rooms}")
        if not is_active(zone_obj):
            raise AssertionError("Zone activation did not activate objects in the same build zone.")
        if is_active(outside_obj):
            raise AssertionError("Zone activation leaked into an unrelated zone.")

        zone_sources = [entry for entry in get_activation_sources(zone_obj) if str(entry.get("type", "") or "") == "zone"]
        if not zone_sources:
            raise AssertionError("Zone activation did not register a zone source on the zone object.")

        clear_subject_interest(caller)
        if is_active(zone_obj):
            raise AssertionError("Zone cleanup did not remove zone interest from the zone object.")

        set_flag("interest_activation", False, actor="diretest-zone")
        return {
            "commands": list(ctx.command_log),
            "zone_rooms": zone_rooms,
            "zone_source_count": len(zone_sources),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-zone-activation",
        scenario_metadata=getattr(run_interest_zone_activation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-activation-metrics",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural activation-metrics validation should report lag without failing on environment-specific latency.",
    },
)
def run_interest_activation_metrics_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.engine_flags import set_flag
        from world.systems.interest import clear_subject_interest, get_activation_sources, is_active, sync_subject_interest
        from world.systems.metrics import snapshot_metrics

        room = ctx.harness.create_test_room(key="TEST_INTEREST_METRICS_ROOM")
        caller = ctx.harness.create_test_character(room=room, key="TEST_INTEREST_METRICS_CALLER")
        target = ctx.harness.create_test_character(room=room, key="TEST_INTEREST_METRICS_TARGET")

        ctx.character = caller
        ctx.room = room

        set_flag("interest_activation", True, actor="diretest-interest-metrics")

        sync_subject_interest(caller)
        caller.set_target(target)
        caller.set_roundtime(0.5)

        runtime_metrics = dict(snapshot_metrics() or {})
        counters = dict((runtime_metrics.get("counters", {}) or {}))
        gauges = dict((runtime_metrics.get("gauges", {}) or {}))
        if int(gauges.get("interest.active_object_count", 0) or 0) <= 0:
            raise AssertionError(f"Activation metrics did not record any active objects: {runtime_metrics}")
        if int(gauges.get("interest.active_object_peak", 0) or 0) <= 0:
            raise AssertionError(f"Activation metrics did not record the active-object peak: {runtime_metrics}")
        if int(gauges.get("interest.source.current.room", 0) or 0) <= 0:
            raise AssertionError(f"Activation metrics did not record room sources: {runtime_metrics}")
        if int(gauges.get("interest.source.current.direct", 0) or 0) <= 0:
            raise AssertionError(f"Activation metrics did not record direct sources: {runtime_metrics}")
        if int(gauges.get("interest.source.current.scheduled", 0) or 0) != 1:
            raise AssertionError(f"Activation metrics did not record exactly one scheduled source: {runtime_metrics}")
        if int(counters.get("interest.transition.activate", 0) or 0) <= 0:
            raise AssertionError(f"Activation metrics did not record activate transitions: {runtime_metrics}")
        if int(counters.get("interest.source.add.room", 0) or 0) <= 0:
            raise AssertionError(f"Activation metrics did not record room source additions: {runtime_metrics}")
        if int(counters.get("interest.source.add.direct", 0) or 0) <= 0:
            raise AssertionError(f"Activation metrics did not record direct source additions: {runtime_metrics}")
        if int(counters.get("interest.source.add.scheduled", 0) or 0) != 1:
            raise AssertionError(f"Activation metrics did not record the scheduled source addition: {runtime_metrics}")

        caller.set_target(None)
        caller.set_roundtime(0.0)
        clear_subject_interest(caller)
        clear_subject_interest(target)

        runtime_metrics_after_cleanup = dict(snapshot_metrics() or {})
        cleanup_counters = dict((runtime_metrics_after_cleanup.get("counters", {}) or {}))
        cleanup_gauges = dict((runtime_metrics_after_cleanup.get("gauges", {}) or {}))
        if is_active(caller):
            raise AssertionError(f"Activation metrics scenario did not fully deactivate the caller: {get_activation_sources(caller)}")
        if int(cleanup_counters.get("interest.transition.deactivate", 0) or 0) <= 0:
            raise AssertionError(f"Activation metrics did not record deactivate transitions: {runtime_metrics_after_cleanup}")
        if int(cleanup_gauges.get("interest.active_object_count", 0) or 0) != 0:
            raise AssertionError(
                f"Activation metrics did not return active-object count to zero after cleanup: {runtime_metrics_after_cleanup}"
            )

        set_flag("interest_activation", False, actor="diretest-interest-metrics")
        return {
            "commands": list(ctx.command_log),
            "active_object_peak": int(gauges.get("interest.active_object_peak", 0) or 0),
            "source_count_peak": int(gauges.get("interest.source_count.peak", 0) or 0),
            "room_source_count": int(gauges.get("interest.source.current.room", 0) or 0),
            "direct_source_count": int(gauges.get("interest.source.current.direct", 0) or 0),
            "scheduled_source_count": int(gauges.get("interest.source.current.scheduled", 0) or 0),
            "activate_count": int(counters.get("interest.transition.activate", 0) or 0),
            "deactivate_count": int(cleanup_counters.get("interest.transition.deactivate", 0) or 0),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-activation-metrics",
        scenario_metadata=getattr(run_interest_activation_metrics_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-debug-command",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural interest-debug command validation should report lag without failing on environment-specific latency.",
    },
)
def run_interest_debug_command_scenario(args):
    _setup_django()

    def scenario(ctx):
        from commands.cmd_engine import CmdEngine
        from world.systems.engine_flags import set_flag
        from world.systems.interest import clear_subject_interest, sync_subject_interest

        room = ctx.harness.create_test_room(key="TEST_INTEREST_DEBUG_ROOM")
        caller = ctx.harness.create_test_character(room=room, key="TEST_INTEREST_DEBUG_CALLER")
        target = ctx.harness.create_test_character(room=room, key="TEST_INTEREST_DEBUG_TARGET")

        ctx.character = caller
        ctx.room = room

        set_flag("interest_activation", True, actor="diretest-interest-debug")
        clear_subject_interest(caller)
        clear_subject_interest(target)
        sync_subject_interest(caller)
        caller.set_target(target)
        caller.set_roundtime(0.5)

        def run_interest_debug_command():
            command = CmdEngine()
            command.caller = caller
            command.args = "interest debug"
            command._is_admin = lambda: True
            command.func()

        ctx.direct(run_interest_debug_command)
        output_text = "\n".join(list(ctx.output_log or []))
        expected_fragments = [
            "Interest Debug",
            "interest_activation: ON",
            "source types:",
            "room: current=",
            "direct: current=",
            "scheduled: current=",
            "active object details:",
            "TEST_INTEREST_DEBUG_CALLER",
            "TEST_INTEREST_DEBUG_TARGET",
        ]
        for fragment in expected_fragments:
            if fragment not in output_text:
                raise AssertionError(f"Interest debug command output missing '{fragment}': {output_text}")

        caller.set_target(None)
        caller.set_roundtime(0.0)
        clear_subject_interest(caller)
        clear_subject_interest(target)
        set_flag("interest_activation", False, actor="diretest-interest-debug")
        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "output_line_count": len(list(ctx.output_log or [])),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-debug-command",
        scenario_metadata=getattr(run_interest_debug_command_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-direct-activation",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural direct-target activation validation should report lag without failing on environment-specific latency.",
    },
)
def run_interest_direct_activation_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.engine_flags import set_flag
        from world.systems.interest import clear_direct_interest, direct_interest, get_activation_sources, is_active

        room = ctx.harness.create_test_room(key="TEST_DIRECT_ROOM")
        caller = ctx.harness.create_test_character(room=room, key="TEST_DIRECT_CALLER")
        combat_target = ctx.harness.create_test_character(room=room, key="TEST_DIRECT_TARGET")
        aim_target = ctx.harness.create_test_character(room=room, key="TEST_DIRECT_AIM_TARGET")
        spell_target = ctx.harness.create_test_character(room=room, key="TEST_DIRECT_SPELL_TARGET")
        caller.has_ranged_weapon_equipped = lambda: True

        ctx.character = caller
        ctx.room = room

        set_flag("interest_activation", True, actor="diretest-direct")

        caller.set_target(combat_target)
        combat_sources = [entry for entry in get_activation_sources(combat_target) if str(entry.get("type", "") or "") == "direct"]
        if not is_active(combat_target) or not combat_sources:
            raise AssertionError("Direct activation did not attach to the combat target.")

        aim_ok, _ = caller.build_ranger_aim(aim_target)
        if not aim_ok:
            raise AssertionError("Direct activation scenario could not establish ranger aim state.")
        aim_sources = [entry for entry in get_activation_sources(aim_target) if str(entry.get("type", "") or "") == "direct"]
        if not is_active(aim_target) or not aim_sources:
            raise AssertionError("Direct activation did not attach to the aim target.")

        caller.clear_aim()
        if any(str(entry.get("source", "") or "").startswith("direct:TEST_DIRECT_CALLER:aim") for entry in get_activation_sources(aim_target)):
            raise AssertionError("Direct activation did not clear aim interest.")

        with direct_interest(caller, [spell_target], channel="spell"):
            spell_sources_during = [entry for entry in get_activation_sources(spell_target) if str(entry.get("type", "") or "") == "direct"]
            if not spell_sources_during:
                raise AssertionError("Direct activation did not attach temporary spell interest.")
        if any(str(entry.get("source", "") or "").startswith("direct:TEST_DIRECT_CALLER:spell") for entry in get_activation_sources(spell_target)):
            raise AssertionError("Direct activation did not clear temporary spell interest.")

        caller.set_target(None)
        if any(str(entry.get("source", "") or "").startswith("direct:TEST_DIRECT_CALLER:combat") for entry in get_activation_sources(combat_target)):
            raise AssertionError("Direct activation did not clear combat interest.")

        clear_direct_interest(caller, channel="spell")
        set_flag("interest_activation", False, actor="diretest-direct")
        return {
            "commands": list(ctx.command_log),
            "combat_direct_source_count": len(combat_sources),
            "aim_direct_source_count": len(aim_sources),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-direct-activation",
        scenario_metadata=getattr(run_interest_direct_activation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-scheduled-activation",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural scheduled-activation validation should report lag without failing on environment-specific latency.",
    },
)
def run_interest_scheduled_activation_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.engine_flags import set_flag
        from world.systems.interest import get_activation_sources, is_active
        from world.systems.scheduler import flush_due, get_scheduler_snapshot

        room = ctx.harness.create_test_room(key="TEST_SCHEDULED_ROOM")
        caller = ctx.harness.create_test_character(room=room, key="TEST_SCHEDULED_CALLER")

        ctx.character = caller
        ctx.room = room

        set_flag("interest_activation", True, actor="diretest-scheduled")

        initial_scheduled_sources = [entry for entry in get_activation_sources(caller) if str(entry.get("type", "") or "") == "scheduled"]
        if initial_scheduled_sources:
            raise AssertionError(f"Scheduled activation scenario started with unexpected scheduled sources: {initial_scheduled_sources}")

        caller.set_roundtime(0.1)
        scheduled_sources = [entry for entry in get_activation_sources(caller) if str(entry.get("type", "") or "") == "scheduled"]
        if not is_active(caller) or len(scheduled_sources) != 1:
            raise AssertionError("Scheduled activation did not attach a scheduled source to the pending roundtime job.")

        scheduler_snapshot = get_scheduler_snapshot() or {}
        active_jobs = list(scheduler_snapshot.get("active_jobs", []) or [])
        scheduled_job = next((job for job in active_jobs if job.get("key") == caller._get_roundtime_schedule_key()), None)
        if not scheduled_job:
            raise AssertionError(f"Scheduled activation did not expose the roundtime job in scheduler snapshot: {scheduler_snapshot}")
        if scheduled_job.get("interest_object_key") != f"#{int(caller.id)}":
            raise AssertionError(f"Scheduled activation did not record the owning object on the scheduler job: {scheduled_job}")

        time.sleep(0.15)
        ctx.direct(flush_due)
        remaining_sources_after_flush = [entry for entry in get_activation_sources(caller) if str(entry.get("type", "") or "") == "scheduled"]
        if remaining_sources_after_flush:
            raise AssertionError("Scheduled activation did not clear scheduled interest after job completion.")

        caller.set_roundtime(1.0)
        cancel_sources = [entry for entry in get_activation_sources(caller) if str(entry.get("type", "") or "") == "scheduled"]
        if len(cancel_sources) != 1:
            raise AssertionError("Scheduled activation did not reattach scheduled interest for the second pending job.")

        caller.set_roundtime(0.0)
        remaining_sources_after_cancel = [entry for entry in get_activation_sources(caller) if str(entry.get("type", "") or "") == "scheduled"]
        if remaining_sources_after_cancel:
            raise AssertionError("Scheduled activation did not clear scheduled interest after cancellation.")

        set_flag("interest_activation", False, actor="diretest-scheduled")
        return {
            "commands": list(ctx.command_log),
            "scheduled_source_count": len(scheduled_sources),
            "scheduler_job_key": scheduled_job.get("key"),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-scheduled-activation",
        scenario_metadata=getattr(run_interest_scheduled_activation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-scheduler-respects-activation",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural scheduler activation-gate validation should report lag without failing on environment-specific latency.",
    },
)
def run_interest_scheduler_respects_activation_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.engine_flags import set_flag
        from world.systems.interest import clear_subject_interest, get_activation_sources, is_active, remove_scheduled_interest
        from world.systems.metrics import snapshot_metrics
        from world.systems.scheduler import flush_due, get_scheduler_snapshot, schedule
        from world.systems.time_model import SCHEDULED_EXPIRY

        room = ctx.harness.create_test_room(key="TEST_SCHED_GATE_ROOM")
        caller = ctx.harness.create_test_character(room=room, key="TEST_SCHED_GATE_CALLER")

        ctx.character = caller
        ctx.room = room

        set_flag("interest_activation", True, actor="diretest-scheduler-gate")
        clear_subject_interest(caller)

        callback_hits = []
        schedule_key = f"diretest:scheduler-gate:{int(caller.id)}"

        def _mark_executed():
            callback_hits.append("executed")

        schedule(
            0.1,
            _mark_executed,
            key=schedule_key,
            system="diretest.scheduler_gate",
            timing_mode=SCHEDULED_EXPIRY,
            keep_active_obj=caller,
            inactive_policy="skip",
        )

        if not is_active(caller):
            raise AssertionError("Scheduler gate scenario did not activate the caller while the job was pending.")

        remove_scheduled_interest(caller, schedule_key=schedule_key, system="diretest.scheduler_gate")
        if is_active(caller):
            raise AssertionError(
                f"Scheduler gate scenario did not make the caller inactive before execution: {get_activation_sources(caller)}"
            )

        time.sleep(0.15)
        ctx.direct(flush_due)

        if callback_hits:
            raise AssertionError("Scheduler activation gate did not suppress execution for an inactive owner.")

        scheduler_snapshot = get_scheduler_snapshot() or {}
        if int(scheduler_snapshot.get("active_job_count", 0) or 0) != 0:
            raise AssertionError(f"Scheduler activation gate left the skipped job in the queue: {scheduler_snapshot}")

        runtime_metrics = dict(snapshot_metrics() or {})
        counters = dict((runtime_metrics.get("counters", {}) or {}))
        skip_entries = list(dict((runtime_metrics.get("events", {}) or {}).get("scheduler.skip", {}) or {}).get("entries", []) or [])
        if int(counters.get("scheduler.skip.inactive", 0) or 0) <= 0:
            raise AssertionError(f"Scheduler activation gate did not record an inactive skip counter: {runtime_metrics}")
        if not any(str(((entry or {}).get("metadata", {}) or {}).get("key", "") or "") == schedule_key for entry in skip_entries):
            raise AssertionError(f"Scheduler activation gate did not record the skipped job metadata: {runtime_metrics}")

        set_flag("interest_activation", False, actor="diretest-scheduler-gate")
        return {
            "commands": list(ctx.command_log),
            "skip_count": int(counters.get("scheduler.skip", 0) or 0),
            "skip_reason_count": int(counters.get("scheduler.skip.inactive", 0) or 0),
            "scheduler_job_key": schedule_key,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-scheduler-respects-activation",
        scenario_metadata=getattr(run_interest_scheduler_respects_activation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-scheduler-safe-skip",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Structural scheduler defer validation should report lag without failing on environment-specific latency.",
    },
)
def run_interest_scheduler_safe_skip_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.engine_flags import set_flag
        from world.systems.interest import clear_subject_interest, is_active, remove_scheduled_interest
        from world.systems.metrics import snapshot_metrics
        from world.systems.scheduler import flush_due, get_scheduler_snapshot, schedule
        from world.systems.time_model import SCHEDULED_EXPIRY

        room = ctx.harness.create_test_room(key="TEST_SCHED_DEFER_ROOM")
        caller = ctx.harness.create_test_character(room=room, key="TEST_SCHED_DEFER_CALLER")

        ctx.character = caller
        ctx.room = room

        set_flag("interest_activation", True, actor="diretest-scheduler-defer")
        clear_subject_interest(caller)

        callback_hits = []
        schedule_key = f"diretest:scheduler-defer:{int(caller.id)}"

        def _mark_executed():
            callback_hits.append("executed")

        schedule(
            0.1,
            _mark_executed,
            key=schedule_key,
            system="diretest.scheduler_defer",
            timing_mode=SCHEDULED_EXPIRY,
            keep_active_obj=caller,
            inactive_policy="defer",
            inactive_defer_delay=0.1,
            max_inactive_defers=2,
        )

        remove_scheduled_interest(caller, schedule_key=schedule_key, system="diretest.scheduler_defer")
        if is_active(caller):
            raise AssertionError("Scheduler defer scenario did not isolate the caller before the first flush.")

        time.sleep(0.15)
        ctx.direct(flush_due)
        if callback_hits:
            raise AssertionError("Scheduler defer scenario executed too early instead of deferring.")

        deferred_snapshot = get_scheduler_snapshot() or {}
        deferred_jobs = list(deferred_snapshot.get("active_jobs", []) or [])
        deferred_job = next((job for job in deferred_jobs if job.get("key") == schedule_key), None)
        if not deferred_job:
            raise AssertionError(f"Scheduler defer scenario did not retain the deferred job: {deferred_snapshot}")
        if str(deferred_job.get("inactive_policy", "") or "") != "defer":
            raise AssertionError(f"Scheduler defer scenario lost the inactive policy metadata: {deferred_job}")
        if int(deferred_job.get("inactive_defer_count", 0) or 0) != 1:
            raise AssertionError(f"Scheduler defer scenario did not increment defer count on the retained job: {deferred_job}")
        if not is_active(caller):
            raise AssertionError("Scheduler defer scenario did not reactivate the caller after deferring the job.")

        time.sleep(0.15)
        ctx.direct(flush_due)
        if callback_hits != ["executed"]:
            raise AssertionError(f"Scheduler defer scenario did not re-execute the callback safely: {callback_hits}")

        final_snapshot = get_scheduler_snapshot() or {}
        if int(final_snapshot.get("active_job_count", 0) or 0) != 0:
            raise AssertionError(f"Scheduler defer scenario left the deferred job queued after execution: {final_snapshot}")

        runtime_metrics = dict(snapshot_metrics() or {})
        counters = dict((runtime_metrics.get("counters", {}) or {}))
        defer_entries = list(dict((runtime_metrics.get("events", {}) or {}).get("scheduler.defer", {}) or {}).get("entries", []) or [])
        if int(counters.get("scheduler.defer", 0) or 0) != 1:
            raise AssertionError(f"Scheduler defer scenario did not record exactly one defer: {runtime_metrics}")
        if not any(str(((entry or {}).get("metadata", {}) or {}).get("key", "") or "") == schedule_key for entry in defer_entries):
            raise AssertionError(f"Scheduler defer scenario did not record defer metadata for the retained job: {runtime_metrics}")

        set_flag("interest_activation", False, actor="diretest-scheduler-defer")
        return {
            "commands": list(ctx.command_log),
            "defer_count": int(counters.get("scheduler.defer", 0) or 0),
            "scheduler_job_key": schedule_key,
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-scheduler-safe-skip",
        scenario_metadata=getattr(run_interest_scheduler_safe_skip_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-scheduler-stress",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Scheduler stress validation is structural and should surface lag without failing on environment-specific latency.",
    },
)
def run_interest_scheduler_stress_scenario(args):
    _setup_django()

    def scenario(ctx):
        import world.systems.scheduler as scheduler_module

        from world.systems.metrics import snapshot_metrics
        from world.systems.scheduler import cancel, flush_due, get_scheduler_snapshot, schedule

        total_jobs = 24
        key_prefix = "diretest:scheduler-stress"
        system_name = "diretest.scheduler_stress"
        system_metric_key = "scheduler.queue.system.diretest_scheduler_stress"
        callback_hits = []
        scheduled_keys = []
        owner_limit = scheduler_module.MAX_JOBS_PER_OWNER
        system_limit = scheduler_module.MAX_JOBS_PER_SYSTEM
        total_limit = scheduler_module.MAX_TOTAL_JOBS

        try:
            scheduler_module.MAX_JOBS_PER_OWNER = max(int(owner_limit or 0), total_jobs)
            scheduler_module.MAX_JOBS_PER_SYSTEM = max(int(system_limit or 0), total_jobs)
            scheduler_module.MAX_TOTAL_JOBS = max(int(total_limit or 0), total_jobs)

            for index in range(total_jobs):
                key = f"{key_prefix}:{index}"
                scheduled_keys.append(key)
                schedule(
                    0,
                    lambda job_index=index: callback_hits.append(job_index),
                    key=key,
                    owner=f"owner:{index}",
                    system=system_name,
                )

            queued_snapshot = get_scheduler_snapshot() or {}
            queued_jobs = [job for job in list(queued_snapshot.get("active_jobs", []) or []) if str(job.get("key", "") or "").startswith(key_prefix)]
            if len(queued_jobs) != total_jobs:
                raise AssertionError(f"Scheduler stress scenario queued an unexpected job count: {queued_snapshot}")
            if int((queued_snapshot.get("by_system", {}) or {}).get(system_name, 0) or 0) != total_jobs:
                raise AssertionError(f"Scheduler stress scenario did not expose by-system counts: {queued_snapshot}")

            queued_metrics = dict(snapshot_metrics() or {})
            queued_gauges = dict((queued_metrics.get("gauges", {}) or {}))
            if int(queued_gauges.get("scheduler.queue.current", 0) or 0) != total_jobs:
                raise AssertionError(f"Scheduler stress scenario did not update queue depth metrics: {queued_metrics}")
            if int(queued_gauges.get(system_metric_key, 0) or 0) != total_jobs:
                raise AssertionError(f"Scheduler stress scenario did not update system queue gauges: {queued_metrics}")

            executed = ctx.direct(flush_due)
            if int(executed or 0) != total_jobs:
                raise AssertionError(f"Scheduler stress scenario executed {executed} jobs instead of {total_jobs}.")
            if sorted(callback_hits) != list(range(total_jobs)):
                raise AssertionError(f"Scheduler stress scenario lost callbacks under load: {callback_hits}")

            final_snapshot = get_scheduler_snapshot() or {}
            if any(str(job.get("key", "") or "").startswith(key_prefix) for job in list(final_snapshot.get("active_jobs", []) or [])):
                raise AssertionError(f"Scheduler stress scenario left jobs queued after flush: {final_snapshot}")

            runtime_metrics = dict(snapshot_metrics() or {})
            counters = dict((runtime_metrics.get("counters", {}) or {}))
            gauges = dict((runtime_metrics.get("gauges", {}) or {}))
            if int(counters.get("scheduler.execute", 0) or 0) != total_jobs:
                raise AssertionError(f"Scheduler stress scenario did not record execute counters correctly: {runtime_metrics}")
            if int(gauges.get("scheduler.queue.peak", 0) or 0) < total_jobs:
                raise AssertionError(f"Scheduler stress scenario did not record queue peak metrics: {runtime_metrics}")
            if int(gauges.get("scheduler.queue.current", 0) or 0) != 0:
                raise AssertionError(f"Scheduler stress scenario did not drain the queue metrics: {runtime_metrics}")
            if int(gauges.get(system_metric_key, 0) or 0) != 0:
                raise AssertionError(f"Scheduler stress scenario did not clear the system gauge after flush: {runtime_metrics}")

            return {
                "commands": list(ctx.command_log),
                "total_jobs": total_jobs,
                "executed_jobs": int(counters.get("scheduler.execute", 0) or 0),
                "queue_peak": int(gauges.get("scheduler.queue.peak", 0) or 0),
                "output_log": list(ctx.output_log),
            }
        finally:
            for key in scheduled_keys:
                cancel(key)
            scheduler_module.MAX_JOBS_PER_OWNER = owner_limit
            scheduler_module.MAX_JOBS_PER_SYSTEM = system_limit
            scheduler_module.MAX_TOTAL_JOBS = total_limit

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-scheduler-stress",
        scenario_metadata=getattr(run_interest_scheduler_stress_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-scheduler-duplicate-key",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Duplicate-key scheduler validation is structural and should not fail on environment-specific latency.",
    },
)
def run_interest_scheduler_duplicate_key_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.metrics import snapshot_metrics
        from world.systems.scheduler import cancel, flush_due, get_scheduler_snapshot, schedule

        key_prefix = "diretest:scheduler-duplicate"
        replace_key = f"{key_prefix}:replace"
        reject_key = f"{key_prefix}:reject"
        callback_hits = []

        try:
            schedule(0, lambda: callback_hits.append("first"), key=replace_key, owner="owner:replace", system="diretest.scheduler_duplicate")
            schedule(0, lambda: callback_hits.append("second"), key=replace_key, owner="owner:replace", system="diretest.scheduler_duplicate")

            replace_snapshot = get_scheduler_snapshot() or {}
            replace_jobs = [job for job in list(replace_snapshot.get("active_jobs", []) or []) if str(job.get("key", "") or "") == replace_key]
            if len(replace_jobs) != 1:
                raise AssertionError(f"Duplicate-key replace path left an unexpected queue state: {replace_snapshot}")

            executed_replace = ctx.direct(flush_due)
            if int(executed_replace or 0) != 1 or callback_hits != ["second"]:
                raise AssertionError(f"Duplicate-key replace path did not preserve only the latest job: {callback_hits}")

            schedule(0, lambda: callback_hits.append("keep"), key=reject_key, owner="owner:reject", system="diretest.scheduler_duplicate")
            rejected_job = schedule(
                0,
                lambda: callback_hits.append("reject"),
                key=reject_key,
                owner="owner:reject",
                system="diretest.scheduler_duplicate",
                key_conflict="reject",
            )
            if rejected_job is not None:
                raise AssertionError("Duplicate-key reject path returned a scheduled job instead of rejecting it.")

            reject_snapshot = get_scheduler_snapshot() or {}
            reject_jobs = [job for job in list(reject_snapshot.get("active_jobs", []) or []) if str(job.get("key", "") or "") == reject_key]
            if len(reject_jobs) != 1:
                raise AssertionError(f"Duplicate-key reject path corrupted the queue state: {reject_snapshot}")

            executed_reject = ctx.direct(flush_due)
            if int(executed_reject or 0) != 1 or callback_hits != ["second", "keep"]:
                raise AssertionError(f"Duplicate-key reject path executed the wrong callback set: {callback_hits}")

            runtime_metrics = dict(snapshot_metrics() or {})
            counters = dict((runtime_metrics.get("counters", {}) or {}))
            reject_entries = list(dict((runtime_metrics.get("events", {}) or {}).get("scheduler.reject", {}) or {}).get("entries", []) or [])
            if int(counters.get("scheduler.reject.duplicate-key", 0) or 0) != 1:
                raise AssertionError(f"Duplicate-key scenario did not record the reject counter: {runtime_metrics}")
            if not any(str(((entry or {}).get("metadata", {}) or {}).get("reason", "") or "") == "duplicate-key" for entry in reject_entries):
                raise AssertionError(f"Duplicate-key scenario did not record reject metadata: {runtime_metrics}")

            return {
                "commands": list(ctx.command_log),
                "executed_jobs": int(counters.get("scheduler.execute", 0) or 0),
                "duplicate_rejections": int(counters.get("scheduler.reject.duplicate-key", 0) or 0),
                "output_log": list(ctx.output_log),
            }
        finally:
            cancel(replace_key)
            cancel(reject_key)

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-scheduler-duplicate-key",
        scenario_metadata=getattr(run_interest_scheduler_duplicate_key_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-scheduler-quota-violation",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Quota enforcement validation is structural and should not fail on environment-specific latency.",
    },
)
def run_interest_scheduler_quota_violation_scenario(args):
    _setup_django()

    def scenario(ctx):
        import world.systems.scheduler as scheduler_module

        from world.systems.metrics import snapshot_metrics
        from world.systems.scheduler import cancel, flush_due, get_scheduler_snapshot, schedule

        key_prefix = "diretest:scheduler-quota"
        owner_limit = scheduler_module.MAX_JOBS_PER_OWNER
        system_limit = scheduler_module.MAX_JOBS_PER_SYSTEM
        total_limit = scheduler_module.MAX_TOTAL_JOBS
        owner_behavior = scheduler_module.OWNER_QUOTA_BEHAVIOR
        system_behavior = scheduler_module.SYSTEM_QUOTA_BEHAVIOR
        global_behavior = scheduler_module.GLOBAL_QUOTA_BEHAVIOR
        scheduled_keys = []

        def _assert_reject_entry(entries, reason, scope, limit):
            for entry in entries:
                metadata = dict(((entry or {}).get("metadata", {}) or {}))
                if str(metadata.get("reason", "") or "") != reason:
                    continue
                if str(metadata.get("quota_scope", "") or "") != scope:
                    continue
                if int(metadata.get("quota_limit", 0) or 0) != limit:
                    continue
                return True
            return False

        try:
            scheduler_module.OWNER_QUOTA_BEHAVIOR = "reject"
            scheduler_module.SYSTEM_QUOTA_BEHAVIOR = "reject"
            scheduler_module.GLOBAL_QUOTA_BEHAVIOR = "reject"
            scheduler_module.MAX_JOBS_PER_OWNER = 1
            scheduler_module.MAX_JOBS_PER_SYSTEM = 2
            scheduler_module.MAX_TOTAL_JOBS = 10

            owner_key = f"{key_prefix}:owner:1"
            owner_reject_key = f"{key_prefix}:owner:2"
            system_key = f"{key_prefix}:system:1"
            system_reject_key = f"{key_prefix}:system:2"
            scheduled_keys.extend([owner_key, owner_reject_key, system_key, system_reject_key])

            schedule(5, lambda: None, key=owner_key, owner="owner:quota-a", system="diretest.scheduler_quota")
            owner_reject = schedule(5, lambda: None, key=owner_reject_key, owner="owner:quota-a", system="diretest.scheduler_quota")
            schedule(5, lambda: None, key=system_key, owner="owner:quota-b", system="diretest.scheduler_quota")
            system_reject = schedule(5, lambda: None, key=system_reject_key, owner="owner:quota-c", system="diretest.scheduler_quota")

            if owner_reject is not None or system_reject is not None:
                raise AssertionError("Quota scenario failed to reject owner or system overflow.")

            owner_system_snapshot = get_scheduler_snapshot() or {}
            owner_system_jobs = [
                job for job in list(owner_system_snapshot.get("active_jobs", []) or []) if str(job.get("key", "") or "").startswith(key_prefix)
            ]
            if len(owner_system_jobs) != 2:
                raise AssertionError(f"Quota scenario retained an unexpected job count after owner/system rejections: {owner_system_snapshot}")

            cancel(owner_key)
            cancel(system_key)

            scheduler_module.MAX_JOBS_PER_OWNER = 10
            scheduler_module.MAX_JOBS_PER_SYSTEM = 10
            scheduler_module.MAX_TOTAL_JOBS = 2

            global_key_a = f"{key_prefix}:global:1"
            global_key_b = f"{key_prefix}:global:2"
            global_key_c = f"{key_prefix}:global:3"
            scheduled_keys.extend([global_key_a, global_key_b, global_key_c])

            schedule(5, lambda: None, key=global_key_a, owner="owner:global-a", system="diretest.scheduler_quota_a")
            schedule(5, lambda: None, key=global_key_b, owner="owner:global-b", system="diretest.scheduler_quota_b")
            global_reject = schedule(5, lambda: None, key=global_key_c, owner="owner:global-c", system="diretest.scheduler_quota_c")
            if global_reject is not None:
                raise AssertionError("Quota scenario failed to reject global queue overflow.")

            global_snapshot = get_scheduler_snapshot() or {}
            global_jobs = [
                job for job in list(global_snapshot.get("active_jobs", []) or []) if str(job.get("key", "") or "").startswith(key_prefix)
            ]
            if len(global_jobs) != 2:
                raise AssertionError(f"Quota scenario retained an unexpected job count after global rejection: {global_snapshot}")

            runtime_metrics = dict(snapshot_metrics() or {})
            counters = dict((runtime_metrics.get("counters", {}) or {}))
            reject_entries = list(dict((runtime_metrics.get("events", {}) or {}).get("scheduler.reject", {}) or {}).get("entries", []) or [])
            if int(counters.get("scheduler.reject.owner-quota", 0) or 0) != 1:
                raise AssertionError(f"Quota scenario did not record the owner quota rejection: {runtime_metrics}")
            if int(counters.get("scheduler.reject.system-quota", 0) or 0) != 1:
                raise AssertionError(f"Quota scenario did not record the system quota rejection: {runtime_metrics}")
            if int(counters.get("scheduler.reject.global-quota", 0) or 0) != 1:
                raise AssertionError(f"Quota scenario did not record the global quota rejection: {runtime_metrics}")
            if not _assert_reject_entry(reject_entries, "owner-quota", "owner", 1):
                raise AssertionError(f"Quota scenario did not preserve owner quota metadata on reject events: {runtime_metrics}")
            if not _assert_reject_entry(reject_entries, "system-quota", "system", 2):
                raise AssertionError(f"Quota scenario did not preserve system quota metadata on reject events: {runtime_metrics}")
            if not _assert_reject_entry(reject_entries, "global-quota", "global", 2):
                raise AssertionError(f"Quota scenario did not preserve global quota metadata on reject events: {runtime_metrics}")

            replace_oldest_key_a = f"{key_prefix}:replace:1"
            replace_oldest_key_b = f"{key_prefix}:replace:2"
            replace_oldest_key_c = f"{key_prefix}:replace:3"
            scheduled_keys.extend([replace_oldest_key_a, replace_oldest_key_b, replace_oldest_key_c])

            cancel(global_key_a)
            cancel(global_key_b)

            scheduler_module.OWNER_QUOTA_BEHAVIOR = "replace_oldest"
            scheduler_module.SYSTEM_QUOTA_BEHAVIOR = "reject"
            scheduler_module.GLOBAL_QUOTA_BEHAVIOR = "reject"
            scheduler_module.MAX_JOBS_PER_OWNER = 2
            scheduler_module.MAX_JOBS_PER_SYSTEM = 10
            scheduler_module.MAX_TOTAL_JOBS = 10

            replace_hits = []
            schedule(5, lambda: replace_hits.append("oldest"), key=replace_oldest_key_a, owner="owner:replace", system="diretest.scheduler_replace")
            schedule(5, lambda: replace_hits.append("middle"), key=replace_oldest_key_b, owner="owner:replace", system="diretest.scheduler_replace")
            replacement_job = schedule(
                0,
                lambda: replace_hits.append("newest"),
                key=replace_oldest_key_c,
                owner="owner:replace",
                system="diretest.scheduler_replace",
            )
            if replacement_job is None:
                raise AssertionError("Quota scenario did not admit the replacement job when owner replace_oldest was enabled.")

            replacement_snapshot = get_scheduler_snapshot() or {}
            replacement_jobs = [
                job for job in list(replacement_snapshot.get("active_jobs", []) or []) if str(job.get("key", "") or "").startswith(f"{key_prefix}:replace:")
            ]
            replacement_keys = sorted(str(job.get("key", "") or "") for job in replacement_jobs)
            expected_replacement_keys = sorted([replace_oldest_key_b, replace_oldest_key_c])
            if replacement_keys != expected_replacement_keys:
                raise AssertionError(f"Quota scenario did not evict the oldest owner job during replacement: {replacement_snapshot}")

            ctx.direct(scheduler_module.flush_due)
            if replace_hits != ["newest"]:
                raise AssertionError(f"Quota scenario did not execute the replacement job correctly: {replace_hits}")

            runtime_metrics = dict(snapshot_metrics() or {})
            counters = dict((runtime_metrics.get("counters", {}) or {}))
            replace_entries = list(dict((runtime_metrics.get("events", {}) or {}).get("scheduler.replace", {}) or {}).get("entries", []) or [])
            if int(counters.get("scheduler.replace.owner-quota", 0) or 0) != 1:
                raise AssertionError(f"Quota scenario did not record the owner replacement counter: {runtime_metrics}")
            if not any(
                str(((entry or {}).get("metadata", {}) or {}).get("evicted_key", "") or "") == replace_oldest_key_a
                and str(((entry or {}).get("metadata", {}) or {}).get("new_key", "") or "") == replace_oldest_key_c
                for entry in replace_entries
            ):
                raise AssertionError(f"Quota scenario did not record replacement metadata: {runtime_metrics}")

            delay_key_a = f"{key_prefix}:delay:1"
            delay_key_b = f"{key_prefix}:delay:2"
            scheduled_keys.extend([delay_key_a, delay_key_b])

            cancel(replace_oldest_key_b)
            cancel(replace_oldest_key_c)

            scheduler_module.OWNER_QUOTA_BEHAVIOR = "delay"
            scheduler_module.SYSTEM_QUOTA_BEHAVIOR = "reject"
            scheduler_module.GLOBAL_QUOTA_BEHAVIOR = "reject"
            scheduler_module.MAX_JOBS_PER_OWNER = 1
            scheduler_module.MAX_JOBS_PER_SYSTEM = 10
            scheduler_module.MAX_TOTAL_JOBS = 10

            delay_hits = []
            schedule(5, lambda: delay_hits.append("blocking"), key=delay_key_a, owner="owner:delay", system="diretest.scheduler_delay")
            delayed_job = schedule(
                0,
                lambda: delay_hits.append("delayed"),
                key=delay_key_b,
                owner="owner:delay",
                system="diretest.scheduler_delay",
            )
            if delayed_job is not None:
                raise AssertionError("Quota scenario should not admit the overflow job immediately when delay backpressure is enabled.")

            delayed_snapshot = get_scheduler_snapshot() or {}
            delayed_jobs = [
                job for job in list(delayed_snapshot.get("delayed_jobs", []) or []) if str(job.get("key", "") or "").startswith(f"{key_prefix}:delay:")
            ]
            if len(delayed_jobs) != 1 or str(delayed_jobs[0].get("key", "") or "") != delay_key_b:
                raise AssertionError(f"Quota scenario did not retain the overflow job in the delayed queue: {delayed_snapshot}")
            if int(delayed_snapshot.get("delayed_job_count", 0) or 0) != 1:
                raise AssertionError(f"Quota scenario did not expose delayed queue counts: {delayed_snapshot}")

            cancel(delay_key_a)
            time.sleep(0.3)
            ctx.direct(flush_due)

            if delay_hits != ["delayed"]:
                raise AssertionError(f"Quota scenario did not drain and execute the delayed job after capacity returned: {delay_hits}")

            runtime_metrics = dict(snapshot_metrics() or {})
            counters = dict((runtime_metrics.get("counters", {}) or {}))
            delay_entries = list(dict((runtime_metrics.get("events", {}) or {}).get("scheduler.delay", {}) or {}).get("entries", []) or [])
            if int(counters.get("scheduler.delay.owner-quota", 0) or 0) != 1:
                raise AssertionError(f"Quota scenario did not record the owner delay counter: {runtime_metrics}")
            if int(counters.get("scheduler.delay.execute", 0) or 0) != 1:
                raise AssertionError(f"Quota scenario did not record delayed retry execution: {runtime_metrics}")
            if not any(
                str(((entry or {}).get("metadata", {}) or {}).get("key", "") or "") == delay_key_b
                and str(((entry or {}).get("metadata", {}) or {}).get("quota_behavior", "") or "") == "delay"
                for entry in delay_entries
            ):
                raise AssertionError(f"Quota scenario did not record delayed queue metadata: {runtime_metrics}")

            return {
                "commands": list(ctx.command_log),
                "owner_quota_rejections": int(counters.get("scheduler.reject.owner-quota", 0) or 0),
                "system_quota_rejections": int(counters.get("scheduler.reject.system-quota", 0) or 0),
                "global_quota_rejections": int(counters.get("scheduler.reject.global-quota", 0) or 0),
                "owner_quota_replacements": int(counters.get("scheduler.replace.owner-quota", 0) or 0),
                "owner_quota_delays": int(counters.get("scheduler.delay.owner-quota", 0) or 0),
                "output_log": list(ctx.output_log),
            }
        finally:
            for key in scheduled_keys:
                cancel(key)
            scheduler_module.MAX_JOBS_PER_OWNER = owner_limit
            scheduler_module.MAX_JOBS_PER_SYSTEM = system_limit
            scheduler_module.MAX_TOTAL_JOBS = total_limit
            scheduler_module.OWNER_QUOTA_BEHAVIOR = owner_behavior
            scheduler_module.SYSTEM_QUOTA_BEHAVIOR = system_behavior
            scheduler_module.GLOBAL_QUOTA_BEHAVIOR = global_behavior

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-scheduler-quota-violation",
        scenario_metadata=getattr(run_interest_scheduler_quota_violation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "interest-scheduler-queue-stability",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Queue stability validation is structural and should not fail on environment-specific latency.",
    },
)
def run_interest_scheduler_queue_stability_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.metrics import snapshot_metrics
        from world.systems.scheduler import cancel, flush_due, get_scheduler_snapshot, schedule

        cycles = 12
        jobs_per_cycle = 3
        key_prefix = "diretest:scheduler-stability"
        system_name = "diretest.scheduler_stability"
        system_metric_key = "scheduler.queue.system.diretest_scheduler_stability"
        callback_hits = []
        scheduled_keys = []

        try:
            for cycle in range(cycles):
                cycle_keys = []
                for slot in range(jobs_per_cycle):
                    key = f"{key_prefix}:{cycle}:{slot}"
                    cycle_keys.append(key)
                    scheduled_keys.append(key)
                    schedule(
                        0,
                        lambda cycle_index=cycle, slot_index=slot: callback_hits.append((cycle_index, slot_index)),
                        key=key,
                        owner=f"owner:stability:{slot}",
                        system=system_name,
                    )

                queued_snapshot = get_scheduler_snapshot() or {}
                queued_jobs = [
                    job for job in list(queued_snapshot.get("active_jobs", []) or []) if str(job.get("key", "") or "") in cycle_keys
                ]
                if len(queued_jobs) != jobs_per_cycle:
                    raise AssertionError(f"Queue stability scenario queued an unexpected cycle size: {queued_snapshot}")

                executed = ctx.direct(flush_due)
                if int(executed or 0) != jobs_per_cycle:
                    raise AssertionError(f"Queue stability scenario executed {executed} jobs instead of {jobs_per_cycle} in cycle {cycle}.")

                cycle_snapshot = get_scheduler_snapshot() or {}
                lingering_jobs = [
                    job for job in list(cycle_snapshot.get("active_jobs", []) or []) if str(job.get("key", "") or "") in cycle_keys
                ]
                if lingering_jobs:
                    raise AssertionError(f"Queue stability scenario leaked jobs after cycle {cycle}: {cycle_snapshot}")

            expected_jobs = cycles * jobs_per_cycle
            if len(callback_hits) != expected_jobs:
                raise AssertionError(f"Queue stability scenario lost callbacks across cycles: {callback_hits}")

            runtime_metrics = dict(snapshot_metrics() or {})
            counters = dict((runtime_metrics.get("counters", {}) or {}))
            gauges = dict((runtime_metrics.get("gauges", {}) or {}))
            if int(counters.get("scheduler.schedule", 0) or 0) != expected_jobs:
                raise AssertionError(f"Queue stability scenario did not record schedule counters correctly: {runtime_metrics}")
            if int(counters.get("scheduler.execute", 0) or 0) != expected_jobs:
                raise AssertionError(f"Queue stability scenario did not record execute counters correctly: {runtime_metrics}")
            if int(gauges.get("scheduler.queue.current", 0) or 0) != 0:
                raise AssertionError(f"Queue stability scenario left the current queue gauge non-zero: {runtime_metrics}")
            if int(gauges.get("scheduler.queue.peak", 0) or 0) > jobs_per_cycle:
                raise AssertionError(f"Queue stability scenario exceeded the expected bounded queue peak: {runtime_metrics}")
            if int(gauges.get(system_metric_key, 0) or 0) != 0:
                raise AssertionError(f"Queue stability scenario left the per-system gauge non-zero: {runtime_metrics}")

            final_snapshot = get_scheduler_snapshot() or {}
            if int(final_snapshot.get("active_job_count", 0) or 0) != 0:
                raise AssertionError(f"Queue stability scenario left the scheduler non-empty at the end: {final_snapshot}")
            if int((final_snapshot.get("by_system", {}) or {}).get(system_name, 0) or 0) != 0:
                raise AssertionError(f"Queue stability scenario left residual by-system counts: {final_snapshot}")

            return {
                "commands": list(ctx.command_log),
                "cycles": cycles,
                "jobs_per_cycle": jobs_per_cycle,
                "executed_jobs": int(counters.get("scheduler.execute", 0) or 0),
                "queue_peak": int(gauges.get("scheduler.queue.peak", 0) or 0),
                "output_log": list(ctx.output_log),
            }
        finally:
            for key in scheduled_keys:
                cancel(key)

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="interest-scheduler-queue-stability",
        scenario_metadata=getattr(run_interest_scheduler_queue_stability_scenario, "diretest_metadata", {}),
    )


@register_scenario("onboarding_lag")
def run_onboarding_lag_scenario(args):
    _setup_django()

    def scenario(ctx):
        from evennia.objects.models import ObjectDB
        from evennia.utils.create import create_object

        from systems import onboarding

        def ensure_tutorial_room(room_name):
            for candidate in ObjectDB.objects.filter(db_key__iexact=room_name):
                if getattr(getattr(candidate, "db", None), "is_tutorial", False):
                    return candidate
            room = create_object("typeclasses.rooms.Room", key=room_name, nohome=True)
            room.db.is_tutorial = True
            ctx.harness.track_object(room)
            return room

        rooms = {room_name: ensure_tutorial_room(room_name) for room_name in ONBOARDING_ROOM_NAMES}
        character = create_object("typeclasses.characters.Character", key="TEST_ONBOARD_LAG_CHAR", location=rooms["Intake Hall"], home=rooms["Intake Hall"])
        ctx.harness.track_object(character)
        character.db.onboarding_state = onboarding._default_state()
        character.db.gender = None
        character.db.race = "human"
        character.db.injuries = {
            "left_arm": {"bleed": 2, "external": 6, "internal": 0, "bruise": 0, "max": 100, "vital": False, "tended": False, "tend": {}},
            "head": {"bleed": 0, "external": 0, "internal": 0, "bruise": 0, "max": 100, "vital": True, "tended": False, "tend": {}},
            "chest": {"bleed": 0, "external": 0, "internal": 0, "bruise": 0, "max": 100, "vital": True, "tended": False, "tend": {}},
        }
        character.db.coins = 50

        ctx.character = character
        ctx.room = rooms["Intake Hall"]

        results = []

        gender_ok, gender_message = ctx.direct(onboarding.set_gender, character, "male")
        ctx.snapshot("post_gender")
        results.append({"step": "gender", "ok": gender_ok, "message": gender_message})

        ctx.direct(character.move_to, rooms["Lineup Platform"], quiet=True, use_destination=False)
        ctx.room = rooms["Lineup Platform"]
        race_ok, race_message = ctx.direct(onboarding.select_race, character, "human")
        ctx.snapshot("post_race")
        results.append({"step": "race", "ok": race_ok, "message": race_message})

        ctx.direct(character.move_to, rooms["Mirror Alcove"], quiet=True, use_destination=False)
        ctx.room = rooms["Mirror Alcove"]
        mirror_ok = True
        mirror_message = "configured tutorial appearance"
        for trait, value in {"hair style": "short", "hair color": "brown", "build": "average", "height": "average", "eyes": "gray"}.items():
            step_ok, step_message = ctx.direct(onboarding.set_trait, character, trait, value)
            mirror_ok = mirror_ok and bool(step_ok)
            mirror_message = step_message
        ctx.snapshot("post_mirror")
        results.append({"step": "mirror", "ok": mirror_ok, "message": mirror_message})

        ctx.direct(character.move_to, rooms["Gear Rack Room"], quiet=True, use_destination=False)
        ctx.room = rooms["Gear Rack Room"]
        shirt = create_object("typeclasses.wearables.Wearable", key="TEST_ONBOARD_LAG_SHIRT", location=character, home=character)
        shirt.db.slot = "torso"
        shirt.db.weight = 1.0
        boots = create_object("typeclasses.wearables.Wearable", key="TEST_ONBOARD_LAG_BOOTS", location=character, home=character)
        boots.db.slot = "feet"
        boots.db.weight = 1.5
        ctx.harness.track_object(shirt)
        ctx.harness.track_object(boots)
        ctx.direct(character.equip_item, shirt)
        ctx.direct(character.equip_item, boots)
        ctx.direct(character.move_to, rooms["Weapon Cage"], quiet=True, use_destination=False)
        ctx.room = rooms["Weapon Cage"]
        weapon = create_object("typeclasses.objects.Object", key="TEST_ONBOARD_LAG_SWORD", location=character, home=character)
        weapon.db.item_type = "weapon"
        weapon.db.weight = 3.0
        ctx.harness.track_object(weapon)
        weapon_ok, weapon_message = ctx.direct(onboarding.note_weapon_action, character, weapon)
        ctx.snapshot("post_weapon")
        results.append({"step": "weapon", "ok": weapon_ok, "message": weapon_message})

        ctx.direct(character.move_to, rooms["Training Yard"], quiet=True, use_destination=False)
        ctx.room = rooms["Training Yard"]
        goblin = create_object("typeclasses.npcs.NPC", key="TEST_ONBOARD_LAG_GOBLIN", location=rooms["Training Yard"], home=rooms["Training Yard"])
        goblin.db.is_npc = True
        goblin.db.is_tutorial_enemy = True
        goblin.db.onboarding_enemy_role = "training"
        goblin.db.hp = 0
        ctx.harness.track_object(goblin)
        ctx.direct(onboarding.note_combat_start, character, goblin)
        combat_ok, combat_message = ctx.direct(onboarding.note_combat_win, character, goblin)
        ctx.snapshot("post_combat")
        results.append({"step": "combat", "ok": combat_ok, "message": combat_message})

        ctx.direct(character.move_to, rooms["Vendor Stall"], quiet=True, use_destination=False)
        ctx.room = rooms["Vendor Stall"]
        buy_ok, _ = ctx.direct(onboarding.note_trade_action, character, "buy")
        sell_ok, vendor_message = ctx.direct(onboarding.note_trade_action, character, "sell")
        ctx.snapshot("post_vendor")
        results.append({"step": "vendor", "ok": bool(buy_ok and sell_ok), "message": vendor_message})

        state = onboarding.ensure_onboarding_state(character)
        return {
            "commands": list(ctx.command_log),
            "results": results,
            "completed_steps": list(state.get("completed_steps") or []),
            "token_count": int(state.get("tokens", 0) or 0),
            "output_log": list(ctx.output_log),
            "snapshot_count": len(ctx.snapshots),
            "snapshot_labels": ctx.get_snapshot_labels(),
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="onboarding_lag")


@register_scenario("onboarding_full")
def run_onboarding_full_scenario(args):
    output = _build_onboarding_full_output(args)
    _emit_onboarding_output(output, as_json=bool(getattr(args, "json", False)))
    return 0 if output["all_valid"] else 1


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


@register_scenario("onboarding_no_armor")
def run_onboarding_no_armor_scenario(args):
    return _run_onboarding_failure_case(args, "no_armor")


@register_scenario("onboarding_no_attack")
def run_onboarding_no_attack_scenario(args):
    return _run_onboarding_failure_case(args, "no_attack")


@register_scenario("onboarding_no_heal")
def run_onboarding_no_heal_scenario(args):
    return _run_onboarding_failure_case(args, "no_heal")


def _get_locked_onboarding_room(ObjectDB, room_name):
    for room in ObjectDB.objects.filter(db_key__iexact=room_name):
        if bool(getattr(getattr(room, "db", None), "is_onboarding", False)):
            return room
    return None


def _build_locked_onboarding_character(create_object, onboarding):
    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial

    _ensure_new_player_tutorial()
    intake = _get_locked_onboarding_room(ObjectDB, "Intake Chamber")
    training = _get_locked_onboarding_room(ObjectDB, "Training Hall")
    practice = _get_locked_onboarding_room(ObjectDB, "Practice Yard")
    if not intake or not training or not practice:
        raise RuntimeError("Locked onboarding rooms are missing.")

    character = create_object(
        "typeclasses.characters.Character",
        key=f"DireTest Onboarding {int(time.time() * 1000)}",
        location=intake,
        home=intake,
    )
    onboarding.activate_onboarding(character)
    onboarding.handle_room_entry(character)

    sword = ObjectDB.objects.filter(db_key__iexact="training sword", db_location=training).first()
    vest = ObjectDB.objects.filter(db_key__iexact="training vest", db_location=training).first()
    dummy = ObjectDB.objects.filter(db_key__iexact="training dummy", db_location=practice).first()
    if not sword or not vest or not dummy:
        character.delete()
        raise RuntimeError("Locked onboarding training objects are missing.")

    return {
        "character": character,
        "intake": intake,
        "training": training,
        "practice": practice,
        "sword": sword,
        "vest": vest,
        "dummy": dummy,
    }


def _expected_recovery_room_key(onboarding):
    destination = onboarding._resolve_recovery_destination() if hasattr(onboarding, "_resolve_recovery_destination") else None
    if destination:
        return getattr(destination, "key", None)
    return getattr(onboarding, "EMPATH_GUILD_ROOM", None)


def _build_chargen_mirror_character(create_object):
    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from systems.chargen import mirror as chargen_mirror

    _ensure_new_player_tutorial()
    intake = _get_locked_onboarding_room(ObjectDB, "Intake Chamber")
    if not intake:
        raise RuntimeError("Intake Chamber is missing.")

    mirror = ObjectDB.objects.filter(db_key__iexact=chargen_mirror.MIRROR_KEY, db_location=intake).first()
    if not mirror:
        raise RuntimeError("Chargen mirror is missing from Intake Chamber.")

    character = create_object(
        "typeclasses.characters.Character",
        key=f"DireTest Mirror {int(time.time() * 1000)}",
        location=intake,
        home=intake,
    )
    chargen_mirror.initialize_chargen_character(character)
    captured, originals = _capture_object_messages(character)
    chargen_mirror.emit_step_prompt(character, force=True)
    return {
        "character": character,
        "intake": intake,
        "mirror": mirror,
        "captured": captured,
        "originals": originals,
    }


def _run_chargen_mirror_case(args, case_name):
    _setup_django()

    from systems import onboarding
    from systems.chargen import mirror as chargen_mirror

    created_character = None
    extra_characters = []
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        ctx = _build_chargen_mirror_character(create_object)
        character = ctx["character"]
        created_character = character
        mirror = ctx["mirror"]
        captured = ctx["captured"]
        originals = ctx["originals"]

        ok = False
        detail = ""

        if case_name == "cycle":
            captured[character].clear()
            steps = len(chargen_mirror.STEP_OPTIONS["race"])
            for _ in range(steps):
                character.execute_cmd("touch mirror")
            messages = "\n".join(captured.get(character) or [])
            ok = (
                getattr(character.db, "chargen_step", None) == "race"
                and int(getattr(character.db, "chargen_index", 0)) == 0
                and dict(getattr(character.db, "chargen_selections", {}) or {}).get("race") == chargen_mirror.STEP_OPTIONS["race"][0]
                and "It waits. Not for approval, but for interruption." in messages
            )
            detail = messages or f"index={getattr(character.db, 'chargen_index', None)}"
        elif case_name == "actions-visible":
            appearance = ctx["intake"].return_appearance(character)
            observer = create_object(
                "typeclasses.characters.Character",
                key=f"DireTest Mirror Observer {int(time.time() * 1000)}",
                location=ctx["intake"],
                home=ctx["intake"],
            )
            extra_characters.append(observer)
            observer_view = ctx["intake"].return_appearance(observer)
            ok = (
                "|wActions:|n" in appearance
                and "|wExits:|n" not in appearance
                and "|wExits:|n" in observer_view
                and "|wActions:|n" not in observer_view
            )
            detail = appearance
        elif case_name == "actions-contextual":
            race_view = ctx["intake"].return_appearance(character)
            character.execute_cmd("accept")
            build_view = ctx["intake"].return_appearance(character)
            ok = (
                "|lc__clickmove__ accept|lt|yaccept|n|le" in race_view
                and "|lc__clickmove__ next|lt|ynext|n|le" in race_view
                and "|lc__clickmove__ back|lt|yback|n|le" not in race_view
                and "|lc__clickmove__ back|lt|yback|n|le" in build_view
                and "|lc__clickmove__ finalize|lt|yfinalize|n|le" not in build_view
            )
            detail = build_view
        elif case_name == "lock-flow":
            captured[character].clear()
            character.execute_cmd("next")
            character.execute_cmd("accept")
            character.execute_cmd("east")
            messages = "\n".join(captured.get(character) or [])
            ok = (
                getattr(character.db, "chargen_step", None) == "height"
                and getattr(getattr(character, "location", None), "key", None) == "Intake Chamber"
                and chargen_mirror.BLOCKED_INPUT_MESSAGE in messages
            )
            detail = messages or f"step={getattr(character.db, 'chargen_step', None)}"
        elif case_name == "race-lock":
            captured[character].clear()
            character.execute_cmd("touch mirror")
            chosen_race = dict(getattr(character.db, "chargen_selections", {}) or {}).get("race")
            character.execute_cmd("accept")
            character.execute_cmd("back")
            character.execute_cmd("touch mirror")
            messages = "\n".join(captured.get(character) or [])
            ok = (
                chosen_race != dict(getattr(character.db, "chargen_selections", {}) or {}).get("race")
                and getattr(character.db, "chargen_step", None) == "race"
                and "The mirror gives the last choice back." in messages
            )
            detail = messages or f"race={chosen_race}"
        elif case_name == "render":
            character.execute_cmd("touch mirror")
            appearance = mirror.return_appearance(character)
            chosen_race = dict(getattr(character.db, "chargen_selections", {}) or {}).get("race")
            ok = chosen_race in appearance.lower() and "It waits. Not for approval, but for interruption." in appearance
            detail = appearance
        elif case_name == "click-executes":
            character.execute_cmd("accept")
            build_view = ctx["intake"].return_appearance(character)
            captured[character].clear()
            character.execute_cmd("accept")
            messages = "\n".join(captured.get(character) or [])
            ok = (
                "|lc__clickmove__ accept|lt|yaccept|n|le" in build_view
                and getattr(character.db, "chargen_step", None) == "height"
                and "The reflection settles." in messages
            )
            detail = messages or build_view
        elif case_name == "back-navigation":
            character.execute_cmd("touch mirror")
            chosen_race = dict(getattr(character.db, "chargen_selections", {}) or {}).get("race")
            character.execute_cmd("accept")
            character.execute_cmd("touch mirror")
            chosen_build = dict(getattr(character.db, "chargen_selections", {}) or {}).get("build")
            captured[character].clear()
            character.execute_cmd("back")
            back_messages = "\n".join(captured.get(character) or [])
            character.execute_cmd("back")
            restored_race = dict(getattr(character.db, "chargen_selections", {}) or {}).get("race")
            ok = (
                getattr(character.db, "chargen_step", None) == "race"
                and chosen_race == restored_race
                and chosen_build == dict(getattr(character.db, "chargen_selections", {}) or {}).get("build")
                and "The mirror gives the last choice back." in back_messages
            )
            detail = back_messages or f"step={getattr(character.db, 'chargen_step', None)}"
        elif case_name == "confirmation-gate":
            for _step in chargen_mirror.CHARGEN_STEPS:
                character.execute_cmd("accept")
            review_view = mirror.return_appearance(character)
            captured[character].clear()
            character.execute_cmd("finalize")
            finalize_messages = "\n".join(captured.get(character) or [])
            confirm_view = mirror.return_appearance(character)
            ok = (
                chargen_mirror.is_chargen_active(character)
                and "The mirror holds what you've made of it." in review_view
                and "The mirror waits for the last word." in finalize_messages
                and "Decide now. It won't change after this." in confirm_view
            )
            detail = finalize_messages or confirm_view
        elif case_name == "finalize-lock":
            while chargen_mirror.is_chargen_active(character):
                actions = chargen_mirror.get_available_actions(character)
                finalize_action = next((entry for entry in actions if entry["label"] == "finalize"), None)
                confirm_action = next((entry for entry in actions if entry["label"] == "confirm"), None)
                accept_action = next((entry for entry in actions if entry["label"] == "accept"), None)
                if confirm_action:
                    character.execute_cmd(confirm_action["command"])
                    break
                if finalize_action:
                    character.execute_cmd(finalize_action["command"])
                    continue
                if accept_action:
                    character.execute_cmd(accept_action["command"])
                    continue
                break
            ok = (
                not chargen_mirror.is_chargen_active(character)
                and onboarding.get_onboarding_step(character) == onboarding.STEP_START
                and not bool(getattr(character.db, "chargen_active", False))
            )
            detail = f"chargen_active={chargen_mirror.is_chargen_active(character)} step={onboarding.get_onboarding_step(character)}"
        elif case_name == "no-command-needed":
            while chargen_mirror.is_chargen_active(character):
                actions = chargen_mirror.get_available_actions(character)
                if not actions:
                    break
                action = next(
                    (entry for entry in actions if entry["label"] in {"accept", "finalize", "confirm", "next"}),
                    None,
                )
                if not action:
                    break
                character.execute_cmd(action["command"])
            ok = (
                not chargen_mirror.is_chargen_active(character)
                and onboarding.get_onboarding_step(character) == onboarding.STEP_START
            )
            detail = f"chargen_active={chargen_mirror.is_chargen_active(character)} step={onboarding.get_onboarding_step(character)}"
        elif case_name == "no-exits":
            appearance = ctx["intake"].return_appearance(character)
            ok = "|wExits:|n" not in appearance and "|wActions:|n" in appearance
            detail = appearance
        elif case_name == "movement-blocked":
            before_room = getattr(getattr(character, "location", None), "key", None)
            captured[character].clear()
            character.execute_cmd("east")
            messages = "\n".join(captured.get(character) or [])
            ok = (
                getattr(getattr(character, "location", None), "key", None) == before_room
                and chargen_mirror.MOVEMENT_BLOCKED_MESSAGE in messages
            )
            detail = messages or before_room
        elif case_name == "exit-restored":
            while chargen_mirror.is_chargen_active(character):
                actions = chargen_mirror.get_available_actions(character)
                action = next((entry for entry in actions if entry["label"] in {"accept", "finalize", "confirm"}), None)
                if not action:
                    break
                character.execute_cmd(action["command"])
            appearance = ctx["intake"].return_appearance(character)
            ok = "|wExits:|n" in appearance and "|wActions:|n" not in appearance
            detail = appearance
        elif case_name == "no-softlock":
            counts = []
            labels = []
            while chargen_mirror.is_chargen_active(character):
                actions = chargen_mirror.get_available_actions(character)
                counts.append(len(actions))
                labels.append(",".join(entry["label"] for entry in actions))
                action = next((entry for entry in actions if entry["label"] in {"accept", "finalize", "confirm"}), None)
                if not action:
                    break
                character.execute_cmd(action["command"])
            ok = bool(counts) and all(1 <= count <= 3 for count in counts)
            detail = " | ".join(labels)
        elif case_name == "transition":
            captured[character].clear()
            while chargen_mirror.is_chargen_active(character):
                actions = chargen_mirror.get_available_actions(character)
                action = next((entry for entry in actions if entry["label"] in {"accept", "finalize", "confirm"}), None)
                if not action:
                    break
                character.execute_cmd(action["command"])
            after_messages = "\n".join(captured.get(character) or [])
            ok = (
                not chargen_mirror.is_chargen_active(character)
                and onboarding.get_onboarding_step(character) == onboarding.STEP_START
                and getattr(getattr(character, "location", None), "key", None) == "Intake Chamber"
                and "Move." in after_messages
            )
            detail = after_messages or f"step={onboarding.get_onboarding_step(character)}"
        else:
            raise RuntimeError(f"Unknown chargen mirror case: {case_name}")

        payload = {
            "scenario": f"chargen-{case_name}",
            "ok": bool(ok),
            "detail": detail,
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"DireTest Scenario: chargen-{case_name}")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            if detail:
                print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        for extra in extra_characters:
            try:
                extra.delete()
            except Exception:
                pass
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


def _run_locked_onboarding_case(args, case_name):
    _setup_django()

    from systems import onboarding

    created_character = None
    sword = None
    vest = None
    sword_home = None
    vest_home = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        ctx = _build_locked_onboarding_character(create_object, onboarding)
        character = ctx["character"]
        created_character = character
        training = ctx["training"]
        practice = ctx["practice"]
        sword = ctx["sword"]
        vest = ctx["vest"]
        dummy = ctx["dummy"]
        sword_home = getattr(sword, "location", None)
        vest_home = getattr(vest, "location", None)
        expected_recovery_room = _expected_recovery_room_key(onboarding)
        captured, originals = _capture_object_messages(character)

        ok = False
        detail = ""

        if case_name == "movement":
            captured[character].clear()
            character.move_to(training, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            messages = "\n".join(captured.get(character) or [])
            ok = onboarding.get_onboarding_step(character) == onboarding.STEP_MOVEMENT and "You'll need something in your hands." in messages
            detail = messages or f"step={onboarding.get_onboarding_step(character)}"
        elif case_name == "get":
            captured[character].clear()
            character.move_to(training, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            captured[character].clear()
            character.execute_cmd("take sword")
            messages = "\n".join(captured.get(character) or [])
            ok = (
                onboarding.get_onboarding_step(character) == onboarding.STEP_PREPARATION
                and onboarding.SWORD_PICKUP_MESSAGE in messages
                and onboarding.INVENTORY_HINT in messages
                and "Wear what you can. Carry it properly." in messages
            )
            detail = messages or f"step={onboarding.get_onboarding_step(character)}"
        elif case_name == "equip":
            captured[character].clear()
            character.move_to(training, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            character.execute_cmd("get sword")
            character.execute_cmd("get vest")
            character.execute_cmd("wear vest")
            captured[character].clear()
            character.execute_cmd("wield sword")
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                onboarding.get_onboarding_step(character) == onboarding.STEP_COMBAT
                and onboarding.EQUIP_COMPLETION_MESSAGE in messages
                and onboarding.COMBAT_TRANSITION_LINE in messages
            )
            detail = messages or f"step={onboarding.get_onboarding_step(character)}"
        elif case_name == "equip-alias":
            captured[character].clear()
            character.move_to(training, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            character.execute_cmd("grab sword")
            character.execute_cmd("get vest")
            character.execute_cmd("wear vest")
            captured[character].clear()
            character.execute_cmd("equip sword")
            messages = "\n".join(captured.get(character) or [])
            ok = bool(onboarding.get_onboarding_step(character) == onboarding.STEP_COMBAT and onboarding.EQUIP_COMPLETION_MESSAGE in messages)
            detail = messages or f"step={onboarding.get_onboarding_step(character)}"
        elif case_name == "inventory-skip-nudge":
            captured[character].clear()
            character.move_to(training, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            character.execute_cmd("get sword")
            state = onboarding.ensure_onboarding_state(character)
            state["last_progress_at"] = time.time() - 8.0
            state["idle_prompt_step"] = onboarding.STEP_PREPARATION
            state["idle_prompt_stage"] = 0
            character.db.onboarding_state = state
            character.db.onboarding_room_entered_at = time.time() - 8.0
            captured[character].clear()
            prompted = onboarding.remind_objective_if_idle(character, idle_threshold=5.0, minimum_interval=0.0)
            messages = "\n".join(captured.get(character) or [])
            ok = bool(prompted and 'Know what you carry.' in messages)
            detail = messages or f"prompted={prompted}"
        elif case_name == "blocked-command":
            _, message = onboarding.remap_onboarding_input(character, "inventory")
            ok = message == onboarding.EARLY_BLOCKED_COMMAND_MESSAGE
            detail = str(message or "")
        elif case_name == "between-lock":
            captured[character].clear()
            character.move_to(training, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            character.execute_cmd("get sword")
            character.execute_cmd("get vest")
            character.execute_cmd("wear vest")
            character.execute_cmd("wield sword")
            character.move_to(practice, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            character.execute_cmd("attack dummy")
            character.execute_cmd("attack goblin")
            character.execute_cmd("attack goblin")
            before_room = getattr(getattr(character, "location", None), "key", None)
            captured[character].clear()
            character.execute_cmd("inventory")
            character.execute_cmd("east")
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                bool(getattr(character.db, "training_between", False))
                and bool(getattr(character.db, "training_collapse", False))
                and onboarding.get_onboarding_step(character) == onboarding.STEP_COLLAPSE
                and getattr(getattr(character, "location", None), "key", None) == before_room
                and not messages.strip()
            )
            detail = messages or f"step={onboarding.get_onboarding_step(character)} between={getattr(character.db, 'training_between', None)}"
        elif case_name == "resurrection-sequence":
            captured[character].clear()
            _run_e2e_onboarding(character, onboarding)
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                _fragments_in_order(
                    messages,
                    [
                        onboarding.COLLAPSE_LINE,
                        onboarding.BETWEEN_STATE_INTRO,
                        onboarding.BETWEEN_STATE_OBSERVER,
                        'Hold',
                        'The spirit is slipping.',
                        'Footsteps. Quick. Close.',
                        'Can you hold it?',
                        'Pressure.',
                        'Light',
                        'Breath returns like it was forced into you.',
                        "They'll hold.",
                        "Then don't keep them here.",
                        'A shift in the air',
                        'Send them through.',
                        'The space beside you folds',
                        'Not a step.',
                        'Stone beneath you.',
                    ],
                )
                and getattr(getattr(character, "location", None), "key", None) == expected_recovery_room
            )
            detail = messages or f"step={onboarding.get_onboarding_step(character)}"
        elif case_name == "recovery-state":
            captured[character].clear()
            character.move_to(training, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            character.execute_cmd("get sword")
            character.execute_cmd("get vest")
            character.execute_cmd("wear vest")
            character.execute_cmd("wield sword")
            character.move_to(practice, quiet=True, use_destination=False)
            onboarding.handle_room_entry(character)
            character.execute_cmd("attack dummy")
            character.execute_cmd("attack goblin")
            character.execute_cmd("attack goblin")
            _advance_training_resurrection(character, onboarding, complete_release=False)
            ok = bool(
                onboarding.get_onboarding_step(character) == onboarding.STEP_COMPLETE
                and not bool(getattr(character.db, "training_between", False))
                and not bool(getattr(character.db, "training_collapse", False))
                and int(getattr(character.db, "hp", 0) or 0) > 0
                and getattr(getattr(character, "location", None), "key", None) == expected_recovery_room
            )
            detail = f"step={onboarding.get_onboarding_step(character)} hp={int(getattr(character.db, 'hp', 0) or 0)} between={bool(getattr(character.db, 'training_between', False))}"
        elif case_name == "transport-sequence":
            captured[character].clear()
            _run_e2e_onboarding(character, onboarding)
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                _fragments_in_order(
                    messages,
                    [
                        "They'll hold.",
                        "For now.",
                        "Then don't keep them here.",
                        'A shift in the air',
                        '"I\'m here."',
                        '"Stable enough."',
                        '"Send them through."',
                        'The space beside you folds',
                        'Not a step.',
                        'Stone beneath you.',
                    ],
                )
                and getattr(getattr(character, "location", None), "key", None) == expected_recovery_room
            )
            detail = messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"
        elif case_name == "final-location":
            captured[character].clear()
            _run_e2e_onboarding(character, onboarding)
            ok = getattr(getattr(character, "location", None), "key", None) == expected_recovery_room
            detail = f"room={getattr(getattr(character, 'location', None), 'key', None)}"
        elif case_name == "control-return":
            captured[character].clear()
            _run_e2e_onboarding(character, onboarding)
            before_room = character.location
            character.execute_cmd("look")
            character.execute_cmd("guild")
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                onboarding.get_onboarding_step(character) == onboarding.STEP_COMPLETE
                and not bool(getattr(character.db, "training_between", False))
                and not bool(getattr(character.db, "training_collapse", False))
                and getattr(before_room, "key", None) == expected_recovery_room
                and getattr(getattr(character, "location", None), "key", None) == onboarding.EMPATH_GUILD_ROOM
                and messages.strip()
            )
            detail = messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"
        elif case_name == "npc-presence":
            captured[character].clear()
            _run_e2e_onboarding(character, onboarding)
            character.execute_cmd("guild")
            room = getattr(character, "location", None)
            occupants = [str(getattr(obj, "key", "") or "") for obj in list(getattr(room, "contents", []) or []) if obj != character]
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                onboarding.TRIAGE_EMPATH_KEY in occupants
                and onboarding.WARD_CLERIC_KEY in occupants
                and "welcome" not in messages.lower()
                and "hello" not in messages.lower()
            )
            detail = messages or ", ".join(occupants)
        elif case_name == "complete":
            captured[character].clear()
            _run_e2e_onboarding(character, onboarding)
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                onboarding.get_onboarding_step(character) == onboarding.STEP_COMPLETE
                and getattr(getattr(character, "location", None), "key", None) == expected_recovery_room
                and onboarding.BETWEEN_STATE_INTRO in messages
                and "Stone beneath you." in messages
            )
            detail = messages or f"step={onboarding.get_onboarding_step(character)} room={getattr(getattr(character, 'location', None), 'key', None)}"
        else:
            raise ValueError(f"Unknown locked onboarding case: {case_name}")

        if args.json:
            print(json.dumps({"scenario": f"onboarding-{case_name}", "ok": ok, "detail": detail}, indent=2, sort_keys=True))
        else:
            print(f"DireTest Scenario: onboarding-{case_name}")
            print(f"Result: {'PASS' if ok else 'FAIL'}")
            print(f"Detail: {detail}")
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if sword and sword_home and getattr(sword, "location", None) != sword_home:
            try:
                sword.move_to(sword_home, quiet=True, use_destination=False)
            except Exception:
                pass
        if vest and vest_home and getattr(vest, "location", None) != vest_home:
            try:
                vest.move_to(vest_home, quiet=True, use_destination=False)
            except Exception:
                pass
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


def _get_room_exit(room, direction):
    if not room:
        return None
    normalized = str(direction or "").strip().lower()
    for obj in list(getattr(room, "contents", []) or []):
        if not getattr(obj, "destination", None):
            continue
        if str(getattr(obj, "key", "") or "").strip().lower() == normalized:
            return obj
        aliases = {str(alias or "").strip().lower() for alias in getattr(getattr(obj, "aliases", None), "all", lambda: [])()}
        if normalized in aliases:
            return obj
    return None


def _build_alpha_suffix(seed_value, length=6):
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    seed = max(0, int(seed_value or 0))
    chars = []
    for _ in range(max(1, int(length or 1))):
        chars.append(alphabet[seed % len(alphabet)])
        seed //= len(alphabet)
    return "".join(reversed(chars))


def _build_e2e_unique_name(prefix, race, index, *, max_length=20):
    race_fragment = "".join(ch for ch in str(race or "").title() if ch.isalpha())[:8] or "Race"
    suffix_seed = int(time.time() * 1000) + (int(index or 0) * 97)
    suffix = _build_alpha_suffix(suffix_seed, length=6)
    raw = f"{prefix}{race_fragment}{suffix}"
    return raw[: int(max_length or 20)]


def _build_e2e_creation_blueprint(race, index):
    return {
        "name": _build_e2e_unique_name("Life", race, index),
        "race": str(race or "human"),
        "gender": "neutral",
        "profession": "commoner",
        "stats": {
            "strength": 10,
            "agility": 10,
            "reflex": 10,
            "intelligence": 10,
            "wisdom": 10,
            "stamina": 10,
        },
        "description": f"A deterministic lifecycle test character for {race}.",
        "appearance": {
            "build": "athletic",
            "height": "average",
            "hair": "brown",
            "eyes": "gray",
            "skin": "tan",
        },
    }


def _create_e2e_account(create_account, race, index):
    account_name = _build_e2e_unique_name("Acct", race, index)
    return create_account(
        account_name,
        f"{account_name.lower()}@diretest.local",
        "DiretestPass123!",
        typeclass="typeclasses.accounts.Account",
    )


def _create_e2e_character(account, race, index):
    from systems.character.creation import create_character_from_blueprint

    blueprint = _build_e2e_creation_blueprint(race, index)
    character, errors = create_character_from_blueprint(account, blueprint, allow_reserved_name=True)
    if errors:
        raise AssertionError(f"character creation errors: {'; '.join(str(error) for error in errors)}")
    if not character:
        raise AssertionError("character creation returned no character")
    return character


def _spawn_e2e_support_npcs(create_object, room, race, index):
    helpers = []
    suffix = _build_alpha_suffix(int(time.time() * 1000) + (int(index or 0) * 131), length=5)
    specs = (("cleric", f"LifecycleCleric{suffix}"), ("empath", f"LifecycleEmpath{suffix}"))
    for profession, key in specs:
        helper = create_object(
            "typeclasses.characters.Character",
            key=key,
            location=room,
            home=room,
        )
        helper.ensure_core_defaults()
        helper.db.is_npc = True
        helper.db.gender = "neutral"
        helper.set_race("human", sync=False, emit_messages=False)
        if hasattr(helper, "set_profession"):
            if helper.set_profession(profession) is False:
                raise AssertionError(f"failed to assign helper profession: {profession}")
        else:
            helper.db.profession = profession
            helper.db.guild = profession
        helper.db.attunement = helper.db.max_attunement
        helper.db.balance = helper.db.max_balance
        helper.db.fatigue = 0
        helper.sync_client_state(include_map=False)
        helpers.append(helper)
    return tuple(helpers)


def _assert_e2e_spawn_state(character, race, onboarding):
    if str(getattr(character.db, "race", "") or "") != str(race):
        raise AssertionError(f"spawn race mismatch: {character.db.race} != {race}")
    identity = getattr(character.db, "identity", None)
    if not isinstance(identity, Mapping):
        raise AssertionError("spawned without an identity object")
    if str(identity.get("race", "") or "") != str(race):
        raise AssertionError(f"identity race mismatch: {identity.get('race')} != {race}")
    if not isinstance(identity.get("appearance"), Mapping):
        raise AssertionError("spawned without an identity appearance mapping")
    rendered = character.get_rendered_desc(character) if hasattr(character, "get_rendered_desc") else str(getattr(character.db, "desc", "") or "")
    if not isinstance(rendered, str) or not rendered.strip():
        raise AssertionError("spawned without a renderable description")
    if int(getattr(character.db, "hp", 0) or 0) <= 0:
        raise AssertionError("spawned with non-positive hp")
    if getattr(getattr(character, "location", None), "key", None) != onboarding.INTAKE_CHAMBER:
        raise AssertionError(f"spawn room mismatch: {getattr(getattr(character, 'location', None), 'key', None)}")
    if onboarding.get_onboarding_step(character) != onboarding.STEP_START:
        raise AssertionError(f"unexpected onboarding step at spawn: {onboarding.get_onboarding_step(character)}")
    if not onboarding.is_in_onboarding(character):
        raise AssertionError("character did not enter onboarding")


def _run_e2e_onboarding(character, onboarding):
    commands = ("east", "get sword", "get vest", "wear vest", "wield sword", "east", "attack dummy", "attack goblin", "attack goblin")
    for command in commands:
        character.execute_cmd(command)
    onboarding._process_pending_scene(character, force=True)


def _fragments_in_order(text, fragments):
    cursor = 0
    for fragment in fragments:
        next_index = text.find(fragment, cursor)
        if next_index < 0:
            return False
        cursor = next_index + len(fragment)
    return True


def _advance_training_resurrection(character, onboarding, *, complete_release=False):
    onboarding._process_pending_scene(character, force=True)
    if complete_release:
        onboarding._process_pending_scene(character, force=True)


def _snapshot_e2e_object(obj):
    if not obj:
        return None
    return {
        "id": int(getattr(obj, "id", 0) or 0),
        "key": str(getattr(obj, "key", "") or ""),
    }


def _snapshot_e2e_inventory(character):
    snapshot = []
    for obj in list(getattr(character, "contents", []) or []):
        snapshot.append(_snapshot_e2e_object(obj))
    return sorted(snapshot, key=lambda entry: (int(entry.get("id", 0) or 0), str(entry.get("key", "") or "")))


def _normalize_e2e_value(value):
    if isinstance(value, Mapping):
        return {str(key): _normalize_e2e_value(entry) for key, entry in dict(value).items()}
    if isinstance(value, list):
        return [_normalize_e2e_value(entry) for entry in value]
    if isinstance(value, tuple):
        return [_normalize_e2e_value(entry) for entry in value]
    return value


def _snapshot_e2e_identity(character):
    payload = getattr(getattr(character, "db", None), "identity", None) or {}
    return _normalize_e2e_value(payload)


def _snapshot_e2e_equipment(character):
    return {
        "weapon": _snapshot_e2e_object(character.get_weapon() if hasattr(character, "get_weapon") else None),
        "inventory": _snapshot_e2e_inventory(character),
        "identity": _snapshot_e2e_identity(character),
    }


def _assert_e2e_onboarding_complete(character, onboarding):
    if onboarding.get_onboarding_step(character) != onboarding.STEP_COMPLETE:
        raise AssertionError(f"onboarding did not complete: {onboarding.get_onboarding_step(character)}")
    if not bool(getattr(character.db, "onboarding_complete", False)):
        raise AssertionError("onboarding_complete flag was not set")
    expected_room = _expected_recovery_room_key(onboarding)
    if getattr(getattr(character, "location", None), "key", None) != expected_room:
        raise AssertionError(f"unexpected onboarding completion room: {getattr(getattr(character, 'location', None), 'key', None)}")
    weapon = character.get_weapon() if hasattr(character, "get_weapon") else None
    if not weapon or str(getattr(weapon, "key", "") or "").strip().lower() != onboarding.TRAINING_SWORD_KEY:
        raise AssertionError("training sword is not wielded after onboarding")
    worn_items = list(character.get_worn_items() if hasattr(character, "get_worn_items") else [])
    if not any(str(getattr(item, "key", "") or "").strip().lower() == onboarding.TRAINING_VEST_KEY for item in worn_items):
        raise AssertionError("training vest is not worn after onboarding")


def _force_e2e_death(character):
    character.set_hp(0)


def _assert_e2e_dead(character, onboarding, expected_room=None):
    corpse = character.get_death_corpse() if hasattr(character, "get_death_corpse") else None
    if not character.is_dead():
        raise AssertionError("character did not enter dead state")
    if not corpse:
        raise AssertionError("death did not produce a corpse")
    target_room = expected_room or onboarding.PRACTICE_YARD
    if getattr(getattr(corpse, "location", None), "key", None) != target_room:
        raise AssertionError(f"corpse spawned in wrong room: {getattr(getattr(corpse, 'location', None), 'key', None)}")
    weapon = character.get_weapon() if hasattr(character, "get_weapon") else None
    if not weapon or str(getattr(weapon, "key", "") or "").strip().lower() != onboarding.TRAINING_SWORD_KEY:
        raise AssertionError("weapon state broke on death")
    worn_items = list(character.get_worn_items() if hasattr(character, "get_worn_items") else [])
    if not any(str(getattr(item, "key", "") or "").strip().lower() == onboarding.TRAINING_VEST_KEY for item in worn_items):
        raise AssertionError("worn gear state broke on death")
    return corpse


def _run_e2e_resurrection_pipeline(character, corpse, cleric, empath):
    if hasattr(corpse, "adjust_condition"):
        corpse.adjust_condition(-10)
    stabilized, stabilize_message = empath.stabilize_corpse(corpse)
    if not stabilized:
        raise AssertionError(f"corpse stabilization failed: {stabilize_message}")
    if not bool(getattr(getattr(corpse, "db", None), "stabilized", False)):
        raise AssertionError("corpse stabilization did not set the stabilized flag")
    resurrected, resurrect_message = character.force_resurrect(corpse=corpse, helper=cleric)
    if not resurrected:
        raise AssertionError(f"forced resurrection failed: {resurrect_message}")


def _assert_e2e_resurrected(character, onboarding, expected_room=None):
    if character.is_dead():
        raise AssertionError("character is still dead after resurrection")
    if not character.is_alive():
        raise AssertionError("character is not alive after resurrection")
    if character.get_death_corpse() is not None:
        raise AssertionError("corpse link remained after resurrection")
    if getattr(character.db, "last_recovery_type", None) != "resurrection":
        raise AssertionError(f"unexpected recovery type: {getattr(character.db, 'last_recovery_type', None)}")
    if int(getattr(character.db, "hp", 0) or 0) <= 0:
        raise AssertionError("resurrection left hp at zero")
    if int(getattr(character.db, "hp", 0) or 0) > int(getattr(character.db, "max_hp", 0) or 0):
        raise AssertionError("resurrection exceeded max hp")
    target_room = expected_room or onboarding.PRACTICE_YARD
    if getattr(getattr(character, "location", None), "key", None) != target_room:
        raise AssertionError(f"unexpected resurrection room: {getattr(getattr(character, 'location', None), 'key', None)}")


def _assert_e2e_equipment_persistence(character, equipment_before):
    weapon_before = dict((equipment_before or {}).get("weapon") or {})
    inventory_before = list((equipment_before or {}).get("inventory") or [])
    identity_before = dict((equipment_before or {}).get("identity") or {})
    weapon_after = _snapshot_e2e_object(character.get_weapon() if hasattr(character, "get_weapon") else None)
    inventory_after = _snapshot_e2e_inventory(character)
    identity_after = _snapshot_e2e_identity(character)

    if weapon_before and not weapon_after:
        raise AssertionError("weapon missing after resurrection")
    if weapon_before and int(weapon_after.get("id", 0) or 0) != int(weapon_before.get("id", 0) or 0):
        raise AssertionError(f"weapon changed across death: {weapon_before} -> {weapon_after}")
    if inventory_after != inventory_before:
        raise AssertionError(f"inventory changed across death: {inventory_before} -> {inventory_after}")
    if identity_after != identity_before:
        raise AssertionError(f"identity changed across death: {identity_before} -> {identity_after}")


def _enter_e2e_live_game(character):
    return character


def _assert_e2e_cleanup_state(character, onboarding):
    raw_step = str(getattr(character.db, "onboarding_step", "") or "").strip().lower()
    if raw_step not in {"", onboarding.STEP_COMPLETE}:
        raise AssertionError(f"unexpected onboarding step after completion: {raw_step}")
    if onboarding.is_in_onboarding(character):
        raise AssertionError("character is still considered in onboarding after live entry")
    state = onboarding.ensure_onboarding_state(character)
    if bool(state.get("active", False)):
        raise AssertionError("onboarding state still marked active")
    if not bool(state.get("complete", False)):
        raise AssertionError("onboarding state lost completion marker")
    script_keys = [str(getattr(script, "key", "") or "") for script in list(character.scripts.all())] if hasattr(character, "scripts") else []
    if any("onboarding" in key.lower() for key in script_keys):
        raise AssertionError(f"onboarding scripts still attached to character: {script_keys}")


def _assert_e2e_live_commands_unlocked(character, onboarding):
    captured, originals = _capture_object_messages(character)
    try:
        before_room = character.location
        character.execute_cmd("inventory")
        character.execute_cmd("look")
        character.execute_cmd("get nonexistent-diretest-item")
        if character.location != before_room:
            raise AssertionError("core commands changed location unexpectedly")
        blocked_messages = {
            str(onboarding.BLOCKED_COMMAND_MESSAGE or ""),
            str(onboarding.EARLY_BLOCKED_COMMAND_MESSAGE or ""),
            str(onboarding.INVALID_COMMAND_MESSAGE or ""),
        }
        messages = [str(message or "") for message in list(captured.get(character) or [])]
        if any(message in blocked_messages for message in messages):
            raise AssertionError(f"live-game command remained onboarding-blocked: {messages}")
    finally:
        _restore_object_messages(originals)


def _assert_e2e_live_game_ready(character, onboarding, first_area):
    expected_room = _expected_recovery_room_key(onboarding)
    if getattr(getattr(character, "location", None), "key", None) != expected_room:
        raise AssertionError(f"unexpected live-game landing room: {getattr(getattr(character, 'location', None), 'key', None)}")
    exits = {str(getattr(obj, "key", "") or "").strip().lower() for obj in list(getattr(character.location, "contents", []) or []) if getattr(obj, "destination", None)}
    expected_exits = {"east", "west", "path", "guild"} if expected_room == onboarding.EMPATH_GUILD_ENTRY_ROOM else {"out", "street"}
    if exits != expected_exits:
        raise AssertionError(f"unexpected live-game exits: {sorted(exits)}")
    if not bool(getattr(character.db, "onboarding_complete", False)):
        raise AssertionError("onboarding completion flag cleared before live entry")
    if not character.is_alive():
        raise AssertionError("character is not alive in live game")
    weapon = character.get_weapon() if hasattr(character, "get_weapon") else None
    if not weapon or str(getattr(weapon, "key", "") or "").strip().lower() != onboarding.TRAINING_SWORD_KEY:
        raise AssertionError("equipped weapon did not survive into live game")
    worn_items = list(character.get_worn_items() if hasattr(character, "get_worn_items") else [])
    if not any(str(getattr(item, "key", "") or "").strip().lower() == onboarding.TRAINING_VEST_KEY for item in worn_items):
        raise AssertionError("worn gear did not survive into live game")
    rendered = character.get_rendered_desc(character) if hasattr(character, "get_rendered_desc") else str(getattr(character.db, "desc", "") or "")
    if not isinstance(rendered, str) or not rendered.strip():
        raise AssertionError("live character does not have a renderable description")
    _assert_e2e_cleanup_state(character, onboarding)
    _assert_e2e_live_commands_unlocked(character, onboarding)


def _run_e2e_creation_flow(race, index):
    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_account
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from systems import first_area, onboarding

    for obj in ObjectDB.objects.filter(db_key__istartswith="corpse of Life"):
        try:
            obj.delete()
        except Exception:
            pass
    for prefix in ("Life", "LifecycleCleric", "LifecycleEmpath"):
        for obj in ObjectDB.objects.filter(db_key__istartswith=prefix):
            try:
                obj.delete()
            except Exception:
                pass
    for obj in ObjectDB.objects.filter(db_key__iexact=onboarding.TRAINING_SWORD_KEY):
        location_key = str(getattr(getattr(obj, "location", None), "key", "") or "")
        if location_key not in {onboarding.PRACTICE_YARD, first_area.OUTER_YARD, first_area.MARKET_APPROACH, first_area.SIDE_PASSAGE}:
            continue
        try:
            obj.delete()
        except Exception:
            pass

    _ensure_new_player_tutorial()
    account = _create_e2e_account(create_account, race, index)
    character = _create_e2e_character(account, race, index)
    account.route_character_to_onboarding(character, create=True)
    return account, character


def _teardown_e2e_entities(account=None, character=None, helpers=None, extra_objects=None):
    for helper in reversed(list(helpers or [])):
        try:
            helper.delete()
        except Exception:
            pass
    for obj in reversed(list(extra_objects or [])):
        try:
            obj.delete()
        except Exception:
            pass
    if character:
        try:
            character.delete()
        except Exception:
            pass
    if account:
        try:
            account.delete()
        except Exception:
            pass


def _run_invalid_onboarding_command_case(race, index):
    from systems import onboarding

    account = None
    character = None
    captured = {}
    originals = {}
    try:
        account, character = _run_e2e_creation_flow(race, index)
        _assert_e2e_spawn_state(character, race, onboarding)
        captured, originals = _capture_object_messages(character)
        for command in ("dance", "fly", "xyz"):
            character.execute_cmd(command)
        if onboarding.get_onboarding_step(character) != onboarding.STEP_START:
            raise AssertionError(f"invalid commands corrupted onboarding step: {onboarding.get_onboarding_step(character)}")
        if getattr(getattr(character, "location", None), "key", None) != onboarding.INTAKE_CHAMBER:
            raise AssertionError("invalid commands changed onboarding location")
        if not character.is_alive():
            raise AssertionError("invalid commands broke character life state")
        return {
            "case": "invalid-commands",
            "messages": list(captured.get(character) or []),
        }
    finally:
        _restore_object_messages(originals)
        _teardown_e2e_entities(account=account, character=character)


def _run_skip_equip_case(race, index):
    from systems import onboarding

    account = None
    character = None
    try:
        account, character = _run_e2e_creation_flow(race, index)
        _assert_e2e_spawn_state(character, race, onboarding)
        character.execute_cmd("east")
        character.execute_cmd("get sword")
        character.execute_cmd("east")
        if onboarding.get_onboarding_step(character) != onboarding.STEP_PREPARATION:
            raise AssertionError(f"skip-equip bypassed preparation state: {onboarding.get_onboarding_step(character)}")
        if getattr(getattr(character, "location", None), "key", None) != onboarding.TRAINING_HALL:
            raise AssertionError("skip-equip case advanced rooms unexpectedly")
        if bool(getattr(character.db, "onboarding_complete", False)):
            raise AssertionError("skip-equip case completed onboarding unexpectedly")
        return {
            "case": "skip-equip",
            "step": onboarding.get_onboarding_step(character),
            "room": getattr(getattr(character, "location", None), "key", None),
        }
    finally:
        _teardown_e2e_entities(account=account, character=character)


def _run_drop_weapon_before_death_case(race, index):
    from evennia.utils.create import create_object
    from systems import first_area, onboarding

    account = None
    character = None
    helpers = []
    extra_objects = []
    try:
        account, character = _run_e2e_creation_flow(race, index)
        _assert_e2e_spawn_state(character, race, onboarding)
        cleric, empath = _spawn_e2e_support_npcs(create_object, character.location, race, index)
        helpers = [cleric, empath]

        _run_e2e_onboarding(character, onboarding)
        _assert_e2e_onboarding_complete(character, onboarding)

        dropped_weapon = character.get_weapon() if hasattr(character, "get_weapon") else None
        if not dropped_weapon:
            raise AssertionError("drop-weapon case had no weapon to drop")
        dropped_weapon_id = int(getattr(dropped_weapon, "id", 0) or 0)
        character.execute_cmd(f"drop {dropped_weapon.key}")
        if character.get_weapon() is not None:
            raise AssertionError("drop-weapon case left the weapon equipped")
        expected_recovery_room = _expected_recovery_room_key(onboarding)
        if getattr(getattr(dropped_weapon, "location", None), "key", None) != expected_recovery_room:
            raise AssertionError("dropped weapon did not remain in the room")

        inventory_before = _snapshot_e2e_inventory(character)
        _force_e2e_death(character)
        corpse = character.get_death_corpse() if hasattr(character, "get_death_corpse") else None
        extra_objects.extend([obj for obj in (dropped_weapon, corpse) if obj])
        if not character.is_dead() or not corpse:
            raise AssertionError("drop-weapon case did not produce a corpse")
        if getattr(getattr(corpse, "location", None), "key", None) != expected_recovery_room:
            raise AssertionError("drop-weapon corpse spawned in the wrong room")
        worn_items = list(character.get_worn_items() if hasattr(character, "get_worn_items") else [])
        if not any(str(getattr(item, "key", "") or "").strip().lower() == onboarding.TRAINING_VEST_KEY for item in worn_items):
            raise AssertionError("drop-weapon case lost worn gear on death")
        if getattr(getattr(dropped_weapon, "location", None), "key", None) != expected_recovery_room:
            raise AssertionError("dropped weapon was moved by death processing")

        cleric.move_to(corpse.location, quiet=True, use_destination=False)
        empath.move_to(corpse.location, quiet=True, use_destination=False)
        _run_e2e_resurrection_pipeline(character, corpse, cleric, empath)
        _assert_e2e_resurrected(character, onboarding, expected_room=expected_recovery_room)
        if _snapshot_e2e_inventory(character) != inventory_before:
            raise AssertionError("inventory changed across dropped-weapon resurrection")
        if character.get_weapon() is not None:
            raise AssertionError("dropped weapon was incorrectly re-equipped after resurrection")
        if getattr(getattr(dropped_weapon, "location", None), "key", None) != expected_recovery_room:
            raise AssertionError("dropped weapon was lost or duplicated after resurrection")

        character.execute_cmd(f"get {dropped_weapon.key}")
        character.execute_cmd(f"wield {dropped_weapon.key}")
        equipped = character.get_weapon() if hasattr(character, "get_weapon") else None
        if int(getattr(equipped, "id", 0) or 0) != dropped_weapon_id:
            raise AssertionError("recovered weapon identity did not match the dropped weapon")

        _enter_e2e_live_game(character)
        _assert_e2e_live_game_ready(character, onboarding, first_area)
        return {
            "case": "drop-weapon-before-death",
            "weapon_id": dropped_weapon_id,
            "landing_room": expected_recovery_room,
        }
    finally:
        _teardown_e2e_entities(account=account, character=character, helpers=helpers, extra_objects=extra_objects)


def _run_early_death_recovery_case(race, index):
    from evennia.utils.create import create_object
    from systems import first_area, onboarding

    account = None
    character = None
    helpers = []
    extra_objects = []
    try:
        account, character = _run_e2e_creation_flow(race, index)
        _assert_e2e_spawn_state(character, race, onboarding)
        expected_recovery_room = _expected_recovery_room_key(onboarding)
        cleric, empath = _spawn_e2e_support_npcs(create_object, character.location, race, index)
        helpers = [cleric, empath]

        character.execute_cmd("east")
        character.execute_cmd("get sword")
        if onboarding.get_onboarding_step(character) != onboarding.STEP_PREPARATION:
            raise AssertionError("early-death case did not reach preparation")
        equipment_before = _snapshot_e2e_equipment(character)

        _force_e2e_death(character)
        corpse = character.get_death_corpse() if hasattr(character, "get_death_corpse") else None
        extra_objects.extend([obj for obj in (corpse,) if obj])
        if not character.is_dead() or not corpse:
            raise AssertionError("early-death case did not produce a corpse")
        if getattr(getattr(corpse, "location", None), "key", None) != onboarding.TRAINING_HALL:
            raise AssertionError("early-death corpse spawned in the wrong room")

        cleric.move_to(corpse.location, quiet=True, use_destination=False)
        empath.move_to(corpse.location, quiet=True, use_destination=False)
        _run_e2e_resurrection_pipeline(character, corpse, cleric, empath)
        _assert_e2e_resurrected(character, onboarding, expected_room=onboarding.TRAINING_HALL)
        if getattr(getattr(character, "location", None), "key", None) != onboarding.TRAINING_HALL:
            raise AssertionError("early-death resurrection returned to the wrong room")
        _assert_e2e_equipment_persistence(character, equipment_before)
        if onboarding.get_onboarding_step(character) != onboarding.STEP_PREPARATION:
            raise AssertionError(f"early-death case lost onboarding progress: {onboarding.get_onboarding_step(character)}")

        character.execute_cmd("get vest")
        character.execute_cmd("wear vest")
        character.execute_cmd("wield sword")
        character.execute_cmd("east")
        character.execute_cmd("attack dummy")
        character.execute_cmd("attack goblin")
        character.execute_cmd("attack goblin")
        _advance_training_resurrection(character, onboarding, complete_release=True)
        _assert_e2e_onboarding_complete(character, onboarding)

        _enter_e2e_live_game(character)
        _assert_e2e_live_game_ready(character, onboarding, first_area)
        return {
            "case": "early-death-recovery",
            "landing_room": expected_recovery_room,
            "step_after_resurrection": onboarding.get_onboarding_step(character),
        }
    finally:
        _teardown_e2e_entities(account=account, character=character, helpers=helpers, extra_objects=extra_objects)


def _run_e2e_full_lifecycle_for_race(race, index):
    from evennia.utils.create import create_object
    from systems import first_area, onboarding

    account = None
    character = None
    helpers = []
    try:
        account, character = _run_e2e_creation_flow(race, index)
        _assert_e2e_spawn_state(character, race, onboarding)
        expected_recovery_room = _expected_recovery_room_key(onboarding)

        cleric, empath = _spawn_e2e_support_npcs(create_object, character.location, race, index)
        helpers = [cleric, empath]

        _run_e2e_onboarding(character, onboarding)
        _assert_e2e_onboarding_complete(character, onboarding)
        equipment_before = _snapshot_e2e_equipment(character)

        _force_e2e_death(character)
        corpse = _assert_e2e_dead(character, onboarding, expected_room=expected_recovery_room)

        cleric.move_to(corpse.location, quiet=True, use_destination=False)
        empath.move_to(corpse.location, quiet=True, use_destination=False)
        _run_e2e_resurrection_pipeline(character, corpse, cleric, empath)
        _assert_e2e_resurrected(character, onboarding, expected_room=expected_recovery_room)
        _assert_e2e_equipment_persistence(character, equipment_before)

        _enter_e2e_live_game(character)
        _assert_e2e_live_game_ready(character, onboarding, first_area)

        return {
            "race": str(race),
            "character": str(getattr(character, "key", "") or ""),
            "account": str(getattr(account, "key", "") or ""),
            "ok": True,
            "spawn_room": onboarding.INTAKE_CHAMBER,
            "onboarding_room": expected_recovery_room,
            "landing_room": expected_recovery_room,
            "recovery_type": str(getattr(character.db, "last_recovery_type", "") or ""),
            "hp": int(getattr(character.db, "hp", 0) or 0),
            "max_hp": int(getattr(character.db, "max_hp", 0) or 0),
        }
    finally:
        _teardown_e2e_entities(account=account, character=character, helpers=helpers)


def _build_first_area_character(create_object, onboarding):
    ctx = _build_locked_onboarding_character(create_object, onboarding)
    character = ctx["character"]
    _run_e2e_onboarding(character, onboarding)

    return ctx


def _run_first_area_case(args, case_name):
    _setup_django()

    from systems import onboarding
    from systems import first_area

    created_character = None
    sword = None
    sword_home = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        ctx = _build_first_area_character(create_object, onboarding)
        character = ctx["character"]
        created_character = character
        sword = ctx["sword"]
        sword_home = getattr(sword, "home", None) or getattr(sword, "location", None)
        captured, originals = _capture_object_messages(character)

        expected_recovery_room = _expected_recovery_room_key(onboarding)
        lane_room = character.location
        if getattr(lane_room, "key", None) == onboarding.EMPATH_GUILD_ROOM:
            character.execute_cmd("south")
            lane_room = character.location
        if getattr(lane_room, "key", None) == getattr(onboarding, "EMPATH_GUILD_INTERIOR_ENTRY_ROOM", None):
            character.execute_cmd("out")
            lane_room = character.location
        if getattr(lane_room, "key", None) != onboarding.EMPATH_GUILD_ENTRY_ROOM:
            raise RuntimeError(f"Onboarding did not release into the first-area lane. room={getattr(lane_room, 'key', None)} recovery={expected_recovery_room}")
        guild_room = _get_room_exit(lane_room, "guild").destination if _get_room_exit(lane_room, "guild") else None
        east_room = _get_room_exit(lane_room, "east").destination if _get_room_exit(lane_room, "east") else None
        west_room = _get_room_exit(lane_room, "west").destination if _get_room_exit(lane_room, "west") else None
        path_room = _get_room_exit(lane_room, "path").destination if _get_room_exit(lane_room, "path") else None

        ok = False
        detail = ""

        if case_name == "entry":
            captured[character].clear()
            character.execute_cmd("guild")
            messages = "\n".join(captured.get(character) or [])
            ok = (
                getattr(character.location, "key", None) == getattr(onboarding, "EMPATH_GUILD_INTERIOR_ENTRY_ROOM", onboarding.EMPATH_GUILD_ROOM)
                and "It is a place for those who have not yet died." in messages
            )
            detail = messages or str(getattr(getattr(character, "location", None), "key", ""))
        elif case_name == "choice":
            ok = bool(
                guild_room
                and east_room
                and west_room
                and path_room
            )
            detail = ", ".join(sorted(room.key for room in [guild_room, east_room, west_room, path_room] if room))
        elif case_name == "interaction":
            captured[character].clear()
            character.execute_cmd("guild")
            character.execute_cmd("out")
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                getattr(character.location, "key", None) == onboarding.EMPATH_GUILD_ENTRY_ROOM
                and messages.strip()
            )
            detail = messages or "interaction"
        elif case_name == "exploration":
            captured[character].clear()
            character.execute_cmd("east")
            character.execute_cmd("west")
            character.execute_cmd("path")
            messages = "\n".join(captured.get(character) or [])
            ok = (
                getattr(character.location, "key", None) == getattr(path_room, "key", None)
                and messages.strip()
            )
            detail = messages or str(getattr(getattr(character, "location", None), "key", ""))
        elif case_name == "linger":
            captured[character].clear()
            character.execute_cmd("look")
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                getattr(getattr(character, "location", None), "key", None) == onboarding.EMPATH_GUILD_ENTRY_ROOM
                and messages.strip()
            )
            detail = messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"
        else:
            raise ValueError(f"Unknown first area case: {case_name}")

        if args.json:
            print(json.dumps({"scenario": f"first-area-{case_name}", "ok": ok, "detail": detail}, indent=2, sort_keys=True))
        else:
            print(f"DireTest Scenario: first-area-{case_name}")
            print(f"Result: {'PASS' if ok else 'FAIL'}")
            print(f"Detail: {detail}")
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if sword and sword_home and getattr(sword, "location", None) != sword_home:
            try:
                sword.move_to(sword_home, quiet=True, use_destination=False)
            except Exception:
                pass
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("first-area-entry")
def run_first_area_entry_scenario(args):
    return _run_first_area_case(args, "entry")


@register_scenario("first-area-choice")
def run_first_area_choice_scenario(args):
    return _run_first_area_case(args, "choice")

@register_scenario("first-area-interaction")
def run_first_area_interaction_scenario(args):
    return _run_first_area_case(args, "interaction")


@register_scenario("first-area-exploration")
def run_first_area_exploration_scenario(args):
    return _run_first_area_case(args, "exploration")


@register_scenario("first-area-linger")
def run_first_area_linger_scenario(args):
    return _run_first_area_case(args, "linger")


def _run_empath_guild_case(args, case_name):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from systems import onboarding

    created_character = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()
        expected_recovery_room = _expected_recovery_room_key(onboarding)

        lane_room = ObjectDB.objects.get_id(onboarding.EMPATH_GUILD_ENTRY_DBREF)
        if not lane_room or getattr(lane_room, "key", None) != onboarding.EMPATH_GUILD_ENTRY_ROOM:
            raise RuntimeError("Larkspur Lane, Midway (#4280) is missing.")
        guild_room = next(
            (
                room for room in ObjectDB.objects.filter(db_key__iexact=onboarding.EMPATH_GUILD_ROOM)
                if getattr(room, "db_typeclass_path", "") == "typeclasses.rooms.Room"
            ),
            None,
        )
        if not guild_room:
            raise RuntimeError("Empath Guild room is missing.")
        guild_entry_room = next(
            (
                room for room in ObjectDB.objects.filter(db_key__iexact=getattr(onboarding, "EMPATH_GUILD_INTERIOR_ENTRY_ROOM", "Empath Guild, Entry Hall"))
                if getattr(room, "db_typeclass_path", "") == "typeclasses.rooms.Room"
            ),
            None,
        )
        if not guild_entry_room:
            raise RuntimeError("Empath Guild entry room is missing.")

        character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Empath Guild {int(time.time() * 1000)}",
            location=lane_room,
            home=lane_room,
        )
        character.ensure_core_defaults()
        created_character = character
        captured, originals = _capture_object_messages(character)

        ok = False
        detail = ""

        if case_name == "entry":
            character.execute_cmd("guild")
            ok = getattr(getattr(character, "location", None), "key", None) == getattr(onboarding, "EMPATH_GUILD_INTERIOR_ENTRY_ROOM", onboarding.EMPATH_GUILD_ROOM)
            detail = f"room={getattr(getattr(character, 'location', None), 'key', None)}"
        elif case_name == "aliases":
            results = []
            for command in ["empath", "empath guild", "door"]:
                character.move_to(lane_room, quiet=True, use_destination=False)
                character.execute_cmd(command)
                results.append((command, getattr(getattr(character, "location", None), "key", None)))
            expected_entry_key = getattr(onboarding, "EMPATH_GUILD_INTERIOR_ENTRY_ROOM", onboarding.EMPATH_GUILD_ROOM)
            ok = all(room_key == expected_entry_key for _, room_key in results)
            detail = ", ".join(f"{command}->{room_key}" for command, room_key in results)
        elif case_name == "return":
            character.move_to(guild_entry_room, quiet=True, use_destination=False)
            entry_appearance = guild_entry_room.return_appearance(character)
            character.execute_cmd("out")
            out_room = getattr(getattr(character, "location", None), "key", None)
            character.move_to(guild_entry_room, quiet=True, use_destination=False)
            character.execute_cmd("street")
            street_room = getattr(getattr(character, "location", None), "key", None)
            ok = (
                out_room == onboarding.EMPATH_GUILD_ENTRY_ROOM
                and street_room == onboarding.EMPATH_GUILD_ENTRY_ROOM
                and "|lc__clickmove__ out|lt|yOut|n|le" in entry_appearance
            )
            detail = f"out={out_room}, street={street_room}, appearance={entry_appearance}"
        elif case_name == "clickable":
            appearance = lane_room.return_appearance(character)
            character.execute_cmd("__clickmove__ north")
            ok = (
                "|lc__clickmove__ north|lt|yEmpath Guild|n|le" in appearance
                and getattr(getattr(character, "location", None), "key", None) == getattr(onboarding, "EMPATH_GUILD_INTERIOR_ENTRY_ROOM", onboarding.EMPATH_GUILD_ROOM)
            )
            detail = appearance
        elif case_name == "post-teleport-location":
            from evennia.utils.create import create_object as onboarding_create_object

            onboarding_ctx = _build_locked_onboarding_character(onboarding_create_object, onboarding)
            onboarding_character = onboarding_ctx["character"]
            try:
                _run_e2e_onboarding(onboarding_character, onboarding)
                ok = getattr(getattr(onboarding_character, "location", None), "key", None) == expected_recovery_room
                detail = f"room={getattr(getattr(onboarding_character, 'location', None), 'key', None)}"
            finally:
                try:
                    onboarding_character.delete()
                except Exception:
                    pass
        else:
            raise RuntimeError(f"Unknown empath guild case: {case_name}")

        payload = {"scenario": f"empath-guild-{case_name}", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"DireTest Scenario: empath-guild-{case_name}")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            if detail:
                print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("cleric-join")
def run_cleric_join_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object
    from server.conf.at_server_startstop import _ensure_new_player_tutorial

    def _travel(actor, direction):
        current_room = getattr(actor, "location", None)
        if not current_room:
            return None
        wanted = str(direction or "").strip().lower()
        for obj in list(getattr(current_room, "exits", []) or []):
            destination = getattr(obj, "destination", None)
            if not destination:
                continue
            key = str(getattr(obj, "key", "") or "").strip().lower()
            aliases = {str(alias or "").strip().lower() for alias in getattr(getattr(obj, "aliases", None), "all", lambda: [])()}
            if wanted == key or wanted in aliases:
                actor.move_to(destination, quiet=True, use_destination=False)
                return destination
        return None

    created_character = None
    captured = {}
    originals = {}
    try:
        _ensure_new_player_tutorial()

        alley_room = ObjectDB.objects.get_id(4233)
        guild_room = ObjectDB.objects.filter(db_key__iexact="Cleric Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        office = ObjectDB.objects.filter(db_key__iexact="Guildleader Esuin's Office", db_typeclass_path="typeclasses.rooms.Room").first()
        esuin = ObjectDB.objects.filter(db_key__iexact="Guildleader Esuin", db_location=office).first() if office else None
        library = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Library", db_typeclass_path="typeclasses.rooms.Room").first()
        glass_hall = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Glass Hall", db_typeclass_path="typeclasses.rooms.Room").first()
        garden = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Garden", db_typeclass_path="typeclasses.rooms.Room").first()
        arch_hall = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Arch Hall", db_typeclass_path="typeclasses.rooms.Room").first()
        chapel = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Chapel", db_typeclass_path="typeclasses.rooms.Room").first()
        wine_cellar = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Wine Cellar", db_typeclass_path="typeclasses.rooms.Room").first()
        cellar_arch = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Cellar Arch", db_typeclass_path="typeclasses.rooms.Room").first()
        tunnel_mouth = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Tunnel Mouth", db_typeclass_path="typeclasses.rooms.Room").first()
        refectory_passage = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Refectory Passage", db_typeclass_path="typeclasses.rooms.Room").first()
        refectory = ObjectDB.objects.filter(db_key__iexact="Cleric Guild, Refectory", db_typeclass_path="typeclasses.rooms.Room").first()

        if not alley_room or getattr(alley_room, "key", None) != "Ratwhistle Alley, North Reach":
            raise RuntimeError("Ratwhistle Alley, North Reach (#4233) is missing.")
        for required_name, room in [
            ("Cleric Guild", guild_room),
            ("Guildleader Esuin's Office", office),
            ("Cleric Guild, Library", library),
            ("Cleric Guild, Glass Hall", glass_hall),
            ("Cleric Guild, Garden", garden),
            ("Cleric Guild, Arch Hall", arch_hall),
            ("Cleric Guild, Chapel", chapel),
            ("Cleric Guild, Wine Cellar", wine_cellar),
            ("Cleric Guild, Cellar Arch", cellar_arch),
            ("Cleric Guild, Tunnel Mouth", tunnel_mouth),
            ("Cleric Guild, Refectory Passage", refectory_passage),
            ("Cleric Guild, Refectory", refectory),
        ]:
            if not room:
                raise RuntimeError(f"{required_name} is missing.")
        if not esuin:
            raise RuntimeError("Guildleader Esuin is missing from the cleric office.")

        character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Cleric Join {int(time.time() * 1000)}",
            location=alley_room,
            home=alley_room,
        )
        character.ensure_core_defaults()
        created_character = character
        captured, originals = _capture_object_messages(character)

        results = []

        location_ok, location_message = character.join_profession("cleric")
        results.append(("location", (not location_ok) and "proper guildhall" in str(location_message or "").lower(), str(location_message or "missing location failure message")))

        walk_expectations = [
            ("north", "Cleric Guild"),
            ("north", "Guildleader Esuin's Office"),
            ("south", "Cleric Guild"),
            ("east", "Cleric Guild, Library"),
            ("east", "Cleric Guild, Glass Hall"),
            ("north", "Cleric Guild, Garden"),
            ("south", "Cleric Guild, Glass Hall"),
            ("west", "Cleric Guild, Library"),
            ("west", "Cleric Guild"),
            ("south", "Cleric Guild, Arch Hall"),
            ("west", "Cleric Guild, Chapel"),
            ("east", "Cleric Guild, Arch Hall"),
            ("east", "Cleric Guild, Wine Cellar"),
            ("south", "Cleric Guild, Cellar Arch"),
            ("north", "Cleric Guild, Wine Cellar"),
            ("east", "Cleric Guild, Tunnel Mouth"),
            ("west", "Cleric Guild, Wine Cellar"),
            ("west", "Cleric Guild, Arch Hall"),
            ("south", "Cleric Guild, Refectory Passage"),
            ("west", "Cleric Guild, Refectory"),
            ("east", "Cleric Guild, Refectory Passage"),
            ("north", "Cleric Guild, Arch Hall"),
            ("north", "Cleric Guild"),
            ("out", "Ratwhistle Alley, North Reach"),
        ]
        walk_failures = []
        for command, expected_room in walk_expectations:
            destination = _travel(character, command)
            actual_room = getattr(destination, "key", None) if destination else getattr(getattr(character, "location", None), "key", None)
            if actual_room != expected_room:
                walk_failures.append(f"{command}->{actual_room} (expected {expected_room})")
                break
        results.append(("walk", not walk_failures, "; ".join(walk_failures) if walk_failures else "route ok"))

        character.move_to(guild_room, quiet=True, use_destination=False)
        _travel(character, "north")

        inquiry_messages = str(esuin.handle_inquiry(character, "guild") or "")
        inquiry_ok = "duty" in inquiry_messages.lower() and "take that burden" in inquiry_messages.lower()
        results.append(("inquiry-guild", inquiry_ok, inquiry_messages or "missing guild inquiry response"))

        magic_messages = str(esuin.handle_inquiry(character, "magic") or "")
        magic_ok = "holy power" in magic_messages.lower() and "discipline" in magic_messages.lower()
        results.append(("inquiry-magic", magic_ok, magic_messages or "missing magic inquiry response"))

        join_ok, join_messages = character.join_profession("cleric")
        join_ok = (
            bool(join_ok)
            and character.get_profession() == "cleric"
            and character.get_guild() == "cleric"
            and "recognized as a cleric" in str(join_messages or "").lower()
        )
        results.append(("join", join_ok, str(join_messages or "missing join success message")))

        ok = all(passed for _name, passed, _detail in results)
        detail = " | ".join(f"{name}={'PASS' if passed else 'FAIL'}:{detail}" for name, passed, detail in results)
        payload = {"scenario": "cleric-join", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: cleric-join")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("empath-guild-entry")
def run_empath_guild_entry_scenario(args):
    return _run_empath_guild_case(args, "entry")


@register_scenario("empath-guild-aliases")
def run_empath_guild_aliases_scenario(args):
    return _run_empath_guild_case(args, "aliases")


@register_scenario("empath-guild-return")
def run_empath_guild_return_scenario(args):
    return _run_empath_guild_case(args, "return")


@register_scenario("post-teleport-location")
def run_post_teleport_location_scenario(args):
    return _run_empath_guild_case(args, "post-teleport-location")


@register_scenario("guild-clickable")
def run_guild_clickable_scenario(args):
    return _run_empath_guild_case(args, "clickable")


@register_scenario("empath-guild-map")
def run_empath_guild_map_scenario(args):
    _setup_django()

    from evennia.utils.create import create_object
    from world.area_forge.map_api import get_zone_map
    from world.areas.crossing.empath_guild.build import MAP_BUILD_TAG, ROOM_SPECS, ensure_crossing_empath_guildhall

    created_character = None
    try:
        rooms = ensure_crossing_empath_guildhall()
        guild_room = rooms["main_hall"]
        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Empath Guild Map {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        created_character.ensure_core_defaults()

        payload = get_zone_map(created_character)
        room_names = {entry.get("name") for entry in payload.get("rooms", [])}
        room_positions = {(entry.get("x"), entry.get("y")) for entry in payload.get("rooms", [])}
        current_room = next((entry for entry in payload.get("rooms", []) if entry.get("current")), None)
        ok = (
            payload.get("zone") == MAP_BUILD_TAG
            and len(payload.get("rooms", [])) == len(ROOM_SPECS)
            and len(room_positions) == len(ROOM_SPECS)
            and room_names == {spec["key"] for spec in ROOM_SPECS.values()}
            and current_room is not None
            and current_room.get("name") == guild_room.key
        )
        detail = (
            f"zone={payload.get('zone')}, rooms={len(payload.get('rooms', []))}, "
            f"edges={len(payload.get('edges', []))}, unique_positions={len(room_positions)}"
        )
        payload_out = {"scenario": "empath-guild-map", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload_out, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: empath-guild-map")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("empath-join")
def run_empath_join_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object
    from server.conf.at_server_startstop import _ensure_new_player_tutorial

    created_character = None
    captured = {}
    originals = {}
    try:
        _ensure_new_player_tutorial()

        lane_room = ObjectDB.objects.get_id(4280)
        guild_room = ObjectDB.objects.filter(db_key__iexact="Empath Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        guild_entry = ObjectDB.objects.filter(db_key__iexact="Empath Guild, Entry Hall", db_typeclass_path="typeclasses.rooms.Room").first()
        office = ObjectDB.objects.filter(db_key__iexact="Empath Guildleader's Office", db_typeclass_path="typeclasses.rooms.Room").first()
        merla = ObjectDB.objects.filter(db_key__iexact="Guildleader Merla", db_location=office).first() if office else None
        if not lane_room or getattr(lane_room, "key", None) != "Larkspur Lane, Midway":
            raise RuntimeError("Larkspur Lane, Midway (#4280) is missing.")
        if not guild_room:
            raise RuntimeError("Empath Guild room is missing.")
        if not guild_entry:
            raise RuntimeError("Empath Guild entry room is missing.")
        if not office:
            raise RuntimeError("Empath Guildleader's Office is missing.")
        if not merla:
            raise RuntimeError("Guildleader Merla is missing from the Empath Guildleader's Office.")

        character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Empath Join {int(time.time() * 1000)}",
            location=lane_room,
            home=lane_room,
        )
        character.ensure_core_defaults()
        created_character = character
        captured, originals = _capture_object_messages(character)

        results = []

        captured[character].clear()
        character.execute_cmd("join empath")
        fail_messages = "\n".join(captured.get(character) or [])
        fail_ok = character.get_profession() == "commoner" and "guildleader's office" in fail_messages.lower()
        results.append(("location", fail_ok, fail_messages or "missing location failure message"))

        captured[character].clear()
        character.execute_cmd("go empath")
        go_messages = "\n".join(captured.get(character) or [])
        go_ok = getattr(getattr(character, "location", None), "key", None) == "Empath Guild, Entry Hall"
        results.append(("go-empath", go_ok, go_messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"))

        captured[character].clear()
        character.execute_cmd("northeast")
        office_messages = "\n".join(captured.get(character) or [])
        office_ok = getattr(getattr(character, "location", None), "key", None) == "Empath Guildleader's Office"
        results.append(("office", office_ok, office_messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"))

        captured[character].clear()
        character.execute_cmd("ask merla about join")
        inquiry_messages = "\n".join(captured.get(character) or [])
        inquiry_ok = "accepting another person's hurt" in inquiry_messages.lower() or "join by" in inquiry_messages.lower()
        results.append(("inquiry", inquiry_ok, inquiry_messages or "missing inquiry response"))

        captured[character].clear()
        character.execute_cmd("join empath")
        join_messages = "\n".join(captured.get(character) or [])
        patient = character.get_empath_tutorial_patient() if hasattr(character, "get_empath_tutorial_patient") else None
        join_ok = (
            character.get_profession() == "empath"
            and character.get_guild() == "empath"
            and getattr(getattr(character, "location", None), "key", None) == "Empath Guild, Lecture Hall"
            and int(getattr(character.db, "empath_training_stage", 0) or 0) == 1
            and patient is not None
            and getattr(getattr(patient, "location", None), "key", None) == "Empath Guild, Lecture Hall"
        )
        results.append(("join", join_ok, join_messages or "missing join success message"))

        ok = all(passed for _name, passed, _detail in results)
        detail = " | ".join(f"{name}={'PASS' if passed else 'FAIL'}:{detail}" for name, passed, detail in results)
        payload = {"scenario": "empath-join", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: empath-join")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.clear_empath_tutorial_patient(delete_patient=True)
            except Exception:
                pass
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("empath-tutorial")
def run_empath_tutorial_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object
    from server.conf.at_server_startstop import _ensure_new_player_tutorial

    created_character = None
    captured = {}
    originals = {}
    try:
        _ensure_new_player_tutorial()

        office = ObjectDB.objects.filter(db_key__iexact="Empath Guildleader's Office", db_typeclass_path="typeclasses.rooms.Room").first()
        if not office:
            raise RuntimeError("Empath Guildleader's Office is missing.")

        character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Empath Tutorial {int(time.time() * 1000)}",
            location=office,
            home=office,
        )
        character.ensure_core_defaults()
        created_character = character
        captured, originals = _capture_object_messages(character)

        results = []

        captured[character].clear()
        character.execute_cmd("join empath")
        join_messages = "\n".join(captured.get(character) or [])
        patient = character.get_empath_tutorial_patient() if hasattr(character, "get_empath_tutorial_patient") else None
        joined_ok = character.get_profession() == "empath" and patient is not None
        results.append(("join", joined_ok, join_messages or "missing join output"))

        captured[character].clear()
        character.execute_cmd("touch patient")
        touch_messages = "\n".join(captured.get(character) or [])
        touch_ok = "sense the condition of your patient" in touch_messages.lower()
        results.append(("touch", touch_ok, touch_messages or "missing touch output"))

        captured[character].clear()
        character.execute_cmd("assess patient")
        assess_messages = "\n".join(captured.get(character) or [])
        assess_ok = "vitality:" in assess_messages.lower() and "bleeding:" in assess_messages.lower()
        results.append(("assess", assess_ok, assess_messages or "missing assess output"))

        captured[character].clear()
        character.execute_cmd("take bleeding all")
        character.execute_cmd("take vitality all")
        take_messages = "\n".join(captured.get(character) or [])
        patient_after_take = character.get_empath_tutorial_patient() if hasattr(character, "get_empath_tutorial_patient") else None
        take_ok = "draw the wound into yourself" in take_messages.lower() and patient_after_take is None
        results.append(("take", take_ok, take_messages or "missing take output"))

        captured[character].clear()
        character.execute_cmd("mend self")
        character.execute_cmd("mend self")
        mend_messages = "\n".join(captured.get(character) or [])
        mend_ok = (
            int(getattr(character.db, "empath_training_stage", 0) or 0) == 2
            and int(character.get_empath_wound("vitality") or 0) <= 0
            and int(character.get_empath_wound("bleeding") or 0) <= 0
            and "finished the lesson" in mend_messages.lower()
        )
        results.append(("mend", mend_ok, mend_messages or "missing mend output"))

        gate_ok, gate_message = character.can_use_empath_ability("link") if hasattr(character, "can_use_empath_ability") else (False, "missing ability gate")
        link_ok = (not gate_ok) and "lack the discipline" in str(gate_message or "").lower()
        results.append(("gate", link_ok, str(gate_message or "missing apprentice gate output")))

        ok = all(passed for _name, passed, _detail in results)
        detail = " | ".join(f"{name}={'PASS' if passed else 'FAIL'}:{detail}" for name, passed, detail in results)
        payload = {"scenario": "empath-tutorial", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: empath-tutorial")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.clear_empath_tutorial_patient(delete_patient=True)
            except Exception:
                pass
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("ranger-join")
def run_ranger_join_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()

        alley_room = ObjectDB.objects.get_id(4244)
        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not alley_room or getattr(alley_room, "key", None) != "Cracked Bell Alley, East Reach":
            raise RuntimeError("Cracked Bell Alley, East Reach (#4244) is missing.")
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        elarion = ObjectDB.objects.filter(db_key__iexact="Elarion", db_location=guild_room).first()
        if not elarion:
            raise RuntimeError("Elarion is missing from the Ranger Guild.")

        character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Join {int(time.time() * 1000)}",
            location=alley_room,
            home=alley_room,
        )
        character.ensure_core_defaults()
        created_character = character
        captured, originals = _capture_object_messages(character)

        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            character.set_stat(stat_name, minimum)

        results = []

        captured[character].clear()
        character.execute_cmd("join ranger")
        location_messages = "\n".join(captured.get(character) or [])
        location_ok = character.get_profession() == "commoner" and "proper guildhall" in location_messages.lower()
        results.append(("location", location_ok, location_messages or "missing location failure message"))

        captured[character].clear()
        character.execute_cmd("go guild")
        go_guild_messages = "\n".join(captured.get(character) or [])
        go_guild_ok = getattr(getattr(character, "location", None), "key", None) == "Ranger Guild"
        results.append(("go-guild", go_guild_ok, go_guild_messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"))

        character.move_to(alley_room, quiet=True, use_destination=False)
        captured[character].clear()
        character.execute_cmd("go ranger")
        go_ranger_messages = "\n".join(captured.get(character) or [])
        go_ranger_ok = getattr(getattr(character, "location", None), "key", None) == "Ranger Guild"
        results.append(("go-ranger", go_ranger_ok, go_ranger_messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"))

        captured[character].clear()
        guild_appearance = guild_room.return_appearance(character)
        exit_display_ok = all(fragment in guild_appearance.lower() for fragment in ["|wexits:|n", "north", "south", "east", "west"])
        results.append(("exit-display", exit_display_ok, guild_appearance or "missing guild appearance"))

        character.move_to(guild_room, quiet=True, use_destination=False)
        stat_name, minimum, label = RANGER_JOIN_REQUIREMENTS[0]
        character.set_stat(stat_name, minimum - 1)
        captured[character].clear()
        character.execute_cmd("join ranger")
        stat_messages = "\n".join(captured.get(character) or [])
        stat_ok = character.get_profession() == "commoner" and "not yet" in stat_messages.lower() and label.lower() in stat_messages.lower()
        results.append(("stats", stat_ok, stat_messages or "missing stat failure message"))

        for reset_name, reset_minimum, _reset_label in RANGER_JOIN_REQUIREMENTS:
            character.set_stat(reset_name, reset_minimum)

        captured[character].clear()
        character.execute_cmd("ask elarion about join")
        inquiry_messages = "\n".join(captured.get(character) or [])
        inquiry_ok = "say it, and mean it" in inquiry_messages.lower() and "join ranger" not in inquiry_messages.lower()
        results.append(("inquiry", inquiry_ok, inquiry_messages or "missing inquiry response"))

        captured[character].clear()
        character.execute_cmd("join ranger")
        join_messages = "\n".join(captured.get(character) or [])
        join_ok = (
            character.get_profession() == "ranger"
            and character.get_guild() == "ranger"
            and "recognized as a ranger" in join_messages.lower()
        )
        results.append(("join", join_ok, join_messages or "missing join success message"))

        captured[character].clear()
        character.execute_cmd("stats")
        stats_messages = "\n".join(captured.get(character) or [])
        stats_ok = (
            "wilderness bond:" in stats_messages.lower()
            and "environment:" in stats_messages.lower()
            and "terrain:" in stats_messages.lower()
            and "companion:" in stats_messages.lower()
            and "(" in stats_messages
        )
        results.append(("stats-tone", stats_ok, stats_messages or "missing ranger stats output"))

        captured[character].clear()
        character.execute_cmd("inf")
        nomatch_messages = "\n".join(captured.get(character) or [])
        nomatch_ok = "you hesitate, but nothing comes of it." in nomatch_messages.lower() and "command 'inf' is not available" not in nomatch_messages.lower()
        results.append(("nomatch", nomatch_ok, nomatch_messages or "missing softened nomatch response"))

        captured[character].clear()
        for command in ["west", "down", "down", "up", "down", "down", "up", "east", "south"]:
            character.execute_cmd(command)
        treehouse_return_messages = "\n".join(captured.get(character) or [])
        treehouse_return_ok = getattr(getattr(character, "location", None), "key", None) == "Cracked Bell Alley, East Reach"
        results.append(("treehouse-return", treehouse_return_ok, treehouse_return_messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"))

        character.move_to(guild_room, quiet=True, use_destination=False)
        captured[character].clear()
        character.execute_cmd("south")
        out_messages = "\n".join(captured.get(character) or [])
        out_ok = getattr(getattr(character, "location", None), "key", None) == "Cracked Bell Alley, East Reach"
        results.append(("out", out_ok, out_messages or f"room={getattr(getattr(character, 'location', None), 'key', None)}"))

        ok = all(passed for _name, passed, _detail in results)
        detail = " | ".join(f"{name}={'PASS' if passed else 'FAIL'}:{detail}" for name, passed, detail in results)
        payload = {"scenario": "ranger-join", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-join")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("ranger-npc-inquiry")
def run_ranger_npc_inquiry_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()

        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Inquiry {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        character.ensure_core_defaults()
        created_character = character
        captured, originals = _capture_object_messages(character)

        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            character.set_stat(stat_name, minimum)

        character.execute_cmd("join ranger")

        checks = [
            ("bram", ["west", "west"], "ask bram about training", "forage"),
            ("serik", ["east", "east"], "ask serik about hunting", "clean shot"),
            ("lysa", ["west", "down", "down", "up"], "ask lysa about scouting", "move without being noticed"),
            ("orren", ["north"], "ask orren about magic", "old ways"),
        ]
        results = []

        for label, travel_commands, ask_command, expected_text in checks:
            character.move_to(guild_room, quiet=True, use_destination=False)
            captured[character].clear()
            for command in travel_commands:
                character.execute_cmd(command)
            character.execute_cmd(ask_command)
            messages = "\n".join(captured.get(character) or [])
            ok = expected_text.lower() in messages.lower()
            results.append((label, ok, messages or "missing mentor response"))

        ok = all(passed for _name, passed, _detail in results)
        detail = " | ".join(f"{name}={'PASS' if passed else 'FAIL'}:{detail}" for name, passed, detail in results)
        payload = {"scenario": "ranger-npc-inquiry", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-npc-inquiry")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("ranger-circle-default")
def run_ranger_circle_default_scenario(args):
    _setup_django()

    room_name = None
    room = None
    created_character = None
    try:
        from evennia.utils.create import create_object

        room_name, room = _create_temp_room("diretest_ranger_circle_default")
        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Circle {int(time.time() * 1000)}",
            location=room,
            home=room,
        )
        created_character.ensure_core_defaults()
        ok = int(getattr(created_character.db, "circle", 0) or 0) == 1 and int(created_character.get_circle()) == 1
        detail = f"circle={getattr(created_character.db, 'circle', None)} get_circle={created_character.get_circle()}"
        payload = {"scenario": "ranger-circle-default", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-circle-default")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass
        _cleanup_named_object(room_name)
        if room:
            try:
                room.delete()
            except Exception:
                pass


@register_scenario("ranger-advance-fail")
def run_ranger_advance_fail_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()
        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Advance Fail {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        created_character.ensure_core_defaults()
        captured, originals = _capture_object_messages(created_character)

        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            created_character.set_stat(stat_name, minimum)

        created_character.execute_cmd("join ranger")
        captured[created_character].clear()
        created_character.execute_cmd("ask elarion about advancement")
        messages = "\n".join(captured.get(created_character) or [])
        ok = created_character.get_circle() == 1 and "gather" in messages.lower() and "awareness" in messages.lower()
        detail = messages or f"circle={created_character.get_circle()}"
        payload = {"scenario": "ranger-advance-fail", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-advance-fail")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("ranger-advance-success")
def run_ranger_advance_success_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()
        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Advance Success {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        created_character.ensure_core_defaults()
        captured, originals = _capture_object_messages(created_character)

        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            created_character.set_stat(stat_name, minimum)

        created_character.execute_cmd("join ranger")
        created_character.db.forage_uses = 1
        created_character.learn_skill("perception", {"rank": 5, "mindstate": 0})

        captured[created_character].clear()
        created_character.execute_cmd("ask elarion about advancement")
        messages = "\n".join(captured.get(created_character) or [])
        ok = created_character.get_circle() == 2 and "first true step" in messages.lower()
        detail = messages or f"circle={created_character.get_circle()}"
        payload = {"scenario": "ranger-advance-success", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-advance-success")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("ranger-advance-feedback")
def run_ranger_advance_feedback_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()
        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Advance Feedback {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        created_character.ensure_core_defaults()
        captured, originals = _capture_object_messages(created_character)

        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            created_character.set_stat(stat_name, minimum)

        created_character.execute_cmd("join ranger")
        captured[created_character].clear()
        created_character.execute_cmd("ask elarion about advancement")
        messages = "\n".join(captured.get(created_character) or [])
        ok = ("gather" in messages.lower() or "wild" in messages.lower()) and "awareness" in messages.lower()
        detail = messages or "missing advancement feedback"
        payload = {"scenario": "ranger-advance-feedback", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-advance-feedback")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("ranger-forage-scaling")
def run_ranger_forage_scaling_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    temp_room_name = None
    temp_room = None
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()
        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        temp_room_name, temp_room = _create_temp_room("diretest_ranger_forage_scaling")
        temp_room.db.forage_difficulty = 1

        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Forage {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        created_character.ensure_core_defaults()
        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            created_character.set_stat(stat_name, minimum)
        created_character.execute_cmd("join ranger")
        created_character.learn_skill("outdoorsmanship", {"rank": 10, "mindstate": 0})
        created_character.move_to(temp_room, quiet=True, use_destination=False)

        before = len(list(created_character.get_visible_carried_items()))
        created_character.execute_cmd("forage")
        after_items = list(created_character.get_visible_carried_items())
        after = len(after_items)
        ok = after > before and (after - before) >= 2
        detail = f"before={before} after={after} items={[item.key for item in after_items]}"
        payload = {"scenario": "ranger-forage-scaling", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-forage-scaling")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass
        _cleanup_named_object(temp_room_name)
        if temp_room:
            try:
                temp_room.delete()
            except Exception:
                pass


@register_scenario("ranger-forage-variation")
def run_ranger_forage_variation_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    temp_room_name = None
    temp_room = None
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()
        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        temp_room_name, temp_room = _create_temp_room("diretest_ranger_forage_variation")
        temp_room.db.forage_difficulty = 1

        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Forage Variation {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        created_character.ensure_core_defaults()
        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            created_character.set_stat(stat_name, minimum)
        created_character.execute_cmd("join ranger")
        created_character.learn_skill("outdoorsmanship", {"rank": 20, "mindstate": 0})
        created_character.move_to(temp_room, quiet=True, use_destination=False)

        results = set()
        for _index in range(12):
            created_character.execute_cmd("forage")
            created_character.set_roundtime(0)
        for item in list(created_character.get_visible_carried_items()):
            kind = str(getattr(item.db, "forage_kind", "") or "").strip().lower()
            if kind:
                results.add(kind)

        ok = len(results) > 1
        detail = f"resource_kinds={sorted(results)}"
        payload = {"scenario": "ranger-forage-variation", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-forage-variation")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass
        _cleanup_named_object(temp_room_name)
        if temp_room:
            try:
                temp_room.delete()
            except Exception:
                pass


@register_scenario("ranger-skin-fail")
def run_ranger_skin_fail_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    corpse = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()
        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Skin Fail {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        created_character.ensure_core_defaults()
        captured, originals = _capture_object_messages(created_character)
        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            created_character.set_stat(stat_name, minimum)
        created_character.execute_cmd("join ranger")

        corpse = create_object("typeclasses.corpse.Corpse", key="deer", location=guild_room, home=guild_room)
        corpse.locks.add("search:true();view:true()")
        corpse.db.skinnable = True
        corpse.db.skin_difficulty = 1
        corpse.db.dead = True

        created_character.skin_target(corpse)
        messages = "\n".join(captured.get(created_character) or [])
        ok = "need a skinning knife" in messages.lower()
        detail = messages or "missing skinning failure message"
        payload = {"scenario": "ranger-skin-fail", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-skin-fail")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if corpse:
            try:
                corpse.delete()
            except Exception:
                pass
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


@register_scenario("ranger-skin-success")
def run_ranger_skin_success_scenario(args):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from typeclasses.characters import RANGER_JOIN_REQUIREMENTS

    created_character = None
    corpse = None
    knife = None
    captured = {}
    originals = {}
    try:
        from evennia.utils.create import create_object

        _ensure_new_player_tutorial()
        guild_room = ObjectDB.objects.filter(db_key__iexact="Ranger Guild", db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Ranger Guild room is missing.")

        created_character = create_object(
            "typeclasses.characters.Character",
            key=f"DireTest Ranger Skin Success {int(time.time() * 1000)}",
            location=guild_room,
            home=guild_room,
        )
        created_character.ensure_core_defaults()
        captured, originals = _capture_object_messages(created_character)
        for stat_name, minimum, _label in RANGER_JOIN_REQUIREMENTS:
            created_character.set_stat(stat_name, minimum)
        created_character.execute_cmd("join ranger")
        created_character.learn_skill("skinning", {"rank": 20, "mindstate": 0})

        corpse = create_object("typeclasses.corpse.Corpse", key="deer", location=guild_room, home=guild_room)
        corpse.locks.add("search:true();view:true()")
        corpse.db.skinnable = True
        corpse.db.skin_difficulty = 1
        corpse.db.dead = True

        knife = create_object("typeclasses.objects.Object", key="skinning knife", location=created_character, home=created_character)
        created_character.execute_cmd("wield skinning knife")
        captured[created_character].clear()
        created_character.skin_target(corpse)

        carried = list(created_character.get_visible_carried_items())
        hides = [item for item in carried if "hide bundle" in str(getattr(item, "key", "") or "").lower()]
        ok = bool(hides) and str(getattr(hides[0].db, "skinning_quality", "") or "") in {"poor", "normal", "fine"}
        detail = f"messages={' | '.join(captured.get(created_character) or [])} hides={[item.key for item in hides]}"
        payload = {"scenario": "ranger-skin-success", "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("DireTest Scenario: ranger-skin-success")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        if corpse:
            try:
                corpse.delete()
            except Exception:
                pass
        if knife:
            try:
                knife.delete()
            except Exception:
                pass
        if created_character:
            try:
                created_character.delete()
            except Exception:
                pass


def _run_aftermath_case(args, case_name):
    _setup_django()

    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object
    from server.conf.at_server_startstop import _ensure_new_player_tutorial
    from systems import aftermath

    created_objects = []
    captured = {}
    originals = {}
    try:
        _ensure_new_player_tutorial()
        aftermath.ensure_poi_tags()

        guild_room = ObjectDB.objects.filter(db_key__iexact=aftermath.GUILD_ROOM_KEY, db_typeclass_path="typeclasses.rooms.Room").first()
        if not guild_room:
            raise RuntimeError("Empath Guild room is missing.")

        def build_character(room, label):
            character = create_object(
                "typeclasses.characters.Character",
                key=f"DireTest Aftermath {label} {int(time.time() * 1000)}",
                location=room,
                home=room,
            )
            character.ensure_core_defaults()
            created_objects.append(character)
            return character

        def build_temp_room(label, poi_tag=None):
            _, room = _create_temp_room(f"aftermath_{label}")
            created_objects.append(room)
            if poi_tag:
                room.tags.add(poi_tag)
            return room

        ok = False
        detail = ""

        if case_name == "recovery-orderly":
            character = build_character(guild_room, "orderly")
            aftermath.activate_new_player_state(character)
            captured, originals = _capture_object_messages(character)
            appearance = guild_room.return_appearance(character)
            first_messages = "\n".join(captured.get(character) or [])
            captured[character].clear()
            guild_room.return_appearance(character)
            repeat_messages = "\n".join(captured.get(character) or [])
            ok = bool(
                aftermath.ORDERLY_KEY in appearance
                and _fragments_in_order(first_messages, [line for line in aftermath.ORDERLY_DIALOGUE if line])
                and not repeat_messages.strip()
                and bool(getattr(character.db, "aftermath_orderly_prompted", False))
            )
            detail = first_messages or appearance
        elif case_name == "aftermath-per-player":
            room = build_temp_room("per_player")
            first = build_character(room, "per_player_a")
            second = build_character(room, "per_player_b")
            aftermath.activate_new_player_state(first)
            aftermath.activate_new_player_state(second)
            aftermath.note_room_entry(first, room)
            aftermath.note_room_entry(second, room)
            before_first = "\n".join(aftermath.get_room_render_lines(first, room))
            before_second = "\n".join(aftermath.get_room_render_lines(second, room))
            first_result = aftermath.handle_search(first, "raider")
            after_first = "\n".join(aftermath.get_room_render_lines(first, room))
            after_second = "\n".join(aftermath.get_room_render_lines(second, room))
            second_result = aftermath.handle_search(second, "raider")
            ok = bool(
                first_result
                and second_result
                and "fallen goblin raider" in before_first
                and "fallen goblin raider" in before_second
                and "fallen goblin raider" not in after_first
                and "fallen goblin raider" in after_second
            )
            detail = f"first_after={after_first!r} second_after={after_second!r}"
        elif case_name == "aftermath-currency-cap":
            room = build_temp_room("currency_cap")
            character = build_character(room, "currency_cap")
            captured, originals = _capture_object_messages(character)
            aftermath.activate_new_player_state(character)
            character.db.aftermath_currency_cap = 1
            character.db.aftermath_currency_total = 0
            character.db.coffer_room = int(getattr(room, "id", 0) or 0)
            aftermath.note_room_entry(character, room)
            corpse_result = aftermath.handle_search(character, "raider")
            coffer_result = aftermath.handle_pick(character, "coffer")
            messages = "\n".join(captured.get(character) or [])
            ok = bool(
                corpse_result
                and coffer_result
                and int(getattr(character.db, "aftermath_currency_total", 0) or 0) == 1
                and bool(getattr(character.db, "coffer_looted", False))
                and "1 copper" in messages.lower()
            )
            detail = messages or f"currency_total={getattr(character.db, 'aftermath_currency_total', None)}"
        elif case_name == "aftermath-full-kit":
            character = build_character(guild_room, "full_kit")
            aftermath.activate_new_player_state(character)
            rooms = [build_temp_room(f"full_kit_{index}") for index in range(2)]
            character.db.coffer_room = int(getattr(rooms[0], "id", 0) or 0)
            for room in rooms:
                character.move_to(room, quiet=True, use_destination=False)
                aftermath.note_room_entry(character, room)
                if not aftermath.handle_search(character, "raider"):
                    raise AssertionError(f"corpse search did not resolve in {getattr(room, 'key', None)}")

            poi_room = None
            for index in range(20):
                candidate = build_temp_room(f"full_kit_poi_{index}", poi_tag="poi_market")
                character.move_to(candidate, quiet=True, use_destination=False)
                if aftermath.handle_search(character, "raider"):
                    poi_room = candidate
                    if not aftermath._missing_kit_items(character):
                        break
            missing = aftermath._missing_kit_items(character)
            ok = bool(not missing and poi_room is not None)
            detail = f"missing={missing} poi_room={getattr(poi_room, 'key', None)} inventory={[getattr(obj, 'key', None) for obj in list(getattr(character, 'contents', []) or [])]}"
        elif case_name == "coffer-flow":
            room = build_temp_room("coffer_flow")
            character = build_character(room, "coffer_flow")
            captured, originals = _capture_object_messages(character)
            aftermath.activate_new_player_state(character)
            character.db.coffer_room = int(getattr(room, "id", 0) or 0)
            aftermath.note_room_entry(character, room)
            locked_result = aftermath.handle_pick(character, "coffer")
            locked_messages = "\n".join(captured.get(character) or [])
            captured[character].clear()
            corpse_result = aftermath.handle_search(character, "raider")
            search_messages = "\n".join(captured.get(character) or [])
            render_after_search = "\n".join(aftermath.get_room_render_lines(character, room))
            captured[character].clear()
            unlocked_result = aftermath.handle_pick(character, "coffer")
            pick_messages = "\n".join(captured.get(character) or [])
            render_after_pick = "\n".join(aftermath.get_room_render_lines(character, room))
            ok = bool(
                locked_result
                and corpse_result
                and unlocked_result
                and "Locked." in locked_messages
                and "basic lockpick" in search_messages
                and "ironbound coffer" in render_after_search
                and "A soft click." in pick_messages
                and "ironbound coffer" not in render_after_pick
            )
            detail = "\n\n".join(filter(None, [locked_messages, search_messages, pick_messages]))
        elif case_name == "coffer-single-instance":
            room = build_temp_room("coffer_single")
            first = build_character(room, "coffer_single_a")
            second = build_character(room, "coffer_single_b")
            aftermath.activate_new_player_state(first)
            aftermath.activate_new_player_state(second)
            first.db.coffer_room = int(getattr(room, "id", 0) or 0)
            second.db.coffer_room = int(getattr(room, "id", 0) or 0)
            aftermath._create_lockpicks(first)
            aftermath._create_lockpicks(second)
            before_first = "\n".join(aftermath.get_room_render_lines(first, room))
            first_result = aftermath.handle_pick(first, "coffer")
            after_first = "\n".join(aftermath.get_room_render_lines(first, room))
            second_view = "\n".join(aftermath.get_room_render_lines(second, room))
            ok = bool(
                first_result
                and "ironbound coffer" in before_first
                and "ironbound coffer" not in after_first
                and "ironbound coffer" in second_view
            )
            detail = f"first_after={after_first!r} second_view={second_view!r}"
        elif case_name == "poi-spawn-weight":
            ambient_room = build_temp_room("poi_ambient")
            poi_room = build_temp_room("poi_weighted", poi_tag="poi_market")
            ambient_hits = 0
            poi_hits = 0
            ambient_room_id = int(getattr(ambient_room, "id", 0) or 0)
            poi_room_id = int(getattr(poi_room, "id", 0) or 0)
            for index in range(24):
                if aftermath._hash_float(f"corpse:{index + 1}:{ambient_room_id}") < aftermath.AMBIENT_SPAWN_CHANCE:
                    ambient_hits += 1
                if aftermath._hash_float(f"corpse:{index + 1}:{poi_room_id}") < aftermath.POI_SPAWN_CHANCE:
                    poi_hits += 1
            ok = bool(
                aftermath.get_spawn_chance_for_room(None, ambient_room) == aftermath.AMBIENT_SPAWN_CHANCE
                and aftermath.get_spawn_chance_for_room(None, poi_room) == aftermath.POI_SPAWN_CHANCE
                and poi_hits > ambient_hits
            )
            detail = f"ambient_hits={ambient_hits} poi_hits={poi_hits} ambient={aftermath.AMBIENT_SPAWN_CHANCE} poi={aftermath.POI_SPAWN_CHANCE}"
        else:
            raise RuntimeError(f"Unknown aftermath case: {case_name}")

        payload = {"scenario": case_name, "ok": bool(ok), "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"DireTest Scenario: {case_name}")
            print(f"Status: {'PASS' if ok else 'FAIL'}")
            if detail:
                print(detail)
        return 0 if ok else 1
    finally:
        _restore_object_messages(originals)
        for obj in reversed(created_objects):
            try:
                obj.delete()
            except Exception:
                pass


@register_scenario("recovery-orderly")
def run_recovery_orderly_scenario(args):
    return _run_aftermath_case(args, "recovery-orderly")


@register_scenario("aftermath-per-player")
def run_aftermath_per_player_scenario(args):
    return _run_aftermath_case(args, "aftermath-per-player")


@register_scenario("aftermath-currency-cap")
def run_aftermath_currency_cap_scenario(args):
    return _run_aftermath_case(args, "aftermath-currency-cap")


@register_scenario("aftermath-full-kit")
def run_aftermath_full_kit_scenario(args):
    return _run_aftermath_case(args, "aftermath-full-kit")


@register_scenario("coffer-flow")
def run_coffer_flow_scenario(args):
    return _run_aftermath_case(args, "coffer-flow")


@register_scenario("coffer-single-instance")
def run_coffer_single_instance_scenario(args):
    return _run_aftermath_case(args, "coffer-single-instance")


@register_scenario("poi-spawn-weight")
def run_poi_spawn_weight_scenario(args):
    return _run_aftermath_case(args, "poi-spawn-weight")


@register_scenario("e2e-full-lifecycle-all-races")
def run_e2e_full_lifecycle_all_races_scenario(args):
    _setup_django()

    from world.races import TEST_RACES

    results = []
    failures = []
    for index, race in enumerate(TEST_RACES):
        print(f"\n=== E2E Lifecycle: {race} ===")
        try:
            result = _run_e2e_full_lifecycle_for_race(race, index)
            results.append(result)
            print(f"[{race}] onboarding complete")
            print(f"[{race}] death triggered")
            print(f"[{race}] resurrected")
            print(f"[{race}] entered live game")
        except Exception as exc:
            failures.append({"race": str(race), "error": str(exc)})
            results.append({"race": str(race), "ok": False, "error": str(exc)})

    output = {
        "scenario": "e2e-full-lifecycle-all-races",
        "races": list(TEST_RACES),
        "results": results,
        "failures": failures,
        "ok": not failures,
    }

    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print("\nDireTest Scenario: e2e-full-lifecycle-all-races")
        print(f"Race Count: {len(TEST_RACES)}")
        for result in results:
            status = "PASS" if result.get("ok") else "FAIL"
            detail = result.get("landing_room") or result.get("error") or "ok"
            print(f"[{status}] {result.get('race')}: {detail}")
        print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
    return 0 if output["ok"] else 1


@register_scenario("e2e-failure-cases")
def run_e2e_failure_cases_scenario(args):
    _setup_django()

    from world.races import TEST_RACES

    results = []
    failures = []
    for index, race in enumerate(TEST_RACES):
        print(f"\n=== E2E Failure Cases: {race} ===")
        try:
            race_results = [
                _run_invalid_onboarding_command_case(race, (index * 10) + 1),
                _run_skip_equip_case(race, (index * 10) + 2),
                _run_drop_weapon_before_death_case(race, (index * 10) + 3),
                _run_early_death_recovery_case(race, (index * 10) + 4),
            ]
            results.append({"race": str(race), "ok": True, "cases": race_results})
            for case in race_results:
                print(f"[{race}] {case.get('case')}: PASS")
        except Exception as exc:
            failures.append({"race": str(race), "error": str(exc)})
            results.append({"race": str(race), "ok": False, "error": str(exc)})

    output = {
        "scenario": "e2e-failure-cases",
        "races": list(TEST_RACES),
        "results": results,
        "failures": failures,
        "ok": not failures,
    }

    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print("\nDireTest Scenario: e2e-failure-cases")
        print(f"Race Count: {len(TEST_RACES)}")
        for result in results:
            status = "PASS" if result.get("ok") else "FAIL"
            detail = result.get("error") or f"{len(list(result.get('cases') or []))} cases"
            print(f"[{status}] {result.get('race')}: {detail}")
        print(f"Status: {'PASS' if output['ok'] else 'FAIL'}")
    return 0 if output["ok"] else 1


@register_scenario("onboarding-movement")
def run_onboarding_movement_scenario(args):
    return _run_locked_onboarding_case(args, "movement")


@register_scenario("training-move")
def run_training_move_scenario(args):
    return _run_locked_onboarding_case(args, "movement")


@register_scenario("training-get")
def run_training_get_scenario(args):
    return _run_locked_onboarding_case(args, "get")


@register_scenario("training-equip")
def run_training_equip_scenario(args):
    return _run_locked_onboarding_case(args, "equip")


@register_scenario("training-equip-alias")
def run_training_equip_alias_scenario(args):
    return _run_locked_onboarding_case(args, "equip-alias")


@register_scenario("training-inventory-skip-nudge")
def run_training_inventory_skip_nudge_scenario(args):
    return _run_locked_onboarding_case(args, "inventory-skip-nudge")


@register_scenario("onboarding-interaction")
def run_onboarding_interaction_scenario(args):
    return _run_locked_onboarding_case(args, "get")


@register_scenario("onboarding-combat")
def run_onboarding_combat_scenario(args):
    return _run_locked_onboarding_case(args, "equip")


@register_scenario("onboarding-complete")
def run_onboarding_complete_scenario(args):
    return _run_locked_onboarding_case(args, "complete")


@register_scenario("training-resurrection-sequence")
def run_training_resurrection_sequence_scenario(args):
    return _run_locked_onboarding_case(args, "resurrection-sequence")


@register_scenario("training-between-state-lock")
def run_training_between_state_lock_scenario(args):
    return _run_locked_onboarding_case(args, "between-lock")


@register_scenario("training-transport-sequence")
def run_training_transport_sequence_scenario(args):
    return _run_locked_onboarding_case(args, "transport-sequence")


@register_scenario("training-final-location")
def run_training_final_location_scenario(args):
    return _run_locked_onboarding_case(args, "final-location")


@register_scenario("training-control-return")
def run_training_control_return_scenario(args):
    return _run_locked_onboarding_case(args, "control-return")


@register_scenario("training-npc-presence")
def run_training_npc_presence_scenario(args):
    return _run_locked_onboarding_case(args, "npc-presence")


@register_scenario("training-recovery-state")
def run_training_recovery_state_scenario(args):
    return _run_locked_onboarding_case(args, "recovery-state")


@register_scenario("chargen-mirror-cycle")
def run_chargen_mirror_cycle_scenario(args):
    return _run_chargen_mirror_case(args, "cycle")


@register_scenario("chargen-lock-flow")
def run_chargen_lock_flow_scenario(args):
    return _run_chargen_mirror_case(args, "lock-flow")


@register_scenario("chargen-race-lock")
def run_chargen_race_lock_scenario(args):
    return _run_chargen_mirror_case(args, "race-lock")


@register_scenario("chargen-mirror-render")
def run_chargen_mirror_render_scenario(args):
    return _run_chargen_mirror_case(args, "render")


@register_scenario("chargen-transition")
def run_chargen_transition_scenario(args):
    return _run_chargen_mirror_case(args, "transition")


@register_scenario("chargen-actions-visible")
def run_chargen_actions_visible_scenario(args):
    return _run_chargen_mirror_case(args, "actions-visible")


@register_scenario("chargen-actions-contextual")
def run_chargen_actions_contextual_scenario(args):
    return _run_chargen_mirror_case(args, "actions-contextual")


@register_scenario("chargen-click-executes")
def run_chargen_click_executes_scenario(args):
    return _run_chargen_mirror_case(args, "click-executes")


@register_scenario("chargen-back-navigation")
def run_chargen_back_navigation_scenario(args):
    return _run_chargen_mirror_case(args, "back-navigation")


@register_scenario("chargen-confirmation-gate")
def run_chargen_confirmation_gate_scenario(args):
    return _run_chargen_mirror_case(args, "confirmation-gate")


@register_scenario("chargen-finalize-lock")
def run_chargen_finalize_lock_scenario(args):
    return _run_chargen_mirror_case(args, "finalize-lock")


@register_scenario("chargen-no-command-needed")
def run_chargen_no_command_needed_scenario(args):
    return _run_chargen_mirror_case(args, "no-command-needed")


@register_scenario("chargen-no-exits")
def run_chargen_no_exits_scenario(args):
    return _run_chargen_mirror_case(args, "no-exits")


@register_scenario("chargen-movement-blocked")
def run_chargen_movement_blocked_scenario(args):
    return _run_chargen_mirror_case(args, "movement-blocked")


@register_scenario("chargen-exit-restored")
def run_chargen_exit_restored_scenario(args):
    return _run_chargen_mirror_case(args, "exit-restored")


@register_scenario("chargen-no-softlock")
def run_chargen_no_softlock_scenario(args):
    return _run_chargen_mirror_case(args, "no-softlock")


@register_scenario("onboarding-blocked-command")
def run_onboarding_blocked_command_scenario(args):
    return _run_locked_onboarding_case(args, "blocked-command")


def _build_exp_test_character(ctx, *, key):
    room = ctx.harness.create_test_room(key=f"{key}_ROOM")
    character = ctx.harness.create_test_character(room=room, key=key)
    character.permissions.add("Developer")
    ctx.character = character
    ctx.room = room
    return character


@register_scenario("exp-xp-injection")
def run_exp_xp_injection_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import award_xp

        character = _build_exp_test_character(ctx, key="TEST_EXP_INJECT_CHAR")
        skill = character.exp_skills.get("evasion")
        gained = ctx.direct(award_xp, skill, 100)
        if gained <= 0 or skill.pool <= 0:
            raise AssertionError(f"XP injection did not increase the pool: gained={gained}, pool={skill.pool}")

        ctx.cmd("skilldebug evasion")
        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "gained": gained,
            "pool": skill.pool,
            "mindstate": skill.mindstate,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-xp-injection")


@register_scenario("exp-hard-stop")
def run_exp_hard_stop_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import award_xp

        character = _build_exp_test_character(ctx, key="TEST_EXP_HARD_STOP_CHAR")
        skill = character.exp_skills.get("evasion")
        first_gain = ctx.direct(award_xp, skill, skill.max_pool)
        before_pool = skill.pool
        second_gain = ctx.direct(award_xp, skill, 1000)
        if first_gain <= 0:
            raise AssertionError("Hard-stop scenario failed to fill the skill pool.")
        if second_gain != 0 or skill.pool != before_pool:
            raise AssertionError(f"Mind lock hard stop failed: second_gain={second_gain}, before={before_pool}, after={skill.pool}")

        ctx.cmd("skilldebug evasion")
        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "first_gain": first_gain,
            "second_gain": second_gain,
            "pool": skill.pool,
            "mindstate": skill.mindstate,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-hard-stop")


@register_scenario("exp-difficulty-curve")
def run_exp_difficulty_curve_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import SkillState, train

        character = _build_exp_test_character(ctx, key="TEST_EXP_DIFFICULTY_CHAR")
        skill = SkillState("evasion")
        skill.rank = 50
        skill.recalc_pool()

        optimal_gain = ctx.direct(train, skill, 50)
        skill.pool = 0.0
        skill.update_mindstate()
        easy_gain = ctx.direct(train, skill, 10)
        skill.pool = 0.0
        skill.update_mindstate()
        hard_gain = ctx.direct(train, skill, 120)

        if not (optimal_gain > easy_gain and optimal_gain > hard_gain):
            raise AssertionError(
                f"Difficulty curve did not peak at matching rank: optimal={optimal_gain}, easy={easy_gain}, hard={hard_gain}"
            )

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "rank": skill.rank,
            "optimal_gain": optimal_gain,
            "easy_gain": easy_gain,
            "hard_gain": hard_gain,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-difficulty-curve")


@register_scenario("exp-low-rank-boost")
def run_exp_low_rank_boost_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import calculate_xp

        character = _build_exp_test_character(ctx, key="TEST_EXP_LOW_RANK_CHAR")
        low_skill = character.exp_skills.get("evasion")
        low_skill.rank = 0
        low_skill.recalc_pool()
        low_xp = ctx.direct(calculate_xp, low_skill, 10)

        high_skill = character.exp_skills.get("appraisal")
        high_skill.rank = 100
        high_skill.recalc_pool()
        high_xp = ctx.direct(calculate_xp, high_skill, 10)

        if low_xp <= high_xp:
            raise AssertionError(f"Low rank bonus did not increase XP: low={low_xp}, high={high_xp}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "low_rank_xp": low_xp,
            "high_rank_xp": high_xp,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-low-rank-boost")


@register_scenario("exp-miss-learning")
def run_exp_miss_learning_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import train

        character = _build_exp_test_character(ctx, key="TEST_EXP_MISS_CHAR")
        skill = character.exp_skills.get("evasion")
        hit_gain = ctx.direct(train, skill, 20, True)
        skill.pool = 0.0
        skill.update_mindstate()
        miss_gain = ctx.direct(train, skill, 20, False)

        if miss_gain <= 0 or miss_gain >= hit_gain:
            raise AssertionError(f"Miss learning modifier was invalid: hit={hit_gain}, miss={miss_gain}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "hit_gain": hit_gain,
            "miss_gain": miss_gain,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-miss-learning")


@register_scenario("exp-outcome-learning")
def run_exp_outcome_learning_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import award_exp_skill

        character = _build_exp_test_character(ctx, key="TEST_EXP_OUTCOME_CHAR")
        skill = character.exp_skills.get("stealth")
        skill.rank = 13
        skill.recalc_pool()

        fail_gain = ctx.direct(award_exp_skill, character, "stealth", 20, False, "fail")
        skill.pool = 0.0
        skill.update_mindstate()

        partial_gain = ctx.direct(award_exp_skill, character, "stealth", 20, True, "partial")
        skill.pool = 0.0
        skill.update_mindstate()

        success_gain = ctx.direct(award_exp_skill, character, "stealth", 20, True, "success")

        if fail_gain <= 0.0:
            raise AssertionError(f"Failure learning should still grant some XP: {fail_gain}")
        if not (fail_gain < partial_gain < success_gain):
            raise AssertionError(
                f"Outcome learning gains were not ordered failure < partial < success: fail={fail_gain}, partial={partial_gain}, success={success_gain}"
            )

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "fail_gain": fail_gain,
            "partial_gain": partial_gain,
            "success_gain": success_gain,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-outcome-learning")


@register_scenario("exp-event-weight")
def run_exp_event_weight_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import SkillState, calculate_xp

        locksmith_skill = SkillState("locksmithing")
        locksmith_skill.rank = 25
        locksmith_skill.recalc_pool()

        lockpick_easy = ctx.direct(calculate_xp, locksmith_skill, 10, True, "success", "locksmithing")
        lockpick_equal = ctx.direct(calculate_xp, locksmith_skill, 25, True, "success", "locksmithing")
        trap_disarm_equal = ctx.direct(calculate_xp, locksmith_skill, 25, True, "success", "trap_disarm")
        trap_disarm_hard = ctx.direct(calculate_xp, locksmith_skill, 80, True, "success", "trap_disarm")

        combat_skill = SkillState("evasion")
        combat_skill.rank = 25
        combat_skill.recalc_pool()
        evasion_equal = ctx.direct(calculate_xp, combat_skill, 25, True, "success", "evasion")

        if lockpick_equal <= lockpick_easy:
            raise AssertionError(
                f"Difficulty weighting did not reward an on-rank locksmithing event over an easy one: easy={lockpick_easy}, equal={lockpick_equal}"
            )
        if trap_disarm_equal <= lockpick_equal:
            raise AssertionError(
                f"Trap-disarm event weight did not exceed standard locksmithing event weight: trap={trap_disarm_equal}, lockpick={lockpick_equal}"
            )
        if trap_disarm_hard >= trap_disarm_equal:
            raise AssertionError(
                f"Very hard rare-event training should still fall below optimal difficulty: hard={trap_disarm_hard}, equal={trap_disarm_equal}"
            )
        if lockpick_equal <= evasion_equal:
            raise AssertionError(
                f"Rare locksmithing event did not exceed routine combat event at equal rank/difficulty: locksmithing={lockpick_equal}, evasion={evasion_equal}"
            )

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "lockpick_easy": lockpick_easy,
            "lockpick_equal": lockpick_equal,
            "trap_disarm_equal": trap_disarm_equal,
            "trap_disarm_hard": trap_disarm_hard,
            "evasion_equal": evasion_equal,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-event-weight")


@register_scenario("exp-mind-lock")
def run_exp_mind_lock_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import train

        character = _build_exp_test_character(ctx, key="TEST_EXP_MIND_LOCK_CHAR")
        skill = character.exp_skills.get("evasion")
        iterations = 0
        previous_pool = skill.pool
        while skill.mindstate < 34 and iterations < 200:
            ctx.direct(train, skill, 20)
            if skill.pool < previous_pool:
                raise AssertionError("Mind lock scenario decreased the pool unexpectedly.")
            previous_pool = skill.pool
            iterations += 1

        before = skill.pool
        extra_gain = ctx.direct(train, skill, 20)
        if skill.mindstate != 34:
            raise AssertionError(f"Mind lock scenario did not reach 34: {skill.mindstate}")
        if extra_gain != 0 or skill.pool != before:
            raise AssertionError(f"Mind lock scenario kept gaining XP after lock: extra_gain={extra_gain}, before={before}, after={skill.pool}")

        ctx.cmd("skilldebug evasion")
        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "iterations": iterations,
            "pool": skill.pool,
            "mindstate": skill.mindstate,
            "extra_gain": extra_gain,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-mind-lock")


@register_scenario("exp-time-to-lock")
def run_exp_time_to_lock_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import train

        character = _build_exp_test_character(ctx, key="TEST_EXP_TIME_LOCK_CHAR")
        skill = character.exp_skills.get("evasion")
        gains = []
        for _ in range(30):
            gains.append(ctx.direct(train, skill, 20))
            if skill.mindstate >= 34:
                break

        if skill.mindstate < 34:
            raise AssertionError(f"Time-to-lock simulation did not reach mind lock in range: {skill.mindstate}")
        if len(gains) > 30:
            raise AssertionError(f"Time-to-lock simulation exceeded expected iterations: {len(gains)}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "iterations": len(gains),
            "gains": gains,
            "mindstate": skill.mindstate,
            "pool": skill.pool,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-time-to-lock")


@register_scenario("exp-rank-scaling")
def run_exp_rank_scaling_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import SkillState, calculate_xp, rank_scaling, skill_gain_modifier

        low_rank_perception = SkillState("perception")
        low_rank_perception.rank = 1
        low_rank_perception.recalc_pool()

        mid_rank_stealth = SkillState("stealth")
        mid_rank_stealth.rank = 13
        mid_rank_stealth.recalc_pool()

        perception_xp = ctx.direct(calculate_xp, low_rank_perception, 10, True)
        stealth_xp = ctx.direct(calculate_xp, mid_rank_stealth, 10, True)

        if rank_scaling(low_rank_perception.rank) <= rank_scaling(mid_rank_stealth.rank):
            raise AssertionError(
                f"Rank scaling did not favor lower rank skill: {rank_scaling(low_rank_perception.rank)} <= {rank_scaling(mid_rank_stealth.rank)}"
            )
        if skill_gain_modifier("stealth") >= skill_gain_modifier("perception"):
            raise AssertionError(
                f"Stealth modifier should stay below perception modifier: {skill_gain_modifier('stealth')} >= {skill_gain_modifier('perception')}"
            )
        if stealth_xp >= perception_xp:
            raise AssertionError(
                f"Rank-sensitive XP did not reduce mid-rank stealth below low-rank perception: stealth={stealth_xp}, perception={perception_xp}"
            )

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "perception_rank": low_rank_perception.rank,
            "perception_xp": perception_xp,
            "perception_scale": rank_scaling(low_rank_perception.rank),
            "stealth_rank": mid_rank_stealth.rank,
            "stealth_xp": stealth_xp,
            "stealth_scale": rank_scaling(mid_rank_stealth.rank),
            "perception_modifier": skill_gain_modifier("perception"),
            "stealth_modifier": skill_gain_modifier("stealth"),
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-rank-scaling")


@register_scenario("exp-drain-timing")
def run_exp_drain_timing_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import pulse

        character = _build_exp_test_character(ctx, key="TEST_EXP_DRAIN_CHAR")
        skill = character.exp_skills.get("evasion")
        skill.pool = 1000.0
        skill.update_mindstate()

        drains = []
        for _ in range(15):
            drains.append(ctx.direct(pulse, skill))

        if skill.pool > 5.0:
            raise AssertionError(f"Drain timing scenario left too much pool after 15 pulses: {skill.pool}")
        if skill.rank_progress <= 0:
            raise AssertionError("Drain timing scenario did not convert drained pool into rank progress.")
        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "drains": drains,
            "final_pool": skill.pool,
            "rank_progress": skill.rank_progress,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-drain-timing")


@register_scenario("exp-rank-gain")
def run_exp_rank_gain_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import award_xp, pulse

        character = _build_exp_test_character(ctx, key="TEST_EXP_RANK_GAIN_CHAR")
        skill = character.exp_skills.get("evasion")
        before_rank = skill.rank
        skill.rank_progress = 500.0
        ctx.direct(award_xp, skill, skill.max_pool)
        for _ in range(20):
            ctx.direct(pulse, skill)
            if skill.rank > before_rank:
                break

        if skill.rank <= before_rank:
            raise AssertionError(f"Rank gain scenario did not increase rank: before={before_rank}, after={skill.rank}")

        ctx.cmd("skilldebug evasion")
        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "before_rank": before_rank,
            "after_rank": skill.rank,
            "rank_progress": skill.rank_progress,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-rank-gain")


@register_scenario("exp-skillset-drain")
def run_exp_skillset_drain_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import SkillState, drain_skill

        character = _build_exp_test_character(ctx, key="TEST_EXP_SKILLSET_DRAIN_CHAR")
        primary = SkillState("evasion")
        secondary = SkillState("athletics")
        tertiary = SkillState("perception")

        primary.skillset = "primary"
        secondary.skillset = "secondary"
        tertiary.skillset = "tertiary"

        for skill in (primary, secondary, tertiary):
            skill.pool = 1000.0
            skill.rank_progress = 0.0
            skill.recalc_pool()
            skill.pool = 1000.0
            skill.update_mindstate()

        primary_drain = ctx.direct(drain_skill, primary)
        secondary_drain = ctx.direct(drain_skill, secondary)
        tertiary_drain = ctx.direct(drain_skill, tertiary)

        if not (primary_drain > secondary_drain > tertiary_drain):
            raise AssertionError(
                f"Skillset drain rates were not ordered primary > secondary > tertiary: {primary_drain}, {secondary_drain}, {tertiary_drain}"
            )

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "primary_drain": primary_drain,
            "secondary_drain": secondary_drain,
            "tertiary_drain": tertiary_drain,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-skillset-drain")


@register_scenario("exp-wisdom-drain")
def run_exp_wisdom_drain_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import drain_skill

        character = _build_exp_test_character(ctx, key="TEST_EXP_WISDOM_DRAIN_CHAR")
        normal_skill = character.exp_skills.get("evasion")
        high_wis_skill = character.exp_skills.get("athletics")

        for skill in (normal_skill, high_wis_skill):
            skill.skillset = "primary"
            skill.pool = 1000.0
            skill.rank_progress = 0.0
            skill.recalc_pool()
            skill.pool = 1000.0
            skill.update_mindstate()

        normal_drain = ctx.direct(drain_skill, normal_skill, 30)
        high_wis_drain = ctx.direct(drain_skill, high_wis_skill, 60)

        if high_wis_drain <= normal_drain:
            raise AssertionError(f"Wisdom modifier did not increase drain: normal={normal_drain}, high={high_wis_drain}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "normal_drain": normal_drain,
            "high_wis_drain": high_wis_drain,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-wisdom-drain")


@register_scenario("exp-single-tick")
def run_exp_single_tick_scenario(args):
    _setup_django()

    def scenario(ctx):
        import time

        from world.systems import exp_pulse

        character = _build_exp_test_character(ctx, key="TEST_EXP_SINGLE_TICK_CHAR")
        skill = character.exp_skills.get("stealth")
        skill.pool = 1000.0
        skill.last_trained = time.time()
        skill.update_mindstate()

        exp_pulse.GLOBAL_TICK = 0
        ctx.cmd("skilldebug tick")

        if exp_pulse.GLOBAL_TICK != exp_pulse.PULSE_TICK:
            raise AssertionError(f"Single tick scenario did not advance global tick: {exp_pulse.GLOBAL_TICK}")
        if skill.pool >= 1000.0:
            raise AssertionError(f"Single tick scenario did not drain eligible offset skill: {skill.pool}")
        if "Tick executed" not in "\n".join(ctx.output_log):
            raise AssertionError(f"Single tick scenario did not emit tick confirmation: {ctx.output_log}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "global_tick": exp_pulse.GLOBAL_TICK,
            "remaining_pool": skill.pool,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-single-tick")


@register_scenario("exp-offset-behavior")
def run_exp_offset_behavior_scenario(args):
    _setup_django()

    def scenario(ctx):
        import time

        from world.systems import exp_pulse

        character = _build_exp_test_character(ctx, key="TEST_EXP_OFFSET_CHAR")
        evasion = character.exp_skills.get("evasion")
        stealth = character.exp_skills.get("stealth")

        evasion.pool = 1000.0
        stealth.pool = 1000.0
        evasion.last_trained = time.time()
        stealth.last_trained = time.time()
        evasion.update_mindstate()
        stealth.update_mindstate()
        exp_pulse.GLOBAL_TICK = 0

        evasion_pools = []
        stealth_pools = []
        ticks = []
        for _ in range(10):
            ticks.append(ctx.direct(exp_pulse.exp_pulse_tick))
            evasion_pools.append(evasion.pool)
            stealth_pools.append(stealth.pool)

        if evasion_pools[0] != 1000.0:
            raise AssertionError(f"Offset behavior drained evasion before offset 0: {evasion_pools}")
        if stealth_pools[0] >= 1000.0:
            raise AssertionError(f"Offset behavior did not drain stealth at offset 20: {stealth_pools}")
        if evasion_pools[8] != 1000.0:
            raise AssertionError(f"Offset behavior drained evasion before the full cycle completed: {evasion_pools}")
        if evasion_pools[9] >= 1000.0:
            raise AssertionError(f"Offset behavior did not drain evasion at offset 0 after full cycle: {evasion_pools}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "ticks": ticks,
            "evasion_pools": evasion_pools,
            "stealth_pools": stealth_pools,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-offset-behavior")


@register_scenario("exp-multi-skill-tick")
def run_exp_multi_skill_tick_scenario(args):
    _setup_django()

    def scenario(ctx):
        import time

        from world.systems import exp_pulse

        character = _build_exp_test_character(ctx, key="TEST_EXP_MULTI_TICK_CHAR")
        evasion = character.exp_skills.get("evasion")
        stealth = character.exp_skills.get("stealth")
        appraisal = character.exp_skills.get("appraisal")

        for skill in (evasion, stealth, appraisal):
            skill.pool = 1000.0
            skill.last_trained = time.time()
            skill.update_mindstate()

        exp_pulse.GLOBAL_TICK = 0
        tick_states = []
        for _ in range(10):
            current_tick = ctx.direct(exp_pulse.exp_pulse_tick)
            tick_states.append(
                {
                    "tick": current_tick,
                    "evasion": evasion.pool,
                    "stealth": stealth.pool,
                    "appraisal": appraisal.pool,
                }
            )

        tick_20 = tick_states[0]
        tick_40 = tick_states[1]
        tick_0 = tick_states[9]

        if not (tick_20["stealth"] < 1000.0 and tick_20["evasion"] == 1000.0 and tick_20["appraisal"] == 1000.0):
            raise AssertionError(f"Multi-skill tick scenario failed staggered drain at tick 20: {tick_20}")
        if not (tick_40["appraisal"] < 1000.0 and tick_40["evasion"] == 1000.0):
            raise AssertionError(f"Multi-skill tick scenario failed staggered drain at tick 40: {tick_40}")
        if not (tick_0["evasion"] < 1000.0 and tick_0["stealth"] < 1000.0 and tick_0["appraisal"] < 1000.0):
            raise AssertionError(f"Multi-skill tick scenario failed to reach evasion offset by full cycle: {tick_0}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "tick_states": tick_states,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-multi-skill-tick")


@register_scenario("exp-inactive-skill")
def run_exp_inactive_skill_scenario(args):
    _setup_django()

    def scenario(ctx):
        import time

        from world.systems import exp_pulse
        from world.systems.skills import ACTIVE_WINDOW, GRACE_WINDOW, train

        character = _build_exp_test_character(ctx, key="TEST_EXP_INACTIVE_CHAR")
        skill = character.exp_skills.get("stealth")
        ctx.direct(train, skill, 20)
        before_pool = skill.pool
        skill.last_trained = time.time() - (ACTIVE_WINDOW + GRACE_WINDOW + 1)

        exp_pulse.GLOBAL_TICK = 0
        current_tick = ctx.direct(exp_pulse.exp_pulse_tick)

        if current_tick != 20:
            raise AssertionError(f"Inactive skill scenario did not advance global tick as expected: {current_tick}")
        if skill.pool != before_pool:
            raise AssertionError(f"Inactive skill drained outside the activity window: before={before_pool}, after={skill.pool}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "before_pool": before_pool,
            "after_pool": skill.pool,
            "last_trained": skill.last_trained,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-inactive-skill")


@register_scenario("exp-active-skill-only")
def run_exp_active_skill_only_scenario(args):
    _setup_django()

    def scenario(ctx):
        import time

        from world.systems import exp_pulse
        from world.systems.skills import ACTIVE_WINDOW, GRACE_WINDOW, train

        character = _build_exp_test_character(ctx, key="TEST_EXP_ACTIVE_ONLY_CHAR")
        active_skill = character.exp_skills.get("stealth")
        inactive_skill = character.exp_skills.get("locksmithing")

        ctx.direct(train, active_skill, 20)
        inactive_skill.pool = active_skill.pool
        inactive_skill.update_mindstate()
        inactive_skill.last_trained = time.time() - (ACTIVE_WINDOW + GRACE_WINDOW + 1)

        before_active = active_skill.pool
        before_inactive = inactive_skill.pool
        exp_pulse.GLOBAL_TICK = 0
        ctx.direct(exp_pulse.exp_pulse_tick)

        if active_skill.pool >= before_active:
            raise AssertionError(f"Active-skill-only scenario did not drain the active skill: before={before_active}, after={active_skill.pool}")
        if inactive_skill.pool != before_inactive:
            raise AssertionError(f"Active-skill-only scenario drained the inactive skill: before={before_inactive}, after={inactive_skill.pool}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "before_active": before_active,
            "after_active": active_skill.pool,
            "before_inactive": before_inactive,
            "after_inactive": inactive_skill.pool,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-active-skill-only")


@register_scenario("exp-mindstate-transitions")
def run_exp_mindstate_transitions_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import SkillState, award_xp

        character = _build_exp_test_character(ctx, key="TEST_EXP_MINDSTATE_TRANSITIONS_CHAR")
        skill = SkillState("evasion", owner=character)

        ctx.direct(award_xp, skill, 35)
        skill.last_feedback_time = 0.0
        ctx.direct(award_xp, skill, 115)
        skill.last_feedback_time = 0.0
        ctx.direct(award_xp, skill, 440)
        skill.last_feedback_time = 0.0
        ctx.direct(award_xp, skill, 410)

        transcript = "\n".join(ctx.output_log)
        expected_messages = [
            "You feel your evasion settling into dabbling.",
            "You feel your evasion settling into thinking.",
            "You feel your evasion settling into absorbed.",
            "Your evasion is fully absorbed. You can learn no more.",
        ]
        for message in expected_messages:
            if message not in transcript:
                raise AssertionError(f"Missing mindstate transition message: {message}\nTranscript:\n{transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "mindstate": skill.mindstate,
            "mindstate_name": skill.mindstate_name(),
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-mindstate-transitions")


@register_scenario("exp-no-spam")
def run_exp_no_spam_scenario(args):
    _setup_django()

    def scenario(ctx):
        import time

        from world.systems.skills import pulse

        character = _build_exp_test_character(ctx, key="TEST_EXP_NO_SPAM_CHAR")
        skill = character.exp_skills.get("evasion")
        skill.pool = 500.0
        skill.last_trained = time.time()
        skill.update_mindstate()
        skill.last_mindstate_name = skill.mindstate_name()
        ctx.output_log.clear()

        skill.last_feedback_time = 0.0
        ctx.direct(pulse, skill)
        skill.last_feedback_time = 0.0
        ctx.direct(pulse, skill)
        skill.last_feedback_time = 0.0
        ctx.direct(pulse, skill)

        attentive_message = "You feel your evasion settling into attentive."
        attentive_count = sum(1 for entry in ctx.output_log if attentive_message in str(entry))
        if attentive_count != 1:
            raise AssertionError(f"Expected one attentive transition message, got {attentive_count}: {ctx.output_log}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "final_mindstate": skill.mindstate,
            "final_mindstate_name": skill.mindstate_name(),
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-no-spam")


@register_scenario("exp-command-active")
def run_exp_command_active_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import award_xp

        character = _build_exp_test_character(ctx, key="TEST_EXP_COMMAND_ACTIVE_CHAR")
        evasion = character.exp_skills.get("evasion")
        stealth = character.exp_skills.get("stealth")
        stealth.rank = 18
        stealth.recalc_pool()
        ctx.direct(award_xp, evasion, 120)

        ctx.cmd("experience")
        transcript = "\n".join(ctx.output_log)
        if "evasion" not in transcript:
            raise AssertionError(f"experience did not show active skill: {transcript}")
        if "stealth" in transcript:
            raise AssertionError(f"experience showed inactive skill: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-command-active")


@register_scenario("exp-command-all")
def run_exp_command_all_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.skills import award_xp

        character = _build_exp_test_character(ctx, key="TEST_EXP_COMMAND_ALL_CHAR")
        evasion = character.exp_skills.get("evasion")
        stealth = character.exp_skills.get("stealth")
        evasion.rank = 25
        stealth.rank = 18
        evasion.recalc_pool()
        stealth.recalc_pool()
        ctx.direct(award_xp, evasion, 120)

        ctx.cmd("experience all")
        transcript = "\n".join(ctx.output_log).lower()
        if "evasion" not in transcript or "stealth" not in transcript:
            raise AssertionError(f"experience all did not show all skills: {transcript}")
        if "total ranks displayed:" not in transcript:
            raise AssertionError(f"experience all did not include footer: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="exp-command-all")


@register_scenario(
    "exp-stealth-bridge",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_stealth_bridge_scenario(args):
    _setup_django()

    def scenario(ctx):
        from typeclasses.abilities import get_ability
        from world.systems.scheduler import flush_due

        character = _build_exp_test_character(ctx, key="TEST_EXP_STEALTH_BRIDGE_CHAR")
        observer = ctx.harness.create_test_character(room=ctx.room, key="TEST_EXP_STEALTH_OBSERVER")
        observer.ensure_core_defaults()
        observer.update_skill("perception", rank=12, mindstate=0)
        character.update_skill("stealth", rank=20, mindstate=0)

        ctx.cmd("hide")

        stealth_skill = character.exp_skills.get("stealth")
        legacy_mindstate = int(((character.db.skills or {}).get("stealth") or {}).get("mindstate", 0) or 0)
        if stealth_skill.pool != 0:
            raise AssertionError(f"Hide paid stealth XP before roundtime resolved: pool={stealth_skill.pool}")

        time.sleep(2.1)
        ctx.direct(flush_due)

        if stealth_skill.pool <= 0:
            raise AssertionError(f"Hide did not train stealth in exp_skills after roundtime resolution: pool={stealth_skill.pool}")
        if legacy_mindstate != 0:
            raise AssertionError(f"Legacy stealth mindstate remained authoritative: legacy={legacy_mindstate}")

        ctx.output_log.clear()
        ctx.cmd("exp all")
        transcript = "\n".join(ctx.output_log)
        if "stealth" not in transcript.lower():
            raise AssertionError(f"exp all did not show stealth after hide: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "stealth_pool": stealth_skill.pool,
            "legacy_mindstate": legacy_mindstate,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-stealth-bridge",
        scenario_metadata=getattr(run_exp_stealth_bridge_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-stealth-no-observer",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate delayed stealth routing and should not fail on host timing drift.",
    },
)
def run_exp_stealth_no_observer_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.scheduler import flush_due

        character = _build_exp_test_character(ctx, key="TEST_EXP_STEALTH_NO_OBSERVER_CHAR")
        character.update_skill("stealth", rank=5, mindstate=0)

        ctx.cmd("hide")

        stealth_skill = character.exp_skills.get("stealth")
        if stealth_skill.pool != 0:
            raise AssertionError(f"No-observer hide paid stealth XP before roundtime resolved: pool={stealth_skill.pool}")

        time.sleep(2.1)
        ctx.direct(flush_due)

        if stealth_skill.pool <= 0:
            raise AssertionError(f"Low-rank no-observer hide did not pay any delayed stealth XP: pool={stealth_skill.pool}")
        if stealth_skill.mindstate != 0:
            raise AssertionError(
                f"Low-rank no-observer hide should remain sub-threshold after one hide: pool={stealth_skill.pool}, mindstate={stealth_skill.mindstate}"
            )

        learning_state = dict(getattr(character.db, "stealth_learning", None) or {})
        last_contest = dict(learning_state.get("last_contest") or {})
        if bool(last_contest.get("contest_occurred", False)):
            raise AssertionError(f"No-observer hide incorrectly recorded a contest: {last_contest}")

        ctx.output_log.clear()
        ctx.cmd("exp all")
        transcript = "\n".join(ctx.output_log).lower()
        if "stealth" not in transcript:
            raise AssertionError(f"exp all did not show stealth after no-observer hide: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "stealth_pool": stealth_skill.pool,
            "mindstate": stealth_skill.mindstate,
            "last_contest": last_contest,
            "rank": stealth_skill.rank,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-stealth-no-observer",
        scenario_metadata=getattr(run_exp_stealth_no_observer_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-stealth-practice-cap",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Practice-cap probes validate the solo-learning threshold rather than environment-dependent command latency.",
    },
)
def run_exp_stealth_practice_cap_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.scheduler import flush_due

        def run_single(rank):
            character = _build_exp_test_character(ctx, key=f"TEST_EXP_STEALTH_PRACTICE_{rank}")
            character.update_skill("stealth", rank=rank, mindstate=0)
            stealth_skill = character.exp_skills.get("stealth")

            before_pool = stealth_skill.pool
            ctx.output_log.clear()
            ctx.cmd("hide")
            if not character.is_hidden():
                transcript = "\n".join(ctx.output_log)
                raise AssertionError(f"Practice hide unexpectedly failed at rank {rank}: {transcript}")

            time.sleep(2.1)
            ctx.direct(flush_due)
            gain = stealth_skill.pool - before_pool
            last_contest = dict((dict(getattr(character.db, "stealth_learning", None) or {})).get("last_contest") or {})
            ctx.direct(character.break_stealth)
            return gain, last_contest, stealth_skill.rank

        low_gain, low_contest, low_rank = run_single(5)
        mid_gain, mid_contest, mid_rank = run_single(12)
        cap_gain, cap_contest, cap_rank = run_single(16)

        if low_gain <= 0:
            raise AssertionError(f"Low-rank solo practice did not award XP: gain={low_gain}")
        if mid_gain <= 0:
            raise AssertionError(f"Mid-rank solo practice did not award XP below the cap: gain={mid_gain}")
        if low_gain <= mid_gain:
            raise AssertionError(f"Solo practice did not decay toward the cap: low={low_gain}, mid={mid_gain}")
        if cap_gain != 0:
            raise AssertionError(f"Solo practice did not hard-stop above the cap: gain={cap_gain}")
        if bool(low_contest.get("contest_occurred", False)) or bool(mid_contest.get("contest_occurred", False)) or bool(cap_contest.get("contest_occurred", False)):
            raise AssertionError(
                f"Practice-cap probe incorrectly recorded contests: low={low_contest}, mid={mid_contest}, cap={cap_contest}"
            )

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "low_rank": low_rank,
            "low_gain": low_gain,
            "mid_rank": mid_rank,
            "mid_gain": mid_gain,
            "cap_rank": cap_rank,
            "cap_gain": cap_gain,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-stealth-practice-cap",
        scenario_metadata=getattr(run_exp_stealth_practice_cap_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-stealth-empty-room-loop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Stealth feel probes measure delayed no-observer pacing and should not fail on host timing drift.",
    },
)
def run_exp_stealth_empty_room_loop_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.scheduler import flush_due

        character = _build_exp_test_character(ctx, key="TEST_EXP_STEALTH_EMPTY_ROOM_CHAR")
        character.update_skill("stealth", rank=13, mindstate=0)

        stealth_skill = character.exp_skills.get("stealth")
        gains = []
        success_count = 0

        for attempt in range(5):
            ctx.output_log.clear()
            before_pool = stealth_skill.pool
            ctx.cmd("hide")
            if not character.is_hidden():
                transcript = "\n".join(ctx.output_log)
                raise AssertionError(f"Empty-room hide unexpectedly failed on attempt {attempt + 1}: {transcript}")

            success_count += 1
            time.sleep(2.1)
            ctx.direct(flush_due)
            after_pool = stealth_skill.pool
            gains.append(after_pool - before_pool)
            ctx.direct(character.break_stealth)

        if any(gain <= 0 for gain in gains):
            raise AssertionError(f"Empty-room hide loop produced a non-positive delayed gain: {gains}")
        if gains[-1] >= gains[0]:
            raise AssertionError(f"Empty-room hide loop did not diminish over repeated no-observer attempts: {gains}")

        learning_state = dict(getattr(character.db, "stealth_learning", None) or {})
        last_contest = dict(learning_state.get("last_contest") or {})
        if bool(last_contest.get("contest_occurred", False)):
            raise AssertionError(f"Empty-room hide loop incorrectly recorded a contest: {last_contest}")

        ctx.output_log.clear()
        ctx.cmd("exp all")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "success_count": success_count,
            "attempt_count": 5,
            "gains": gains,
            "final_pool": stealth_skill.pool,
            "final_mindstate": stealth_skill.mindstate,
            "last_contest": last_contest,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-stealth-empty-room-loop",
        scenario_metadata=getattr(run_exp_stealth_empty_room_loop_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-stealth-failure-margins",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Failure-margin probes validate stealth payout ordering rather than environment-dependent command latency.",
    },
)
def run_exp_stealth_failure_margins_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.scheduler import flush_due

        character = _build_exp_test_character(ctx, key="TEST_EXP_STEALTH_FAILURE_MARGIN_CHAR")
        character.update_skill("stealth", rank=20, mindstate=0)
        stealth_skill = character.exp_skills.get("stealth")

        gains = {}
        for label, margin in (("terrible", -60), ("moderate", -20), ("near_miss", -5)):
            before_pool = stealth_skill.pool
            ctx.direct(
                character.record_stealth_contest,
                "hide",
                20,
                result={"outcome": "fail", "diff": margin},
                target=ctx.room,
                roundtime=0.0,
                event_key="stealth",
                require_hidden=False,
            )
            ctx.direct(flush_due)
            gains[label] = stealth_skill.pool - before_pool

        if not (gains["terrible"] < gains["moderate"] < gains["near_miss"]):
            raise AssertionError(f"Failure margin scaling did not increase with closer misses: {gains}")

        command_room = ctx.harness.create_test_room(key="TEST_EXP_STEALTH_FAILURE_COMMAND_ROOM")
        command_character = ctx.harness.create_test_character(room=command_room, key="TEST_EXP_STEALTH_FAILURE_COMMAND_CHAR")
        observer = ctx.harness.create_test_character(room=command_room, key="TEST_EXP_STEALTH_FAILURE_COMMAND_OBSERVER")
        command_character.permissions.add("Developer")
        command_character.ensure_core_defaults()
        observer.ensure_core_defaults()
        command_character.update_skill("stealth", rank=13, mindstate=0)
        observer.update_skill("perception", rank=80, mindstate=0)
        command_character.db.stats["agility"] = 20
        command_character.db.stats["reflex"] = 20
        observer.db.stats["agility"] = 40
        observer.db.stats["reflex"] = 40

        command_skill = command_character.exp_skills.get("stealth")
        before_command_pool = command_skill.pool
        ctx.character = command_character
        ctx.room = command_room
        ctx.output_log.clear()
        ctx.cmd("hide")
        if command_character.is_hidden():
            transcript = "\n".join(ctx.output_log)
            raise AssertionError(f"Crowded failure probe unexpectedly hid the actor: {transcript}")

        time.sleep(2.1)
        ctx.direct(flush_due)
        command_gain = command_skill.pool - before_command_pool
        learning_state = dict(getattr(command_character.db, "stealth_learning", None) or {})
        last_contest = dict(learning_state.get("last_contest") or {})
        if str(last_contest.get("outcome", "") or "") != "fail":
            raise AssertionError(f"Crowded failure probe did not record a failed hide: {last_contest}")
        if command_gain <= 0:
            raise AssertionError(
                f"Failed hide through the real command path did not award delayed stealth XP: gain={command_gain}, contest={last_contest}"
            )

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "gains": gains,
            "command_fail_gain": command_gain,
            "command_fail_contest": last_contest,
            "final_pool": stealth_skill.pool,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-stealth-failure-margins",
        scenario_metadata=getattr(run_exp_stealth_failure_margins_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-stealth-perception-dual",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_stealth_perception_dual_scenario(args):
    _setup_django()

    def scenario(ctx):
        from typeclasses.abilities import get_ability
        from world.systems.scheduler import flush_due

        room = ctx.harness.create_test_room(key="TEST_EXP_STEALTH_PERCEPTION_ROOM")
        stealth_actor = ctx.harness.create_test_character(room=room, key="TEST_EXP_STEALTH_ACTOR")
        observer = ctx.harness.create_test_character(room=room, key="TEST_EXP_PERCEPTION_ACTOR")
        ctx.character = stealth_actor
        ctx.room = room

        stealth_actor.ensure_core_defaults()
        observer.ensure_core_defaults()
        stealth_actor.update_skill("stealth", rank=25, mindstate=0)
        observer.update_skill("perception", rank=25, mindstate=0)

        ctx.cmd("hide")
        ctx.direct(get_ability("search", observer).execute, observer)

        if stealth_actor.exp_skills.get("stealth").pool != 0:
            raise AssertionError("Stealth actor gained hide XP before roundtime resolution.")

        time.sleep(2.1)
        ctx.direct(flush_due)

        stealth_pool = stealth_actor.exp_skills.get("stealth").pool
        perception_pool = observer.exp_skills.get("perception").pool
        if stealth_pool <= 0:
            raise AssertionError(f"Stealth actor did not train in exp_skills: {stealth_pool}")
        if perception_pool <= 0:
            raise AssertionError(f"Observer did not train perception in exp_skills: {perception_pool}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "stealth_pool": stealth_pool,
            "perception_pool": perception_pool,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-stealth-perception-dual",
        scenario_metadata=getattr(run_exp_stealth_perception_dual_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-stealth-observer-aggregation",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Observer aggregation probes validate strongest-watcher weighting rather than environment-dependent command latency.",
    },
)
def run_exp_stealth_observer_aggregation_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.scheduler import flush_due

        def run_case(case_name, actor_rank, actor_stats, observer_specs, attempts=8):
            room = ctx.harness.create_test_room(key=f"TEST_STEALTH_AGG_{case_name}_ROOM")
            actor = ctx.harness.create_test_character(room=room, key=f"TEST_STEALTH_AGG_{case_name}_ACTOR")
            actor.permissions.add("Developer")
            actor.ensure_core_defaults()
            actor.update_skill("stealth", rank=actor_rank, mindstate=0)
            actor.db.stats["agility"] = int(actor_stats.get("agility", 20))
            actor.db.stats["reflex"] = int(actor_stats.get("reflex", 20))
            ctx.character = actor
            ctx.room = room

            for index, spec in enumerate(list(observer_specs or [])):
                observer = ctx.harness.create_test_character(room=room, key=f"TEST_STEALTH_AGG_{case_name}_OBS_{index}")
                observer.ensure_core_defaults()
                observer.update_skill("perception", rank=int(spec.get("rank", 1) or 1), mindstate=0)
                observer.db.stats["agility"] = int(spec.get("agility", 10) or 10)
                observer.db.stats["reflex"] = int(spec.get("reflex", 10) or 10)

            skill = actor.exp_skills.get("stealth")
            margins = []
            outcomes = []
            observer_pressures = []
            support_pressures = []
            crowd_penalties = []
            success_count = 0
            severe_fail_count = 0

            for _ in range(attempts):
                ctx.output_log.clear()
                ctx.cmd("hide")
                time.sleep(2.1)
                ctx.direct(flush_due)
                last_contest = dict((dict(getattr(actor.db, "stealth_learning", None) or {})).get("last_contest") or {})
                margin = int(last_contest.get("margin", 0) or 0)
                outcome = str(last_contest.get("outcome", "fail") or "fail")
                margins.append(margin)
                outcomes.append(outcome)
                observer_pressures.append(float(last_contest.get("observer_pressure", 0.0) or 0.0))
                support_pressures.append(float(last_contest.get("support_pressure", 0.0) or 0.0))
                crowd_penalties.append(float(last_contest.get("crowd_penalty", 0.0) or 0.0))
                if outcome != "fail":
                    success_count += 1
                if margin <= -50:
                    severe_fail_count += 1
                actor.break_stealth()

            return {
                "case": case_name,
                "attempts": attempts,
                "margins": margins,
                "outcomes": outcomes,
                "success_count": success_count,
                "severe_fail_count": severe_fail_count,
                "avg_observer_pressure": sum(observer_pressures) / max(1, len(observer_pressures)),
                "avg_support_pressure": sum(support_pressures) / max(1, len(support_pressures)),
                "avg_crowd_penalty": sum(crowd_penalties) / max(1, len(crowd_penalties)),
            }

        single_strong = run_case(
            "single_strong",
            actor_rank=10,
            actor_stats={"agility": 10, "reflex": 10},
            observer_specs=[{"rank": 100, "agility": 40, "reflex": 40}],
        )
        many_weak = run_case(
            "many_weak",
            actor_rank=200,
            actor_stats={"agility": 20, "reflex": 20},
            observer_specs=[{"rank": 5, "agility": 5, "reflex": 5} for _ in range(12)],
        )
        strong_cluster = run_case(
            "strong_cluster",
            actor_rank=200,
            actor_stats={"agility": 20, "reflex": 20},
            observer_specs=[
                {"rank": 180, "agility": 30, "reflex": 30},
                {"rank": 120, "agility": 20, "reflex": 20},
                {"rank": 120, "agility": 20, "reflex": 20},
                *[{"rank": 10, "agility": 5, "reflex": 5} for _ in range(8)],
            ],
        )

        if single_strong["success_count"] != 0 or single_strong["severe_fail_count"] < 4:
            raise AssertionError(f"Single strong observer should produce mostly severe failures: {single_strong}")
        if many_weak["success_count"] <= 0 or many_weak["severe_fail_count"] >= many_weak["attempts"]:
            raise AssertionError(f"Many weak observers should remain beatable for elite stealth: {many_weak}")
        if strong_cluster["success_count"] <= 0 or strong_cluster["severe_fail_count"] >= strong_cluster["attempts"]:
            raise AssertionError(f"Strong observer cluster should be hard but not impossible: {strong_cluster}")
        if many_weak["avg_observer_pressure"] >= strong_cluster["avg_observer_pressure"]:
            raise AssertionError(
                f"Many weak observers should add less total pressure than a strong cluster: weak={many_weak}, cluster={strong_cluster}"
            )

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "single_strong": single_strong,
            "many_weak": many_weak,
            "strong_cluster": strong_cluster,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-stealth-observer-aggregation",
        scenario_metadata=getattr(run_exp_stealth_observer_aggregation_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-stealth-state-machine",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Stealth scheduling validation depends on short roundtime waits and should report lag without failing on host timing drift.",
    },
)
def run_exp_stealth_state_machine_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.scheduler import flush_due

        character = _build_exp_test_character(ctx, key="TEST_EXP_STEALTH_STATE_MACHINE_CHAR")
        observer = ctx.harness.create_test_character(room=ctx.room, key="TEST_EXP_STEALTH_STATE_MACHINE_OBSERVER")
        observer.ensure_core_defaults()
        observer.update_skill("perception", rank=12, mindstate=0)
        character.update_skill("stealth", rank=25, mindstate=0)

        ctx.cmd("hide")
        stealth_skill = character.exp_skills.get("stealth")
        if stealth_skill.pool != 0:
            raise AssertionError(f"Stealth state machine paid XP before roundtime: {stealth_skill.pool}")

        time.sleep(2.1)
        ctx.direct(flush_due)
        first_gain = stealth_skill.pool
        if first_gain <= 0:
            raise AssertionError(f"Stealth state machine did not pay after maintained concealment: {first_gain}")

        ctx.direct(character.break_stealth)
        ctx.cmd("hide")
        cancelled_before = stealth_skill.pool
        ctx.direct(character.break_stealth)
        time.sleep(2.1)
        ctx.direct(flush_due)
        cancelled_after = stealth_skill.pool
        if cancelled_after != cancelled_before:
            raise AssertionError(
                f"Stealth state machine paid despite broken concealment: before={cancelled_before}, after={cancelled_after}"
            )

        ctx.cmd("hide")
        time.sleep(2.1)
        ctx.direct(flush_due)
        repeated_total = stealth_skill.pool
        repeated_gain = repeated_total - cancelled_after
        if repeated_gain <= 0:
            raise AssertionError(f"Repeated maintained hide did not pay any XP: total={repeated_total}, prior={cancelled_after}")
        if repeated_gain >= first_gain:
            raise AssertionError(f"Repeated hide did not diminish against the same observer context: first={first_gain}, repeated={repeated_gain}")

        learning_state = dict(getattr(character.db, "stealth_learning", None) or {})
        last_contest = dict(learning_state.get("last_contest") or {})
        if not bool(last_contest.get("contest_occurred", False)):
            raise AssertionError(f"Stealth state machine did not persist contest context: {learning_state}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "first_gain": first_gain,
            "cancelled_gain": cancelled_after - cancelled_before,
            "repeated_gain": repeated_gain,
            "last_contest": last_contest,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-stealth-state-machine",
        scenario_metadata=getattr(run_exp_stealth_state_machine_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-appraisal-loop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_appraisal_loop_scenario(args):
    _setup_django()

    def scenario(ctx):
        import time

        from world.systems import exp_pulse
        from world.systems.skills import ACTIVE_WINDOW, GRACE_WINDOW

        character = _build_exp_test_character(ctx, key="TEST_EXP_APPRAISAL_CHAR")
        gem = ctx.harness.create_test_object(
            key="testgem",
            location=character,
            is_gem=True,
            gem_type="quartz",
            size_tier=2,
            quality_tier=2,
            item_value=25,
            value=25,
        )
        weapon = ctx.harness.create_test_object(
            key="testweapon",
            location=character,
            item_type="weapon",
            weapon_type="brawling",
            skill="brawling",
            damage=4,
            damage_min=1,
            damage_max=3,
            item_value=40,
            value=40,
        )
        armor = ctx.harness.create_test_object(
            key="testarmor",
            location=character,
            item_type="armor",
            armor_type="chain",
            protection=3,
            hindrance=1,
            item_value=35,
            value=35,
        )
        creature = ctx.harness.create_test_character(room=ctx.room, key="testbeast")

        for target in (gem, weapon, armor, creature, gem):
            ctx.direct(character.appraise_target, target)
            character.set_roundtime(0)

        appraisal_skill = character.exp_skills.get("appraisal")
        if appraisal_skill.pool <= 0:
            raise AssertionError(f"Appraisal actions did not train appraisal: {appraisal_skill.pool}")

        ctx.output_log.clear()
        ctx.cmd("exp")
        active_transcript = "\n".join(ctx.output_log)
        if "appraisal" not in active_transcript:
            raise AssertionError(f"exp did not show appraisal while active: {active_transcript}")

        before_pool = appraisal_skill.pool
        appraisal_skill.last_trained = time.time() - (ACTIVE_WINDOW + GRACE_WINDOW + 1)
        exp_pulse.GLOBAL_TICK = 20
        ctx.direct(exp_pulse.exp_pulse_tick)
        if appraisal_skill.pool != before_pool:
            raise AssertionError(f"Inactive appraisal still drained: before={before_pool}, after={appraisal_skill.pool}")

        ctx.output_log.clear()
        ctx.cmd("exp")
        inactive_transcript = "\n".join(ctx.output_log)
        if "appraisal" in inactive_transcript:
            raise AssertionError(f"Inactive appraisal still showed in exp: {inactive_transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "appraisal_pool": appraisal_skill.pool,
            "before_pool": before_pool,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-appraisal-loop",
        scenario_metadata=getattr(run_exp_appraisal_loop_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-targeted-magic-bridge",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_targeted_magic_bridge_scenario(args):
    _setup_django()

    def scenario(ctx):
        caster = _build_exp_test_character(ctx, key="TEST_EXP_TM_CASTER")
        target_hit = ctx.harness.create_test_character(room=ctx.room, key="tmhit")
        target_miss = ctx.harness.create_test_character(room=ctx.room, key="tmmiss")

        caster.set_profession("warrior_mage")
        caster.ensure_core_defaults()
        caster.update_skill("targeted_magic", rank=80, mindstate=0)
        caster.update_skill("attunement", rank=80, mindstate=0)

        target_hit.ensure_core_defaults()
        target_miss.ensure_core_defaults()
        target_hit.update_skill("evasion", rank=1, mindstate=0)
        target_hit.db.stats["reflex"] = 1
        target_miss.update_skill("evasion", rank=220, mindstate=0)
        target_miss.db.stats["reflex"] = 220

        ctx.direct(caster.prepare_spell, "flare 10")
        ctx.direct(caster.cast_spell, "tmhit")
        after_hit = caster.exp_skills.get("targeted_magic").pool
        if after_hit <= 0:
            raise AssertionError("Successful targeted cast did not train targeted magic.")

        caster.clear_state("cooldown_flare")
        ctx.direct(caster.prepare_spell, "flare 10")
        ctx.direct(caster.cast_spell, "tmmiss")
        after_miss = caster.exp_skills.get("targeted_magic").pool
        if after_miss <= after_hit:
            raise AssertionError(f"Missed targeted cast did not add EXP: hit={after_hit}, miss={after_miss}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "after_hit": after_hit,
            "after_miss": after_miss,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-targeted-magic-bridge",
        scenario_metadata=getattr(run_exp_targeted_magic_bridge_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-athletics-bridge",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_athletics_bridge_scenario(args):
    _setup_django()

    def scenario(ctx):
        character = _build_exp_test_character(ctx, key="TEST_EXP_ATHLETICS_CHAR")

        character.ensure_core_defaults()
        character.update_skill("athletics", rank=80, mindstate=0)
        character.db.stats["agility"] = 40
        character.db.stats["strength"] = 40
        character.db.stats["stamina"] = 40
        ctx.room.db.climbable = True
        ctx.room.db.climb_difficulty = 20
        ctx.room.db.swimmable = True
        ctx.room.db.swim_difficulty = 20

        ctx.direct(character.attempt_climb)
        after_climb = character.exp_skills.get("athletics").pool
        if after_climb <= 0:
            raise AssertionError("Climb attempt did not train athletics.")

        ctx.direct(character.attempt_swim)
        after_swim = character.exp_skills.get("athletics").pool
        if after_swim <= after_climb:
            raise AssertionError(f"Swim attempt did not add athletics EXP: climb={after_climb}, swim={after_swim}")

        ctx.output_log.clear()
        ctx.cmd("exp all")
        all_transcript = "\n".join(ctx.output_log).lower()
        if "athletics" not in all_transcript:
            raise AssertionError(f"exp all did not show athletics after terrain actions: {all_transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "after_climb": after_climb,
            "after_swim": after_swim,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-athletics-bridge",
        scenario_metadata=getattr(run_exp_athletics_bridge_scenario, "diretest_metadata", {}),
    )


def _build_climb_test_course(ctx):
    from evennia.utils.create import create_object

    rope_walk = create_object("typeclasses.rooms.Room", key="DireTest Rope Walk", nohome=True)
    rope_walk.db.desc = "A test landing with the first rise into the climbing lanes above."
    low_blind = create_object("typeclasses.rooms.Room", key="DireTest Low Blind", nohome=True)
    low_blind.db.desc = "The first blind above the rope walk."
    middle_fort = create_object("typeclasses.rooms.Room", key="DireTest Middle Fort", nohome=True)
    middle_fort.db.desc = "A middle perch with the High Hide looming above."
    high_hide = create_object("typeclasses.rooms.Room", key="DireTest High Hide", nohome=True)
    high_hide.db.desc = "The top perch of the test climb."
    middle_fort.db.ranger_prestige_room = high_hide
    middle_fort.db.ranger_prestige_presence_text = "You catch movement high above in the branches."

    low_exit = create_object(
        "typeclasses.exits.Exit",
        key="up",
        aliases=["low blind", "blind"],
        location=rope_walk,
        destination=low_blind,
        home=rope_walk,
    )
    low_exit.db.climb_contest = True
    low_exit.db.climb_tier = "low"
    low_exit.db.climb_difficulty = 5
    low_exit.db.climb_failure_destination = rope_walk
    low_exit.db.climb_action_command = "climb up"
    low_exit.db.climb_action_label = "climb up"
    low_exit.db.climb_default_action = True

    create_object(
        "typeclasses.exits.Exit",
        key="down",
        location=low_blind,
        destination=rope_walk,
        home=low_blind,
    )

    mid_exit = create_object(
        "typeclasses.exits.Exit",
        key="up",
        aliases=["middle fort", "fort"],
        location=low_blind,
        destination=middle_fort,
        home=low_blind,
    )
    mid_exit.db.climb_contest = True
    mid_exit.db.climb_tier = "mid"
    mid_exit.db.climb_difficulty = 15
    mid_exit.db.climb_failure_destination = low_blind
    mid_exit.db.climb_action_command = "climb up"
    mid_exit.db.climb_action_label = "climb up"
    mid_exit.db.climb_default_action = True
    create_object(
        "typeclasses.exits.Exit",
        key="down",
        location=middle_fort,
        destination=low_blind,
        home=middle_fort,
    )

    high_exit = create_object(
        "typeclasses.exits.Exit",
        key="up",
        aliases=["high hide", "hide"],
        location=middle_fort,
        destination=high_hide,
        home=middle_fort,
    )
    high_exit.db.climb_contest = True
    high_exit.db.climb_tier = "high"
    high_exit.db.climb_difficulty = 22
    high_exit.db.climb_readiness_rank = 18
    high_exit.db.climb_failure_destination = middle_fort
    high_exit.db.climb_action_command = "climb up"
    high_exit.db.climb_action_label = "climb up"
    high_exit.db.climb_default_action = True
    create_object(
        "typeclasses.exits.Exit",
        key="down",
        location=high_hide,
        destination=middle_fort,
        home=high_hide,
    )

    return rope_walk, low_blind, middle_fort, high_hide, low_exit, mid_exit, high_exit


@register_scenario(
    "climb-success",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Contest traversal scenarios validate climb outcomes rather than environment-dependent command latency.",
    },
)
def run_climb_success_scenario(args):
    _setup_django()

    def scenario(ctx):
        character = _build_exp_test_character(ctx, key="TEST_CLIMB_SUCCESS")
        rope_walk, low_blind, _middle_fort, _high_hide, _low_exit, _mid_exit, _high_exit = _build_climb_test_course(ctx)
        character.move_to(rope_walk, move_hooks=True)
        character.ensure_core_defaults()
        character.update_skill("athletics", rank=8, mindstate=0)
        character.db.stats["agility"] = 10
        character.db.stats["strength"] = 10

        appearance = rope_walk.return_appearance(character)
        if "|lc__clickmove__ climb up|lt|yclimb up|n|le" not in appearance:
            raise AssertionError(f"Rope Walk did not expose climb action: {appearance}")
        if "|lc__clickmove__ up|lt|yup|n|le" in appearance:
            raise AssertionError(f"Contested climb exit still rendered as a plain exit: {appearance}")

        ctx.cmd("climb up")

        if getattr(character.location, "id", None) != getattr(low_blind, "id", None):
            raise AssertionError("Successful climb did not advance the character.")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "location": character.location.key,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="climb-success",
        scenario_metadata=getattr(run_climb_success_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "climb-failure",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Contest traversal scenarios validate climb outcomes rather than environment-dependent command latency.",
    },
)
def run_climb_failure_scenario(args):
    _setup_django()

    def scenario(ctx):
        character = _build_exp_test_character(ctx, key="TEST_CLIMB_FAILURE")
        rope_walk, _low_blind, _middle_fort, _high_hide, _low_exit, _mid_exit, _high_exit = _build_climb_test_course(ctx)
        character.move_to(rope_walk, move_hooks=True)
        character.ensure_core_defaults()
        character.update_skill("athletics", rank=2, mindstate=0)
        character.db.stats["agility"] = 5
        character.db.stats["strength"] = 5

        ctx.cmd("climb up")

        if getattr(character.location, "id", None) != getattr(rope_walk, "id", None):
            raise AssertionError("Failed climb should drop the character back one level.")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "location": character.location.key,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="climb-failure",
        scenario_metadata=getattr(run_climb_failure_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "climb-partial",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Contest traversal scenarios validate climb outcomes rather than environment-dependent command latency.",
    },
)
def run_climb_partial_scenario(args):
    _setup_django()

    def scenario(ctx):
        character = _build_exp_test_character(ctx, key="TEST_CLIMB_PARTIAL")
        rope_walk, low_blind, _middle_fort, _high_hide, _low_exit, mid_exit, _high_exit = _build_climb_test_course(ctx)
        character.move_to(low_blind, move_hooks=True)
        character.ensure_core_defaults()
        character.update_skill("athletics", rank=13, mindstate=0)
        character.db.stats["agility"] = 10
        character.db.stats["strength"] = 10

        character.resolve_climb_exit(mid_exit)

        if getattr(character.location, "id", None) != getattr(low_blind, "id", None):
            raise AssertionError("Partial climb should not move the character.")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "location": character.location.key,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="climb-partial",
        scenario_metadata=getattr(run_climb_partial_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "climb-xp",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Contest traversal scenarios validate climb outcomes rather than environment-dependent command latency.",
    },
)
def run_climb_xp_scenario(args):
    _setup_django()

    def scenario(ctx):
        character = _build_exp_test_character(ctx, key="TEST_CLIMB_XP")
        rope_walk, low_blind, _middle_fort, _high_hide, _low_exit, mid_exit, _high_exit = _build_climb_test_course(ctx)
        character.move_to(low_blind, move_hooks=True)
        character.ensure_core_defaults()
        character.update_skill("athletics", rank=13, mindstate=0)
        character.db.stats["agility"] = 10
        character.db.stats["strength"] = 10
        before = character.exp_skills.get("athletics").pool

        character.resolve_climb_exit(mid_exit)

        after = character.exp_skills.get("athletics").pool
        if after <= before:
            raise AssertionError(f"Climb attempt did not award athletics EXP: before={before}, after={after}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "before": before,
            "after": after,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="climb-xp",
        scenario_metadata=getattr(run_climb_xp_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "climb-repeat-training",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Contest traversal scenarios validate climb outcomes rather than environment-dependent command latency.",
    },
)
def run_climb_repeat_training_scenario(args):
    _setup_django()

    def scenario(ctx):
        character = _build_exp_test_character(ctx, key="TEST_CLIMB_REPEAT")
        rope_walk, low_blind, _middle_fort, _high_hide, low_exit, _mid_exit, _high_exit = _build_climb_test_course(ctx)
        character.move_to(rope_walk, move_hooks=True)
        character.ensure_core_defaults()
        character.update_skill("athletics", rank=2, mindstate=0)
        character.db.stats["agility"] = 10
        character.db.stats["strength"] = 10

        ctx.cmd("climb up")
        if getattr(character.location, "id", None) != getattr(rope_walk, "id", None):
            raise AssertionError("First practice climb should have stayed on the rope walk.")
        character.set_roundtime(0)
        if int(character._get_climb_practice_bonus(low_exit) or 0) != 3:
            raise AssertionError("First failed practice climb did not add the expected practice bonus.")

        ctx.cmd("climb up")
        if getattr(character.location, "id", None) != getattr(rope_walk, "id", None):
            raise AssertionError("Second practice climb should still be training the route.")
        character.set_roundtime(0)
        if int(character._get_climb_practice_bonus(low_exit) or 0) != 6:
            raise AssertionError("Second failed practice climb did not stack practice bonus.")

        ctx.cmd("climb up")

        if getattr(character.location, "id", None) != getattr(low_blind, "id", None):
            raise AssertionError("Repeated climb practice did not improve the eventual outcome.")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "location": character.location.key,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="climb-repeat-training",
        scenario_metadata=getattr(run_climb_repeat_training_scenario, "diretest_metadata", {}),
    )


@register_scenario("ranger-high-hide-visibility")
def run_ranger_high_hide_visibility_scenario(args):
    _setup_django()

    def scenario(ctx):
        ranger = _build_exp_test_character(ctx, key="TEST_RANGER_VISIBILITY")
        watcher = _build_exp_test_character(ctx, key="TEST_HIGH_HIDE_WATCHER")
        ranger.db.profession = "ranger"
        _rope_walk, _low_blind, middle_fort, high_hide, _low_exit, _mid_exit, _high_exit = _build_climb_test_course(ctx)
        ranger.move_to(middle_fort, move_hooks=True)

        before = middle_fort.return_appearance(ranger)
        if "High Hide looming above" not in before:
            raise AssertionError(f"Middle Fort description did not advertise the High Hide: {before}")

        watcher.move_to(high_hide, move_hooks=True)
        after = middle_fort.return_appearance(ranger)
        if "You catch movement high above in the branches." not in after:
            raise AssertionError(f"High Hide presence signal did not render from below: {after}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="ranger-high-hide-visibility")


@register_scenario(
    "ranger-quartermaster-shop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Shop scenarios validate inventory and purchase flow rather than environment-dependent command latency.",
    },
)
def run_ranger_quartermaster_shop_scenario(args):
    _setup_django()

    def scenario(ctx):
        from evennia.utils.create import create_object

        character = _build_exp_test_character(ctx, key="TEST_RANGER_SHOPPER")
        character.db.coins = 50
        character.move_to(ctx.room, move_hooks=True)
        quartermaster = create_object("typeclasses.vendor.Vendor", key="Quartermaster", location=ctx.room, home=ctx.room)
        quartermaster.db.is_vendor = True
        quartermaster.db.is_shopkeeper = True
        quartermaster.db.inventory = ["basic cloak", "simple boots", "starter pack", "rope", "basic knife"]
        quartermaster.db.price_map = {
            "basic cloak": 8,
            "simple boots": 6,
            "starter pack": 9,
            "rope": 5,
            "basic knife": 6,
        }
        quartermaster.db.shop_intro_lines = ["The quartermaster cracks open a field chest and gestures across the starter kit with a curt nod."]

        intro_lines = quartermaster.get_vendor_interaction_lines(character, action="shop")
        if not intro_lines or "starter kit" not in intro_lines[0]:
            raise AssertionError("Quartermaster did not expose the expected browse flavor.")

        if character.list_vendor_inventory() is False:
            raise AssertionError("Quartermaster did not present an inventory list.")

        character.buy_item("basic cloak")
        carried = [str(getattr(item, "key", "") or "").lower() for item in character.contents]
        if "basic cloak" not in carried:
            raise AssertionError("Buying from the Quartermaster did not create the purchased item.")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "carried": carried,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="ranger-quartermaster-shop")


@register_scenario(
    "ranger-high-hide-shop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Shop scenarios validate inventory and purchase flow rather than environment-dependent command latency.",
    },
)
def run_ranger_high_hide_shop_scenario(args):
    _setup_django()

    def scenario(ctx):
        from evennia.utils.create import create_object

        character = _build_exp_test_character(ctx, key="TEST_HIGH_HIDE_SHOPPER")
        character.db.coins = 80
        character.move_to(ctx.room, move_hooks=True)
        lysa = create_object("typeclasses.npcs.LysaWindstep", key="Lysa Windstep", location=ctx.room, home=ctx.room)
        lysa.db.is_vendor = True
        lysa.db.is_shopkeeper = True
        lysa.db.inventory = ["balanced climbing gloves", "lightweight ranger cloak", "reinforced rope", "fine skinning knife"]
        lysa.db.price_map = {
            "balanced climbing gloves": 18,
            "lightweight ranger cloak": 16,
            "reinforced rope": 14,
            "fine skinning knife": 18,
        }

        intro_lines = lysa.get_vendor_interaction_lines(character, action="shop")
        if not intro_lines or "field-tuned gear" not in "\n".join(intro_lines):
            raise AssertionError(f"Lysa did not present the flavored browse text: {intro_lines}")

        if character.list_vendor_inventory() is False:
            raise AssertionError("Lysa did not present an inventory list.")

        character.buy_item("balanced climbing gloves")
        carried = [str(getattr(item, "key", "") or "").lower() for item in character.contents]
        if "balanced climbing gloves" not in carried:
            raise AssertionError("Buying from Lysa did not create the purchased item.")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "carried": carried,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="ranger-high-hide-shop")


@register_scenario("ranger-resource-visibility")
def run_ranger_resource_visibility_scenario(args):
    _setup_django()

    def scenario(ctx):
        ranger = _build_exp_test_character(ctx, key="TEST_RANGER_RESOURCES")
        outsider = _build_exp_test_character(ctx, key="TEST_OUTSIDER_RESOURCES")
        ranger.db.profession = "ranger"
        ctx.room.db.ranger_resources = ["grass", "stick"]
        ranger.move_to(ctx.room, move_hooks=True)
        outsider.move_to(ctx.room, move_hooks=True)

        ranger_appearance = ctx.room.return_appearance(ranger)
        outsider_appearance = ctx.room.return_appearance(outsider)
        if "a patch of tall grass" not in ranger_appearance or "a fallen branch" not in ranger_appearance:
            raise AssertionError(f"Ranger could not see the room resources: {ranger_appearance}")
        if "gather grass" not in ranger_appearance or "gather stick" not in ranger_appearance:
            raise AssertionError(f"Ranger did not receive clickable gather actions: {ranger_appearance}")
        if "a patch of tall grass" in outsider_appearance or "gather grass" in outsider_appearance:
            raise AssertionError(f"Non-ranger should not see Ranger-only resources: {outsider_appearance}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="ranger-resource-visibility")


@register_scenario(
    "ranger-resource-sell-loop",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Gather and sell loop scenarios validate item flow rather than environment-dependent command latency.",
    },
)
def run_ranger_resource_sell_loop_scenario(args):
    _setup_django()

    def scenario(ctx):
        from evennia.utils.create import create_object

        ranger = _build_exp_test_character(ctx, key="TEST_RANGER_LOOP")
        ranger.db.profession = "ranger"
        ranger.move_to(ctx.room, move_hooks=True)
        ctx.room.db.ranger_resources = ["grass", "stick"]

        buyer = create_object("typeclasses.vendor.Vendor", key="Field Buyer", location=ctx.room, home=ctx.room)
        buyer.db.is_vendor = True
        buyer.db.is_shopkeeper = True
        buyer.db.accepted_item_types = ["bundle", "braid", "hide"]
        buyer.db.sale_multiplier = 1.0

        starting_coins = int(getattr(ranger.db, "coins", 0) or 0)

        ranger.gather_ranger_resource("stick")
        ranger.gather_ranger_resource("grass")
        after_gather = ctx.room.return_appearance(ranger)
        if "gather stick" in after_gather or "gather grass" in after_gather:
            raise AssertionError("Gathered resources should disappear for the Ranger after use.")

        bundle_item = ranger.transform_ranger_resource("bundle", "sticks")
        braid_item = ranger.transform_ranger_resource("braid", "grass")
        if not bundle_item or not braid_item:
            raise AssertionError("Ranger transforms did not create the expected sale goods.")

        if not ranger.vendor_accepts_item(buyer, bundle_item) or not ranger.vendor_accepts_item(buyer, braid_item):
            raise AssertionError("Field Buyer did not accept the crafted Ranger goods.")

        bundle_value = max(1, int(ranger.get_item_value(bundle_item) * float(ranger.get_vendor_sale_multiplier(buyer, bundle_item) or 0)))
        braid_value = max(1, int(ranger.get_item_value(braid_item) * float(ranger.get_vendor_sale_multiplier(buyer, braid_item) or 0)))
        ranger.add_coins(bundle_value + braid_value)

        ending_coins = int(getattr(ranger.db, "coins", 0) or 0)
        if ending_coins <= starting_coins:
            raise AssertionError("Field Buyer payout logic did not increase the Ranger's coin total.")

        carried = [str(getattr(item, "key", "") or "").lower() for item in ranger.contents]

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "starting_coins": starting_coins,
            "ending_coins": ending_coins,
            "carried": carried,
        }

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="ranger-resource-sell-loop")


@register_scenario(
    "exp-locksmithing-bridge",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_locksmithing_bridge_scenario(args):
    _setup_django()

    def scenario(ctx):
        character = _build_exp_test_character(ctx, key="TEST_EXP_LOCKSMITH_CHAR")
        box = ctx.harness.create_test_object(key="practice box", location=ctx.room)
        pick = ctx.harness.create_test_object(key="training pick", location=character)

        character.ensure_core_defaults()
        character.update_skill("locksmithing", rank=80, mindstate=0)
        character.db.stats["intelligence"] = 40

        box.db.is_box = True
        box.db.locked = True
        box.db.lock_difficulty = 20
        box.db.trap_present = True
        box.db.trap_difficulty = 20
        box.db.trap_type = "needle"
        box.db.disarmed = False
        box.db.last_disarmed_trap = None

        pick.db.is_lockpick = True
        pick.db.grade = "fine"
        pick.db.quality = 5
        pick.db.durability = 20

        ctx.direct(character.inspect_box, box)
        after_inspect = character.exp_skills.get("locksmithing").pool
        if after_inspect <= 0:
            raise AssertionError("Inspect box did not train locksmithing.")

        ctx.direct(character.disarm_box, box)
        after_disarm = character.exp_skills.get("locksmithing").pool
        if not bool(getattr(box.db, "disarmed", False)):
            raise AssertionError("Disarm box did not complete successfully in locksmithing bridge scenario.")
        if after_disarm <= after_inspect:
            raise AssertionError(f"Disarm box did not add locksmithing EXP: inspect={after_inspect}, disarm={after_disarm}")

        ctx.direct(character.pick_box, box, pick)
        after_pick = character.exp_skills.get("locksmithing").pool
        if bool(getattr(box.db, "locked", True)):
            raise AssertionError("Pick box did not unlock the practice box.")
        if after_pick <= after_disarm:
            raise AssertionError(f"Pick box did not add locksmithing EXP: disarm={after_disarm}, pick={after_pick}")

        ctx.output_log.clear()
        ctx.cmd("exp all")
        transcript = "\n".join(ctx.output_log)
        if "locksmithing" not in transcript:
            raise AssertionError(f"exp all did not show locksmithing after box workflow: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "after_inspect": after_inspect,
            "after_disarm": after_disarm,
            "after_pick": after_pick,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-locksmithing-bridge",
        scenario_metadata=getattr(run_exp_locksmithing_bridge_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-debilitation-bridge",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_debilitation_bridge_scenario(args):
    _setup_django()

    def scenario(ctx):
        caster = _build_exp_test_character(ctx, key="TEST_EXP_DEBIL_CASTER")
        target_hit = ctx.harness.create_test_character(room=ctx.room, key="debilhit")
        target_resist = ctx.harness.create_test_character(room=ctx.room, key="debilresist")

        caster.set_profession("warrior_mage")
        caster.ensure_core_defaults()
        caster.update_skill("debilitation", rank=80, mindstate=0)
        caster.update_skill("attunement", rank=80, mindstate=0)

        target_hit.ensure_core_defaults()
        target_resist.ensure_core_defaults()
        target_hit.update_skill("warding", rank=1, mindstate=0)
        target_hit.db.stats["discipline"] = 1
        target_resist.update_skill("warding", rank=220, mindstate=0)
        target_resist.db.stats["discipline"] = 220

        ctx.direct(caster.prepare_spell, "hinder 10")
        ctx.direct(caster.cast_spell, "debilhit")
        after_hit = caster.exp_skills.get("debilitation").pool
        if after_hit <= 0:
            raise AssertionError("Successful debilitation cast did not train debilitation.")
        if not target_hit.get_state("debilitated"):
            raise AssertionError("Successful debilitation cast did not apply the debuff state.")

        caster.clear_state("cooldown_hinder")
        ctx.direct(caster.prepare_spell, "hinder 10")
        ctx.direct(caster.cast_spell, "debilresist")
        after_resist = caster.exp_skills.get("debilitation").pool
        if after_resist <= after_hit:
            raise AssertionError(f"Resisted debilitation cast did not add EXP: hit={after_hit}, resist={after_resist}")
        if target_resist.get_state("debilitated"):
            raise AssertionError("Resisted debilitation cast should not apply the debuff state.")

        ctx.output_log.clear()
        ctx.cmd("exp all")
        transcript = "\n".join(ctx.output_log)
        if "debilitation" not in transcript:
            raise AssertionError(f"exp all did not show debilitation after spell casts: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "after_hit": after_hit,
            "after_resist": after_resist,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-debilitation-bridge",
        scenario_metadata=getattr(run_exp_debilitation_bridge_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-light-edge-bridge",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_light_edge_bridge_scenario(args):
    _setup_django()

    def scenario(ctx):
        attacker = _build_exp_test_character(ctx, key="TEST_EXP_LIGHT_EDGE_ATTACKER")
        target = ctx.harness.create_test_character(room=ctx.room, key="lightedgedummy")
        weapon = ctx.harness.create_test_object(
            key="training knife",
            location=attacker,
            typeclass="typeclasses.weapons.Weapon",
        )

        attacker.ensure_core_defaults()
        target.ensure_core_defaults()
        attacker.update_skill("light_edge", rank=40, mindstate=0)
        attacker.db.stats["reflex"] = 10
        attacker.db.stats["agility"] = 10
        target.update_skill("evasion", rank=20, mindstate=0)
        target.db.stats["reflex"] = 15
        target.db.stats["agility"] = 15

        weapon.db.skill = "light_edge"
        weapon.db.weapon_type = "light_edge"
        weapon.db.damage_type = "slice"
        weapon.db.damage_types = {"slice": 1, "impact": 0, "puncture": 0}
        weapon.db.weapon_profile = {
            "type": "light_edge",
            "skill": "light_edge",
            "damage": 5,
            "balance": 50,
            "speed": 2.0,
            "damage_min": 2,
            "damage_max": 5,
            "roundtime": 2.0,
        }
        if hasattr(weapon, "sync_profile_fields"):
            weapon.sync_profile_fields()
        attacker.db.equipped_weapon = weapon

        light_edge_pool = 0.0
        for _ in range(5):
            ctx.cmd("attack lightedgedummy")
            light_edge_pool = attacker.exp_skills.get("light_edge").pool
            if light_edge_pool > 0:
                break
            attacker.set_roundtime(0)
        if light_edge_pool <= 0:
            raise AssertionError("Successful light-edge attack did not train light edge.")
        if attacker.exp_skills.get("brawling").pool != 0:
            raise AssertionError("Weapon attack incorrectly trained brawling instead of light edge.")

        ctx.output_log.clear()
        ctx.cmd("exp all")
        transcript = "\n".join(ctx.output_log)
        if "light edge" not in transcript:
            raise AssertionError(f"exp all did not show light edge after armed attack: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "light_edge_pool": light_edge_pool,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-light-edge-bridge",
        scenario_metadata=getattr(run_exp_light_edge_bridge_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-second-wave-command-visibility",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_second_wave_command_visibility_scenario(args):
    _setup_django()

    def scenario(ctx):
        import time

        from world.systems.skills import ACTIVE_WINDOW, GRACE_WINDOW

        character = _build_exp_test_character(ctx, key="TEST_EXP_SECOND_WAVE_VIS")
        spell_target = ctx.harness.create_test_character(room=ctx.room, key="waveward")
        box = ctx.harness.create_test_object(key="wave box", location=ctx.room)
        pick = ctx.harness.create_test_object(key="wave pick", location=character)

        character.set_profession("warrior_mage")
        character.ensure_core_defaults()
        spell_target.ensure_core_defaults()

        character.update_skill("athletics", rank=60, mindstate=0)
        character.update_skill("locksmithing", rank=60, mindstate=0)
        character.update_skill("debilitation", rank=80, mindstate=0)
        character.update_skill("light_edge", rank=27, mindstate=0)
        character.update_skill("attunement", rank=80, mindstate=0)
        character.update_skill("brawling", rank=25, mindstate=0)
        spell_target.update_skill("warding", rank=1, mindstate=0)
        spell_target.db.stats["discipline"] = 1

        character.db.stats["agility"] = 40
        character.db.stats["strength"] = 40
        character.db.stats["intelligence"] = 40

        ctx.room.db.climbable = True
        ctx.room.db.climb_difficulty = 20

        box.db.is_box = True
        box.db.locked = True
        box.db.lock_difficulty = 20
        box.db.trap_present = False

        pick.db.is_lockpick = True
        pick.db.grade = "fine"
        pick.db.quality = 5
        pick.db.durability = 20

        ctx.direct(character.attempt_climb)
        ctx.direct(character.pick_box, box, pick)
        ctx.direct(character.prepare_spell, "hinder 10")
        ctx.direct(character.cast_spell, "waveward")

        for skill_name in ("athletics", "locksmithing", "debilitation"):
            skill = character.exp_skills.get(skill_name)
            skill.pool = max(float(skill.pool or 0.0), float(skill.max_pool / 34.0) + 1.0)
            skill.update_mindstate()

        light_edge_skill = character.exp_skills.get("light_edge")
        light_edge_skill.last_trained = time.time() - (ACTIVE_WINDOW + GRACE_WINDOW + 1)

        ctx.output_log.clear()
        ctx.cmd("exp")
        active_transcript = "\n".join(ctx.output_log).lower()
        for skill_name in ("athletics", "lockpicking", "debilitation"):
            if skill_name not in active_transcript:
                raise AssertionError(f"exp missing active second-wave skill {skill_name}: {active_transcript}")
        for skill_name in ("light-edged", "hand-to-hand", "perception"):
            if skill_name in active_transcript:
                raise AssertionError(f"exp showed inactive skill {skill_name}: {active_transcript}")

        ctx.output_log.clear()
        ctx.cmd("exp all")
        all_transcript = "\n".join(ctx.output_log).lower()
        for skill_name in ("athletics", "lockpicking", "debilitation", "light-edged"):
            if skill_name not in all_transcript:
                raise AssertionError(f"exp all missing seeded second-wave skill {skill_name}: {all_transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-second-wave-command-visibility",
        scenario_metadata=getattr(run_exp_second_wave_command_visibility_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-brawling-bridge",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_brawling_bridge_scenario(args):
    _setup_django()

    def scenario(ctx):
        attacker = _build_exp_test_character(ctx, key="TEST_EXP_BRAWL_ATTACKER")
        target = ctx.harness.create_test_character(room=ctx.room, key="brawldummy")
        gem = ctx.harness.create_test_object(
            key="brawlgem",
            location=attacker,
            is_gem=True,
            gem_type="quartz",
            size_tier=1,
            quality_tier=1,
            item_value=10,
            value=10,
        )

        attacker.ensure_core_defaults()
        target.ensure_core_defaults()
        attacker.update_skill("brawling", rank=100, mindstate=0)
        attacker.db.stats["reflex"] = 5
        attacker.db.stats["agility"] = 5
        target.update_skill("evasion", rank=80, mindstate=0)
        target.db.stats["reflex"] = 40
        target.db.stats["agility"] = 40

        ctx.direct(attacker.appraise_target, gem)
        attacker.set_roundtime(0)
        if attacker.exp_skills.get("brawling").pool != 0:
            raise AssertionError("Brawling trained outside the unarmed attack path.")

        ctx.cmd("attack brawldummy")
        brawling_pool = attacker.exp_skills.get("brawling").pool
        if brawling_pool <= 0:
            raise AssertionError("Successful unarmed attack did not train brawling.")
        ctx.output_log.clear()
        ctx.cmd("exp all")
        transcript = "\n".join(ctx.output_log)
        if "brawling" not in transcript:
            raise AssertionError(f"exp all did not show brawling after unarmed attack: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "brawling_pool": brawling_pool,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-brawling-bridge",
        scenario_metadata=getattr(run_exp_brawling_bridge_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-evasion-passive",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_evasion_passive_scenario(args):
    _setup_django()

    def scenario(ctx):
        attacker = _build_exp_test_character(ctx, key="TEST_EXP_EVASION_ATTACKER")
        defender = ctx.harness.create_test_character(room=ctx.room, key="evadee")

        attacker.ensure_core_defaults()
        defender.ensure_core_defaults()
        attacker.update_skill("brawling", rank=40, mindstate=0)
        attacker.db.stats["reflex"] = 10
        attacker.db.stats["agility"] = 10
        defender.update_skill("evasion", rank=20, mindstate=0)
        defender.db.stats["reflex"] = 40
        defender.db.stats["agility"] = 40

        ctx.cmd("attack evadee")
        evasion_pool = defender.exp_skills.get("evasion").pool
        if evasion_pool <= 0:
            raise AssertionError("Incoming combat pressure did not train evasion.")
        original_character = ctx.character
        original_room = ctx.room
        ctx.character = defender
        ctx.room = defender.location
        try:
            ctx.output_log.clear()
            ctx.cmd("exp all")
        finally:
            ctx.character = original_character
            ctx.room = original_room

        transcript = "\n".join(ctx.output_log)
        if "evasion" not in transcript:
            raise AssertionError(f"exp all did not show evasion after defensive engagement: {transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
            "evasion_pool": evasion_pool,
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-evasion-passive",
        scenario_metadata=getattr(run_exp_evasion_passive_scenario, "diretest_metadata", {}),
    )


@register_scenario(
    "exp-command-visibility",
    metadata={
        "fail_on_critical_lag": False,
        "lag_policy_reason": "Bridge scenarios validate EXP routing rather than environment-dependent command latency.",
    },
)
def run_exp_command_visibility_scenario(args):
    _setup_django()

    def scenario(ctx):
        character = _build_exp_test_character(ctx, key="TEST_EXP_COMMAND_VISIBILITY")
        attacker = ctx.harness.create_test_character(room=ctx.room, key="visibilityfoe")
        spell_target = ctx.harness.create_test_character(room=ctx.room, key="visibilitytarget")
        gem = ctx.harness.create_test_object(
            key="visibilitygem",
            location=character,
            is_gem=True,
            gem_type="quartz",
            size_tier=1,
            quality_tier=1,
            item_value=15,
            value=15,
        )

        character.set_profession("warrior_mage")
        character.ensure_core_defaults()
        attacker.ensure_core_defaults()
        spell_target.ensure_core_defaults()
        attacker.permissions.add("Developer")

        character.update_skill("evasion", rank=20, mindstate=0)
        character.update_skill("stealth", rank=20, mindstate=0)
        character.update_skill("targeted_magic", rank=80, mindstate=0)
        character.update_skill("attunement", rank=80, mindstate=0)
        attacker.update_skill("brawling", rank=40, mindstate=0)
        character.db.stats["reflex"] = 40
        character.db.stats["agility"] = 40
        attacker.db.stats["reflex"] = 5
        attacker.db.stats["agility"] = 5
        spell_target.update_skill("evasion", rank=60, mindstate=0)
        spell_target.db.stats["reflex"] = 20

        evasion_skill = character.exp_skills.get("evasion")
        evasion_skill.pool = max(0.0, (evasion_skill.max_pool / 34.0) - 1.0)
        evasion_skill.update_mindstate()
        stealth_skill = character.exp_skills.get("stealth")
        stealth_skill.pool = max(0.0, (stealth_skill.max_pool / 34.0) - 1.0)
        stealth_skill.update_mindstate()
        targeted_magic_skill = character.exp_skills.get("targeted_magic")
        targeted_magic_skill.pool = max(0.0, (targeted_magic_skill.max_pool / 34.0) - 1.0)
        targeted_magic_skill.update_mindstate()

        ctx.cmd("hide")
        character.set_roundtime(0)
        ctx.direct(character.appraise_target, gem)
        character.set_roundtime(0)
        ctx.direct(character.prepare_spell, "flare 10")
        ctx.direct(character.cast_spell, "visibilitytarget")
        character.set_target(attacker)

        original_character = ctx.character
        original_room = ctx.room
        ctx.character = attacker
        ctx.room = attacker.location
        try:
            ctx.cmd("attack TEST_EXP_COMMAND_VISIBILITY")
        finally:
            ctx.character = original_character
            ctx.room = original_room

        ctx.output_log.clear()
        ctx.cmd("exp")
        active_transcript = "\n".join(ctx.output_log).lower()
        for skill_name in ("stealth", "appraisal", "targeted magic", "evasion"):
            if skill_name not in active_transcript:
                raise AssertionError(f"exp missing active skill {skill_name}: {active_transcript}")
        for skill_name in ("hand-to-hand", "perception"):
            if skill_name in active_transcript:
                raise AssertionError(f"exp showed inactive skill {skill_name}: {active_transcript}")
        for skill_name in ("stealth", "appraisal", "targeted magic", "evasion"):
            for line in active_transcript.splitlines():
                if skill_name not in line:
                    continue
                if "clear" in line:
                    raise AssertionError(f"exp showed active skill {skill_name} as clear: {line}")
                if ")         (0/" in line:
                    raise AssertionError(f"exp showed active skill {skill_name} with zero displayed pool bits: {line}")
                break

        ctx.output_log.clear()
        ctx.cmd("exp all")
        all_transcript = "\n".join(ctx.output_log).lower()
        for skill_name in ("evasion", "stealth", "perception", "hand-to-hand", "targeted magic", "appraisal"):
            if skill_name not in all_transcript:
                raise AssertionError(f"exp all missing seeded template skill {skill_name}: {all_transcript}")

        return {
            "commands": list(ctx.command_log),
            "output_log": list(ctx.output_log),
        }

    return _run_registered_scenario(
        args,
        scenario,
        auto_snapshot=False,
        name="exp-command-visibility",
        scenario_metadata=getattr(run_exp_command_visibility_scenario, "diretest_metadata", {}),
    )


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
    command_count = int(len(list(result.get("commands", []) or [])))
    snapshot_count = int(len(list(result.get("snapshots", []) or [])))

    print(f"DireTest Scenario: {str(getattr(args, 'scenario_name', 'scenario') or 'scenario')}")
    print(f"Seed: {int(result.get('seed', 0) or 0)}")
    print(f"Exit Code: {int(result.get('exit_code', 0))}")
    print(f"Artifact Dir: {result.get('artifact_dir')}")
    print(f"Commands Logged: {command_count}")
    print(f"Snapshots: {snapshot_count}")
    duration_ms = int((result.get("metrics", {}) or {}).get("scenario_duration_ms", 0) or 0)
    if duration_ms:
        print(f"Duration Ms: {duration_ms}")
    performance_summary = _build_performance_summary_line(result.get("metrics", {}))
    if performance_summary:
        print(performance_summary)
    for line in _build_lag_summary_lines(result.get("metrics", {})):
        print(line)
    for line in _build_replay_lag_lines(result.get("metrics", {})):
        print(line)
    for line in _build_benchmark_summary_lines(scenario_result):
        print(line)
    if result.get("traceback"):
        print("Traceback:")
        print(result.get("traceback"))
    status = "PASS" if int(result.get("exit_code", 0) or 0) == 0 else "FAIL"
    print(f"{status}: {str(getattr(args, 'scenario_name', 'scenario') or 'scenario')}")
    print(f"See artifacts: {result.get('artifact_dir')}")


def _emit_basic_result(args, exit_code, artifact_dir, traceback_text="", failure_type=None):
    payload = {
        "artifact_dir": str(artifact_dir or ""),
        "exit_code": int(exit_code),
        "failure_type": str(failure_type or "") or None,
        "scenario": str(getattr(args, "scenario_name", getattr(args, "command", "scenario")) or "scenario"),
        "seed": int(getattr(args, "seed", 0) or 0),
        "traceback": str(traceback_text or ""),
    }
    if bool(getattr(args, "json", False)):
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print(f"DireTest Scenario: {payload['scenario']}")
    print(f"Artifact Dir: {payload['artifact_dir']}")
    if traceback_text:
        print("Traceback:")
        print(traceback_text)
    status = "PASS" if int(exit_code) == 0 else "FAIL"
    print(f"{status}: {payload['scenario']}")
    print(f"See artifacts: {payload['artifact_dir']}")


def _execute_cli_scenario(args):
    scenario_tag = str(getattr(args, "tag", "") or "").strip().lower()
    if scenario_tag:
        tagged_scenarios = [(name, handler) for name, handler in _get_canonical_scenarios() if _scenario_has_tag(handler, scenario_tag)]
        if not tagged_scenarios:
            if bool(getattr(args, "json", False)):
                print(json.dumps({"exit_code": 1, "failure_type": "scenario_tag_lookup_failure", "message": f"No scenarios are registered with tag '{scenario_tag}'."}, indent=2, sort_keys=True))
            else:
                print(f"No scenarios are registered with tag '{scenario_tag}'.")
            return 1

        parser = build_parser()
        results = []
        exit_code = 0
        for scenario_name, _handler in tagged_scenarios:
            scenario_argv = ["scenario", scenario_name]
            if getattr(args, "seed", None) is not None:
                scenario_argv.extend(["--seed", str(int(args.seed))])
            if bool(getattr(args, "check_lag", False)):
                scenario_argv.append("--check-lag")
            scenario_args = parser.parse_args(scenario_argv)
            scenario_args.json = False
            scenario_exit = int(_execute_cli_scenario(scenario_args))
            results.append({"scenario": scenario_name, "exit_code": scenario_exit, "seed": int(getattr(scenario_args, "seed", 0) or 0)})
            if scenario_exit != 0:
                exit_code = 1

        if bool(getattr(args, "json", False)):
            print(json.dumps({"command": "scenario", "tag": scenario_tag, "exit_code": exit_code, "results": results}, indent=2, sort_keys=True))
            return exit_code

        passed = sum(1 for entry in results if int(entry.get("exit_code", 0) or 0) == 0)
        total = len(results)
        print(f"Scenario Tag Summary ({scenario_tag}): {passed}/{total} passed")
        return exit_code

    if not getattr(args, "scenario_name", None):
        if bool(getattr(args, "json", False)):
            print(json.dumps({"exit_code": 1, "failure_type": "scenario_lookup_failure", "message": "A scenario name or --tag is required."}, indent=2, sort_keys=True))
        else:
            print("A scenario name or --tag is required.")
        return 1

    seed = _ensure_scenario_seed(args)
    traceback_text = ""
    exit_code = 1
    handler_result = None
    artifact_dir = None
    failure_type = None

    try:
        handler_result = args.handler(args)
    except Exception:
        traceback_text = traceback.format_exc()
        failure_type = "unexpected_exception"
    if _is_runner_result(handler_result):
        _emit_runner_result(args, handler_result)
        return int(handler_result.get("exit_code", 0))

    if handler_result is not None:
        exit_code = int(handler_result)

    artifact_dir = write_artifacts(
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
                "diffs": [],
                "metrics": {
                    "exit_code": int(exit_code),
                    "failure_type": failure_type,
                },
                "failure_summary": build_failure_summary(
                    failure_type=failure_type,
                    message=traceback_text.strip().splitlines()[-1] if traceback_text else "",
                    scenario=str(getattr(args, "scenario_name", "scenario") or "scenario"),
                    seed=seed,
                    mode="direct",
                ),
                "traceback": traceback_text,
            },
        )
    _emit_basic_result(args, exit_code=exit_code, artifact_dir=artifact_dir, traceback_text=traceback_text, failure_type=failure_type)
    return int(exit_code)


def _handle_list_command(args):
    scenario_names = sorted(SCENARIO_REGISTRY)
    if bool(getattr(args, "json", False)):
        print(json.dumps({"scenarios": scenario_names}, indent=2, sort_keys=True))
        return 0

    print("Available scenarios:")
    for scenario_name in scenario_names:
        print(f"- {scenario_name}")
    return 0


def _get_canonical_scenarios():
    scenarios = []
    seen = set()
    for name, handler in sorted(SCENARIO_REGISTRY.items()):
        canonical_name = str(getattr(handler, "diretest_scenario_name", name) or name)
        if canonical_name != name:
            continue
        if canonical_name in seen:
            continue
        seen.add(canonical_name)
        scenarios.append((canonical_name, handler))
    return scenarios


def _scenario_has_tag(handler, tag):
    desired = str(tag or "").strip().lower()
    if not desired:
        return False
    metadata = dict(getattr(handler, "diretest_metadata", {}) or {})
    tags = [str(entry or "").strip().lower() for entry in list(metadata.get("tags", []) or []) if str(entry or "").strip()]
    return desired in tags


def _handle_smoke_command(args):
    tagged_scenarios = [(name, handler) for name, handler in _get_canonical_scenarios() if _scenario_has_tag(handler, "smoke")]
    if not tagged_scenarios:
        if bool(getattr(args, "json", False)):
            print(json.dumps({"exit_code": 1, "failure_type": "smoke_lookup_failure", "message": "No smoke-tagged scenarios are registered."}, indent=2, sort_keys=True))
            return 1
        print("FAIL: smoke")
        print("No smoke-tagged scenarios are registered.")
        return 1

    parser = build_parser()
    results = []
    exit_code = 0
    for scenario_name, _handler in tagged_scenarios:
        scenario_argv = ["scenario", scenario_name]
        if getattr(args, "seed", None) is not None:
            scenario_argv.extend(["--seed", str(int(args.seed))])
        if bool(getattr(args, "check_lag", False)):
            scenario_argv.append("--check-lag")
        scenario_args = parser.parse_args(scenario_argv)
        scenario_args.json = False
        scenario_exit = int(_execute_cli_scenario(scenario_args))
        results.append({"scenario": scenario_name, "exit_code": scenario_exit, "seed": int(getattr(scenario_args, "seed", 0) or 0)})
        if scenario_exit != 0:
            exit_code = 1

    if bool(getattr(args, "json", False)):
        print(json.dumps({"command": "smoke", "exit_code": exit_code, "results": results}, indent=2, sort_keys=True))
        return exit_code

    passed = sum(1 for entry in results if int(entry.get("exit_code", 0) or 0) == 0)
    total = len(results)
    print(f"Smoke Summary: {passed}/{total} passed")
    return exit_code


def _handle_repro_command(args):
    metadata = _load_artifact_metadata(args.artifact_path)
    scenario_name = metadata["scenario"]
    seed = int(metadata["seed"])
    handler = _get_registered_scenario(scenario_name)

    if not bool(getattr(args, "json", False)):
        print(f"Replaying scenario: {scenario_name}")
        print(f"Seed: {seed}")

    if handler is None:
        artifact_dir = _write_cli_failure_artifact(
            scenario_name=scenario_name or "repro",
            seed=seed,
            failure_type="scenario_lookup_failure",
            message=f"No registered DireTest scenario matches artifact scenario '{scenario_name}'.",
            mode=metadata.get("mode", "direct"),
        )
        if bool(getattr(args, "json", False)):
            print(
                json.dumps(
                    {
                        "artifact_dir": artifact_dir,
                        "exit_code": 1,
                        "failure_type": "scenario_lookup_failure",
                        "scenario": scenario_name,
                        "seed": seed,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"FAIL: {scenario_name}")
            print(f"See artifacts: {artifact_dir}")
        return 1

    parser = build_parser()
    replay_args = parser.parse_args(["scenario", scenario_name, "--seed", str(seed)])
    replay_args.json = bool(getattr(args, "json", False))
    replay_args.repro_artifact_path = args.artifact_path
    return _execute_cli_scenario(replay_args)


def _handle_diff_command(args):
    before_snapshot = _load_snapshot_reference(args.before_snapshot)
    after_snapshot = _load_snapshot_reference(args.after_snapshot)
    diff_payload = build_snapshot_diff(before_snapshot, after_snapshot)

    if getattr(args, "output", None):
        Path(args.output).write_text(json.dumps(diff_payload, indent=2, sort_keys=True), encoding="utf-8")

    if bool(getattr(args, "json", False)):
        print(json.dumps(diff_payload, indent=2, sort_keys=True))
        return 0

    character_changes = diff_payload["character_changes"]
    room_changes = diff_payload["room_changes"]
    inventory_changes = diff_payload["inventory_changes"]
    combat_changes = diff_payload["combat_changes"]
    object_changes = diff_payload["object_delta_changes"]

    print(f"Diff: {before_snapshot.get('label', '')} -> {after_snapshot.get('label', '')}")
    print(f"Room Changed: {room_changes['changed']}")
    print(f"Coins Delta: {character_changes['coins_delta']}")
    print(f"Bank Coins Delta: {character_changes['bank_coins_delta']}")
    print(f"Inventory Added: {', '.join(inventory_changes['added']) if inventory_changes['added'] else '(none)'}")
    print(f"Inventory Removed: {', '.join(inventory_changes['removed']) if inventory_changes['removed'] else '(none)'}")
    print(f"Entered Combat: {combat_changes['entered_combat']}")
    print(f"Exited Combat: {combat_changes['exited_combat']}")
    print(f"Objects Created: {', '.join(object_changes['created']) if object_changes['created'] else '(none)'}")
    print(f"Objects Deleted: {', '.join(object_changes['deleted']) if object_changes['deleted'] else '(none)'}")
    if getattr(args, "output", None):
        print(f"Wrote JSON diff: {args.output}")
    return 0


def _add_common_scenario_args(parser):
    parser.add_argument("--seed", type=int)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-lag", action="store_true")
    return parser


def build_parser():
    parser = argparse.ArgumentParser(prog="diretest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scenario_parser = subparsers.add_parser("scenario")
    scenario_parser.add_argument("--tag")
    scenario_parser.set_defaults(cli_handler=_execute_cli_scenario)
    scenario_subparsers = scenario_parser.add_subparsers(dest="scenario_name", required=False)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(cli_handler=_handle_list_command)

    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument("--seed", type=int)
    smoke_parser.add_argument("--json", action="store_true")
    smoke_parser.add_argument("--check-lag", action="store_true")
    smoke_parser.set_defaults(cli_handler=_handle_smoke_command)

    repro_parser = subparsers.add_parser("repro")
    repro_parser.add_argument("artifact_path")
    repro_parser.add_argument("--json", action="store_true")
    repro_parser.set_defaults(cli_handler=_handle_repro_command)

    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument("before_snapshot")
    diff_parser.add_argument("after_snapshot")
    diff_parser.add_argument("--json", action="store_true")
    diff_parser.add_argument("--output")
    diff_parser.set_defaults(cli_handler=_handle_diff_command)

    balance_baseline_parser = subparsers.add_parser("balance-baseline")
    balance_baseline_parser.add_argument("--name", default="DireTestHero")
    balance_baseline_parser.add_argument("--seed", type=int)
    balance_baseline_parser.add_argument("--json", action="store_true")
    balance_baseline_parser.set_defaults(cli_handler=_handle_balance_baseline_command)

    baseline_parser = subparsers.add_parser("baseline")
    baseline_subparsers = baseline_parser.add_subparsers(dest="baseline_action", required=True)

    baseline_save_parser = baseline_subparsers.add_parser("save")
    baseline_save_parser.add_argument("baseline_name")
    baseline_save_parser.add_argument("--character-name", default="DireTestHero")
    baseline_save_parser.add_argument("--seed", type=int)
    baseline_save_parser.add_argument("--json", action="store_true")
    baseline_save_parser.set_defaults(cli_handler=_handle_baseline_save_command)

    baseline_compare_parser = baseline_subparsers.add_parser("compare")
    baseline_compare_parser.add_argument("baseline_name")
    baseline_compare_parser.add_argument("--character-name", default="DireTestHero")
    baseline_compare_parser.add_argument("--seed", type=int)
    baseline_compare_parser.add_argument("--json", action="store_true")
    baseline_compare_parser.set_defaults(cli_handler=_handle_baseline_compare_command)

    race_balance_parser = _add_common_scenario_args(scenario_subparsers.add_parser("race-balance"))
    race_balance_parser.add_argument("--profession", default="commoner")
    race_balance_parser.add_argument("--sample-weight", type=float, default=80.0)
    race_balance_parser.add_argument("--base-xp", type=int, default=100)
    race_balance_parser.set_defaults(handler=run_race_balance_scenario)

    race_descriptor_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("race-descriptor-basic"))
    race_descriptor_basic_parser.set_defaults(handler=run_race_descriptor_basic_scenario)

    race_descriptor_age_shift_parser = _add_common_scenario_args(scenario_subparsers.add_parser("race-descriptor-age-shift"))
    race_descriptor_age_shift_parser.set_defaults(handler=run_race_descriptor_age_shift_scenario)

    race_descriptor_no_race_parser = _add_common_scenario_args(scenario_subparsers.add_parser("race-descriptor-no-race"))
    race_descriptor_no_race_parser.set_defaults(handler=run_race_descriptor_no_race_scenario)

    language_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-basic"))
    language_basic_parser.set_defaults(handler=run_language_basic_scenario)

    language_switch_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-switch"))
    language_switch_parser.set_defaults(handler=run_language_switch_scenario)

    language_accent_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-accent"))
    language_accent_parser.set_defaults(handler=run_language_accent_scenario)

    language_invalid_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-invalid"))
    language_invalid_parser.set_defaults(handler=run_language_invalid_scenario)

    language_comprehension_none_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-comprehension-none"))
    language_comprehension_none_parser.set_defaults(handler=run_language_comprehension_none_scenario)

    language_comprehension_full_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-comprehension-full"))
    language_comprehension_full_parser.set_defaults(handler=run_language_comprehension_full_scenario)

    language_comprehension_partial_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-comprehension-partial"))
    language_comprehension_partial_parser.set_defaults(handler=run_language_comprehension_partial_scenario)

    language_learning_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-learning-basic"))
    language_learning_basic_parser.set_defaults(handler=run_language_learning_basic_scenario)

    language_learning_cap_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-learning-cap"))
    language_learning_cap_parser.set_defaults(handler=run_language_learning_cap_scenario)

    language_learning_comprehension_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-learning-comprehension"))
    language_learning_comprehension_parser.set_defaults(handler=run_language_learning_comprehension_scenario)

    language_learning_eavesdrop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("language-learning-eavesdrop"))
    language_learning_eavesdrop_parser.set_defaults(handler=run_language_learning_eavesdrop_scenario)

    whisper_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("whisper-basic"))
    whisper_basic_parser.set_defaults(handler=run_whisper_basic_scenario)

    whisper_language_parser = _add_common_scenario_args(scenario_subparsers.add_parser("whisper-language"))
    whisper_language_parser.set_defaults(handler=run_whisper_language_scenario)

    whisper_comprehension_parser = _add_common_scenario_args(scenario_subparsers.add_parser("whisper-comprehension"))
    whisper_comprehension_parser.set_defaults(handler=run_whisper_comprehension_scenario)

    whisper_invalid_parser = _add_common_scenario_args(scenario_subparsers.add_parser("whisper-invalid"))
    whisper_invalid_parser.set_defaults(handler=run_whisper_invalid_scenario)

    eavesdrop_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("eavesdrop-basic"))
    eavesdrop_basic_parser.set_defaults(handler=run_eavesdrop_basic_scenario)

    eavesdrop_none_parser = _add_common_scenario_args(scenario_subparsers.add_parser("eavesdrop-none"))
    eavesdrop_none_parser.set_defaults(handler=run_eavesdrop_none_scenario)

    eavesdrop_degraded_parser = _add_common_scenario_args(scenario_subparsers.add_parser("eavesdrop-degraded"))
    eavesdrop_degraded_parser.set_defaults(handler=run_eavesdrop_degraded_scenario)

    eavesdrop_comprehension_parser = _add_common_scenario_args(scenario_subparsers.add_parser("eavesdrop-comprehension"))
    eavesdrop_comprehension_parser.set_defaults(handler=run_eavesdrop_comprehension_scenario)

    movement_parser = _add_common_scenario_args(scenario_subparsers.add_parser("movement"))
    movement_parser.set_defaults(handler=run_movement_scenario)

    fishing_vertical_slice_parser = _add_common_scenario_args(scenario_subparsers.add_parser("fishing-vertical-slice"))
    fishing_vertical_slice_parser.set_defaults(handler=run_fishing_vertical_slice_scenario)

    fishing_junk_event_slice_parser = _add_common_scenario_args(scenario_subparsers.add_parser("fishing-junk-event-slice"))
    fishing_junk_event_slice_parser.set_defaults(handler=run_fishing_junk_event_slice_scenario)

    fishing_simulation_100_parser = _add_common_scenario_args(scenario_subparsers.add_parser("fishing-simulation-100"))
    fishing_simulation_100_parser.set_defaults(handler=run_fishing_simulation_100_scenario)

    fishing_help_parser = _add_common_scenario_args(scenario_subparsers.add_parser("fishing-help"))
    fishing_help_parser.set_defaults(handler=run_fishing_help_scenario)

    fishing_borrowed_gear_exit_parser = _add_common_scenario_args(scenario_subparsers.add_parser("fishing-borrowed-gear-exit"))
    fishing_borrowed_gear_exit_parser.set_defaults(handler=run_fishing_borrowed_gear_exit_scenario)

    fishing_borrowed_gear_full_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("fishing-borrowed-gear-full-loop"))
    fishing_borrowed_gear_full_loop_parser.set_defaults(handler=run_fishing_borrowed_gear_full_loop_scenario)

    rt_timing_parser = _add_common_scenario_args(scenario_subparsers.add_parser("rt-timing"))
    rt_timing_parser.set_defaults(handler=run_rt_timing_scenario)

    inventory_parser = _add_common_scenario_args(scenario_subparsers.add_parser("inventory"))
    inventory_parser.set_defaults(handler=run_inventory_scenario)

    thief_counterplay_parser = _add_common_scenario_args(scenario_subparsers.add_parser("thief-counterplay"))
    thief_counterplay_parser.set_defaults(handler=run_thief_counterplay_scenario)

    thief_burglary_justice_parser = _add_common_scenario_args(scenario_subparsers.add_parser("thief-burglary-justice"))
    thief_burglary_justice_parser.set_defaults(handler=run_thief_burglary_justice_scenario)

    justice_arrest_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("justice-arrest-basic"))
    justice_arrest_basic_parser.set_defaults(handler=run_justice_arrest_basic_scenario)

    justice_enforcement_outcomes_parser = _add_common_scenario_args(scenario_subparsers.add_parser("justice-enforcement-outcomes"))
    justice_enforcement_outcomes_parser.set_defaults(handler=run_justice_enforcement_outcomes_scenario)

    justice_guardhouse_flow_parser = _add_common_scenario_args(scenario_subparsers.add_parser("justice-guardhouse-flow"))
    justice_guardhouse_flow_parser.set_defaults(handler=run_justice_guardhouse_flow_scenario)

    thief_caught_vs_uncaught_parser = _add_common_scenario_args(scenario_subparsers.add_parser("thief-caught-vs-uncaught"))
    thief_caught_vs_uncaught_parser.set_defaults(handler=run_thief_caught_vs_uncaught_scenario)

    canon_seed_validation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("canon-seed-validation"))
    canon_seed_validation_parser.set_defaults(handler=run_canon_seed_validation_scenario)

    guard_ai_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("guard-ai-basic"))
    guard_ai_basic_parser.set_defaults(handler=run_guard_ai_basic_scenario)

    empath_core_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-core-loop"))
    empath_core_loop_parser.set_defaults(handler=run_empath_core_loop_scenario)

    empath_triage_pressure_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-triage-pressure", aliases=["empath_triage_pressure"]))
    empath_triage_pressure_parser.set_defaults(handler=run_empath_triage_pressure_scenario)

    empath_circle_formation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-circle-formation", aliases=["empath_circle_formation"]))
    empath_circle_formation_parser.set_defaults(handler=run_empath_circle_formation_scenario)

    empath_circle_shock_distribution_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-circle-shock-distribution", aliases=["empath_circle_shock_distribution"]))
    empath_circle_shock_distribution_parser.set_defaults(handler=run_empath_circle_shock_distribution_scenario)

    empath_circle_cascade_failure_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-circle-cascade-failure", aliases=["empath_circle_cascade_failure"]))
    empath_circle_cascade_failure_parser.set_defaults(handler=run_empath_circle_cascade_failure_scenario)

    empath_cooperative_efficiency_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-cooperative-efficiency", aliases=["empath_cooperative_efficiency"]))
    empath_cooperative_efficiency_parser.set_defaults(handler=run_empath_cooperative_efficiency_scenario)

    empath_reputation_drift_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-reputation-drift", aliases=["empath_reputation_drift"]))
    empath_reputation_drift_parser.set_defaults(handler=run_empath_reputation_drift_scenario)

    empath_group_survival_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-group-survival", aliases=["empath_group_survival"]))
    empath_group_survival_parser.set_defaults(handler=run_empath_group_survival_scenario)

    empath_failure_cascade_stability_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-failure-cascade-stability", aliases=["empath_failure_cascade_stability"]))
    empath_failure_cascade_stability_parser.set_defaults(handler=run_empath_failure_cascade_stability_scenario)

    empath_link_state_compat_parser = _add_common_scenario_args(
        scenario_subparsers.add_parser(
            "empath-link-state-compat",
            aliases=["empath_link_state_compat"],
        )
    )
    empath_link_state_compat_parser.set_defaults(handler=run_empath_link_state_compat_scenario)

    empath_completion_pass_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-completion-pass"))
    empath_completion_pass_parser.set_defaults(handler=run_empath_completion_pass_scenario)

    empath_learning_unification_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-learning-unification"))
    empath_learning_unification_parser.set_defaults(handler=run_empath_learning_unification_scenario)

    empath_perceive_cooldown_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-perceive-cooldown"))
    empath_perceive_cooldown_parser.set_defaults(handler=run_empath_perceive_cooldown_scenario)

    empath_shock_transfer_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-shock-transfer"))
    empath_shock_transfer_parser.set_defaults(handler=run_empath_shock_transfer_scenario)

    empath_shift_structure_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-shift-structure"))
    empath_shift_structure_parser.set_defaults(handler=run_empath_shift_structure_scenario)

    empath_service_foundation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-service-foundation"))
    empath_service_foundation_parser.set_defaults(handler=run_empath_service_foundation_scenario)

    empath_vitality_transfer_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-vitality-transfer"))
    empath_vitality_transfer_parser.set_defaults(handler=run_empath_vitality_transfer_scenario)

    empath_poison_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-poison-loop"))
    empath_poison_loop_parser.set_defaults(handler=run_empath_poison_loop_scenario)

    empath_shock_lockout_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-shock-lockout"))
    empath_shock_lockout_parser.set_defaults(handler=run_empath_shock_lockout_scenario)

    empath_link_stability_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-link-stability"))
    empath_link_stability_parser.set_defaults(handler=run_empath_link_stability_scenario)

    empath_link_separation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-link-separation"))
    empath_link_separation_parser.set_defaults(handler=run_empath_link_separation_scenario)

    empath_link_vs_shock_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-link-vs-shock"))
    empath_link_vs_shock_parser.set_defaults(handler=run_empath_link_vs_shock_scenario)

    empath_persistent_link_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-persistent-link"))
    empath_persistent_link_parser.set_defaults(handler=run_empath_persistent_link_scenario)

    empath_unity_burden_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-unity-burden"))
    empath_unity_burden_parser.set_defaults(handler=run_empath_unity_burden_scenario)

    empath_redirect_strain_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-redirect-strain"))
    empath_redirect_strain_parser.set_defaults(handler=run_empath_redirect_strain_scenario)

    empath_unity_breaks_on_shock_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-unity-breaks-on-shock"))
    empath_unity_breaks_on_shock_parser.set_defaults(handler=run_empath_unity_breaks_on_shock_scenario)

    empath_circle_progression_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-circle-progression"))
    empath_circle_progression_parser.set_defaults(handler=run_empath_circle_progression_scenario)

    empath_unlock_separation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-unlock-separation"))
    empath_unlock_separation_parser.set_defaults(handler=run_empath_unlock_separation_scenario)

    combat_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("combat-basic"))
    combat_basic_parser.set_defaults(handler=run_combat_basic_scenario)

    death_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-loop"))
    death_loop_parser.set_defaults(handler=run_death_loop_scenario)

    cleric_revive_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-revive-loop"))
    cleric_revive_loop_parser.set_defaults(handler=run_cleric_revive_loop_scenario)

    cleric_revive_interrupt_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-revive-interrupt"))
    cleric_revive_interrupt_parser.set_defaults(handler=run_cleric_revive_interrupt_scenario)

    cleric_devotion_gating_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-devotion-gating"))
    cleric_devotion_gating_parser.set_defaults(handler=run_cleric_devotion_gating_scenario)

    cleric_devotion_consumption_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-devotion-consumption"))
    cleric_devotion_consumption_parser.set_defaults(handler=run_cleric_devotion_consumption_scenario)

    cleric_ritual_interruption_consequences_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-interruption-consequences"))
    cleric_ritual_interruption_consequences_parser.set_defaults(handler=run_cleric_ritual_interruption_consequences_scenario)

    cleric_ritual_multiple_failures_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-multiple-failures"))
    cleric_ritual_multiple_failures_parser.set_defaults(handler=run_cleric_ritual_multiple_failures_scenario)

    cleric_ritual_quality_scaling_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-quality-scaling"))
    cleric_ritual_quality_scaling_parser.set_defaults(handler=run_cleric_ritual_quality_scaling_scenario)

    corpse_wound_pipeline_parser = _add_common_scenario_args(scenario_subparsers.add_parser("corpse-wound-pipeline"))
    corpse_wound_pipeline_parser.set_defaults(handler=run_corpse_wound_pipeline_scenario)

    resurrection_bad_prep_redie_parser = _add_common_scenario_args(scenario_subparsers.add_parser("resurrection-bad-prep-redie"))
    resurrection_bad_prep_redie_parser.set_defaults(handler=run_resurrection_bad_prep_redie_scenario)

    resurrection_good_prep_survives_parser = _add_common_scenario_args(scenario_subparsers.add_parser("resurrection-good-prep-survives"))
    resurrection_good_prep_survives_parser.set_defaults(handler=run_resurrection_good_prep_survives_scenario)

    resurrection_borderline_needs_care_parser = _add_common_scenario_args(scenario_subparsers.add_parser("resurrection-borderline-needs-care"))
    resurrection_borderline_needs_care_parser.set_defaults(handler=run_resurrection_borderline_needs_care_scenario)

    resurrection_stabilization_decay_parser = _add_common_scenario_args(scenario_subparsers.add_parser("resurrection-stabilization-decay"))
    resurrection_stabilization_decay_parser.set_defaults(handler=run_resurrection_stabilization_decay_scenario)

    cleric_group_speed_quality_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-group-speed-quality"))
    cleric_group_speed_quality_parser.set_defaults(handler=run_cleric_group_speed_quality_scenario)

    cleric_group_interruption_mitigation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-group-interruption-mitigation"))
    cleric_group_interruption_mitigation_parser.set_defaults(handler=run_cleric_group_interruption_mitigation_scenario)

    cleric_specialization_light_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-specialization-light"))
    cleric_specialization_light_parser.set_defaults(handler=run_cleric_specialization_light_scenario)

    cleric_specialization_score_output_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-specialization-score-output"))
    cleric_specialization_score_output_parser.set_defaults(handler=run_cleric_specialization_score_output_scenario)

    cleric_specialization_unlock_behavior_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-specialization-unlock-behavior"))
    cleric_specialization_unlock_behavior_parser.set_defaults(handler=run_cleric_specialization_unlock_behavior_scenario)

    cleric_specialization_match_feedback_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-specialization-match-feedback"))
    cleric_specialization_match_feedback_parser.set_defaults(handler=run_cleric_specialization_match_feedback_scenario)

    cleric_assess_visibility_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-assess-visibility"))
    cleric_assess_visibility_parser.set_defaults(handler=run_cleric_assess_visibility_scenario)

    cleric_assess_blockers_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-assess-blockers"))
    cleric_assess_blockers_parser.set_defaults(handler=run_cleric_assess_blockers_scenario)

    cleric_ritual_start_join_messaging_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-start-join-messaging"))
    cleric_ritual_start_join_messaging_parser.set_defaults(handler=run_cleric_ritual_start_join_messaging_scenario)

    cleric_ritual_interruption_locality_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-interruption-locality"))
    cleric_ritual_interruption_locality_parser.set_defaults(handler=run_cleric_ritual_interruption_locality_scenario)

    cleric_ritual_progression_messaging_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-progression-messaging"))
    cleric_ritual_progression_messaging_parser.set_defaults(handler=run_cleric_ritual_progression_messaging_scenario)

    cleric_ritual_antispam_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-antispam"))
    cleric_ritual_antispam_parser.set_defaults(handler=run_cleric_ritual_antispam_scenario)

    cleric_ritual_failure_reduces_quality_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-failure-reduces-quality"))
    cleric_ritual_failure_reduces_quality_parser.set_defaults(handler=run_cleric_ritual_failure_reduces_quality_scenario)

    cleric_ritual_unprepared_revive_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-unprepared-revive"))
    cleric_ritual_unprepared_revive_parser.set_defaults(handler=run_cleric_ritual_unprepared_revive_scenario)

    cleric_ritual_prepare_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-prepare"))
    cleric_ritual_prepare_parser.set_defaults(handler=run_cleric_ritual_prepare_scenario)

    cleric_ritual_restore_flow_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-restore-flow"))
    cleric_ritual_restore_flow_parser.set_defaults(handler=run_cleric_ritual_restore_flow_scenario)

    cleric_ritual_missing_step_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-ritual-missing-step"))
    cleric_ritual_missing_step_parser.set_defaults(handler=run_cleric_ritual_missing_step_scenario)

    cleric_revive_zero_favor_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-revive-zero-favor"))
    cleric_revive_zero_favor_parser.set_defaults(handler=run_cleric_revive_zero_favor_scenario)

    favor_clamp_parser = _add_common_scenario_args(scenario_subparsers.add_parser("favor-clamp"))
    favor_clamp_parser.set_defaults(handler=run_favor_clamp_scenario)

    favor_pray_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("favor-pray-loop"))
    favor_pray_loop_parser.set_defaults(handler=run_favor_pray_loop_scenario)

    favor_decay_parser = _add_common_scenario_args(scenario_subparsers.add_parser("favor-decay"))
    favor_decay_parser.set_defaults(handler=run_favor_decay_scenario)

    grave_creation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-creation"))
    grave_creation_parser.set_defaults(handler=run_grave_creation_scenario)

    grave_recovery_direct_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-recovery-direct"))
    grave_recovery_direct_parser.set_defaults(handler=run_grave_recovery_direct_scenario)

    grave_nonowner_blocked_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-nonowner-blocked"))
    grave_nonowner_blocked_parser.set_defaults(handler=run_grave_nonowner_blocked_scenario)

    grave_partial_recovery_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-partial-recovery"))
    grave_partial_recovery_parser.set_defaults(handler=run_grave_partial_recovery_scenario)

    grave_loss_scaling_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-loss-scaling"))
    grave_loss_scaling_parser.set_defaults(handler=run_grave_loss_scaling_scenario)

    grave_expiry_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-expiry"))
    grave_expiry_parser.set_defaults(handler=run_grave_expiry_scenario)

    grave_multiple_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-multiple"))
    grave_multiple_parser.set_defaults(handler=run_grave_multiple_scenario)

    grave_revive_vs_depart_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-revive-vs-depart"))
    grave_revive_vs_depart_parser.set_defaults(handler=run_grave_revive_vs_depart_scenario)

    grave_reconnect_recovery_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-reconnect-recovery"))
    grave_reconnect_recovery_parser.set_defaults(handler=run_grave_reconnect_recovery_scenario)

    grave_full_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-full-loop"))
    grave_full_loop_parser.set_defaults(handler=run_grave_full_loop_scenario)

    cleric_revive_expired_corpse_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-revive-expired-corpse"))
    cleric_revive_expired_corpse_parser.set_defaults(handler=run_cleric_revive_expired_corpse_scenario)

    cleric_revive_wrong_location_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-revive-wrong-location"))
    cleric_revive_wrong_location_parser.set_defaults(handler=run_cleric_revive_wrong_location_scenario)

    cleric_revive_mid_delay_expiry_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-revive-mid-delay-expiry"))
    cleric_revive_mid_delay_expiry_parser.set_defaults(handler=run_cleric_revive_mid_delay_expiry_scenario)

    economy_parser = _add_common_scenario_args(scenario_subparsers.add_parser("economy"))
    economy_parser.set_defaults(handler=run_economy_scenario)

    bank_parser = _add_common_scenario_args(scenario_subparsers.add_parser("bank"))
    bank_parser.set_defaults(handler=run_bank_scenario)

    grave_recovery_parser = _add_common_scenario_args(scenario_subparsers.add_parser("grave-recovery"))
    grave_recovery_parser.set_defaults(handler=run_grave_recovery_scenario)

    trap_expiry_parser = _add_common_scenario_args(scenario_subparsers.add_parser("trap-expiry"))
    trap_expiry_parser.set_defaults(handler=run_trap_expiry_scenario)

    ticker_execution_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ticker-execution"))
    ticker_execution_parser.set_defaults(handler=run_ticker_execution_scenario)

    interest_renew_benchmark_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-renew-benchmark"))
    interest_renew_benchmark_parser.set_defaults(handler=run_interest_renew_benchmark_scenario)

    interest_dual_mode_compare_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-dual-mode-compare"))
    interest_dual_mode_compare_parser.set_defaults(handler=run_interest_dual_mode_compare_scenario)

    interest_zone_activation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-zone-activation"))
    interest_zone_activation_parser.set_defaults(handler=run_interest_zone_activation_scenario)

    interest_activation_metrics_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-activation-metrics"))
    interest_activation_metrics_parser.set_defaults(handler=run_interest_activation_metrics_scenario)

    interest_debug_command_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-debug-command"))
    interest_debug_command_parser.set_defaults(handler=run_interest_debug_command_scenario)

    interest_direct_activation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-direct-activation"))
    interest_direct_activation_parser.set_defaults(handler=run_interest_direct_activation_scenario)

    interest_scheduled_activation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-scheduled-activation"))
    interest_scheduled_activation_parser.set_defaults(handler=run_interest_scheduled_activation_scenario)

    interest_scheduler_respects_activation_parser = _add_common_scenario_args(
        scenario_subparsers.add_parser("interest-scheduler-respects-activation")
    )
    interest_scheduler_respects_activation_parser.set_defaults(handler=run_interest_scheduler_respects_activation_scenario)

    interest_scheduler_safe_skip_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-scheduler-safe-skip"))
    interest_scheduler_safe_skip_parser.set_defaults(handler=run_interest_scheduler_safe_skip_scenario)

    interest_scheduler_stress_parser = _add_common_scenario_args(scenario_subparsers.add_parser("interest-scheduler-stress"))
    interest_scheduler_stress_parser.set_defaults(handler=run_interest_scheduler_stress_scenario)

    interest_scheduler_duplicate_key_parser = _add_common_scenario_args(
        scenario_subparsers.add_parser("interest-scheduler-duplicate-key")
    )
    interest_scheduler_duplicate_key_parser.set_defaults(handler=run_interest_scheduler_duplicate_key_scenario)

    interest_scheduler_quota_violation_parser = _add_common_scenario_args(
        scenario_subparsers.add_parser("interest-scheduler-quota-violation")
    )
    interest_scheduler_quota_violation_parser.set_defaults(handler=run_interest_scheduler_quota_violation_scenario)

    interest_scheduler_queue_stability_parser = _add_common_scenario_args(
        scenario_subparsers.add_parser("interest-scheduler-queue-stability")
    )
    interest_scheduler_queue_stability_parser.set_defaults(handler=run_interest_scheduler_queue_stability_scenario)

    onboarding_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding_full"))
    onboarding_parser.add_argument("--name", default="DireTestHero")
    onboarding_parser.set_defaults(handler=run_onboarding_full_scenario)

    onboarding_lag_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding_lag"))
    onboarding_lag_parser.set_defaults(handler=run_onboarding_lag_scenario)

    onboarding_no_armor_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding_no_armor"))
    onboarding_no_armor_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_armor_parser.set_defaults(handler=run_onboarding_no_armor_scenario)

    onboarding_no_attack_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding_no_attack"))
    onboarding_no_attack_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_attack_parser.set_defaults(handler=run_onboarding_no_attack_scenario)

    onboarding_no_heal_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding_no_heal"))
    onboarding_no_heal_parser.add_argument("--name", default="DireTestHero")
    onboarding_no_heal_parser.set_defaults(handler=run_onboarding_no_heal_scenario)

    onboarding_movement_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding-movement"))
    onboarding_movement_parser.set_defaults(handler=run_onboarding_movement_scenario)

    training_move_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-move"))
    training_move_parser.set_defaults(handler=run_training_move_scenario)

    training_get_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-get"))
    training_get_parser.set_defaults(handler=run_training_get_scenario)

    training_equip_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-equip"))
    training_equip_parser.set_defaults(handler=run_training_equip_scenario)

    training_equip_alias_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-equip-alias"))
    training_equip_alias_parser.set_defaults(handler=run_training_equip_alias_scenario)

    training_inventory_skip_nudge_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-inventory-skip-nudge"))
    training_inventory_skip_nudge_parser.set_defaults(handler=run_training_inventory_skip_nudge_scenario)

    onboarding_interaction_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding-interaction"))
    onboarding_interaction_parser.set_defaults(handler=run_onboarding_interaction_scenario)

    onboarding_combat_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding-combat"))
    onboarding_combat_parser.set_defaults(handler=run_onboarding_combat_scenario)

    onboarding_complete_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding-complete"))
    onboarding_complete_parser.set_defaults(handler=run_onboarding_complete_scenario)

    training_resurrection_sequence_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-resurrection-sequence"))
    training_resurrection_sequence_parser.set_defaults(handler=run_training_resurrection_sequence_scenario)

    training_between_state_lock_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-between-state-lock"))
    training_between_state_lock_parser.set_defaults(handler=run_training_between_state_lock_scenario)

    training_transport_sequence_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-transport-sequence"))
    training_transport_sequence_parser.set_defaults(handler=run_training_transport_sequence_scenario)

    training_final_location_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-final-location"))
    training_final_location_parser.set_defaults(handler=run_training_final_location_scenario)

    training_control_return_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-control-return"))
    training_control_return_parser.set_defaults(handler=run_training_control_return_scenario)

    training_npc_presence_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-npc-presence"))
    training_npc_presence_parser.set_defaults(handler=run_training_npc_presence_scenario)

    training_recovery_state_parser = _add_common_scenario_args(scenario_subparsers.add_parser("training-recovery-state"))
    training_recovery_state_parser.set_defaults(handler=run_training_recovery_state_scenario)

    death_depart_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-depart-basic"))
    death_depart_basic_parser.set_defaults(handler=run_death_depart_basic_scenario)

    death_depart_keeps_favor_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-depart-keeps-favor"))
    death_depart_keeps_favor_parser.set_defaults(handler=run_death_depart_keeps_favor_scenario)

    death_revive_blocked_after_depart_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-revive-blocked-after-depart"))
    death_revive_blocked_after_depart_parser.set_defaults(handler=run_death_revive_blocked_after_depart_scenario)

    death_sting_applied_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-sting-applied"))
    death_sting_applied_parser.set_defaults(handler=run_death_sting_applied_scenario)

    death_sting_recovery_severity_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-sting-recovery-severity"))
    death_sting_recovery_severity_parser.set_defaults(handler=run_death_sting_recovery_severity_scenario)

    death_favor_softens_sting_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-favor-softens-sting"))
    death_favor_softens_sting_parser.set_defaults(handler=run_death_favor_softens_sting_scenario)

    death_no_double_sting_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-no-double-sting"))
    death_no_double_sting_parser.set_defaults(handler=run_death_no_double_sting_scenario)

    death_revive_interrupted_then_depart_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-revive-interrupted-then-depart"))
    death_revive_interrupted_then_depart_parser.set_defaults(handler=run_death_revive_interrupted_then_depart_scenario)

    death_depart_corpse_missing_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-depart-corpse-missing"))
    death_depart_corpse_missing_parser.set_defaults(handler=run_death_depart_corpse_missing_scenario)

    death_reconnect_dead_state_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-reconnect-dead-state"))
    death_reconnect_dead_state_parser.set_defaults(handler=run_death_reconnect_dead_state_scenario)

    death_depart_final_integration_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-depart-final-integration"))
    death_depart_final_integration_parser.set_defaults(handler=run_death_depart_final_integration_scenario)

    onboarding_blocked_command_parser = _add_common_scenario_args(scenario_subparsers.add_parser("onboarding-blocked-command"))
    onboarding_blocked_command_parser.set_defaults(handler=run_onboarding_blocked_command_scenario)

    chargen_mirror_cycle_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-mirror-cycle"))
    chargen_mirror_cycle_parser.set_defaults(handler=run_chargen_mirror_cycle_scenario)

    chargen_lock_flow_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-lock-flow"))
    chargen_lock_flow_parser.set_defaults(handler=run_chargen_lock_flow_scenario)

    chargen_race_lock_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-race-lock"))
    chargen_race_lock_parser.set_defaults(handler=run_chargen_race_lock_scenario)

    chargen_mirror_render_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-mirror-render"))
    chargen_mirror_render_parser.set_defaults(handler=run_chargen_mirror_render_scenario)

    chargen_transition_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-transition"))
    chargen_transition_parser.set_defaults(handler=run_chargen_transition_scenario)

    chargen_actions_visible_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-actions-visible"))
    chargen_actions_visible_parser.set_defaults(handler=run_chargen_actions_visible_scenario)

    chargen_actions_contextual_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-actions-contextual"))
    chargen_actions_contextual_parser.set_defaults(handler=run_chargen_actions_contextual_scenario)

    chargen_click_executes_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-click-executes"))
    chargen_click_executes_parser.set_defaults(handler=run_chargen_click_executes_scenario)

    chargen_back_navigation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-back-navigation"))
    chargen_back_navigation_parser.set_defaults(handler=run_chargen_back_navigation_scenario)

    chargen_confirmation_gate_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-confirmation-gate"))
    chargen_confirmation_gate_parser.set_defaults(handler=run_chargen_confirmation_gate_scenario)

    chargen_finalize_lock_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-finalize-lock"))
    chargen_finalize_lock_parser.set_defaults(handler=run_chargen_finalize_lock_scenario)

    chargen_no_command_needed_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-no-command-needed"))
    chargen_no_command_needed_parser.set_defaults(handler=run_chargen_no_command_needed_scenario)

    chargen_no_exits_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-no-exits"))
    chargen_no_exits_parser.set_defaults(handler=run_chargen_no_exits_scenario)

    chargen_movement_blocked_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-movement-blocked"))
    chargen_movement_blocked_parser.set_defaults(handler=run_chargen_movement_blocked_scenario)

    chargen_exit_restored_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-exit-restored"))
    chargen_exit_restored_parser.set_defaults(handler=run_chargen_exit_restored_scenario)

    chargen_no_softlock_parser = _add_common_scenario_args(scenario_subparsers.add_parser("chargen-no-softlock"))
    chargen_no_softlock_parser.set_defaults(handler=run_chargen_no_softlock_scenario)

    empath_guild_entry_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-guild-entry"))
    empath_guild_entry_parser.set_defaults(handler=run_empath_guild_entry_scenario)

    empath_guild_aliases_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-guild-aliases"))
    empath_guild_aliases_parser.set_defaults(handler=run_empath_guild_aliases_scenario)

    empath_guild_return_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-guild-return"))
    empath_guild_return_parser.set_defaults(handler=run_empath_guild_return_scenario)

    empath_guild_map_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-guild-map"))
    empath_guild_map_parser.set_defaults(handler=run_empath_guild_map_scenario)

    post_teleport_location_parser = _add_common_scenario_args(scenario_subparsers.add_parser("post-teleport-location"))
    post_teleport_location_parser.set_defaults(handler=run_post_teleport_location_scenario)

    guild_clickable_parser = _add_common_scenario_args(scenario_subparsers.add_parser("guild-clickable"))
    guild_clickable_parser.set_defaults(handler=run_guild_clickable_scenario)

    empath_join_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-join"))
    empath_join_parser.set_defaults(handler=run_empath_join_scenario)

    empath_tutorial_parser = _add_common_scenario_args(scenario_subparsers.add_parser("empath-tutorial"))
    empath_tutorial_parser.set_defaults(handler=run_empath_tutorial_scenario)

    ranger_join_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-join"))
    ranger_join_parser.set_defaults(handler=run_ranger_join_scenario)

    cleric_join_parser = _add_common_scenario_args(scenario_subparsers.add_parser("cleric-join"))
    cleric_join_parser.set_defaults(handler=run_cleric_join_scenario)

    ranger_npc_inquiry_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-npc-inquiry"))
    ranger_npc_inquiry_parser.set_defaults(handler=run_ranger_npc_inquiry_scenario)

    ranger_circle_default_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-circle-default"))
    ranger_circle_default_parser.set_defaults(handler=run_ranger_circle_default_scenario)

    ranger_advance_fail_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-advance-fail"))
    ranger_advance_fail_parser.set_defaults(handler=run_ranger_advance_fail_scenario)

    ranger_advance_success_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-advance-success"))
    ranger_advance_success_parser.set_defaults(handler=run_ranger_advance_success_scenario)

    ranger_advance_feedback_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-advance-feedback"))
    ranger_advance_feedback_parser.set_defaults(handler=run_ranger_advance_feedback_scenario)

    ranger_forage_scaling_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-forage-scaling"))
    ranger_forage_scaling_parser.set_defaults(handler=run_ranger_forage_scaling_scenario)

    ranger_forage_variation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-forage-variation"))
    ranger_forage_variation_parser.set_defaults(handler=run_ranger_forage_variation_scenario)

    ranger_skin_fail_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-skin-fail"))
    ranger_skin_fail_parser.set_defaults(handler=run_ranger_skin_fail_scenario)

    ranger_skin_success_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-skin-success"))
    ranger_skin_success_parser.set_defaults(handler=run_ranger_skin_success_scenario)

    recovery_orderly_parser = _add_common_scenario_args(scenario_subparsers.add_parser("recovery-orderly"))
    recovery_orderly_parser.set_defaults(handler=run_recovery_orderly_scenario)

    aftermath_per_player_parser = _add_common_scenario_args(scenario_subparsers.add_parser("aftermath-per-player"))
    aftermath_per_player_parser.set_defaults(handler=run_aftermath_per_player_scenario)

    aftermath_currency_cap_parser = _add_common_scenario_args(scenario_subparsers.add_parser("aftermath-currency-cap"))
    aftermath_currency_cap_parser.set_defaults(handler=run_aftermath_currency_cap_scenario)

    aftermath_full_kit_parser = _add_common_scenario_args(scenario_subparsers.add_parser("aftermath-full-kit"))
    aftermath_full_kit_parser.set_defaults(handler=run_aftermath_full_kit_scenario)

    coffer_flow_parser = _add_common_scenario_args(scenario_subparsers.add_parser("coffer-flow"))
    coffer_flow_parser.set_defaults(handler=run_coffer_flow_scenario)

    coffer_single_instance_parser = _add_common_scenario_args(scenario_subparsers.add_parser("coffer-single-instance"))
    coffer_single_instance_parser.set_defaults(handler=run_coffer_single_instance_scenario)

    poi_spawn_weight_parser = _add_common_scenario_args(scenario_subparsers.add_parser("poi-spawn-weight"))
    poi_spawn_weight_parser.set_defaults(handler=run_poi_spawn_weight_scenario)

    first_area_entry_parser = _add_common_scenario_args(scenario_subparsers.add_parser("first-area-entry"))
    first_area_entry_parser.set_defaults(handler=run_first_area_entry_scenario)

    first_area_choice_parser = _add_common_scenario_args(scenario_subparsers.add_parser("first-area-choice"))
    first_area_choice_parser.set_defaults(handler=run_first_area_choice_scenario)

    first_area_interaction_parser = _add_common_scenario_args(scenario_subparsers.add_parser("first-area-interaction"))
    first_area_interaction_parser.set_defaults(handler=run_first_area_interaction_scenario)

    first_area_exploration_parser = _add_common_scenario_args(scenario_subparsers.add_parser("first-area-exploration"))
    first_area_exploration_parser.set_defaults(handler=run_first_area_exploration_scenario)

    first_area_linger_parser = _add_common_scenario_args(scenario_subparsers.add_parser("first-area-linger"))
    first_area_linger_parser.set_defaults(handler=run_first_area_linger_scenario)

    e2e_full_lifecycle_all_races_parser = _add_common_scenario_args(scenario_subparsers.add_parser("e2e-full-lifecycle-all-races"))
    e2e_full_lifecycle_all_races_parser.set_defaults(handler=run_e2e_full_lifecycle_all_races_scenario)

    e2e_failure_cases_parser = _add_common_scenario_args(scenario_subparsers.add_parser("e2e-failure-cases"))
    e2e_failure_cases_parser.set_defaults(handler=run_e2e_failure_cases_scenario)

    exp_xp_injection_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-xp-injection"))
    exp_xp_injection_parser.set_defaults(handler=run_exp_xp_injection_scenario)

    exp_hard_stop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-hard-stop"))
    exp_hard_stop_parser.set_defaults(handler=run_exp_hard_stop_scenario)

    exp_difficulty_curve_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-difficulty-curve"))
    exp_difficulty_curve_parser.set_defaults(handler=run_exp_difficulty_curve_scenario)

    exp_low_rank_boost_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-low-rank-boost"))
    exp_low_rank_boost_parser.set_defaults(handler=run_exp_low_rank_boost_scenario)

    exp_miss_learning_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-miss-learning"))
    exp_miss_learning_parser.set_defaults(handler=run_exp_miss_learning_scenario)

    exp_outcome_learning_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-outcome-learning"))
    exp_outcome_learning_parser.set_defaults(handler=run_exp_outcome_learning_scenario)

    exp_event_weight_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-event-weight"))
    exp_event_weight_parser.set_defaults(handler=run_exp_event_weight_scenario)

    exp_mind_lock_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-mind-lock"))
    exp_mind_lock_parser.set_defaults(handler=run_exp_mind_lock_scenario)

    exp_time_to_lock_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-time-to-lock"))
    exp_time_to_lock_parser.set_defaults(handler=run_exp_time_to_lock_scenario)

    exp_rank_scaling_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-rank-scaling"))
    exp_rank_scaling_parser.set_defaults(handler=run_exp_rank_scaling_scenario)

    exp_drain_timing_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-drain-timing"))
    exp_drain_timing_parser.set_defaults(handler=run_exp_drain_timing_scenario)

    exp_rank_gain_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-rank-gain"))
    exp_rank_gain_parser.set_defaults(handler=run_exp_rank_gain_scenario)

    exp_skillset_drain_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-skillset-drain"))
    exp_skillset_drain_parser.set_defaults(handler=run_exp_skillset_drain_scenario)

    exp_wisdom_drain_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-wisdom-drain"))
    exp_wisdom_drain_parser.set_defaults(handler=run_exp_wisdom_drain_scenario)

    exp_single_tick_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-single-tick"))
    exp_single_tick_parser.set_defaults(handler=run_exp_single_tick_scenario)

    exp_offset_behavior_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-offset-behavior"))
    exp_offset_behavior_parser.set_defaults(handler=run_exp_offset_behavior_scenario)

    exp_multi_skill_tick_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-multi-skill-tick"))
    exp_multi_skill_tick_parser.set_defaults(handler=run_exp_multi_skill_tick_scenario)

    exp_inactive_skill_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-inactive-skill"))
    exp_inactive_skill_parser.set_defaults(handler=run_exp_inactive_skill_scenario)

    exp_active_skill_only_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-active-skill-only"))
    exp_active_skill_only_parser.set_defaults(handler=run_exp_active_skill_only_scenario)

    exp_mindstate_transitions_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-mindstate-transitions"))
    exp_mindstate_transitions_parser.set_defaults(handler=run_exp_mindstate_transitions_scenario)

    exp_no_spam_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-no-spam"))
    exp_no_spam_parser.set_defaults(handler=run_exp_no_spam_scenario)

    exp_command_active_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-command-active"))
    exp_command_active_parser.set_defaults(handler=run_exp_command_active_scenario)

    exp_command_all_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-command-all"))
    exp_command_all_parser.set_defaults(handler=run_exp_command_all_scenario)

    exp_stealth_bridge_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-stealth-bridge"))
    exp_stealth_bridge_parser.set_defaults(handler=run_exp_stealth_bridge_scenario)

    exp_stealth_no_observer_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-stealth-no-observer"))
    exp_stealth_no_observer_parser.set_defaults(handler=run_exp_stealth_no_observer_scenario)

    exp_stealth_practice_cap_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-stealth-practice-cap"))
    exp_stealth_practice_cap_parser.set_defaults(handler=run_exp_stealth_practice_cap_scenario)

    exp_stealth_empty_room_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-stealth-empty-room-loop"))
    exp_stealth_empty_room_loop_parser.set_defaults(handler=run_exp_stealth_empty_room_loop_scenario)

    exp_stealth_failure_margins_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-stealth-failure-margins"))
    exp_stealth_failure_margins_parser.set_defaults(handler=run_exp_stealth_failure_margins_scenario)

    exp_stealth_observer_aggregation_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-stealth-observer-aggregation"))
    exp_stealth_observer_aggregation_parser.set_defaults(handler=run_exp_stealth_observer_aggregation_scenario)

    exp_stealth_perception_dual_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-stealth-perception-dual"))
    exp_stealth_perception_dual_parser.set_defaults(handler=run_exp_stealth_perception_dual_scenario)

    exp_stealth_state_machine_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-stealth-state-machine"))
    exp_stealth_state_machine_parser.set_defaults(handler=run_exp_stealth_state_machine_scenario)

    exp_appraisal_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-appraisal-loop"))
    exp_appraisal_loop_parser.set_defaults(handler=run_exp_appraisal_loop_scenario)

    exp_targeted_magic_bridge_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-targeted-magic-bridge"))
    exp_targeted_magic_bridge_parser.set_defaults(handler=run_exp_targeted_magic_bridge_scenario)

    exp_athletics_bridge_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-athletics-bridge"))
    exp_athletics_bridge_parser.set_defaults(handler=run_exp_athletics_bridge_scenario)

    climb_success_parser = _add_common_scenario_args(scenario_subparsers.add_parser("climb-success"))
    climb_success_parser.set_defaults(handler=run_climb_success_scenario)

    climb_failure_parser = _add_common_scenario_args(scenario_subparsers.add_parser("climb-failure"))
    climb_failure_parser.set_defaults(handler=run_climb_failure_scenario)

    climb_partial_parser = _add_common_scenario_args(scenario_subparsers.add_parser("climb-partial"))
    climb_partial_parser.set_defaults(handler=run_climb_partial_scenario)

    climb_xp_parser = _add_common_scenario_args(scenario_subparsers.add_parser("climb-xp"))
    climb_xp_parser.set_defaults(handler=run_climb_xp_scenario)

    climb_repeat_training_parser = _add_common_scenario_args(scenario_subparsers.add_parser("climb-repeat-training"))
    climb_repeat_training_parser.set_defaults(handler=run_climb_repeat_training_scenario)

    ranger_high_hide_visibility_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-high-hide-visibility"))
    ranger_high_hide_visibility_parser.set_defaults(handler=run_ranger_high_hide_visibility_scenario)

    ranger_quartermaster_shop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-quartermaster-shop"))
    ranger_quartermaster_shop_parser.set_defaults(handler=run_ranger_quartermaster_shop_scenario)

    ranger_high_hide_shop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-high-hide-shop"))
    ranger_high_hide_shop_parser.set_defaults(handler=run_ranger_high_hide_shop_scenario)

    ranger_resource_visibility_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-resource-visibility"))
    ranger_resource_visibility_parser.set_defaults(handler=run_ranger_resource_visibility_scenario)

    ranger_resource_sell_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("ranger-resource-sell-loop"))
    ranger_resource_sell_loop_parser.set_defaults(handler=run_ranger_resource_sell_loop_scenario)

    exp_locksmithing_bridge_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-locksmithing-bridge"))
    exp_locksmithing_bridge_parser.set_defaults(handler=run_exp_locksmithing_bridge_scenario)

    exp_debilitation_bridge_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-debilitation-bridge"))
    exp_debilitation_bridge_parser.set_defaults(handler=run_exp_debilitation_bridge_scenario)

    exp_light_edge_bridge_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-light-edge-bridge"))
    exp_light_edge_bridge_parser.set_defaults(handler=run_exp_light_edge_bridge_scenario)

    exp_brawling_bridge_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-brawling-bridge"))
    exp_brawling_bridge_parser.set_defaults(handler=run_exp_brawling_bridge_scenario)

    exp_evasion_passive_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-evasion-passive"))
    exp_evasion_passive_parser.set_defaults(handler=run_exp_evasion_passive_scenario)

    exp_command_visibility_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-command-visibility"))
    exp_command_visibility_parser.set_defaults(handler=run_exp_command_visibility_scenario)

    exp_second_wave_command_visibility_parser = _add_common_scenario_args(scenario_subparsers.add_parser("exp-second-wave-command-visibility"))
    exp_second_wave_command_visibility_parser.set_defaults(handler=run_exp_second_wave_command_visibility_scenario)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    cli_handler = getattr(args, "cli_handler", None)
    if cli_handler is None:
        return _execute_cli_scenario(args)
    return cli_handler(args)


if __name__ == "__main__":
    raise SystemExit(main())