from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path

import yaml


_VOCAB_PATH = Path(__file__).resolve().parent.parent / "vocab" / "terrain_vocab.yaml"
_REQUIRED_FIELDS = ("primary", "secondary")


def _require_mapping(data: object, label: str) -> Mapping:
    if not isinstance(data, Mapping):
        raise ValueError(f"{label} must be a mapping.")
    return data


def _normalize_optional_string(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_string_list(value: object, label: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be a list of strings.")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


@lru_cache(maxsize=1)
def load_terrain_vocab() -> dict[str, list[str]]:
    with _VOCAB_PATH.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("terrain vocab must be a mapping.")
    normalized: dict[str, list[str]] = {}
    for key, value in payload.items():
        normalized[str(key or "").strip()] = _normalize_string_list(value, f"terrain vocab '{key}'")
    for required_key in _REQUIRED_FIELDS:
        if required_key not in normalized:
            raise ValueError(f"terrain vocab missing '{required_key}'.")
    return normalized


def normalize_room_terrain(data: object) -> dict[str, str | None]:
    if data in (None, ""):
        return {"primary": None, "secondary": None}

    payload = _require_mapping(data, "room terrain")
    vocab = load_terrain_vocab()
    normalized = {
        "primary": _normalize_optional_string(payload.get("primary")),
        "secondary": _normalize_optional_string(payload.get("secondary")),
    }

    primary = normalized["primary"]
    if primary is not None and primary not in vocab["primary"]:
        raise ValueError(f"room.terrain.primary must be one of: {', '.join(vocab['primary'])}")

    secondary = normalized["secondary"]
    if secondary is not None and secondary not in vocab["secondary"]:
        raise ValueError(f"room.terrain.secondary must be one of: {', '.join(vocab['secondary'])}")

    return normalized