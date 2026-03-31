import argparse
import json
import os
from pathlib import Path
import sys
import time
import traceback

from tools.diretest.core.diff import diff_snapshots as build_snapshot_diff
from tools.diretest.core.artifacts import write_artifacts
from tools.diretest.core.baselines import METRIC_SPECS, compare_named_baseline, load_named_baseline, save_named_baseline
from tools.diretest.core.failures import build_failure_summary
from tools.diretest.core.runner import run_scenario
from tools.diretest.core.seed import set_seed


SCENARIO_REGISTRY = {}


def register_scenario(name, *, metadata=None):
    scenario_name = str(name or "").strip()
    if not scenario_name:
        raise ValueError("DireTest scenario name must be a non-empty string.")
    scenario_metadata = dict(metadata or {})

    def decorator(func):
        SCENARIO_REGISTRY[scenario_name] = func
        setattr(func, "diretest_scenario_name", scenario_name)
        setattr(func, "diretest_metadata", scenario_metadata)
        return func

    return decorator


def _get_registered_scenario(name):
    return SCENARIO_REGISTRY.get(str(name or "").strip())


def _write_cli_failure_artifact(scenario_name, seed, failure_type, message, mode="direct"):
    run_id = f"{str(scenario_name or 'scenario').replace(' ', '_').lower()}_{str(mode or 'direct')}_{int(seed or 0)}"
    artifact_dir = write_artifacts(
        run_id,
        {
            "scenario": {
                "name": str(scenario_name or "scenario"),
                "mode": str(mode or "direct"),
                "seed": int(seed or 0),
            },
            "seed": int(seed or 0),
            "command_log": [],
            "snapshots": [],
            "diffs": [],
            "metrics": {
                "exit_code": 1,
                "failure_type": str(failure_type or "unexpected_exception"),
            },
            "failure_summary": build_failure_summary(
                failure_type=failure_type,
                message=message,
                scenario=scenario_name,
                seed=seed,
                mode=mode,
            ),
            "traceback": str(message or ""),
        },
    )
    return str(artifact_dir)


def _load_json_file(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_snapshot_reference(reference):
    raw = str(reference or "").strip()
    if not raw:
        raise ValueError("Snapshot reference cannot be empty.")

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


def _parse_seed_text(seed_text):
    raw = str(seed_text or "").strip()
    if raw.startswith("seed="):
        raw = raw.split("=", 1)[1]
    return int(raw or 0)


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


@register_scenario("combat-basic")
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

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="combat-basic")


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
        ctx.cmd("depart full")
        ctx.cmd("depart confirm")
        ctx.snapshot("departed")

        labels = ctx.get_snapshot_labels()
        expected_labels = ["alive", "dead", "departed"]
        if labels != expected_labels:
            raise AssertionError(f"Death-loop snapshot labels drifted: expected {expected_labels}, got {labels}")

        death_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("alive"), ctx.get_snapshot_by_label("dead"))
        depart_diff = ctx.diff_snapshots(ctx.get_snapshot_by_label("dead"), ctx.get_snapshot_by_label("departed"))

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
        if depart_diff["character_changes"]["coins_delta"] != 37:
            raise AssertionError(f"Depart diff did not restore kept coins: {depart_diff}")
        if depart_diff["inventory_changes"]["added"] != ["TEST_DEATH_TOKEN"]:
            raise AssertionError(f"Depart diff did not restore carried items: {depart_diff}")
        if corpse.key not in depart_diff["object_delta_changes"]["deleted"]:
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

    return _run_registered_scenario(args, scenario, auto_snapshot=False, name="death-loop")


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
        "lag_policy_reason": "Structural corpse decay scheduling validation should report lag without failing on environment-specific latency.",
    },
)
def run_grave_recovery_scenario(args):
    _setup_django()

    def scenario(ctx):
        from world.systems.scheduler import flush_due, get_scheduler_snapshot

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

        corpse.db.decay_time = time.time() + 0.1
        ctx.direct(corpse.schedule_decay_transition)
        scheduler_snapshot = get_scheduler_snapshot() or {}
        active_jobs = list(scheduler_snapshot.get("active_jobs", []) or [])
        decay_key = corpse._get_decay_schedule_key() if hasattr(corpse, "_get_decay_schedule_key") else None
        if not any(job.get("key") == decay_key and job.get("system") == "world.corpse_decay" for job in active_jobs):
            raise AssertionError(f"Grave-recovery scenario did not register corpse decay scheduler metadata: {scheduler_snapshot}")

        time.sleep(0.15)
        ctx.direct(flush_due)
        grave = character.get_owned_grave(location=room) if hasattr(character, "get_owned_grave") else None
        if not grave:
            raise AssertionError("Grave-recovery scenario did not decay the corpse into a grave via scheduler expiry.")
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

        if grave.key not in grave_decay_diff["object_delta_changes"]["created"]:
            raise AssertionError(f"Grave decay diff did not record grave creation: {grave_decay_diff}")
        if corpse.key not in grave_decay_diff["object_delta_changes"]["deleted"]:
            raise AssertionError(f"Grave decay diff did not record corpse removal: {grave_decay_diff}")

        if not depart_diff["character_changes"]["revived"]:
            raise AssertionError(f"Grave depart diff did not record revival: {depart_diff}")
        if depart_diff["inventory_changes"]["added"] or depart_diff["character_changes"]["coins_delta"] != 0:
            raise AssertionError(f"Grave depart unexpectedly restored belongings: {depart_diff}")

        if recover_diff["inventory_changes"]["added"] != ["TEST_GRAVE_TOKEN"]:
            raise AssertionError(f"Grave recover diff did not restore the grave item: {recover_diff}")
        if recover_diff["character_changes"]["coins_delta"] != 29:
            raise AssertionError(f"Grave recover diff did not restore grave coins: {recover_diff}")
        if grave.key not in recover_diff["object_delta_changes"]["deleted"]:
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
            "corpse_decay_key": decay_key,
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
    print(f"Seed: {payload['seed']}")
    print(f"Exit Code: {payload['exit_code']}")
    print(f"Artifact Dir: {payload['artifact_dir']}")
    if traceback_text:
        print("Traceback:")
        print(traceback_text)
    status = "PASS" if int(exit_code) == 0 else "FAIL"
    print(f"{status}: {payload['scenario']}")
    print(f"See artifacts: {payload['artifact_dir']}")


def _execute_cli_scenario(args):
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
    scenario_parser.set_defaults(cli_handler=_execute_cli_scenario)
    scenario_subparsers = scenario_parser.add_subparsers(dest="scenario_name", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(cli_handler=_handle_list_command)

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

    movement_parser = _add_common_scenario_args(scenario_subparsers.add_parser("movement"))
    movement_parser.set_defaults(handler=run_movement_scenario)

    rt_timing_parser = _add_common_scenario_args(scenario_subparsers.add_parser("rt-timing"))
    rt_timing_parser.set_defaults(handler=run_rt_timing_scenario)

    inventory_parser = _add_common_scenario_args(scenario_subparsers.add_parser("inventory"))
    inventory_parser.set_defaults(handler=run_inventory_scenario)

    combat_basic_parser = _add_common_scenario_args(scenario_subparsers.add_parser("combat-basic"))
    combat_basic_parser.set_defaults(handler=run_combat_basic_scenario)

    death_loop_parser = _add_common_scenario_args(scenario_subparsers.add_parser("death-loop"))
    death_loop_parser.set_defaults(handler=run_death_loop_scenario)

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