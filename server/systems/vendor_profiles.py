from __future__ import annotations

import logging
import random
from pathlib import Path

import yaml

from server.systems import item_loader
from server.systems.kit_templates import get_kit_template


VENDOR_PROFILE_ROOT = Path(__file__).resolve().parents[2] / "world_data" / "vendor_profiles"
VENDOR_PROFILES: dict[str, dict] = {}
VENDOR_PROFILE_CATEGORIES = set(item_loader.ITEM_CATEGORY_DIRECTORIES) | {"general_goods"}

VENDOR_PROFILE_ALLOWED_KEYS = {
    "id",
    "category",
    "level_band",
    "stock_count",
    "allowed_weapon_classes",
    "preferred_weapon_classes",
    "excluded_weapon_classes",
    "allowed_armor_classes",
    "preferred_armor_classes",
    "excluded_armor_classes",
    "allowed_armor_slots",
    "preferred_armor_slots",
    "slot_targets",
    "slot_priority",
    "kit_templates",
    "kit_count",
    "snobbishness",
    "ammo_types",
    "ammo_classes",
    "ammo_stock_count",
    "required_tags",
    "allow_duplicates",
    "essential_item_ids",
    "optional_item_ids",
    "optional_stock_count",
}

VENDOR_SLOT_PRIORITY_LEVELS = {"low", "medium", "high"}
VENDOR_SLOT_PRIORITY_COUNTS = {"low": 1, "medium": 2, "high": 3}
BASELINE_ARMOR_TIERS = ("below_average", "average")
ARMOR_TIER_WEIGHTS = {
    "below_average": 0.0,
    "average": 0.0,
    "above_average": 0.25,
    "exquisite": 0.10,
    "epic": 0.03,
    "legendary": 0.01,
}
TIER_DISPLAY_LABELS = {
    "below_average": "[Low]",
    "average": "[Avg]",
    "above_average": "[Fine]",
    "exquisite": "[Exq]",
    "epic": "[Epic]",
    "legendary": "[Legend]",
}

TIER_PRICE_MULTIPLIER = {
    "below_average": 0.7,
    "average": 1.0,
    "above_average": 1.3,
    "exquisite": 1.8,
    "epic": 2.5,
    "legendary": 4.0,
}
AMMO_TIER_WEIGHTS = {
    "above_average": 0.25,
    "exquisite": 0.10,
    "epic": 0.03,
    "legendary": 0.01,
}


def _defaults(profile_id: str = "") -> dict:
    return {
        "id": profile_id,
        "category": "weapon",
        "level_band": {"min": 1, "max": 1},
        "stock_count": 1,
        "allowed_weapon_classes": [],
        "preferred_weapon_classes": {},
        "excluded_weapon_classes": [],
        "allowed_armor_classes": [],
        "preferred_armor_classes": {},
        "excluded_armor_classes": [],
        "allowed_armor_slots": [],
        "preferred_armor_slots": {},
        "slot_targets": {},
        "slot_priority": {},
        "kit_templates": [],
        "kit_count": 0,
        "snobbishness": 0.5,
        "ammo_types": [],
        "ammo_classes": [],
        "ammo_stock_count": 0,
        "required_tags": [],
        "allow_duplicates": True,
        "essential_item_ids": [],
        "optional_item_ids": [],
        "optional_stock_count": 0,
    }


def _normalize_string_list(values) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized = []
    seen = set()
    for value in values:
        item = str(value or "").strip().lower()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def validate_vendor_profile(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Vendor profile payload must be an object")
    unknown = sorted(set(payload.keys()) - VENDOR_PROFILE_ALLOWED_KEYS)
    if unknown:
        raise ValueError(f"unknown vendor profile fields: {', '.join(unknown)}")


def _normalize_weight_map(values, *, allowed_values: set[str], field_name: str) -> dict[str, float]:
    payload = values if isinstance(values, dict) else {}
    normalized_weights = {}
    total_weight = 0.0
    for key, raw_weight in payload.items():
        normalized_key = str(key or "").strip().lower()
        if normalized_key not in allowed_values:
            raise ValueError(f"{field_name} is invalid")
        weight = float(raw_weight or 0.0)
        if weight < 0.0:
            raise ValueError(f"{field_name} weights must be >= 0")
        normalized_weights[normalized_key] = weight
        total_weight += weight
    if total_weight > 1.0 + 1e-9:
        raise ValueError(f"{field_name} weights must sum to <= 1.0")
    return normalized_weights


def _normalize_slot_targets(values) -> dict[str, int]:
    payload = values if isinstance(values, dict) else {}
    targets = {}
    for slot_name, raw_count in payload.items():
        normalized_slot = str(slot_name or "").strip().lower()
        if normalized_slot not in item_loader.ITEM_ARMOR_SLOTS:
            raise ValueError("slot_targets armor_slot is invalid")
        count = int(raw_count or 0)
        if count < 0:
            raise ValueError("slot_targets counts must be >= 0")
        if count > 0:
            targets[normalized_slot] = count
    return targets


def _normalize_slot_priority(values) -> dict[str, str]:
    payload = values if isinstance(values, dict) else {}
    priorities = {}
    for slot_name, raw_priority in payload.items():
        normalized_slot = str(slot_name or "").strip().lower()
        if normalized_slot not in item_loader.ITEM_ARMOR_SLOTS:
            raise ValueError("slot_priority armor_slot is invalid")
        priority = str(raw_priority or "").strip().lower()
        if priority not in VENDOR_SLOT_PRIORITY_LEVELS:
            raise ValueError("slot_priority value is invalid")
        priorities[normalized_slot] = priority
    return priorities


def _slot_targets_to_priority(slot_targets: dict[str, int]) -> dict[str, str]:
    priorities = {}
    for slot_name, count in dict(slot_targets or {}).items():
        if int(count or 0) >= 3:
            priorities[slot_name] = "high"
        elif int(count or 0) == 2:
            priorities[slot_name] = "medium"
        elif int(count or 0) == 1:
            priorities[slot_name] = "low"
    return priorities


def calculate_tier_price(base_price: int, tier: str) -> int:
    normalized_tier = str(tier or "average").strip().lower()
    if normalized_tier not in TIER_PRICE_MULTIPLIER:
        raise ValueError("item tier is invalid")
    return max(1, int(round(int(base_price or 0) * TIER_PRICE_MULTIPLIER[normalized_tier])))


def _build_tiered_display_name(item_record: dict, tier: str) -> str:
    normalized_tier = str(tier or "average").strip().lower()
    tier_label = TIER_DISPLAY_LABELS.get(normalized_tier, f"[{normalized_tier.replace('_', ' ').title()}]")
    base_name = str(item_record.get("name") or item_record.get("id") or "item").strip()
    return f"{tier_label} {base_name}"


def _build_armor_entry(item_record: dict, tier: str) -> dict:
    item_id = str(item_record.get("id") or "").strip()
    armor_class = str(item_record.get("armor_class") or "").strip().lower()
    armor_slot = str(item_record.get("armor_slot") or "").strip().lower()
    price = calculate_tier_price(int(item_record.get("value", 0) or 0), tier)
    return {
        "item_id": item_id,
        "display_name": _build_tiered_display_name(item_record, tier),
        "tier": str(tier or "average").strip().lower(),
        "price": price,
        "armor_class": armor_class,
        "armor_slot": armor_slot,
        "category": "armor",
    }


def _build_general_goods_entry(item_record: dict) -> dict:
    item_id = str(item_record.get("id") or "").strip()
    return {
        "item_id": item_id,
        "display_name": str(item_record.get("name") or item_id or "item").strip(),
        "price": max(1, int(item_record.get("value", 0) or 0)),
        "category": str(item_record.get("category") or "misc").strip().lower(),
        "tier": str(item_record.get("tier") or "").strip().lower(),
        "utility_category": str(item_record.get("utility_category") or "").strip().lower(),
        "functional_type": str(item_record.get("functional_type") or "").strip().lower(),
        "tool_type": str(item_record.get("tool_type") or "").strip().lower(),
    }


def _append_vendor_entry(entry: dict, inventory: list, price_map: dict[str, int], inventory_entry_map: dict, item_ids: list[str]) -> None:
    display_name = str(entry.get("display_name") or entry.get("item_id") or "item").strip()
    normalized_label = display_name.lower()
    stored_entry = dict(entry)
    stored_entry["display_name"] = display_name
    inventory.append(stored_entry)
    price = int(stored_entry.get("price", 0) or 0)
    price_map[normalized_label] = price
    item_id = str(stored_entry.get("item_id") or "").strip()
    if item_id:
        price_map[item_id.lower()] = price
    inventory_entry_map[normalized_label] = stored_entry
    item_ids.append(item_id)


def _theme_score(record: dict, template: dict, target_tier: str) -> int:
    score = 0
    template_tags = set(template.get("theme_tags") or [])
    record_tags = set(record.get("tags") or [])
    score += len(template_tags & record_tags) * 5

    normalized_tier = str(record.get("tier") or "average").strip().lower()
    if normalized_tier == target_tier:
        score += 4
    elif normalized_tier in {"average", "above_average", "exquisite"} and target_tier in {"average", "above_average", "exquisite"}:
        score += 2

    name_tokens = {token for token in str(record.get("name") or "").strip().lower().replace("-", " ").split() if len(token) > 3}
    score += len(template_tags & name_tokens) * 2
    if str(record.get("armor_class") or "").strip().lower() == str(template.get("armor_class") or "").strip().lower():
        score += 3
    return score


def _roll_weighted_key(weight_map: dict[str, float], rng, *, default: str) -> str:
    weights = {str(key or "").strip().lower(): float(value or 0.0) for key, value in dict(weight_map or {}).items() if float(value or 0.0) > 0.0}
    if not weights:
        return default
    return rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def _roll_optional_slot(slot_name: str, rng) -> bool:
    normalized_slot = str(slot_name or "").strip().lower()
    chance_by_slot = {
        "head": 0.50,
        "cloak": 0.40,
        "shield": 0.50,
        "feet": 0.45,
        "shoulders": 0.35,
    }
    return rng.random() < chance_by_slot.get(normalized_slot, 0.50)


def _build_kit_label(template: dict) -> str:
    base_id = str(template.get("id") or "kit").strip().replace("_", " ").title()
    return f"{base_id} Set"


def _trim_kit_entries(kit_entries: list[dict], max_count: int) -> list[dict]:
    if len(kit_entries) <= max_count:
        return list(kit_entries)
    required_entries = [entry for entry in kit_entries if not bool(entry.get("optional"))]
    optional_entries = [entry for entry in kit_entries if bool(entry.get("optional"))]
    while len(required_entries) + len(optional_entries) > max_count and optional_entries:
        optional_entries.pop()
    return required_entries + optional_entries[: max(0, max_count - len(required_entries))]


def generate_kit_stock(profile: dict, *, item_records: dict | None = None, rng=None) -> list[dict]:
    resolved_profile = get_vendor_profile(profile.get("id")) if "id" in profile else normalize_vendor_profile(profile)
    if resolved_profile.get("category") != "armor":
        return []
    rng = rng or random.Random()
    records = dict(item_records or {}) or item_loader.load_all_items()
    template_ids = [template_id for template_id in resolved_profile.get("kit_templates") or [] if str(template_id or "").strip()]
    if not template_ids:
        return []

    kit_count = max(0, int(resolved_profile.get("kit_count", 0) or 0))
    if kit_count <= 0:
        return []

    available_candidates = _filter_candidates(resolved_profile, records)
    generated_entries = []
    exact_keys = set()
    for index in range(kit_count):
        template_id = template_ids[index % len(template_ids)]
        template = get_kit_template(template_id)
        target_tier = _roll_weighted_key(template.get("tier_bias") or {}, rng, default="average")
        class_candidates = [
            candidate
            for candidate in available_candidates
            if str(candidate.get("armor_class") or "").strip().lower() == str(template.get("armor_class") or "").strip().lower()
        ]
        if not class_candidates:
            logging.warning("[VendorGen] %s missing kit candidates for template '%s'", resolved_profile["id"], template_id)
            continue

        kit_entries = []
        used_item_ids = set()
        all_slots = [(slot_name, False) for slot_name in template.get("required_slots") or []]
        for optional_slot in template.get("optional_slots") or []:
            if _roll_optional_slot(optional_slot, rng):
                all_slots.append((optional_slot, True))

        for slot_name, is_optional in all_slots:
            slot_candidates = [candidate for candidate in class_candidates if str(candidate.get("armor_slot") or "").strip().lower() == str(slot_name or "").strip().lower()]
            if not slot_candidates:
                if not is_optional:
                    logging.warning("[VendorGen] %s kit '%s' missing required slot '%s'", resolved_profile["id"], template_id, slot_name)
                continue

            scored_candidates = sorted(
                slot_candidates,
                key=lambda record: (
                    _theme_score(record, template, target_tier),
                    str(record.get("id") or ""),
                ),
                reverse=True,
            )
            for candidate in scored_candidates:
                item_id = str(candidate.get("id") or "").strip().lower()
                if item_id and item_id in used_item_ids:
                    continue
                entry = _build_armor_entry(candidate, target_tier)
                exact_key = _armor_entry_key(entry)
                if not bool(resolved_profile.get("allow_duplicates", True)) and exact_key in exact_keys:
                    continue
                used_item_ids.add(item_id)
                exact_keys.add(exact_key)
                entry["kit_id"] = template_id
                entry["kit_name"] = _build_kit_label(template)
                entry["optional"] = bool(is_optional)
                entry["theme_tags"] = list(template.get("theme_tags") or [])
                kit_entries.append(entry)
                break

        remaining = max(0, int(resolved_profile.get("stock_count", 0) or 0) - len(generated_entries))
        generated_entries.extend(_trim_kit_entries(kit_entries, remaining))
        if len(generated_entries) >= int(resolved_profile.get("stock_count", 0) or 0):
            break

    return generated_entries


def _armor_entry_key(entry: dict) -> tuple[str, str]:
    return (
        str(entry.get("item_id") or "").strip().lower(),
        str(entry.get("tier") or "average").strip().lower(),
    )


def _choose_slot_candidate(candidate_pool: list[dict], profile: dict, rng, *, slot_name: str, fallback_pool: list[dict]) -> dict | None:
    slot_candidates = [candidate for candidate in candidate_pool if str(candidate.get("armor_slot") or "").strip().lower() == slot_name]
    if slot_candidates:
        return _choose_candidate(slot_candidates, profile, rng, forced_slot=slot_name)
    logging.warning("[VendorGen] %s missing candidates for armor slot '%s'; falling back to any valid armor", profile["id"], slot_name)
    if not fallback_pool:
        return None
    return _choose_candidate(list(fallback_pool), profile, rng)


def _generate_armor_stock(profile: dict, candidates: list[dict], fallback_candidates: list[dict], rng, *, reserved_entries: list[dict] | None = None) -> dict:
    inventory = []
    price_map = {}
    inventory_entry_map = {}
    item_ids = []
    allow_duplicates = bool(profile.get("allow_duplicates", True))
    reserved_entries = list(reserved_entries or [])
    priority_map = dict(profile.get("slot_priority") or {})
    allowed_slots = list(profile.get("allowed_armor_slots") or [])
    prioritized_slots = [slot_name for slot_name in priority_map if slot_name]
    active_slots = prioritized_slots or allowed_slots or sorted({str(candidate.get("armor_slot") or "").strip().lower() for candidate in candidates if str(candidate.get("armor_slot") or "").strip()})
    if not active_slots:
        raise ValueError(f"Vendor profile '{profile['id']}' produced no stock")

    used_exact_entries = set()
    covered_slot_counts = {}
    high_tier_count = 0
    epic_count = 0
    legendary_per_slot = {}

    def append_entry(entry: dict) -> bool:
        exact_key = _armor_entry_key(entry)
        if not allow_duplicates and exact_key in used_exact_entries:
            return False
        _append_vendor_entry(entry, inventory, price_map, inventory_entry_map, item_ids)
        used_exact_entries.add(exact_key)
        slot_name = str(entry.get("armor_slot") or "").strip().lower()
        if slot_name:
            covered_slot_counts[slot_name] = covered_slot_counts.get(slot_name, 0) + 1
        return True

    for entry in reserved_entries:
        if append_entry(entry):
            normalized_tier = str(entry.get("tier") or "average").strip().lower()
            slot_name = str(entry.get("armor_slot") or "").strip().lower()
            if normalized_tier in {"epic", "legendary"}:
                high_tier_count += 1
            if normalized_tier == "epic":
                epic_count += 1
            if normalized_tier == "legendary":
                legendary_per_slot[slot_name] = legendary_per_slot.get(slot_name, 0) + 1

    baseline_candidates = list(candidates)
    baseline_fallback = list(fallback_candidates)
    slot_coverage = set()
    for slot_name in active_slots:
        if covered_slot_counts.get(slot_name, 0) > 0:
            slot_coverage.add(slot_name)
            continue
        selected = _choose_slot_candidate(baseline_candidates, profile, rng, slot_name=slot_name, fallback_pool=baseline_fallback)
        if not selected:
            continue
        for tier in BASELINE_ARMOR_TIERS:
            append_entry(_build_armor_entry(selected, tier))
        slot_coverage.add(str(selected.get("armor_slot") or "").strip().lower())
    missing_slots = [slot_name for slot_name in active_slots if slot_name not in slot_coverage]
    for slot_name in missing_slots:
        logging.warning("[VendorGen] %s could not satisfy baseline slot coverage for '%s'", profile["id"], slot_name)

    stock_count = max(1, int(profile.get("stock_count", 1) or 1))
    baseline_count = len(inventory)
    max_total_for_baseline = int(baseline_count / 0.7) if baseline_count else stock_count
    target_count = min(stock_count, max_total_for_baseline if max_total_for_baseline > 0 else stock_count)
    if target_count < stock_count:
        logging.warning(
            "[VendorGen] %s trimmed armor stock from %s to %s to preserve baseline coverage",
            profile["id"],
            stock_count,
            target_count,
        )
    extra_count = max(0, target_count - baseline_count)
    epic_cap = min(2, int(profile.get("stock_count", target_count) or target_count))
    high_tier_cap = int(target_count * 0.10)

    extra_slot_names = []
    extra_slot_weights = []
    for slot_name in active_slots:
        priority = priority_map.get(slot_name, "low")
        extra_slot_names.append(slot_name)
        extra_slot_weights.append(VENDOR_SLOT_PRIORITY_COUNTS.get(priority, 1) / max(1, covered_slot_counts.get(slot_name, 0) + 1))

    weighted_tiers = list(ARMOR_TIER_WEIGHTS.keys())
    weighted_values = list(ARMOR_TIER_WEIGHTS.values())
    for _index in range(extra_count):
        if not extra_slot_names:
            break
        slot_name = rng.choices(extra_slot_names, weights=extra_slot_weights, k=1)[0]
        selected = _choose_slot_candidate(candidates, profile, rng, slot_name=slot_name, fallback_pool=fallback_candidates)
        if not selected:
            continue
        selected_slot = str(selected.get("armor_slot") or "").strip().lower()
        tier = rng.choices(weighted_tiers, weights=weighted_values, k=1)[0]
        if tier == "legendary" and legendary_per_slot.get(selected_slot, 0) >= 1:
            tier = "epic"
        if tier == "epic" and epic_count >= epic_cap:
            tier = "exquisite"
        if tier in {"epic", "legendary"} and high_tier_count >= high_tier_cap:
            tier = "exquisite"
        entry = _build_armor_entry(selected, tier)
        if not append_entry(entry):
            fallback_tiers = ["exquisite", "above_average", "average", "below_average"]
            appended = False
            for fallback_tier in fallback_tiers:
                fallback_entry = _build_armor_entry(selected, fallback_tier)
                if append_entry(fallback_entry):
                    entry = fallback_entry
                    appended = True
                    break
            if not appended:
                continue
        normalized_tier = str(entry.get("tier") or "average").strip().lower()
        if normalized_tier == "legendary":
            legendary_per_slot[selected_slot] = legendary_per_slot.get(selected_slot, 0) + 1
            high_tier_count += 1
        elif normalized_tier == "epic":
            epic_count += 1
            high_tier_count += 1

    rng.shuffle(inventory)
    return {
        "inventory": inventory,
        "price_map": price_map,
        "inventory_entry_map": inventory_entry_map,
        "item_ids": item_ids,
    }


def calculate_ammo_price(base_price: int, tier: str) -> int:
    normalized_tier = str(tier or "average").strip().lower()
    if normalized_tier not in TIER_PRICE_MULTIPLIER:
        raise ValueError("ammo tier is invalid")
    return int(int(base_price or 0) * TIER_PRICE_MULTIPLIER[normalized_tier] * 10)


def _build_ammo_display_name(item_record: dict, tier: str, quantity: int) -> str:
    tier_label = str(tier or "average").replace("_", " ")
    base_name = str(item_record.get("name") or item_record.get("id") or "ammunition").strip()
    return f"{tier_label.title()} {base_name} ({int(quantity or 0)})"


def _build_ammo_entry(item_record: dict, tier: str) -> dict:
    quantity = int(item_record.get("stack_size", 10) or 10)
    price = calculate_ammo_price(int(item_record.get("base_price", 0) or 0), tier)
    return {
        "item_id": str(item_record.get("id") or "").strip(),
        "quantity": quantity,
        "tier": str(tier or "average").strip().lower(),
        "price": price,
        "display_name": _build_ammo_display_name(item_record, tier, quantity),
    }


def _compatible_ammo_candidates(profile: dict, item_records: dict) -> list[dict]:
    required_tags = set(profile.get("required_tags") or [])
    allowed_types = set(profile.get("ammo_types") or [])
    allowed_classes = set(profile.get("ammo_classes") or [])
    candidates = []
    for item_id, raw_record in dict(item_records or {}).items():
        record = dict(raw_record or {})
        if str(record.get("category") or "").strip().lower() != "ammunition":
            continue
        if not _level_band_matches(record, profile):
            continue
        record_tags = set(record.get("tags") or [])
        if required_tags and not required_tags.issubset(record_tags):
            continue
        ammo_type = str(record.get("ammo_type") or "").strip().lower()
        ammo_class = str(record.get("ammo_class") or "").strip().lower()
        if allowed_types and ammo_type not in allowed_types:
            continue
        if allowed_classes and ammo_class not in allowed_classes:
            continue
        record["id"] = str(record.get("id") or item_id)
        candidates.append(record)
    return candidates


def generate_ammo_stock(profile: dict, *, item_records: dict | None = None, rng=None) -> list[dict]:
    resolved_profile = get_vendor_profile(profile.get("id")) if "id" in profile else normalize_vendor_profile(profile)
    rng = rng or random.Random()
    ammo_candidates = _compatible_ammo_candidates(resolved_profile, item_records or {})
    if not ammo_candidates:
        logging.warning("[VendorGen] %s produced no compatible ammunition candidates", resolved_profile["id"])
        return []

    grouped = {}
    for record in ammo_candidates:
        grouped.setdefault(str(record.get("ammo_class") or "").strip().lower(), []).append(record)

    entries = []
    for ammo_class in resolved_profile.get("ammo_classes") or []:
        class_candidates = sorted(grouped.get(ammo_class) or [], key=lambda item: str(item.get("id") or ""))
        if not class_candidates:
            logging.warning("[VendorGen] %s missing baseline ammo for ammo_class '%s'", resolved_profile["id"], ammo_class)
            continue
        selected = class_candidates[0]
        entries.append(_build_ammo_entry(selected, "below_average"))
        entries.append(_build_ammo_entry(selected, "average"))

    weighted_tiers = list(AMMO_TIER_WEIGHTS.keys())
    weighted_values = list(AMMO_TIER_WEIGHTS.values())
    compatible_classes = [ammo_class for ammo_class in resolved_profile.get("ammo_classes") or [] if grouped.get(ammo_class)]
    for _index in range(int(resolved_profile.get("ammo_stock_count", 0) or 0)):
        if not compatible_classes:
            break
        ammo_class = rng.choice(compatible_classes)
        candidate = rng.choice(grouped[ammo_class])
        tier = rng.choices(weighted_tiers, weights=weighted_values, k=1)[0]
        entries.append(_build_ammo_entry(candidate, tier))
    return entries


def _resolve_general_goods_record(item_id: str, item_records: dict, profile: dict) -> dict | None:
    record = dict((item_records or {}).get(str(item_id or "").strip()) or {})
    if not record:
        logging.warning("[VendorGen] %s missing general goods item '%s'", profile["id"], item_id)
        return None
    if not _level_band_matches(record, profile):
        return None
    record["id"] = str(record.get("id") or item_id)
    return record


def _generate_general_goods_stock(profile: dict, item_records: dict, rng) -> dict:
    inventory = []
    price_map = {}
    inventory_entry_map = {}
    item_ids = []

    essential_ids = list(profile.get("essential_item_ids") or [])
    optional_ids = list(profile.get("optional_item_ids") or [])
    stock_count = max(1, int(profile.get("stock_count", 1) or 1))
    optional_stock_count = max(0, int(profile.get("optional_stock_count", 0) or 0))

    for item_id in essential_ids:
        record = _resolve_general_goods_record(item_id, item_records, profile)
        if not record:
            continue
        _append_vendor_entry(_build_general_goods_entry(record), inventory, price_map, inventory_entry_map, item_ids)

    remaining = max(0, stock_count - len(inventory))
    optional_target = min(remaining, optional_stock_count if optional_stock_count > 0 else remaining)
    optional_candidates = []
    for item_id in optional_ids:
        if item_id in item_ids:
            continue
        record = _resolve_general_goods_record(item_id, item_records, profile)
        if record:
            optional_candidates.append(record)

    if optional_target and optional_candidates:
        sample_size = min(optional_target, len(optional_candidates))
        sampled = rng.sample(optional_candidates, sample_size) if len(optional_candidates) > sample_size else list(optional_candidates)
        for record in sorted(sampled, key=lambda entry: (str(entry.get("utility_category") or ""), str(entry.get("name") or entry.get("id") or ""))):
            _append_vendor_entry(_build_general_goods_entry(record), inventory, price_map, inventory_entry_map, item_ids)

    if not inventory:
        raise ValueError(f"Vendor profile '{profile['id']}' produced no stock")

    return {
        "inventory": inventory,
        "price_map": price_map,
        "inventory_entry_map": inventory_entry_map,
        "item_ids": item_ids,
    }


def normalize_vendor_profile(payload: dict, *, fallback_id: str = "") -> dict:
    validate_vendor_profile(payload)
    profile_id = str(payload.get("id") or fallback_id or "").strip()
    if not profile_id:
        raise ValueError("id is required")
    defaults = _defaults(profile_id)
    category = str(payload.get("category") or defaults["category"] or "").strip().lower()
    if category not in VENDOR_PROFILE_CATEGORIES:
        raise ValueError("category is invalid")

    level_band_payload = payload.get("level_band") if isinstance(payload.get("level_band"), dict) else {}
    level_min = int(level_band_payload.get("min", defaults["level_band"]["min"]) or defaults["level_band"]["min"])
    level_max = int(level_band_payload.get("max", defaults["level_band"]["max"]) or defaults["level_band"]["max"])
    if level_min < 1 or level_max < level_min:
        raise ValueError("level_band is invalid")

    allowed_weapon_classes = _normalize_string_list(payload.get("allowed_weapon_classes", defaults["allowed_weapon_classes"]))
    excluded_weapon_classes = _normalize_string_list(payload.get("excluded_weapon_classes", defaults["excluded_weapon_classes"]))
    for weapon_class in allowed_weapon_classes + excluded_weapon_classes:
        if weapon_class not in item_loader.ITEM_WEAPON_CLASSES:
            raise ValueError("allowed/excluded weapon class is invalid")

    preferred_weapon_classes = _normalize_weight_map(
        payload.get("preferred_weapon_classes"),
        allowed_values=item_loader.ITEM_WEAPON_CLASSES,
        field_name="preferred weapon class",
    )

    allowed_armor_classes = _normalize_string_list(payload.get("allowed_armor_classes", defaults["allowed_armor_classes"]))
    excluded_armor_classes = _normalize_string_list(payload.get("excluded_armor_classes", defaults["excluded_armor_classes"]))
    for armor_class in allowed_armor_classes + excluded_armor_classes:
        if armor_class not in item_loader.ITEM_ARMOR_CLASSES:
            raise ValueError("allowed/excluded armor class is invalid")

    preferred_armor_classes = _normalize_weight_map(
        payload.get("preferred_armor_classes"),
        allowed_values=item_loader.ITEM_ARMOR_CLASSES,
        field_name="preferred armor class",
    )

    allowed_armor_slots = _normalize_string_list(payload.get("allowed_armor_slots", defaults["allowed_armor_slots"]))
    for armor_slot in allowed_armor_slots:
        if armor_slot not in item_loader.ITEM_ARMOR_SLOTS:
            raise ValueError("allowed armor slot is invalid")

    preferred_armor_slots = _normalize_weight_map(
        payload.get("preferred_armor_slots"),
        allowed_values=item_loader.ITEM_ARMOR_SLOTS,
        field_name="preferred armor slot",
    )

    slot_targets = _normalize_slot_targets(payload.get("slot_targets", defaults["slot_targets"]))
    slot_priority = _normalize_slot_priority(payload.get("slot_priority", defaults["slot_priority"]))
    if not slot_priority and slot_targets:
        slot_priority = _slot_targets_to_priority(slot_targets)
    kit_templates = _normalize_string_list(payload.get("kit_templates", defaults["kit_templates"]))
    kit_count = max(0, int(payload.get("kit_count", defaults["kit_count"]) or defaults["kit_count"]))
    snobbishness = float(payload.get("snobbishness", defaults["snobbishness"]) or defaults["snobbishness"])
    snobbishness = max(0.0, min(1.0, snobbishness))
    stock_count = max(1, int(payload.get("stock_count", defaults["stock_count"]) or defaults["stock_count"]))
    if sum(slot_targets.values()) > stock_count:
        raise ValueError("slot_targets total must be <= stock_count")
    if allowed_armor_slots and any(slot not in set(allowed_armor_slots) for slot in slot_targets):
        raise ValueError("slot_targets must use allowed armor slots")
    if allowed_armor_slots and any(slot not in set(allowed_armor_slots) for slot in slot_priority):
        raise ValueError("slot_priority must use allowed armor slots")

    ammo_types = _normalize_string_list(payload.get("ammo_types", defaults["ammo_types"]))
    for ammo_type in ammo_types:
        if ammo_type not in item_loader.ITEM_AMMO_TYPES:
            raise ValueError("ammo_type is invalid")

    ammo_classes = _normalize_string_list(payload.get("ammo_classes", defaults["ammo_classes"]))
    for ammo_class in ammo_classes:
        if ammo_class not in item_loader.ITEM_AMMO_CLASSES:
            raise ValueError("ammo_class is invalid")

    ammo_stock_count = max(0, int(payload.get("ammo_stock_count", defaults["ammo_stock_count"]) or defaults["ammo_stock_count"]))

    required_tags = _normalize_string_list(payload.get("required_tags", defaults["required_tags"]))
    essential_item_ids = _normalize_string_list(payload.get("essential_item_ids", defaults["essential_item_ids"]))
    optional_item_ids = _normalize_string_list(payload.get("optional_item_ids", defaults["optional_item_ids"]))
    optional_stock_count = max(0, int(payload.get("optional_stock_count", defaults["optional_stock_count"]) or defaults["optional_stock_count"]))
    if category == "general_goods" and len(essential_item_ids) > stock_count:
        raise ValueError("essential_item_ids total must be <= stock_count")

    return {
        "id": profile_id,
        "category": category,
        "level_band": {"min": level_min, "max": level_max},
        "stock_count": stock_count,
        "allowed_weapon_classes": allowed_weapon_classes,
        "preferred_weapon_classes": preferred_weapon_classes,
        "excluded_weapon_classes": excluded_weapon_classes,
        "allowed_armor_classes": allowed_armor_classes,
        "preferred_armor_classes": preferred_armor_classes,
        "excluded_armor_classes": excluded_armor_classes,
        "allowed_armor_slots": allowed_armor_slots,
        "preferred_armor_slots": preferred_armor_slots,
        "slot_targets": slot_targets,
        "slot_priority": slot_priority,
        "kit_templates": kit_templates,
        "kit_count": kit_count,
        "snobbishness": snobbishness,
        "ammo_types": ammo_types,
        "ammo_classes": ammo_classes,
        "ammo_stock_count": ammo_stock_count,
        "required_tags": required_tags,
        "allow_duplicates": bool(payload.get("allow_duplicates", defaults["allow_duplicates"])),
        "essential_item_ids": essential_item_ids,
        "optional_item_ids": optional_item_ids,
        "optional_stock_count": optional_stock_count,
    }


def _iter_profile_files():
    if not VENDOR_PROFILE_ROOT.exists():
        return
    for file_path in sorted(VENDOR_PROFILE_ROOT.glob("*.yaml")):
        if file_path.name == "schema_vendor_profile.yaml":
            continue
        yield file_path


def load_vendor_profiles() -> dict[str, dict]:
    profiles = {}
    for file_path in _iter_profile_files() or []:
        with file_path.open(encoding="utf-8") as file_handle:
            payload = yaml.safe_load(file_handle) or {}
        normalized = normalize_vendor_profile(payload, fallback_id=file_path.stem)
        profiles[normalized["id"]] = normalized
    return dict(sorted(profiles.items(), key=lambda item: item[0]))


def reload_vendor_profiles() -> dict[str, dict]:
    VENDOR_PROFILES.clear()
    VENDOR_PROFILES.update(load_vendor_profiles())
    return dict(VENDOR_PROFILES)


def get_vendor_profile(profile_id: str) -> dict:
    normalized_id = str(profile_id or "").strip()
    if not normalized_id:
        raise ValueError("vendor profile id is required")
    if not VENDOR_PROFILES:
        reload_vendor_profiles()
    if normalized_id not in VENDOR_PROFILES:
        raise ValueError(f"Unknown vendor profile '{normalized_id}'")
    return dict(VENDOR_PROFILES[normalized_id])


def _level_band_matches(item_record: dict, profile: dict) -> bool:
    item_band = dict(item_record.get("level_band") or {})
    item_min = int(item_band.get("min", 1) or 1)
    item_max = int(item_band.get("max", item_min) or item_min)
    profile_min = int(profile["level_band"]["min"])
    profile_max = int(profile["level_band"]["max"])
    return item_min <= profile_max and item_max >= profile_min


def _filter_candidates(profile: dict, item_records: dict, *, ignore_armor_slots: bool = False) -> list[dict]:
    candidates = []
    required_tags = set(profile.get("required_tags") or [])
    allowed_weapon_classes = set(profile.get("allowed_weapon_classes") or [])
    excluded_weapon_classes = set(profile.get("excluded_weapon_classes") or [])
    allowed_armor_classes = set(profile.get("allowed_armor_classes") or [])
    excluded_armor_classes = set(profile.get("excluded_armor_classes") or [])
    allowed_armor_slots = set(profile.get("allowed_armor_slots") or [])
    for item_id, raw_record in dict(item_records or {}).items():
        record = dict(raw_record or {})
        if str(record.get("category") or "").strip().lower() != profile["category"]:
            continue
        if not _level_band_matches(record, profile):
            continue
        record_tags = set(record.get("tags") or [])
        if required_tags and not required_tags.issubset(record_tags):
            continue
        if profile["category"] == "weapon":
            weapon_class = str(record.get("weapon_class") or "").strip().lower()
            if excluded_weapon_classes and weapon_class in excluded_weapon_classes:
                continue
            if allowed_weapon_classes and weapon_class not in allowed_weapon_classes:
                continue
        if profile["category"] == "armor":
            armor_class = str(record.get("armor_class") or "").strip().lower()
            armor_slot = str(record.get("armor_slot") or "").strip().lower()
            if excluded_armor_classes and armor_class in excluded_armor_classes:
                continue
            if allowed_armor_classes and armor_class not in allowed_armor_classes:
                continue
            if not ignore_armor_slots and allowed_armor_slots and armor_slot not in allowed_armor_slots:
                continue
        record["id"] = str(record.get("id") or item_id)
        candidates.append(record)
    return candidates


def _choose_candidate(candidates: list[dict], profile: dict, rng, *, forced_slot: str = "") -> dict:
    if profile["category"] != "weapon":
        armor_candidates = list(candidates)
        if forced_slot:
            slot_candidates = [candidate for candidate in armor_candidates if str(candidate.get("armor_slot") or "").strip().lower() == forced_slot]
            if slot_candidates:
                armor_candidates = slot_candidates
        grouped_by_slot = {}
        for record in armor_candidates:
            grouped_by_slot.setdefault(str(record.get("armor_slot") or "").strip().lower(), []).append(record)
        preferred_slots = {
            slot_name: weight
            for slot_name, weight in dict(profile.get("preferred_armor_slots") or {}).items()
            if weight > 0 and slot_name in grouped_by_slot and not forced_slot
        }
        if preferred_slots:
            chosen_slot = rng.choices(list(preferred_slots.keys()), weights=list(preferred_slots.values()), k=1)[0]
            armor_candidates = list(grouped_by_slot.get(chosen_slot) or armor_candidates)
        grouped_by_class = {}
        for record in armor_candidates:
            grouped_by_class.setdefault(str(record.get("armor_class") or "").strip().lower(), []).append(record)
        preferred_classes = {
            armor_class: weight
            for armor_class, weight in dict(profile.get("preferred_armor_classes") or {}).items()
            if weight > 0 and armor_class in grouped_by_class
        }
        if preferred_classes:
            chosen_class = rng.choices(list(preferred_classes.keys()), weights=list(preferred_classes.values()), k=1)[0]
            class_candidates = list(grouped_by_class.get(chosen_class) or [])
            if class_candidates:
                return rng.choice(class_candidates)
        return rng.choice(armor_candidates)
    grouped = {}
    for record in candidates:
        grouped.setdefault(str(record.get("weapon_class") or ""), []).append(record)
    preferred = {
        weapon_class: weight
        for weapon_class, weight in dict(profile.get("preferred_weapon_classes") or {}).items()
        if weight > 0 and weapon_class in grouped
    }
    if preferred:
        chosen_class = rng.choices(list(preferred.keys()), weights=list(preferred.values()), k=1)[0]
        class_candidates = list(grouped.get(chosen_class) or [])
        if class_candidates:
            return rng.choice(class_candidates)
    return rng.choice(candidates)


def _add_selected_item(selected: dict, inventory: list[str], price_map: dict[str, int], inventory_entry_map: dict[str, str], item_ids: list[str]) -> None:
    display_name = str(selected.get("name") or selected.get("id") or "").strip()
    normalized_label = display_name.lower()
    inventory.append(display_name)
    price_map[normalized_label] = int(selected.get("value", 0) or 0)
    inventory_entry_map[normalized_label] = str(selected.get("id") or "").strip()
    item_ids.append(str(selected.get("id") or "").strip())


def _add_ammo_entry(entry: dict, inventory: list, price_map: dict[str, int], inventory_entry_map: dict, item_ids: list[str]) -> None:
    _append_vendor_entry(entry, inventory, price_map, inventory_entry_map, item_ids)


def generate_vendor_stock(profile: dict, *, item_records: dict | None = None, rng=None) -> dict:
    resolved_profile = get_vendor_profile(profile.get("id")) if "id" in profile else normalize_vendor_profile(profile)
    records = dict(item_records or {}) or item_loader.load_all_items()
    rng = rng or random.Random()
    if resolved_profile["category"] == "general_goods":
        return _generate_general_goods_stock(resolved_profile, records, rng)
    candidates = _filter_candidates(resolved_profile, records)
    fallback_candidates = _filter_candidates(resolved_profile, records, ignore_armor_slots=True) if resolved_profile["category"] == "armor" else list(candidates)
    if not candidates:
        raise ValueError(f"Vendor profile '{resolved_profile['id']}' produced no candidate items")

    working_candidates = list(candidates)
    fallback_working_candidates = list(fallback_candidates)
    inventory = []
    price_map = {}
    inventory_entry_map = {}
    item_ids = []
    stock_count = int(resolved_profile.get("stock_count", 1) or 1)
    allow_duplicates = bool(resolved_profile.get("allow_duplicates", True))

    if resolved_profile["category"] == "armor":
        kit_entries = generate_kit_stock(resolved_profile, item_records=records, rng=rng)
        kit_entries = _trim_kit_entries(kit_entries, int(resolved_profile.get("stock_count", 1) or 1))
        return _generate_armor_stock(resolved_profile, working_candidates, fallback_working_candidates, rng, reserved_entries=kit_entries)

    for _index in range(stock_count):
        if not working_candidates:
            if not inventory:
                raise ValueError(f"Vendor profile '{resolved_profile['id']}' produced no stock")
            break
        selected = _choose_candidate(working_candidates, resolved_profile, rng)
        _add_selected_item(selected, inventory, price_map, inventory_entry_map, item_ids)
        if not allow_duplicates:
            working_candidates = [candidate for candidate in working_candidates if str(candidate.get("id") or "") != str(selected.get("id") or "")]

    if not inventory:
        raise ValueError(f"Vendor profile '{resolved_profile['id']}' produced no stock")

    ammo_entries = []
    if resolved_profile.get("ammo_types") and resolved_profile.get("ammo_classes"):
        ammo_entries = generate_ammo_stock(resolved_profile, item_records=records, rng=rng)
        for entry in ammo_entries:
            _add_ammo_entry(entry, inventory, price_map, inventory_entry_map, item_ids)

    return {
        "inventory": inventory,
        "price_map": price_map,
        "inventory_entry_map": inventory_entry_map,
        "item_ids": item_ids,
    }