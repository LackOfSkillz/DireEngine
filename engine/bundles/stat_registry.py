from __future__ import annotations

import logging

from engine.bundles.registry import Registry
from world.systems.canon_seed import connect_direlore


LOGGER = logging.getLogger(__name__)

FALLBACK_STAT_DEFINITIONS = {
    "strength": {
        "id": 21,
        "display_name": "Strength",
        "abbreviation": "STR",
        "description": "Fallback canonical stat definition for strength.",
        "gsl_dispatch_id": 1,
        "default": 10,
    },
    "reflex": {
        "id": 22,
        "display_name": "Reflex",
        "abbreviation": "REF",
        "description": "Fallback canonical stat definition for reflex.",
        "gsl_dispatch_id": 2,
        "default": 10,
    },
    "agility": {
        "id": 23,
        "display_name": "Agility",
        "abbreviation": "AGI",
        "description": "Fallback canonical stat definition for agility.",
        "gsl_dispatch_id": 3,
        "default": 10,
    },
    "charisma": {
        "id": 24,
        "display_name": "Charisma",
        "abbreviation": "CHA",
        "description": "Fallback canonical stat definition for charisma.",
        "gsl_dispatch_id": 4,
        "default": 10,
    },
    "discipline": {
        "id": 25,
        "display_name": "Discipline",
        "abbreviation": "DIS",
        "description": "Fallback canonical stat definition for discipline.",
        "gsl_dispatch_id": 5,
        "default": 10,
    },
    "wisdom": {
        "id": 26,
        "display_name": "Wisdom",
        "abbreviation": "WIS",
        "description": "Fallback canonical stat definition for wisdom.",
        "gsl_dispatch_id": 6,
        "default": 10,
    },
    "intelligence": {
        "id": 27,
        "display_name": "Intelligence",
        "abbreviation": "INT",
        "description": "Fallback canonical stat definition for intelligence.",
        "gsl_dispatch_id": 7,
        "default": 10,
    },
    "stamina": {
        "id": 28,
        "display_name": "Stamina",
        "abbreviation": "STA",
        "description": "Fallback canonical stat definition for stamina.",
        "gsl_dispatch_id": 8,
        "default": 10,
    },
    "concentration": {
        "id": 29,
        "display_name": "Concentration",
        "abbreviation": "CON",
        "description": "Fallback canonical stat definition for concentration.",
        "gsl_dispatch_id": 9,
        "default": 10,
    },
    "aura": {
        "id": 30,
        "display_name": "Aura",
        "abbreviation": "AUR",
        "description": "Fallback canonical stat definition for aura.",
        "gsl_dispatch_id": 10,
        "default": 10,
    },
}


class StatRegistry(Registry):
    required_fields = ("id", "display_name", "abbreviation")


stat_registry = StatRegistry("stat_registry")


def _normalize_stat_key(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _definition_from_row(row: dict) -> tuple[str, dict]:
    key = _normalize_stat_key(row.get("name"))
    return key, {
        "id": int(row.get("id") or 0),
        "display_name": str(row.get("name") or "").strip(),
        "abbreviation": str(row.get("abbreviation") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "gsl_dispatch_id": row.get("gsl_dispatch_id"),
        "source_entity_id": row.get("source_entity_id"),
        "confidence": row.get("confidence"),
        "default": 10,
    }


def populate_stat_registry_fallback(*, registry: StatRegistry | None = None, source_bundle: str = "engine.builtin") -> str:
    target_registry = registry or stat_registry
    target_registry.clear()
    for key, definition in FALLBACK_STAT_DEFINITIONS.items():
        target_registry.register(key, definition, source_bundle=source_bundle)
    return "fallback"


def populate_stat_registry_from_canon(
    *,
    registry: StatRegistry | None = None,
    source_bundle: str = "engine.builtin",
    connection_factory=connect_direlore,
    log=LOGGER,
) -> str:
    target_registry = registry or stat_registry
    try:
        with connection_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, abbreviation, gsl_dispatch_id, description, source_entity_id, confidence
                FROM public.canon_stats
                ORDER BY id
                """
            )
            rows = cur.fetchall()
        target_registry.clear()
        for row in rows:
            key, definition = _definition_from_row(row)
            target_registry.register(key, definition, source_bundle=source_bundle)
        return "canon"
    except Exception as exc:
        if log is not None:
            log.warning("[Bundles] DireLore canon_stats unavailable at boot; using fallback stat registry: %s", exc)
        return populate_stat_registry_fallback(registry=target_registry, source_bundle=source_bundle)


def get_default_stat_values(*, registry: StatRegistry | None = None) -> dict[str, int]:
    target_registry = registry or stat_registry
    keys = target_registry.list_keys()
    if not keys:
        return {key: int(payload.get("default", 10) or 10) for key, payload in FALLBACK_STAT_DEFINITIONS.items()}
    return {
        key: int((target_registry.get(key) or {}).get("default", 10) or 10)
        for key in keys
    }


def is_known_stat(stat_name: str, *, registry: StatRegistry | None = None) -> bool:
    return (registry or stat_registry).is_registered(_normalize_stat_key(stat_name))