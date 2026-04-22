from __future__ import annotations

from pathlib import Path

import yaml

from server.systems import item_loader


LOOT_ROOT = Path(__file__).resolve().parents[3] / "world_data" / "loot"
LOOT_ALLOWED_TOP_LEVEL_KEYS = {"id", "drops"}
LOOT_DROP_ALLOWED_KEYS = {"item", "chance", "min", "max"}

loot_registry: dict[str, dict] = {}


def _coerce_int(value, field_name: str, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return parsed


def _coerce_float(value, field_name: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{field_name} must be <= {maximum}")
    return parsed


def validate_loot_table(payload: dict, *, item_records: dict[str, dict] | None = None) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Loot payload must be an object")

    unknown_top_level = sorted(set(payload.keys()) - LOOT_ALLOWED_TOP_LEVEL_KEYS)
    if unknown_top_level:
        raise ValueError(f"unknown loot fields: {', '.join(unknown_top_level)}")

    loot_id = str(payload.get("id") or "").strip()
    if not loot_id:
        raise ValueError("id is required")

    raw_drops = payload.get("drops")
    if not isinstance(raw_drops, list) or not raw_drops:
        raise ValueError("drops must be a non-empty list")

    item_records = item_records if item_records is not None else item_loader.load_all_items()
    normalized_drops: list[dict] = []
    for index, raw_entry in enumerate(raw_drops):
        field_prefix = f"drops[{index}]"
        if not isinstance(raw_entry, dict):
            raise ValueError(f"{field_prefix} must be an object")
        unknown_drop_fields = sorted(set(raw_entry.keys()) - LOOT_DROP_ALLOWED_KEYS)
        if unknown_drop_fields:
            raise ValueError(f"unknown {field_prefix} fields: {', '.join(unknown_drop_fields)}")

        item_id = str(raw_entry.get("item") or "").strip()
        if not item_id:
            raise ValueError(f"{field_prefix}.item is required")
        if item_id not in item_records:
            raise ValueError(f"{field_prefix}.item references unknown item '{item_id}'")

        chance = _coerce_float(raw_entry.get("chance", 0.0), f"{field_prefix}.chance", minimum=0.0, maximum=1.0)
        min_count = _coerce_int(raw_entry.get("min", 1), f"{field_prefix}.min", minimum=1)
        max_count = _coerce_int(raw_entry.get("max", raw_entry.get("min", 1)), f"{field_prefix}.max", minimum=1)
        if min_count > max_count:
            raise ValueError(f"{field_prefix}.min must be <= {field_prefix}.max")

        normalized_drops.append(
            {
                "item": item_id,
                "chance": chance,
                "min": min_count,
                "max": max_count,
            }
        )

    return {
        "id": loot_id,
        "drops": normalized_drops,
    }


def _iter_loot_files():
    if not LOOT_ROOT.exists():
        return
    for file_path in sorted(LOOT_ROOT.glob("*.yaml")):
        if file_path.name == "schema_loot.yaml":
            continue
        yield file_path


def load_all_loot_tables(*, item_records: dict[str, dict] | None = None) -> dict[str, dict]:
    item_records = item_records if item_records is not None else item_loader.load_all_items()
    tables: dict[str, dict] = {}
    for file_path in _iter_loot_files() or []:
        with file_path.open(encoding="utf-8") as file_handle:
            payload = yaml.safe_load(file_handle) or {}
        normalized = validate_loot_table(payload, item_records=item_records)
        tables[normalized["id"]] = normalized
    return dict(sorted(tables.items(), key=lambda item: item[0]))


def reload_loot_tables(*, item_records: dict[str, dict] | None = None) -> dict[str, dict]:
    loot_registry.clear()
    loot_registry.update(load_all_loot_tables(item_records=item_records))
    return dict(loot_registry)


def ensure_loot_tables_loaded(*, item_records: dict[str, dict] | None = None) -> None:
    if not loot_registry:
        reload_loot_tables(item_records=item_records)