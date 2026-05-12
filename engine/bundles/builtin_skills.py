from __future__ import annotations

import logging

from engine.bundles.skill_registry import SkillRegistry, skill_registry
from world.systems.canon_seed import connect_direlore


LOGGER = logging.getLogger(__name__)
SOURCE_BUNDLE = "engine.builtin"

LEGACY_SKILL_PULSE_GROUPS = {
    "evasion": 100,
    "brawling": 100,
    "athletics": 100,
    "stealth": 120,
    "perception": 120,
    "locksmithing": 120,
    "first_aid": 120,
    "appraisal": 140,
    "light_edge": 140,
    "targeted_magic": 160,
    "debilitation": 160,
    "empathy": 180,
    "scholarship": 180,
}

FALLBACK_SKILLS = {
    "athletics": {
        "id": "athletics",
        "canon_id": None,
        "display_name": "Athletics",
        "group": "survival",
        "description": "Fallback skill definition for athletics.",
        "skillset": "survival",
        "pulse_group": 100,
    },
    "brawling": {
        "id": "brawling",
        "canon_id": None,
        "display_name": "Brawling",
        "group": "weapons",
        "description": "Fallback skill definition for brawling.",
        "skillset": "weapons",
        "pulse_group": 100,
    },
    "debilitation": {
        "id": "debilitation",
        "canon_id": None,
        "display_name": "Debilitation",
        "group": "magic",
        "description": "Fallback skill definition for debilitation.",
        "skillset": "magic",
        "pulse_group": 160,
    },
    "empathy": {
        "id": "empathy",
        "canon_id": None,
        "display_name": "Empathy",
        "group": "magic",
        "description": "Fallback skill definition for empathy.",
        "skillset": "magic",
        "pulse_group": 180,
    },
    "evasion": {
        "id": "evasion",
        "canon_id": None,
        "display_name": "Evasion",
        "group": "survival",
        "description": "Fallback skill definition for evasion.",
        "skillset": "survival",
        "pulse_group": 100,
    },
    "first_aid": {
        "id": "first_aid",
        "canon_id": None,
        "display_name": "First Aid",
        "group": "survival",
        "description": "Fallback skill definition for first aid.",
        "skillset": "survival",
        "pulse_group": 120,
    },
    "locksmithing": {
        "id": "locksmithing",
        "canon_id": None,
        "display_name": "Locksmithing",
        "group": "survival",
        "description": "Fallback skill definition for locksmithing.",
        "skillset": "survival",
        "pulse_group": 120,
    },
    "light_edge": {
        "id": "light_edge",
        "canon_id": None,
        "display_name": "Light Edge",
        "group": "weapons",
        "description": "Fallback skill definition for light edged weapons.",
        "skillset": "weapons",
        "pulse_group": 140,
    },
    "perception": {
        "id": "perception",
        "canon_id": None,
        "display_name": "Perception",
        "group": "survival",
        "description": "Fallback skill definition for perception.",
        "skillset": "survival",
        "pulse_group": 120,
    },
    "scholarship": {
        "id": "scholarship",
        "canon_id": None,
        "display_name": "Scholarship",
        "group": "lore",
        "description": "Fallback skill definition for scholarship.",
        "skillset": "lore",
        "pulse_group": 180,
    },
    "stealth": {
        "id": "stealth",
        "canon_id": None,
        "display_name": "Stealth",
        "group": "survival",
        "description": "Fallback skill definition for stealth.",
        "skillset": "survival",
        "pulse_group": 120,
    },
    "targeted_magic": {
        "id": "targeted_magic",
        "canon_id": None,
        "display_name": "Targeted Magic",
        "group": "magic",
        "description": "Fallback skill definition for targeted magic.",
        "skillset": "magic",
        "pulse_group": 160,
    },
}


def normalize_skill_registry_key(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _infer_skill_group(key: str, row: dict) -> str:
    explicit_group = str(row.get("skillset") or "").strip().lower()
    if explicit_group:
        return explicit_group
    if key in {"perception", "hiding"}:
        return "survival"
    if key in {"mechanical_lore", "trading", "astrology"}:
        return "lore"
    if key in {"primary_magic", "transference", "magical_devices"}:
        return "magic"
    return "general"


def _definition_from_row(row: dict) -> tuple[str, dict]:
    key = normalize_skill_registry_key(row.get("name"))
    display_name = str(row.get("name") or "").strip() or key.replace("_", " ").title()
    description = str(row.get("description") or "").strip() or f"Canonical skill row from canon_skills for {display_name}."
    group = _infer_skill_group(key, row)
    return key, {
        "id": key,
        "canon_id": row.get("id"),
        "display_name": display_name,
        "group": group,
        "description": description,
        "gsl_id": row.get("gsl_id"),
        "skillset": str(row.get("skillset") or "").strip().lower() or group,
        "source_entity_id": row.get("source_entity_id"),
        "confidence": row.get("confidence"),
        "pulse_group": int(LEGACY_SKILL_PULSE_GROUPS.get(key, 100) or 100),
        "resolved": not key.startswith("unknown_"),
    }


def populate_skill_registry_fallback(*, registry: SkillRegistry | None = None, source_bundle: str = SOURCE_BUNDLE, log=LOGGER) -> str:
    target_registry = registry or skill_registry
    target_registry.clear()
    for key, definition in FALLBACK_SKILLS.items():
        payload = dict(definition)
        payload["canon_id"] = payload.get("canon_id") if payload.get("canon_id") is not None else 0
        target_registry.register(key, payload, source_bundle=source_bundle)
    if log is not None:
        log.warning("[Bundles] skill_registry running on fallback subset (%s skills)", len(FALLBACK_SKILLS))
    return "fallback"


def populate_skill_registry_from_canon(
    *,
    registry: SkillRegistry | None = None,
    source_bundle: str = SOURCE_BUNDLE,
    connection_factory=connect_direlore,
    log=LOGGER,
) -> str:
    target_registry = registry or skill_registry
    try:
        with connection_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, gsl_id, name, skillset, description, source_entity_id, confidence
                FROM public.canon_skills
                ORDER BY id
                """
            )
            rows = cur.fetchall()
        target_registry.clear()
        unresolved = 0
        for row in rows:
            key, definition = _definition_from_row(row)
            if key.startswith("unknown_"):
                unresolved += 1
            target_registry.register(key, definition, source_bundle=source_bundle)
        if log is not None:
            log.info(
                "[Bundles] Populated skill_registry with %s skills from canon_skills (%s unresolved placeholder rows)",
                len(rows),
                unresolved,
            )
        return "canon"
    except Exception as exc:
        if log is not None:
            log.warning("[Bundles] DireLore canon_skills unavailable at boot; using fallback skill registry: %s", exc)
        return populate_skill_registry_fallback(registry=target_registry, source_bundle=source_bundle, log=log)