from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _catalog_path() -> Path:
    return _repo_root() / "world" / "builder" / "content" / "forage_catalog.yaml"


@lru_cache(maxsize=1)
def load_forage_catalog() -> dict[str, object]:
    path = _catalog_path()
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("forage catalog must be a mapping.")
    return payload


@lru_cache(maxsize=1)
def iter_forage_catalog_entries() -> tuple[dict[str, object], ...]:
    entries: list[dict[str, object]] = []
    for group_name, group_entries in load_forage_catalog().items():
        if not isinstance(group_entries, dict):
            continue
        for slug, payload in group_entries.items():
            if not isinstance(payload, dict):
                continue
            display_name = str(payload.get("display_name") or "").strip()
            if not display_name:
                continue
            entries.append(
                {
                    "group": str(group_name or "").strip(),
                    "slug": str(slug or "").strip(),
                    **payload,
                }
            )
    return tuple(entries)


def clear_forage_catalog_cache() -> None:
    load_forage_catalog.cache_clear()
    iter_forage_catalog_entries.cache_clear()