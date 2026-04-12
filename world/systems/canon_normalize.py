import copy


DEFAULT_DOCILE_FLEE_PROFILE = {
    "threshold": 0.7,
    "chance": 0.6,
}

GUARD_KEYWORDS = (
    "guard",
    "guardian",
    "sentry",
    "watchman",
    "watchwoman",
    "constable",
    "marshal",
    "patrol",
    "soldier",
    "captain",
)

SHOPKEEPER_KEYWORDS = (
    "merchant",
    "trader",
    "shopkeeper",
    "bartender",
    "barkeep",
    "innkeeper",
    "proprietor",
    "clerk",
)

CIVILIAN_KEYWORDS = (
    "beggar",
    "sailor",
    "farmer",
    "villager",
    "citizen",
)


def normalize_item(item):
    record = dict(item or {})
    raw_tags = list(record.get("tags") or [])
    normalized = {
        "category": record.get("category"),
        "item_type": record.get("item_type") or record.get("category"),
        "tags": list(raw_tags),
        "damage_profile": copy.deepcopy(record.get("damage_profile")),
        "protection_profile": copy.deepcopy(record.get("protection_profile")),
        "slot": record.get("slot"),
        "capacity": copy.deepcopy(record.get("capacity_json")),
        "restrictions": copy.deepcopy(record.get("restrictions_json")),
        "value": record.get("value_num"),
        "value_text": record.get("value_text"),
        "allowed_slots": [record.get("slot")] if record.get("slot") else [],
    }
    warnings = []
    applied_defaults = []

    category = str(record.get("category") or "").strip().lower()
    if category == "weapon" and _is_missing(normalized.get("damage_profile")):
        normalized["damage_profile"] = {
            "slice": None,
            "puncture": None,
            "impact": None,
        }
        applied_defaults.append("damage_profile")
    if category == "armor" and _is_missing(normalized.get("protection_profile")):
        normalized["protection_profile"] = {
            "absorption": None,
            "protection": None,
        }
        applied_defaults.append("protection_profile")
    if category == "container":
        if "storage" not in normalized["tags"]:
            normalized["tags"].append("storage")
        if _is_missing(normalized.get("slot")):
            normalized["slot"] = None
        if _is_missing(normalized.get("capacity")):
            normalized["capacity"] = None
    if category == "clothing" and not normalized.get("allowed_slots"):
        normalized["allowed_slots"] = ["body"]
        applied_defaults.append("allowed_slots")

    if _is_missing(normalized.get("value_text")):
        normalized["value"] = None
        warnings.append("value")

    return {
        "fields": normalized,
        "warnings": warnings,
        "applied_defaults": applied_defaults,
    }


def normalize_actor(actor):
    record = dict(actor or {})
    raw_tags = list(record.get("tags") or [])
    classification = classify_actor(record)
    normalized = {
        "role": classification["role"],
        "classification_confidence": classification["confidence"],
        "aggression_type": record.get("aggression_type"),
        "flee_behavior": copy.deepcopy(record.get("flee_behavior")),
        "tags": list(dict.fromkeys(raw_tags + classification["tags"])),
        "shop_name": record.get("shop_name"),
        "actor_type": record.get("actor_type"),
        "npc_type": record.get("npc_type"),
    }
    warnings = list(classification["warnings"])
    applied_defaults = []

    role = normalized["role"]
    category = str(record.get("category") or "").strip().lower()

    if role == "guard" and _is_missing(normalized.get("aggression_type")):
        normalized["aggression_type"] = "defensive"
        applied_defaults.append("aggression_type")
    if role in {"guard", "civilian", "shopkeeper"} and normalized.get("actor_type") not in {"social"}:
        normalized["actor_type"] = "social"
        applied_defaults.append("actor_type")
    if role == "guard" and "law_enforcement" not in normalized["tags"]:
        normalized["tags"].append("law_enforcement")
    if category == "hostile_creature" and _is_missing(normalized.get("aggression_type")):
        normalized["aggression_type"] = "aggressive"
        applied_defaults.append("aggression_type")
    if category == "docile_creature" and _is_missing(normalized.get("flee_behavior")):
        normalized["flee_behavior"] = copy.deepcopy(DEFAULT_DOCILE_FLEE_PROFILE)
        applied_defaults.append("flee_behavior")
    if role == "civilian" and _is_missing(normalized.get("aggression_type")):
        normalized["aggression_type"] = "passive"
        applied_defaults.append("aggression_type")
    if _is_missing(normalized.get("aggression_type")):
        normalized["aggression_type"] = "defensive"
        applied_defaults.append("aggression_type")

    if normalized["classification_confidence"] < 0.5:
        warnings.append("low_classification_confidence")

    return {
        "fields": normalized,
        "warnings": warnings,
        "applied_defaults": applied_defaults,
    }


def normalize_shop(shop):
    record = dict(shop or {})
    raw_tags = list(record.get("tags") or [])
    normalized = {
        "name": record.get("name"),
        "shop_type": record.get("shop_type"),
        "owner_name": record.get("owner_name"),
        "tags": list(dict.fromkeys(raw_tags + ["shop"])),
        "classification_confidence": 1.0 if record.get("owner_name") else 0.6,
    }
    warnings = []
    if not record.get("owner_name"):
        warnings.append("missing_owner_name")
    return {
        "fields": normalized,
        "warnings": warnings,
        "applied_defaults": [],
    }


def classify_actor(entity):
    record = dict(entity or {})
    name = str(record.get("name") or "").strip().lower()
    actor_type = str(record.get("actor_type") or record.get("entity_type") or "").strip().lower()
    npc_type = str(record.get("npc_type") or "").strip().lower()
    occupation = str(record.get("occupation") or "").strip().lower()
    role_fact = str(record.get("role_fact") or "").strip().lower()
    category = str(record.get("category") or "").strip().lower()
    tags = []
    warnings = []

    if record.get("shop_name") or record.get("shop_owner"):
        return {
            "role": "shopkeeper",
            "confidence": 0.95,
            "tags": ["shopkeeper"],
            "warnings": warnings,
        }
    if category == "guard" or _contains_any(name, GUARD_KEYWORDS) or _contains_any(occupation, GUARD_KEYWORDS) or _contains_any(role_fact, GUARD_KEYWORDS):
        return {
            "role": "guard",
            "confidence": 0.85 if category == "guard" else 0.7,
            "tags": ["guard"],
            "warnings": warnings,
        }
    if category == "civilian" or _contains_any(name, SHOPKEEPER_KEYWORDS + CIVILIAN_KEYWORDS) or _contains_any(occupation, SHOPKEEPER_KEYWORDS + CIVILIAN_KEYWORDS):
        tags.append("civilian")
        if _contains_any(name, SHOPKEEPER_KEYWORDS) or _contains_any(occupation, SHOPKEEPER_KEYWORDS):
            return {
                "role": "shopkeeper",
                "confidence": 0.55,
                "tags": ["shopkeeper"],
                "warnings": ["shopkeeper_name_heuristic"],
            }
        return {
            "role": "civilian",
            "confidence": 0.7 if category == "civilian" else 0.55,
            "tags": tags,
            "warnings": warnings,
        }
    if category in {"hostile_creature", "docile_creature"} or npc_type in {"creature", "passive"}:
        return {
            "role": "creature",
            "confidence": 0.9,
            "tags": ["creature"],
            "warnings": warnings,
        }

    if actor_type in {"npc", "creature", "shop"}:
        warnings.append("fallback_actor_classification")
        return {
            "role": "civilian" if actor_type == "shop" else "creature" if actor_type == "creature" else "civilian",
            "confidence": 0.4,
            "tags": ["civilian"] if actor_type != "creature" else ["creature"],
            "warnings": warnings,
        }

    warnings.append("unclassified_actor")
    return {
        "role": "civilian",
        "confidence": 0.3,
        "tags": ["civilian"],
        "warnings": warnings,
    }


def _contains_any(text, keywords):
    value = str(text or "")
    return any(keyword in value for keyword in keywords)


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False