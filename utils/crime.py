def _is_guard(obj):
    role = str(getattr(getattr(obj, "db", None), "role", "") or "").lower()
    if "guard" in role:
        return True
    return False


def _iter_guard_candidates(room):
    if not room:
        return []

    seen_ids = set()
    candidates = []
    rooms = [room]
    exits = [obj for obj in room.contents if getattr(obj, "destination", None)]
    rooms.extend(exit_obj.destination for exit_obj in exits if getattr(exit_obj, "destination", None))

    for candidate_room in rooms:
        if not candidate_room:
            continue
        for obj in candidate_room.contents:
            if getattr(obj, "id", None) in seen_ids:
                continue
            if not _is_guard(obj):
                continue
            seen_ids.add(obj.id)
            candidates.append(obj)
    return candidates


def call_guards(room, culprit):
    responders = []
    if not room or not culprit:
        return responders

    for guard in _iter_guard_candidates(room):
        if hasattr(guard, "set_awareness"):
            guard.set_awareness("alert")
        if getattr(guard, "location", None) != room and hasattr(guard, "move_to"):
            guard.move_to(room, quiet=True, move_type="pursuit")
        if hasattr(guard, "set_target"):
            guard.set_target(culprit)
        if hasattr(guard, "set_state"):
            guard.set_state("last_seen_target", culprit.id)
        responders.append(guard)

    if responders:
        room.msg_contents("The alarm spreads quickly through the area.", exclude=[culprit])
    else:
        room.db.pending_guard_target = culprit.id

    return responders