from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Mapping
from threading import RLock
import time
import weakref

from evennia.utils import logger

from world.systems.engine_flags import is_enabled
from world.systems.metrics import increment_counter, observe_max, record_event, snapshot_metrics, set_gauge


ROOM = "room"
PROXIMITY = "proximity"
ZONE = "zone"
DIRECT = "direct"
SCHEDULED = "scheduled"
VALID_INTEREST_TYPES = {ROOM, PROXIMITY, ZONE, DIRECT, SCHEDULED}


_LOCK = RLock()
_INTEREST_REGISTRY = {}
_ZONE_CACHE = {}
ZONE_CACHE_SECONDS = 30.0


def _refresh_interest_gauges():
    source_counts = {interest_type: 0 for interest_type in sorted(VALID_INTEREST_TYPES)}
    active_object_count = 0
    total_source_count = 0

    with _LOCK:
        stale_keys = []
        for object_key, record in list(_INTEREST_REGISTRY.items()):
            obj = record.get("object_ref")() if record.get("object_ref") else None
            if obj is None:
                stale_keys.append(object_key)
                continue

            sources = dict(record.get("sources", {}) or {})
            if sources:
                active_object_count += 1
            for entry in sources.values():
                interest_type = str((entry or {}).get("type", "") or "").strip().lower()
                total_source_count += 1
                if interest_type in source_counts:
                    source_counts[interest_type] += 1

        for object_key in stale_keys:
            _INTEREST_REGISTRY.pop(object_key, None)

    set_gauge("interest.active_object_count", active_object_count)
    observe_max("interest.active_object_peak", active_object_count)
    set_gauge("interest.source_count.current", total_source_count)
    observe_max("interest.source_count.peak", total_source_count)
    for interest_type, count in source_counts.items():
        set_gauge(f"interest.source.current.{interest_type}", count)
        observe_max(f"interest.source.peak.{interest_type}", count)


def _record_transition(event, obj, source_count):
    object_key = _object_key(obj)
    object_label = getattr(obj, "key", None) or object_key
    increment_counter(f"interest.transition.{event}")
    record_event(
        "interest.transition",
        0.0,
        metadata={
            "event": event,
            "object_key": object_key,
            "object_label": object_label,
            "source_count": int(source_count or 0),
        },
    )


def _normalize_interest_type(interest_type):
    normalized = str(interest_type or "").strip().lower()
    if normalized not in VALID_INTEREST_TYPES:
        raise ValueError(f"Unknown interest type: {interest_type}")
    return normalized


def _object_key(obj):
    if obj is None:
        raise ValueError("Interest registration requires an object.")
    object_id = getattr(obj, "id", None)
    if object_id is not None:
        return f"#{int(object_id)}"
    return f"mem:{id(obj)}"


def _source_key(source):
    if source is None:
        raise ValueError("Interest registration requires a source.")
    if isinstance(source, Mapping):
        source_type = str(source.get("type") or "source").strip().lower() or "source"
        value = str(source.get("id") or source.get("key") or source.get("value") or "").strip()
        if value:
            return f"{source_type}:{value}"
    source_id = getattr(source, "id", None)
    if source_id is not None:
        return f"obj:{int(source_id)}"
    source_key = getattr(source, "key", None)
    if source_key:
        return f"key:{str(source_key).strip().lower()}"
    normalized = str(source).strip().lower()
    if not normalized:
        raise ValueError("Interest registration requires a non-empty source.")
    return f"text:{normalized}"


def _source_label(source):
    if isinstance(source, Mapping):
        for field in ("label", "key", "id", "value"):
            if source.get(field):
                return str(source.get(field)).strip()
    if getattr(source, "key", None):
        return str(source.key).strip()
    if getattr(source, "id", None) is not None:
        return f"#{int(source.id)}"
    return str(source).strip()


def _get_record(obj, create=False):
    object_key = _object_key(obj)
    record = _INTEREST_REGISTRY.get(object_key)
    if record is None and create:
        record = {
            "object_key": object_key,
            "object_ref": weakref.ref(obj),
            "object_label": getattr(obj, "key", None) or object_key,
            "sources": {},
        }
        _INTEREST_REGISTRY[object_key] = record
    return record


def _prune_record_if_empty(record):
    if record and not record.get("sources"):
        _INTEREST_REGISTRY.pop(record.get("object_key"), None)
        _refresh_interest_gauges()


def _iter_room_targets(room):
    if room is None:
        return []
    targets = []
    seen = set()
    for candidate in [room, *list(getattr(room, "contents", []) or [])]:
        if candidate is None:
            continue
        try:
            candidate_key = _object_key(candidate)
        except ValueError:
            continue
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        targets.append(candidate)
    return targets


def _iter_exit_destinations(room):
    if room is None:
        return []
    exits = list(getattr(room, "exits", []) or [])
    if not exits:
        exits = [obj for obj in list(getattr(room, "contents", []) or []) if getattr(obj, "destination", None)]

    destinations = []
    seen = set()
    for exit_obj in exits:
        destination = getattr(exit_obj, "destination", None)
        if destination is None:
            continue
        try:
            destination_key = _object_key(destination)
        except ValueError:
            continue
        if destination_key in seen:
            continue
        seen.add(destination_key)
        destinations.append(destination)
    return destinations


def _iter_proximity_rooms(room, radius=1):
    if room is None or int(radius or 0) <= 0:
        return []

    frontier = [room]
    visited = {_object_key(room)}
    proximity_rooms = []

    for _ in range(int(radius or 0)):
        next_frontier = []
        for current in frontier:
            for destination in _iter_exit_destinations(current):
                destination_key = _object_key(destination)
                if destination_key in visited:
                    continue
                visited.add(destination_key)
                proximity_rooms.append(destination)
                next_frontier.append(destination)
        frontier = next_frontier
        if not frontier:
            break
    return proximity_rooms


def _iter_proximity_targets(room, radius=1):
    targets = []
    seen = set()
    for proximity_room in _iter_proximity_rooms(room, radius=radius):
        for target in _iter_room_targets(proximity_room):
            try:
                target_key = _object_key(target)
            except ValueError:
                continue
            if target_key in seen:
                continue
            seen.add(target_key)
            targets.append(target)
    return targets


def _get_room_area_tag(room):
    if room is None or not hasattr(room, "tags"):
        return None
    try:
        build_tags = room.tags.get(category="build", return_list=True) or []
    except Exception:
        build_tags = []
    normalized = str(build_tags[0] or "").strip().lower() if build_tags else ""
    return normalized or None


def _get_room_region_key(room):
    if room is None:
        return None
    region = ""
    if hasattr(room, "get_region"):
        try:
            region = str(room.get_region() or "").strip().lower()
        except Exception:
            region = ""
    else:
        region = str(getattr(getattr(room, "db", None), "region", "") or "").strip().lower()
    if not region or region == "default_region":
        return None
    return region


def _get_zone_key(room):
    area_tag = _get_room_area_tag(room)
    if area_tag:
        return f"area:{area_tag}"
    region = _get_room_region_key(room)
    if region:
        return f"region:{region}"
    return None


def _iter_zone_rooms(room):
    zone_key = _get_zone_key(room)
    if not zone_key:
        return []

    now = time.time()
    cached = _ZONE_CACHE.get(zone_key)
    if cached and now < float(cached.get("expires_at", 0.0) or 0.0):
        return list(cached.get("rooms", []) or [])

    rooms = []
    if zone_key.startswith("area:"):
        from evennia.utils.search import search_tag

        area_tag = zone_key.split(":", 1)[1]
        rooms = [candidate for candidate in list(search_tag(area_tag, category="build") or []) if getattr(candidate, "destination", None) is None]
    elif zone_key.startswith("region:"):
        from evennia.objects.models import ObjectDB

        region = zone_key.split(":", 1)[1]
        for candidate in ObjectDB.objects.filter(db_location__isnull=True).order_by("id"):
            if getattr(candidate, "destination", None) is not None:
                continue
            if _get_room_region_key(candidate) != region:
                continue
            rooms.append(candidate)

    _ZONE_CACHE[zone_key] = {"expires_at": now + ZONE_CACHE_SECONDS, "rooms": list(rooms)}
    return list(rooms)


def _iter_zone_targets(room):
    targets = []
    seen = set()
    for zone_room in _iter_zone_rooms(room):
        for target in _iter_room_targets(zone_room):
            try:
                target_key = _object_key(target)
            except ValueError:
                continue
            if target_key in seen:
                continue
            seen.add(target_key)
            targets.append(target)
    return targets


def _room_source(subject):
    return {
        "type": "room-subject",
        "id": getattr(subject, "id", None) or id(subject),
        "label": f"room:{getattr(subject, 'key', getattr(subject, 'id', 'subject'))}",
    }


def _proximity_source(subject, radius=1):
    return {
        "type": "proximity-subject",
        "id": f"{getattr(subject, 'id', None) or id(subject)}:r{int(radius or 1)}",
        "label": f"proximity:{getattr(subject, 'key', getattr(subject, 'id', 'subject'))}:r{int(radius or 1)}",
    }


def _zone_source(subject, zone_key):
    return {
        "type": "zone-subject",
        "id": f"{getattr(subject, 'id', None) or id(subject)}:{str(zone_key or '').strip().lower()}",
        "label": f"zone:{getattr(subject, 'key', getattr(subject, 'id', 'subject'))}:{str(zone_key or '').strip().lower()}",
    }


def _direct_source(subject, channel="direct"):
    normalized_channel = str(channel or "direct").strip().lower() or "direct"
    return {
        "type": "direct-subject",
        "id": f"{getattr(subject, 'id', None) or id(subject)}:{normalized_channel}",
        "label": f"direct:{getattr(subject, 'key', getattr(subject, 'id', 'subject'))}:{normalized_channel}",
    }


def _scheduled_source(schedule_key=None, system="", job_id=None):
    normalized_system = str(system or "scheduler").strip().lower() or "scheduler"
    normalized_key = str(schedule_key or job_id or "").strip().lower()
    if not normalized_key:
        raise ValueError("Scheduled interest requires a scheduler key or job id.")
    return {
        "type": "scheduled-job",
        "id": normalized_key,
        "label": f"scheduled:{normalized_system}:{normalized_key}",
    }


def _remove_source_everywhere(source):
    normalized_source_key = _source_key(source)
    deactivated = []
    with _LOCK:
        for record in list(_INTEREST_REGISTRY.values()):
            was_active = bool(record.get("sources"))
            record.get("sources", {}).pop(normalized_source_key, None)
            if was_active and not record.get("sources"):
                obj = record.get("object_ref")() if record.get("object_ref") else None
                if obj is not None:
                    deactivated.append(obj)
                _prune_record_if_empty(record)
    for obj in deactivated:
        _record_transition("deactivate", obj, 0)
        _call_hook(obj, "on_deactivate")


def _call_hook(obj, hook_name):
    if not is_enabled("interest_activation"):
        return
    hook = getattr(obj, hook_name, None)
    if not callable(hook):
        return
    try:
        hook()
    except Exception as error:
        logger.log_warn(f"[Interest] {hook_name} failed for {_object_key(obj)}: {error}")


def add_interest(obj, source, interest_type):
    if not is_enabled("interest_activation"):
        return []
    normalized_type = _normalize_interest_type(interest_type)
    normalized_source_key = _source_key(source)
    normalized_source_label = _source_label(source)

    with _LOCK:
        record = _get_record(obj, create=True)
        was_inactive = not bool(record["sources"])
        record["object_ref"] = weakref.ref(obj)
        record["object_label"] = getattr(obj, "key", None) or record["object_key"]
        record["sources"][normalized_source_key] = {
            "type": normalized_type,
            "source": normalized_source_label,
            "source_key": normalized_source_key,
            "added_at": time.time(),
        }
        _refresh_interest_gauges()

    increment_counter(f"interest.source.add.{normalized_type}")

    if was_inactive:
        _record_transition("activate", obj, len(get_activation_sources(obj)))
        _call_hook(obj, "on_activate")

    return get_activation_sources(obj)


def remove_interest(obj, source):
    if not is_enabled("interest_activation"):
        return []
    normalized_source_key = _source_key(source)

    removed_type = None
    with _LOCK:
        record = _get_record(obj, create=False)
        if not record:
            return []
        was_active = bool(record["sources"])
        removed = record["sources"].pop(normalized_source_key, None)
        removed_type = str((removed or {}).get("type", "") or "").strip().lower() or None
        is_now_inactive = not bool(record["sources"])
        remaining = [dict(entry) for entry in sorted(record["sources"].values(), key=lambda item: (item["type"], item["source"]))]
        if is_now_inactive:
            _prune_record_if_empty(record)

    if removed_type:
        increment_counter(f"interest.source.remove.{removed_type}")

    if was_active and is_now_inactive:
        _record_transition("deactivate", obj, 0)
        _call_hook(obj, "on_deactivate")

    return remaining


def get_activation_sources(obj):
    if not is_enabled("interest_activation"):
        return []
    with _LOCK:
        record = _get_record(obj, create=False)
        if not record:
            return []
        return [dict(entry) for entry in sorted(record["sources"].values(), key=lambda item: (item["type"], item["source"]))]


def is_active(obj) -> bool:
    if not is_enabled("interest_activation"):
        return True
    return bool(get_activation_sources(obj))


def get_adjacent_rooms(room, radius=1):
    return list(_iter_proximity_rooms(room, radius=radius))


def get_zone_rooms(room):
    return list(_iter_zone_rooms(room))


def get_active_objects():
    if not is_enabled("interest_activation"):
        return []
    with _LOCK:
        active_objects = []
        stale_keys = []
        for object_key, record in _INTEREST_REGISTRY.items():
            obj = record.get("object_ref")() if record.get("object_ref") else None
            if obj is None:
                stale_keys.append(object_key)
                continue
            if record.get("sources"):
                active_objects.append(obj)
        for object_key in stale_keys:
            _INTEREST_REGISTRY.pop(object_key, None)
        _refresh_interest_gauges()
        return active_objects


def clear_room_interest(subject, room=None):
    if not is_enabled("interest_activation"):
        return
    target_room = room if room is not None else getattr(subject, "location", None)
    source = _room_source(subject)
    for target in _iter_room_targets(target_room):
        remove_interest(target, source)


def clear_proximity_interest(subject, room=None, radius=1):
    if not is_enabled("interest_activation"):
        return
    target_room = room if room is not None else getattr(subject, "location", None)
    source = _proximity_source(subject, radius=radius)
    for target in _iter_proximity_targets(target_room, radius=radius):
        remove_interest(target, source)


def clear_zone_interest(subject, room=None):
    if not is_enabled("interest_activation"):
        return
    target_room = room if room is not None else getattr(subject, "location", None)
    zone_key = _get_zone_key(target_room)
    if not zone_key:
        return
    source = _zone_source(subject, zone_key)
    for target in _iter_zone_targets(target_room):
        remove_interest(target, source)


def clear_direct_interest(subject, channel="direct"):
    if not is_enabled("interest_activation"):
        return
    _remove_source_everywhere(_direct_source(subject, channel=channel))


def add_scheduled_interest(obj, schedule_key=None, system="", job_id=None):
    if not is_enabled("interest_activation"):
        return []
    return add_interest(obj, _scheduled_source(schedule_key=schedule_key, system=system, job_id=job_id), SCHEDULED)


def remove_scheduled_interest(obj, schedule_key=None, system="", job_id=None):
    if not is_enabled("interest_activation"):
        return []
    return remove_interest(obj, _scheduled_source(schedule_key=schedule_key, system=system, job_id=job_id))


def sync_room_interest(subject, previous_room=None):
    if not is_enabled("interest_activation"):
        return
    source = _room_source(subject)
    for target in _iter_room_targets(previous_room):
        remove_interest(target, source)
    current_room = getattr(subject, "location", None)
    for target in _iter_room_targets(current_room):
        add_interest(target, source, ROOM)


def sync_proximity_interest(subject, previous_room=None, radius=1):
    if not is_enabled("interest_activation"):
        return
    source = _proximity_source(subject, radius=radius)
    for target in _iter_proximity_targets(previous_room, radius=radius):
        remove_interest(target, source)
    current_room = getattr(subject, "location", None)
    for target in _iter_proximity_targets(current_room, radius=radius):
        add_interest(target, source, PROXIMITY)


def sync_zone_interest(subject, previous_room=None):
    if not is_enabled("interest_activation"):
        return
    previous_zone_key = _get_zone_key(previous_room)
    current_room = getattr(subject, "location", None)
    current_zone_key = _get_zone_key(current_room)

    if previous_zone_key and previous_zone_key != current_zone_key:
        previous_source = _zone_source(subject, previous_zone_key)
        for target in _iter_zone_targets(previous_room):
            remove_interest(target, previous_source)

    if not current_zone_key:
        return
    if current_zone_key == previous_zone_key:
        return

    current_source = _zone_source(subject, current_zone_key)
    for target in _iter_zone_targets(current_room):
        add_interest(target, current_source, ZONE)


def sync_direct_interest(subject, targets, channel="direct"):
    if not is_enabled("interest_activation"):
        return
    source = _direct_source(subject, channel=channel)
    _remove_source_everywhere(source)
    for target in list(targets or []):
        if target is None:
            continue
        add_interest(target, source, DIRECT)


@contextmanager
def direct_interest(subject, targets, channel="direct"):
    sync_direct_interest(subject, targets, channel=channel)
    try:
        yield
    finally:
        clear_direct_interest(subject, channel=channel)


def clear_subject_interest(subject):
    if not is_enabled("interest_activation"):
        return
    _remove_source_everywhere(_room_source(subject))
    _remove_source_everywhere(_proximity_source(subject, radius=1))
    current_room = getattr(subject, "location", None)
    zone_key = _get_zone_key(current_room)
    if zone_key:
        _remove_source_everywhere(_zone_source(subject, zone_key))


def sync_subject_interest(subject, previous_room=None):
    if not is_enabled("interest_activation"):
        return
    sync_room_interest(subject, previous_room=previous_room)
    sync_proximity_interest(subject, previous_room=previous_room, radius=1)
    sync_zone_interest(subject, previous_room=previous_room)


def get_interest_snapshot():
    with _LOCK:
        snapshot = []
        stale_keys = []
        for object_key, record in _INTEREST_REGISTRY.items():
            obj = record.get("object_ref")() if record.get("object_ref") else None
            if obj is None:
                stale_keys.append(object_key)
                continue
            snapshot.append(
                {
                    "object_key": object_key,
                    "object_label": getattr(obj, "key", None) or record.get("object_label") or object_key,
                    "active": bool(record.get("sources")),
                    "sources": [
                        dict(entry)
                        for entry in sorted(record.get("sources", {}).values(), key=lambda item: (item["type"], item["source"]))
                    ],
                }
            )
        for object_key in stale_keys:
            _INTEREST_REGISTRY.pop(object_key, None)
        return sorted(snapshot, key=lambda item: item["object_label"].lower())


def collect_interest_debug(max_objects=25):
    interest_snapshot = list(get_interest_snapshot() or [])
    runtime_metrics = dict(snapshot_metrics() or {})
    runtime_counters = dict(runtime_metrics.get("counters", {}) or {})
    runtime_gauges = dict(runtime_metrics.get("gauges", {}) or {})

    source_types = sorted(VALID_INTEREST_TYPES)
    active_objects = [entry for entry in interest_snapshot if bool(entry.get("active"))]
    source_counts = {
        source_type: int(runtime_gauges.get(f"interest.source.current.{source_type}", 0) or 0)
        for source_type in source_types
    }
    source_peak_counts = {
        source_type: int(runtime_gauges.get(f"interest.source.peak.{source_type}", 0) or 0)
        for source_type in source_types
    }
    transition_counts = {
        "activate": int(runtime_counters.get("interest.transition.activate", 0) or 0),
        "deactivate": int(runtime_counters.get("interest.transition.deactivate", 0) or 0),
    }

    return {
        "interest_enabled": bool(is_enabled("interest_activation")),
        "active_object_count": int(runtime_gauges.get("interest.active_object_count", len(active_objects)) or 0),
        "active_object_peak": int(runtime_gauges.get("interest.active_object_peak", len(active_objects)) or 0),
        "source_count_current": int(runtime_gauges.get("interest.source_count.current", 0) or 0),
        "source_count_peak": int(runtime_gauges.get("interest.source_count.peak", 0) or 0),
        "transition_counts": transition_counts,
        "source_counts": source_counts,
        "source_peak_counts": source_peak_counts,
        "active_objects": active_objects[: max(0, int(max_objects or 0))],
        "active_object_overflow": max(0, len(active_objects) - max(0, int(max_objects or 0))),
    }


def render_interest_debug_text(report):
    payload = dict(report or {})
    lines = ["Interest Debug"]
    lines.append(f"interest_activation: {'ON' if payload.get('interest_enabled') else 'OFF'}")
    lines.append(
        f"active objects: {int(payload.get('active_object_count', 0) or 0)} (peak {int(payload.get('active_object_peak', 0) or 0)})"
    )
    lines.append(
        f"sources: {int(payload.get('source_count_current', 0) or 0)} (peak {int(payload.get('source_count_peak', 0) or 0)})"
    )

    transition_counts = dict(payload.get("transition_counts", {}) or {})
    lines.append(
        f"transitions: activate={int(transition_counts.get('activate', 0) or 0)} deactivate={int(transition_counts.get('deactivate', 0) or 0)}"
    )

    lines.append("source types:")
    source_counts = dict(payload.get("source_counts", {}) or {})
    source_peak_counts = dict(payload.get("source_peak_counts", {}) or {})
    for source_type in sorted(VALID_INTEREST_TYPES):
        lines.append(
            f"  {source_type}: current={int(source_counts.get(source_type, 0) or 0)} peak={int(source_peak_counts.get(source_type, 0) or 0)}"
        )

    active_objects = list(payload.get("active_objects", []) or [])
    lines.append(f"active object details: {len(active_objects)}")
    for entry in active_objects:
        sources = list(entry.get("sources", []) or [])
        if not sources:
            lines.append(f"  {entry.get('object_label') or entry.get('object_key')}: no active sources")
            continue
        source_bits = [f"{source.get('type')}:{source.get('source')}" for source in sources]
        lines.append(f"  {entry.get('object_label') or entry.get('object_key')}: {', '.join(source_bits)}")

    overflow = int(payload.get("active_object_overflow", 0) or 0)
    if overflow > 0:
        lines.append(f"  ... {overflow} more active objects")

    return "\n".join(lines)