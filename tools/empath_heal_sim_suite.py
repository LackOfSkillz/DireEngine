import os
import sys
import statistics
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from diretest import _build_fake_delay_queue, _diretest_set_progression_rank, _run_fake_delay_queue, _setup_django


LOG_PATH = os.path.join(REPO_ROOT, "docs", "logs", "empathHealLog.md")
SCENARIO_ITERATIONS = 5
SCENARIO_ORDER = ("A", "B", "C")
SCENARIO_NAMES = {
    "A": "Minor Bleeder",
    "B": "Serious + Internal",
    "C": "Corpse Stabilize + Res + Finish Heal",
}
OBSERVE_TICKS = {"A": 5, "B": 10, "C": 15}

command_module = None
character_module = None
create_object = None

CmdAssess = None
CmdDiagnose = None
CmdMend = None
CmdStabilize = None
CmdTake = None
CmdTouch = None


class EventRecorder:
    def __init__(self):
        self.events = []

    def record(self, channel, text):
        payload = text
        if isinstance(payload, tuple) and payload:
            payload = payload[0]
        self.events.append((str(channel or "GAME"), str(payload or "")))

    def mark(self):
        return len(self.events)

    def lines_since(self, mark):
        return [f"[{channel}] {text}" for channel, text in self.events[mark:]]

    def all_lines(self):
        return [f"[{channel}] {text}" for channel, text in self.events]


def _patch_messages(recorder, room, patient, empath, cleric=None):
    originals = {
        "room_msg_contents": room.msg_contents,
        "patient_msg": patient.msg,
        "empath_msg": empath.msg,
    }
    if cleric is not None:
        originals["cleric_msg"] = cleric.msg

    def build_msg(channel, original):
        def wrapper(text=None, **kwargs):
            recorder.record(channel, text)
            return original(text=text, **kwargs)

        return wrapper

    def room_wrapper(message=None, exclude=None, **kwargs):
        recorder.record("ROOM", message)
        return originals["room_msg_contents"](message, exclude=exclude, **kwargs)

    room.msg_contents = room_wrapper
    patient.msg = build_msg("PATIENT", patient.msg)
    empath.msg = build_msg("EMPATH", empath.msg)
    if cleric is not None:
        cleric.msg = build_msg("CLERIC", cleric.msg)
    return originals


def _restore_messages(room, patient, empath, originals, cleric=None):
    room.msg_contents = originals["room_msg_contents"]
    patient.msg = originals["patient_msg"]
    empath.msg = originals["empath_msg"]
    if cleric is not None and "cleric_msg" in originals:
        cleric.msg = originals["cleric_msg"]


def _run_command(command_cls, caller, args, cmdstring, recorder):
    command = command_cls()
    command.caller = caller
    command.args = str(args or "")
    command.cmdstring = str(cmdstring or "")
    command.func()


def _run_direct_step(actor, command_text, recorder, callback, scheduled=None):
    ok, message = callback()
    actor.msg(message)
    if scheduled is not None:
        _run_fake_delay_queue(scheduled)
    return ok, message


def _set_body_part(patient, part_name, external=0, internal=0, bleed=0):
    body_part = patient.get_body_part(part_name)
    if not body_part:
        return
    body_part["external"] = int(external or 0)
    body_part["internal"] = int(internal or 0)
    body_part["bleed"] = int(bleed or 0)
    body_part["tended"] = False
    body_part["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}


def _reset_common_state(character):
    character.ensure_core_defaults()
    character.db.death_sting = 0
    character.db.death_sting_active = False
    character.db.death_sting_end = 0.0
    character.db.death_sting_severity = 0.0
    character.db.death_sting_hp_cap_ratio = 1.0
    character.db.death_sting_recovery_label = "none"
    character.db.last_medical_decay_at = 0.0
    character.db.last_critical_warning_at = 0.0
    character.db.stabilized_until = 0.0
    character.db.stability_strength = 0.0
    character.db.is_dead = False
    character.db.life_state = "ALIVE"
    character.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0, "trauma": 0}
    character.db.injuries = character_module._copy_default_injuries()
    character.db.hp = int(character.db.max_hp or 100)
    character.db.balance = int(character.db.max_balance or 100)
    character.db.fatigue = 0
    character.db.empath_shock = 0
    character.db.empath_strain = 0
    character.db.empath_overload_until = 0.0
    character.ndb.next_empath_shock_decay_at = 0.0
    character.ndb.next_empath_strain_decay_at = 0.0
    character.ndb.next_empath_feedback_at = 0.0
    character.ndb.empath_recent_healing_until = 0.0
    if hasattr(character, "clear_linked_target"):
        character.clear_linked_target()
    if hasattr(character, "clear_state"):
        for state_key in (
            "empath_channel",
            "empath_transfer_overload",
            "empath_overdraw",
            "resurrection_fragility",
            "resurrection_instability",
        ):
            character.clear_state(state_key)
    character.sync_client_state()


def _prepare_empath(empath):
    empath.set_profession("empath")
    _diretest_set_progression_rank(empath, "empathy", 60)
    _diretest_set_progression_rank(empath, "first_aid", 60)
    _reset_common_state(empath)


def _prepare_cleric(cleric):
    cleric.set_profession("cleric")
    _diretest_set_progression_rank(cleric, "theurgy", 60)
    _diretest_set_progression_rank(cleric, "first_aid", 45)
    _reset_common_state(cleric)
    if hasattr(cleric, "get_devotion_max"):
        devotion_max = int(cleric.get_devotion_max() or 0)
        cleric.db.devotion_current = devotion_max
        cleric.db.devotion = devotion_max


def _prepare_patient(patient):
    _reset_common_state(patient)
    patient.set_favor(0)


def _configure_scenario_a(patient):
    _prepare_patient(patient)
    patient.set_empath_wound("vitality", 8)
    patient.set_empath_wound("bleeding", 6)
    _set_body_part(patient, "left_arm", external=10, internal=0, bleed=4)
    patient.sync_client_state()


def _configure_scenario_b(patient):
    _prepare_patient(patient)
    patient.set_empath_wound("vitality", 52)
    patient.set_empath_wound("bleeding", 26)
    patient.set_empath_wound("trauma", 18)
    _set_body_part(patient, "chest", external=34, internal=28, bleed=10)
    _set_body_part(patient, "abdomen", external=22, internal=24, bleed=7)
    _set_body_part(patient, "head", external=6, internal=0, bleed=1)
    patient.sync_client_state()


def _configure_scenario_c(patient):
    _prepare_patient(patient)
    patient.set_favor(15)
    patient.set_empath_wound("vitality", 62)
    patient.set_empath_wound("bleeding", 32)
    patient.set_empath_wound("trauma", 20)
    _set_body_part(patient, "head", external=8, internal=6, bleed=2)
    _set_body_part(patient, "chest", external=42, internal=28, bleed=14)
    _set_body_part(patient, "abdomen", external=34, internal=24, bleed=10)
    patient.sync_client_state()


def _summarize_body_parts(patient):
    parts = []
    for part_name in ("head", "chest", "abdomen", "left_arm", "right_arm", "left_leg", "right_leg"):
        body_part = patient.get_body_part(part_name)
        if not body_part:
            continue
        external = int(body_part.get("external", 0) or 0)
        internal = int(body_part.get("internal", 0) or 0)
        bleed = int(body_part.get("bleed", 0) or 0)
        if external <= 0 and internal <= 0 and bleed <= 0:
            continue
        parts.append(
            f"{patient.format_body_part_name(part_name)}: external {external}, internal {internal}, bleed {bleed}"
        )
    return "; ".join(parts) if parts else "none"


def _summarize_condition(character):
    wounds = character.get_empath_wounds() if hasattr(character, "get_empath_wounds") else {}
    return (
        f"alive={'NO' if character.is_dead() else 'YES'}"
        f", hp={int(getattr(character.db, 'hp', 0) or 0)}"
        f", vitality={int(wounds.get('vitality', 0) or 0)}"
        f", bleeding={int(wounds.get('bleeding', 0) or 0)}"
        f", fatigue={int(wounds.get('fatigue', 0) or 0)}"
        f", trauma={int(wounds.get('trauma', 0) or 0)}"
        f", medical={character.get_medical_severity_state() if hasattr(character, 'get_medical_severity_state') else 'unknown'}"
        f", shock={int(character.get_empath_shock() if hasattr(character, 'get_empath_shock') else 0)}"
    )


def _observe_tick(label, tick, patient, empath, recorder, now_base):
    mark = recorder.mark()
    patient.process_bleed()
    patient.process_medical_decay(now=now_base + (tick * 12.0))
    if hasattr(empath, "process_bleed"):
        empath.process_bleed()
        empath.process_medical_decay(now=now_base + (tick * 12.0) + 1.0)
    if hasattr(empath, "process_empath_tick"):
        empath.process_empath_tick()
    lines = recorder.lines_since(mark)
    summary = (
        f"Tick {tick}: patient={'dead' if patient.is_dead() else 'alive'}"
        f" | patient hp {int(getattr(patient.db, 'hp', 0) or 0)}"
        f" | patient bleed {int(patient.get_total_bleed() if hasattr(patient, 'get_total_bleed') else 0)}"
        f" | patient medical {patient.get_medical_severity_state() if hasattr(patient, 'get_medical_severity_state') else 'unknown'}"
        f" | empath hp {int(getattr(empath.db, 'hp', 0) or 0)}"
        f" | empath bleed {int(empath.get_empath_wound('bleeding') if hasattr(empath, 'get_empath_wound') else 0)}"
        f" | empath vitality {int(empath.get_empath_wound('vitality') if hasattr(empath, 'get_empath_wound') else 0)}"
    )
    if lines:
        summary += " | Messages: " + " || ".join(lines)
    return summary, lines


def _drive_wound_death(patient, recorder):
    death_lines = []
    for tick in range(1, 13):
        mark = recorder.mark()
        patient.process_bleed()
        patient.process_medical_decay(now=1000.0 + (tick * 12.0))
        death_lines.append(
            f"Death Tick {tick}: patient={'dead' if patient.is_dead() else 'alive'} | hp {int(getattr(patient.db, 'hp', 0) or 0)} | bleed {int(patient.get_total_bleed() if hasattr(patient, 'get_total_bleed') else 0)} | medical {patient.get_medical_severity_state() if hasattr(patient, 'get_medical_severity_state') else 'unknown'}"
            + (" | Messages: " + " || ".join(recorder.lines_since(mark)) if recorder.lines_since(mark) else "")
        )
        if patient.is_dead():
            break
    return death_lines


def _run_scenario_a(run_number, iteration, recorder, room, patient, empath):
    _configure_scenario_a(patient)
    setup_lines = _format_initial_setup("A", room, patient, empath, cleric=None)

    command_trace = []
    diagnose_mark = recorder.mark()
    _run_command(CmdDiagnose, empath, patient.key, f"diagnose {patient.key}", recorder)
    command_trace.append(f"> diagnose {patient.key}")
    diagnose_lines = recorder.lines_since(diagnose_mark)
    _run_command(CmdTouch, empath, patient.key, f"touch {patient.key}", recorder)
    command_trace.append(f"> touch {patient.key}")
    assess_mark = recorder.mark()
    _run_command(CmdAssess, empath, "", "assess", recorder)
    command_trace.append("> assess")
    assess_lines = recorder.lines_since(assess_mark)
    _run_command(CmdTake, empath, "arm", "take arm", recorder)
    command_trace.append("> take arm")

    tick_lines = []
    for tick in range(1, OBSERVE_TICKS["A"] + 1):
        line, _messages = _observe_tick("A", tick, patient, empath, recorder, 2000.0)
        tick_lines.append(line)

    patient_wounds = patient.get_empath_wounds()
    empath_wounds = empath.get_empath_wounds()
    diagnose_assess_output = "\n".join(diagnose_lines + assess_lines).lower()
    remaining_bleed = int(patient.get_total_bleed() if hasattr(patient, "get_total_bleed") else 0)
    transfer_succeeded = remaining_bleed < 4
    patient_stabilized = not patient.is_dead() and int(patient.get_total_bleed() if hasattr(patient, "get_total_bleed") else 0) <= 1
    if remaining_bleed >= 4:
        observed_issue = "body-part transfer reported success but did not stop the active bleed"
    elif "left arm" not in diagnose_assess_output and "arm" not in diagnose_assess_output:
        observed_issue = "body-part location is not explicit in empath diagnostics"
    else:
        observed_issue = "no major issue observed"
    player_feel = "clear" if int(empath_wounds.get("bleeding", 0) or 0) > 0 else "flat"
    return {
        "scenario": "A",
        "setup_lines": setup_lines,
        "command_trace": command_trace,
        "tick_lines": tick_lines,
        "transfer_succeeded": transfer_succeeded,
        "patient_stabilized": patient_stabilized,
        "corpse_res_succeeded": None,
        "patient_redied_after_res": None,
        "final_patient_condition": _summarize_condition(patient),
        "final_empath_condition": _summarize_condition(empath),
        "observed_issue": observed_issue,
        "player_feel": player_feel,
        "extra_flags": {
            "minor_meaningful": int(empath_wounds.get("bleeding", 0) or 0) > 0,
            "diagnostic_location_clear": ("left arm" in diagnose_assess_output or "arm" in diagnose_assess_output),
            "messages": ["clear" if player_feel == "clear" else "flat", "vague" if observed_issue != "no major issue observed" else "clear"],
        },
    }


def _run_scenario_b(run_number, iteration, recorder, room, patient, empath):
    _configure_scenario_b(patient)
    setup_lines = _format_initial_setup("B", room, patient, empath, cleric=None)

    command_trace = []
    _run_command(CmdDiagnose, empath, patient.key, f"diagnose {patient.key}", recorder)
    command_trace.append(f"> diagnose {patient.key}")
    _run_command(CmdTouch, empath, patient.key, f"touch {patient.key}", recorder)
    command_trace.append(f"> touch {patient.key}")
    _run_command(CmdAssess, empath, "", "assess", recorder)
    command_trace.append("> assess")
    _run_command(CmdStabilize, empath, patient.key, f"stabilize {patient.key}", recorder)
    command_trace.append(f"> stabilize {patient.key}")
    _run_command(CmdTake, empath, "bleeding all", "take bleeding all", recorder)
    command_trace.append("> take bleeding all")
    _run_command(CmdTake, empath, "vitality 20", "take vitality 20", recorder)
    command_trace.append("> take vitality 20")

    tick_lines = []
    for tick in range(1, OBSERVE_TICKS["B"] + 1):
        line, _messages = _observe_tick("B", tick, patient, empath, recorder, 3000.0)
        tick_lines.append(line)

    output_text = "\n".join(recorder.all_lines()).lower()
    patient_wounds = patient.get_empath_wounds()
    transfer_succeeded = int(patient_wounds.get("vitality", 0) or 0) < 52 or int(patient_wounds.get("bleeding", 0) or 0) < 26
    patient_stabilized = not patient.is_dead()
    observed_issue = "internal bleeding is not clearly differentiated in player-facing output" if "internal" not in output_text else "no major issue observed"
    player_feel = "tense" if patient_stabilized and int(patient_wounds.get("vitality", 0) or 0) >= 20 else "abrupt"
    return {
        "scenario": "B",
        "setup_lines": setup_lines,
        "command_trace": command_trace,
        "tick_lines": tick_lines,
        "transfer_succeeded": transfer_succeeded,
        "patient_stabilized": patient_stabilized,
        "corpse_res_succeeded": None,
        "patient_redied_after_res": None,
        "final_patient_condition": _summarize_condition(patient),
        "final_empath_condition": _summarize_condition(empath),
        "observed_issue": observed_issue,
        "player_feel": player_feel,
        "extra_flags": {
            "internal_urgency": any("slipping away" in line.lower() or "worsening" in line.lower() for line in recorder.all_lines()),
            "patient_survived_window": not patient.is_dead(),
            "messages": ["clear" if "slipping away" in output_text else "vague", "immersive" if player_feel == "tense" else "flat"],
        },
    }


def _run_cleric_ritual_chain(cleric, corpse, recorder, scheduled, command_trace):
    for action in ("prepare", "stabilize", "restore", "bind"):
        _run_direct_step(
            cleric,
            f"{action} corpse",
            recorder,
            lambda action=action: cleric.prepare_corpse(corpse) if action == "prepare" else cleric.start_cleric_corpse_ritual(corpse, action),
            scheduled=scheduled,
        )
        command_trace.append(f"> {action} corpse")
    ok, _message = _run_direct_step(cleric, "revive corpse", recorder, lambda: cleric.start_cleric_revive(corpse), scheduled=scheduled)
    command_trace.append("> revive corpse")
    return ok


def _run_scenario_c(run_number, iteration, recorder, room, patient, empath, cleric, scheduled):
    _configure_scenario_c(patient)

    death_lines = _drive_wound_death(patient, recorder)
    corpse = patient.get_death_corpse()
    if not corpse:
        raise RuntimeError("Scenario C setup failed to create a corpse from wound death.")
    if hasattr(corpse, "adjust_condition"):
        corpse.adjust_condition(-30)
    else:
        corpse.db.condition = 70.0
    setup_lines = _format_initial_setup("C", room, patient, empath, cleric=cleric)
    setup_lines.append(f"- Corpse condition: {int(round(corpse.get_condition() if hasattr(corpse, 'get_condition') else getattr(corpse.db, 'condition', 0) or 0))}/100")

    command_trace = []
    _run_direct_step(empath, "stabilize corpse", recorder, lambda: empath.stabilize_corpse(corpse))
    command_trace.append("> stabilize corpse")
    corpse_res_succeeded = _run_cleric_ritual_chain(cleric, corpse, recorder, scheduled, command_trace)

    if corpse_res_succeeded and not patient.is_dead():
        _run_command(CmdTouch, empath, patient.key, f"touch {patient.key}", recorder)
        command_trace.append(f"> touch {patient.key}")
        _run_command(CmdAssess, empath, "", "assess", recorder)
        command_trace.append("> assess")
        _run_command(CmdStabilize, empath, patient.key, f"stabilize {patient.key}", recorder)
        command_trace.append(f"> stabilize {patient.key}")
        _run_command(CmdTake, empath, "bleeding all", "take bleeding all", recorder)
        command_trace.append("> take bleeding all")
        _run_command(CmdTake, empath, "vitality 20", "take vitality 20", recorder)
        command_trace.append("> take vitality 20")

    tick_lines = list(death_lines)
    redied = False
    for tick in range(1, OBSERVE_TICKS["C"] + 1):
        line, _messages = _observe_tick("C", tick, patient, empath, recorder, 4000.0)
        tick_lines.append(line)
        if corpse_res_succeeded and patient.is_dead():
            redied = True

    output_text = "\n".join(recorder.all_lines()).lower()
    observed_issue = "corpse stabilization is not enough on its own to neutralize lethal wound burden before resurrection" if corpse_res_succeeded and redied else ("revive failed before post-res healing began" if not corpse_res_succeeded else "no major issue observed")
    player_feel = "awkward" if corpse_res_succeeded and redied else ("clear" if corpse_res_succeeded else "abrupt")
    return {
        "scenario": "C",
        "setup_lines": setup_lines,
        "command_trace": command_trace,
        "tick_lines": tick_lines,
        "transfer_succeeded": any("take bleeding all" in line for line in command_trace),
        "patient_stabilized": bool(getattr(patient.db, "stabilized_until", 0.0) or 0.0) > 0.0,
        "corpse_res_succeeded": corpse_res_succeeded,
        "patient_redied_after_res": redied if corpse_res_succeeded else None,
        "final_patient_condition": _summarize_condition(patient),
        "final_empath_condition": _summarize_condition(empath),
        "observed_issue": observed_issue,
        "player_feel": player_feel,
        "extra_flags": {
            "corpse_stabilization_possible": "carefully tend to the corpse" in output_text,
            "redied_after_res": redied,
            "post_res_healing_required": corpse_res_succeeded,
            "messages": ["clear" if "final rite" in output_text else "confusing", "awkward" if player_feel == "awkward" else "immersive"],
        },
    }


def _format_initial_setup(scenario, room, patient, empath, cleric=None):
    lines = [
        "Initial Setup:",
        f"- Patient state: {_summarize_condition(patient)}",
        f"- Empath state: {_summarize_condition(empath)}",
    ]
    if cleric is not None:
        lines.append(f"- Cleric state: {_summarize_condition(cleric)}")
    else:
        lines.append("- Cleric state: N/A")
    lines.extend(
        [
            f"- Favor: {int(patient.get_favor_current() if hasattr(patient, 'get_favor_current') else getattr(patient.db, 'favor_current', 0) or 0)}",
            f"- Devotion: {int(getattr(getattr(cleric, 'db', None), 'devotion_current', 0) or 0) if cleric is not None else 'N/A'}",
            f"- Room: {room.key}",
            f"- Wounds summary: {_summarize_body_parts(patient)}",
        ]
    )
    return lines


def _format_run(run_number, scenario, iteration, result, setup_lines, recorder):
    lines = [
        f"=== RUN {run_number:02d} ===",
        f"Scenario: {scenario}",
        f"Scenario Name: {SCENARIO_NAMES[scenario]}",
        f"Iteration: {iteration} of {SCENARIO_ITERATIONS}",
        "",
    ]
    lines.extend(setup_lines)
    lines.extend(["", "Command Trace:"])
    lines.extend(result["command_trace"])
    lines.extend(["", "System / Game Output:"])
    lines.extend(recorder.all_lines())
    lines.extend(["", "Tick Observation:"])
    lines.extend(result["tick_lines"])
    lines.extend(["", "Outcome Summary:"])
    lines.append(f"- Transfer succeeded: {'YES' if result['transfer_succeeded'] else 'NO'}")
    lines.append(f"- Patient stabilized: {'YES' if result['patient_stabilized'] else 'NO'}")
    if scenario == "C":
        lines.append(f"- Corpse res succeeded: {'YES' if result['corpse_res_succeeded'] else 'NO'}")
        if result["corpse_res_succeeded"]:
            lines.append(f"- Patient re-died after res: {'YES' if result['patient_redied_after_res'] else 'NO'}")
        else:
            lines.append("- Patient re-died after res: N/A")
    else:
        lines.append("- Corpse res succeeded: N/A")
        lines.append("- Patient re-died after res: N/A")
    lines.append(f"- Final patient condition: {result['final_patient_condition']}")
    lines.append(f"- Final empath condition: {result['final_empath_condition']}")
    lines.append(f"- Observed issue: {result['observed_issue']}")
    lines.append(f"- Player feel: {result['player_feel']}")
    lines.append("")
    return lines


def _messaging_label(results):
    labels = []
    for result in results:
        labels.extend(list(result.get("extra_flags", {}).get("messages", [])))
    unique = []
    for label in labels:
        if label not in unique:
            unique.append(label)
    return ", ".join(unique) if unique else "clear"


def _build_comparative_summary(results):
    by_scenario = {scenario: [entry for entry in results if entry["scenario"] == scenario] for scenario in SCENARIO_ORDER}
    scenario_a = by_scenario["A"]
    scenario_b = by_scenario["B"]
    scenario_c = by_scenario["C"]

    lines = ["=== COMPARATIVE SUMMARY ===", "", "1. Minor wound handling"]
    minor_meaningful = sum(1 for entry in scenario_a if entry["extra_flags"].get("minor_meaningful"))
    minor_responsive = sum(1 for entry in scenario_a if entry["transfer_succeeded"])
    lines.append(f"Did minor bleeding feel meaningful? {'Yes' if minor_meaningful >= 3 else 'No'} ({minor_meaningful}/5 runs showed meaningful empath self-burden)")
    lines.append(f"Did wound-taking feel responsive? {'Yes' if minor_responsive >= 4 else ('Mixed' if minor_responsive > 0 else 'No')} ({minor_responsive}/5 transfers reduced the patient cleanly)")

    lines.append("")
    lines.append("2. Serious/internal handling")
    urgency = sum(1 for entry in scenario_b if entry["extra_flags"].get("internal_urgency"))
    reliable_save = sum(1 for entry in scenario_b if entry["extra_flags"].get("patient_survived_window"))
    lines.append(f"Did internal bleeding create real urgency? {'Yes' if urgency >= 3 else 'No'} ({urgency}/5 runs emitted critical-pressure feedback)")
    lines.append(f"Could the empath reliably save the patient? {'Yes' if reliable_save >= 4 else ('Mixed' if reliable_save > 0 else 'No')} ({reliable_save}/5 runs survived the full observation window)")

    lines.append("")
    lines.append("3. Corpse stabilization chain")
    corpse_stable = sum(1 for entry in scenario_c if entry["extra_flags"].get("corpse_stabilization_possible"))
    res_success = sum(1 for entry in scenario_c if entry["corpse_res_succeeded"])
    redie_count = sum(1 for entry in scenario_c if entry["extra_flags"].get("redied_after_res"))
    corpse_safe_label = 'Yes' if res_success > 0 and redie_count == 0 else ('Mixed' if corpse_stable > 0 and redie_count < res_success else 'No')
    lines.append(f"Could the empath make the corpse safe enough for res? {corpse_safe_label} ({corpse_stable}/5 corpse stabilization steps succeeded, {redie_count}/5 revived patients re-died)")
    lines.append(f"Did the patient still re-die after res in any run? {'Yes' if redie_count > 0 else 'No'} ({redie_count}/5 revived runs)")
    lines.append(f"Was post-res healing mandatory in a way that felt good or awkward? {'Awkward' if redie_count > 0 else 'Natural'}")

    lines.append("")
    lines.append("4. Messaging quality")
    lines.append(f"Scenario A: {_messaging_label(scenario_a)}")
    lines.append(f"Scenario B: {_messaging_label(scenario_b)}")
    lines.append(f"Scenario C: {_messaging_label(scenario_c)}")

    lines.append("")
    lines.append("5. Mechanical concerns")
    concerns = []
    if any("body-part transfer reported success" in entry["observed_issue"] for entry in scenario_a):
        concerns.append("- wound burden not actually reduced")
        concerns.append("- player lacks enough information to act well")
    if any("body-part location" in entry["observed_issue"] for entry in scenario_a):
        if "- player lacks enough information to act well" not in concerns:
            concerns.append("- player lacks enough information to act well")
    if any("internal bleeding is not clearly differentiated" in entry["observed_issue"] for entry in scenario_b):
        concerns.append("- internal bleeding not meaningfully differentiated")
    if any("corpse stabilization is not enough" in entry["observed_issue"] for entry in scenario_c):
        concerns.append("- corpse stabilization not respected by res")
        concerns.append("- res succeeds but body state still lethal without warning")
    empath_burden_high = any("medical=critical" in entry["final_empath_condition"] for entry in results)
    if empath_burden_high:
        concerns.append("- empath burden too high")
    if not concerns:
        concerns.append("- none observed beyond normal scenario pressure")
    lines.extend(concerns)

    lines.append("")
    lines.append("6. Recommended fixes")
    fixes = []
    if any("body-part transfer reported success" in entry["observed_issue"] for entry in scenario_a):
        fixes.extend([
            "Issue: Body-part empath transfer on a minor bleeder does not actually stop the underlying bleed.",
            "Likely Cause: Selector-based empath transfer reduces aggregate wound state but is not clearing the corresponding body-part bleed value.",
            "Recommended Fix: When a selector-based transfer succeeds, propagate the reduction into the matching injury record so active bleeding actually changes.",
            "Priority: High",
            "",
        ])
    if any("body-part location" in entry["observed_issue"] for entry in scenario_a):
        fixes.extend([
            "Issue: Empath diagnostics do not identify the wounded body part clearly in minor cases.",
            "Likely Cause: `diagnose` and `assess` only report aggregate empath wound buckets.",
            "Recommended Fix: Add body-part context from injury data to empath diagnosis and assess output when a dominant wound source exists.",
            "Priority: Medium",
            "",
        ])
    if any("internal bleeding is not clearly differentiated" in entry["observed_issue"] for entry in scenario_b):
        fixes.extend([
            "Issue: Internal bleeding pressure is real mechanically but not explicit enough in the output.",
            "Likely Cause: Bleed escalation messaging is generic and does not mention internal trauma separately.",
            "Recommended Fix: Add explicit internal-bleeding diagnosis lines and a distinct warning when internal wounds keep generating bleed.",
            "Priority: High",
            "",
        ])
    if any("corpse stabilization is not enough" in entry["observed_issue"] for entry in scenario_c):
        fixes.extend([
            "Issue: Corpse stabilization before resurrection does not make the revived body safe enough on its own.",
            "Likely Cause: Empath corpse stabilization only improves corpse condition/decay and does not reduce the owner's lethal wound burden.",
            "Recommended Fix: Either let empath corpse stabilization reduce carried wound burden, or surface a clear warning that post-res living stabilization is still mandatory.",
            "Priority: High",
            "",
        ])
    if any("medical=critical" in entry["final_empath_condition"] for entry in results):
        fixes.extend([
            "Issue: Empath self-burden remains dangerously high after serious interventions.",
            "Likely Cause: Transfer backlash plus limited self-mend may overshoot recovery pacing for solo treatment.",
            "Recommended Fix: Revisit empath backlash scaling or improve self-recovery tools after large vitality/bleeding transfers.",
            "Priority: Medium",
            "",
        ])
    if not fixes:
        fixes.extend([
            "Issue: No material issues surfaced in this run set.",
            "Likely Cause: Current empath and cleric flows held under the tested severity bands.",
            "Recommended Fix: No immediate mechanical changes required.",
            "Priority: Low",
        ])
    lines.extend(fixes)
    return lines


def run_single(run_number, scenario, iteration):
    room = None
    patient = None
    empath = None
    cleric = None
    recorder = EventRecorder()
    originals = None
    scheduled = None
    original_delay = None
    try:
        room = create_object("typeclasses.rooms.Room", key=f"SIM_EMPATH_ROOM_{scenario}_{run_number:02d}", nohome=True)
        room.db.is_shrine = True
        patient = create_object("typeclasses.characters.Character", key=f"SIM_PATIENT_{scenario}_{run_number:02d}", location=room, home=room)
        empath = create_object("typeclasses.characters.Character", key=f"SIM_EMPATH_{scenario}_{run_number:02d}", location=room, home=room)
        cleric = create_object("typeclasses.characters.Character", key=f"SIM_CLERIC_{scenario}_{run_number:02d}", location=room, home=room) if scenario == "C" else None

        _prepare_empath(empath)
        _prepare_patient(patient)
        if cleric is not None:
            _prepare_cleric(cleric)

        originals = _patch_messages(recorder, room, patient, empath, cleric=cleric)
        if scenario == "C":
            scheduled, fake_delay = _build_fake_delay_queue()
            original_delay = character_module.delay
            character_module.delay = fake_delay

        if scenario == "A":
            result = _run_scenario_a(run_number, iteration, recorder, room, patient, empath)
        elif scenario == "B":
            result = _run_scenario_b(run_number, iteration, recorder, room, patient, empath)
        else:
            result = _run_scenario_c(run_number, iteration, recorder, room, patient, empath, cleric, scheduled)

        return result, result["setup_lines"], recorder
    finally:
        if scenario == "C" and original_delay is not None:
            character_module.delay = original_delay
        if originals is not None:
            _restore_messages(room, patient, empath, originals, cleric=cleric)
        for obj in (cleric, empath, patient, room):
            if obj is None:
                continue
            try:
                obj.delete()
            except Exception:
                pass


def main():
    global command_module, character_module, create_object
    global CmdAssess, CmdDiagnose, CmdMend, CmdStabilize, CmdTake, CmdTouch

    _setup_django()

    import typeclasses.characters as loaded_character_module
    from commands.cmd_assess import CmdAssess as LoadedCmdAssess
    from commands.cmd_diagnose import CmdDiagnose as LoadedCmdDiagnose
    from commands.cmd_mend import CmdMend as LoadedCmdMend
    from commands.cmd_stabilize import CmdStabilize as LoadedCmdStabilize
    from commands.cmd_take import CmdTake as LoadedCmdTake
    from commands.cmd_touch import CmdTouch as LoadedCmdTouch
    from evennia.utils.create import create_object as loaded_create_object

    character_module = loaded_character_module
    create_object = loaded_create_object
    CmdAssess = LoadedCmdAssess
    CmdDiagnose = LoadedCmdDiagnose
    CmdMend = LoadedCmdMend
    CmdStabilize = LoadedCmdStabilize
    CmdTake = LoadedCmdTake
    CmdTouch = LoadedCmdTouch

    all_results = []
    lines = []
    run_number = 1
    for scenario in SCENARIO_ORDER:
        for iteration in range(1, SCENARIO_ITERATIONS + 1):
            result, setup_lines, recorder = run_single(run_number, scenario, iteration)
            result["scenario"] = scenario
            all_results.append(result)
            lines.extend(_format_run(run_number, scenario, iteration, result, setup_lines, recorder))
            run_number += 1

    lines.extend(_build_comparative_summary(all_results))
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).strip() + "\n")
    print(f"Wrote {LOG_PATH} with {len(all_results)} runs.")


if __name__ == "__main__":
    main()