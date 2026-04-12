"""Helpers for wound state records."""

from __future__ import annotations

from domain.wounds.constants import DEFAULT_INJURIES, DEFAULT_TEND_STATE


def copy_default_injuries() -> dict:
	injuries = {}
	for part_name, data in DEFAULT_INJURIES.items():
		copied = dict(data)
		copied["tend"] = dict(data.get("tend", DEFAULT_TEND_STATE))
		injuries[part_name] = copied
	return injuries


def normalize_body_part(body_part: dict | None) -> dict:
	data = dict(body_part or {})
	data.setdefault("external", 0)
	data.setdefault("internal", 0)
	data.setdefault("bruise", 0)
	data.setdefault("bleed", 0)
	data.setdefault("scar", 0)
	data.setdefault("tended", False)
	data.setdefault("max", 100)
	data.setdefault("vital", False)
	data["tend"] = dict(data.get("tend") or DEFAULT_TEND_STATE)
	return data


def normalize_injuries(injuries: dict | None) -> dict:
	normalized = copy_default_injuries()
	for part_name, body_part in dict(injuries or {}).items():
		normalized[part_name] = normalize_body_part(body_part)
	return normalized
