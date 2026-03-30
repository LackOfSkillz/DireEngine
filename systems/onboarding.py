import time
from collections.abc import Mapping

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from systems.chargen.validators import validate_name
from world.races import RACE_DEFINITIONS, resolve_race_name


GENDER_OPTIONS = ("male", "female", "neutral")
APPEARANCE_OPTIONS = {
    "hair_style": ("short", "long", "tied", "shaved"),
    "hair_color": ("black", "brown", "blonde", "red"),
    "build": ("lean", "average", "broad"),
    "height": ("short", "average", "tall"),
    "eyes": ("brown", "blue", "green", "gray"),
}
REQUIRED_APPEARANCE_FIELDS = tuple(APPEARANCE_OPTIONS.keys())
FORWARD_REQUIREMENTS = {
    "Lineup Platform": ("gender", "You need to choose your gender before moving on. Try: male, female, or neutral."),
    "Mirror Alcove": ("race", "You need to choose your race before moving on. Try: human, elf, or dwarf."),
    "Gear Rack Room": ("appearance", "You need to finish your appearance first. Try: hair short, hair black, build lean, height tall, eyes green."),
}
RELEASE_STEPS = ("gender", "race", "appearance", "gear", "weapon", "combat", "healing", "economy", "breach", "name")
ACTION_FLAG_DEFAULTS = {
    "gear_items": [],
    "weapon_wielded": False,
    "combat_started": False,
    "combat_won": False,
    "healing_success": False,
    "economy_buy": False,
    "economy_sell": False,
    "breach_started": False,
    "breach_cleared": False,
}
EVENT_FLAG_DEFAULTS = {
    "gear_delay_scene": False,
    "almost_failure_scene": False,
    "breach_warning": False,
    "breach_break": False,
    "breach_stabilized": False,
}
STEP_FAILURE_REACTIONS = {
    "gender": {
        "mentor": "Answer the intake question before you drift any farther.",
        "gremlin": "You can absolutely outrun paperwork right up until the paperwork catches you.",
    },
    "race": {
        "mentor": "Pick a station and own it.",
        "gremlin": "The platform only gets more confusing if you keep circling it.",
    },
    "appearance": {
        "mentor": "Use the mirror properly. The city will judge what it sees.",
        "gremlin": "Half-finished faces make people nervous. Sometimes that's useful. Not today.",
    },
    "gear": {
        "mentor": "Wear your kit before you try to prove anything.",
        "gremlin": "Boots first, heroics later. That's my professional view.",
    },
    "weapon": {
        "mentor": "Arm yourself before you enter the yard.",
        "gremlin": "Fists are free, but the goblins are still overpriced.",
    },
    "combat": {
        "mentor": "Finish the fight in the yard before you look for the next lesson.",
        "gremlin": "The goblin is not going to grade itself.",
    },
    "healing": {
        "mentor": "Patch the bleeding before you move on.",
        "gremlin": "Leaking is a bad long-term strategy.",
    },
    "economy": {
        "mentor": "Buy once and sell once. Learn the cost both ways.",
        "gremlin": "Quartermaster Nella charges for mistakes and refunds for smaller ones.",
    },
    "breach": {
        "mentor": "Hold the breach before you ask the gate to open.",
        "gremlin": "Those sounds mean someone forgot to keep goblins on the other side.",
    },
    "name": {
        "mentor": "Put a name on yourself before you leave this place.",
        "gremlin": "Names help us return your body to the correct ledger.",
    },
}
ROLE_KEYS = {
    "mentor": "Marshal Vey",
    "gremlin": "Pip the Gremlin",
}
ROLE_CUES = {
    "wake_room": {
        "mentor": "Up. You're late, which means you move now or you die tired.",
        "gremlin": "I brought forms. I dropped most of them, but the important panic survived.",
    },
    "gender": {
        "mentor": "Make the call and keep moving.",
        "gremlin": "See? Easy. Unless I wrote it down backward again.",
    },
    "race": {
        "mentor": "Good. Better to choose plainly than pretend badly.",
        "gremlin": "We could still swap boots between stations if you want excitement.",
    },
    "appearance": {
        "mentor": "Good. That's what strangers get first. Make it count.",
        "gremlin": "I liked the messier version, personally.",
    },
    "gear": {
        "mentor": "Wear what keeps you breathing, not what flatters you.",
        "gremlin": "I only handed out one left glove by mistake this time.",
    },
    "weapon": {
        "mentor": "Pick a weapon you can actually recover with after the first bad swing.",
        "gremlin": "The spear looked dramatic. I respect drama.",
    },
    "combat": {
        "mentor": "It bleeds. So will you, if you drift.",
        "gremlin": "If it bites you, try not to take it personally.",
    },
    "healing": {
        "mentor": "Patch yourself fast and get back on your feet.",
        "gremlin": "I sorted the bandages by least suspicious stain.",
    },
    "economy": {
        "mentor": "Count your money before someone else does it for you.",
        "gremlin": "If you overpay, call it an investment in morale.",
    },
    "breach": {
        "mentor": "That noise is why we stopped pretending this was a lesson.",
        "gremlin": "Technically it is still a lesson. Just louder now.",
    },
    "outer_gate": {
        "mentor": "Put a name on yourself before you step into a city that will remember it.",
        "gremlin": "Try a good one. Bad names travel faster.",
    },
    "name": {
        "mentor": "Good. Keep it if you can.",
        "gremlin": "Excellent choice. I would have picked something less pronounceable.",
    },
    "release": {
        "mentor": "You are as ready as anyone ever is. Move.",
        "gremlin": "If you come back missing anything, label it first.",
    },
}
ROLE_NUDGES = {
    "Wake Room": {
        "mentor": "On your feet. Intake is waiting.",
        "gremlin": "If you lie there much longer, I might inventory you.",
    },
    "Intake Hall": {
        "mentor": "Gender first. Simple answer, fast feet.",
        "gremlin": "I can guess if you'd rather regret that.",
    },
    "Lineup Platform": {
        "mentor": "Stand at the station that fits what you are.",
        "gremlin": "We could mix them. We should not. But we could.",
    },
    "Mirror Alcove": {
        "mentor": "Set your traits and stop wasting mirror light.",
        "gremlin": "The shaved option has conviction.",
    },
    "Outer Gate": {
        "mentor": "Choose your name. Then leave.",
        "gremlin": "No pressure. Only your whole future.",
    },
}

STEP_EXAMPLES = {
    "gender": ("male", "female", "neutral"),
    "race": ("human", "elf", "dwarf"),
    "appearance": ("hair short", "hair black", "build lean", "height tall", "eyes green"),
    "name": ("name Aric",),
}

STEP_MENTOR_HINTS = {
    "gender": "Answer plainly. Try: male.",
    "race": "Pick a station. Try: human.",
    "appearance": "Do the mirror work one trait at a time. Try: hair short.",
    "name": "Pick the name you intend to keep. Try: name Aric.",
}

STEP_GREMLIN_HINTS = {
    "gender": "Three choices. You only need one of them.",
    "race": "Human works if you are feeling traditional.",
    "appearance": "Hair first. It makes the mirror feel involved.",
    "name": "Names are easier when they fit on paperwork.",
}


def _format_examples(step):
    examples = STEP_EXAMPLES.get(step) or ()
    if not examples:
        return ""
    return " Try: " + ", ".join(examples) + "."


def _get_failure_counts(state):
    return dict(state.get("failure_counts") or {})


def _increment_failure_count(state, step):
    failure_counts = _get_failure_counts(state)
    new_count = int(failure_counts.get(str(step), 0) or 0) + 1
    failure_counts[str(step)] = new_count
    state["failure_counts"] = failure_counts
    return new_count


def _reset_failure_count(state, step):
    failure_counts = _get_failure_counts(state)
    if str(step) in failure_counts:
        failure_counts[str(step)] = 0
        state["failure_counts"] = failure_counts
    return state


def _queue_hint_lines(character, step, count):
    if int(count or 0) < 2:
        return False
    mentor_line = STEP_MENTOR_HINTS.get(step)
    gremlin_line = STEP_GREMLIN_HINTS.get(step)
    if mentor_line:
        _queue_roleplay(character, "mentor", mentor_line)
    if gremlin_line:
        _queue_roleplay(character, "gremlin", gremlin_line)
    return bool(mentor_line or gremlin_line)


def _normalize_input(raw_string):
    return " ".join(str(raw_string or "").strip().lower().split())


def _extract_choice(raw, prefixes):
    if raw in prefixes:
        return ""
    for prefix in prefixes:
        if raw.startswith(f"{prefix} "):
            return raw[len(prefix):].strip()
    return None


def _remap_gender_input(raw):
    candidate = _extract_choice(raw, ("gender", "choose", "pick", "select", "i am", "im", "i'm"))
    if raw in GENDER_OPTIONS:
        candidate = raw
    if candidate in GENDER_OPTIONS:
        return f"gender {candidate}"
    return None


def _remap_race_input(raw):
    candidate = _extract_choice(raw, ("race", "choose", "pick", "select", "stand", "stand at", "go to", "station"))
    if raw in {"human", "elf", "dwarf"}:
        candidate = raw
    if candidate:
        candidate = candidate.replace("station", "").strip()
    normalized = resolve_race_name(candidate or "", default=None)
    if normalized in RACE_DEFINITIONS:
        return f"stand at {normalized}"
    return None


def _remap_appearance_input(raw):
    mirror_verbs = {
        "mirror",
        "look mirror",
        "look at mirror",
        "touch mirror",
        "use mirror",
        "look into mirror",
    }
    if raw in mirror_verbs:
        return None, "The mirror only responds to clear choices." + _format_examples("appearance")

    tokens = raw.split()
    if not tokens:
        return None, None

    if tokens[0] in {"set", "choose", "pick", "select"}:
        tokens = tokens[1:]
    if not tokens:
        return None, None

    if len(tokens) >= 2 and tokens[0] == "hair":
        if tokens[1] == "style" and len(tokens) >= 3 and tokens[2] in APPEARANCE_OPTIONS["hair_style"]:
            return f"set hair style {tokens[2]}", None
        if tokens[1] == "color" and len(tokens) >= 3 and tokens[2] in APPEARANCE_OPTIONS["hair_color"]:
            return f"set hair color {tokens[2]}", None
        value = tokens[1]
        if value in APPEARANCE_OPTIONS["hair_style"]:
            return f"set hair style {value}", None
        if value in APPEARANCE_OPTIONS["hair_color"]:
            return f"set hair color {value}", None

    if len(tokens) >= 2 and tokens[0] in {"build", "height", "eyes"}:
        trait = tokens[0]
        value = tokens[1]
        if value in APPEARANCE_OPTIONS[trait]:
            return f"set {trait} {value}", None

    if tokens[0] in {"hair", "build", "height", "eyes", "mirror"}:
        return None, "Use one clear mirror trait at a time." + _format_examples("appearance")
    return None, None


def remap_onboarding_input(character, raw_string):
    if not is_onboarding_character(character):
        return None, None
    raw = _normalize_input(raw_string)
    if not raw:
        return None, None

    room_key = str(getattr(getattr(character, "location", None), "key", "") or "")
    state = ensure_onboarding_state(character)
    completed = set(state.get("completed_steps") or [])

    remapped = None
    immediate_message = None
    step = None

    if room_key == "Intake Hall" and "gender" not in completed:
        step = "gender"
        remapped = _remap_gender_input(raw)
    elif room_key == "Lineup Platform" and "race" not in completed:
        step = "race"
        remapped = _remap_race_input(raw)
    elif room_key == "Mirror Alcove" and "appearance" not in completed:
        step = "appearance"
        remapped, immediate_message = _remap_appearance_input(raw)
    elif room_key == "Outer Gate" and "name" not in completed and raw.startswith("call me "):
        step = "name"
        remapped = f"name {raw[8:].strip()}"

    if remapped:
        return remapped, None
    if immediate_message:
        count = _increment_failure_count(state, step)
        _persist_state(character, state)
        _queue_hint_lines(character, step, count)
        _emit_objective_line(character, _sync_current_objective(character, state=state), state, force=False, minimum_interval=6.0)
        return None, immediate_message

    likely_failed = False
    if step == "gender":
        likely_failed = raw in {"man", "woman"} or raw.startswith(("choose ", "pick ", "select ", "gender "))
    elif step == "race":
        likely_failed = raw.startswith(("race ", "choose ", "pick ", "select ", "stand ")) or raw in {"human", "elf", "dwarf"}
    elif step == "appearance":
        likely_failed = raw.startswith(("hair", "build", "height", "eyes", "set hair", "set build", "set height", "set eyes", "choose hair", "choose build", "choose height", "choose eyes"))
    elif step == "name":
        likely_failed = raw.startswith("call me ")

    if likely_failed and step:
        count = _increment_failure_count(state, step)
        _persist_state(character, state)
        _queue_hint_lines(character, step, count)
        _emit_objective_line(character, _sync_current_objective(character, state=state), state, force=False, minimum_interval=6.0)
        return None, f"That doesn't lock in yet.{_format_examples(step)}"

    return None, None


def _default_state():
    return {
        "active": True,
        "complete": False,
        "completed_steps": [],
        "action_flags": dict(ACTION_FLAG_DEFAULTS),
        "appearance": {field: None for field in REQUIRED_APPEARANCE_FIELDS},
        "current_objective": None,
        "objective_updated_at": 0.0,
        "last_progress_at": 0.0,
        "room_entered_at": 0.0,
        "tokens": 0,
        "visited_rooms": [],
        "event_flags": dict(EVENT_FLAG_DEFAULTS),
        "pending_roleplay": [],
        "reward_claimed": False,
        "final_name": None,
        "failure_counts": {},
        "last_roleplay": {},
    }


def ensure_onboarding_state(character):
    state = getattr(character.db, "onboarding_state", None)
    if not isinstance(state, Mapping):
        state = _default_state()
    else:
        normalized = _default_state()
        normalized.update(state)
        appearance = dict(normalized.get("appearance") or {})
        normalized["appearance"] = {field: appearance.get(field) for field in REQUIRED_APPEARANCE_FIELDS}
        action_flags = dict(ACTION_FLAG_DEFAULTS)
        action_flags.update(dict(normalized.get("action_flags") or {}))
        action_flags["gear_items"] = [str(item) for item in (action_flags.get("gear_items") or []) if item]
        normalized["action_flags"] = action_flags
        event_flags = dict(EVENT_FLAG_DEFAULTS)
        event_flags.update(dict(normalized.get("event_flags") or {}))
        normalized["event_flags"] = event_flags
        normalized["completed_steps"] = [str(step) for step in (normalized.get("completed_steps") or [])]
        normalized["visited_rooms"] = [str(room) for room in (normalized.get("visited_rooms") or [])]
        normalized["pending_roleplay"] = list(normalized.get("pending_roleplay") or [])
        normalized["failure_counts"] = dict(normalized.get("failure_counts") or {})
        normalized["current_objective"] = str(normalized.get("current_objective") or "") or None
        normalized["objective_updated_at"] = float(normalized.get("objective_updated_at", 0.0) or 0.0)
        normalized["last_progress_at"] = float(normalized.get("last_progress_at", 0.0) or 0.0)
        normalized["room_entered_at"] = float(normalized.get("room_entered_at", 0.0) or 0.0)
        normalized["last_roleplay"] = dict(normalized.get("last_roleplay") or {})
        state = normalized
    character.db.onboarding_state = state
    return state


def is_onboarding_character(character):
    if not character or not bool(getattr(character, "has_account", False)):
        return False
    state = ensure_onboarding_state(character)
    if bool(state.get("complete", False)):
        return False
    location = getattr(character, "location", None)
    return bool(getattr(getattr(location, "db", None), "is_tutorial", False) or state.get("active", False))


def _calculate_onboarding_objective(state):
    completed = set(state.get("completed_steps") or [])
    action_flags = dict(state.get("action_flags") or {})
    if "gender" not in completed:
        return "Choose your gender in Intake Hall." + _format_examples("gender")
    if "race" not in completed:
        return "Choose your race at the Lineup Platform." + _format_examples("race")
    if "appearance" not in completed:
        return "Set all five mirror traits in the Mirror Alcove." + _format_examples("appearance")
    if "gear" not in completed:
        return "Wear at least two pieces of starter gear in the Gear Rack Room."
    if "weapon" not in completed:
        return "Wield a weapon in the Weapon Cage."
    if "combat" not in completed:
        if not bool(action_flags.get("combat_started", False)):
            return "Attack the training goblin in the Training Yard."
        return "Bring down the training goblin in the Training Yard."
    if "healing" not in completed:
        return "Stop the bleeding with tend once you reach the Supply Shack."
    if "economy" not in completed:
        if not bool(action_flags.get("economy_buy", False)):
            return "Buy one item from Quartermaster Nella in the Vendor Stall."
        return "Sell one item back in the Vendor Stall so you learn both sides of trade."
    if "breach" not in completed:
        return "Hold the Breach Corridor until the way out is secure."
    if "name" not in completed:
        return "Choose your final name at the Outer Gate." + _format_examples("name")
    return "Leave through the gate and take your chances in The Landing."


def get_onboarding_objective(character):
    state = ensure_onboarding_state(character)
    return _calculate_onboarding_objective(state)


def _persist_state(character, state):
    character.db.onboarding_state = state
    return state


def _remember_recent_line(character, text, limit=25):
    if not character or not text or not hasattr(character, "ndb"):
        return []
    recent_lines = list(getattr(character.ndb, "_recent_lines", None) or [])
    recent_lines.append(str(text))
    character.ndb._recent_lines = recent_lines[-int(limit):]
    return list(character.ndb._recent_lines)


def get_recent_lines(character):
    if not character or not hasattr(character, "ndb"):
        return []
    return list(getattr(character.ndb, "_recent_lines", None) or [])


def _emit_objective_line(character, objective, state, force=False, minimum_interval=10.0):
    if not hasattr(character, "msg"):
        return False
    now = time.time()
    last_roleplay = dict(state.get("last_roleplay") or {})
    last_objective = float(last_roleplay.get("system:objective", 0.0) or 0.0)
    if not force and now - last_objective < float(minimum_interval or 0.0):
        return False
    line = f"[Objective] {objective}"
    character.msg(line)
    _remember_recent_line(character, line)
    last_roleplay["system:objective"] = now
    last_roleplay["system:prompt_pause"] = now
    state["last_roleplay"] = last_roleplay
    _persist_state(character, state)
    return True


def emit_room_line(character, text, exclude=None):
    room = getattr(character, "location", None)
    if room:
        room.msg_contents(str(text), exclude=exclude or [])
    _remember_recent_line(character, text)
    state = ensure_onboarding_state(character)
    last_roleplay = dict(state.get("last_roleplay") or {})
    last_roleplay["system:prompt_pause"] = time.time()
    state["last_roleplay"] = last_roleplay
    _persist_state(character, state)
    return True


def emit_npc_line(character, npc, line, exclude=None):
    if not character or not npc or not line:
        return False
    room = getattr(character, "location", None)
    if room and getattr(npc, "location", None) != room:
        npc.move_to(room, quiet=True)
    speaker = str(getattr(npc, "key", "Someone") or "Someone")
    text = f'{speaker} says, "{line}"'
    return emit_room_line(character, text, exclude=exclude)


def emit_named_line(character, speaker, line, exclude=None):
    if not character or not speaker or not line:
        return False
    text = f'{str(speaker)} says, "{line}"'
    return emit_room_line(character, text, exclude=exclude)


def _sync_current_objective(character, state=None, announce=False, force=False, minimum_interval=10.0):
    state = state or ensure_onboarding_state(character)
    objective = _calculate_onboarding_objective(state)
    previous = str(state.get("current_objective") or "") or None
    changed = previous != objective
    if changed:
        state["current_objective"] = objective
        state["objective_updated_at"] = time.time()
        _persist_state(character, state)
    tutorial = dict(getattr(character.db, "tutorial", None) or {})
    if tutorial.get("current_objective") != objective:
        tutorial["current_objective"] = objective
        character.db.tutorial = tutorial
        changed = True
    if announce and (changed or force):
        _emit_objective_line(character, objective, state, force=force or changed, minimum_interval=minimum_interval)
    return objective


def announce_objective(character, force=False):
    return _sync_current_objective(character, announce=True, force=force)


def remind_objective_if_idle(character, idle_threshold=5.0, minimum_interval=12.0):
    if not is_onboarding_character(character):
        return False
    state = ensure_onboarding_state(character)
    idle_for = time.time() - max(
        float(state.get("last_progress_at", 0.0) or 0.0),
        float(state.get("room_entered_at", 0.0) or 0.0),
    )
    if idle_for < float(idle_threshold or 0.0):
        return False
    objective = _sync_current_objective(character, state=state)
    return _emit_objective_line(character, objective, state, force=False, minimum_interval=minimum_interval)


def format_token_feedback(state):
    return f"You've learned something. (+1 Token, {int(state.get('tokens', 0) or 0)} total.)"


def _complete_step(character, step, tokens=1):
    state = ensure_onboarding_state(character)
    completed = list(state.get("completed_steps") or [])
    awarded = False
    if step not in completed:
        completed.append(step)
        state["completed_steps"] = completed
        state["last_progress_at"] = time.time()
        if int(tokens or 0) > 0:
            state["tokens"] = int(state.get("tokens", 0) or 0) + int(tokens or 0)
            awarded = True
    _persist_state(character, state)
    _sync_current_objective(character, state=state, announce=awarded, force=awarded)
    return state, awarded


def _set_action_flag(state, key, value):
    action_flags = dict(state.get("action_flags") or {})
    action_flags[key] = value
    state["action_flags"] = action_flags
    return state


def _set_event_flag(state, key, value):
    event_flags = dict(state.get("event_flags") or {})
    event_flags[key] = bool(value)
    state["event_flags"] = event_flags
    return state


def get_event_flag(character, key):
    state = ensure_onboarding_state(character)
    return bool(dict(state.get("event_flags") or {}).get(key, False))


def set_event_flag(character, key, value=True):
    state = ensure_onboarding_state(character)
    _set_event_flag(state, key, value)
    _persist_state(character, state)
    return bool(value)


def _append_action_flag_value(state, key, value):
    action_flags = dict(state.get("action_flags") or {})
    values = [str(entry) for entry in (action_flags.get(key) or []) if entry]
    if value not in values:
        values.append(value)
    action_flags[key] = values
    state["action_flags"] = action_flags
    return state


def _queue_roleplay(character, role, line):
    if role not in ROLE_KEYS or not line:
        return False
    state = ensure_onboarding_state(character)
    pending = list(state.get("pending_roleplay") or [])
    entry = {"role": str(role), "line": str(line)}
    if entry not in pending:
        pending.append(entry)
        state["pending_roleplay"] = pending
        _persist_state(character, state)
        return True
    return False


def queue_roleplay_line(character, role, line):
    return _queue_roleplay(character, role, line)


def pop_pending_roleplay(character, role):
    state = ensure_onboarding_state(character)
    pending = list(state.get("pending_roleplay") or [])
    for index, entry in enumerate(pending):
        if str(entry.get("role", "") or "") != str(role):
            continue
        pending.pop(index)
        state["pending_roleplay"] = pending
        _persist_state(character, state)
        return str(entry.get("line", "") or "")
    return None


def note_step_failure(character, step):
    if not is_onboarding_character(character):
        return False
    state = ensure_onboarding_state(character)
    reaction = STEP_FAILURE_REACTIONS.get(step)
    if not reaction:
        return False
    _queue_roleplay(character, "mentor", reaction.get("mentor"))
    _queue_roleplay(character, "gremlin", reaction.get("gremlin"))
    count = _increment_failure_count(state, step)
    _queue_hint_lines(character, step, count)
    objective = _sync_current_objective(character, state=state)
    _emit_objective_line(character, objective, state, force=False, minimum_interval=6.0)
    return True


def note_hesitation(character, context=None):
    if not is_onboarding_character(character):
        return False
    objective = get_onboarding_objective(character)
    mentor_line = "Standing still won't help you."
    gremlin_line = "Still thinking? The goblins are very action-oriented."
    normalized = str(context or "").strip().lower()
    if normalized == "combat":
        mentor_line = "Standing still won't help you. Hit it."
        gremlin_line = "It is still there. I checked by looking at all the teeth."
    elif normalized == "gear":
        mentor_line = "Standing still won't help you. Dress for the hit before it lands."
        gremlin_line = "You do look dramatically unarmored."
    elif normalized == "healing":
        mentor_line = "Fix it. Now."
        gremlin_line = "The floor is noticing how much of you is on it."
    _queue_roleplay(character, "mentor", mentor_line)
    _queue_roleplay(character, "gremlin", gremlin_line)
    _emit_objective_line(character, objective, ensure_onboarding_state(character), force=True)
    return True


def _record_room_visit(character, room_key):
    state = ensure_onboarding_state(character)
    visited = list(state.get("visited_rooms") or [])
    if room_key not in visited:
        visited.append(room_key)
        state["visited_rooms"] = visited
        _persist_state(character, state)
        return True
    return False


def _find_role_npc(role):
    return ObjectDB.objects.filter(db_key__iexact=ROLE_KEYS[role]).first()


def is_training_enemy(target):
    if not target:
        return False
    role = str(getattr(getattr(target, "db", None), "onboarding_enemy_role", "") or "").lower()
    if role in {"training", "breach"}:
        return True
    return bool(getattr(getattr(target, "db", None), "is_tutorial_enemy", False))


def _deliver_role_line(character, cue_key, role, force=False):
    npc = _find_role_npc(role)
    if not npc or not getattr(character, "location", None):
        return False
    if getattr(npc, "location", None) != character.location:
        npc.move_to(character.location, quiet=True)
    state = ensure_onboarding_state(character)
    throttle_key = f"{role}:{cue_key}"
    last_roleplay = dict(state.get("last_roleplay") or {})
    now = time.time()
    if not force and now - float(last_roleplay.get(throttle_key, 0.0) or 0.0) < 8.0:
        return False
    line = ROLE_CUES.get(cue_key, {}).get(role)
    if not line:
        return False
    emit_npc_line(character, npc, line)
    last_roleplay[throttle_key] = now
    state["last_roleplay"] = last_roleplay
    _persist_state(character, state)
    return True


def emit_progress_cue(character, cue_key):
    _deliver_role_line(character, cue_key, "mentor", force=True)
    _deliver_role_line(character, cue_key, "gremlin", force=True)


def build_description(character):
    state = ensure_onboarding_state(character)
    appearance = dict(state.get("appearance") or {})
    race_key = str(getattr(character.db, "race", "person") or "person").replace("_", " ")
    return (
        f"A {appearance['height']}, {appearance['build']} {race_key} with {appearance['hair_style']} "
        f"{appearance['hair_color']} hair and {appearance['eyes']} eyes."
    )


def set_gender(character, value):
    if not is_onboarding_character(character):
        return False, "You are not in an intake sequence."
    room = getattr(character.location, "key", None)
    if room != "Intake Hall":
        note_step_failure(character, "gender")
        return False, "You must choose your gender in Intake Hall."
    normalized = str(value or "").strip().lower()
    if normalized not in GENDER_OPTIONS:
        return False, f"Choose one of: {', '.join(GENDER_OPTIONS)}."
    character.db.gender = normalized
    state, awarded = _complete_step(character, "gender", tokens=1)
    _reset_failure_count(state, "gender")
    _persist_state(character, state)
    emit_progress_cue(character, "gender")
    message = f"You set your intake gender to {normalized}."
    if awarded:
        message = f"{message} {format_token_feedback(state)}"
    return True, message


def select_race(character, value):
    if not is_onboarding_character(character):
        return False, "You are not in an intake sequence."
    room = getattr(character.location, "key", None)
    if room != "Lineup Platform":
        note_step_failure(character, "race")
        return False, "You must choose your race at the Lineup Platform."
    state = ensure_onboarding_state(character)
    if "race" in set(state.get("completed_steps") or []):
        return False, "Your intake race has already been locked in."
    raw = str(value or "").strip().lower()
    if raw.startswith("at "):
        raw = raw[3:].strip()
    normalized = resolve_race_name(raw.replace(" station", ""), default=None)
    if normalized not in RACE_DEFINITIONS:
        return False, "Choose one of the marked stations: human, elf, or dwarf."
    if hasattr(character, "set_race"):
        character.set_race(normalized, sync=False, emit_messages=False)
    else:
        character.db.race = normalized
    state, awarded = _complete_step(character, "race", tokens=1)
    _reset_failure_count(state, "race")
    _persist_state(character, state)
    emit_progress_cue(character, "race")
    message = f"You take your place at the {normalized.replace('_', ' ')} station."
    if awarded:
        message = f"{message} {format_token_feedback(state)}"
    return True, message


def set_trait(character, trait, value):
    if not is_onboarding_character(character):
        return False, "You are not in an intake sequence."
    room = getattr(character.location, "key", None)
    if room != "Mirror Alcove":
        note_step_failure(character, "appearance")
        return False, "You must set your appearance in the Mirror Alcove."
    normalized_trait = str(trait or "").strip().lower().replace(" ", "_")
    normalized_value = str(value or "").strip().lower()
    if normalized_trait not in APPEARANCE_OPTIONS:
        return False, "Choose one of these traits: hair style, hair color, build, height, eyes."
    if normalized_value not in APPEARANCE_OPTIONS[normalized_trait]:
        choices = ", ".join(APPEARANCE_OPTIONS[normalized_trait])
        return False, f"Choose one of these {normalized_trait.replace('_', ' ')} values: {choices}."
    state = ensure_onboarding_state(character)
    appearance = dict(state.get("appearance") or {})
    appearance[normalized_trait] = normalized_value
    state["appearance"] = appearance
    character.db.onboarding_state = state
    character.db.appearance = dict(appearance)
    _reset_failure_count(state, "appearance")
    if all(appearance.get(field) for field in REQUIRED_APPEARANCE_FIELDS):
        character.db.desc = build_description(character)
        state, awarded = _complete_step(character, "appearance", tokens=1)
        _persist_state(character, state)
        emit_progress_cue(character, "appearance")
        message = f"You settle your reflection into focus. {character.db.desc}"
        if awarded:
            message = f"{message} {format_token_feedback(state)}"
        return True, message
    missing = [field.replace("_", " ") for field in REQUIRED_APPEARANCE_FIELDS if not appearance.get(field)]
    _persist_state(character, state)
    return True, "You adjust your reflection. Remaining traits: " + ", ".join(missing) + "."


def set_final_name(character, value):
    if not is_onboarding_character(character):
        return False, "You are not in an intake sequence."
    room = getattr(character.location, "key", None)
    if room != "Outer Gate":
        note_step_failure(character, "name")
        return False, "You choose your final name at the Outer Gate."
    normalized = str(value or "").strip()
    if not normalized:
        return False, "Choose a name."
    if normalized.lower() != str(getattr(character, "key", "") or "").lower():
        ok, error = validate_name(normalized)
        if not ok:
            return False, error
    old_key = character.key
    character.key = normalized
    character.save()
    state, awarded = _complete_step(character, "name", tokens=1)
    state["final_name"] = normalized
    _reset_failure_count(state, "name")
    _persist_state(character, state)
    emit_progress_cue(character, "name")
    message = f"You take the name {normalized}."
    if old_key != normalized:
        message = f"{message} The old intake tag is gone."
    if awarded:
        message = f"{message} {format_token_feedback(state)}"
    return True, message


def can_exit_to_world(character):
    state = ensure_onboarding_state(character)
    completed = set(state.get("completed_steps") or [])
    missing = [step for step in RELEASE_STEPS if step not in completed]
    if missing:
        if "name" in missing:
            return False, "Marshal Vey says, 'Put a name on yourself before you step beyond this gate.'"
        return False, "You are not ready to leave yet. " + get_onboarding_objective(character)
    return True, ""


def release_to_world(character):
    ok, error = can_exit_to_world(character)
    if not ok:
        return False, error
    state = ensure_onboarding_state(character)
    if not bool(state.get("reward_claimed", False)):
        tokens = int(state.get("tokens", 0) or 0)
        character.add_coins(40 + (tokens * 3))
        tonic = create_object("typeclasses.objects.Object", key="field tonic", location=character, home=character)
        tonic.db.weight = 0.2
        tonic.db.desc = "A sharp-smelling tonic from the Last Intake compound. It is meant to get you moving again, not comfort you."
        chit = create_object("typeclasses.objects.Object", key="last intake token-bundle", location=character, home=character)
        chit.db.weight = 0.1
        chit.db.desc = "A tied bundle of stamped intake tokens showing you survived the compound's last rushed intake."
        cloak = create_object("typeclasses.wearables.Wearable", key="compound issue cloak", location=character, home=character)
        cloak.db.slot = "torso"
        cloak.db.item_type = "armor"
        cloak.db.armor_type = "light_armor"
        cloak.db.protection = 2
        cloak.db.hindrance = 0
        cloak.db.coverage = ["torso", "left_arm", "right_arm"]
        cloak.db.weight = 1.5
        cloak.db.desc = "A reinforced intake cloak with stitched interior plates, issued only to survivors of the compound's last rushed intake."
        state["reward_claimed"] = True
    state["active"] = False
    state["complete"] = True
    _persist_state(character, state)
    emit_progress_cue(character, "release")
    return True, "Marshal Vey gives a curt nod, tosses you a plated intake cloak and a heavier purse, and waves you through. The intake is over."


def prompt_spacing_active(character, minimum_interval=2.5):
    state = ensure_onboarding_state(character)
    last_roleplay = dict(state.get("last_roleplay") or {})
    last_prompt = float(last_roleplay.get("system:prompt_pause", 0.0) or 0.0)
    return (time.time() - last_prompt) < float(minimum_interval or 0.0)


def get_traverse_block(exit_obj, character, target_location):
    if not character or not is_onboarding_character(character):
        return None
    destination_key = str(getattr(target_location, "key", "") or "")
    requirement = FORWARD_REQUIREMENTS.get(destination_key)
    if requirement:
        step, message = requirement
        state = ensure_onboarding_state(character)
        if step not in set(state.get("completed_steps") or []):
            note_step_failure(character, step)
            return message
    current_room = getattr(character.location, "key", None)
    leaving_tutorial = bool(getattr(getattr(character.location, "db", None), "is_tutorial", False)) and not bool(getattr(getattr(target_location, "db", None), "is_tutorial", False))
    if leaving_tutorial or (current_room == "Outer Gate" and str(getattr(exit_obj, "key", "")).lower() in {"out", "leave"}) or (current_room == "Secret Tunnel" and str(getattr(exit_obj, "key", "")).lower() == "crawl"):
        ok, error = can_exit_to_world(character)
        if not ok:
            missing = [step for step in RELEASE_STEPS if step not in set(ensure_onboarding_state(character).get("completed_steps") or [])]
            if missing:
                note_step_failure(character, missing[0])
            return error
        release_to_world(character)
    return None


def handle_room_entry(character):
    if not is_onboarding_character(character):
        return
    room = getattr(character, "location", None)
    if not room:
        return
    state = ensure_onboarding_state(character)
    if bool(state.get("complete", False)):
        return
    room_key = str(getattr(room, "key", "") or "")
    state["room_entered_at"] = time.time()
    _persist_state(character, state)
    first_visit = _record_room_visit(character, room_key)
    if first_visit and room_key == "Wake Room":
        emit_progress_cue(character, "wake_room")
    elif first_visit and room_key == "Outer Gate":
        emit_progress_cue(character, "outer_gate")
    _sync_current_objective(character, state=state)


def note_equipment_action(character, item):
    if not is_onboarding_character(character):
        return False, False
    if "appearance" not in set(ensure_onboarding_state(character).get("completed_steps") or []):
        note_step_failure(character, "appearance")
        return False, False
    state = ensure_onboarding_state(character)
    item_key = str(getattr(item, "key", "gear") or "gear")
    _append_action_flag_value(state, "gear_items", item_key)
    state["last_progress_at"] = time.time()
    _persist_state(character, state)
    worn_count = len(getattr(character, "get_worn_items", lambda: [])() or [])
    if worn_count < 2:
        _queue_roleplay(character, "mentor", "Good. One more.")
        _sync_current_objective(character, state=state)
        return False, False
    state, awarded = _complete_step(character, "gear", tokens=1)
    if awarded:
        emit_progress_cue(character, "gear")
    return True, awarded


def note_weapon_action(character, item):
    if not is_onboarding_character(character):
        return False, False
    state = ensure_onboarding_state(character)
    if "gear" not in set(state.get("completed_steps") or []):
        note_step_failure(character, "gear")
        return False, False
    _set_action_flag(state, "weapon_wielded", True)
    state["last_progress_at"] = time.time()
    _persist_state(character, state)
    state, awarded = _complete_step(character, "weapon", tokens=1)
    if awarded:
        emit_progress_cue(character, "weapon")
    return True, awarded


def note_combat_start(character, target):
    if not is_onboarding_character(character) or not is_training_enemy(target):
        return False
    state = ensure_onboarding_state(character)
    _set_action_flag(state, "combat_started", True)
    state["last_progress_at"] = time.time()
    _persist_state(character, state)
    _queue_roleplay(character, "mentor", "Good. Again.")
    return True


def note_combat_win(character, target):
    if not is_onboarding_character(character) or not is_training_enemy(target):
        return False, False
    enemy_role = str(getattr(getattr(target, "db", None), "onboarding_enemy_role", "") or "training").lower()
    state = ensure_onboarding_state(character)
    _set_action_flag(state, "combat_started", True)
    state["last_progress_at"] = time.time()
    if enemy_role == "breach":
        _set_action_flag(state, "breach_started", True)
        _set_action_flag(state, "breach_cleared", True)
        _persist_state(character, state)
        state, awarded = _complete_step(character, "breach", tokens=1)
        if awarded:
            emit_progress_cue(character, "breach")
        return True, awarded
    _set_action_flag(state, "combat_won", True)
    _persist_state(character, state)
    state, awarded = _complete_step(character, "combat", tokens=1)
    if awarded:
        emit_progress_cue(character, "combat")
    return True, awarded


def note_healing_action(character, patient=None, part=None):
    if not is_onboarding_character(character):
        return False, False
    state = ensure_onboarding_state(character)
    if "combat" not in set(state.get("completed_steps") or []):
        note_step_failure(character, "combat")
        return False, False
    _set_action_flag(state, "healing_success", True)
    state["last_progress_at"] = time.time()
    _persist_state(character, state)
    state, awarded = _complete_step(character, "healing", tokens=1)
    if awarded:
        emit_progress_cue(character, "healing")
    return True, awarded


def note_trade_action(character, action):
    if not is_onboarding_character(character):
        return False, False
    normalized = str(action or "").strip().lower()
    state = ensure_onboarding_state(character)
    if "healing" not in set(state.get("completed_steps") or []):
        note_step_failure(character, "healing")
        return False, False
    if normalized == "buy":
        _set_action_flag(state, "economy_buy", True)
    elif normalized == "sell":
        _set_action_flag(state, "economy_sell", True)
    else:
        return False, False
    state["last_progress_at"] = time.time()
    _persist_state(character, state)
    action_flags = dict(state.get("action_flags") or {})
    if not (bool(action_flags.get("economy_buy", False)) and bool(action_flags.get("economy_sell", False))):
        return False, False
    state, awarded = _complete_step(character, "economy", tokens=1)
    if awarded:
        emit_progress_cue(character, "economy")
    return True, awarded


def note_breach_progress(character, action):
    if not is_onboarding_character(character):
        return False, False
    state = ensure_onboarding_state(character)
    if "economy" not in set(state.get("completed_steps") or []):
        note_step_failure(character, "economy")
        return False, False
    normalized = str(action or "").strip().lower()
    if normalized == "start":
        _set_action_flag(state, "breach_started", True)
        state["last_progress_at"] = time.time()
        _persist_state(character, state)
        return True, False
    if normalized != "clear":
        return False, False
    _set_action_flag(state, "breach_started", True)
    _set_action_flag(state, "breach_cleared", True)
    state["last_progress_at"] = time.time()
    _persist_state(character, state)
    state, awarded = _complete_step(character, "breach", tokens=1)
    if awarded:
        emit_progress_cue(character, "breach")
    return True, awarded


def _get_contextual_roleplay_line(role, character):
    state = ensure_onboarding_state(character)
    completed = set(state.get("completed_steps") or [])
    action_flags = dict(state.get("action_flags") or {})
    now = time.time()
    room_key = str(getattr(getattr(character, "location", None), "key", "") or "")
    hp = int(getattr(getattr(character, "db", None), "hp", 0) or 0)
    max_hp = max(1, int(getattr(getattr(character, "db", None), "max_hp", 1) or 1))
    if (hp / max_hp) <= 0.5 and "healing" not in completed:
        return "Fix it. Now." if role == "mentor" else "You are very visibly losing this argument with your blood."
    objective_age = now - float(state.get("objective_updated_at", 0.0) or 0.0)
    if objective_age > 18.0 and "name" not in completed:
        return "Standing still won't help you." if role == "mentor" else "I admire the pause. The goblins won't."
    mentor_lines = {
        "Intake Hall": "Gender first. Keep it simple and keep moving.",
        "Lineup Platform": "Choose the station that matches what you are.",
        "Mirror Alcove": "Finish the mirror work before you touch the kit.",
        "Gear Rack Room": "Wear at least two pieces. I want to hear cloth, not excuses.",
        "Weapon Cage": "Wield something before you step into the yard.",
        "Training Yard": "Start the fight clean and finish it faster.",
        "Supply Shack": "Tend the wound. Survivors learn before the scar sets.",
        "Vendor Stall": "Buy once. Sell once. Know what your mistakes cost.",
        "Breach Corridor": "Hold this corridor. No one is opening the gate for panic.",
        "Outer Gate": "Name yourself, then leave.",
    }
    gremlin_lines = {
        "Intake Hall": "Three options. Only one of them is 'keep staring at me.'",
        "Lineup Platform": "Pick a station before I alphabetize you incorrectly.",
        "Mirror Alcove": "The mirror likes commitment.",
        "Gear Rack Room": "Boots and trousers are both stronger when they are on you.",
        "Weapon Cage": "A weapon in hand looks much more intentional.",
        "Training Yard": "The goblin is having a far worse morning than you. Keep it that way.",
        "Supply Shack": "Bandages are cheaper than replacement limbs.",
        "Vendor Stall": "Quartermaster Nella enjoys exact change and mild suffering.",
        "Breach Corridor": "That noise is the sound of scheduling problems with knives.",
        "Outer Gate": "I recommend a name you can shout while running.",
    }
    if room_key == "Training Yard" and "combat" not in completed:
        if not bool(action_flags.get("weapon_wielded", False)):
            return STEP_FAILURE_REACTIONS["weapon"].get(role)
        if not bool(action_flags.get("combat_started", False)):
            return mentor_lines[room_key] if role == "mentor" else gremlin_lines[room_key]
        return "Finish the goblin before you drift." if role == "mentor" else "You are doing the dangerous part. Commit." 
    if room_key == "Vendor Stall" and "economy" not in completed:
        if not bool(action_flags.get("economy_buy", False)):
            return "Buy something small and remember the price." if role == "mentor" else "Spend a little. Educational regret builds character."
        return "Sell something back and learn the other half." if role == "mentor" else "Now sell something before the lesson becomes philosophy."
    if room_key == "Breach Corridor" and "breach" not in completed:
        return mentor_lines[room_key] if role == "mentor" else gremlin_lines[room_key]
    if "gender" not in completed:
        return mentor_lines.get("Intake Hall") if role == "mentor" else gremlin_lines.get("Intake Hall")
    if "race" not in completed:
        return mentor_lines.get("Lineup Platform") if role == "mentor" else gremlin_lines.get("Lineup Platform")
    if "appearance" not in completed:
        return mentor_lines.get("Mirror Alcove") if role == "mentor" else gremlin_lines.get("Mirror Alcove")
    if "gear" not in completed:
        return mentor_lines.get("Gear Rack Room") if role == "mentor" else gremlin_lines.get("Gear Rack Room")
    if "weapon" not in completed:
        return mentor_lines.get("Weapon Cage") if role == "mentor" else gremlin_lines.get("Weapon Cage")
    if "combat" not in completed:
        return mentor_lines.get("Training Yard") if role == "mentor" else gremlin_lines.get("Training Yard")
    if "healing" not in completed:
        return mentor_lines.get("Supply Shack") if role == "mentor" else gremlin_lines.get("Supply Shack")
    if "economy" not in completed:
        return mentor_lines.get("Vendor Stall") if role == "mentor" else gremlin_lines.get("Vendor Stall")
    if "breach" not in completed:
        return mentor_lines.get("Breach Corridor") if role == "mentor" else gremlin_lines.get("Breach Corridor")
    if "name" not in completed:
        return mentor_lines.get("Outer Gate") if role == "mentor" else gremlin_lines.get("Outer Gate")
    return None


def get_roleplay_nudge(npc, character):
    room = getattr(character, "location", None)
    if not room:
        return None
    room_key = str(getattr(room, "key", "") or "")
    role = str(getattr(getattr(npc, "db", None), "onboarding_role", "") or "").lower()
    if role not in {"mentor", "gremlin"}:
        return None
    pending = pop_pending_roleplay(character, role)
    if pending:
        return pending
    contextual = _get_contextual_roleplay_line(role, character)
    if contextual:
        return contextual
    return ROLE_NUDGES.get(room_key, {}).get(role)


def trigger_gear_delay_scene(character):
    if not is_onboarding_character(character) or get_event_flag(character, "gear_delay_scene"):
        return False
    state = ensure_onboarding_state(character)
    if "appearance" not in set(state.get("completed_steps") or []):
        return False
    if "gear" in set(state.get("completed_steps") or []):
        return False
    if str(getattr(getattr(character, "location", None), "key", "") or "") != "Gear Rack Room":
        return False
    set_event_flag(character, "gear_delay_scene", True)
    gremlin = _find_role_npc("gremlin")
    mentor = _find_role_npc("mentor")
    room = getattr(character, "location", None)
    if gremlin and getattr(gremlin, "location", None) != room:
        gremlin.move_to(room, quiet=True)
    if mentor and getattr(mentor, "location", None) != room:
        mentor.move_to(room, quiet=True)
    if room:
        if gremlin:
            emit_npc_line(character, gremlin, "Handled!")
        else:
            emit_named_line(character, ROLE_KEYS["gremlin"], "Handled!")
        if mentor:
            emit_npc_line(character, mentor, "...no.")
            emit_npc_line(character, mentor, "Wear something that stops a blade.")
        else:
            emit_named_line(character, ROLE_KEYS["mentor"], "...no.")
            emit_named_line(character, ROLE_KEYS["mentor"], "Wear something that stops a blade.")
    announce_objective(character, force=True)
    return True


def trigger_almost_failure_scene(character):
    if not is_onboarding_character(character) or get_event_flag(character, "almost_failure_scene"):
        return False
    state = ensure_onboarding_state(character)
    if "weapon" not in set(state.get("completed_steps") or []):
        return False
    if bool(dict(state.get("action_flags") or {}).get("combat_started", False)):
        return False
    if str(getattr(getattr(character, "location", None), "key", "") or "") != "Training Yard":
        return False
    set_event_flag(character, "almost_failure_scene", True)
    room = getattr(character, "location", None)
    gremlin = _find_role_npc("gremlin")
    mentor = _find_role_npc("mentor")
    if gremlin and getattr(gremlin, "location", None) != room:
        gremlin.move_to(room, quiet=True)
    if mentor and getattr(mentor, "location", None) != room:
        mentor.move_to(room, quiet=True)
    if room:
        if gremlin:
            emit_npc_line(character, gremlin, "Threat handled.")
        else:
            emit_named_line(character, ROLE_KEYS["gremlin"], "Threat handled.")
    if hasattr(character, "apply_damage"):
        character.apply_damage("left_arm", 4, damage_type="slice")
    if hasattr(character, "msg"):
        line = "A goblin lunges out of the dust and clips your arm before you can settle."
        character.msg(line)
        _remember_recent_line(character, line)
    if room:
        emit_room_line(character, f"A goblin lunges out of the yard haze and clips {character.key} before they can settle.", exclude=[character])
        if mentor:
            emit_npc_line(character, mentor, "Stop listening. Start acting.")
        else:
            emit_named_line(character, ROLE_KEYS["mentor"], "Stop listening. Start acting.")
    announce_objective(character, force=True)
    return True


def get_status_lines(character):
    state = ensure_onboarding_state(character)
    completed = set(state.get("completed_steps") or [])
    appearance = dict(state.get("appearance") or {})
    action_flags = dict(state.get("action_flags") or {})
    remaining_traits = [field.replace("_", " ") for field in REQUIRED_APPEARANCE_FIELDS if not appearance.get(field)]
    return [
        f"Objective: {_sync_current_objective(character, state=state)}",
        f"Tokens: {int(state.get('tokens', 0) or 0)}",
        "Completed: " + (", ".join(sorted(completed)) if completed else "none"),
        "Action flags: " + ", ".join(
            [
                f"gear={len(action_flags.get('gear_items') or [])}",
                f"weapon={'yes' if action_flags.get('weapon_wielded') else 'no'}",
                f"combat={'won' if action_flags.get('combat_won') else ('started' if action_flags.get('combat_started') else 'no')}",
                f"healing={'yes' if action_flags.get('healing_success') else 'no'}",
                f"economy={'buy/sell' if action_flags.get('economy_buy') and action_flags.get('economy_sell') else ('buy' if action_flags.get('economy_buy') else ('sell' if action_flags.get('economy_sell') else 'no'))}",
                f"breach={'clear' if action_flags.get('breach_cleared') else ('started' if action_flags.get('breach_started') else 'no')}",
            ]
        ),
        "Remaining appearance: " + (", ".join(remaining_traits) if remaining_traits else "none"),
    ]