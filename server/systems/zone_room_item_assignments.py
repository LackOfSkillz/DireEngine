from pathlib import Path
import re

import yaml


ZONE_ROOT = Path(__file__).resolve().parents[2] / "worlddata" / "zones"


def normalize_room_item_entries(entries):
    merged_entries = {}
    ordered_ids = []
    for entry in list(entries or []):
        if isinstance(entry, dict):
            item_id = str(entry.get("id") or "").strip()
            count = int(entry.get("count") or 0)
            nested_items = normalize_room_item_entries(entry.get("items") or [])
        else:
            item_id = str(entry or "").strip()
            count = 1
            nested_items = []

        if not item_id:
            continue

        if item_id not in merged_entries:
            merged_entries[item_id] = {
                "id": item_id,
                "count": 0,
                "items": nested_items,
            }
            ordered_ids.append(item_id)

        merged_entries[item_id]["count"] += max(0, count)
        if nested_items:
          merged_entries[item_id]["items"] = nested_items

    normalized = []
    for item_id in ordered_ids:
        entry = merged_entries[item_id]
        if entry["count"] <= 0:
            continue
        normalized_entry = {
            "id": item_id,
            "count": entry["count"],
        }
        if entry["items"]:
            normalized_entry["items"] = entry["items"]
        normalized.append(normalized_entry)
    return normalized


def _normalize_zone_id(raw_zone_id):
    text = str(raw_zone_id or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _zone_path(zone_id):
    normalized_zone_id = _normalize_zone_id(zone_id)
    if not normalized_zone_id:
        raise ValueError("zone_id is required")
    return ZONE_ROOT / f"{normalized_zone_id}.yaml"


def _load_zone_payload(zone_id):
    zone_path = _zone_path(zone_id)
    if not zone_path.exists():
        raise ValueError(f"zone not found: {zone_id}")
    with zone_path.open(encoding="utf-8") as file_handle:
        payload = yaml.safe_load(file_handle) or {}

    payload["zone_id"] = _normalize_zone_id(payload.get("zone_id") or zone_id)
    payload["rooms"] = [dict(room or {}) for room in list(payload.get("rooms") or [])]
    for room in payload["rooms"]:
        room["items"] = normalize_room_item_entries(room.get("items") or [])
    return payload


def _write_zone_payload(zone_id, payload):
    normalized_zone_id = _normalize_zone_id(payload.get("zone_id") or zone_id)
    payload["zone_id"] = normalized_zone_id
    for room in list(payload.get("rooms") or []):
        room["items"] = normalize_room_item_entries(room.get("items") or [])

    zone_path = _zone_path(normalized_zone_id)
    zone_path.parent.mkdir(parents=True, exist_ok=True)
    with zone_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(payload, file_handle, sort_keys=False)
    return payload


def resolve_builder_zone_room(room_id, zone_id=""):
    normalized_room_id = str(room_id or "").strip()
    if not normalized_room_id:
        raise ValueError("room_id is required")

    candidate_zone_ids = []
    normalized_zone_id = _normalize_zone_id(zone_id) if zone_id else ""
    if normalized_zone_id:
        candidate_zone_ids.append(normalized_zone_id)
    else:
        candidate_zone_ids.extend(file_path.stem for file_path in sorted(ZONE_ROOT.glob("*.yaml")))

    for candidate_zone_id in candidate_zone_ids:
        zone_payload = _load_zone_payload(candidate_zone_id)
        for room_data in zone_payload.get("rooms") or []:
            if str(room_data.get("id") or "").strip() == normalized_room_id:
                return zone_payload, room_data

    raise ValueError(f"room not found: {normalized_room_id}")


def update_room_items(room_id, items, zone_id=""):
    zone_payload, room_data = resolve_builder_zone_room(room_id, zone_id=zone_id)
    room_data["items"] = normalize_room_item_entries(items)
    updated_zone = _write_zone_payload(zone_payload.get("zone_id") or zone_id or "", zone_payload)
    updated_room = next(
        (
            candidate
            for candidate in updated_zone.get("rooms") or []
            if str(candidate.get("id") or "").strip() == str(room_id or "").strip()
        ),
        None,
    )
    if updated_room is None:
        raise ValueError(f"room not found after update: {room_id}")
    return updated_zone, updated_room