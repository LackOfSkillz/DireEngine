import time

from systems.appearance.normalizer import normalize_identity_data
from systems.character.creation import apply_character_stats, create_character_from_blueprint
from systems.chargen.state import CHARGEN_BASE_STATS
from systems.chargen.validators import preview_race_stats, release_name, reserve_name, validate_name


CHARGEN_STEPS = ("race", "build", "height", "hair", "eyes", "skin")
MIRROR_KEY = "assessment mirror"
GREMLIN_KEY = "Intake Gremlin"
GUIDE_KEY = "Intake Guide"
DEFAULT_RACE = "human"
DEFAULT_GENDER = "neutral"
DEFAULT_PROFESSION = "commoner"
BLOCKED_INPUT_MESSAGE = "Not that. Choose what the mirror gives you."
MOVEMENT_BLOCKED_MESSAGE = "The guide doesn't move. Neither do you."
FINALIZE_WARNING = "Once this holds, it cannot be undone."
FINALIZE_WARNING_FOLLOWUP = "Decide now. It won't change after this."

STEP_OPTIONS = {
    "race": ["human", "elf", "dwarf", "halfling", "gnome", "volgrin", "saurathi", "valran", "aethari", "felari", "lunari"],
    "build": ["lean", "athletic", "heavy", "slight"],
    "height": ["short", "average", "tall"],
    "hair": ["black", "brown", "blonde", "gray"],
    "eyes": ["brown", "blue", "green", "gray"],
    "skin": ["fair", "tan", "dark", "weathered"],
}

STEP_LABELS = {
    "race": "race",
    "build": "build",
    "height": "height",
    "hair": "hair",
    "eyes": "eyes",
    "skin": "skin",
}

GUIDE_STEP_LINES = {
    "race": [],
    "build": ["You carry this before anything else."],
    "height": ["Reach matters."],
    "hair": ["People remember what frames the face."],
    "eyes": ["Eyes matter."],
    "skin": ["The road will mark you soon enough."],
}

GREMLIN_STEP_LINES = {
    "build": "Pick one that survives the first hit.",
    "height": "Tall gets noticed sooner. Short gets cornered sooner.",
    "skin": "Bruises improve with contrast.",
}

GUIDE_IDLE_LINES = {
    "race": "Touch it again if you're not finished.",
    "build": "Pick the frame and keep moving.",
    "height": "Pick your reach.",
    "hair": "Set it.",
    "eyes": "Look back and finish it.",
    "skin": "One last choice. Then move.",
}

STEP_TOUCH_LINES = {
    "race": (
        "The face shifts, lengthening and refining, until it settles into {value} lines.",
        "The structure compresses and thickens until the reflection settles into {value} proportions.",
        "The reflection redraws itself again until {value} remains, waiting without comment.",
    ),
    "build": (
        "The shoulders broaden, weight settling into {article_value} frame.",
        "The body narrows and draws tighter into {article_value} build.",
        "The frame shifts again until a {value} shape holds in the glass.",
    ),
    "height": (
        "The body lengthens and resets into a {value} stance.",
        "The reflection rises, then settles, measured now at {value} height.",
        "The mirror adjusts the frame again until it stands {value} and still.",
    ),
    "hair": (
        "Hair darkens and reshapes until {value} remains.",
        "The line of the face changes as {value} hair settles into place.",
        "The mirror redraws the edges of you until {value} hair holds.",
    ),
    "eyes": (
        "The gaze clears and fixes into {value} eyes.",
        "Color drains and returns until {value} remains in the glass.",
        "The reflection blinks once, then opens on {value} eyes.",
    ),
    "skin": (
        "Tone and weather settle until the reflection holds {value} skin.",
        "The mirror dulls and redraws you with {value} skin.",
        "The surface shifts once more until {value} skin remains.",
    ),
}

STEP_LOOK_LINES = {
    "race": (
        "The mirror finds a face and holds it there.\n\n{value_cap}.\n\nIt waits. Not for approval, but for interruption.",
    ),
    "build": (
        "The frame shifts, lean and then heavier, before settling at {value}.\n\nNone of them belong to you yet.",
    ),
    "height": (
        "The body in the glass stands {value}, measured without kindness.",
    ),
    "hair": (
        "The mirror shows {value} hair framing the same unreadable face.",
    ),
    "eyes": (
        "The reflection meets you with {value} eyes that do not blink first.",
    ),
    "skin": (
        "The mirror settles on {value} skin and refuses to explain itself.",
    ),
}

FINAL_GUIDE_LINES = ["Enough.", "Move."]

STEP_LOCK_LINES = {
    "race": "The mirror stills.\n\nIt does not confirm your choice.\n\nIt simply stops changing.",
    "build": "The reflection settles.\n\nThis time, it does not try to change.",
}

NEXT_STEP_GUIDE_LINES = (
    "Good. Move on.",
    "That'll do.",
    "Enough. Next.",
    "Keep moving.",
    "",
)


def is_chargen_active(character):
    if not character:
        return False
    data = getattr(character, "db", None)
    return bool(getattr(data, "chargen_active", False) or getattr(data, "in_chargen", False))


def _allowed_free_commands():
    return {
        "look",
        "l",
        "look mirror",
        "l mirror",
        "touch mirror",
        "done",
        "next",
        "next feature",
        "accept",
        "accept reflection",
        "back",
        "finalize",
        "confirm",
        "cancel",
        "inventory",
        "inv",
        "i",
        "help",
    }


def _is_movement_command(character, lowered_command):
    if lowered_command == "__clickmove__":
        return True
    room = getattr(character, "location", None)
    if not room:
        return False
    for exit_obj in list(getattr(room, "contents_get", lambda **kwargs: [])(content_type="exit") or []):
        exit_key = str(getattr(exit_obj, "key", "") or "").strip().lower()
        if exit_key and lowered_command == exit_key:
            return True
    return False


def get_available_actions(character):
    if not is_chargen_active(character):
        return []
    if _is_confirm_mode(character):
        return [
            {"label": "confirm", "command": "confirm"},
            {"label": "cancel", "command": "cancel"},
        ]
    if _is_review_mode(character):
        return [
            {"label": "review", "command": "look mirror"},
            {"label": "back", "command": "back"},
            {"label": "finalize", "command": "finalize"},
        ]
    step = _current_step(character)
    actions = [
        {"label": "look mirror", "command": "look mirror"},
        {"label": "touch mirror", "command": "touch mirror"},
        {"label": "accept", "command": "accept"},
    ]
    step_index = CHARGEN_STEPS.index(step)
    if step_index > 0:
        actions.append({"label": "back", "command": "back"})
    if step_index < len(CHARGEN_STEPS) - 1:
        actions.append({"label": "next", "command": "next"})
    return actions


def get_active_chargen_character(account):
    if not account:
        return None
    for character in list(account.characters.all()):
        if is_chargen_active(character):
            return character
    return None


def _find_room_actor(room, key):
    if not room:
        return None
    for obj in list(getattr(room, "contents", []) or []):
        if str(getattr(obj, "key", "") or "").strip().lower() == key.lower():
            return obj
    return None


def _speaker_name(character, preferred_key):
    speaker = _find_room_actor(getattr(character, "location", None), preferred_key)
    return getattr(speaker, "key", preferred_key)


def _msg_line(character, speaker, line):
    character.msg(f"{speaker} says, \"{line}\"")


def _current_step(character):
    step = str(getattr(character.db, "chargen_step", CHARGEN_STEPS[0]) or CHARGEN_STEPS[0]).strip().lower()
    if step not in STEP_OPTIONS:
        return CHARGEN_STEPS[0]
    return step


def _current_index(character):
    try:
        value = int(getattr(character.db, "chargen_index", 0) or 0)
    except (TypeError, ValueError):
        value = 0
    options = STEP_OPTIONS[_current_step(character)]
    return value % len(options)


def _current_value(character):
    step = _current_step(character)
    selections = dict(getattr(character.db, "chargen_selections", {}) or {})
    options = STEP_OPTIONS[step]
    value = selections.get(step)
    if value in options:
        return value
    return options[_current_index(character)]


def _store_current_value(character, value=None):
    step = _current_step(character)
    options = STEP_OPTIONS[step]
    current_value = value if value in options else _current_value(character)
    selections = dict(getattr(character.db, "chargen_selections", {}) or {})
    selections[step] = current_value
    character.db.chargen_selections = selections
    character.db.chargen_index = options.index(current_value)
    return current_value


def _set_step(character, step):
    character.db.chargen_step = step
    character.db.chargen_last_interaction_at = time.time()
    current_value = _current_value_for_step(character, step)
    options = STEP_OPTIONS[step]
    character.db.chargen_index = options.index(current_value) if current_value in options else 0
    _store_current_value(character, current_value)
    return step


def _advance_step(character):
    step = _current_step(character)
    position = CHARGEN_STEPS.index(step)
    if position + 1 >= len(CHARGEN_STEPS):
        return None
    next_step = CHARGEN_STEPS[position + 1]
    _set_step(character, next_step)
    return next_step


def _rewind_step(character):
    step = _current_step(character)
    position = CHARGEN_STEPS.index(step)
    if position <= 0:
        return None
    previous_step = CHARGEN_STEPS[position - 1]
    _set_step(character, previous_step)
    return previous_step


def _locked_steps(character):
    return list(getattr(character.db, "chargen_locked_steps", []) or [])


def _mark_locked(character, step):
    locked = _locked_steps(character)
    if step not in locked:
        locked.append(step)
    character.db.chargen_locked_steps = locked
    return locked


def _unmark_locked(character, step):
    locked = [entry for entry in _locked_steps(character) if entry != step]
    character.db.chargen_locked_steps = locked
    return locked


def _current_value_for_step(character, step):
    current_step = str(step or _current_step(character)).strip().lower()
    selections = dict(getattr(character.db, "chargen_selections", {}) or {})
    options = STEP_OPTIONS[current_step]
    value = selections.get(current_step)
    if value in options:
        return value
    return options[0]


def _is_review_mode(character):
    return bool(getattr(character.db, "chargen_review_mode", False))


def _set_review_mode(character, enabled):
    character.db.chargen_review_mode = bool(enabled)
    if enabled:
        character.db.chargen_confirm_mode = False
    return bool(character.db.chargen_review_mode)


def _is_confirm_mode(character):
    return bool(getattr(character.db, "chargen_confirm_mode", False))


def _set_confirm_mode(character, enabled):
    character.db.chargen_confirm_mode = bool(enabled)
    return bool(character.db.chargen_confirm_mode)


def _build_description(appearance):
    article = "An" if str(appearance.get("height", "a"))[0].lower() in "aeiou" else "A"
    return (
        f"{article} {appearance['height']}, {appearance['build']} figure with {appearance['skin']} skin, "
        f"{appearance['hair']} hair, and {appearance['eyes']} eyes."
    )


def _apply_final_identity(character):
    selections = dict(getattr(character.db, "chargen_selections", {}) or {})
    race = selections.get("race", DEFAULT_RACE)
    appearance = {step: selections[step] for step in CHARGEN_STEPS if step != "race"}
    identity = normalize_identity_data(
        {
            "race": race,
            "gender": DEFAULT_GENDER,
            "appearance": appearance,
        },
        fallback_race=race,
        fallback_gender=DEFAULT_GENDER,
        fallback_appearance=appearance,
    )
    character.db.gender = DEFAULT_GENDER
    character.db.identity = identity
    character.db.desc = _build_description(appearance)
    if hasattr(character, "set_race"):
        character.set_race(race, sync=False, emit_messages=False)
    apply_character_stats(character, preview_race_stats(CHARGEN_BASE_STATS, race))
    if hasattr(character, "get_rendered_desc"):
        character.db.desc = character.get_rendered_desc()
    if hasattr(character, "sync_client_state"):
        character.sync_client_state(include_map=False)


def _clear_chargen_flags(character):
    character.db.chargen_active = False
    character.db.in_chargen = False
    character.db.chargen_step = None
    character.db.chargen_index = None
    character.db.chargen_locked_steps = []
    character.db.chargen_selections = {}
    character.db.chargen_prompted_steps = []
    character.db.chargen_gremlin_steps = []
    character.db.chargen_last_interaction_at = 0.0
    character.db.chargen_last_nudge_at = 0.0
    character.db.chargen_step_interactions = {}
    character.db.chargen_variant_counts = {}
    character.db.chargen_review_mode = False
    character.db.chargen_confirm_mode = False
    character.db.chargen_finalized = False


def _get_step_map(character, attr_name):
    return dict(getattr(character.db, attr_name, {}) or {})


def _set_step_map(character, attr_name, data):
    setattr(character.db, attr_name, dict(data or {}))
    return dict(getattr(character.db, attr_name, {}) or {})


def _article_for(value):
    raw = str(value or "").strip()
    if not raw:
        return raw
    article = "an" if raw[0].lower() in "aeiou" else "a"
    return f"{article} {raw}"


def _get_step_interactions(character, step=None):
    current_step = str(step or _current_step(character)).strip().lower()
    return int(_get_step_map(character, "chargen_step_interactions").get(current_step, 0) or 0)


def _increment_step_interactions(character, step=None):
    current_step = str(step or _current_step(character)).strip().lower()
    data = _get_step_map(character, "chargen_step_interactions")
    data[current_step] = int(data.get(current_step, 0) or 0) + 1
    _set_step_map(character, "chargen_step_interactions", data)
    return int(data[current_step] or 0)


def _next_variant_line(character, table, *, step=None, **format_kwargs):
    current_step = str(step or _current_step(character)).strip().lower()
    variants = tuple((table.get(current_step) or ()))
    if not variants:
        return ""
    counts = _get_step_map(character, "chargen_variant_counts")
    counter_key = f"{current_step}:{id(table)}"
    index = int(counts.get(counter_key, 0) or 0) % len(variants)
    counts[counter_key] = int(index + 1)
    _set_step_map(character, "chargen_variant_counts", counts)
    return str(variants[index]).format(**format_kwargs)


def _mirror_instruction(character, *, step=None):
    current_step = str(step or _current_step(character)).strip().lower()
    if _get_step_interactions(character, current_step) > 0:
        return ""
    if current_step == "race":
        return "Touch it if you want it to change."
    return "Touch it if you want it to change."


def _next_transition_line(character):
    counts = _get_step_map(character, "chargen_variant_counts")
    counter_key = "transition:guide"
    index = int(counts.get(counter_key, 0) or 0) % len(NEXT_STEP_GUIDE_LINES)
    counts[counter_key] = int(index + 1)
    _set_step_map(character, "chargen_variant_counts", counts)
    return str(NEXT_STEP_GUIDE_LINES[index] or "")


def emit_step_prompt(character, *, force=False):
    if not is_chargen_active(character):
        return False
    step = _current_step(character)
    prompted = list(getattr(character.db, "chargen_prompted_steps", []) or [])
    if not force and step in prompted:
        return False
    guide_name = _speaker_name(character, GUIDE_KEY)
    gremlin_name = _speaker_name(character, GREMLIN_KEY)
    for line in GUIDE_STEP_LINES[step]:
        _msg_line(character, guide_name, line)
    gremlin_steps = list(getattr(character.db, "chargen_gremlin_steps", []) or [])
    gremlin_line = GREMLIN_STEP_LINES.get(step)
    if gremlin_line and step not in gremlin_steps:
        _msg_line(character, gremlin_name, gremlin_line)
        gremlin_steps.append(step)
        character.db.chargen_gremlin_steps = gremlin_steps
    prompted.append(step)
    character.db.chargen_prompted_steps = prompted
    character.db.chargen_last_interaction_at = time.time()
    return True


def maybe_nudge_if_idle(character, *, idle_threshold=6.0, minimum_interval=8.0):
    if not is_chargen_active(character):
        return False
    now = time.time()
    last_interaction = float(getattr(character.db, "chargen_last_interaction_at", 0.0) or 0.0)
    last_nudge = float(getattr(character.db, "chargen_last_nudge_at", 0.0) or 0.0)
    if now - last_interaction < idle_threshold:
        return False
    if now - last_nudge < minimum_interval:
        return False
    guide_name = _speaker_name(character, GUIDE_KEY)
    _msg_line(character, guide_name, GUIDE_IDLE_LINES[_current_step(character)])
    character.db.chargen_last_nudge_at = now
    return True


def render_mirror(character):
    if _is_confirm_mode(character):
        return f"{FINALIZE_WARNING}\n\n{FINALIZE_WARNING_FOLLOWUP}"
    if _is_review_mode(character):
        selections = dict(getattr(character.db, "chargen_selections", {}) or {})
        lines = [
            "The mirror holds what you've made of it.",
            "",
        ]
        for step in CHARGEN_STEPS:
            lines.append(f"{STEP_LABELS[step].title()}: {str(selections.get(step, _current_value_for_step(character, step))).capitalize()}")
        lines.extend(["", "Back if it isn't yours yet."])
        return "\n".join(lines)
    step = _current_step(character)
    value = _current_value(character)
    lines = [
        _next_variant_line(character, STEP_LOOK_LINES, step=step, value=value, value_cap=str(value).capitalize()),
    ]
    instruction = _mirror_instruction(character, step=step)
    if instruction:
        lines.extend(["", instruction])
    return "\n".join(lines)


def cycle_current_option(character):
    if not is_chargen_active(character):
        return {"ok": False, "error": "Nothing in the glass answers you."}
    if _is_review_mode(character) or _is_confirm_mode(character):
        return {"ok": False, "error": "The mirror has stopped changing. Either go back or finish it."}
    step = _current_step(character)
    options = STEP_OPTIONS[step]
    next_index = (_current_index(character) + 1) % len(options)
    character.db.chargen_index = next_index
    character.db.chargen_last_interaction_at = time.time()
    value = _store_current_value(character, options[next_index])
    _increment_step_interactions(character, step)
    return {
        "ok": True,
        "message": _next_variant_line(character, STEP_TOUCH_LINES, step=step, value=value, article_value=_article_for(value)),
        "prompt": render_mirror(character),
    }


def move_between_steps(character, direction):
    if not is_chargen_active(character):
        return {"ok": False, "error": "Nothing answers that command."}
    normalized = str(direction or "").strip().lower()
    character.db.chargen_last_interaction_at = time.time()
    if _is_confirm_mode(character):
        return {"ok": False, "error": "Confirm it or cancel it first."}
    if _is_review_mode(character):
        _set_review_mode(character, False)
    if normalized == "back":
        previous_step = _rewind_step(character)
        if not previous_step:
            return {"ok": False, "error": "There is nowhere earlier to return to."}
        _unmark_locked(character, previous_step)
        return {
            "ok": True,
            "message": "The mirror gives the last choice back.",
            "step": previous_step,
            "prompt": render_mirror(character),
        }
    if normalized == "next":
        next_step = _advance_step(character)
        if not next_step:
            _set_review_mode(character, True)
            return {
                "ok": True,
                "message": "The mirror stops changing and waits for judgment.",
                "prompt": render_mirror(character),
            }
        return {
            "ok": True,
            "message": "You move on without settling it yet.",
            "step": next_step,
            "prompt": render_mirror(character),
        }
    return {"ok": False, "error": "That direction means nothing here."}


def lock_current_step(character, command_name):
    if not is_chargen_active(character):
        return {"ok": False, "error": "Nothing answers that command."}
    if _is_review_mode(character) or _is_confirm_mode(character):
        return {"ok": False, "error": "That choice has already been set aside. Finish it or go back."}
    step = _current_step(character)
    normalized = str(command_name or "").strip().lower()
    if normalized not in {"accept", "accept reflection", "done"}:
        return {"ok": False, "error": "Set it first."}

    value = _store_current_value(character)
    _mark_locked(character, step)
    character.db.chargen_last_interaction_at = time.time()

    if step == CHARGEN_STEPS[-1]:
        _set_review_mode(character, True)
        return {
            "ok": True,
            "message": STEP_LOCK_LINES.get(step, f"{value.capitalize()} remains."),
            "prompt": render_mirror(character),
        }

    next_step = _advance_step(character)
    guide_name = _speaker_name(character, GUIDE_KEY)
    transition_line = _next_transition_line(character)
    if transition_line:
        _msg_line(character, guide_name, transition_line)
    emit_step_prompt(character, force=True)
    return {
        "ok": True,
        "message": STEP_LOCK_LINES.get(step, f"{value.capitalize()} holds."),
        "step": next_step,
        "prompt": render_mirror(character),
    }


def begin_finalize(character):
    if not is_chargen_active(character):
        return {"ok": False, "error": "Nothing answers that command."}
    if _is_confirm_mode(character):
        return {"ok": False, "error": "The mirror is already waiting for your answer."}
    if not _is_review_mode(character):
        return {"ok": False, "error": "Not yet. Set the reflection first."}
    _set_confirm_mode(character, True)
    character.db.chargen_last_interaction_at = time.time()
    return {
        "ok": True,
        "message": "The mirror waits for the last word.",
        "prompt": render_mirror(character),
    }


def cancel_finalize(character):
    if not is_chargen_active(character):
        return {"ok": False, "error": "Nothing answers that command."}
    if not _is_confirm_mode(character):
        return {"ok": False, "error": "There is nothing to cancel."}
    _set_confirm_mode(character, False)
    _set_review_mode(character, True)
    character.db.chargen_last_interaction_at = time.time()
    return {
        "ok": True,
        "message": "The mirror waits. It has not closed around the choice yet.",
        "prompt": render_mirror(character),
    }


def confirm_finalize(character):
    if not is_chargen_active(character):
        return {"ok": False, "error": "Nothing answers that command."}
    if not _is_confirm_mode(character):
        return {"ok": False, "error": "The mirror has not asked for that yet."}
    value = _store_current_value(character, _current_value_for_step(character, CHARGEN_STEPS[-1]))
    _apply_final_identity(character)
    character.db.chargen_finalized = True
    guide_name = _speaker_name(character, GUIDE_KEY)
    for line in FINAL_GUIDE_LINES:
        _msg_line(character, guide_name, line)
    _clear_chargen_flags(character)
    from systems import onboarding

    onboarding.start_onboarding(character)
    return {"ok": True, "complete": True, "message": f"The mirror dulls. {value.capitalize()} remains.", "character": character}


def begin_mirror_chargen(account, raw_name):
    existing = get_active_chargen_character(account)
    if existing:
        return {
            "ok": True,
            "character": existing,
            "message": "Your reflection is already waiting.",
        }

    name = str(raw_name or "").strip()
    ok, error = validate_name(name)
    if not ok:
        return {"ok": False, "error": error or "Choose a valid name."}

    reserved, reserve_error = reserve_name(name)
    if not reserved:
        return {"ok": False, "error": reserve_error or "That name is not available."}

    try:
        from server.conf.at_server_startstop import _ensure_new_player_tutorial

        room = _ensure_new_player_tutorial()
        blueprint = {
            "name": name,
            "race": DEFAULT_RACE,
            "gender": DEFAULT_GENDER,
            "profession": DEFAULT_PROFESSION,
            "stats": preview_race_stats(CHARGEN_BASE_STATS, DEFAULT_RACE),
            "description": "An unremarkable person.",
            "appearance": {},
            "identity": {"race": DEFAULT_RACE, "gender": DEFAULT_GENDER, "appearance": {}},
        }
        character, errors = create_character_from_blueprint(
            account,
            blueprint,
            allow_reserved_name=True,
            start_room=room,
            skip_post_create_setup=True,
            activate_onboarding=False,
        )
        if errors or not character:
            return {"ok": False, "error": "; ".join(errors or ["Character creation failed."])}
        release_name(name)
        initialize_chargen_character(character)
        emit_step_prompt(character, force=True)
        return {
            "ok": True,
            "character": character,
            "message": "The guide places the mirror in your hands without explanation.\n\nIt is heavier than it should be.",
        }
    except Exception as exc:
        release_name(name)
        return {"ok": False, "error": f"Character creation failed: {exc}"}


def initialize_chargen_character(character):
    character.db.chargen_active = True
    character.db.in_chargen = True
    character.db.onboarding_step = None
    character.db.onboarding_complete = False
    character.db.chargen_locked_steps = []
    character.db.chargen_prompted_steps = []
    character.db.chargen_gremlin_steps = []
    character.db.chargen_last_nudge_at = 0.0
    character.db.chargen_step_interactions = {}
    character.db.chargen_variant_counts = {}
    character.db.chargen_review_mode = False
    character.db.chargen_confirm_mode = False
    character.db.chargen_finalized = False
    _set_step(character, CHARGEN_STEPS[0])
    return character


def cancel_mirror_chargen(account, session=None):
    character = get_active_chargen_character(account)
    if not character:
        return {"ok": False, "error": "No active character creation session."}
    try:
        if session and account.get_puppet(session) == character:
            account.unpuppet_object(session)
    except Exception:
        pass
    name = str(getattr(character, "key", "") or "").strip()
    character.delete()
    release_name(name)
    return {"ok": True, "message": "The mirror goes dark."}


def gate_chargen_input(character, raw_string):
    if not is_chargen_active(character):
        return raw_string, None
    raw = str(raw_string or "").strip()
    lowered = raw.lower()
    if not lowered:
        return None, BLOCKED_INPUT_MESSAGE
    if lowered in _allowed_free_commands():
        return raw_string, None
    if lowered.startswith("__clickmove__") or _is_movement_command(character, lowered):
        character.db.chargen_last_interaction_at = time.time()
        return None, MOVEMENT_BLOCKED_MESSAGE
    character.db.chargen_last_interaction_at = time.time()
    return None, BLOCKED_INPUT_MESSAGE
