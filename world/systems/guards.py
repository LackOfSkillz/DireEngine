import json
import random
import time
import warnings
from collections.abc import Mapping
from uuid import uuid4

from django.db import connection
from evennia.objects.models import ObjectDB
from evennia.utils import delay
from evennia.utils.create import create_object

from world.systems.justice import begin_arrest, can_be_arrested, complete_arrest, get_wanted_tier


GUARD_TEMPLATE_CACHE = []
ACTIVE_GUARDS = []

GUARD_MOVE_COOLDOWN = 20.0
GUARD_IDLE_MAX = 90.0
GUARD_CLUMP_EXIT_DELAY = 5.0
GUARD_RECENT_ROOM_LIMIT = 5
GUARD_PATROL_ZONE = "landing"
GUARD_TICK_INTERVAL = 20
GUARD_TARGET_MEMORY = 120.0
GUARD_WATCH_THRESHOLD = 2
GUARD_ARREST_THRESHOLD = 5
GUARD_WATCH_MESSAGE_COOLDOWN = 30.0
GUARD_SUSPICION_DECAY_INTERVAL = 30.0
GUARD_SHARED_SUSPICION_WATCH = 1
GUARD_SHARED_SUSPICION_ARREST = 2
GUARD_MAX_FOLLOW_STEPS = 2
GUARD_WARNING_COOLDOWN = 10.0
GUARD_CONFRONT_TIMEOUT = 30.0
REPEAT_OFFENDER_WARNING_THRESHOLD = 3
GUARD_DISPLAY_NAME = "Town Guard"


def get_valid_guard_templates(limit=15, refresh=False):
    global GUARD_TEMPLATE_CACHE

    if refresh or not GUARD_TEMPLATE_CACHE:
        GUARD_TEMPLATE_CACHE = _load_valid_guard_templates()

    templates = [dict(template) for template in GUARD_TEMPLATE_CACHE[: max(0, int(limit or 0))]]
    if len(templates) < int(limit or 0):
        warnings.warn(
            f"Only {len(templates)} validated guard templates were available; guard spawning will not substitute other NPC types.",
            RuntimeWarning,
        )
    return templates


def spawn_guards_in_landing(count=15):
    templates = get_valid_guard_templates(limit=count)
    candidate_rooms = _get_patrol_rooms_for_zone(GUARD_PATROL_ZONE)
    if not candidate_rooms:
        warnings.warn("No lawful landing rooms were available for guard patrols.", RuntimeWarning)
        return []

    shuffled_rooms = list(candidate_rooms)
    random.shuffle(shuffled_rooms)
    used_room_ids = set()
    spawned = []

    room_iter = iter(shuffled_rooms)
    for template in templates:
        room = None
        for candidate_room in room_iter:
            candidate_room_id = int(getattr(candidate_room, "id", 0) or 0)
            if candidate_room_id in used_room_ids:
                continue
            if bool(getattr(getattr(candidate_room, "db", None), "no_guard", False)):
                continue
            if _count_guards_in_room(candidate_room) > 0:
                continue
            room = candidate_room
            break
        if room is None:
            break
        if int(getattr(room, "id", 0) or 0) in used_room_ids:
            continue
        if bool(getattr(getattr(room, "db", None), "no_guard", False)):
            continue
        if _count_guards_in_room(room) > 0:
            continue
        guard = create_object(
            "typeclasses.npcs.GuardNPC",
            key=GUARD_DISPLAY_NAME,
            location=room,
            home=room,
        )
        _assign_template_to_guard(guard, template, room)
        spawned.append(guard)
        used_room_ids.add(int(getattr(room, "id", 0) or 0))
        ACTIVE_GUARDS.append(guard)
        if len(spawned) >= int(count or 0):
            break

    return list(spawned)


def ensure_landing_guards(count=15):
    desired_count = max(0, int(count or 0))
    if desired_count <= 0:
        return []

    candidate_rooms = {
        int(getattr(room, "id", 0) or 0)
        for room in _get_patrol_rooms_for_zone(GUARD_PATROL_ZONE)
        if getattr(room, "id", None)
    }
    if not candidate_rooms:
        warnings.warn("No lawful landing patrol rooms were available for guard bootstrap.", RuntimeWarning)
        return []

    existing_guards = []
    seen_ids = set()
    for guard in iter_active_guards():
        guard_id = int(getattr(guard, "id", 0) or 0)
        if guard_id <= 0 or guard_id in seen_ids:
            continue
        guard_room = getattr(guard, "location", None)
        guard_room_id = int(getattr(guard_room, "id", 0) or 0)
        guard_zone = str(getattr(getattr(guard, "db", None), "zone", "") or "").strip().lower()
        if guard_zone == GUARD_PATROL_ZONE or guard_room_id in candidate_rooms:
            _normalize_guard_identity(guard)
            existing_guards.append(guard)
            seen_ids.add(guard_id)
            if guard not in ACTIVE_GUARDS:
                ACTIVE_GUARDS.append(guard)

    if len(existing_guards) >= desired_count:
        return list(existing_guards)

    spawned = spawn_guards_in_landing(count=desired_count - len(existing_guards))
    return list(existing_guards) + list(spawned)


def guard_movement_tick(guard):
    if not _is_active_guard(guard):
        return False

    now = time.time()
    last_move_time = float(getattr(getattr(guard, "db", None), "last_move_time", 0.0) or 0.0)
    last_idle_time = float(getattr(getattr(guard, "db", None), "last_idle_time", 0.0) or 0.0)
    force_move = (now - last_idle_time) > GUARD_IDLE_MAX
    if not force_move and (now - last_move_time) < GUARD_MOVE_COOLDOWN:
        return False

    current_room = getattr(guard, "location", None)
    if current_room is None:
        return False

    _remember_recent_room(guard, current_room)
    exits = _get_valid_guard_exits(guard, current_room)
    if not exits:
        guard.db.last_idle_time = now
        return False

    selected_exit = _select_targeted_exit(guard, exits)
    used_targeted_follow = selected_exit is not None
    if selected_exit is None:
        selected_exit = _select_guard_exit(guard, exits, force_move=force_move)
    if selected_exit is None:
        guard.db.last_idle_time = now
        return False

    destination = getattr(selected_exit, "destination", None)
    if destination is None:
        guard.db.last_idle_time = now
        return False

    guard.db.previous_room_id = int(getattr(current_room, "id", 0) or 0)
    moved = guard.move_to(destination, quiet=True, move_type="patrol")
    if not moved:
        guard.db.last_idle_time = now
        return False

    _remember_recent_room(guard, destination)
    guard.db.last_move_time = now
    guard.db.last_idle_time = now
    if used_targeted_follow:
        remaining = max(0, int(getattr(getattr(guard, "db", None), "follow_steps_remaining", 0) or 0) - 1)
        guard.db.follow_steps_remaining = remaining
        if remaining <= 0:
            _clear_guard_target_state(guard)

    if _count_other_guards_in_room(guard, destination) > 0:
        _mark_clump_exit(guard, destination)
    return True


def handle_guard_room_entry(guard, source_location=None):
    if not _is_active_guard(guard):
        return
    _emit_guard_entry_message(guard)
    scan_room_for_suspicion(guard)
    current_room = getattr(guard, "location", None)
    if current_room and _count_guards_in_room(current_room) > 1:
        _mark_clump_exit(guard, current_room)


def scan_room_for_suspicion(guard):
    if not _is_active_guard(guard):
        return {}

    room = getattr(guard, "location", None)
    if room is None:
        return {}

    now = time.time()
    room_id = int(getattr(room, "id", 0) or 0)
    updated = {
        str(key): _normalize_suspicion_state(value)
        for key, value in dict(getattr(getattr(guard, "db", None), "suspicion_targets", None) or {}).items()
    }
    updated = decay_suspicion(guard, suspicion_targets=updated, now=now, persist=False)
    strongest_target = None
    for occupant in list(getattr(room, "contents", None) or []):
        if occupant == guard:
            continue
        if bool(getattr(getattr(occupant, "db", None), "is_guard", False)):
            continue
        if bool(getattr(getattr(occupant, "db", None), "is_npc", False)):
            continue
        if not getattr(occupant, "id", None):
            continue

        key = str(occupant.id)
        suspicion_state = _normalize_suspicion_state(updated.get(key))
        suspicion = int(suspicion_state.get("score", 0) or 0)
        repeat_pressure = _get_repeat_offender_pressure(occupant)
        hidden_detected = False
        evidence = 0
        if hasattr(occupant, "is_hidden") and occupant.is_hidden():
            hidden_detected = bool(hasattr(guard, "can_perceive") and guard.can_perceive(occupant))
            if hidden_detected:
                evidence += 1
        wanted_tier = get_wanted_tier(occupant)
        if bool(getattr(getattr(occupant, "db", None), "crime_flag", False)):
            evidence += 1
        if wanted_tier == "watched":
            evidence += 1
        elif wanted_tier == "wanted":
            evidence += 2
        elif wanted_tier == "arrest_eligible":
            evidence += 3

        if evidence > 0:
            evidence += repeat_pressure
        elif hidden_detected and repeat_pressure > 0:
            evidence += repeat_pressure

        if evidence > 0:
            if (now - float(suspicion_state.get("last_seen_time", 0.0) or 0.0)) <= GUARD_TARGET_MEMORY:
                evidence += 1
            suspicion += evidence
            suspicion_state["score"] = max(0, suspicion)
            suspicion_state["sightings"] = int(suspicion_state.get("sightings", 0) or 0) + 1
            suspicion_state["last_seen_time"] = now
            suspicion_state["last_decay_time"] = now
            suspicion_state["last_room_id"] = room_id
            suspicion_state["wanted_tier"] = wanted_tier
            suspicion_state["repeat_pressure"] = repeat_pressure
            updated[key] = suspicion_state
        elif key in updated:
            suspicion_state["wanted_tier"] = wanted_tier
            suspicion_state["repeat_pressure"] = repeat_pressure
            updated[key] = suspicion_state

        response = _get_suspicion_response(wanted_tier, int(suspicion_state.get("score", 0) or 0))
        if strongest_target is None or _is_stronger_target(suspicion_state, strongest_target["state"]):
            strongest_target = {"occupant": occupant, "state": dict(suspicion_state), "response": response}

        if response in {"watch", "arrest"}:
            _share_suspicion_with_nearby_guards(
                guard,
                occupant,
                suspicion_state,
                GUARD_SHARED_SUSPICION_ARREST if response == "arrest" else GUARD_SHARED_SUSPICION_WATCH,
                now,
            )

        if not _guard_has_authority(guard, occupant):
            continue

        if _should_start_confrontation(wanted_tier, suspicion_state):
            begin_guard_confrontation(guard, occupant)
        elif response == "watch":
            if not _guard_owns_actor(guard, occupant):
                guard.db.enforcement_state = "watching"
            _emit_guard_watch_message(guard, occupant, suspicion_state)

    updated = _prune_suspicion_targets(updated, now)
    _sync_guard_target_state(guard, updated, strongest_target)
    guard.db.suspicion_targets = updated
    return updated


def process_guard_tick():
    for guard in iter_active_guards():
        if not _is_active_guard(guard):
            continue
        decay_suspicion(guard)
        current_target = _resolve_guard_target_object(guard)
        if current_target is not None and _guard_owns_actor(guard, current_target):
            result = _process_guard_enforcement(guard, current_target)
            if result in {"holding", "moving", "arrested", "released"}:
                continue
        if getattr(guard, "location", None) is not None:
            scan_room_for_suspicion(guard)
            current_target = _resolve_guard_target_object(guard)
            if current_target is not None and _guard_owns_actor(guard, current_target):
                result = _process_guard_enforcement(guard, current_target)
                if result in {"holding", "moving", "arrested", "released"}:
                    continue
        _maybe_emit_guard_idle_look(guard)
        guard_movement_tick(guard)


def iter_active_guards():
    seen_ids = set()
    guards = []
    for guard in list(ACTIVE_GUARDS):
        guard_id = int(getattr(guard, "id", 0) or 0)
        if guard_id <= 0 or guard_id in seen_ids or not _is_active_guard(guard):
            continue
        guards.append(guard)
        seen_ids.add(guard_id)

    for guard in ObjectDB.objects.filter(
        db_typeclass_path__in=["typeclasses.npcs.GuardNPC", "typeclasses.npcs.guard.GuardNPC"]
    ):
        guard_id = int(getattr(guard, "id", 0) or 0)
        if guard_id <= 0 or guard_id in seen_ids or not _is_active_guard(guard):
            continue
        guards.append(guard)
        seen_ids.add(guard_id)
    return guards


def get_guard_by_id(guard_id):
    guard_id = int(guard_id or 0)
    if guard_id <= 0:
        return None
    for guard in iter_active_guards():
        if int(getattr(guard, "id", 0) or 0) == guard_id:
            return guard
    return ObjectDB.objects.filter(id=guard_id).first()


def begin_guard_confrontation(guard, actor):
    if not _is_active_guard(guard) or actor is None or not getattr(actor, "id", None):
        return False
    if not _guard_has_authority(guard, actor):
        return False
    if _guard_owns_actor(guard, actor) and str(getattr(getattr(guard, "db", None), "enforcement_state", "idle") or "idle") in {
        "confronting",
        "warning",
        "arresting",
    }:
        return True

    now = time.time()
    actor.db.active_guard_id = int(getattr(guard, "id", 0) or 0)
    actor.db.pending_arrest = True
    actor.db.justice_confrontation_started_at = now
    guard.db.current_target_id = int(getattr(actor, "id", 0) or 0)
    guard.db.current_target_name = str(getattr(actor, "key", "") or "")
    guard.db.current_target_room_id = int(getattr(getattr(actor, "location", None), "id", 0) or 0)
    guard.db.follow_steps_remaining = GUARD_MAX_FOLLOW_STEPS
    guard.db.enforcement_state = "confronting"
    guard.db.warning_count = 0
    guard.db.last_warning_time = 0.0
    guard.db.enforcement_started_at = now

    if _is_repeat_offender(actor):
        guard.db.warning_count = 2
        actor.db.justice_warning_level = max(2, int(getattr(getattr(actor, "db", None), "justice_warning_level", 0) or 0))
        actor.msg(f"{guard.key} narrows his eyes. 'You again...' ")

    actor.msg(f"{guard.key} steps in front of you. 'Hold there.'")
    room = getattr(guard, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(f"{guard.key} steps toward {actor.key} and blocks their path.", exclude=[guard, actor])

    _advance_guard_warning(guard, actor, now=now, force=True)
    return True


def attempt_visible_arrest(guard, actor):
    if not _is_active_guard(guard) or actor is None or not _guard_owns_actor(guard, actor):
        return {"started": False, "reason": "guard does not own target"}
    allowed, reason = can_be_arrested(actor)
    if not allowed:
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True, clear_attention=False)
        return {"started": False, "reason": str(reason or "arrest unavailable")}
    if int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) < 3 and not bool(getattr(getattr(actor, "db", None), "justice_flee_flag", False)):
        return {"started": False, "reason": "warning ladder incomplete"}

    guard.db.enforcement_state = "arresting"
    actor.db.pending_arrest = True
    actor.msg(f"{guard.key} grabs you.")
    actor.msg("You are seized by the town watch.")
    room = getattr(guard, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(f"{guard.key} seizes {actor.key} and takes them into custody.", exclude=[guard, actor])
    begin_arrest(actor, source=f"{guard.key} arrest", quiet=True)
    result = complete_arrest(actor, source=f"{guard.key} arrest", voluntary=False)
    release_guard_enforcement(guard=guard, actor=actor, clear_actor=True, clear_attention=True, clear_flee=True)
    return {"started": True, **result}


def release_guard_enforcement(guard=None, actor=None, clear_actor=True, clear_attention=False, clear_flee=False):
    if actor is None and guard is not None:
        actor = _resolve_guard_target_object(guard)

    if guard is not None and _is_active_guard(guard):
        _clear_guard_target_state(guard)
        guard.db.enforcement_state = "idle"
        guard.db.warning_count = 0
        guard.db.last_warning_time = 0.0
        guard.db.enforcement_started_at = 0.0

    if actor is not None and clear_actor:
        owner_id = int(getattr(getattr(actor, "db", None), "active_guard_id", 0) or 0)
        guard_id = int(getattr(guard, "id", 0) or 0) if guard is not None else 0
        if guard is None or owner_id in {0, guard_id}:
            actor.db.active_guard_id = None
            actor.db.pending_arrest = False
            actor.db.justice_warning_level = 0
            actor.db.justice_confrontation_started_at = 0
            if clear_attention:
                actor.db.guard_attention = False
            if clear_flee:
                actor.db.justice_flee_flag = False
    return True


def reset_guard_runtime(delete_spawned=False, refresh_templates=False):
    global GUARD_TEMPLATE_CACHE
    if delete_spawned:
        for guard in list(ACTIVE_GUARDS):
            try:
                if getattr(guard, "pk", None):
                    guard.delete()
            except Exception:
                continue
    ACTIVE_GUARDS.clear()
    if refresh_templates:
        GUARD_TEMPLATE_CACHE = []


def decay_suspicion(guard, suspicion_targets=None, now=None, persist=True):
    if not _is_active_guard(guard):
        return {}

    now = float(now or time.time())
    updated = {
        str(key): _normalize_suspicion_state(value)
        for key, value in dict(suspicion_targets or getattr(getattr(guard, "db", None), "suspicion_targets", None) or {}).items()
    }
    for key, state in list(updated.items()):
        last_decay_time = float(state.get("last_decay_time", state.get("last_seen_time", 0.0)) or 0.0)
        if last_decay_time <= 0:
            continue
        decay_steps = int(max(0.0, now - last_decay_time) // GUARD_SUSPICION_DECAY_INTERVAL)
        if decay_steps <= 0:
            continue
        state["score"] = max(0, int(state.get("score", 0) or 0) - decay_steps)
        state["last_decay_time"] = last_decay_time + (decay_steps * GUARD_SUSPICION_DECAY_INTERVAL)
        updated[str(key)] = state

    updated = _prune_suspicion_targets(updated, now)
    if persist:
        guard.db.suspicion_targets = updated
        _sync_guard_target_state(guard, updated, None)
    return updated


def _load_valid_guard_templates():
    templates = []
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT canonical_key, name, actor_type, base_health, tags_json, normalized_fields_json, source_id
            FROM canon_actors
            WHERE role = %s
            ORDER BY name
            """,
            ["guard"],
        )
        rows = cursor.fetchall()

    for canonical_key, name, actor_type, base_health, tags_json, normalized_json, source_id in rows:
        normalized_fields = _parse_json(normalized_json, {})
        tags = _parse_json(tags_json, [])
        normalized_actor_type = str(normalized_fields.get("actor_type") or actor_type or "").strip().lower()
        aggression_type = str(normalized_fields.get("aggression_type") or "").strip().lower()
        if not str(name or "").strip():
            continue
        if normalized_actor_type != "social":
            continue
        if aggression_type != "defensive":
            continue
        template_tags = list(dict.fromkeys(list(tags or []) + ["guard_validated"]))
        if "guard" not in template_tags:
            template_tags.append("guard")
        normalized_copy = dict(normalized_fields)
        normalized_copy["actor_type"] = "social"
        normalized_copy["aggression_type"] = "defensive"
        normalized_copy["tags"] = list(dict.fromkeys(list(normalized_copy.get("tags") or []) + ["guard_validated", "guard"]))
        templates.append(
            {
                "canonical_key": canonical_key,
                "template_id": str(source_id),
                "name": str(name),
                "actor_type": "social",
                "base_health": base_health,
                "tags": template_tags,
                "normalized_fields": normalized_copy,
            }
        )
    return templates


def _assign_template_to_guard(guard, template, start_room):
    _normalize_guard_identity(guard)
    guard.db.template_id = str(template.get("template_id") or template.get("canonical_key") or "")
    guard.db.template_key = str(template.get("canonical_key") or "")
    guard.db.template_name = str(template.get("name") or "")
    guard.db.is_guard = True
    guard.db.is_npc = True
    guard.db.patrol_anchor = start_room
    guard.db.patrol_radius = 5
    guard.db.last_move_time = 0.0
    guard.db.last_idle_time = time.time()
    guard.db.recent_rooms = [int(getattr(start_room, "id", 0) or 0)]
    guard.db.suspicion_targets = {}
    guard.db.guard_id = str(uuid4())
    guard.db.zone = str(getattr(getattr(start_room, "db", None), "zone", None) or GUARD_PATROL_ZONE)
    guard.db.current_target_id = None
    guard.db.current_target_name = None
    guard.db.current_target_score = 0
    guard.db.last_seen_time = 0.0
    guard.db.current_target_room_id = None
    guard.db.follow_steps_remaining = 0
    guard.db.previous_room_id = int(getattr(start_room, "id", 0) or 0)
    guard.db.enforcement_state = "idle"
    guard.db.warning_count = 0
    guard.db.last_warning_time = 0.0
    guard.db.enforcement_started_at = 0.0
    guard.db.guard_template = {
        "canonical_key": template.get("canonical_key"),
        "name": template.get("name"),
        "base_health": template.get("base_health"),
        "tags": list(template.get("tags") or []),
    }
    if template.get("base_health"):
        guard.db.max_hp = int(template.get("base_health") or 1)
        guard.db.hp = int(template.get("base_health") or 1)


def _normalize_guard_identity(guard):
    guard.key = GUARD_DISPLAY_NAME
    guard.db.name = GUARD_DISPLAY_NAME


def _get_patrol_rooms_for_zone(zone_name):
    rooms = []
    for room in ObjectDB.objects.filter(db_typeclass_path="typeclasses.rooms.Room").order_by("id"):
        if _allows_guard_patrol_room(room, zone_name=zone_name):
            rooms.append(room)
    return rooms


def _is_active_guard(guard):
    return bool(guard and getattr(guard, "pk", None) and bool(getattr(getattr(guard, "db", None), "is_guard", False)))


def _is_lawful_room(room):
    if room is None:
        return False
    explicit = getattr(getattr(room, "db", None), "is_lawful", None)
    if explicit is not None:
        return bool(explicit)
    law_type = str(getattr(getattr(room, "db", None), "law_type", "standard") or "standard").strip().lower()
    return law_type != "none"


def _remember_recent_room(guard, room):
    recent = list(getattr(getattr(guard, "db", None), "recent_rooms", None) or [])
    room_id = int(getattr(room, "id", 0) or 0)
    recent.append(room_id)
    guard.db.recent_rooms = recent[-GUARD_RECENT_ROOM_LIMIT:]


def _get_valid_guard_exits(guard, room):
    exits = []
    for obj in list(getattr(room, "contents", None) or []):
        destination = getattr(obj, "destination", None)
        if destination is None:
            continue
        if bool(getattr(getattr(obj, "db", None), "no_guard", False)):
            continue
        if not _allows_guard_patrol_room(destination, zone_name=str(getattr(getattr(guard, "db", None), "zone", "") or GUARD_PATROL_ZONE)):
            continue
        if not _within_patrol_radius(guard, destination):
            continue
        exits.append(obj)
    return exits


def _within_patrol_radius(guard, destination):
    anchor = getattr(getattr(guard, "db", None), "patrol_anchor", None)
    radius = int(getattr(getattr(guard, "db", None), "patrol_radius", 5) or 5)
    if anchor is None or destination is None:
        return True
    return _room_distance(anchor, destination, max_depth=radius) <= radius


def _room_distance(anchor, target, max_depth=5):
    if anchor == target:
        return 0
    visited = {int(getattr(anchor, "id", 0) or 0)}
    frontier = [(anchor, 0)]
    while frontier:
        room, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for obj in list(getattr(room, "contents", None) or []):
            destination = getattr(obj, "destination", None)
            if destination is None:
                continue
            destination_id = int(getattr(destination, "id", 0) or 0)
            if destination_id in visited:
                continue
            if destination == target:
                return depth + 1
            visited.add(destination_id)
            frontier.append((destination, depth + 1))
    return max_depth + 1


def _select_guard_exit(guard, exits, force_move=False):
    if not exits:
        return None
    recent_rooms = set(int(entry or 0) for entry in list(getattr(getattr(guard, "db", None), "recent_rooms", None) or []))
    previous_room_id = int(getattr(getattr(guard, "db", None), "previous_room_id", 0) or 0)
    scored = []
    non_recent = []
    for exit_obj in exits:
        destination = getattr(exit_obj, "destination", None)
        destination_id = int(getattr(destination, "id", 0) or 0)
        guard_count = _count_guards_in_room(destination)
        crowd_count = _count_non_guard_occupants(destination)
        weight = 10
        if _is_lawful_room(destination):
            weight += 5
        if destination_id not in recent_rooms:
            weight += 6
            non_recent.append(exit_obj)
        else:
            weight = max(1, weight - 8)
        if previous_room_id and destination_id == previous_room_id:
            weight = max(1, weight - 9)
        weight = max(1, weight - min(6, crowd_count))
        if guard_count > 0:
            weight = max(1, weight - 12)
        scored.append((exit_obj, weight))

    pool = non_recent if non_recent else [entry[0] for entry in scored]
    weighted_pool = [(exit_obj, weight) for exit_obj, weight in scored if exit_obj in pool]
    if not weighted_pool:
        return None
    if force_move:
        weighted_pool.sort(key=lambda entry: entry[1], reverse=True)
        return weighted_pool[0][0]

    total_weight = sum(weight for _, weight in weighted_pool)
    roll = random.uniform(0.0, float(total_weight))
    running = 0.0
    for exit_obj, weight in weighted_pool:
        running += float(weight)
        if roll <= running:
            return exit_obj
    return weighted_pool[-1][0]


def _select_targeted_exit(guard, exits):
    target = _resolve_guard_target_object(guard)
    if target is None:
        return None

    current_room = getattr(guard, "location", None)
    target_room = getattr(target, "location", None)
    if current_room is None or target_room is None or target_room == current_room:
        return None

    for exit_obj in exits:
        if getattr(exit_obj, "destination", None) == target_room:
            return exit_obj

    viable = []
    for exit_obj in exits:
        destination = getattr(exit_obj, "destination", None)
        if destination is None:
            continue
        distance = _room_distance(destination, target_room, max_depth=2)
        if distance <= 2:
            viable.append((exit_obj, distance, _count_guards_in_room(destination)))
    if not viable:
        return None
    viable.sort(key=lambda entry: (entry[1], entry[2]))
    return viable[0][0]


def _mark_clump_exit(guard, room):
    now = time.time()
    guard.db.pending_clump_exit_at = now + GUARD_CLUMP_EXIT_DELAY
    guard.db.last_idle_time = min(float(getattr(guard.db, "last_idle_time", now) or now), now - GUARD_IDLE_MAX)
    delay(GUARD_CLUMP_EXIT_DELAY, guard_movement_tick, guard)


def _emit_guard_entry_message(guard):
    room = getattr(guard, "location", None)
    if room is None or not hasattr(room, "msg_contents"):
        return
    now = time.time()
    last_entry = float(getattr(getattr(room, "db", None), "last_guard_entry_time", 0.0) or 0.0)
    guard_count = _count_guards_in_room(room)
    if last_entry and (now - last_entry) < GUARD_CLUMP_EXIT_DELAY:
        message = "Several guards pass through."
    elif guard_count > 1:
        message = "Several guards pass through."
    else:
        message = f"{guard.key} strides in on patrol."
    room.db.last_guard_entry_time = now
    room.db.last_guard_entry_message = message
    room.msg_contents(message, exclude=[guard])


def _count_guards_in_room(room):
    return sum(1 for obj in list(getattr(room, "contents", None) or []) if bool(getattr(getattr(obj, "db", None), "is_guard", False)))


def _count_other_guards_in_room(guard, room):
    return sum(
        1
        for obj in list(getattr(room, "contents", None) or [])
        if obj != guard and bool(getattr(getattr(obj, "db", None), "is_guard", False))
    )


def _count_non_guard_occupants(room):
    return sum(
        1
        for obj in list(getattr(room, "contents", None) or [])
        if getattr(obj, "destination", None) is None and not bool(getattr(getattr(obj, "db", None), "is_guard", False))
    )


def _parse_json(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _allows_guard_patrol_room(room, zone_name=None):
    if room is None:
        return False
    if bool(getattr(getattr(room, "db", None), "no_guard", False)):
        return False
    room_zone = str(getattr(getattr(room, "db", None), "zone", "") or "").strip().lower()
    guard_zone = str(getattr(getattr(room, "db", None), "guard_zone", "") or "").strip().lower()
    if zone_name and room_zone != zone_name and guard_zone != zone_name:
        return False
    if not _is_lawful_room(room):
        return False
    patrol_flag = getattr(getattr(room, "db", None), "guard_patrol", None)
    if bool(_zone_uses_explicit_patrol(zone_name)):
        return patrol_flag is True
    return patrol_flag is not False


def _zone_uses_explicit_patrol(zone_name):
    for room in ObjectDB.objects.filter(db_typeclass_path="typeclasses.rooms.Room"):
        room_zone = str(getattr(getattr(room, "db", None), "zone", "") or "").strip().lower()
        guard_zone = str(getattr(getattr(room, "db", None), "guard_zone", "") or "").strip().lower()
        if zone_name and room_zone != zone_name and guard_zone != zone_name:
            continue
        if bool(getattr(getattr(room, "db", None), "guard_patrol", False)) and _is_lawful_room(room):
            return True
    return False


def _normalize_suspicion_state(value):
    if isinstance(value, Mapping):
        return {
            "score": int(value.get("score", 0) or 0),
            "sightings": int(value.get("sightings", 0) or 0),
            "last_seen_time": float(value.get("last_seen_time", 0.0) or 0.0),
            "last_decay_time": float(value.get("last_decay_time", value.get("last_seen_time", 0.0)) or 0.0),
            "last_room_id": int(value.get("last_room_id", 0) or 0),
            "wanted_tier": str(value.get("wanted_tier", "clear") or "clear"),
            "warned_at": float(value.get("warned_at", 0.0) or 0.0),
            "repeat_pressure": int(value.get("repeat_pressure", 0) or 0),
        }
    return {
        "score": int(value or 0),
        "sightings": 0,
        "last_seen_time": 0.0,
        "last_decay_time": 0.0,
        "last_room_id": 0,
        "wanted_tier": "clear",
        "warned_at": 0.0,
        "repeat_pressure": 0,
    }


def _get_repeat_offender_pressure(actor):
    crime_count = int(getattr(getattr(actor, "db", None), "crime_count", 0) or 0)
    law_reputation = int(getattr(getattr(actor, "db", None), "law_reputation", 0) or 0)
    pressure = 0
    if crime_count >= REPEAT_OFFENDER_WARNING_THRESHOLD:
        pressure += 1
    if crime_count >= 5:
        pressure += 1
    if law_reputation <= -3:
        pressure += 1
    if law_reputation <= -6:
        pressure += 1
    if law_reputation >= 3:
        pressure -= 1
    return max(0, pressure)


def _is_repeat_offender(actor):
    return _get_repeat_offender_pressure(actor) > 0


def _get_suspicion_response(wanted_tier, suspicion_score):
    tier = str(wanted_tier or "clear").strip().lower()
    score = int(suspicion_score or 0)
    if tier == "arrest_eligible":
        return "arrest"
    if tier == "wanted" and score >= (GUARD_ARREST_THRESHOLD - 1):
        return "arrest"
    if score >= GUARD_ARREST_THRESHOLD:
        return "arrest"
    if tier in {"watched", "wanted"} or score >= GUARD_WATCH_THRESHOLD:
        return "watch"
    return "ignore"


def _is_stronger_target(candidate, current):
    if current is None:
        return True
    candidate_score = int(candidate.get("score", 0) or 0)
    current_score = int(current.get("score", 0) or 0)
    if candidate_score != current_score:
        return candidate_score > current_score
    return float(candidate.get("last_seen_time", 0.0) or 0.0) > float(current.get("last_seen_time", 0.0) or 0.0)


def _prune_suspicion_targets(updated, now):
    pruned = {}
    for key, value in updated.items():
        state = _normalize_suspicion_state(value)
        age = now - float(state.get("last_seen_time", 0.0) or 0.0)
        if age > GUARD_TARGET_MEMORY:
            continue
        if int(state.get("score", 0) or 0) <= 0:
            continue
        pruned[str(key)] = state
    return pruned


def _sync_guard_target_state(guard, updated, strongest_target):
    if strongest_target is not None:
        occupant = strongest_target.get("occupant")
        state = _normalize_suspicion_state(strongest_target.get("state"))
        response = _get_suspicion_response(state.get("wanted_tier"), int(state.get("score", 0) or 0))
        guard.db.current_target_id = int(getattr(occupant, "id", 0) or 0)
        guard.db.current_target_name = str(getattr(occupant, "key", "") or "")
        guard.db.current_target_score = int(state.get("score", 0) or 0)
        guard.db.last_seen_time = float(state.get("last_seen_time", 0.0) or 0.0)
        guard.db.current_target_room_id = int(state.get("last_room_id", 0) or 0)
        if not _guard_owns_actor(guard, occupant):
            guard.db.follow_steps_remaining = GUARD_MAX_FOLLOW_STEPS if response in {"watch", "arrest"} else 0
        return

    best_key = None
    best_state = None
    for key, state in updated.items():
        normalized = _normalize_suspicion_state(state)
        if _is_stronger_target(normalized, best_state):
            best_key = str(key)
            best_state = normalized

    if best_key is None or best_state is None:
        _clear_guard_target_state(guard)
        return

    target = ObjectDB.objects.filter(id=int(best_key or 0)).first()
    guard.db.current_target_id = int(best_key or 0)
    guard.db.current_target_name = str(getattr(target, "key", "") or guard.db.current_target_name or "")
    guard.db.current_target_score = int(best_state.get("score", 0) or 0)
    guard.db.last_seen_time = float(best_state.get("last_seen_time", 0.0) or 0.0)
    guard.db.current_target_room_id = int(best_state.get("last_room_id", 0) or 0)
    if not _guard_owns_actor(guard, target):
        guard.db.follow_steps_remaining = GUARD_MAX_FOLLOW_STEPS if _get_suspicion_response(best_state.get("wanted_tier"), int(best_state.get("score", 0) or 0)) in {"watch", "arrest"} else 0


def _get_current_guard_target(guard):
    target = _resolve_guard_target_object(guard)
    if target is None:
        return None
    score = int(getattr(getattr(guard, "db", None), "current_target_score", 0) or 0)
    wanted_tier = get_wanted_tier(target)
    return {
        "target": target,
        "score": score,
        "response": _get_suspicion_response(wanted_tier, score),
        "wanted_tier": wanted_tier,
    }


def _resolve_guard_target_object(guard):
    target_id = int(getattr(getattr(guard, "db", None), "current_target_id", 0) or 0)
    last_seen = float(getattr(getattr(guard, "db", None), "last_seen_time", 0.0) or 0.0)
    if target_id <= 0:
        return None
    if last_seen > 0 and (time.time() - last_seen) > GUARD_TARGET_MEMORY:
        _clear_guard_target_state(guard)
        return None
    return ObjectDB.objects.filter(id=target_id).first()


def _emit_guard_watch_message(guard, target, suspicion_state):
    if not _guard_has_authority(guard, target):
        return
    now = time.time()
    last_message = float(getattr(getattr(target, "db", None), "last_guard_watch_message_at", 0.0) or 0.0)
    if last_message and (now - last_message) < GUARD_WATCH_MESSAGE_COOLDOWN:
        return
    target.db.last_guard_watch_message_at = now
    target.msg(f"{guard.key} watches you closely.")
    room = getattr(guard, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(
            f"{guard.key} slows and keeps a close eye on {target.key}.",
            exclude=[guard, target],
        )


def _share_suspicion_with_nearby_guards(guard, target, suspicion_state, amount, now):
    for other_guard in _iter_nearby_guards(guard):
        if other_guard == guard or not _is_active_guard(other_guard):
            continue
        other_targets = {
            str(key): _normalize_suspicion_state(value)
            for key, value in dict(getattr(getattr(other_guard, "db", None), "suspicion_targets", None) or {}).items()
        }
        key = str(getattr(target, "id", 0) or 0)
        if not key:
            continue
        other_state = _normalize_suspicion_state(other_targets.get(key))
        other_state["score"] = max(int(other_state.get("score", 0) or 0), int(suspicion_state.get("score", 0) or 0) - 1)
        other_state["score"] = max(0, int(other_state.get("score", 0) or 0) + int(amount or 0))
        other_state["sightings"] = max(int(other_state.get("sightings", 0) or 0), 1)
        other_state["last_seen_time"] = now
        other_state["last_decay_time"] = now
        other_state["last_room_id"] = int(getattr(getattr(guard, "location", None), "id", 0) or 0)
        other_state["wanted_tier"] = str(suspicion_state.get("wanted_tier", "clear") or "clear")
        if float(other_state.get("warned_at", 0.0) or 0.0) <= 0 and float(suspicion_state.get("warned_at", 0.0) or 0.0) > 0:
            other_state["warned_at"] = float(suspicion_state.get("warned_at", 0.0) or 0.0)
        other_targets[key] = other_state
        other_targets = _prune_suspicion_targets(other_targets, now)
        other_guard.db.suspicion_targets = other_targets
        _sync_guard_target_state(other_guard, other_targets, None)


def _iter_nearby_guards(guard):
    current_room = getattr(guard, "location", None)
    if current_room is None:
        return []
    seen_ids = set()
    nearby = []
    for obj in list(getattr(current_room, "contents", None) or []):
        if obj != guard and _is_active_guard(obj):
            nearby.append(obj)
            seen_ids.add(int(getattr(obj, "id", 0) or 0))
    for exit_obj in list(getattr(current_room, "contents", None) or []):
        destination = getattr(exit_obj, "destination", None)
        if destination is None:
            continue
        for obj in list(getattr(destination, "contents", None) or []):
            obj_id = int(getattr(obj, "id", 0) or 0)
            if obj != guard and obj_id not in seen_ids and _is_active_guard(obj):
                nearby.append(obj)
                seen_ids.add(obj_id)
    return nearby


def _clear_guard_target_state(guard):
    guard.db.current_target_id = None
    guard.db.current_target_name = None
    guard.db.current_target_score = 0
    guard.db.last_seen_time = 0.0
    guard.db.current_target_room_id = None
    guard.db.follow_steps_remaining = 0


def _guard_has_authority(guard, actor):
    owner_id = int(getattr(getattr(actor, "db", None), "active_guard_id", 0) or 0)
    guard_id = int(getattr(guard, "id", 0) or 0)
    return owner_id in {0, guard_id}


def _guard_owns_actor(guard, actor):
    return int(getattr(getattr(actor, "db", None), "active_guard_id", 0) or 0) == int(getattr(guard, "id", 0) or 0)


def _should_start_confrontation(wanted_tier, suspicion_state):
    score = int((suspicion_state or {}).get("score", 0) or 0)
    tier = str(wanted_tier or "clear").strip().lower()
    repeat_pressure = int((suspicion_state or {}).get("repeat_pressure", 0) or 0)
    threshold = max(1, GUARD_ARREST_THRESHOLD - min(2, repeat_pressure))
    return score >= threshold or tier in {"wanted", "arrest_eligible"}


def _process_guard_enforcement(guard, actor):
    if actor is None:
        release_guard_enforcement(guard=guard, clear_actor=False)
        return "released"
    if bool(getattr(getattr(actor, "db", None), "detained", False)):
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True, clear_attention=True, clear_flee=True)
        return "arrested"
    if not _guard_owns_actor(guard, actor):
        release_guard_enforcement(guard=guard, clear_actor=False)
        return "released"

    target_room = getattr(actor, "location", None)
    guard_room = getattr(guard, "location", None)
    if not _allows_guard_patrol_room(target_room, zone_name=str(getattr(getattr(guard, "db", None), "zone", "") or GUARD_PATROL_ZONE)):
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True)
        return "released"
    if target_room is None or guard_room is None:
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True)
        return "released"

    if target_room != guard_room:
        if int(getattr(getattr(guard, "db", None), "follow_steps_remaining", 0) or 0) > 0:
            moved = guard_movement_tick(guard)
            return "moving" if moved else "holding"
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True)
        return "released"

    now = time.time()
    guard.db.last_idle_time = now
    if str(getattr(getattr(guard, "db", None), "enforcement_state", "idle") or "idle") == "watching":
        begin_guard_confrontation(guard, actor)
        return "holding"

    if bool(getattr(getattr(actor, "db", None), "justice_flee_flag", False)):
        if int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) < 3:
            guard.db.warning_count = 2
            guard.db.last_warning_time = 0.0
        if (now - float(getattr(getattr(guard, "db", None), "last_warning_time", 0.0) or 0.0)) >= GUARD_WARNING_COOLDOWN:
            if int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) >= 3:
                attempt_visible_arrest(guard, actor)
            else:
                _advance_guard_warning(guard, actor, now=now, force=True)
        return "holding"

    elapsed = now - float(getattr(getattr(actor, "db", None), "justice_confrontation_started_at", 0.0) or now)
    if _is_repeat_offender(actor) and int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) >= 2:
        if (now - float(getattr(getattr(guard, "db", None), "last_warning_time", 0.0) or 0.0)) >= GUARD_WARNING_COOLDOWN:
            attempt_visible_arrest(guard, actor)
        return "holding"
    if elapsed >= GUARD_CONFRONT_TIMEOUT and int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) < 3:
        _advance_guard_warning(guard, actor, now=now, force=True)
        return "holding"

    if (now - float(getattr(getattr(guard, "db", None), "last_warning_time", 0.0) or 0.0)) >= GUARD_WARNING_COOLDOWN:
        if int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) >= 3:
            attempt_visible_arrest(guard, actor)
        else:
            _advance_guard_warning(guard, actor, now=now, force=True)
    return "holding"


def _advance_guard_warning(guard, actor, now=None, force=False):
    if not _guard_owns_actor(guard, actor):
        return False
    now = float(now or time.time())
    last_warning_time = float(getattr(getattr(guard, "db", None), "last_warning_time", 0.0) or 0.0)
    if not force and (now - last_warning_time) < GUARD_WARNING_COOLDOWN:
        return False

    next_stage = min(4, int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) + 1)
    guard.db.warning_count = next_stage
    guard.db.last_warning_time = now
    guard.db.enforcement_state = "warning"
    actor.db.justice_warning_level = min(3, next_stage)
    actor.db.pending_arrest = True
    guard.db.follow_steps_remaining = GUARD_MAX_FOLLOW_STEPS

    if next_stage == 1:
        actor.msg(f"{guard.key} eyes you suspiciously.")
    elif next_stage == 2:
        actor.msg(f"{guard.key} says, 'You are being watched.'")
    elif next_stage == 3:
        actor.msg(f"{guard.key} says, 'Surrender now or face arrest.'")
    else:
        return attempt_visible_arrest(guard, actor)

    room = getattr(guard, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(f"{guard.key} keeps {actor.key} under open scrutiny.", exclude=[guard, actor])
    return True


def _maybe_emit_guard_idle_look(guard):
    room = getattr(guard, "location", None)
    if room is None or not hasattr(room, "msg_contents"):
        return
    now = time.time()
    last_look = float(getattr(getattr(guard, "db", None), "last_idle_look_time", 0.0) or 0.0)
    if (now - last_look) < 60.0:
        return
    if random.random() > 0.15:
        return
    guard.db.last_idle_look_time = now
    room.msg_contents(f"{guard.key} pauses and surveys the street.", exclude=[guard])