import random
import time


BUYER_RATE_LIMIT_SECONDS = 0.75
TROPHY_MIN_MULTIPLIER = 1.5
TROPHY_MAX_MULTIPLIER = 3.0
PROCESSED_FISH_ITEM_TYPES = {"fish_meat", "fish_skin"}
JUNK_ITEM_TYPES = {"junk"}

REGION_VALUE_MODIFIERS = {
    "river 1": 1.0,
    "river 2": 1.05,
    "river 3": 1.12,
    "ocean": 1.18,
}


def is_fish_item(item):
    if not item:
        return False
    item_type = str(getattr(getattr(item, "db", None), "item_type", "") or "").strip().lower()
    if item_type == "fish":
        return True
    return bool(getattr(getattr(item, "db", None), "fish_profile_key", None))


def is_processed_fish_item(item):
    if not item:
        return False
    item_type = str(getattr(getattr(item, "db", None), "item_type", "") or "").strip().lower()
    return item_type in PROCESSED_FISH_ITEM_TYPES


def is_junk_item(item):
    if not item:
        return False
    item_type = str(getattr(getattr(item, "db", None), "item_type", "") or "").strip().lower()
    return bool(getattr(getattr(item, "db", None), "is_junk", False)) or item_type in JUNK_ITEM_TYPES


def is_fish_trade_item(item):
    return is_fish_item(item) or is_processed_fish_item(item) or is_junk_item(item)


def is_fish_string(item):
    return bool(item and getattr(getattr(item, "db", None), "is_fish_string", False))


def get_region_value_modifier(fish_group):
    normalized = str(fish_group or "").strip().lower()
    return float(REGION_VALUE_MODIFIERS.get(normalized, 1.0))


def get_trophy_chance(fish_profile):
    difficulty = max(0.0, float((fish_profile or {}).get("difficulty", 0.0) or 0.0))
    chance = 0.03 + (difficulty / 1000.0)
    return max(0.03, min(0.12, chance))


def maybe_apply_trophy_metadata(fish, fish_profile, rng=None):
    rng = rng or random
    fish_profile = dict(fish_profile or {})
    is_trophy = float(rng.random()) < get_trophy_chance(fish_profile)
    fish.db.is_trophy = bool(is_trophy)
    if not is_trophy:
        fish.db.trophy_multiplier = 1.0
        return False

    multiplier = round(rng.uniform(TROPHY_MIN_MULTIPLIER, TROPHY_MAX_MULTIPLIER), 2)
    fish.db.trophy_multiplier = float(multiplier)
    fish.db.value = max(1, int(round(float(getattr(fish.db, "value", 1) or 1) * multiplier)))
    return True


def apply_region_value_modifier(fish):
    modifier = get_region_value_modifier(getattr(getattr(fish, "db", None), "fish_group", None))
    fish.db.region_value_multiplier = float(modifier)
    fish.db.value = max(1, int(round(float(getattr(fish.db, "value", 1) or 1) * modifier)))
    return int(getattr(fish.db, "value", 1) or 1)


def set_fish_economy_metadata(fish, fish_profile, rng=None):
    if not fish:
        return fish
    fish.db.item_type = "fish"
    fish.db.fish_type = str((fish_profile or {}).get("name", getattr(fish.db, "species", fish.key)) or fish.key)
    fish.db.skinning_xp_hint = max(1, int(round(float(getattr(fish.db, "fish_difficulty", 1) or 1) * 0.35)))
    difficulty = max(1, int(getattr(getattr(fish, "db", None), "fish_difficulty", (fish_profile or {}).get("difficulty", 20)) or 20))
    weight = max(1, int(getattr(getattr(fish, "db", None), "weight", 1) or 1))
    fish.db.processing_difficulty = max(8, int(round((difficulty * 0.55) + (weight * 1.5))))
    fish.db.processing_meat_yield = max(1, int(round(weight * 0.65)))
    fish.db.processing_skin_yield = max(1, int(round(weight * 0.30)))
    apply_region_value_modifier(fish)
    maybe_apply_trophy_metadata(fish, fish_profile, rng=rng)
    return fish


def format_fish_weight(weight):
    normalized = max(1, int(weight or 0))
    label = "stone" if normalized == 1 else "stones"
    return f"{normalized} {label}"


def get_fish_catch_message(fish):
    species = str(getattr(getattr(fish, "db", None), "species", getattr(fish, "key", "fish")) or getattr(fish, "key", "fish"))
    weight = format_fish_weight(getattr(getattr(fish, "db", None), "weight", 0))
    return f"You catch a {species} weighing {weight}."


def get_trophy_message(fish):
    if not bool(getattr(getattr(fish, "db", None), "is_trophy", False)):
        return None
    return "This is a remarkable catch!"


def get_fish_sale_value(fish):
    return max(1, int(getattr(getattr(fish, "db", None), "value", 1) or 1))


def get_fish_buyer_bonus(fish):
    if not bool(getattr(getattr(fish, "db", None), "is_trophy", False)):
        return 0
    base_value = get_fish_sale_value(fish)
    return max(1, int(round(base_value * 0.20)))


def get_fish_vendor_sale_value(fish, vendor=None):
    if is_junk_item(fish):
        return max(1, int(getattr(getattr(fish, "db", None), "value", 1) or 1))
    if is_processed_fish_item(fish):
        return max(1, int(getattr(getattr(fish, "db", None), "value", 1) or 1))
    value = get_fish_sale_value(fish)
    vendor_type = str(getattr(getattr(vendor, "db", None), "vendor_type", "") or "").strip().lower()
    if vendor_type == "fish_buyer":
        value += get_fish_buyer_bonus(fish)
    if bool(getattr(getattr(fish, "db", None), "is_trophy", False)):
        bonus_multiplier = float(getattr(getattr(vendor, "db", None), "trophy_sale_bonus_multiplier", 1.0) or 1.0)
        if bonus_multiplier > 1.0:
            value = max(1, int(round(float(value) * bonus_multiplier)))
    return max(1, int(value or 1))


def get_fish_buyer_reaction(fish, payout, vendor=None):
    if is_junk_item(fish):
        if str(getattr(getattr(fish, "db", None), "junk_tier", "common") or "common") == "interesting":
            return '"Lucky pull. Someone will pay for that."'
        return '"Not much, but even river junk has its buyer."'
    if is_processed_fish_item(fish):
        if str(getattr(getattr(fish, "db", None), "item_type", "") or "") == "fish_skin":
            return '"Cleanly done. Tanners can use this."'
        return '"Good work. Properly cleaned meat always sells."'
    if bool(getattr(getattr(fish, "db", None), "is_trophy", False)):
        return 'Maren raises her brows. "That\'s a remarkable catch."'
    if payout >= 80:
        return '"Now that\'s a fine fish."'
    if payout >= 25:
        return '"A fair catch."'
    return '"Not much to this one, but I\'ll take it."'


def get_bulk_sale_summary(fish_items, total_value):
    items = list(fish_items or [])
    fish_count = sum(1 for item in items if is_fish_item(item))
    salvage_count = sum(1 for item in items if is_processed_fish_item(item) or is_junk_item(item))
    return {
        "count": len(items),
        "fish_count": int(fish_count),
        "salvage_count": int(salvage_count),
        "only_fish": bool(items) and fish_count == len(items),
        "only_salvage": bool(items) and salvage_count == len(items),
        "mixed": bool(fish_count and salvage_count),
        "total_value": int(total_value or 0),
    }


def get_nearby_weigh_station(actor):
    location = getattr(actor, "location", None)
    if not location:
        return None
    for obj in list(getattr(location, "contents", []) or []):
        if bool(getattr(getattr(obj, "db", None), "is_weigh_station", False)):
            return obj
    return None


def format_fish_inspection(fish):
    species = str(getattr(getattr(fish, "db", None), "species", getattr(fish, "key", "fish")) or getattr(fish, "key", "fish"))
    fish_type = str(getattr(getattr(fish, "db", None), "fish_type", species) or species)
    weight = format_fish_weight(getattr(getattr(fish, "db", None), "weight", 0))
    value = int(getattr(getattr(fish, "db", None), "value", 0) or 0)
    trophy = "Yes" if bool(getattr(getattr(fish, "db", None), "is_trophy", False)) else "No"
    lines = [species, str(getattr(getattr(fish, "db", None), "desc", "A freshly caught fish."))]
    lines.append(f"Type: {fish_type}")
    lines.append(f"Weight: {weight}")
    lines.append(f"Value: {value} coins")
    lines.append(f"Trophy: {trophy}")
    return "\n".join(lines)


def format_processed_fish_inspection(item):
    key = str(getattr(item, "key", "processed fish") or "processed fish")
    desc = str(getattr(getattr(item, "db", None), "desc", "Prepared fish goods ready for sale.") or "Prepared fish goods ready for sale.")
    quantity = max(1, int(getattr(getattr(item, "db", None), "quantity", 1) or 1))
    material_type = str(getattr(getattr(item, "db", None), "item_type", "") or "").replace("_", " ").title()
    value = max(1, int(getattr(getattr(item, "db", None), "value", 1) or 1))
    source = str(getattr(getattr(item, "db", None), "processed_from", "fresh catch") or "fresh catch")
    lines = [key, desc]
    lines.append(f"Material: {material_type}")
    lines.append(f"Quantity: {quantity}")
    lines.append(f"From: {source}")
    lines.append(f"Value: {value} coins")
    return "\n".join(lines)


def format_junk_inspection(item):
    key = str(getattr(item, "key", "junk") or "junk")
    desc = str(getattr(getattr(item, "db", None), "desc", "A soggy bit of fishing salvage.") or "A soggy bit of fishing salvage.")
    tier = str(getattr(getattr(item, "db", None), "junk_tier", "common") or "common").title()
    source = str(getattr(getattr(item, "db", None), "junk_group", "River 1") or "River 1")
    value = max(1, int(getattr(getattr(item, "db", None), "value", 1) or 1))
    lines = [key, desc]
    lines.append(f"Tier: {tier}")
    lines.append(f"Source: {source}")
    lines.append(f"Value: {value} coins")
    return "\n".join(lines)


def get_fish_processing_profile(fish):
    weight = max(1, int(getattr(getattr(fish, "db", None), "weight", 1) or 1))
    difficulty = max(8, int(getattr(getattr(fish, "db", None), "processing_difficulty", 12) or 12))
    species = str(getattr(getattr(fish, "db", None), "species", getattr(fish, "key", "fish")) or getattr(fish, "key", "fish"))
    meat_yield = max(1, int(getattr(getattr(fish, "db", None), "processing_meat_yield", max(1, int(round(weight * 0.65)))) or 1))
    skin_yield = max(1, int(getattr(getattr(fish, "db", None), "processing_skin_yield", max(1, int(round(weight * 0.30)))) or 1))
    meat_value = max(2, int(round((weight * 2.5) + (difficulty * 0.12))))
    skin_value = max(1, int(round((weight * 1.5) + (difficulty * 0.08))))
    return {
        "species": species,
        "difficulty": difficulty,
        "meat_yield": meat_yield,
        "skin_yield": skin_yield,
        "meat_value": meat_value,
        "skin_value": skin_value,
    }


def update_heaviest_fish_record(actor, fish):
    if not actor or not fish:
        return None
    current = dict(getattr(actor.db, "fishing_leaderboard", None) or {})
    current_best = int(current.get("heaviest_weight", 0) or 0)
    weight = int(getattr(getattr(fish, "db", None), "weight", 0) or 0)
    if weight <= current_best:
        return current
    current.update(
        {
            "heaviest_weight": weight,
            "fish_name": str(getattr(fish, "key", "fish") or "fish"),
            "value": int(getattr(getattr(fish, "db", None), "value", 0) or 0),
            "updated_at": float(time.time()),
        }
    )
    actor.db.fishing_leaderboard = current
    return current


def can_use_fish_buyer(vendor, actor):
    if vendor is None or actor is None:
        return False, "There is no buyer here."
    throttle_map = dict(getattr(vendor.ndb, "fish_buyer_throttle", {}) or {})
    actor_key = str(int(getattr(actor, "id", 0) or 0))
    now = time.time()
    blocked_until = float(throttle_map.get(actor_key, 0.0) or 0.0)
    if blocked_until > now:
        return False, "The buyer raises a hand. 'One moment at a time.'"
    throttle_map[actor_key] = now + BUYER_RATE_LIMIT_SECONDS
    vendor.ndb.fish_buyer_throttle = throttle_map
    return True, ""


def find_fish_string(actor, require_capacity=False, fish=None):
    if actor is None:
        return None
    strings = [obj for obj in list(getattr(actor, "contents", []) or []) if is_fish_string(obj)]
    if not require_capacity:
        return strings[0] if strings else None
    for string in strings:
        if hasattr(string, "can_hold_item"):
            can_hold, _msg = string.can_hold_item(fish)
            if can_hold:
                return string
    return None


def place_fish_on_string(actor, fish, preferred_string=None):
    fish_string = preferred_string or find_fish_string(actor, require_capacity=True, fish=fish)
    if not fish_string or not hasattr(fish_string, "store_item"):
        return False, None, None
    success, message = fish_string.store_item(fish)
    if not success:
        return False, fish_string, message
    return True, fish_string, message


def can_receive_caught_fish(actor, fish):
    if actor is None or fish is None:
        return False
    if not hasattr(actor, "get_total_weight") or not hasattr(actor, "get_max_carry_weight") or not hasattr(actor, "get_object_total_weight"):
        return True
    projected = float(actor.get_total_weight() or 0.0) + float(actor.get_object_total_weight(fish) or 0.0)
    return projected <= float(actor.get_max_carry_weight() or 0.0)


def award_bait_usage_xp(actor):
    if actor is None or not hasattr(actor, "award_skill_experience"):
        return 0
    actor.award_skill_experience("mechanical_lore", 8, success=True, outcome="partial", event_key="fishing_bait", context_multiplier=0.20)
    return 1