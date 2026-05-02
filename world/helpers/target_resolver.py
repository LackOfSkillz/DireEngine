import time
import re

from world.helpers.display_aggregation import strip_article
from world.helpers.ordinals import split_ordinal_target


_LEADING_QUANTITY_RE = re.compile(r"^(?P<quantity>\d+)\s+(?P<name>.+)$")


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _candidate_names(obj):
    names = []
    key = str(getattr(obj, "key", "") or "").strip().lower()
    if key:
        names.append(key)

    aliases = getattr(obj, "aliases", None)
    if aliases and hasattr(aliases, "all"):
        try:
            names.extend(str(alias).strip().lower() for alias in aliases.all())
        except Exception:
            pass
    return [name for name in names if name]


def normalize_target_query(query):
    text = str(query or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered.startswith("my "):
        text = text[3:].strip()
        lowered = text.lower()
    if lowered.startswith("other "):
        return text
    return strip_article(text)


def get_item_recency_key(obj):
    db = getattr(obj, "db", None)
    arrival_rank = float(getattr(db, "mt516_arrived_at", 0.0) or 0.0)
    created_value = getattr(obj, "db_date_created", 0) or 0
    if hasattr(created_value, "timestamp"):
        try:
            created_rank = float(created_value.timestamp())
        except Exception:
            created_rank = 0.0
    else:
        created_rank = float(created_value or 0)
    object_id = _safe_int(getattr(obj, "id", 0), 0)
    return (arrival_rank, created_rank, object_id)


def _is_character(obj):
    if obj is None or not hasattr(obj, "is_typeclass"):
        return False
    try:
        return bool(obj.is_typeclass("typeclasses.characters.Character", exact=False))
    except Exception:
        return False


def _is_exit(obj):
    if obj is None or not hasattr(obj, "is_typeclass"):
        return False
    try:
        return bool(obj.is_typeclass("typeclasses.exits.Exit", exact=False))
    except Exception:
        return False


def _is_npc(obj):
    return bool(getattr(getattr(obj, "db", None), "is_npc", False))


def _can_detect(caller, obj):
    if caller is None or obj is None:
        return False
    if hasattr(caller, "can_detect"):
        try:
            return bool(caller.can_detect(obj))
        except Exception:
            return False
    return True


def _get_inventory_candidates(caller):
    if caller is None:
        return []
    if hasattr(caller, "merge_stackable_inventory"):
        try:
            caller.merge_stackable_inventory()
        except Exception:
            pass
    if hasattr(caller, "get_visible_carried_items"):
        try:
            return list(caller.get_visible_carried_items() or [])
        except Exception:
            return []
    return [
        obj for obj in list(getattr(caller, "contents", []) or [])
        if getattr(getattr(obj, "db", None), "worn_by", None) != caller
    ]


def _get_room_candidates(caller):
    room = getattr(caller, "location", None)
    if room is None:
        return []
    candidates = []
    for obj in list(getattr(room, "contents", []) or []):
        if obj == caller or _is_character(obj) or _is_exit(obj):
            continue
        candidates.append(obj)
    return candidates


def _get_character_candidates(caller):
    room = getattr(caller, "location", None)
    if room is None:
        return []
    candidates = []
    for obj in list(getattr(room, "contents", []) or []):
        if obj == caller or not _is_character(obj):
            continue
        if not _can_detect(caller, obj):
            continue
        candidates.append(obj)
    return candidates


def get_scope_candidates(caller, scope):
    normalized = str(scope or "").strip().lower()
    if normalized == "inventory":
        return _get_inventory_candidates(caller)
    if normalized == "room":
        return _get_room_candidates(caller)
    if normalized == "characters":
        return _get_character_candidates(caller)
    if normalized == "npcs":
        return [obj for obj in _get_character_candidates(caller) if _is_npc(obj)]
    return []


def mark_item_arrival(obj):
    if obj is None or not hasattr(obj, "db"):
        return None
    stamp = time.time()
    obj.db.mt516_arrived_at = stamp
    return stamp


def get_name_matches(query, candidates):
    target = normalize_target_query(query).lower()
    if not target:
        return []

    exact = []
    partial = []
    contains = []
    for obj in list(candidates or []):
        names = _candidate_names(obj)
        if not names:
            continue
        if target in names:
            exact.append(obj)
            continue
        if any(name.startswith(target) for name in names):
            partial.append(obj)
            continue
        if any(target in name for name in names):
            contains.append(obj)

    sorter = lambda item: get_item_recency_key(item)
    return sorted(exact, key=sorter, reverse=True) or sorted(partial, key=sorter, reverse=True) or sorted(contains, key=sorter, reverse=True)


def resolve_item_target(query, candidates, default_first=True):
    raw_query = str(query or "").strip()
    index, base_query = split_ordinal_target(raw_query)
    if raw_query.lower().startswith("other "):
        index = 2
        base_query = raw_query[6:].strip()
    base_query = normalize_target_query(base_query)

    matches = get_name_matches(base_query, candidates)
    if not matches:
        return None, matches, base_query, index

    if index is not None:
        if len(matches) == 1:
            stack = matches[0]
            if hasattr(stack, "is_stackable") and stack.is_stackable() and hasattr(stack, "get_stack_quantity"):
                quantity = max(1, int(stack.get_stack_quantity() or 1))
                if 1 <= index <= quantity:
                    return stack, matches, base_query, index
        if 1 <= index <= len(matches):
            return matches[index - 1], matches, base_query, index
        return None, matches, base_query, index

    if default_first or len(matches) == 1:
        return matches[0], matches, base_query, index

    return None, matches, base_query, index


def format_item_matches(query, matches, looker=None):
    base_query = str(query or "").strip()
    if not matches:
        return ""
    lines = [f"More than one match for '{base_query}'. Try 'first {base_query}', 'second {base_query}', or '2.{base_query}':"]
    for index, match in enumerate(matches, start=1):
        if hasattr(match, "get_display_name"):
            name = match.get_display_name(looker)
        else:
            name = getattr(match, "key", str(match))
        lines.append(f" {index}. {name}")
    return "\n".join(lines)


def resolve_target(query, caller, scopes=("characters", "room", "inventory"), default_first=True):
    for scope in tuple(scopes or ()): 
        candidates = get_scope_candidates(caller, scope)
        target, matches, base_query, index = resolve_item_target(query, candidates, default_first=default_first)
        if target is not None or matches:
            return target, matches, base_query, index, str(scope or "")

    raw_query = str(query or "").strip()
    index, base_query = split_ordinal_target(raw_query)
    if raw_query.lower().startswith("other "):
        index = 2
        base_query = raw_query[6:].strip()
    return None, [], normalize_target_query(base_query), index, None


def split_quantity_target(query):
    text = str(query or "").strip()
    if not text or "." in text.split(None, 1)[0]:
        return None, text
    match = _LEADING_QUANTITY_RE.match(text)
    if not match:
        return None, text
    return max(1, int(match.group("quantity"))), match.group("name").strip()