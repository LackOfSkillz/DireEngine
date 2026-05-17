import time
from collections.abc import Mapping

from django.db import close_old_connections

from evennia.utils.create import create_object
from evennia.utils.search import search_object


RACCOON_COMPANION_TYPE = 101
WOLF_COMPANION_TYPE = 102

COMPANION_TYPE_REGISTRY = {
    RACCOON_COMPANION_TYPE: {
        "type_id": RACCOON_COMPANION_TYPE,
        "type": "raccoon",
        "species": "raccoon",
        "label": "Raccoon",
        "can_summon_in_urban": True,
        "bait_item": "corn",
        "follow_message": "Your raccoon chitters and pads after you.",
        "stay_message": "Your raccoon sits back on its haunches and watches.",
        "return_message": "Your raccoon scampers back to your side.",
        "sit_message": "Your raccoon settles into an alert crouch.",
        "stand_message": "Your raccoon rises and flicks its tail.",
        "hide_message": "Your raccoon slips into whatever cover it can find.",
        "unhide_message": "Your raccoon peeks back out and rejoins you.",
        "hunt_message": "Your raccoon darts off to prowl on its own.",
        "attack_message": "Your raccoon darts in to harry {target}.",
        "rescue_message": "Your raccoon circles back to guard what it found.",
        "tease_ready_message": "Your raccoon chatters at the sight of the corn and reaches for it.",
        "tease_wrong_item_message": "Your raccoon sniffs the offering, unimpressed.",
        "tease_blocked_message": "Your raccoon ignores the game while the city presses in on the bond.",
    },
    WOLF_COMPANION_TYPE: {
        "type_id": WOLF_COMPANION_TYPE,
        "type": "wolf",
        "species": "wolf",
        "label": "Wolf",
        "can_summon_in_urban": False,
        "bait_item": "meat",
        "follow_message": "Your wolf falls into step at your side.",
        "stay_message": "Your wolf plants itself and waits.",
        "return_message": "Your wolf lopes back to your side.",
        "sit_message": "Your wolf lowers onto its haunches without taking its eyes off the wilds.",
        "stand_message": "Your wolf rises in a smooth, ready motion.",
        "hide_message": "Your wolf melts low into the brush.",
        "unhide_message": "Your wolf emerges from cover and watches you closely.",
        "hunt_message": "Your wolf ranges ahead, nose to the wind.",
        "attack_message": "Your wolf lunges at {target}.",
        "rescue_message": "Your wolf stands over what it found and lets out a low warning growl.",
        "tease_ready_message": "Your wolf's ears prick forward at the scent of the meat.",
        "tease_wrong_item_message": "Your wolf sniffs once and turns away.",
        "tease_blocked_message": "Your wolf refuses the play while the bond lies choked by stone and noise.",
    },
}

COMPANION_TYPE_LOOKUP = {
    "101": RACCOON_COMPANION_TYPE,
    "102": WOLF_COMPANION_TYPE,
    "raccoon": RACCOON_COMPANION_TYPE,
    "wolf": WOLF_COMPANION_TYPE,
}

COMPANION_STATE_DISMISSED = "dismissed"
COMPANION_STATE_PRESENT = "present"
COMPANION_STATE_WANDERING = "wandering"
COMPANION_STATE_RETURNING = "returning"
COMPANION_STATE_SEARCHING = "searching"

VALID_COMPANION_STATES = {
    "active": COMPANION_STATE_PRESENT,
    "inactive": COMPANION_STATE_DISMISSED,
    COMPANION_STATE_DISMISSED: COMPANION_STATE_DISMISSED,
    COMPANION_STATE_PRESENT: COMPANION_STATE_PRESENT,
    COMPANION_STATE_WANDERING: COMPANION_STATE_WANDERING,
    COMPANION_STATE_RETURNING: COMPANION_STATE_RETURNING,
    COMPANION_STATE_SEARCHING: COMPANION_STATE_SEARCHING,
}

DEFAULT_RANGER_COMPANION = {
    "type_id": WOLF_COMPANION_TYPE,
    "type": "wolf",
    "species": "wolf",
    "name": "wolf",
    "state": COMPANION_STATE_DISMISSED,
    "bond": 50,
    "entity_id": None,
    "owner_id": None,
}


def _coerce_int(value, default=None):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def resolve_companion_type_id(value, default=WOLF_COMPANION_TYPE):
    if isinstance(value, Mapping):
        value = value.get("type_id", value.get("type", value.get("species")))
    if hasattr(value, "db"):
        value = getattr(getattr(value, "db", None), "companion_type_id", None)
    if isinstance(value, int) and value in COMPANION_TYPE_REGISTRY:
        return value
    normalized = str(value or "").strip().lower()
    return COMPANION_TYPE_LOOKUP.get(normalized, default)


def get_companion_profile(value=None):
    return dict(COMPANION_TYPE_REGISTRY[resolve_companion_type_id(value)])


def validate_companion_type(value):
    normalized = str(value or "").strip().lower()
    if normalized and normalized not in COMPANION_TYPE_LOOKUP:
        raise ValueError(f"Unsupported Ranger companion type: {value}")
    return resolve_companion_type_id(value)


def _resolve_object_id(value):
    if hasattr(value, "id"):
        return _coerce_int(getattr(value, "id", None), None)
    if isinstance(value, Mapping):
        return _resolve_object_id(value.get("entity_id", value.get("owner_id")))
    if isinstance(value, str) and value.startswith("#"):
        value = value[1:]
    return _coerce_int(value, None)


def resolve_companion_entity(reference):
    entity_id = _resolve_object_id(reference)
    if not entity_id:
        return None
    result = search_object(f"#{entity_id}")
    return result[0] if result else None


def build_companion_record(data=None, *, entity=None, owner=None):
    payload = dict(DEFAULT_RANGER_COMPANION)
    if isinstance(data, Mapping):
        payload.update(dict(data))

    resolved_entity = entity or resolve_companion_entity(payload.get("entity_id") or payload)
    resolved_owner = owner
    if resolved_entity is not None:
        entity_payload = {
            "entity_id": getattr(resolved_entity, "id", None),
            "owner_id": getattr(getattr(resolved_entity, "db", None), "owner_id", None),
            "bond": getattr(getattr(resolved_entity, "db", None), "bond", None),
            "state": getattr(getattr(resolved_entity, "db", None), "companion_state", None),
            "type_id": getattr(getattr(resolved_entity, "db", None), "companion_type_id", None),
        }
        for key, value in entity_payload.items():
            if value is not None:
                payload[key] = value
    if resolved_owner is not None:
        payload["owner_id"] = getattr(resolved_owner, "id", None)

    profile = get_companion_profile(payload)
    state = VALID_COMPANION_STATES.get(str(payload.get("state", COMPANION_STATE_DISMISSED) or COMPANION_STATE_DISMISSED).strip().lower(), COMPANION_STATE_DISMISSED)
    bond = max(0, min(100, _coerce_int(payload.get("bond"), 50) or 50))
    return {
        "type_id": profile["type_id"],
        "type": profile["type"],
        "species": profile["species"],
        "name": profile["type"],
        "label": profile["label"],
        "state": state,
        "bond": bond,
        "entity_id": _resolve_object_id(payload.get("entity_id")),
        "owner_id": _resolve_object_id(payload.get("owner_id")),
    }


def normalize_ranger_companion(data=None):
    if hasattr(data, "db") and not isinstance(data, Mapping):
        entity = None
        owner_record = getattr(getattr(data, "db", None), "ranger_companion", None)
        if isinstance(owner_record, Mapping):
            entity = resolve_companion_entity(owner_record.get("entity_id"))
        return build_companion_record(owner_record, entity=entity, owner=data)
    return build_companion_record(data)


def is_companion_active(data=None):
    return normalize_ranger_companion(data).get("state") == COMPANION_STATE_PRESENT


def get_companion_tracking_bonus(data=None):
    companion = normalize_ranger_companion(data)
    if companion["state"] != COMPANION_STATE_PRESENT:
        return 0
    return 4 + int(companion["bond"] / 25)


def get_companion_awareness_bonus(data=None):
    companion = normalize_ranger_companion(data)
    if companion["state"] != COMPANION_STATE_PRESENT:
        return 0
    return 2 + int(companion["bond"] / 34)


def get_companion_label(data=None):
    return str(normalize_ranger_companion(data).get("label", "Wolf") or "Wolf")


def get_owner_companion_entity(owner):
    if owner is None:
        return None
    return resolve_companion_entity(getattr(getattr(owner, "db", None), "ranger_companion", None))


def sync_owner_companion_record(owner, *, entity=None, data=None):
    record = build_companion_record(data or getattr(getattr(owner, "db", None), "ranger_companion", None), entity=entity, owner=owner)
    owner.db.ranger_companion = record
    return record


def clear_owner_companion_record(owner, *, fallback=None):
    record = build_companion_record(fallback, owner=owner)
    record["entity_id"] = None
    record["state"] = COMPANION_STATE_DISMISSED
    owner.db.ranger_companion = record
    return record


def _create_ranger_companion_entity(owner, profile, bond):
    location = getattr(owner, "location", None)
    home = getattr(owner, "home", None) or location
    companion = create_object(
        "typeclasses.npcs.RangerCompanion",
        key=profile["label"],
        location=location,
        home=home,
        nohome=home is None,
    )
    companion.configure_companion(owner=owner, type_id=profile["type_id"], bond=bond, state=COMPANION_STATE_PRESENT)
    return companion


def call_ranger_companion(owner, species=None):
    if species is not None:
        normalized_species = str(species or "").strip().lower()
        if normalized_species and normalized_species not in COMPANION_TYPE_LOOKUP:
            return False, "Only a raccoon or wolf answers a Ranger's call.", normalize_ranger_companion(getattr(getattr(owner, "db", None), "ranger_companion", None))
    record = normalize_ranger_companion(getattr(getattr(owner, "db", None), "ranger_companion", None))
    profile = get_companion_profile(species or record)

    terrain = str(getattr(owner, "get_ranger_terrain_type", lambda: "urban")() or "urban").strip().lower()
    if terrain == "urban" and not bool(profile.get("can_summon_in_urban", False)):
        return False, "The press of the city keeps your wolf from answering.", record

    entity = get_owner_companion_entity(owner)
    if entity is not None:
        entity_type_id = resolve_companion_type_id(entity)
        if entity_type_id != profile["type_id"]:
            entity.delete()
            entity = None
        elif getattr(entity, "location", None) == getattr(owner, "location", None) and str(getattr(getattr(entity, "db", None), "companion_state", "") or "") == COMPANION_STATE_PRESENT:
            record = sync_owner_companion_record(owner, entity=entity)
            return False, f"Your {record['type']} is already with you.", record

    if entity is None:
        entity = _create_ranger_companion_entity(owner, profile, int(record.get("bond", 50) or 50))
    else:
        entity.configure_companion(owner=owner, type_id=profile["type_id"], bond=int(record.get("bond", 50) or 50), state=COMPANION_STATE_PRESENT)
        if getattr(owner, "location", None) is not None and getattr(entity, "location", None) != getattr(owner, "location", None):
            entity.move_to(owner.location, quiet=True, move_type="summon")

    record = sync_owner_companion_record(owner, entity=entity)
    return True, f"A {record['type']} emerges from the wild and joins you.", record


def dismiss_ranger_companion(owner):
    record = normalize_ranger_companion(getattr(getattr(owner, "db", None), "ranger_companion", None))
    entity = get_owner_companion_entity(owner)
    if entity is None and record.get("state") != COMPANION_STATE_PRESENT:
        return False, "Your companion is not currently with you.", record

    if entity is not None:
        if hasattr(entity, "clear_owner"):
            entity.clear_owner()
        delete_error = None
        for _attempt in range(3):
            close_old_connections()
            try:
                entity.delete()
                delete_error = None
                break
            except Exception as error:
                delete_error = error
                if "database is locked" not in str(error or "").lower():
                    raise
                time.sleep(0.1)
        if delete_error is not None:
            raise delete_error

    record = clear_owner_companion_record(owner, fallback=record)
    return True, f"Your {record['type']} slips back into the wild.", record