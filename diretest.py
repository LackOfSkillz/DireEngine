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
        all_transcript = "\n".join(ctx.output_log)
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