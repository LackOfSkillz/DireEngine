import os
import sys
import statistics
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from diretest import _build_fake_delay_queue, _run_fake_delay_queue, _setup_django


character_module = None
CmdBind = None
CmdPrepare = None
CmdResurrect = None
CmdRestore = None
CmdStabilize = None
create_object = None


FAVOR_LEVELS = [0, 1, 5, 15]
RUNS_PER_FAVOR = 5
POST_REVIVE_TICKS = 20
LOG_PATH = "resLog.ms"

WOUND_PROFILE = {
    "head": {"external": 8, "internal": 6, "bleed": 2},
    "chest": {"external": 42, "internal": 28, "bleed": 14},
    "abdomen": {"external": 34, "internal": 24, "bleed": 10},
}

MEDICAL_PROFILE = {
    "vitality": 62,
    "bleeding": 32,
    "fatigue": 0,
    "poison": 0,
    "disease": 0,
    "trauma": 0,
}


class EventRecorder:
    def __init__(self):
        self.events = []
        self._sequence = 0

    def record(self, channel, text):
        payload = text
        if isinstance(payload, tuple) and payload:
            payload = payload[0]
        entry = {
            "index": self._sequence,
            "channel": str(channel or "GAME"),
            "text": str(payload or ""),
        }
        self._sequence += 1
        self.events.append(entry)

    def mark(self):
        return len(self.events)

    def lines_since(self, mark):
        return [f"[{entry['channel']}]: {entry['text']}" for entry in self.events[mark:]]

    def all_lines(self):
        return [f"[{entry['channel']}]: {entry['text']}" for entry in self.events]


def _patch_messages(recorder, room, cleric, target):
    originals = {
        "cleric_msg": cleric.msg,
        "target_msg": target.msg,
        "room_msg_contents": room.msg_contents,
    }

    def build_msg(channel, original):
        def wrapper(text=None, **kwargs):
            recorder.record(channel, text)
            return original(text=text, **kwargs)

        return wrapper

    def room_wrapper(message=None, exclude=None, **kwargs):
        recorder.record("ROOM", message)
        return originals["room_msg_contents"](message, exclude=exclude, **kwargs)

    cleric.msg = build_msg("CLERIC", cleric.msg)
    target.msg = build_msg("TARGET", target.msg)
    room.msg_contents = room_wrapper
    return originals


def _restore_messages(room, cleric, target, originals):
    cleric.msg = originals["cleric_msg"]
    target.msg = originals["target_msg"]
    room.msg_contents = originals["room_msg_contents"]


def _run_command(command_cls, caller, args, cmdstring, recorder, scheduled=None):
    command = command_cls()
    command.caller = caller
    command.args = str(args or "")
    command.cmdstring = cmdstring
    recorder.record("TRACE", f"> {cmdstring} {args}".rstrip())
    command.func()
    if scheduled is not None:
        _run_fake_delay_queue(scheduled)


def _run_ritual_step(caller, corpse, action, recorder, scheduled=None):
    recorder.record("TRACE", f"> {action} corpse")
    if action == "prepare":
        ok, message = caller.prepare_corpse(corpse)
    elif action == "revive":
        ok, message = caller.start_cleric_revive(corpse)
    else:
        ok, message = caller.start_cleric_corpse_ritual(corpse, action)
    caller.msg(message)
    if scheduled is not None:
        _run_fake_delay_queue(scheduled)
    return ok


def _reset_target_state(target, favor):
    target.ensure_core_defaults()
    target.set_favor(favor)
    target.db.death_sting = 0
    target.db.death_sting_active = False
    target.db.death_sting_end = 0.0
    target.db.death_sting_severity = 0.0
    target.db.death_sting_hp_cap_ratio = 1.0
    target.db.death_sting_recovery_label = "none"
    target.db.last_medical_decay_at = 0.0
    target.db.last_critical_warning_at = 0.0
    target.db.stabilized_until = 0.0
    target.db.stability_strength = 0.0
    target.db.is_dead = False
    target.db.life_state = "ALIVE"
    target.db.wounds = dict(MEDICAL_PROFILE)
    for wound_key, wound_value in MEDICAL_PROFILE.items():
        target.set_empath_wound(wound_key, wound_value)
    for part_name, values in WOUND_PROFILE.items():
        body_part = target.get_body_part(part_name)
        if not body_part:
            continue
        body_part["external"] = int(values.get("external", 0) or 0)
        body_part["internal"] = int(values.get("internal", 0) or 0)
        body_part["bleed"] = int(values.get("bleed", 0) or 0)
        body_part["tended"] = False
        body_part["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}
    target.db.hp = int(target.db.max_hp or 100)
    target.sync_client_state()


def _drive_wound_death(target, recorder):
    tick_lines = []
    for tick in range(1, 13):
        recorder.record("TRACE", f"> wound tick {tick}")
        tick_mark = recorder.mark()
        target.process_bleed()
        target.process_medical_decay(now=1000.0 + (tick * 12.0))
        state = "dead" if target.is_dead() else "alive"
        tick_lines.append(
            {
                "tick": tick,
                "state": state,
                "hp": int(getattr(target.db, "hp", 0) or 0),
                "bleed": int(target.get_total_bleed() if hasattr(target, "get_total_bleed") else 0),
                "medical": str(target.get_medical_severity_state() if hasattr(target, "get_medical_severity_state") else "unknown"),
                "messages": recorder.lines_since(tick_mark),
            }
        )
        if target.is_dead():
            break
    return tick_lines


def _observe_post_revive(target, recorder):
    observations = []
    second_death_tick = None
    for tick in range(1, POST_REVIVE_TICKS + 1):
        tick_mark = recorder.mark()
        recorder.record("TRACE", f"> observe tick {tick}")
        if not target.is_dead():
            target.process_bleed()
            target.process_medical_decay(now=2000.0 + (tick * 12.0))
        alive = not target.is_dead()
        if not alive and second_death_tick is None:
            second_death_tick = tick
        observations.append(
            {
                "tick": tick,
                "alive": alive,
                "hp": int(getattr(target.db, "hp", 0) or 0),
                "bleed": int(target.get_total_bleed() if hasattr(target, "get_total_bleed") else 0),
                "medical": str(target.get_medical_severity_state() if hasattr(target, "get_medical_severity_state") else "unknown"),
                "messages": recorder.lines_since(tick_mark),
            }
        )
    return observations, second_death_tick


def _classify_player_feel(second_death_tick, observations):
    if second_death_tick is not None and second_death_tick <= 3:
        return "abrupt"
    if second_death_tick is not None:
        return "punishing"
    critical_ticks = [entry for entry in observations if entry["medical"] == "critical"]
    if critical_ticks:
        return "tense"
    return "expected"


def _classify_observed_issue(second_death_tick, observations):
    if second_death_tick is not None:
        return "wounds persisted and caused a second death"
    if any(entry["bleed"] > 0 for entry in observations):
        return "wounds persisted after revive but did not become lethal in-window"
    return "no immediate post-revive wound recursion observed"


def _format_run(run_number, favor, run_result):
    lines = [
        f"=== RUN {run_number:02d} ===",
        f"Favor: {favor}",
        "Death Type: Wounds",
        "Empath Healing: NONE",
        "Scenario: Base Resurrection + Wound Recursion Observation",
        "COMMAND TRACE",
    ]
    lines.extend(run_result["command_trace"])
    lines.append("SYSTEM OUTPUT")
    lines.extend(run_result["system_output"])
    lines.append("STATE TRANSITIONS")
    lines.extend(run_result["state_transitions"])
    lines.append("POST-REVIVE OBSERVATION")
    lines.extend(run_result["post_revive_lines"])
    lines.append("RESULT SUMMARY")
    lines.append(f"Revive Success: {'YES' if run_result['revive_success'] else 'NO'}")
    lines.append(f"Survival Duration: {run_result['survival_duration']}")
    lines.append(f"Second Death: {'YES' if run_result['second_death'] else 'NO'}")
    lines.append(f"Observed Issue: {run_result['observed_issue']}")
    lines.append(f"Player Feel: {run_result['player_feel']}")
    lines.append("")
    return lines


def _format_validation(results):
    lines = ["=== VALIDATION CHECKS ==="]
    tier_stats = {}
    for favor in FAVOR_LEVELS:
        tier_results = [entry for entry in results if entry["favor"] == favor]
        survival_ticks = [entry["survival_ticks_value"] for entry in tier_results]
        second_deaths = sum(1 for entry in tier_results if entry["second_death"])
        tier_stats[favor] = {
            "avg_survival": statistics.mean(survival_ticks) if survival_ticks else 0.0,
            "second_deaths": second_deaths,
        }

    monotonic = (
        tier_stats[0]["avg_survival"] <= tier_stats[1]["avg_survival"] <= tier_stats[5]["avg_survival"] <= tier_stats[15]["avg_survival"]
    )
    lines.append("1. Favor Scaling")
    lines.append(
        "Hold TRUE? "
        + ("YES" if monotonic else "NO")
        + f" | avg survival ticks -> 0:{tier_stats[0]['avg_survival']:.1f}, 1:{tier_stats[1]['avg_survival']:.1f}, 5:{tier_stats[5]['avg_survival']:.1f}, 15:{tier_stats[15]['avg_survival']:.1f}"
    )

    wound_persisted = any(entry["observed_issue"].startswith("wounds persisted") for entry in results)
    lines.append("2. Wound Persistence")
    lines.append("Persisted after revive? " + ("YES" if wound_persisted else "NO"))

    double_death_count = sum(1 for entry in results if entry["second_death"])
    lines.append("3. Double Death Behavior")
    lines.append(f"Revive -> die again observed in {double_death_count}/{len(results)} runs")

    all_output = "\n".join(line for entry in results for line in entry["system_output"]).lower()
    messaging_quality = "clear enough" if ("bleed" in all_output or "slipping away" in all_output) else "missing cause feedback"
    lines.append("4. Messaging Quality")
    lines.append(f"Observed messaging quality: {messaging_quality}")

    dominant_feel = statistics.mode([entry["player_feel"] for entry in results]) if results else "unknown"
    lines.append("5. System Feel")
    lines.append(f"Dominant feel across runs: {dominant_feel}")
    lines.append("")
    return lines


def run_single_simulation(run_number, favor):
    from evennia.utils.search import search_object

    room = None
    cleric = None
    target = None
    recorder = EventRecorder()
    run_result = None
    scheduled = None
    original_delay = character_module.delay

    try:
        room = create_object("typeclasses.rooms.Room", key=f"SIM_RES_ROOM_{run_number:02d}", nohome=True)
        room.db.is_shrine = True
        cleric = create_object("typeclasses.characters.Character", key=f"SIM_RES_CLERIC_{run_number:02d}", location=room, home=room)
        target = create_object("typeclasses.characters.Character", key=f"SIM_RES_TARGET_{run_number:02d}", location=room, home=room)
        cleric.ensure_core_defaults()
        target.ensure_core_defaults()
        cleric.set_profession("cleric")
        if hasattr(cleric, "get_devotion_max"):
            cleric.db.devotion_current = cleric.get_devotion_max()

        originals = _patch_messages(recorder, room, cleric, target)
        scheduled, fake_delay = _build_fake_delay_queue()
        character_module.delay = fake_delay

        command_trace = [
            f"> reset favor {favor}",
            "> reset death_sting 0",
            "> reset debuffs and wound state",
            "> apply heavy wound profile",
            "> confirm NO empath healing",
        ]
        _reset_target_state(target, favor)

        predeath_ticks = _drive_wound_death(target, recorder)
        corpse = target.get_death_corpse()
        if not corpse:
            raise RuntimeError("Wound simulation did not produce a corpse.")

        for cmdstring in ("prepare", "stabilize", "restore", "bind"):
            _run_ritual_step(cleric, corpse, cmdstring, recorder, scheduled=scheduled)
            command_trace.append(f"> {cmdstring} corpse")

        _run_ritual_step(cleric, corpse, "revive", recorder, scheduled=scheduled)
        command_trace.append("> revive corpse")

        revive_success = not target.is_dead()
        observations, second_death_tick = _observe_post_revive(target, recorder)
        effective_second_death_tick = second_death_tick if revive_success else None

        state_transitions = []
        for tick_entry in predeath_ticks:
            state_transitions.append(
                f"Pre-Death Tick {tick_entry['tick']}: {tick_entry['state']} | HP {tick_entry['hp']} | Bleed {tick_entry['bleed']} | Medical {tick_entry['medical']}"
            )
        state_transitions.append("Corpse created from wound death.")
        state_transitions.append("Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.")
        state_transitions.append(f"Revived: {'YES' if revive_success else 'NO'}")
        if not revive_success:
            state_transitions.append("Revive failed; no post-revive survival window occurred.")
        elif effective_second_death_tick is not None:
            state_transitions.append(f"Second death triggered during post-revive observation at tick {effective_second_death_tick}.")
        else:
            state_transitions.append(f"Survived full {POST_REVIVE_TICKS}-tick observation window.")

        post_revive_lines = []
        for observation in observations:
            summary = (
                f"Tick {observation['tick']}: {'alive' if observation['alive'] else 'dead'}"
                f" | HP {observation['hp']} | Bleed {observation['bleed']} | Medical {observation['medical']}"
            )
            if observation["messages"]:
                summary += " | Messages: " + " || ".join(observation["messages"])
            post_revive_lines.append(summary)

        if not revive_success:
            survival_duration = "not revived"
            observed_issue = "revive failed due to insufficient lingering favor"
            player_feel = "gated"
        else:
            survival_duration = (
                f"{effective_second_death_tick} ticks"
                if effective_second_death_tick is not None
                else f">= {POST_REVIVE_TICKS} ticks"
            )
            observed_issue = _classify_observed_issue(effective_second_death_tick, observations)
            player_feel = _classify_player_feel(effective_second_death_tick, observations)
        run_result = {
            "favor": favor,
            "command_trace": command_trace,
            "system_output": recorder.all_lines(),
            "state_transitions": state_transitions,
            "post_revive_lines": post_revive_lines,
            "revive_success": revive_success,
            "survival_duration": survival_duration,
            "survival_ticks_value": 0 if not revive_success else (effective_second_death_tick if effective_second_death_tick is not None else POST_REVIVE_TICKS),
            "second_death": effective_second_death_tick is not None,
            "observed_issue": observed_issue,
            "player_feel": player_feel,
        }

        _restore_messages(room, cleric, target, originals)
        return run_result
    finally:
        character_module.delay = original_delay
        for obj in (cleric, target, room):
            if obj:
                try:
                    obj.delete()
                except Exception:
                    pass


def main():
    global character_module, CmdBind, CmdPrepare, CmdResurrect, CmdRestore, CmdStabilize, create_object

    _setup_django()
    import typeclasses.characters as loaded_character_module
    from commands.cmd_bind import CmdBind as LoadedCmdBind
    from commands.cmd_prepare import CmdPrepare as LoadedCmdPrepare
    from commands.cmd_resurrect import CmdResurrect as LoadedCmdResurrect
    from commands.cmd_restore import CmdRestore as LoadedCmdRestore
    from commands.cmd_stabilize import CmdStabilize as LoadedCmdStabilize
    from evennia.utils.create import create_object as loaded_create_object

    character_module = loaded_character_module
    CmdBind = LoadedCmdBind
    CmdPrepare = LoadedCmdPrepare
    CmdResurrect = LoadedCmdResurrect
    CmdRestore = LoadedCmdRestore
    CmdStabilize = LoadedCmdStabilize
    create_object = loaded_create_object

    results = []
    lines = []
    run_number = 1
    for favor in FAVOR_LEVELS:
        for _ in range(RUNS_PER_FAVOR):
            run_result = run_single_simulation(run_number, favor)
            results.append(run_result)
            lines.extend(_format_run(run_number, favor, run_result))
            run_number += 1

    lines.extend(_format_validation(results))

    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).strip() + "\n")

    print(f"Wrote {LOG_PATH} with {len(results)} runs.")


if __name__ == "__main__":
    main()