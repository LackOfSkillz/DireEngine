from __future__ import annotations

from datetime import date
import re

from world.systems.canon_seed import connect_direlore

from . import item_loader
from .item_stats import derive_item_stats, normalize_item_weight


DEFAULT_IMPORT_LIMIT = 200
ITEM_NAME_PREFIX_RE = re.compile(r"^(Armor|Weapon|Container|Clothing|Jewelry|Furniture|Item):", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
VALUE_RE = re.compile(r"(\d[\d,]*)")
NOISE_ITEM_PATTERNS = (
    re.compile(r"^test\b", re.IGNORECASE),
    re.compile(r"\bdebug\b", re.IGNORECASE),
)
PLURAL_NOUN_HINTS = ("pants", "shorts", "gloves", "greaves", "robes", "leathers", "leggings", "trousers")
CATEGORY_MAP = {
    "weapon": "weapon",
    "weapons": "weapon",
    "armor": "armor",
    "armour": "armor",
    "shield": "armor",
    "clothing": "clothing",
    "clothes": "clothing",
    "jewelry": "jewelry",
    "jewellery": "jewelry",
    "furniture": "furniture",
    "container": "container",
    "containers": "container",
    "consumable": "consumable",
    "consumables": "consumable",
    "food": "consumable",
    "drink": "consumable",
    "general": "misc",
    "misc": "misc",
}


def normalize_import_item_id(name: str) -> str:
    text = ITEM_NAME_PREFIX_RE.sub("", str(name or "").strip())
    text = NON_ALNUM_RE.sub("_", text.lower())
    return text.strip("_")


def clean_item_name(name: str) -> str:
    return ITEM_NAME_PREFIX_RE.sub("", str(name or "").strip()).strip()


def normalize_category(raw_value: str) -> str:
    normalized = str(raw_value or "").strip().lower()
    if not normalized:
        return "misc"
    return CATEGORY_MAP.get(normalized, "misc")


def ensure_unique_id(base_id: str, existing_ids: set[str]) -> str:
    candidate = str(base_id or "").strip() or "item"
    if candidate not in existing_ids:
        return candidate
    index = 1
    while True:
        candidate_with_suffix = f"{candidate}_{index}"
        if candidate_with_suffix not in existing_ids:
            return candidate_with_suffix
        index += 1


def should_skip_item_row(row: dict) -> bool:
    name = clean_item_name((row or {}).get("name") or "")
    if not name:
        return True
    if name.lower() in {"unknown", "placeholder"}:
        return True
    return any(pattern.search(name) for pattern in NOISE_ITEM_PATTERNS)


def infer_item_category(row: dict) -> str:
    raw_name = str((row or {}).get("name") or "")
    item_type = str((row or {}).get("item_type") or "").strip().lower()
    prefix = str(raw_name.split(":", 1)[0] if ":" in raw_name else "").strip().lower()
    if prefix in {"weapon", "armor", "container", "clothing", "jewelry", "furniture"}:
        return normalize_category(prefix)
    if any(keyword in item_type for keyword in ("armor", "brigandine", "chain", "plate", "leather", "shield")):
        return normalize_category("armor")
    if any(keyword in item_type for keyword in ("weapon", "blade", "sword", "bow", "axe", "hammer", "staff", "dagger")):
        return normalize_category("weapon")
    if any(keyword in item_type for keyword in ("potion", "elixir", "food", "drink", "herb", "consumable")):
        return normalize_category("consumable")
    if any(keyword in item_type for keyword in ("ring", "necklace", "earring", "bracelet", "jewelry")):
        return normalize_category("jewelry")
    return normalize_category("misc")


def infer_equipment_slot(category: str, row: dict) -> str:
    name = clean_item_name((row or {}).get("name") or "").lower()
    item_type = str((row or {}).get("item_type") or "").strip().lower()
    if category == "weapon":
        return "weapon"
    if category != "armor":
        return "none"
    if any(keyword in name or keyword in item_type for keyword in ("helm", "helmet", "hood", "mask", "cowl")):
        return "head"
    if any(keyword in name or keyword in item_type for keyword in ("glove", "gauntlet", "bracer")):
        return "hands"
    if any(keyword in name or keyword in item_type for keyword in ("greave", "legging", "pants", "trousers")):
        return "legs"
    return "chest"


def infer_stack_profile(category: str) -> tuple[bool, int]:
    if category == "consumable":
        return True, 10
    return False, 1


def parse_gold_value(appraised_cost: str | None) -> int:
    text = str(appraised_cost or "").strip()
    match = VALUE_RE.search(text)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def build_item_description(name: str) -> dict:
    lowered = str(name or "").strip().lower()
    if any(lowered.endswith(hint) for hint in PLURAL_NOUN_HINTS):
        return {
            "short": f"some {lowered}",
            "long": f"Some {lowered} lie here.",
        }
    article = "an" if lowered[:1] in "aeiou" else "a"
    lead = article.capitalize()
    return {
        "short": f"{article} {lowered}".strip(),
        "long": f"{lead} {lowered} lies here.",
    }


def interpret_item(row: dict) -> dict:
    name = clean_item_name((row or {}).get("name") or "")
    category = infer_item_category(row)
    stackable, max_stack = infer_stack_profile(category)
    stats = derive_item_stats(category, raw_weight=row.get("weight"))
    return {
        "id": normalize_import_item_id(name),
        "name": name,
        "category": category,
        "value": parse_gold_value(row.get("appraised_cost")) or max(1, int(stats["attack"] + stats["defense"] + 10)),
        "weight": normalize_item_weight(row.get("weight")),
        "stackable": stackable,
        "max_stack": max_stack,
        "equipment": {
            "slot": infer_equipment_slot(category, row),
            "attack": stats["attack"],
            "defense": stats["defense"],
        },
        "consumable": {"effect": "", "duration": 0},
        "container": {"capacity": 10 if category == "container" else 0},
        "description": build_item_description(name),
        "meta": {
            "source": "direlore",
            "imported_at": date.today().isoformat(),
        },
    }


def fetch_items(limit: int | None = None) -> list[dict]:
    with connect_direlore() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, item_type, weight, appraised_cost, has_atmo, has_custom_verbs
                FROM canon_items
                WHERE COALESCE(name, '') <> ''
                ORDER BY id
                LIMIT %s
                """,
                (max(1, int(limit or DEFAULT_IMPORT_LIMIT)),),
            )
            return list(cur.fetchall())


def import_direlore_items(*, limit: int = DEFAULT_IMPORT_LIMIT, dry_run: bool = True, overwrite: bool = False) -> dict:
    rows = fetch_items(limit=limit)
    existing_ids = set(item_loader.load_all_items().keys()) if not dry_run else set()
    reserved_ids = set()
    summary = {
        "selected": len(rows),
        "imported": 0,
        "skipped_existing": 0,
        "skipped_invalid": 0,
        "missing": {
            "appraised_cost": 0,
            "weight": 0,
            "equipment_slot": 0,
        },
        "id_collisions_resolved": 0,
        "items": [],
    }

    for row in rows:
        if should_skip_item_row(row):
            summary["skipped_invalid"] += 1
            continue
        payload = interpret_item(row)
        base_id = payload["id"]
        candidate_ids = set(reserved_ids)
        if not overwrite:
            candidate_ids.update(existing_ids)
        payload["id"] = ensure_unique_id(base_id, candidate_ids)
        if payload["id"] != base_id:
            summary["id_collisions_resolved"] += 1
        if not str(row.get("appraised_cost") or "").strip():
            summary["missing"]["appraised_cost"] += 1
        if row.get("weight") is None:
            summary["missing"]["weight"] += 1
        if payload["equipment"]["slot"] == "none" and payload["category"] in {"weapon", "armor"}:
            summary["missing"]["equipment_slot"] += 1

        if not dry_run and payload["id"] in existing_ids and not overwrite:
            summary["skipped_existing"] += 1
            continue
        if not dry_run:
            item_loader.save_item_payload(payload)
        existing_ids.add(payload["id"])
        reserved_ids.add(payload["id"])
        summary["imported"] += 1
        summary["items"].append(
            {
                "id": payload["id"],
                "name": payload["name"],
                "category": payload["category"],
                "source": payload["meta"]["source"],
            }
        )

    processed = max(1, summary["imported"] + summary["skipped_existing"])
    summary["missing_percent"] = {
        key: round((value / processed) * 100.0, 1)
        for key, value in summary["missing"].items()
    }
    return summary