from __future__ import annotations

from pathlib import Path

import yaml


NPC_TYPE_DIRECTORIES = {
    "hostile": "hostile",
    "neutral": "neutral",
    "vendor": "vendors",
}
NPC_ROOT = Path(__file__).resolve().parents[2] / "world_data" / "npcs"
NPC_ALLOWED_TOP_LEVEL_KEYS = {"id", "name", "type", "stats", "behavior", "vendor", "dialogue", "description", "meta", "loot_table", "vendor_profile_id"}
NPC_ALLOWED_NESTED_KEYS = {
    "stats": {"level", "health", "attack", "defense"},
    "behavior": {"aggressive", "roam", "assist"},
    "vendor": {"enabled", "inventory"},
    "dialogue": {"greeting", "idle"},
    "description": {"short", "long"},
    "meta": {"source", "imported_at"},
}


def _npc_defaults(npc_id: str = "", npc_type: str = "neutral") -> dict:
    return {
        "id": npc_id,
        "name": "",
        "type": npc_type,
        "stats": {
            "level": 1,
            "health": 1,
            "attack": 0,
            "defense": 0,
        },
        "behavior": {
            "aggressive": False,
            "roam": False,
            "assist": False,
        },
        "vendor": {
            "enabled": False,
            "inventory": [],
        },
        "dialogue": {
            "greeting": "",
            "idle": [],
        },
        "description": {
            "short": "",
            "long": "",
        },
        "loot_table": "",
        "vendor_profile_id": "",
        "meta": {
            "source": "",
            "imported_at": "",
        },
    }


def _coerce_int(value, field_name: str, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return parsed


def _normalize_npc_type(value) -> str:
    npc_type = str(value or "").strip().lower()
    if npc_type not in NPC_TYPE_DIRECTORIES:
        raise ValueError("type must be hostile, neutral, or vendor")
    return npc_type


def _normalize_string_list(values) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value or "") for value in values]


def validate_npc_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("NPC payload must be an object")
    unknown_top_level = sorted(set(payload.keys()) - NPC_ALLOWED_TOP_LEVEL_KEYS)
    if unknown_top_level:
        raise ValueError(f"unknown npc fields: {', '.join(unknown_top_level)}")
    for field_name, allowed_keys in NPC_ALLOWED_NESTED_KEYS.items():
        field_value = payload.get(field_name)
        if field_value is None:
            continue
        if not isinstance(field_value, dict):
            raise ValueError(f"{field_name} must be an object")
        unknown_nested = sorted(set(field_value.keys()) - allowed_keys)
        if unknown_nested:
            raise ValueError(f"unknown {field_name} fields: {', '.join(unknown_nested)}")


def normalize_npc_payload(payload: dict, *, fallback_id: str = "", fallback_type: str = "neutral") -> dict:
    validate_npc_payload(payload)

    npc_type = _normalize_npc_type(payload.get("type") or fallback_type)
    defaults = _npc_defaults(str(payload.get("id") or fallback_id or "").strip(), npc_type)
    npc_id = str(payload.get("id") or fallback_id or "").strip()
    name = str(payload.get("name") or "").strip()

    if not npc_id:
        raise ValueError("id is required")
    if not name:
        raise ValueError("name is required")

    stats = dict(defaults["stats"])
    stats_payload = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    stats["level"] = _coerce_int(stats_payload.get("level", stats["level"]), "stats.level", minimum=1)
    stats["health"] = _coerce_int(stats_payload.get("health", stats["health"]), "stats.health", minimum=0)
    stats["attack"] = _coerce_int(stats_payload.get("attack", stats["attack"]), "stats.attack", minimum=0)
    stats["defense"] = _coerce_int(stats_payload.get("defense", stats["defense"]), "stats.defense", minimum=0)

    behavior = dict(defaults["behavior"])
    behavior_payload = payload.get("behavior") if isinstance(payload.get("behavior"), dict) else {}
    behavior["aggressive"] = bool(behavior_payload.get("aggressive", behavior["aggressive"]))
    behavior["roam"] = bool(behavior_payload.get("roam", behavior["roam"]))
    behavior["assist"] = bool(behavior_payload.get("assist", behavior["assist"]))
    if npc_type == "hostile":
        behavior["aggressive"] = True

    vendor = dict(defaults["vendor"])
    vendor_payload = payload.get("vendor") if isinstance(payload.get("vendor"), dict) else {}
    vendor["enabled"] = bool(vendor_payload.get("enabled", vendor["enabled"]))
    vendor["inventory"] = _normalize_string_list(vendor_payload.get("inventory", vendor["inventory"]))
    if npc_type != "vendor":
        vendor["enabled"] = False
        vendor["inventory"] = []

    dialogue = dict(defaults["dialogue"])
    dialogue_payload = payload.get("dialogue") if isinstance(payload.get("dialogue"), dict) else {}
    dialogue["greeting"] = str(dialogue_payload.get("greeting", dialogue["greeting"]) or "")
    dialogue["idle"] = _normalize_string_list(dialogue_payload.get("idle", dialogue["idle"]))

    description = dict(defaults["description"])
    description_payload = payload.get("description") if isinstance(payload.get("description"), dict) else {}
    description["short"] = str(description_payload.get("short", description["short"]) or "").strip()
    description["long"] = str(description_payload.get("long", description["long"]) or "").strip()

    meta = dict(defaults["meta"])
    meta_payload = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    meta["source"] = str(meta_payload.get("source", meta["source"]) or "").strip()
    meta["imported_at"] = str(meta_payload.get("imported_at", meta["imported_at"]) or "").strip()
    loot_table = str(payload.get("loot_table") or defaults["loot_table"] or "").strip()
    vendor_profile_id = str(payload.get("vendor_profile_id") or defaults["vendor_profile_id"] or "").strip()

    return {
        "id": npc_id,
        "name": name,
        "type": npc_type,
        "stats": stats,
        "behavior": behavior,
        "vendor": vendor,
        "dialogue": dialogue,
        "description": description,
        "loot_table": loot_table,
        "vendor_profile_id": vendor_profile_id,
        "meta": meta,
    }


def _npc_directory_for_type(npc_type: str) -> Path:
    return NPC_ROOT / NPC_TYPE_DIRECTORIES[_normalize_npc_type(npc_type)]


def _iter_npc_files():
    if not NPC_ROOT.exists():
        return
    for directory_name in NPC_TYPE_DIRECTORIES.values():
        directory = NPC_ROOT / directory_name
        if not directory.exists():
            continue
        for file_path in sorted(directory.glob("*.yaml")):
            if file_path.name == "schema_npc.yaml":
                continue
            yield file_path


def _find_npc_file(npc_id: str) -> Path | None:
    normalized_id = str(npc_id or "").strip()
    if not normalized_id:
        return None
    for file_path in _iter_npc_files() or []:
        if file_path.stem == normalized_id:
            return file_path
    return None


def load_all_npcs():
    npcs = {}
    for file_path in _iter_npc_files() or []:
        with file_path.open(encoding="utf-8") as file_handle:
            payload = yaml.safe_load(file_handle) or {}
        normalized = normalize_npc_payload(payload, fallback_id=file_path.stem)
        npcs[normalized["id"]] = normalized
    return dict(sorted(npcs.items(), key=lambda item: item[0]))


def save_npc_payload(payload: dict) -> dict:
    normalized = normalize_npc_payload(payload)
    target_path = _npc_directory_for_type(normalized["type"]) / f"{normalized['id']}.yaml"
    previous_path = _find_npc_file(normalized["id"])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if previous_path and previous_path != target_path and previous_path.exists():
        previous_path.unlink()
    with target_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(normalized, file_handle, sort_keys=False)
    return normalized


def delete_npc_payload(npc_id: str) -> str:
    file_path = _find_npc_file(npc_id)
    if file_path is None or not file_path.exists():
        raise ValueError("not_found")
    file_path.unlink()
    return str(npc_id)