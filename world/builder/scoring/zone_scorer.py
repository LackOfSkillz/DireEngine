from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

import yaml


class CountBreakdown(TypedDict):
    satisfied: float
    total: float


class SubScore(TypedDict):
    score: int
    breakdown: dict[str, object]


class RoomScore(TypedDict):
    room_id: str
    name: str
    composite: int
    tier: str
    biggest_gap: str


class ZoneScore(TypedDict):
    composite: int
    tier: str
    completeness: SubScore
    depth: SubScore
    engagement: SubScore
    rooms_needing_attention: list[RoomScore]
    room_scores: list[RoomScore]
    room_count: int
    computed_at: str
    zone_id: str


TIER_LADDER = [
    (90, "The bards sing your praises"),
    (80, "Nearly Legendary!"),
    (70, "This is now a must-see destination"),
    (60, "Worth the visit"),
    (50, "It's a bit mid, don't you think?"),
    (30, "The townsfolk will throw rotten food at you"),
    (0, "The bards will mock you"),
]

WEIGHTS = {
    "completeness": 0.40,
    "depth": 0.30,
    "engagement": 0.30,
}

COMPLETENESS_WEIGHTS = {
    "zone_setting_type": 1.0,
    "zone_era_feel": 1.0,
    "zone_climate": 1.0,
    "zone_mood": 1.0,
    "zone_culture": 1.0,
    "zone_voice": 0.5,
    "room_name": 2.0,
    "room_environment": 2.0,
    "room_terrain_primary": 1.5,
    "room_description": 1.0,
    "room_identity_tags": 1.0,
    "exit_validity": 1.0,
    "npc_declaration": 1.0,
}

ROOM_GAP_PRIORITY = (
    ("environment", "no environment"),
    ("name", "no name"),
    ("description", "no description"),
    ("terrain", "no terrain"),
    ("orphan_exits", "orphan exits"),
    ("identity_tags", "untagged"),
    ("atmosphere", "no atmosphere"),
    ("engagement", "low activity"),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _text(value: object) -> str:
    return str(value or "").strip()


def _list(value: object) -> list:
    return list(value or []) if isinstance(value, list) else []


def _mapping(value: object) -> dict:
    return dict(value or {}) if isinstance(value, dict) else {}


def _ratio(satisfied: float, total: float) -> float:
    return 0.0 if total <= 0 else float(satisfied) / float(total)


def _score_percent(value: float) -> int:
    return max(0, min(100, round(value * 100)))


def _tier_for_score(score: int) -> str:
    for threshold, label in TIER_LADDER:
        if score >= threshold:
            return label
    return TIER_LADDER[-1][1]


@lru_cache(maxsize=1)
def _load_forage_catalog() -> dict[str, object]:
    path = _repo_root() / "world" / "builder" / "content" / "forage_catalog.yaml"
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def _healing_secondary_terrain_values() -> set[str]:
    healing_terrains: set[str] = set()
    for group_entries in _load_forage_catalog().values():
        if not isinstance(group_entries, dict):
            continue
        for entry in group_entries.values():
            if not isinstance(entry, dict) or not entry.get("healing"):
                continue
            for terrain_value in _list(entry.get("terrain")):
                terrain_text = _text(terrain_value)
                if terrain_text:
                    healing_terrains.add(terrain_text)
    return healing_terrains


def engagement_target(zone_size: int) -> float:
    if zone_size <= 20:
        return 0.30
    if zone_size >= 200:
        return 0.20
    return 0.30 - (zone_size - 20) * (0.10 / 180)


def _population_storage_choice(zone: dict, kind: str) -> str:
    metadata = _mapping(_mapping(zone.get("_direbuilder")).get("population_storage"))
    choice = _text(metadata.get(kind)).lower()
    if choice in {"placements", "rooms"}:
        return choice
    placements = _mapping(zone.get("placements"))
    if _list(placements.get(kind)):
        return "placements"
    return "rooms"


def _room_population_indexes(zone: dict) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    rooms = _list(zone.get("rooms"))
    room_npcs: dict[str, list[dict]] = { _text(room.get("id")): [] for room in rooms }
    room_items: dict[str, list[dict]] = { _text(room.get("id")): [] for room in rooms }

    if _population_storage_choice(zone, "npcs") == "placements":
        for entry in _list(_mapping(zone.get("placements")).get("npcs")):
            if not isinstance(entry, dict):
                continue
            room_id = _text(entry.get("room"))
            if room_id:
                room_npcs.setdefault(room_id, []).append(dict(entry))
    else:
        for room in rooms:
            room_id = _text(room.get("id"))
            room_npcs[room_id] = [
                {"id": _text(npc_id), "typeclass": "", "flags": []}
                for npc_id in _list(room.get("npcs"))
                if _text(npc_id)
            ]

    if _population_storage_choice(zone, "items") == "placements":
        for entry in _list(_mapping(zone.get("placements")).get("items")):
            if not isinstance(entry, dict):
                continue
            room_id = _text(entry.get("room"))
            if room_id:
                room_items.setdefault(room_id, []).append(dict(entry))
    else:
        for room in rooms:
            room_id = _text(room.get("id"))
            room_items[room_id] = [dict(item) for item in _list(room.get("items")) if isinstance(item, dict)]

    return room_npcs, room_items


def _room_depth_metrics(room: dict) -> dict[str, float]:
    tags = _mapping(room.get("tags"))
    atmosphere = _mapping(tags.get("atmosphere"))
    atmosphere_axes = (
        bool(_list(atmosphere.get("materials"))),
        bool(_list(atmosphere.get("social_character"))),
        bool(_list(atmosphere.get("surroundings"))),
        bool(_list(atmosphere.get("sensory"))),
        bool(_text(atmosphere.get("upkeep"))),
    )
    atmosphere_axis_coverage = sum(1 for value in atmosphere_axes if value) / 5.0

    tag_fields_filled = sum(
        1
        for value in (
            bool(_text(tags.get("structure"))),
            bool(_text(tags.get("specific_function"))),
            bool(_text(tags.get("named_feature"))),
            bool(_text(tags.get("condition"))),
            bool(_list(tags.get("custom"))),
            *atmosphere_axes,
        )
        if value
    )

    return {
        "atmosphere_axis_coverage": atmosphere_axis_coverage,
        "tag_density": min(1.0, tag_fields_filled / 8.0),
        "generated_desc_coverage": 1.0 if _text(room.get("desc")) else 0.0,
        "stateful_desc_coverage": 1.0 if bool(_mapping(room.get("stateful_descs"))) else 0.0,
    }


def _room_engagement_flags(room: dict, room_npcs: list[dict], room_items: list[dict]) -> dict[str, bool]:
    tags = _mapping(room.get("tags"))
    terrain = _mapping(room.get("terrain"))
    specific_function = _text(tags.get("specific_function")).lower()
    healing_terrain_values = _healing_secondary_terrain_values()
    return {
        "npcs": bool(room_npcs),
        "items": bool(room_items),
        "details": bool(_mapping(room.get("details"))),
        "ambient": bool(_list(_mapping(room.get("ambient")).get("messages"))),
        "stateful": bool(_mapping(room.get("stateful_descs"))),
        "shops": "shop" in specific_function if specific_function else False,
        "hostile": any("aggressive" in {_text(flag).lower() for flag in _list(npc.get("flags"))} for npc in room_npcs),
        "resources": bool(_text(terrain.get("primary"))),
        "healing": _text(terrain.get("secondary")) in healing_terrain_values,
        "quests": bool(_list(room.get("quest_hooks"))),
    }


def _room_completeness_flags(room: dict, valid_room_ids: set[str], room_npcs: list[dict]) -> dict[str, bool]:
    tags = _mapping(room.get("tags"))
    exits = _mapping(room.get("exits"))
    terrain = _mapping(room.get("terrain"))
    exit_targets = [
        _text(_mapping(spec).get("target"))
        for spec in exits.values()
        if isinstance(spec, dict)
    ]
    return {
        "name": bool(_text(room.get("name"))),
        "environment": bool(_text(room.get("environment"))),
        "terrain": bool(_text(terrain.get("primary"))),
        "description": bool(_text(room.get("desc"))),
        "identity_tags": bool(_text(tags.get("structure")) or _text(tags.get("specific_function"))),
        "orphan_exits": all(target in valid_room_ids for target in exit_targets),
        "npc_declarations": all(bool(_text(npc.get("typeclass"))) for npc in room_npcs),
    }


def _room_biggest_gap(completeness_flags: dict[str, bool], depth_metrics: dict[str, float], engagement_flags: dict[str, bool]) -> str:
    lookup = {
        "environment": completeness_flags.get("environment", False),
        "name": completeness_flags.get("name", False),
        "description": completeness_flags.get("description", False),
        "terrain": completeness_flags.get("terrain", False),
        "orphan_exits": completeness_flags.get("orphan_exits", False),
        "identity_tags": completeness_flags.get("identity_tags", False),
        "atmosphere": depth_metrics.get("atmosphere_axis_coverage", 0.0) > 0.0,
        "engagement": any(engagement_flags.values()),
    }
    for key, label in ROOM_GAP_PRIORITY:
        if not lookup.get(key, False):
            return label
    return "needs polish"


def _count_breakdown(satisfied: float, total: float) -> CountBreakdown:
    return {"satisfied": satisfied, "total": total}


def score_zone(zone: dict) -> ZoneScore:
    zone = dict(zone or {})
    rooms = [dict(room) for room in _list(zone.get("rooms")) if isinstance(room, dict)]
    room_count = len(rooms)
    room_ids = {_text(room.get("id")) for room in rooms if _text(room.get("id"))}
    room_npcs_by_room, room_items_by_room = _room_population_indexes(zone)

    generation_context = _mapping(zone.get("generation_context"))
    zone_culture = _list(generation_context.get("culture"))
    zone_mood = _list(generation_context.get("mood"))
    zone_voice = _text(generation_context.get("voice") or generation_context.get("voice_notes"))

    zone_fields_breakdown = {
        "zone_fields": _count_breakdown(
            sum(
                1
                for value in (
                    bool(_text(generation_context.get("setting_type"))),
                    bool(_text(generation_context.get("era_feel"))),
                    bool(_text(generation_context.get("climate"))),
                    bool(zone_mood),
                    bool(zone_culture),
                )
                if value
            ),
            5,
        ),
        "voice_notes_bonus": _count_breakdown(1 if zone_voice else 0, 1),
    }

    room_name_satisfied = 0
    room_environment_satisfied = 0
    room_terrain_satisfied = 0
    room_description_satisfied = 0
    room_identity_tag_satisfied = 0
    room_exit_validity_satisfied = 0
    npc_declaration_satisfied = 0
    npc_declaration_total = 0

    depth_sum = {
        "atmosphere_axis_coverage": 0.0,
        "tag_density": 0.0,
        "generated_desc_coverage": 0.0,
        "stateful_desc_coverage": 0.0,
    }

    engagement_counts = {
        "npcs": 0,
        "items": 0,
        "details": 0,
        "ambient": 0,
        "stateful": 0,
        "shops": 0,
        "hostile": 0,
        "resources": 0,
        "healing": 0,
        "quests": 0,
        "any": 0,
    }

    room_scores: list[RoomScore] = []

    for room in rooms:
        room_id = _text(room.get("id"))
        room_npcs = room_npcs_by_room.get(room_id, [])
        room_items = room_items_by_room.get(room_id, [])
        completeness_flags = _room_completeness_flags(room, room_ids, room_npcs)
        depth_metrics = _room_depth_metrics(room)
        engagement_flags = _room_engagement_flags(room, room_npcs, room_items)

        room_name_satisfied += 1 if completeness_flags["name"] else 0
        room_environment_satisfied += 1 if completeness_flags["environment"] else 0
        room_terrain_satisfied += 1 if completeness_flags["terrain"] else 0
        room_description_satisfied += 1 if completeness_flags["description"] else 0
        room_identity_tag_satisfied += 1 if completeness_flags["identity_tags"] else 0
        room_exit_validity_satisfied += 1 if completeness_flags["orphan_exits"] else 0

        npc_declaration_total += len(room_npcs)
        npc_declaration_satisfied += sum(1 for npc in room_npcs if _text(npc.get("typeclass")))

        for metric, value in depth_metrics.items():
            depth_sum[metric] += value

        any_engagement = False
        for key, value in engagement_flags.items():
            if value:
                engagement_counts[key] += 1
                any_engagement = True
        if any_engagement:
            engagement_counts["any"] += 1

        room_completeness_weighted_total = (
            COMPLETENESS_WEIGHTS["room_name"]
            + COMPLETENESS_WEIGHTS["room_environment"]
            + COMPLETENESS_WEIGHTS["room_terrain_primary"]
            + COMPLETENESS_WEIGHTS["room_description"]
            + COMPLETENESS_WEIGHTS["room_identity_tags"]
            + COMPLETENESS_WEIGHTS["exit_validity"]
        )
        room_completeness_weighted_satisfied = (
            COMPLETENESS_WEIGHTS["room_name"] * int(completeness_flags["name"])
            + COMPLETENESS_WEIGHTS["room_environment"] * int(completeness_flags["environment"])
            + COMPLETENESS_WEIGHTS["room_terrain_primary"] * int(completeness_flags["terrain"])
            + COMPLETENESS_WEIGHTS["room_description"] * int(completeness_flags["description"])
            + COMPLETENESS_WEIGHTS["room_identity_tags"] * int(completeness_flags["identity_tags"])
            + COMPLETENESS_WEIGHTS["exit_validity"] * int(completeness_flags["orphan_exits"])
        )
        if room_npcs:
            room_completeness_weighted_total += COMPLETENESS_WEIGHTS["npc_declaration"]
            room_completeness_weighted_satisfied += COMPLETENESS_WEIGHTS["npc_declaration"] * int(completeness_flags["npc_declarations"])

        room_completeness_score = _score_percent(_ratio(room_completeness_weighted_satisfied, room_completeness_weighted_total))
        room_depth_score = _score_percent(sum(depth_metrics.values()) / 4.0)
        room_engagement_score = _score_percent(sum(1 for value in engagement_flags.values() if value) / 10.0)
        room_composite = round(
            WEIGHTS["completeness"] * room_completeness_score
            + WEIGHTS["depth"] * room_depth_score
            + WEIGHTS["engagement"] * room_engagement_score
        )

        room_scores.append(
            {
                "room_id": room_id,
                "name": _text(room.get("name")) or room_id,
                "composite": room_composite,
                "tier": _tier_for_score(room_composite),
                "biggest_gap": _room_biggest_gap(completeness_flags, depth_metrics, engagement_flags),
            }
        )

    zone_weighted_total = (
        COMPLETENESS_WEIGHTS["zone_setting_type"]
        + COMPLETENESS_WEIGHTS["zone_era_feel"]
        + COMPLETENESS_WEIGHTS["zone_climate"]
        + COMPLETENESS_WEIGHTS["zone_mood"]
        + COMPLETENESS_WEIGHTS["zone_culture"]
        + COMPLETENESS_WEIGHTS["zone_voice"]
    )
    zone_weighted_satisfied = (
        COMPLETENESS_WEIGHTS["zone_setting_type"] * int(bool(_text(generation_context.get("setting_type"))))
        + COMPLETENESS_WEIGHTS["zone_era_feel"] * int(bool(_text(generation_context.get("era_feel"))))
        + COMPLETENESS_WEIGHTS["zone_climate"] * int(bool(_text(generation_context.get("climate"))))
        + COMPLETENESS_WEIGHTS["zone_mood"] * int(bool(zone_mood))
        + COMPLETENESS_WEIGHTS["zone_culture"] * int(bool(zone_culture))
        + COMPLETENESS_WEIGHTS["zone_voice"] * int(bool(zone_voice))
    )
    room_weighted_total = room_count * (
        COMPLETENESS_WEIGHTS["room_name"]
        + COMPLETENESS_WEIGHTS["room_environment"]
        + COMPLETENESS_WEIGHTS["room_terrain_primary"]
        + COMPLETENESS_WEIGHTS["room_description"]
        + COMPLETENESS_WEIGHTS["room_identity_tags"]
        + COMPLETENESS_WEIGHTS["exit_validity"]
    ) + (npc_declaration_total * COMPLETENESS_WEIGHTS["npc_declaration"])
    room_weighted_satisfied = (
        room_name_satisfied * COMPLETENESS_WEIGHTS["room_name"]
        + room_environment_satisfied * COMPLETENESS_WEIGHTS["room_environment"]
        + room_terrain_satisfied * COMPLETENESS_WEIGHTS["room_terrain_primary"]
        + room_description_satisfied * COMPLETENESS_WEIGHTS["room_description"]
        + room_identity_tag_satisfied * COMPLETENESS_WEIGHTS["room_identity_tags"]
        + room_exit_validity_satisfied * COMPLETENESS_WEIGHTS["exit_validity"]
        + npc_declaration_satisfied * COMPLETENESS_WEIGHTS["npc_declaration"]
    )
    completeness_score = _score_percent(_ratio(zone_weighted_satisfied + room_weighted_satisfied, zone_weighted_total + room_weighted_total))

    room_divisor = room_count or 1
    depth_breakdown = {
        "atmosphere_avg": round(depth_sum["atmosphere_axis_coverage"] / room_divisor, 4),
        "tag_density_avg": round(depth_sum["tag_density"] / room_divisor, 4),
        "generated_pct": round(depth_sum["generated_desc_coverage"] / room_divisor, 4),
        "stateful_pct": round(depth_sum["stateful_desc_coverage"] / room_divisor, 4),
    }
    depth_score = _score_percent(sum(depth_breakdown.values()) / 4.0)

    coverage = _ratio(engagement_counts["any"], room_count)
    target = engagement_target(room_count or 0)
    coverage_vs_target = 0.0 if target <= 0 else coverage / target
    engagement_breakdown = {
        "npcs_pct": round(_ratio(engagement_counts["npcs"], room_count), 4),
        "items_pct": round(_ratio(engagement_counts["items"], room_count), 4),
        "details_pct": round(_ratio(engagement_counts["details"], room_count), 4),
        "ambient_pct": round(_ratio(engagement_counts["ambient"], room_count), 4),
        "stateful_pct": round(_ratio(engagement_counts["stateful"], room_count), 4),
        "shops_pct": round(_ratio(engagement_counts["shops"], room_count), 4),
        "hostile_pct": round(_ratio(engagement_counts["hostile"], room_count), 4),
        "resources_pct": round(_ratio(engagement_counts["resources"], room_count), 4),
        "healing_pct": round(_ratio(engagement_counts["healing"], room_count), 4),
        "quests_pct": round(_ratio(engagement_counts["quests"], room_count), 4),
        "any_engagement_pct": round(coverage, 4),
        "target": round(target, 4),
        "coverage_vs_target": round(coverage_vs_target, 4),
    }
    engagement_score = max(0, min(100, round(min(1.0, coverage_vs_target) * 100)))

    composite = round(
        WEIGHTS["completeness"] * completeness_score
        + WEIGHTS["depth"] * depth_score
        + WEIGHTS["engagement"] * engagement_score
    )

    room_scores.sort(key=lambda entry: (int(entry["composite"]), str(entry["name"]).lower(), str(entry["room_id"]).lower()))
    attention_count = min(10, max(5, room_count // 20 if room_count else 5))

    return {
        "composite": composite,
        "tier": _tier_for_score(composite),
        "completeness": {
            "score": completeness_score,
            "breakdown": {
                **zone_fields_breakdown,
                "room_names": _count_breakdown(room_name_satisfied, room_count),
                "room_environments": _count_breakdown(room_environment_satisfied, room_count),
                "room_terrain_primary": _count_breakdown(room_terrain_satisfied, room_count),
                "room_descriptions": _count_breakdown(room_description_satisfied, room_count),
                "room_identity_tags": _count_breakdown(room_identity_tag_satisfied, room_count),
                "exit_validity": _count_breakdown(room_exit_validity_satisfied, room_count),
                "npc_declarations": _count_breakdown(npc_declaration_satisfied, npc_declaration_total),
            },
        },
        "depth": {
            "score": depth_score,
            "breakdown": depth_breakdown,
        },
        "engagement": {
            "score": engagement_score,
            "breakdown": engagement_breakdown,
        },
        "rooms_needing_attention": room_scores[:attention_count],
        "room_scores": room_scores,
        "room_count": room_count,
        "computed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "zone_id": _text(zone.get("zone_id")),
    }