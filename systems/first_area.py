import time
from collections.abc import Mapping


OUTER_YARD = "Outer Yard"
MARKET_APPROACH = "Market Approach"
SIDE_PASSAGE = "Side Passage"
FIRST_AREA_ROOM_NAMES = {OUTER_YARD, MARKET_APPROACH, SIDE_PASSAGE}

THRESHOLD_VENDOR_KEY = "Street Vendor"
FREE_VENDOR_ITEM = "trail bread"
WAYFINDER_TOKEN = "wayfinder token"

VENDOR_PROMPT_LINES = (
    "You look new.",
    "If you need something, say so.",
)
VENDOR_PROMPT_PAUSE = "A pause, not unkind."
FIRST_PURCHASE_MESSAGE = "The exchange is simple. Uneventful.\n\nBut it works."
SIDE_PASSAGE_DISCOVERY_MESSAGE = "You close your hand around the token.\n\nWorth little. Still yours."


def _default_state():
    return {
        "visited_rooms": [],
        "entered_threshold": False,
        "vendor_prompted": False,
        "vendor_interacted": False,
    }


def ensure_state(character):
    state = getattr(getattr(character, "db", None), "first_area_state", None)
    if not isinstance(state, Mapping):
        state = _default_state()
    else:
        normalized = _default_state()
        normalized.update(dict(state))
        normalized["visited_rooms"] = [str(room) for room in (normalized.get("visited_rooms") or []) if str(room or "").strip()]
        normalized["entered_threshold"] = bool(normalized.get("entered_threshold", False))
        normalized["vendor_prompted"] = bool(normalized.get("vendor_prompted", False))
        normalized["vendor_interacted"] = bool(normalized.get("vendor_interacted", False))
        state = normalized
    character.db.first_area_state = state
    return state


def is_first_area_room(room):
    if not room:
        return False
    if bool(getattr(getattr(room, "db", None), "is_first_area", False)):
        return True
    return str(getattr(room, "key", "") or "") in FIRST_AREA_ROOM_NAMES


def is_in_first_area(character):
    return bool(character and is_first_area_room(getattr(character, "location", None)))


def handle_room_entry(character):
    if not character or bool(getattr(getattr(character, "db", None), "is_npc", False)):
        return False
    room = getattr(character, "location", None)
    if not is_first_area_room(room):
        return False
    state = ensure_state(character)
    room_key = str(getattr(room, "key", "") or "")
    visited = list(state.get("visited_rooms") or [])
    if room_key not in visited:
        visited.append(room_key)
    state["visited_rooms"] = visited
    if room_key == OUTER_YARD:
        state["entered_threshold"] = True
    state["last_room_entered_at"] = time.time()
    character.db.first_area_state = state
    return True


def _room_vendor(character):
    room = getattr(character, "location", None)
    if not room:
        return None
    for obj in list(getattr(room, "contents", []) or []):
        if bool(getattr(getattr(obj, "db", None), "is_threshold_vendor", False)):
            return obj
    return None


def emit_vendor_prompt(character, vendor=None):
    if not is_in_first_area(character):
        return False
    room = getattr(character, "location", None)
    if str(getattr(room, "key", "") or "") != MARKET_APPROACH:
        return False
    state = ensure_state(character)
    if bool(state.get("vendor_prompted", False)):
        return False
    vendor = vendor or _room_vendor(character)
    if not vendor:
        return False
    room.msg_contents(f'{vendor.key} says, "{VENDOR_PROMPT_LINES[0]}"', exclude=[])
    character.msg(VENDOR_PROMPT_PAUSE)
    room.msg_contents(f'{vendor.key} says, "{VENDOR_PROMPT_LINES[1]}"', exclude=[])
    state["vendor_prompted"] = True
    character.db.first_area_state = state
    return True


def should_prompt_vendor(character, idle_threshold=5.0):
    if not is_in_first_area(character):
        return False
    room = getattr(character, "location", None)
    if str(getattr(room, "key", "") or "") != MARKET_APPROACH:
        return False
    state = ensure_state(character)
    if bool(state.get("vendor_prompted", False)):
        return False
    last_entered = float(state.get("last_room_entered_at", 0.0) or 0.0)
    return (time.time() - last_entered) >= float(idle_threshold or 0.0)


def note_vendor_interaction(character, vendor=None, action=None):
    if not is_in_first_area(character):
        return False
    room = getattr(character, "location", None)
    if str(getattr(room, "key", "") or "") != MARKET_APPROACH:
        return False
    vendor = vendor or _room_vendor(character)
    if not vendor or not bool(getattr(getattr(vendor, "db", None), "is_threshold_vendor", False)):
        return False
    state = ensure_state(character)
    interaction = str(action or "").strip().lower()
    if interaction in {"shop", "buy"}:
        state["vendor_prompted"] = True
    if interaction == "buy" and not bool(state.get("vendor_interacted", False)):
        character.msg(FIRST_PURCHASE_MESSAGE)
        state["vendor_interacted"] = True
        character.db.first_area_state = state
        return True
    character.db.first_area_state = state
    return interaction in {"shop", "buy"}


def note_item_pickup(character, item):
    if not is_in_first_area(character):
        return False, ""
    room = getattr(character, "location", None)
    if str(getattr(room, "key", "") or "") != SIDE_PASSAGE:
        return False, ""
    item_key = str(getattr(item, "key", "") or "").strip().lower()
    if item_key != WAYFINDER_TOKEN:
        return False, ""
    character.msg(SIDE_PASSAGE_DISCOVERY_MESSAGE)
    state = ensure_state(character)
    state["found_side_passage_item"] = True
    character.db.first_area_state = state
    return True, SIDE_PASSAGE_DISCOVERY_MESSAGE


def get_status_lines(character):
    state = ensure_state(character)
    return [
        f"Visited: {', '.join(state.get('visited_rooms') or []) or 'none'}",
        f"Vendor prompted: {'yes' if state.get('vendor_prompted') else 'no'}",
        f"Vendor interacted: {'yes' if state.get('vendor_interacted') else 'no'}",
    ]