from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path

import yaml


_ROOM_VOCAB_PATH = Path(__file__).resolve().parent.parent / "vocab" / "room_vocab.yaml"
_SINGLE_VALUE_FIELDS = ("structure", "specific_function", "named_feature", "condition")


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
def load_room_vocab() -> dict[str, list[str]]:
    with _ROOM_VOCAB_PATH.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("room vocab must be a mapping.")
    normalized: dict[str, list[str]] = {}
    for key, value in payload.items():
        normalized[str(key or "").strip()] = _normalize_string_list(value, f"room vocab '{key}'")
    for required_key in _SINGLE_VALUE_FIELDS:
        if required_key not in normalized:
            raise ValueError(f"room vocab missing '{required_key}'.")
    return normalized


def normalize_room_tags(data: object) -> dict[str, object]:
    if data in (None, ""):
        return {
            "structure": None,
            "specific_function": None,
            "named_feature": None,
            "condition": None,
            "custom": [],
        }

    payload = _require_mapping(data, "room tags")
    vocab = load_room_vocab()
    normalized: dict[str, object] = {
        field: _normalize_optional_string(payload.get(field))
        for field in _SINGLE_VALUE_FIELDS
    }
    normalized["custom"] = _normalize_string_list(payload.get("custom"), "room_tags.custom")

    for field in _SINGLE_VALUE_FIELDS:
        value = normalized[field]
        if value is not None and value not in vocab[field]:
            raise ValueError(f"room_tags.{field} must be one of: {', '.join(vocab[field])}")
    return normalized