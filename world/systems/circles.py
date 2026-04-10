"""Central profession circle requirements."""

EMPATH_CIRCLE_REQUIREMENT_ANCHORS = {
    1: 0,
    2: 10,
    3: 20,
    4: 30,
    5: 40,
    6: 50,
    7: 65,
    8: 80,
    9: 95,
    10: 110,
    15: 185,
    20: 290,
    25: 395,
    30: 500,
}

EMPATH_CIRCLE_LOCATION_REQUIRED = False
EMPATH_CIRCLE_LOCATION_TAGS = ("guild_empath", "empath_guild", "empath_circle")
EMPATH_CIRCLE_LOCATION_FLAGS = ("empath_circle_room", "empath_guild_room")


def _interpolate_circle_requirements(anchors):
    ordered = sorted((int(circle), int(rank)) for circle, rank in dict(anchors or {}).items())
    requirements = {}
    for index, (start_circle, start_rank) in enumerate(ordered):
        requirements[start_circle] = {"empathy": start_rank}
        if index >= len(ordered) - 1:
            continue
        end_circle, end_rank = ordered[index + 1]
        span = max(1, end_circle - start_circle)
        for step in range(1, span):
            circle = start_circle + step
            ratio = float(step) / float(span)
            rank = int(round(start_rank + ((end_rank - start_rank) * ratio)))
            requirements[circle] = {"empathy": rank}
    return requirements


CIRCLE_REQUIREMENTS = _interpolate_circle_requirements(EMPATH_CIRCLE_REQUIREMENT_ANCHORS)


def get_circle_requirements(circle):
    circle_number = max(1, int(circle or 1))
    return dict(CIRCLE_REQUIREMENTS.get(circle_number, {}))


def get_highest_configured_circle():
    return max(CIRCLE_REQUIREMENTS) if CIRCLE_REQUIREMENTS else 1


def is_circle_location_enforced():
    return bool(EMPATH_CIRCLE_LOCATION_REQUIRED)


def is_valid_empath_circle_location(character, room=None):
    current_room = room or getattr(character, "location", None)
    if not current_room:
        return False, "You must be standing somewhere real before you can circle."
    for attr_name in EMPATH_CIRCLE_LOCATION_FLAGS:
        raw_value = getattr(getattr(current_room, "db", None), attr_name, None)
        if isinstance(raw_value, str):
            if str(raw_value).strip():
                return True, None
        elif raw_value:
            return True, None
    for tag_name in EMPATH_CIRCLE_LOCATION_TAGS:
        try:
            if current_room.tags.has(tag_name):
                return True, None
        except Exception:
            continue
    if hasattr(character, "is_empath_join_room") and character.is_empath_join_room(current_room):
        return True, None
    return False, "You must be in an Empath guild space to circle."