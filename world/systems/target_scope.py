from __future__ import annotations

from world.systems.engine_flags import is_enabled
from world.systems.interest import get_active_objects, get_adjacent_rooms, is_active


def _dedupe_targets(targets):
    unique = []
    seen_ids = set()
    for target in list(targets or []):
        target_id = getattr(target, "id", None)
        marker = target_id if target_id is not None else id(target)
        if marker in seen_ids:
            continue
        seen_ids.add(marker)
        unique.append(target)
    return unique


def _filter_targets(targets, predicate=None):
    filtered = []
    for target in _dedupe_targets(targets):
        if callable(predicate) and not predicate(target):
            continue
        filtered.append(target)
    return filtered


def get_visible_targets(caller, predicate=None):
    room = getattr(caller, "location", None)
    if room is None:
        return _filter_targets([caller], predicate=predicate)
    return _filter_targets(list(getattr(room, "contents", []) or []), predicate=predicate)


def get_nearby_targets(caller, predicate=None, radius=1):
    room = getattr(caller, "location", None)
    if room is None:
        return []
    targets = []
    for nearby_room in get_adjacent_rooms(room, radius=radius):
        targets.extend(list(getattr(nearby_room, "contents", []) or []))
    return _filter_targets(targets, predicate=predicate)


def get_active_targets(caller=None, predicate=None):
    if not is_enabled("interest_activation"):
        return []
    return _filter_targets([target for target in get_active_objects() if is_active(target)], predicate=predicate)