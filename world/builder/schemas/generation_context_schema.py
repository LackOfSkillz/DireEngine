from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path

import yaml


_VOCAB_PATH = Path(__file__).resolve().parent.parent / "vocab" / "zone_vocab.yaml"
_LIST_FIELDS = ("culture", "mood", "banned_phrases")
_SCALAR_FIELDS = ("setting_type", "era_feel", "climate", "voice")
_CONTROLLED_LIST_FIELDS = {
    "culture": "cultures",
    "mood": "moods",
}
_CONTROLLED_SCALAR_FIELDS = {
    "setting_type": "setting_types",
    "era_feel": "eras",
    "climate": "climates",
}


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
    normalized = []
    seen = set()
    for item in value:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


@lru_cache(maxsize=1)
def load_zone_vocab() -> dict[str, list[str]]:
    with _VOCAB_PATH.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("zone vocab must be a mapping.")
    normalized = {}
    for key, value in payload.items():
        normalized[key] = _normalize_string_list(value, f"zone vocab '{key}'")
    for required_key in ("setting_types", "eras", "cultures", "moods", "climates"):
        if required_key not in normalized:
            raise ValueError(f"zone vocab missing '{required_key}'.")
    return normalized


def normalize_generation_context(data: object) -> dict[str, object] | None:
    if data in (None, ""):
        return None
    payload = _require_mapping(data, "generation_context")
    vocab = load_zone_vocab()
    normalized: dict[str, object] = {}
    for field in _SCALAR_FIELDS:
        normalized[field] = _normalize_optional_string(payload.get(field))
    for field in _LIST_FIELDS:
        normalized[field] = _normalize_string_list(payload.get(field), f"generation_context.{field}")
    if not normalized["banned_phrases"]:
        normalized["banned_phrases"] = []

    for field, vocab_key in _CONTROLLED_SCALAR_FIELDS.items():
        value = normalized[field]
        if value is not None and value not in vocab[vocab_key]:
            raise ValueError(f"generation_context.{field} must be one of: {', '.join(vocab[vocab_key])}")
    for field, vocab_key in _CONTROLLED_LIST_FIELDS.items():
        allowed = set(vocab[vocab_key])
        invalid = [value for value in normalized[field] if value not in allowed]
        if invalid:
            raise ValueError(f"generation_context.{field} contains unsupported values: {', '.join(invalid)}")
    return normalized