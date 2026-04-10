import time
from collections.abc import Mapping

from evennia.objects.models import ObjectDB
from evennia.utils import delay
from evennia.utils.create import create_object


STEP_START = "start"
STEP_MOVEMENT = "movement"
STEP_POSSESSION = "possession"
STEP_PREPARATION = "preparation"
STEP_COMBAT = "combat"
STEP_ESCALATION = "escalation"
STEP_COLLAPSE = "collapse"
STEP_TRANSPORT = "transport"
STEP_LEARNING = "learning"
STEP_FAILURE = "failure"
STEP_RECOVERY = "recovery"
STEP_DEPART = "depart"
STEP_COMPLETE = "complete"

ONBOARDING_STEPS = (
    STEP_START,
    STEP_MOVEMENT,
    STEP_POSSESSION,
    STEP_PREPARATION,
    STEP_COMBAT,
    STEP_ESCALATION,
    STEP_COLLAPSE,
    STEP_TRANSPORT,
    STEP_LEARNING,
    STEP_FAILURE,
    STEP_RECOVERY,
    STEP_DEPART,
    STEP_COMPLETE,
)

INTAKE_CHAMBER = "Intake Chamber"
TRAINING_HALL = "Training Hall"
PRACTICE_YARD = "Practice Yard"
ONBOARDING_ROOM_NAMES = {INTAKE_CHAMBER, TRAINING_HALL, PRACTICE_YARD}
EMPATH_GUILD_ROOM = "Empath Guild"
EMPATH_GUILD_INTERIOR_ENTRY_ROOM = "Empath Guild, Entry Hall"
EMPATH_GUILD_ENTRY_ROOM = "Larkspur Lane, Midway"
EMPATH_GUILD_ENTRY_DBREF = 4280
RECOVERY_FALLBACK_ROOM = "Outer Yard"

TRAINING_SWORD_KEY = "training sword"
TRAINING_VEST_KEY = "training vest"
GUIDE_KEY = "Intake Guide"
TRIAGE_EMPATH_KEY = "Triage Empath"
WARD_CLERIC_KEY = "Ward Cleric"

BLOCKED_COMMAND_MESSAGE = "Not yet. Try what's in front of you."
EARLY_BLOCKED_COMMAND_MESSAGE = "Not yet. Start by moving east."
INVALID_COMMAND_MESSAGE = "Not that. Try what's in front of you."

MOVEMENT_COMMANDS = {
    "north",
    "south",
    "east",
    "west",
    "n",
    "s",
    "e",
    "w",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "ne",
    "nw",
    "se",
    "sw",
    "up",
    "down",
    "u",
    "d",
    "out",
    "leave",
}
STEP_ALLOWED_COMMANDS = {
    STEP_START: set(MOVEMENT_COMMANDS),
    STEP_MOVEMENT: set(MOVEMENT_COMMANDS) | {"get", "grab", "take"},
    STEP_PREPARATION: set(MOVEMENT_COMMANDS) | {"get", "grab", "take", "inventory", "inv", "i", "wear", "wea", "wield", "wie", "equip"},
    STEP_COMBAT: set(MOVEMENT_COMMANDS) | {"attack", "att", "hit", "kill", "slice", "bash", "jab"},
    STEP_ESCALATION: {"attack", "att", "hit", "kill", "slice", "bash", "jab"},
    STEP_LEARNING: set(MOVEMENT_COMMANDS) | {"experience", "exp"},
    STEP_RECOVERY: set(MOVEMENT_COMMANDS) | {"stats", "health", "hp", "sta", "score"},
    STEP_DEPART: set(MOVEMENT_COMMANDS) | {"depart"},
}

STATE_DIALOGUE = {
    STEP_START: (
        ("speech", "You're awake. Good."),
        ("text", "A brief glance toward the archway."),
        ("speech", "Start moving."),
    ),
    STEP_MOVEMENT: (
        ("text", "Weapons line the walls. Nothing polished. Nothing ceremonial.\n\nEverything here has been used."),
        ("speech", "Take something."),
    ),
    STEP_PREPARATION: (
        ("speech", "Good enough."),
        ("speech", "Move."),
    ),
    STEP_COMBAT: (
        ("text", "The yard is already in motion.\n\nSteel. Movement. Voices overlapping.\n\nThis isn't for you.\n\nIt doesn't matter."),
        ("speech", "Don't think. Strike."),
    ),
    STEP_ESCALATION: (
        ("text", "Something changes.\n\nNot louder. Heavier."),
        ("text", "A body hits the ground hard enough to be felt.\n\nThen another."),
        ("text", "The goblin steps through the far side of the yard, larger than the rest, armored in pieces that do not match."),
        ("speech", "...move."),
    ),
    "combat_complete": (
        ("speech", "There it is."),
        ("speech", "Enough."),
    ),
    STEP_COMPLETE: (
        ("speech", "You can stand."),
        ("speech", "Go on."),
    ),
}

IDLE_ESCALATIONS = {
    STEP_START: (
        'The guide\'s eyes settle on the archway.\n\n"Now."',
        'A low note carries through the stone--distant, but not harmless.\n\n"If you\'re still here when it arrives--"\n\nA brief pause.\n\n"Move."',
    ),
    STEP_MOVEMENT: (
        'The guide glances at you, then at the rack.\n\n"Don\'t hesitate."',
        'A sound cuts through the space.\n\nDistant at first--then sharper.\n\nBells.',
        'The guide doesn\'t look at you this time.\n\n"If you\'re standing there when it reaches you--"\n\nA brief pause.\n\n"It won\'t matter what you meant to do."',
    ),
    STEP_PREPARATION: (
        'The guide glances at what you\'re holding.\n\n"Good enough."',
        'The guide\'s eyes flick toward the yard entrance.\n\n"Move."',
        'The space ahead is quiet in the wrong way.\n\n"If you\'re still fumbling when it starts--"\n\nA slight shake of the head.\n\n"You won\'t have time to fix it."',
    ),
    STEP_COMBAT: (
        'A shout cuts across the space ahead.\n\nNot instruction. Warning.',
    ),
    STEP_ESCALATION: (
        'The bow comes up already drawn.\n\nIf you move now, you are late.',
    ),
    STEP_RECOVERY: (
        'Pain settles back into your limbs.\n\n(Type stats.)',
    ),
}

SWORD_PICKUP_MESSAGE = "The weight settles into your hand.\n\nNot balanced. Not comfortable.\n\nReal."
INVENTORY_HINT = "The guide gives the weapon a short glance and dismisses the rest of your uncertainty."
EQUIP_COMPLETION_MESSAGE = "The fit is rough, but it settles into place."
COMBAT_TRANSITION_LINE = "A shout cuts across the space ahead.\n\nNot instruction. Warning."
COMBAT_FEEDBACK = (
    "One breaks from the edge of the chaos, smaller and faster, already coming at you.\n\n"
    "Your strike lands--not clean, not perfect--but enough.\n\n"
    "The goblin collapses hard and stays there.\n\n"
    "The yard barely notices."
)
ESCALATION_FEEDBACK = "A guard rushes the larger goblin and is thrown aside like it meant nothing. Another tries to flank and never gets close."
ESCALATION_OBJECTIVE = "Attack the goblin."
COLLAPSE_LINE = 'A thought--distant, thin:\n\n"That was... real."'
BETWEEN_STATE_INTRO = (
    "You are still there.\n\n"
    "Not standing. Not breathing.\n\n"
    "But not gone."
)
BETWEEN_STATE_OBSERVER = "You can see them.\n\nAnd they cannot see you."
RECOVERY_PROMPT = "(Type stats.)"
DEPART_PROMPT = "(Type depart if needed.)"
RECOVERY_HP_RATIO = 0.55
IGNORE_INPUT_COMMAND = "__onboarding_ignore__"
CLERIC_KEY = "Old Cleric"
EMPATH_KEY = "Old Empath"
BETWEEN_SEQUENCE_BEATS = (
    (0.45, "voices"),
    (1.1, "cleric"),
    (1.8, "empath"),
    (2.7, "work"),
    (3.65, "pull"),
    (4.55, "return"),
    (5.45, "body"),
)
TRANSPORT_SEQUENCE_BEATS = (
    (0.45, "empath_hold"),
    (0.95, "cleric_clear"),
    (1.55, "lunar_arrival"),
    (2.15, "instruction"),
    (2.85, "gate"),
    (3.55, "transition"),
    (4.1, "move"),
    (4.55, "arrival"),
    (5.15, "final"),
)


def _room_key(room):
    return str(getattr(room, "key", "") or "")


def _gender_value(character):
    identity = getattr(getattr(character, "db", None), "identity", None) or {}
    if isinstance(identity, Mapping):
        gender = str(identity.get("gender", "") or "").strip().lower()
        if gender:
            return gender
    return str(getattr(getattr(character, "db", None), "gender", "") or "").strip().lower()


def _pronouns(character):
    gender = _gender_value(character)
    if gender in {"male", "man", "masculine"}:
        return {"subject": "he", "object": "him", "possessive": "his"}
    if gender in {"female", "woman", "feminine"}:
        return {"subject": "she", "object": "her", "possessive": "her"}
    return {"subject": "they", "object": "them", "possessive": "their"}


def _update_state(character, **updates):
    state = ensure_onboarding_state(character)
    state.update(updates)
    character.db.onboarding_state = state
    return state


def _schedule_pending_scene(character, scene_name, delay_seconds, token):
    return _update_state(
        character,
        pending_scene=str(scene_name or ""),
        pending_scene_at=time.time() + max(0.0, float(delay_seconds or 0.0)),
        scene_token=int(token or 0),
    )


def _clear_pending_scene(character):
    return _update_state(character, pending_scene="", pending_scene_at=0.0)


def _new_scene_token(character):
    token = int(time.time() * 1000)
    _update_state(character, scene_token=token)
    return token


def _scene_token_matches(character, token):
    if not character or not getattr(character, "pk", None):
        return False
    state = ensure_onboarding_state(character)
    return int(state.get("scene_token", 0) or 0) == int(token or 0)


def _queue_pending_scene(character, scene_name, delay_seconds, token):
    _schedule_pending_scene(character, scene_name, delay_seconds, token)
    delay(max(0.05, float(delay_seconds or 0.0)), _process_pending_scene, character)
    return True


def _is_training_dummy(target):
    if not target:
        return False
    if bool(getattr(getattr(target, "db", None), "is_training_dummy", False)):
        return True
    role = str(getattr(getattr(target, "db", None), "onboarding_enemy_role", "") or "").strip().lower()
    return role in {"training", "dummy", "training_dummy"}


def _is_training_goblin(target):
    if not target:
        return False
    role = str(getattr(getattr(target, "db", None), "onboarding_enemy_role", "") or "").strip().lower()
    return role == "training_goblin" or str(getattr(target, "key", "") or "").strip().lower() == "training goblin"


def _cleanup_room_training_goblins(room):
    if not room:
        return 0
    removed = 0
    for obj in list(getattr(room, "contents", []) or []):
        if not _is_training_goblin(obj):
            continue
        try:
            obj.delete()
            removed += 1
        except Exception:
            pass
    return removed


def _find_room_by_key(room_key):
    if not room_key:
        return None
    return ObjectDB.objects.filter(db_key__iexact=str(room_key)).first()


def _find_room_by_tag(tag_key):
    if not tag_key:
        return None
    for room in ObjectDB.objects.filter(db_typeclass_path="typeclasses.rooms.Room"):
        try:
            if room.tags.has(str(tag_key)):
                return room
        except Exception:
            continue
    return None


def _find_room_by_dbref(dbref):
    try:
        return ObjectDB.objects.get_id(int(dbref or 0))
    except Exception:
        return None


def _recovery_room_fallback():
    return _find_room_by_key(RECOVERY_FALLBACK_ROOM)


def _resolve_recovery_destination():
    guild_room = _resolve_empath_guild_room()
    if guild_room:
        return guild_room
    destination = _find_room_by_dbref(EMPATH_GUILD_ENTRY_DBREF)
    if destination and str(getattr(destination, "key", "") or "") == EMPATH_GUILD_ENTRY_ROOM:
        return destination
    destination = _find_room_by_key(EMPATH_GUILD_ENTRY_ROOM)
    if destination:
        return destination
    return _recovery_room_fallback()


def _resolve_empath_guild_room():
    try:
        from world.areas.crossing.empath_guild import ensure_crossing_empath_guildhall

        ensure_crossing_empath_guildhall()
    except Exception:
        pass
    tagged_room = _find_room_by_tag("guild_empath")
    if tagged_room:
        return tagged_room
    lane_room = _find_room_by_dbref(EMPATH_GUILD_ENTRY_DBREF)
    if lane_room:
        for exit_obj in list(getattr(lane_room, "exits", []) or []):
            key = str(getattr(exit_obj, "key", "") or "").strip().lower()
            aliases = {str(alias or "").strip().lower() for alias in getattr(getattr(exit_obj, "aliases", None), "all", lambda: [])()}
            if key not in {"guild", "north"} and "guild" not in aliases:
                continue
            destination = getattr(exit_obj, "destination", None)
            if destination and str(getattr(getattr(destination, "db", None), "empath_guild_room", "") or "").strip().lower() == "main_hall":
                return destination
    return _find_room_by_key(EMPATH_GUILD_ROOM)


def _ensure_recovery_staff(room):
    if not room:
        return []
    staff_specs = (
        (
            TRIAGE_EMPATH_KEY,
            "An empath works close to the bedspace with precise, economical movements, attention fixed on triage rather than conversation.",
            ["empath", "triage empath"],
        ),
        (
            WARD_CLERIC_KEY,
            "A cleric remains near the far wall with the stillness of someone listening for changes that matter more than words.",
            ["cleric", "ward cleric"],
        ),
    )
    present = []
    for key, desc, aliases in staff_specs:
        npc = ObjectDB.objects.filter(db_key__iexact=key, db_location=room).first()
        if not npc:
            npc = create_object("typeclasses.npcs.NPC", key=key, location=room, home=room)
        npc.db.is_npc = True
        npc.db.desc = desc
        npc.db.is_onboarding_staff = True
        for alias in aliases:
            npc.aliases.add(alias)
        present.append(npc)
    return present


def _find_scripted_enemy(character):
    state = ensure_onboarding_state(character)
    enemy_id = int(state.get("scripted_enemy_id", 0) or 0)
    if enemy_id > 0:
        enemy = ObjectDB.objects.filter(id=enemy_id).first()
        if enemy:
            return enemy
    room = getattr(character, "location", None)
    if not room:
        return None
    for obj in list(getattr(room, "contents", []) or []):
        if _is_training_goblin(obj):
            return obj
    return None


def _cleanup_scripted_enemy(character):
    enemy = _find_scripted_enemy(character)
    if enemy:
        try:
            _clear_combat_state(character, enemy)
        except Exception:
            pass
        try:
            enemy.delete()
        except Exception:
            pass
    _update_state(character, scripted_enemy_id=0)
    return True


def _spawn_training_goblin(character):
    room = getattr(character, "location", None)
    if not room:
        return None
    goblin = _find_scripted_enemy(character)
    if not goblin:
        goblin = create_object("typeclasses.npcs.NPC", key="training goblin", location=room, home=room)
    elif getattr(goblin, "location", None) != room:
        goblin.move_to(room, quiet=True, use_destination=False)
    goblin.db.desc = "A larger goblin moves through the yard like everything else is in the way, bow already in hand beneath armor that does not match from piece to piece."
    goblin.db.is_npc = True
    goblin.db.is_tutorial_enemy = True
    goblin.db.onboarding_enemy_role = "training_goblin"
    goblin.db.hp = 18
    goblin.db.max_hp = 18
    goblin.db.balance = 80
    goblin.db.max_balance = 80
    goblin.db.fatigue = 0
    goblin.db.in_combat = False
    goblin.db.target = None
    goblin.aliases.add("goblin")
    _update_state(character, scripted_enemy_id=int(getattr(goblin, "id", 0) or 0))
    return goblin


def _set_scripted_resources(character, *, hp_ratio=None, balance_ratio=None, fatigue_ratio=None):
    if hasattr(character, "ensure_core_defaults"):
        character.ensure_core_defaults()
    if hp_ratio is not None and hasattr(character, "set_hp"):
        max_hp = max(1, int(getattr(character.db, "max_hp", 1) or 1))
        character.set_hp(max(1, int(round(max_hp * float(hp_ratio)))))
    if balance_ratio is not None and hasattr(character, "set_balance"):
        max_balance = max(1, int(getattr(character.db, "max_balance", 1) or 1))
        character.set_balance(max(0, int(round(max_balance * float(balance_ratio)))))
    if fatigue_ratio is not None and hasattr(character, "set_fatigue"):
        max_fatigue = max(1, int(getattr(character.db, "max_fatigue", 1) or 1))
        character.set_fatigue(max(0, int(round(max_fatigue * float(fatigue_ratio)))))


def _clear_scripted_wounds(character):
    wounds = dict(getattr(character.db, "wounds", None) or {})
    if wounds:
        for key in list(wounds.keys()):
            wounds[key] = 0
        character.db.wounds = wounds
    injuries = getattr(character.db, "injuries", None)
    if isinstance(injuries, Mapping):
        cleaned = {}
        for part_name, payload in dict(injuries).items():
            part_data = dict(payload or {})
            part_data["bleed"] = 0
            part_data["internal"] = 0
            part_data["external"] = 0
            cleaned[part_name] = part_data
        character.db.injuries = cleaned


def _set_between_state(character, active):
    character.db.training_between = bool(active)
    return bool(character.db.training_between)


def _set_training_collapse(character, active):
    character.db.training_collapse = bool(active)
    return bool(character.db.training_collapse)


def _emit_between_beat(character, beat_name):
    if not character:
        return False
    pronouns = _pronouns(character)
    if beat_name == "voices":
        emit_named_line(character, CLERIC_KEY, f"Hold {pronouns['object']}.")
        emit_named_line(character, EMPATH_KEY, f"I have {pronouns['object']}.")
        return True
    if beat_name == "cleric":
        emit_named_line(character, CLERIC_KEY, "The spirit's slipping.")
        emit_text(character, "")
        emit_named_line(character, CLERIC_KEY, "Not yet.")
        return True
    if beat_name == "empath":
        emit_text(character, "Hands--or something like hands--press against what you no longer feel.")
        return True
    if beat_name == "work":
        emit_named_line(character, EMPATH_KEY, "I'm taking the deeper damage.")
        emit_named_line(character, CLERIC_KEY, "Be quick.")
        emit_text(character, "Pressure--\n\nthen absence--\n\nthen something pulling you back toward a shape you remember.")
        return True
    if beat_name == "pull":
        emit_text(character, "The pull does not ask you whether you are ready.")
        return True
    if beat_name == "return":
        emit_named_line(character, CLERIC_KEY, "Now.")
        emit_text(character, "Light--sharp, brief--\n\nand then--")
        return True
    if beat_name == "body":
        _cleanup_scripted_enemy(character)
        _set_scripted_resources(character, hp_ratio=RECOVERY_HP_RATIO, balance_ratio=0.5, fatigue_ratio=0.2)
        _clear_scripted_wounds(character)
        character.db.position = "sitting"
        _touch_progress(character)
        emit_text(character, "Breath returns like it was forced into you.\n\nNot gently.\n\nNot kindly.\n\nThe world follows after.")
        trigger_transport_sequence(character)
        return True
    return False


def _emit_transport_beat(character, beat_name):
    if not character:
        return False
    if beat_name == "empath_hold":
        emit_named_line(character, EMPATH_KEY, "They'll hold.")
        emit_named_line(character, EMPATH_KEY, "For now.")
        return True
    if beat_name == "cleric_clear":
        emit_named_line(character, CLERIC_KEY, "Then move them.")
        return True
    if beat_name == "lunar_arrival":
        emit_text(character, "The space beside you shifts--not opening, just no longer staying where it was.")
        return True
    if beat_name == "instruction":
        emit_text(character, "You feel it take you.\n\nNo step.\nNo motion.\nJust absence--")
        return True
    if beat_name == "gate":
        emit_text(character, "The world does not open. It simply stops being where you were.")
        return True
    if beat_name == "transition":
        emit_text(character, "No step.\n\nNo motion.\n\nAnd then--")
        return True
    if beat_name == "move":
        destination = _resolve_recovery_destination()
        if not destination:
            destination = _recovery_room_fallback()
        guild_room = _resolve_empath_guild_room()
        if guild_room:
            _ensure_recovery_staff(guild_room)
        if destination:
            character.move_to(destination, quiet=True, use_destination=False)
        return True
    if beat_name == "arrival":
        emit_text(character, "Stone beneath you.\n\nClean air. Linen. Low voices kept behind their teeth.\n\nYou are somewhere else.")
        return True
    if beat_name == "final":
        _clear_pending_scene(character)
        _set_between_state(character, False)
        _set_training_collapse(character, False)
        set_onboarding_step(character, STEP_COMPLETE)
        _touch_progress(character)
        try:
            from systems import aftermath

            aftermath.activate_new_player_state(character)
            aftermath.note_room_entry(character, getattr(character, "location", None))
        except Exception:
            pass
        return True
    return False


def _process_transport_sequence(character, *, force=False):
    if not character:
        return False
    state = ensure_onboarding_state(character)
    token = int(state.get("scene_token", 0) or 0)
    if not _scene_token_matches(character, token):
        return False
    started_at = float(state.get("transport_started_at", 0.0) or 0.0)
    if started_at <= 0:
        return False
    beat_index = int(state.get("transport_sequence_index", 0) or 0)
    now = time.time()
    progressed = False
    while beat_index < len(TRANSPORT_SEQUENCE_BEATS):
        beat_at, beat_name = TRANSPORT_SEQUENCE_BEATS[beat_index]
        if not force and now < started_at + float(beat_at):
            break
        _emit_transport_beat(character, beat_name)
        progressed = True
        beat_index += 1
        state = ensure_onboarding_state(character)
        state["transport_sequence_index"] = beat_index
        character.db.onboarding_state = state
    if beat_index >= len(TRANSPORT_SEQUENCE_BEATS):
        state = ensure_onboarding_state(character)
        if str(state.get("pending_scene", "") or "").strip().lower() == "transport_sequence":
            _clear_pending_scene(character)
        return progressed
    next_at = started_at + float(TRANSPORT_SEQUENCE_BEATS[beat_index][0])
    state = ensure_onboarding_state(character)
    state["transport_sequence_index"] = beat_index
    state["pending_scene"] = "transport_sequence"
    state["pending_scene_at"] = 0.0 if force else next_at
    character.db.onboarding_state = state
    if not force:
        delay(max(0.05, next_at - time.time()), _process_pending_scene, character)
    return progressed


def trigger_transport_sequence(character):
    if not character:
        return False
    token = _new_scene_token(character)
    set_onboarding_step(character, STEP_TRANSPORT)
    _update_state(character, transport_started_at=time.time(), transport_sequence_index=0)
    _queue_pending_scene(character, "transport_sequence", float(TRANSPORT_SEQUENCE_BEATS[0][0]), token)
    return True


def _process_between_sequence(character, *, force=False):
    if not character:
        return False
    state = ensure_onboarding_state(character)
    token = int(state.get("scene_token", 0) or 0)
    if not _scene_token_matches(character, token):
        return False
    started_at = float(state.get("between_started_at", 0.0) or 0.0)
    if started_at <= 0:
        return False
    beat_index = int(state.get("between_sequence_index", 0) or 0)
    now = time.time()
    progressed = False
    while beat_index < len(BETWEEN_SEQUENCE_BEATS):
        beat_at, beat_name = BETWEEN_SEQUENCE_BEATS[beat_index]
        if not force and now < started_at + float(beat_at):
            break
        _emit_between_beat(character, beat_name)
        progressed = True
        beat_index += 1
        state = ensure_onboarding_state(character)
        state["between_sequence_index"] = beat_index
        character.db.onboarding_state = state
    if beat_index >= len(BETWEEN_SEQUENCE_BEATS):
        state = ensure_onboarding_state(character)
        if str(state.get("pending_scene", "") or "").strip().lower() == "between_sequence":
            _clear_pending_scene(character)
        return progressed
    next_at = started_at + float(BETWEEN_SEQUENCE_BEATS[beat_index][0])
    state = ensure_onboarding_state(character)
    state["between_sequence_index"] = beat_index
    state["pending_scene"] = "between_sequence"
    state["pending_scene_at"] = 0.0 if force else next_at
    character.db.onboarding_state = state
    if not force:
        delay(max(0.05, next_at - time.time()), _process_pending_scene, character)
    return progressed


def _begin_escalation(character, target):
    if not character or get_onboarding_step(character) != STEP_COMBAT or not _is_training_dummy(target):
        return False
    goblin = _spawn_training_goblin(character)
    if not goblin:
        return False
    set_onboarding_step(character, STEP_ESCALATION)
    token = _new_scene_token(character)
    _update_state(character, combat_exchange_count=0, release_scheduled=False, stats_reviewed=False, depart_hint_shown=False)
    _touch_progress(character)
    emit_text(character, COMBAT_FEEDBACK)
    emit_text(character, ESCALATION_FEEDBACK)
    emit_npc_line(character, _find_room_guide(character) or GUIDE_KEY, "...move.")
    emit_state_dialogue(character, STEP_ESCALATION)
    if hasattr(character, "set_target"):
        character.set_target(goblin)
    if hasattr(goblin, "set_target"):
        goblin.set_target(character)
    character.db.in_combat = True
    goblin.db.in_combat = True
    _update_state(character, scene_token=token)
    return True


def _complete_depart_awareness(character, token):
    if not character or get_onboarding_step(character) != STEP_DEPART or not _scene_token_matches(character, token):
        return False
    _clear_pending_scene(character)
    emit_npc_line(character, _find_room_guide(character) or GUIDE_KEY, "You can stand. Go on.")
    return release_to_world(character)[0]


def _schedule_release(character):
    state = ensure_onboarding_state(character)
    if bool(state.get("release_scheduled", False)):
        return False
    token = _new_scene_token(character)
    _update_state(character, release_scheduled=True, depart_hint_shown=True)
    _queue_pending_scene(character, "release", 1.0, token)
    return True


def _trigger_controlled_loss(character, target):
    if not character:
        return False
    set_onboarding_step(character, STEP_COLLAPSE)
    token = _new_scene_token(character)
    _clear_combat_state(character, target)
    _set_scripted_resources(character, hp_ratio=0.08, balance_ratio=0.0, fatigue_ratio=0.75)
    character.db.position = "prone"
    _set_between_state(character, True)
    _set_training_collapse(character, True)
    _touch_progress(character)
    emit_text(character, "It doesn't rush you.\n\nIt doesn't need to.")
    emit_text(character, "The yard is already losing.")
    emit_text(character, "Then its eyes find you.")
    emit_text(character, "The bow comes up already drawn.\n\nYou understand--too late--that this is not a fight.")
    emit_text(character, "The arrow leaves before you can move.\n\nNo sound.\n\nJust impact.\n\nIt hits you in the chest hard enough to erase everything else.")
    emit_text(character, "The ground finds you.\n\nOr you find it.\n\nIt's unclear.")
    emit_text(character, "The noise fades first.\n\nThen the weight.\n\nThen everything else.")
    emit_text(character, COLLAPSE_LINE)
    emit_text(character, BETWEEN_STATE_INTRO)
    emit_text(character, BETWEEN_STATE_OBSERVER)
    _update_state(character, between_started_at=time.time(), between_sequence_index=0)
    _queue_pending_scene(character, "between_sequence", float(BETWEEN_SEQUENCE_BEATS[0][0]), token)
    return True


def _resolve_scripted_exchange(character, target):
    state = ensure_onboarding_state(character)
    exchange_count = int(state.get("combat_exchange_count", 0) or 0)
    if exchange_count <= 0:
        _touch_progress(character)
        emit_text(character, "You move first, but not fast enough.\n\nThe distance never closes the way you want it to.")
        _update_state(character, combat_exchange_count=1)
        return _trigger_controlled_loss(character, target)
    _update_state(character, combat_exchange_count=exchange_count + 1)
    return _trigger_controlled_loss(character, target)


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


def _completed_steps_for(step):
    order = {
        STEP_START: [],
        STEP_MOVEMENT: [STEP_MOVEMENT],
        STEP_POSSESSION: [STEP_MOVEMENT, STEP_POSSESSION],
        STEP_PREPARATION: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION],
        STEP_COMBAT: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT],
        STEP_ESCALATION: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_ESCALATION],
        STEP_COLLAPSE: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_ESCALATION, STEP_COLLAPSE],
        STEP_TRANSPORT: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_ESCALATION, STEP_COLLAPSE, STEP_TRANSPORT],
        STEP_LEARNING: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_LEARNING],
        STEP_FAILURE: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_LEARNING, STEP_FAILURE],
        STEP_RECOVERY: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_ESCALATION, STEP_COLLAPSE, STEP_RECOVERY],
        STEP_DEPART: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_ESCALATION, STEP_COLLAPSE, STEP_RECOVERY, STEP_DEPART],
        STEP_COMPLETE: [STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_ESCALATION, STEP_COLLAPSE, STEP_TRANSPORT, STEP_COMPLETE],
    }
    return list(order.get(str(step or "").strip().lower(), []))


def get_onboarding_step(character):
    if bool(getattr(getattr(character, "db", None), "chargen_active", False)):
        return None
    step = str(getattr(getattr(character, "db", None), "onboarding_step", "") or "").strip().lower()
    if step in ONBOARDING_STEPS:
        return step
    if bool(getattr(getattr(character, "db", None), "onboarding_complete", False)):
        return STEP_COMPLETE
    room = getattr(character, "location", None)
    if bool(getattr(getattr(room, "db", None), "is_onboarding", False)):
        return STEP_START
    return None


def set_onboarding_step(character, step):
    normalized = str(step or "").strip().lower()
    if normalized not in ONBOARDING_STEPS:
        normalized = STEP_START
    character.db.onboarding_step = normalized
    character.db.onboarding_complete = normalized == STEP_COMPLETE
    ensure_onboarding_state(character)
    return normalized


def activate_onboarding(character):
    if not character:
        return None
    return set_onboarding_step(character, STEP_START)


def start_onboarding(character):
    if not character:
        return None
    return activate_onboarding(character)


def ensure_onboarding_state(character):
    step = get_onboarding_step(character)
    active = step in {STEP_START, STEP_MOVEMENT, STEP_POSSESSION, STEP_PREPARATION, STEP_COMBAT, STEP_ESCALATION, STEP_COLLAPSE, STEP_TRANSPORT, STEP_LEARNING, STEP_FAILURE, STEP_RECOVERY, STEP_DEPART}
    state = getattr(getattr(character, "db", None), "onboarding_state", None)
    if not isinstance(state, Mapping):
        state = {}
    normalized = {
        "active": active,
        "complete": step == STEP_COMPLETE,
        "completed_steps": _completed_steps_for(step),
        "current_objective": get_onboarding_objective(character) if step else None,
        "last_progress_at": float(state.get("last_progress_at", 0.0) or 0.0),
        "room_entered_at": float(getattr(character.db, "onboarding_room_entered_at", 0.0) or 0.0),
        "visited_rooms": list(state.get("visited_rooms") or []),
        "inventory_checked": bool(state.get("inventory_checked", False)),
        "wore_training_gear": bool(state.get("wore_training_gear", False)),
        "wielded_training_weapon": bool(state.get("wielded_training_weapon", False)),
        "idle_prompt_step": str(state.get("idle_prompt_step", step or "") or step or ""),
        "idle_prompt_stage": int(state.get("idle_prompt_stage", 0) or 0),
        "combat_exchange_count": int(state.get("combat_exchange_count", 0) or 0),
        "scripted_enemy_id": int(state.get("scripted_enemy_id", 0) or 0),
        "scene_token": int(state.get("scene_token", 0) or 0),
        "stats_reviewed": bool(state.get("stats_reviewed", False)),
        "depart_hint_shown": bool(state.get("depart_hint_shown", False)),
        "release_scheduled": bool(state.get("release_scheduled", False)),
        "pending_scene": str(state.get("pending_scene", "") or ""),
        "pending_scene_at": float(state.get("pending_scene_at", 0.0) or 0.0),
        "between_started_at": float(state.get("between_started_at", 0.0) or 0.0),
        "between_sequence_index": int(state.get("between_sequence_index", 0) or 0),
        "transport_started_at": float(state.get("transport_started_at", 0.0) or 0.0),
        "transport_sequence_index": int(state.get("transport_sequence_index", 0) or 0),
    }
    character.db.onboarding_state = normalized
    return normalized


def is_in_onboarding(character):
    return get_onboarding_step(character) != STEP_COMPLETE and get_onboarding_step(character) is not None


def is_onboarding_character(character):
    if not character or bool(getattr(getattr(character, "db", None), "is_npc", False)):
        return False
    return is_in_onboarding(character)


def get_onboarding_objective(character):
    step = get_onboarding_step(character)
    if step == STEP_START:
        return "Move east."
    if step == STEP_MOVEMENT:
        return "Get the sword."
    if step == STEP_PREPARATION:
        return "Wear your gear and carry the sword properly."
    if step == STEP_COMBAT:
        return "Attack the dummy."
    if step == STEP_ESCALATION:
        return ESCALATION_OBJECTIVE
    if step == STEP_COLLAPSE:
        return "Hold on."
    if step == STEP_TRANSPORT:
        return "Hold still."
    if step == STEP_LEARNING:
        return "Review your experience."
    if step == STEP_RECOVERY:
        return "Check your condition."
    if step == STEP_DEPART:
        return "Remember how to return."
    if step == STEP_COMPLETE:
        return "Go on."
    return ""


def get_status_lines(character):
    step = get_onboarding_step(character)
    if not step:
        return ["You are not in onboarding."]
    return [f"Onboarding step: {step}", f"Objective: {get_onboarding_objective(character)}"]


def format_token_feedback(state):
    return ""


def _touch_progress(character):
    state = ensure_onboarding_state(character)
    state["last_progress_at"] = time.time()
    state["idle_prompt_step"] = get_onboarding_step(character) or ""
    state["idle_prompt_stage"] = 0
    character.db.onboarding_state = state
    return state


def _find_room_guide(character):
    room = getattr(character, "location", None)
    if not room:
        return None
    for obj in list(getattr(room, "contents", []) or []):
        if bool(getattr(getattr(obj, "db", None), "is_onboarding_guide", False)):
            return obj
    return None


def emit_text(character, text):
    if not character or not text:
        return False
    character.msg(str(text))
    if hasattr(character, "ndb"):
        character.ndb.onboarding_prompt_at = time.time()
    _remember_recent_line(character, text)
    return True


def emit_named_line(character, speaker, line, exclude=None):
    if not character or not speaker or not line:
        return False
    room = getattr(character, "location", None)
    text = f'{str(speaker)} says, "{str(line)}"'
    if room:
        room.msg_contents(text, exclude=exclude or [])
    else:
        character.msg(text)
    if hasattr(character, "ndb"):
        character.ndb.onboarding_prompt_at = time.time()
    _remember_recent_line(character, text)
    return True


def emit_npc_line(character, npc, line, exclude=None):
    speaker = str(getattr(npc, "key", GUIDE_KEY) or GUIDE_KEY)
    return emit_named_line(character, speaker, line, exclude=exclude)


def emit_state_dialogue(character, step=None):
    if not character:
        return False
    guide = _find_room_guide(character)
    dialogue = STATE_DIALOGUE.get(step or get_onboarding_step(character)) or ()
    if not dialogue:
        return False
    for entry_type, line in dialogue:
        if entry_type == "speech" and guide:
            emit_npc_line(character, guide, line)
            continue
        emit_text(character, line)
    return True


def get_room_prompt(character, room=None):
    step = get_onboarding_step(character)
    dialogue = STATE_DIALOGUE.get(step) or ()
    return dialogue[-1][1] if dialogue else None


def prompt_spacing_active(character, minimum_interval=2.5):
    last_prompt_at = float(getattr(getattr(character, "ndb", None), "onboarding_prompt_at", 0.0) or 0.0)
    return (time.time() - last_prompt_at) < float(minimum_interval or 0.0)


def emit_idle_nudge(character):
    step = get_onboarding_step(character)
    if not step:
        return False
    state = ensure_onboarding_state(character)
    step_key = str(state.get("idle_prompt_step", "") or "")
    if step_key != step:
        state["idle_prompt_step"] = step
        state["idle_prompt_stage"] = 0
        character.db.onboarding_state = state
    sequence = list(IDLE_ESCALATIONS.get(step) or [])
    if not sequence:
        return False
    stage = int(state.get("idle_prompt_stage", 0) or 0)
    if stage >= len(sequence):
        return False
    text = sequence[stage]
    state["idle_prompt_stage"] = stage + 1
    character.db.onboarding_state = state
    return emit_text(character, text)


def announce_objective(character, force=False):
    if not force and prompt_spacing_active(character, minimum_interval=5.0):
        return False
    return emit_idle_nudge(character)


def remind_objective_if_idle(character, idle_threshold=5.0, minimum_interval=5.0):
    if not is_in_onboarding(character):
        return False
    state = ensure_onboarding_state(character)
    now = time.time()
    last_progress = max(
        float(state.get("last_progress_at", 0.0) or 0.0),
        float(state.get("room_entered_at", 0.0) or 0.0),
    )
    if (now - last_progress) < float(idle_threshold or 0.0):
        return False
    if prompt_spacing_active(character, minimum_interval=minimum_interval):
        return False
    return emit_idle_nudge(character)


def get_roleplay_nudge(obj, character):
    return None


def trigger_gear_delay_scene(character):
    return False


def trigger_almost_failure_scene(character):
    return False


def note_hesitation(character, context=None):
    return emit_idle_nudge(character)


def note_step_failure(character, step):
    return emit_idle_nudge(character)


def _process_pending_scene(character, force=False):
    if not character or not is_in_onboarding(character):
        return False
    progressed = False
    while True:
        state = ensure_onboarding_state(character)
        scene_name = str(state.get("pending_scene", "") or "").strip().lower()
        scene_at = float(state.get("pending_scene_at", 0.0) or 0.0)
        token = int(state.get("scene_token", 0) or 0)
        if not scene_name:
            return progressed
        if not force and scene_at > 0 and time.time() < scene_at:
            return progressed
        if scene_name == "between_sequence":
            changed = _process_between_sequence(character, force=force)
        elif scene_name == "transport_sequence":
            changed = _process_transport_sequence(character, force=force)
        elif scene_name == "release":
            changed = _complete_depart_awareness(character, token)
        else:
            changed = False
        progressed = progressed or bool(changed)
        if not force:
            return progressed
        next_state = ensure_onboarding_state(character)
        if str(next_state.get("pending_scene", "") or "").strip().lower() == scene_name and not changed:
            return progressed


def remap_onboarding_input(character, raw_string):
    if not is_in_onboarding(character):
        return None, None
    _process_pending_scene(character)
    if not is_in_onboarding(character):
        return None, None
    if bool(getattr(getattr(character, "db", None), "training_between", False)):
        return IGNORE_INPUT_COMMAND, None
    raw = str(raw_string or "").strip()
    if not raw:
        return None, None
    parts = raw.split(None, 1)
    command_name = parts[0].lower()
    arguments = parts[1] if len(parts) > 1 else ""
    step = get_onboarding_step(character)

    if command_name == "take" and step in {STEP_MOVEMENT, STEP_PREPARATION}:
        return f"get {arguments}".strip(), None

    if command_name == "equip" and step == STEP_PREPARATION:
        lowered = arguments.strip().lower()
        if lowered in {"sword", "weapon", TRAINING_SWORD_KEY}:
            return f"wield {arguments}".strip(), None
        return f"wear {arguments}".strip() if arguments.strip() else "wear", None

    if command_name in set(STEP_ALLOWED_COMMANDS.get(step, set())):
        return None, None
    if step == STEP_START:
        return None, EARLY_BLOCKED_COMMAND_MESSAGE
    return None, BLOCKED_COMMAND_MESSAGE


def _is_training_sword(item):
    return str(getattr(item, "key", "") or "").strip().lower() == TRAINING_SWORD_KEY


def _is_training_gear(item):
    item_key = str(getattr(item, "key", "") or "").strip().lower()
    return bool(getattr(getattr(item, "db", None), "is_onboarding_training_gear", False)) or item_key == TRAINING_VEST_KEY


def get_pickup_block(character, obj):
    if not is_in_onboarding(character):
        return None
    step = get_onboarding_step(character)
    room_key = str(getattr(getattr(character, "location", None), "key", "") or "")
    if room_key != TRAINING_HALL:
        return INVALID_COMMAND_MESSAGE
    if step == STEP_MOVEMENT and _is_training_sword(obj):
        return None
    if step == STEP_PREPARATION and (_is_training_sword(obj) or _is_training_gear(obj)):
        return None
    return INVALID_COMMAND_MESSAGE


def get_attack_block(character, target):
    if not is_in_onboarding(character):
        return None
    step = get_onboarding_step(character)
    if step not in {STEP_COMBAT, STEP_ESCALATION}:
        return INVALID_COMMAND_MESSAGE
    if str(getattr(getattr(character, "location", None), "key", "") or "") != PRACTICE_YARD:
        return INVALID_COMMAND_MESSAGE
    if step == STEP_COMBAT and _is_training_dummy(target):
        return None
    if step == STEP_ESCALATION and _is_training_goblin(target):
        return None
    return INVALID_COMMAND_MESSAGE


def get_traverse_block(exit_obj, character, target_location):
    if not character or not is_in_onboarding(character):
        return None
    destination_key = str(getattr(target_location, "key", "") or "")
    step = get_onboarding_step(character)
    if step in {STEP_ESCALATION, STEP_COLLAPSE, STEP_TRANSPORT, STEP_RECOVERY, STEP_DEPART}:
        return INVALID_COMMAND_MESSAGE
    if destination_key not in ONBOARDING_ROOM_NAMES:
        if step != STEP_COMPLETE:
            return INVALID_COMMAND_MESSAGE
        return None
    if destination_key == TRAINING_HALL and step != STEP_START:
        return None
    if destination_key == PRACTICE_YARD and step not in {STEP_COMBAT, STEP_ESCALATION, STEP_COLLAPSE, STEP_LEARNING, STEP_FAILURE, STEP_RECOVERY, STEP_DEPART, STEP_COMPLETE}:
        return INVALID_COMMAND_MESSAGE
    if destination_key == INTAKE_CHAMBER:
        return INVALID_COMMAND_MESSAGE
    return None


def handle_room_entry(character):
    if not character:
        return
    if bool(getattr(getattr(character, "db", None), "chargen_active", False)):
        return
    room = getattr(character, "location", None)
    if not room or not bool(getattr(getattr(room, "db", None), "is_onboarding", False)):
        return
    if not get_onboarding_step(character):
        activate_onboarding(character)
    character.db.onboarding_room_entered_at = time.time()
    state = ensure_onboarding_state(character)
    room_key = str(getattr(room, "key", "") or "")
    visited = list(state.get("visited_rooms") or [])
    if room_key not in visited:
        visited.append(room_key)
        state["visited_rooms"] = visited
    character.db.onboarding_state = state
    if room_key == INTAKE_CHAMBER and get_onboarding_step(character) == STEP_START:
        _touch_progress(character)
        emit_state_dialogue(character, STEP_START)
        return
    if room_key == TRAINING_HALL and get_onboarding_step(character) == STEP_START:
        set_onboarding_step(character, STEP_MOVEMENT)
        _touch_progress(character)
        emit_state_dialogue(character, STEP_MOVEMENT)
        return
    if room_key == PRACTICE_YARD and get_onboarding_step(character) == STEP_COMBAT:
        _cleanup_room_training_goblins(room)
        _touch_progress(character)
        emit_state_dialogue(character, STEP_COMBAT)


def note_item_pickup(character, item):
    if not is_in_onboarding(character):
        return False, ""
    room_key = str(getattr(getattr(character, "location", None), "key", "") or "")
    if room_key != TRAINING_HALL:
        return False, ""
    if get_onboarding_step(character) == STEP_MOVEMENT and _is_training_sword(item):
        emit_text(character, SWORD_PICKUP_MESSAGE)
        emit_text(character, INVENTORY_HINT)
        set_onboarding_step(character, STEP_PREPARATION)
        state = ensure_onboarding_state(character)
        state["idle_prompt_step"] = STEP_PREPARATION
        state["idle_prompt_stage"] = 0
        character.db.onboarding_state = state
        _touch_progress(character)
        emit_state_dialogue(character, STEP_PREPARATION)
        return True, SWORD_PICKUP_MESSAGE
    if get_onboarding_step(character) == STEP_PREPARATION and _is_training_gear(item):
        _touch_progress(character)
    return False, ""


def note_inventory_action(character):
    if not is_in_onboarding(character):
        return False
    if get_onboarding_step(character) != STEP_PREPARATION:
        return False
    state = ensure_onboarding_state(character)
    state["inventory_checked"] = True
    state["idle_prompt_stage"] = max(1, int(state.get("idle_prompt_stage", 0) or 0))
    character.db.onboarding_state = state
    _touch_progress(character)
    return True


def _resolve_preparation_progress(character):
    state = ensure_onboarding_state(character)
    if not (state.get("wore_training_gear") and state.get("wielded_training_weapon")):
        return False, None
    if get_onboarding_step(character) != STEP_PREPARATION:
        return False, None
    set_onboarding_step(character, STEP_COMBAT)
    _touch_progress(character)
    message = f"{EQUIP_COMPLETION_MESSAGE}\n\n{COMBAT_TRANSITION_LINE}"
    if hasattr(character, "ndb"):
        character.ndb.onboarding_prompt_at = time.time()
    _remember_recent_line(character, message)
    return True, message


def note_equipment_action(character, item):
    if not is_in_onboarding(character):
        return False, None
    if get_onboarding_step(character) != STEP_PREPARATION:
        return False, None
    if not _is_training_gear(item):
        return False, None
    state = ensure_onboarding_state(character)
    state["wore_training_gear"] = True
    character.db.onboarding_state = state
    _touch_progress(character)
    return _resolve_preparation_progress(character)


def note_weapon_action(character, item):
    if not is_in_onboarding(character):
        return False, None
    if get_onboarding_step(character) != STEP_PREPARATION:
        return False, None
    if not _is_training_sword(item):
        return False, None
    state = ensure_onboarding_state(character)
    state["wielded_training_weapon"] = True
    character.db.onboarding_state = state
    _touch_progress(character)
    return _resolve_preparation_progress(character)


def is_training_enemy(target):
    if not target:
        return False
    return _is_training_dummy(target) or _is_training_goblin(target) or bool(getattr(getattr(target, "db", None), "is_tutorial_enemy", False))


def note_combat_start(character, target):
    if not is_in_onboarding(character) or not is_training_enemy(target):
        return False
    step = get_onboarding_step(character)
    if step == STEP_COMBAT:
        return _is_training_dummy(target)
    if step == STEP_ESCALATION:
        return _is_training_goblin(target)
    return False


def _clear_combat_state(character, target):
    if hasattr(character, "set_target"):
        character.set_target(None)
    if hasattr(target, "set_target"):
        target.set_target(None)
    character.db.in_combat = False
    target.db.in_combat = False


def note_combat_win(character, target):
    if not is_in_onboarding(character) or not is_training_enemy(target):
        return False, False
    if get_onboarding_step(character) == STEP_COMPLETE:
        return False, False
    if get_onboarding_step(character) == STEP_COMBAT and _is_training_dummy(target):
        return _begin_escalation(character, target), False
    return False, False


def resolve_training_attack(character, target):
    started = note_combat_start(character, target)
    if not started:
        return False
    step = get_onboarding_step(character)
    if step == STEP_COMBAT and _is_training_dummy(target):
        _begin_escalation(character, target)
        return True
    if step == STEP_ESCALATION and _is_training_goblin(target):
        _resolve_scripted_exchange(character, target)
        return True
    return True


def note_healing_action(character, patient=None, part=None):
    return False, False


def note_stats_action(character):
    if not is_in_onboarding(character):
        return False
    if get_onboarding_step(character) != STEP_RECOVERY:
        return False
    set_onboarding_step(character, STEP_DEPART)
    _touch_progress(character)
    _update_state(character, stats_reviewed=True)
    emit_named_line(character, "Old Cleric", "Hold.")
    emit_text(character, "A quick check. Efficient. Final.")
    emit_named_line(character, "Old Cleric", "You'll hold.")
    emit_text(character, "A glance toward the door.")
    emit_named_line(character, "Old Cleric", "If something's been left behind--take it.")
    emit_named_line(character, "Old Cleric", "No one else will.")
    emit_text(character, DEPART_PROMPT)
    _schedule_release(character)
    return True


def note_depart_action(character):
    if not is_in_onboarding(character):
        return False, None
    if get_onboarding_step(character) != STEP_DEPART:
        return False, None
    _schedule_release(character)
    return True, "You are breathing again. Remember the command for the next time death leaves you alone."


def note_trade_action(character, action):
    return False, False


def note_breach_progress(character, action):
    return False, False


def can_exit_to_world(character):
    if get_onboarding_step(character) == STEP_COMPLETE:
        return True, ""
    return False, INVALID_COMMAND_MESSAGE


def release_to_world(character):
    _cleanup_scripted_enemy(character)
    _set_between_state(character, False)
    _set_training_collapse(character, False)
    set_onboarding_step(character, STEP_COMPLETE)
    destination = _resolve_recovery_destination() or _recovery_room_fallback()
    if destination and getattr(character, "location", None) != destination:
        character.move_to(destination, quiet=True, use_destination=False)
    try:
        from systems import aftermath

        aftermath.activate_new_player_state(character)
        aftermath.note_room_entry(character, getattr(character, "location", None))
    except Exception:
        pass
    return True, ""


def set_gender(character, value):
    return False, "Gender is chosen during character creation now."


def select_race(character, value):
    return False, "Race is chosen during character creation now."


def set_trait(character, trait, value):
    return False, "Appearance is chosen during character creation now."


def set_final_name(character, value):
    return False, "Your name is already set. Keep moving."