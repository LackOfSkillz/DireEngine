import os
import statistics
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from diretest import _build_fake_delay_queue, _run_fake_delay_queue, _setup_django


LOG_PATH = os.path.join(REPO_ROOT, "docs", "logs", "fullDeathToRes.md")
FAVOR_LEVELS = (0, 1, 5, 15)
WOUND_ORDER = ("A", "B", "C", "D")
WOUND_NAMES = {
    "A": "No wounds",
    "B": "Minor bruising",
    "C": "Multiple light bleeders",
    "D": "Severe + internal bleeding",
}
DECAY_STAGES = {
    0: "Fresh",
    1: "Early decay",
    2: "Mid decay",
    3: "Late decay",
}
DECAY_STAGE_RATIOS = {
    0: 0.05,
    1: 0.30,
    2: 0.55,
    3: 0.80,
}
POST_RES_TICKS = 20
PRE_HEAL_TICKS = 10
CORPSE_DECAY_WINDOW_SECONDS = 30 * 60
CORPSE_MEMORY_EXTENSION_SECONDS = 15 * 60
SIMULATED_ACTION_SECONDS = 6

character_module = None
create_object = None

CmdAssess = None
CmdPrepare = None
CmdRestore = None
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
        self.events.append((str(channel or "SYSTEM"), str(payload or "")))

    def mark(self):
        return len(self.events)

    def lines_since(self, mark):
        return [f"[{channel}]: {text}" for channel, text in self.events[mark:]]

    def all_lines(self):
        return [f"[{channel}]: {text}" for channel, text in self.events]


def _optimal_play_selected(profile_key, decay_stage):
    return (profile_key == "D" and int(decay_stage or 0) in {2, 3}) or (profile_key == "C" and int(decay_stage or 0) == 3) or (
        profile_key == "B" and int(decay_stage or 0) == 3
    )


def _new_effort_tracker():
    return {
        "total_actions": 0,
        "empath_actions": 0,
        "cleric_actions": 0,
        "prep_completion_action": None,
        "res_attempt_action": None,
        "stabilize_action_total": None,
    }


def _record_action(command_trace, effort, actor_role, command_text):
    command_trace.append(command_text)
    effort["total_actions"] += 1
    if actor_role == "empath":
        effort["empath_actions"] += 1
    elif actor_role == "cleric":
        effort["cleric_actions"] += 1


def _mark_prep_complete(effort):
    if effort["prep_completion_action"] is None:
        effort["prep_completion_action"] = effort["total_actions"]
    if effort["stabilize_action_total"] is None:
        effort["stabilize_action_total"] = effort["total_actions"]


def _format_effort_time(action_count):
    if action_count is None:
        return "not reached"
    return f"{int(action_count)} actions ({int(action_count) * SIMULATED_ACTION_SECONDS}s simulated)"


def _get_build_version():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def _patch_messages(recorder, room, patient, empath, cleric, empath_two):
    originals = {
        "room_msg_contents": room.msg_contents,
        "patient_msg": patient.msg,
        "empath_msg": empath.msg,
        "cleric_msg": cleric.msg,
        "empath_two_msg": empath_two.msg,
    }

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
    cleric.msg = build_msg("CLERIC", cleric.msg)
    empath_two.msg = build_msg("EMPATH-2", empath_two.msg)
    return originals


def _restore_messages(room, patient, empath, cleric, empath_two, originals):
    room.msg_contents = originals["room_msg_contents"]
    patient.msg = originals["patient_msg"]
    empath.msg = originals["empath_msg"]
    cleric.msg = originals["cleric_msg"]
    empath_two.msg = originals["empath_two_msg"]


def _emit_lines(actor, payload):
    if isinstance(payload, str):
        actor.msg(payload)
        return
    for line in list(payload or []):
        actor.msg(line)


def _run_direct(actor, callback, scheduled=None, revive_mode=False):
    ok, payload = callback()
    _emit_lines(actor, payload)
    if scheduled is None or not scheduled:
        return ok, payload
    if revive_mode:
        event = scheduled.pop(0)
        original_delay = character_module.delay

        def _suppress_nested_delay(_seconds, _callback, *event_args, **event_kwargs):
            return None

        character_module.delay = _suppress_nested_delay
        try:
            event["callback"](*event["args"], **event["kwargs"])
        finally:
            character_module.delay = original_delay
        scheduled.clear()
        return ok, payload
    _run_fake_delay_queue(scheduled)
    return ok, payload


def _run_command(command_cls, caller, args, cmdstring):
    command = command_cls()
    command.caller = caller
    command.args = str(args or "")
    command.cmdstring = str(cmdstring or "")
    command.func()


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
    character.db.death_type = None
    character.db.death_timestamp = 0.0
    character.db.death_location = None
    character.db.wounds = {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0, "trauma": 0}
    character.db.injuries = character_module._copy_default_injuries()
    character.db.hp = int(character.db.max_hp or 100)
    character.db.balance = int(character.db.max_balance or 100)
    character.db.fatigue = 0
    character.db.empath_shock = 0
    character.db.empath_strain = 0
    character.db.empath_overload_until = 0.0
    character.db.res_stabilization = None
    character.db.just_revived = False
    character.ndb.next_empath_shock_decay_at = 0.0
    character.ndb.next_empath_strain_decay_at = 0.0
    character.ndb.next_empath_feedback_at = 0.0
    character.ndb.empath_recent_healing_until = 0.0
    character.ndb.pending_cleric_ritual_action = None
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
    if hasattr(character, "clear_death_corpse_link"):
        character.clear_death_corpse_link()
    character.sync_client_state()


def _prepare_patient(patient, favor):
    _reset_common_state(patient)
    patient.set_favor(int(favor or 0))


def _prepare_empath(empath):
    _reset_common_state(empath)
    empath.set_profession("empath")
    empath.db.wounds = empath.normalize_empath_wounds(
        {"vitality": 0, "bleeding": 0, "fatigue": 0, "poison": 0, "disease": 0, "trauma": 0}
    )
    empath.sync_client_state()


def _prepare_cleric(cleric):
    _reset_common_state(cleric)
    cleric.set_profession("cleric")
    if hasattr(cleric, "set_devotion"):
        cleric.set_devotion(500)
    else:
        cleric.db.devotion_current = 500
        cleric.db.devotion = 500
        cleric.sync_client_state()


def _set_body_part(patient, part_name, external=0, internal=0, bleed=0, bruise=0):
    body_part = patient.get_body_part(part_name)
    if not body_part:
        return
    body_part["external"] = int(external or 0)
    body_part["internal"] = int(internal or 0)
    body_part["bleed"] = int(bleed or 0)
    body_part["bruise"] = int(bruise or 0)
    body_part["tended"] = False
    body_part["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}


def _sync_patient_wounds(patient, vitality=0, bleeding=0, fatigue=0, trauma=0, poison=0, disease=0):
    patient.db.wounds = patient.normalize_empath_wounds(
        {
            "vitality": int(vitality or 0),
            "bleeding": int(bleeding or 0),
            "fatigue": int(fatigue or 0),
            "trauma": int(trauma or 0),
            "poison": int(poison or 0),
            "disease": int(disease or 0),
        }
    )
    patient.sync_client_state()


def _apply_profile(patient, profile_key):
    if profile_key == "A":
        _sync_patient_wounds(patient, vitality=0, bleeding=0, fatigue=0, trauma=0)
        return
    if profile_key == "B":
        _set_body_part(patient, "left_arm", bruise=8)
        _set_body_part(patient, "right_leg", bruise=6)
        _sync_patient_wounds(patient, vitality=4, bleeding=0, fatigue=0, trauma=2)
        return
    if profile_key == "C":
        _set_body_part(patient, "left_arm", external=8, bleed=2)
        _set_body_part(patient, "right_arm", external=7, bleed=1)
        _set_body_part(patient, "left_leg", external=10, bleed=2)
        _sync_patient_wounds(patient, vitality=18, bleeding=12, fatigue=0, trauma=4)
        return
    _set_body_part(patient, "head", external=8, internal=6, bleed=2)
    _set_body_part(patient, "chest", external=42, internal=30, bleed=12)
    _set_body_part(patient, "abdomen", external=34, internal=24, bleed=10)
    _sync_patient_wounds(patient, vitality=75, bleeding=45, fatigue=0, trauma=20)


def _summarize_body_parts(patient):
    parts = []
    for part_name in ("head", "neck", "chest", "abdomen", "back", "left_arm", "right_arm", "left_leg", "right_leg"):
        body_part = patient.get_body_part(part_name)
        if not body_part:
            continue
        external = int(body_part.get("external", 0) or 0)
        internal = int(body_part.get("internal", 0) or 0)
        bleed = int(body_part.get("bleed", 0) or 0)
        bruise = int(body_part.get("bruise", 0) or 0)
        if external <= 0 and internal <= 0 and bleed <= 0 and bruise <= 0:
            continue
        parts.append(
            f"{patient.format_body_part_name(part_name)}: external {external}, internal {internal}, bleed {bleed}, bruise {bruise}"
        )
    return "; ".join(parts) if parts else "clean body"


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


def _get_death_pressure_plan(profile_key):
    if profile_key == "A":
        return [("chest", 14, 10, 2, 0), ("abdomen", 14, 10, 2, 0), ("chest", 12, 8, 2, 0), ("abdomen", 12, 8, 2, 0)]
    if profile_key == "B":
        return [("chest", 12, 8, 2, 0), ("abdomen", 12, 8, 2, 0), ("chest", 10, 6, 2, 0)]
    if profile_key == "C":
        return [("chest", 8, 4, 1, 0), ("abdomen", 8, 4, 1, 0)]
    return []


def _apply_wound_pressure(patient, recorder, part_name, external_gain, vitality_gain, bleed_gain, internal_gain):
    body_part = patient.get_body_part(part_name)
    if not body_part:
        return
    body_part["external"] = min(100, int(body_part.get("external", 0) or 0) + int(external_gain or 0))
    body_part["internal"] = min(100, int(body_part.get("internal", 0) or 0) + int(internal_gain or 0))
    body_part["bleed"] = min(100, int(body_part.get("bleed", 0) or 0) + int(bleed_gain or 0))
    patient.set_empath_wound("vitality", patient.get_empath_wound("vitality") + int(vitality_gain or 0))
    patient.set_empath_wound("bleeding", patient.get_empath_wound("bleeding") + int(bleed_gain or 0))
    recorder.record(
        "SYSTEM",
        f"Wound pressure escalates in the {patient.format_body_part_name(part_name)}: +{int(external_gain or 0)} external, +{int(internal_gain or 0)} internal, +{int(bleed_gain or 0)} bleed.",
    )


def _drive_to_wound_death(patient, recorder, profile_key):
    death_lines = []
    pressure_plan = list(_get_death_pressure_plan(profile_key))
    death_tick = None
    pulse_ticks = {2, 4, 6, 8, 10, 12, 14, 16, 18}
    for tick in range(1, 21):
        if not patient.is_dead() and tick in pulse_ticks:
            if pressure_plan:
                part_name, external_gain, vitality_gain, bleed_gain, internal_gain = pressure_plan.pop(0)
            elif profile_key in {"A", "B"}:
                part_name, external_gain, vitality_gain, bleed_gain, internal_gain = ("chest", 12, 10, 2, 1)
            elif profile_key == "C":
                part_name, external_gain, vitality_gain, bleed_gain, internal_gain = ("abdomen", 8, 6, 1, 1)
            else:
                part_name, external_gain, vitality_gain, bleed_gain, internal_gain = ("chest", 6, 4, 1, 1)
            _apply_wound_pressure(patient, recorder, part_name, external_gain, vitality_gain, bleed_gain, internal_gain)
        mark = recorder.mark()
        patient.process_bleed()
        patient.process_medical_decay(now=1000.0 + (tick * 12.0))
        lines = recorder.lines_since(mark)
        death_lines.append(
            f"Death Tick {tick}: alive={'NO' if patient.is_dead() else 'YES'}"
            f" | hp {int(getattr(patient.db, 'hp', 0) or 0)}"
            f" | bleed {int(patient.get_total_bleed() if hasattr(patient, 'get_total_bleed') else 0)}"
            f" | medical {patient.get_medical_severity_state() if hasattr(patient, 'get_medical_severity_state') else 'unknown'}"
            + (f" | Messages: {' || '.join(lines)}" if lines else "")
        )
        if patient.is_dead():
            death_tick = tick
            break
    return death_tick, death_lines


def _advance_corpse_to_decay_stage(corpse, target_stage, recorder):
    now = time.time()
    ratio = float(DECAY_STAGE_RATIOS[int(target_stage or 0)])
    death_time = now - (CORPSE_DECAY_WINDOW_SECONDS * ratio)
    corpse.db.time_of_death = death_time
    corpse.db.death_timestamp = death_time
    corpse.db.decay_end_time = death_time + CORPSE_DECAY_WINDOW_SECONDS
    corpse.db.decay_time = corpse.db.decay_end_time
    corpse.db.memory_time = now + CORPSE_MEMORY_EXTENSION_SECONDS
    corpse.db.memory_faded = False
    if hasattr(corpse, "refresh_decay_stage"):
        corpse.refresh_decay_stage(now=now)
    actual_stage = int(corpse.get_decay_stage() if hasattr(corpse, "get_decay_stage") else target_stage)
    recorder.record(
        "SYSTEM",
        f"Corpse advanced to decay stage {actual_stage} ({DECAY_STAGES.get(actual_stage, 'Unknown')}). Time since death: {int(round(now - death_time))}s.",
    )
    return {
        "target_stage": int(target_stage or 0),
        "actual_stage": actual_stage,
        "time_since_death": int(round(now - death_time)),
    }


def _corpse_metrics(corpse, cleric):
    bleed = cleric.get_corpse_bleed_total(corpse) if hasattr(cleric, "get_corpse_bleed_total") else 0
    internal = cleric.get_corpse_internal_total(corpse) if hasattr(cleric, "get_corpse_internal_total") else 0
    survivable = cleric.is_corpse_revive_survivable(corpse) if hasattr(cleric, "is_corpse_revive_survivable") else False
    band = cleric.get_corpse_revive_survivability_band(corpse) if hasattr(cleric, "get_corpse_revive_survivability_band") else ("stable" if survivable else "unsafe")
    decay = corpse.get_decay_stage_penalties() if hasattr(corpse, "get_decay_stage_penalties") else {}
    wounds = corpse.get_empath_wounds() if hasattr(corpse, "get_empath_wounds") else {}
    return {
        "bleed": int(bleed or 0),
        "internal": int(internal or 0),
        "survivable": bool(survivable),
        "band": str(band or "stable"),
        "decay_stage": int(decay.get("stage", 0) or 0),
        "decay_label": str(decay.get("label", DECAY_STAGES.get(int(decay.get('stage', 0) or 0), 'Unknown')) or "Unknown"),
        "vitality": int(wounds.get("vitality", 0) or 0),
        "bleeding": int(wounds.get("bleeding", 0) or 0),
    }


def _impact_label(before_metrics, after_metrics):
    impact_delta = max(0, (before_metrics["bleed"] + before_metrics["internal"]) - (after_metrics["bleed"] + after_metrics["internal"]))
    if impact_delta >= 20:
        return "HIGH"
    if impact_delta >= 8:
        return "MED"
    return "LOW"


def _prep_with_empath(empath, cleric, corpse, recorder, command_trace, effort, max_cycles=3):
    performed = 0
    for _ in range(max_cycles):
        metrics = _corpse_metrics(corpse, cleric)
        if metrics["survivable"]:
            _mark_prep_complete(effort)
            break
        if metrics["bleed"] > 0:
            _record_action(command_trace, effort, "empath", "> take bleeding all")
            ok, message = empath.take_empath_wound("bleeding", amount_spec="all")
            empath.msg(message)
            if ok:
                performed += 1
            elif "another empath may still help" in str(message).lower():
                return performed, "PrepStop: best_possible_state_reached"
        _record_action(command_trace, effort, "empath", "> assess corpse")
        ok, lines = empath.assess_empath_corpse(corpse)
        _emit_lines(empath, lines if ok else lines)
        metrics = _corpse_metrics(corpse, cleric)
        if metrics["survivable"]:
            _mark_prep_complete(effort)
            return performed, "corpse appears survivable"
        if metrics["internal"] > 0 or metrics["vitality"] > 0:
            _record_action(command_trace, effort, "empath", "> take chest")
            ok, message = empath.take_empath_wound("vitality", selector="chest")
            empath.msg(message)
            if ok:
                performed += 1
            elif "another empath may still help" in str(message).lower():
                return performed, "PrepStop: best_possible_state_reached"
        _record_action(command_trace, effort, "empath", "> assess corpse")
        ok, lines = empath.assess_empath_corpse(corpse)
        _emit_lines(empath, lines if ok else lines)
        if hasattr(corpse, "get_empath_prep_remaining") and corpse.get_empath_prep_remaining(empath) <= 0:
            _mark_prep_complete(effort)
            return performed, "PrepStop: best_possible_state_reached"
    metrics = _corpse_metrics(corpse, cleric)
    if metrics["survivable"]:
        _mark_prep_complete(effort)
        return performed, "corpse appears survivable"
    _mark_prep_complete(effort)
    return performed, "best possible state reached"


def _run_empath_prep(empath, empath_two, cleric, corpse, recorder, command_trace, effort, use_multi_empath=False, prep_cycles=3):
    metrics_before = _corpse_metrics(corpse, cleric)
    _record_action(command_trace, effort, "empath", "> assess corpse")
    ok, lines = empath.assess_empath_corpse(corpse)
    _emit_lines(empath, lines if ok else lines)
    _record_action(command_trace, effort, "empath", "> stabilize corpse")
    ok, message = empath.stabilize_corpse(corpse)
    empath.msg(message)
    if ok and getattr(empath, "location", None):
        empath.location.msg_contents(f"{empath.key} carefully tends to {corpse.key}, slowing its decay.", exclude=[empath])
    _record_action(command_trace, effort, "empath", "> touch corpse")
    ok, message = empath.touch_empath_target(corpse)
    _emit_lines(empath, message)
    _record_action(command_trace, effort, "empath", "> assess corpse")
    ok, lines = empath.assess_empath_corpse(corpse)
    _emit_lines(empath, lines if ok else lines)

    primary_actions, stop_reason = _prep_with_empath(empath, cleric, corpse, recorder, command_trace, effort, max_cycles=prep_cycles)
    primary_after = _corpse_metrics(corpse, cleric)
    prep_cap_reached = bool(hasattr(corpse, "get_empath_prep_remaining") and corpse.get_empath_prep_remaining(empath) <= 0)
    multi_used = False
    multi_improved = False
    multi_measurable = False
    secondary_actions = 0

    if use_multi_empath and not primary_after["survivable"]:
        _record_action(command_trace, effort, "empath", "> touch corpse")
        ok, message = empath_two.touch_empath_target(corpse)
        _emit_lines(empath_two, message)
        _record_action(command_trace, effort, "empath", "> assess corpse")
        ok, lines = empath_two.assess_empath_corpse(corpse)
        _emit_lines(empath_two, lines if ok else lines)
        secondary_actions, stop_reason = _prep_with_empath(empath_two, cleric, corpse, recorder, command_trace, effort, max_cycles=prep_cycles)
        after_secondary = _corpse_metrics(corpse, cleric)
        multi_used = secondary_actions > 0
        primary_load = primary_after["bleed"] + primary_after["internal"]
        secondary_load = after_secondary["bleed"] + after_secondary["internal"]
        multi_measurable = secondary_load != primary_load or after_secondary["band"] != primary_after["band"]
        multi_improved = secondary_load < primary_load or (primary_after["band"] != "stable" and after_secondary["band"] == "stable")

    metrics_after = _corpse_metrics(corpse, cleric)
    if metrics_after["survivable"]:
        stop_reason = "corpse appears survivable"
    _mark_prep_complete(effort)
    recorder.record("SYSTEM", f"Empath prep stop condition: {stop_reason}.")
    if prep_cap_reached:
        recorder.record("SYSTEM", "PrepStop: best_possible_state_reached")
    if use_multi_empath:
        recorder.record(
            "SYSTEM",
            f"Multi-empath effect: improved outcome={'YES' if multi_improved else 'NO'}; measurable difference={'YES' if multi_measurable else 'NO'}.",
        )
    return {
        "before": metrics_before,
        "after_primary": primary_after,
        "after": metrics_after,
        "impact": _impact_label(metrics_before, metrics_after),
        "prep_actions": int(primary_actions + secondary_actions),
        "prep_cap_reached": prep_cap_reached,
        "stop_reason": stop_reason,
        "multi_empath_needed": bool(use_multi_empath and not primary_after["survivable"] and multi_used),
        "multi_empath_used": bool(use_multi_empath and multi_used),
        "multi_empath_improved": bool(multi_improved),
        "multi_empath_measurable": bool(multi_measurable),
    }


def _run_cleric_ritual(cleric, corpse, recorder, command_trace, effort, scheduled):
    _record_action(command_trace, effort, "cleric", "> assess corpse")
    ok, lines = cleric.assess_cleric_corpse(corpse)
    _emit_lines(cleric, lines if ok else lines)
    _record_action(command_trace, effort, "cleric", "> prepare corpse")
    _run_direct(cleric, lambda: cleric.prepare_corpse(corpse), scheduled=scheduled)
    _record_action(command_trace, effort, "cleric", "> stabilize corpse")
    _run_direct(cleric, lambda: cleric.start_cleric_corpse_ritual(corpse, "stabilize"), scheduled=scheduled)
    _record_action(command_trace, effort, "cleric", "> restore corpse")
    _run_direct(cleric, lambda: cleric.start_cleric_corpse_ritual(corpse, "restore"), scheduled=scheduled)
    _record_action(command_trace, effort, "cleric", "> bind corpse")
    _run_direct(cleric, lambda: cleric.start_cleric_corpse_ritual(corpse, "bind"), scheduled=scheduled)
    assess_ok, assess_lines = cleric.assess_cleric_corpse(corpse)
    band_shown = "UNKNOWN"
    for line in list(assess_lines or []):
        if str(line).startswith("Survivability:"):
            band_shown = str(line).split(":", 1)[1].strip().upper()
            break
    mark = recorder.mark()
    _record_action(command_trace, effort, "cleric", "> revive corpse")
    effort["res_attempt_action"] = effort["total_actions"]
    ok, payload = _run_direct(cleric, lambda: cleric.start_cleric_revive(corpse), scheduled=scheduled, revive_mode=True)
    warning_lines = recorder.lines_since(mark)
    warning_seen = any("unstable" in line.lower() or "likely to fail" in line.lower() for line in warning_lines)
    return {
        "warning_seen": warning_seen,
        "res_attempted": True,
        "band_shown": band_shown,
        "start_ok": bool(ok),
        "payload": payload,
    }


def _observe_patient_tick(tick, patient, empath, recorder, phase_label, now_base):
    mark = recorder.mark()
    death_guard_triggered = False
    if not patient.is_dead():
        patient.process_bleed()
        patient.process_medical_decay(now=now_base + (tick * 12.0))
    if hasattr(empath, "process_bleed"):
        empath.process_bleed()
        empath.process_medical_decay(now=now_base + (tick * 12.0) + 1.0)
    if hasattr(empath, "process_empath_tick"):
        empath.process_empath_tick()
    lines = recorder.lines_since(mark)
    if any("one heartbeat" in line.lower() for line in lines):
        death_guard_triggered = True
    stabilization = patient.get_resurrection_stabilization_state() if hasattr(patient, "get_resurrection_stabilization_state") else None
    stabilization_text = "INACTIVE"
    if isinstance(stabilization, dict):
        stabilization_text = f"ACTIVE({str(stabilization.get('band', 'stable')).upper()}:{int(stabilization.get('ticks_remaining', 0) or 0)})"
    line = (
        f"Tick {tick}: phase={phase_label}"
        f" | patient={'dead' if patient.is_dead() else 'alive'}"
        f" | patient hp {int(getattr(patient.db, 'hp', 0) or 0)}"
        f" | patient bleed {int(patient.get_total_bleed() if hasattr(patient, 'get_total_bleed') else 0)}"
        f" | patient medical {patient.get_medical_severity_state() if hasattr(patient, 'get_medical_severity_state') else 'unknown'}"
        f" | stabilization {stabilization_text}"
        f" | death_guard {'TRIGGERED' if death_guard_triggered else 'NO'}"
        + (f" | Messages: {' || '.join(lines)}" if lines else "")
    )
    return line, {"stabilization_active": isinstance(stabilization, dict), "death_guard_triggered": death_guard_triggered}


def _post_res_heal(empath, patient, recorder, command_trace, effort):
    recorder.record("SYSTEM", "Post-res heal attempt begins.")
    if patient.is_dead():
        recorder.record("SYSTEM", "Post-res heal could not proceed because the patient is already dead.")
        return {"attempted": True, "executed": False, "completed": False, "reason": "patient already dead"}
    _run_command(CmdTouch, empath, patient.key, f"touch {patient.key}")
    _record_action(command_trace, effort, "empath", f"> touch {patient.key}")
    _run_command(CmdAssess, empath, "", "assess")
    _record_action(command_trace, effort, "empath", "> assess")
    _run_command(CmdStabilize, empath, patient.key, f"stabilize {patient.key}")
    _record_action(command_trace, effort, "empath", f"> stabilize {patient.key}")
    _run_command(CmdTake, empath, "bleeding all", "take bleeding all")
    _record_action(command_trace, effort, "empath", "> take bleeding all")
    _run_command(CmdTake, empath, "vitality 20", "take vitality 20")
    _record_action(command_trace, effort, "empath", "> take vitality 20")
    _run_command(CmdAssess, empath, "", "assess")
    _record_action(command_trace, effort, "empath", "> assess")
    recorder.record("SYSTEM", "Post-res heal attempt completed.")
    return {"attempted": True, "executed": True, "completed": True, "reason": "completed"}


def _estimate_failure_margin(result, corpse_prep):
    if result["res_success"] and not result["redied"]:
        return ""
    if result["failure_cause"] == "Favor failure" and int(result["favor"] or 0) == 0:
        return "Near success"
    remaining_load = int(corpse_prep["after"]["bleed"] + corpse_prep["after"]["internal"])
    if result["redied"] or (result["failure_cause"] == "Post-res instability"):
        return "Near success"
    if remaining_load <= 8 or corpse_prep["after"]["band"].upper() == "CRITICAL":
        return "Near success"
    if remaining_load <= 24 or corpse_prep["after"]["band"].upper() == "UNSAFE":
        return "Moderate gap"
    return "Impossible under current rules"


def _build_optimal_play_summary(result):
    if not result.get("optimal_play_tested"):
        return ["Optimal Play Outcome: NOT RUN"]
    return [
        f"Optimal Play Outcome: {'SUCCESS' if result['optimal_play_success'] else 'FAIL'}",
        f"Optimal Play Detail: {result['optimal_play_note']}",
    ]


def _format_initial_state(room, patient, empath, cleric, favor, profile_key, decay_state, empath_two=None):
    lines = [
        "INITIAL STATE",
        "[SETUP]",
        f"Wounds: {_summarize_body_parts(patient)}",
        f"Favor: {int(favor or 0)}",
        f"Decay Stage: {int(decay_state['actual_stage'])} ({DECAY_STAGES[int(decay_state['actual_stage'])]})",
        f"Time Since Death: {int(decay_state['time_since_death'])}s",
        f"Empath State: {_summarize_condition(empath)}",
        f"Cleric State: {_summarize_condition(cleric)}",
        f"Room: {room.key}",
        f"Patient State: {_summarize_condition(patient)}",
        f"Wound Profile Detail: {profile_key} ({WOUND_NAMES[profile_key]})",
    ]
    if empath_two is not None:
        lines.append(f"Second Empath State: {_summarize_condition(empath_two)}")
    return lines


def _determine_failure_cause(result):
    if not result["res_success"]:
        if result["favor"] <= 0:
            return "Favor failure"
        if result["decay_stage"] >= 2 and result["heal_start_band"] == "UNSAFE":
            return "Decay overload"
        if result["empath_prep_impact"] in {"LOW", "MED"} and result["heal_start_band"] != "STABLE":
            return "Insufficient prep"
        return "Lethal wounds"
    if result["redied"]:
        return "Post-res instability"
    return "Unknown"


def _failure_mode_lines(result):
    selected = _determine_failure_cause(result)
    labels = ["Favor failure", "Lethal wounds", "Decay overload", "Insufficient prep", "Post-res instability", "Unknown"]
    lines = ["Failure Cause:"]
    for label in labels:
        marker = "[X]" if label == selected else "[ ]"
        lines.append(f"{marker} {label}")
    return lines


def _analyze_result(run_number, favor, profile_key, decay_stage, patient, corpse_prep, cleric_result, tick_states, post_heal, res_success, effort, optimal_play=None):
    survived_10 = False
    survived_20 = False
    redied = False
    time_to_death = "N/A"
    if res_success:
        survived_10 = all(not entry["dead"] for entry in tick_states[:10])
        survived_20 = all(not entry["dead"] for entry in tick_states[:20])
        for entry in tick_states:
            if entry["dead"]:
                redied = True
                time_to_death = str(entry["tick"])
                break
        if not redied:
            time_to_death = "No re-death in 20 ticks"
    final_condition = _summarize_condition(patient)
    stabilization_observed = any(entry["stabilization_active"] for entry in tick_states)
    death_guard_triggered = any(entry["death_guard_triggered"] for entry in tick_states)
    clarity = "clear" if cleric_result["band_shown"] != "UNKNOWN" else "unclear"
    tension = "low"
    if profile_key in {"C", "D"} or decay_stage >= 2 or redied:
        tension = "high"
    elif favor in {0, 1} or corpse_prep["impact"] == "MED":
        tension = "medium"
    fairness = "fair"
    if redied and not stabilization_observed:
        fairness = "unfair"
    notes = [f"Decay stage {decay_stage} produced {corpse_prep['after']['band'].upper()} corpse conditions before the rite."]
    if corpse_prep["multi_empath_used"]:
        notes.append(
            f"Multi-empath effect improved outcome: {'YES' if corpse_prep['multi_empath_improved'] else 'NO'}; measurable difference: {'YES' if corpse_prep['multi_empath_measurable'] else 'NO'}."
        )
    if stabilization_observed:
        notes.append("Stabilization window was visible during post-res observation.")
    if post_heal.get("completed", False):
        notes.append("Post-res heal completed.")
    elif post_heal.get("attempted", False):
        notes.append(f"Post-res heal attempt stopped because {post_heal.get('reason', 'unknown')}.")
    result = {
        "run_number": run_number,
        "favor": int(favor or 0),
        "profile": profile_key,
        "decay_stage": int(decay_stage or 0),
        "res_attempted": bool(cleric_result["res_attempted"]),
        "res_success": bool(res_success),
        "survived_10": bool(survived_10),
        "survived_20": bool(survived_20),
        "redied": bool(redied),
        "time_to_death": time_to_death,
        "stabilization_observed": bool(stabilization_observed),
        "empath_prep_impact": corpse_prep["impact"],
        "post_res_heal_completed": bool(post_heal.get("completed", False)),
        "final_condition": final_condition,
        "clarity": clarity,
        "tension": tension,
        "fairness": fairness,
        "notes": " ".join(notes),
        "decay_applied": corpse_prep["before"]["decay_stage"] == int(decay_stage or 0),
        "prep_cap_reached": bool(corpse_prep["prep_cap_reached"]),
        "multi_empath_needed": bool(corpse_prep["multi_empath_needed"]),
        "stabilization_window_active": bool(stabilization_observed),
        "death_guard_triggered": bool(death_guard_triggered),
        "survivability_band_shown": str(cleric_result["band_shown"] or corpse_prep["after"]["band"]).upper(),
        "heal_start_band": str(corpse_prep["before"]["band"] or "stable").upper(),
        "res_start_band": str(corpse_prep["after"]["band"] or "stable").upper(),
        "heal_start_decay": f"{int(corpse_prep['before']['decay_stage'])} ({corpse_prep['before']['decay_label']})",
        "res_start_decay": f"{int(corpse_prep['after']['decay_stage'])} ({corpse_prep['after']['decay_label']})",
        "cleric_warning_shown": bool(cleric_result["warning_seen"]),
        "multi_empath_improved": bool(corpse_prep["multi_empath_improved"]),
        "multi_empath_measurable": bool(corpse_prep["multi_empath_measurable"]),
        "empath_actions_taken": int(effort["empath_actions"]),
        "cleric_actions_taken": int(effort["cleric_actions"]),
        "time_to_prep_completion": _format_effort_time(effort["prep_completion_action"]),
        "time_to_res_attempt": _format_effort_time(effort["res_attempt_action"]),
        "total_actions_to_stabilize": int(effort["stabilize_action_total"] or effort["total_actions"]),
    }
    result["failure_cause"] = _determine_failure_cause(result) if (not result["res_success"] or result["redied"]) else ""
    result["failure_margin_estimate"] = _estimate_failure_margin(result, corpse_prep)
    result["optimal_play_tested"] = bool(optimal_play)
    result["optimal_play_success"] = bool(optimal_play.get("success", False)) if optimal_play else False
    result["optimal_play_note"] = str(optimal_play.get("note", "not run")) if optimal_play else "not run"
    return result


def _build_result_summary(result):
    lines = ["RESULT SUMMARY"]
    lines.append(f"Res Attempted: {'YES' if result['res_attempted'] else 'NO'}")
    lines.append(f"Res Success: {'YES' if result['res_success'] else 'NO'}")
    lines.append(f"Survived 10 ticks: {'YES' if result['survived_10'] else 'NO'}")
    lines.append(f"Survived 20 ticks: {'YES' if result['survived_20'] else 'NO'}")
    lines.append(f"Re-died: {'YES' if result['redied'] else 'NO'}")
    lines.append(f"Time to Death: {result['time_to_death']}")
    lines.append(f"Stabilization Window Observed: {'YES' if result['stabilization_observed'] else 'NO'}")
    lines.append(f"Empath Prep Impact: {result['empath_prep_impact']}")
    lines.append(f"Post-Res Heal Completed: {'YES' if result['post_res_heal_completed'] else 'NO'}")
    lines.append(f"Final Condition: {result['final_condition']}")
    lines.append("")
    lines.append("EFFORT COST")
    lines.append(f"Empath Actions Taken: {result['empath_actions_taken']}")
    lines.append(f"Cleric Actions Taken: {result['cleric_actions_taken']}")
    lines.append(f"Time to Prep Completion: {result['time_to_prep_completion']}")
    lines.append(f"Time to Res Attempt: {result['time_to_res_attempt']}")
    lines.append(f"Total Actions to Stabilize: {result['total_actions_to_stabilize']}")
    lines.append("")
    lines.append("PLAYER FEEL (MANDATORY)")
    lines.append(f"Clarity: {result['clarity']}")
    lines.append(f"Tension: {result['tension']}")
    lines.append(f"Fairness: {result['fairness']}")
    lines.append(f"Notes: {result['notes']}")
    lines.append("")
    lines.append("[CHECK]")
    lines.append(f"Decay applied: {'YES' if result['decay_applied'] else 'NO'}")
    lines.append(f"Prep cap reached: {'YES' if result['prep_cap_reached'] else 'NO'}")
    lines.append(f"Multi-empath needed: {'YES' if result['multi_empath_needed'] else 'NO'}")
    lines.append(f"Stabilization window active: {'YES' if result['stabilization_window_active'] else 'NO'}")
    lines.append(f"Death guard triggered: {'YES' if result['death_guard_triggered'] else 'NO'}")
    lines.append(f"Survivability band shown: {result['survivability_band_shown']}")
    lines.append(f"Heal-Start Corpse Band: {result['heal_start_band']}")
    lines.append(f"Heal-Start Decay Stage: {result['heal_start_decay']}")
    lines.append(f"Res-Start Corpse Band: {result['res_start_band']}")
    lines.append(f"Res-Start Decay Stage: {result['res_start_decay']}")
    if not result["res_success"] or result["redied"]:
        lines.append("")
        lines.extend(_failure_mode_lines(result))
        lines.append("Failure Margin Estimate:")
        labels = ["Near success", "Moderate gap", "Impossible under current rules"]
        for label in labels:
            marker = "[X]" if result["failure_margin_estimate"] == label else "[ ]"
            lines.append(f"{marker} {label}")
        lines.extend(_build_optimal_play_summary(result))
    return lines


def _build_run_lines(run_number, favor, profile_key, decay_stage, initial_state_lines, command_trace, recorder, tick_lines, result):
    lines = [
        f"=== RUN {run_number:02d} ===",
        f"Favor: {int(favor or 0)}",
        f"Wound Profile: {profile_key} - {WOUND_NAMES[profile_key]}",
        f"Decay Stage: {int(decay_stage or 0)} - {DECAY_STAGES[int(decay_stage or 0)]}",
        "",
    ]
    lines.extend(initial_state_lines)
    lines.append("")
    lines.append("COMMAND INPUT TRACE (EXACT)")
    lines.extend(command_trace if command_trace else ["> no commands executed"])
    lines.append("")
    lines.append("FULL OUTPUT LOG (ALL CHANNELS)")
    lines.extend(recorder.all_lines())
    lines.append("")
    lines.append("TICK OBSERVATION (REQUIRED)")
    lines.extend(tick_lines)
    lines.append("")
    lines.extend(_build_result_summary(result))
    lines.append("")
    return lines


def _run_optimal_play_pass(favor, profile_key, decay_stage, base_result):
    if not _optimal_play_selected(profile_key, decay_stage):
        return None
    if base_result["res_success"] and not base_result["redied"]:
        return None
    _, optimal_result = _run_single(
        900 + int(base_result["run_number"]),
        favor,
        profile_key,
        decay_stage,
        optimal_mode=True,
        allow_optimal_replay=False,
    )
    return {
        "success": bool(optimal_result["res_success"] and not optimal_result["redied"]),
        "note": (
            "perfect empath timing, extended prep, and immediate post-res care converted the case"
            if optimal_result["res_success"] and not optimal_result["redied"]
            else f"still failed with {optimal_result['failure_cause'] or 'unknown cause'}"
        ),
    }


def _run_single(run_number, favor, profile_key, decay_stage, optimal_mode=False, allow_optimal_replay=True):
    room = None
    patient = None
    empath = None
    empath_two = None
    cleric = None
    recorder = EventRecorder()
    scheduled = None
    originals = None
    original_delay = None
    try:
        room = create_object("typeclasses.rooms.Room", key=f"SIM_FULL_RES_ROOM_{run_number:02d}", nohome=True)
        room.db.is_shrine = True
        patient = create_object("typeclasses.characters.Character", key=f"SIM_FULL_PATIENT_{run_number:02d}", location=room, home=room)
        empath = create_object("typeclasses.characters.Character", key=f"SIM_FULL_EMPATH_{run_number:02d}", location=room, home=room)
        empath_two = create_object("typeclasses.characters.Character", key=f"SIM_FULL_EMPATH2_{run_number:02d}", location=room, home=room)
        cleric = create_object("typeclasses.characters.Character", key=f"SIM_FULL_CLERIC_{run_number:02d}", location=room, home=room)

        _prepare_patient(patient, favor)
        _prepare_empath(empath)
        _prepare_empath(empath_two)
        _prepare_cleric(cleric)
        _apply_profile(patient, profile_key)

        recorder.record("SYSTEM", "Clean reset complete.")
        recorder.record("SYSTEM", f"Favor set to {int(favor or 0)}.")
        recorder.record("SYSTEM", f"Applied wound profile {profile_key} ({WOUND_NAMES[profile_key]}).")

        originals = _patch_messages(recorder, room, patient, empath, cleric, empath_two)
        scheduled, fake_delay = _build_fake_delay_queue()
        original_delay = character_module.delay
        character_module.delay = fake_delay

        command_trace = []
        effort = _new_effort_tracker()
        death_tick, death_lines = _drive_to_wound_death(patient, recorder, profile_key)
        if death_tick is None:
            recorder.record("SYSTEM", "Initial wound profile did not reach death quickly; additional wound pressure was required throughout the death phase.")
        corpse = patient.get_death_corpse()
        if not corpse:
            raise RuntimeError("Natural wound death did not produce a corpse.")
        recorder.record("SYSTEM", f"Corpse created with favor snapshot {int(corpse.get_favor_snapshot() if hasattr(corpse, 'get_favor_snapshot') else 0)}.")
        decay_state = _advance_corpse_to_decay_stage(corpse, decay_stage, recorder)

        initial_state_lines = _format_initial_state(room, patient, empath, cleric, favor, profile_key, decay_state, empath_two=empath_two)
        use_multi_empath = optimal_mode or (profile_key == "D" and int(decay_stage or 0) in {2, 3})
        if use_multi_empath:
            recorder.record("SYSTEM", "Multi-empath comparison enabled for severe late-decay case.")
        corpse_prep = _run_empath_prep(
            empath,
            empath_two,
            cleric,
            corpse,
            recorder,
            command_trace,
            effort,
            use_multi_empath=use_multi_empath,
            prep_cycles=6 if optimal_mode else 3,
        )
        cleric_result = _run_cleric_ritual(cleric, corpse, recorder, command_trace, effort, scheduled)

        res_success = not patient.is_dead()
        tick_lines = list(death_lines)
        tick_states = []
        post_heal = {"attempted": False, "executed": False, "completed": False, "reason": "not reached"}
        for tick in range(1, POST_RES_TICKS + 1):
            if tick == (2 if optimal_mode else PRE_HEAL_TICKS + 1):
                post_heal = _post_res_heal(empath, patient, recorder, command_trace, effort)
            phase_label = "post-res-pre-heal" if tick <= PRE_HEAL_TICKS else "post-res-post-heal"
            if res_success:
                tick_line, tick_info = _observe_patient_tick(tick, patient, empath, recorder, phase_label, 2000.0)
                tick_lines.append(tick_line)
                tick_info["tick"] = tick
                tick_info["dead"] = patient.is_dead()
                tick_states.append(tick_info)
            else:
                tick_lines.append(f"Tick {tick}: phase={phase_label} | patient=dead | no resurrection body available | stabilization INACTIVE | death_guard NO | Messages: [SYSTEM]: resurrection did not succeed")
                tick_states.append({"tick": tick, "dead": True, "stabilization_active": False, "death_guard_triggered": False})

        result = _analyze_result(run_number, favor, profile_key, decay_stage, patient, corpse_prep, cleric_result, tick_states, post_heal, res_success, effort)
        if allow_optimal_replay:
            optimal_play = _run_optimal_play_pass(favor, profile_key, decay_stage, result)
            if optimal_play:
                result = _analyze_result(
                    run_number,
                    favor,
                    profile_key,
                    decay_stage,
                    patient,
                    corpse_prep,
                    cleric_result,
                    tick_states,
                    post_heal,
                    res_success,
                    effort,
                    optimal_play=optimal_play,
                )
        run_lines = _build_run_lines(run_number, favor, profile_key, decay_stage, initial_state_lines, command_trace, recorder, tick_lines, result)
        return run_lines, result
    finally:
        if original_delay is not None:
            character_module.delay = original_delay
        if originals is not None:
            _restore_messages(room, patient, empath, cleric, empath_two, originals)
        for obj in (cleric, empath_two, empath, patient, room):
            if obj is None:
                continue
            try:
                obj.delete()
            except Exception:
                pass


def _survival_outcome_label(result):
    if not result["res_success"]:
        return "FAIL"
    if result["survived_20"]:
        return "SURVIVE"
    return "REDIED"


def _balance_bucket(result):
    score = result["decay_stage"] + {"A": 0, "B": 1, "C": 2, "D": 3}[result["profile"]]
    if result["favor"] >= 5:
        score -= 1
    if score <= 1:
        return "easy"
    if score <= 3:
        return "medium"
    if score <= 5:
        return "hard"
    return "extreme"


def _matrix_lines(results):
    lines = ["1. Survival Matrix", "Favor | Wound | Decay | Outcome", "--------------------------------"]
    for entry in results:
        lines.append(f"{entry['favor']} | {entry['profile']} | {entry['decay_stage']} | {_survival_outcome_label(entry)}")
    return lines


def _key_findings_lines(results):
    lines = ["2. Key Findings"]
    decay_zero_failures = sum(1 for entry in results if entry["decay_stage"] == 0 and (not entry["res_success"] or entry["redied"]))
    decay_late_failures = sum(1 for entry in results if entry["decay_stage"] in {2, 3} and (not entry["res_success"] or entry["redied"]))
    favor_zero_survival = sum(1 for entry in results if entry["favor"] == 0 and entry["survived_20"])
    favor_high_survival = sum(1 for entry in results if entry["favor"] == 15 and entry["survived_20"])
    prep_changes = any(entry["empath_prep_impact"] in {"MED", "HIGH"} and entry["survived_20"] for entry in results)
    multi_required = any(entry["multi_empath_needed"] for entry in results)
    stabilization_helped = any(entry["stabilization_observed"] and entry["survived_20"] for entry in results)

    lines.append(f"Does decay meaningfully impact outcome? {'Yes' if decay_late_failures > decay_zero_failures else 'No'}")
    lines.append(f"Does favor scale outcome or just chance? {'Outcome and chance' if favor_high_survival > favor_zero_survival else 'Mostly chance'}")
    lines.append(f"Does empath prep change survivability? {'Yes' if prep_changes else 'No'}")
    lines.append(f"Does multi-empath become required? {'Yes' if multi_required else 'No'}")
    lines.append(f"Does stabilization window allow recovery? {'Yes' if stabilization_helped else 'No'}")
    return lines


def _verdict_lines(results):
    failures = sum(1 for entry in results if not entry["res_success"])
    redies = sum(1 for entry in results if entry["redied"])
    survives = sum(1 for entry in results if entry["survived_20"])
    too_punishing = failures + redies > survives * 2
    too_forgiving = survives > (len(results) * 0.75)
    balanced = not too_punishing and not too_forgiving
    lines = ["3. System Health Verdict"]
    lines.append(f"{'[X]' if too_punishing else '[ ]'} Too Punishing")
    lines.append(f"{'[X]' if too_forgiving else '[ ]'} Too Forgiving")
    lines.append(f"{'[X]' if balanced else '[ ]'} Balanced")
    return lines


def _critical_failures_lines(results):
    lines = ["4. Critical Failures (if any)"]
    instant_redies = [entry for entry in results if entry["redied"] and str(entry["time_to_death"]).isdigit() and int(entry["time_to_death"]) <= 3]
    unrecoverable = [entry for entry in results if not entry["res_success"] and entry["failure_cause"] in {"Decay overload", "Lethal wounds"}]
    broken_thresholds = [entry for entry in results if entry["prep_cap_reached"] and not entry["multi_empath_needed"] and entry["profile"] == "D"]
    messaging_gaps = [entry for entry in results if entry["survivability_band_shown"] == "UNKNOWN"]
    if not instant_redies and not unrecoverable and not broken_thresholds and not messaging_gaps:
        lines.append("- None observed in this run set")
        return lines
    lines.append(f"- Instant re-death cases: {len(instant_redies)}")
    lines.append(f"- Unrecoverable states: {len(unrecoverable)}")
    lines.append(f"- Broken thresholds: {len(broken_thresholds)}")
    lines.append(f"- Messaging gaps: {len(messaging_gaps)}")
    return lines


def _build_executive_summary(results):
    lines = ["=== EXECUTIVE SUMMARY ==="]
    lines.extend(_matrix_lines(results))
    lines.append("")
    lines.extend(_key_findings_lines(results))
    lines.append("")
    lines.extend(_verdict_lines(results))
    lines.append("")
    lines.extend(_critical_failures_lines(results))
    return lines


def _build_final_analysis(results):
    buckets = {"easy": [], "medium": [], "hard": [], "extreme": []}
    for entry in results:
        buckets[_balance_bucket(entry)].append(entry)
    lines = ["=== FINAL ANALYSIS ===", "1. Balance Curve"]
    lines.append(f"Easy cases: {sum(1 for entry in buckets['easy'] if entry['survived_20'])}/{len(buckets['easy'])} survived 20 ticks")
    lines.append(f"Medium cases: {sum(1 for entry in buckets['medium'] if entry['survived_20'])}/{len(buckets['medium'])} survived 20 ticks")
    lines.append(f"Hard cases: {sum(1 for entry in buckets['hard'] if entry['survived_20'])}/{len(buckets['hard'])} survived 20 ticks")
    lines.append(f"Extreme cases: {sum(1 for entry in buckets['extreme'] if entry['survived_20'])}/{len(buckets['extreme'])} survived 20 ticks")
    lines.append("")
    lines.append("2. Breakpoints")
    stage_two_failures = sum(1 for entry in results if entry['decay_stage'] == 2 and (not entry['res_success'] or entry['redied']))
    stage_three_failures = sum(1 for entry in results if entry['decay_stage'] == 3 and (not entry['res_success'] or entry['redied']))
    unsafe_cases = sum(1 for entry in results if entry['heal_start_band'] == 'UNSAFE' and not entry['survived_20'])
    lines.append(f"Decay Stage 2 -> failure spike: {stage_two_failures} failing or re-death outcomes")
    lines.append(f"Decay Stage 3 -> failure spike: {stage_three_failures} failing or re-death outcomes")
    lines.append(f"Unsafe corpse band -> unrecoverable pressure cases: {unsafe_cases}")
    lines.append("")
    lines.append("3. Recommendations")
    lines.append(f"- Increase stabilization window? {'Yes' if any(entry['redied'] and entry['stabilization_observed'] for entry in results) else 'No'}")
    lines.append(f"- Reduce decay penalties? {'Yes' if stage_three_failures > stage_two_failures // 2 else 'No'}")
    lines.append(f"- Increase empath cap? {'Yes' if any(entry['prep_cap_reached'] and not entry['survived_20'] for entry in results) else 'No'}")
    lines.append(f"- Adjust favor scaling? {'Yes' if sum(1 for entry in results if entry['favor'] == 1 and entry['survived_20']) == 0 else 'No'}")
    return lines


def _build_report(results, run_sections):
    header_lines = [
        "=== FULL DEATH → PREP → RES VALIDATION (POST-FIX) ===",
        "",
        f"Build Version: {_get_build_version()}",
        f"Date: {time.strftime('%Y-%m-%d')}",
        "Test Harness: full_death_to_res_suite.py",
        "DireTest Scenario: resurrection-stabilization-decay",
        "Baseline Declaration: I will not optimize, tweak, or adjust any system during these runs.",
        "",
        "[INIT] Previous docs/logs/fullDeathToRes.md deleted",
        "",
    ]
    lines = []
    lines.extend(header_lines)
    lines.extend(_build_executive_summary(results))
    lines.append("")
    for section in run_sections:
        lines.extend(section)
    lines.extend(_build_final_analysis(results))
    return lines


def main():
    global character_module, create_object
    global CmdAssess, CmdPrepare, CmdRestore, CmdStabilize, CmdTake, CmdTouch

    _setup_django()

    import typeclasses.characters as loaded_character_module
    from commands.cmd_assess import CmdAssess as LoadedCmdAssess
    from commands.cmd_prepare import CmdPrepare as LoadedCmdPrepare
    from commands.cmd_restore import CmdRestore as LoadedCmdRestore
    from commands.cmd_stabilize import CmdStabilize as LoadedCmdStabilize
    from commands.cmd_take import CmdTake as LoadedCmdTake
    from commands.cmd_touch import CmdTouch as LoadedCmdTouch
    from evennia.utils.create import create_object as loaded_create_object

    character_module = loaded_character_module
    create_object = loaded_create_object
    CmdAssess = LoadedCmdAssess
    CmdPrepare = LoadedCmdPrepare
    CmdRestore = LoadedCmdRestore
    CmdStabilize = LoadedCmdStabilize
    CmdTake = LoadedCmdTake
    CmdTouch = LoadedCmdTouch

    run_sections = []
    results = []
    run_number = 1
    for favor in FAVOR_LEVELS:
        for profile_key in WOUND_ORDER:
            for decay_stage in sorted(DECAY_STAGES):
                run_lines, result = _run_single(run_number, favor, profile_key, decay_stage)
                run_sections.append(run_lines)
                results.append(result)
                run_number += 1

    report_lines = _build_report(results, run_sections)
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(report_lines).strip() + "\n")
    print(f"Wrote {LOG_PATH} with {len(results)} runs.")


if __name__ == "__main__":
    main()