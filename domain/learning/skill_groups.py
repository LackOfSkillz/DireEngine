from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillPulseGroup:
    index: int
    name: str
    offset_seconds: int
    skill_ids: tuple[str, ...]
    description: str


RUNTIME_SKILL_ALIASES = {
    "bow": "attack",
    "chain": "chain_armor",
    "chain_mail": "chain_armor",
    "crossbow": "attack",
    "defending": "combat",
    "heavy_edge": "heavy_edge",
    "heavy_thrown": "attack",
    "large_blunt": "blunt",
    "large_edged": "heavy_edge",
    "light_edge": "light_edge",
    "light_armor_skill": "light_armor",
    "light_thrown": "attack",
    "lockpicking": "locksmithing",
    "melee_mastery": "attack",
    "missile_mastery": "attack",
    "moe": "multiple_engaged_opponent",
    "multiple_engaged_opponent": "multiple_engaged_opponent",
    "offhand_weapon": "attack",
    "parry": "parry_ability",
    "parry_ability": "parry_ability",
    "plate": "plate_armor",
    "polearm": "polearm",
    "polearms": "polearm",
    "primary_magic": "attunement",
    "shield": "shield_usage",
    "shield_usage": "shield_usage",
    "slings": "attack",
    "small_blunt": "blunt",
    "small_edged": "light_edge",
    "sorcery": "arcana",
    "staves": "polearm",
    "twohanded_blunt": "blunt",
    "twohanded_edged": "heavy_edge",
}

CANONICAL_PULSE_GROUPS = (
    SkillPulseGroup(
        index=0,
        name="Defense and Armor",
        offset_seconds=0,
        skill_ids=("shield_usage", "light_armor", "chain_armor", "brigandine", "plate_armor", "combat", "multiple_engaged_opponent"),
        description="Armor handling, shield use, and broad defensive combat footing.",
    ),
    SkillPulseGroup(
        index=1,
        name="Edged Weapons",
        offset_seconds=20,
        skill_ids=("parry_ability", "light_edge", "heavy_edge"),
        description="Edged weapon training and direct weapon parries.",
    ),
    SkillPulseGroup(
        index=2,
        name="Impact Weapons",
        offset_seconds=40,
        skill_ids=("blunt", "attack"),
        description="General offensive drills and blunt weapon practice.",
    ),
    SkillPulseGroup(
        index=3,
        name="Reach and Mobility",
        offset_seconds=60,
        skill_ids=("polearm", "brawling", "disengage"),
        description="Reach weapons, hand-to-hand fighting, and movement under pressure.",
    ),
    SkillPulseGroup(
        index=4,
        name="Core Magic",
        offset_seconds=80,
        skill_ids=("attunement", "arcana", "targeted_magic", "augmentation"),
        description="Core spell preparation, magical awareness, and offensive/support casting.",
    ),
    SkillPulseGroup(
        index=5,
        name="Applied Magic and Awareness",
        offset_seconds=100,
        skill_ids=("debilitation", "utility", "warding", "empathy", "evasion", "athletics", "perception"),
        description="Applied magical disciplines plus broad survival awareness.",
    ),
    SkillPulseGroup(
        index=6,
        name="Fieldcraft",
        offset_seconds=120,
        skill_ids=("stealth", "locksmithing", "thievery", "first_aid", "outdoorsmanship", "skinning"),
        description="Stealth, field support, and practical survival work.",
    ),
    SkillPulseGroup(
        index=7,
        name="Practical Lore",
        offset_seconds=140,
        skill_ids=("appraisal", "scholarship", "mechanical_lore"),
        description="Practical and scholarly lore study.",
    ),
    SkillPulseGroup(
        index=8,
        name="Shared Specialties",
        offset_seconds=160,
        skill_ids=("tactics", "trading"),
        description="Shared specialty skills awaiting deeper canon partitioning.",
    ),
    SkillPulseGroup(
        index=9,
        name="Guild-Specific",
        offset_seconds=180,
        skill_ids=(),
        description="Reserved for profession dispatches to populate guild-specific identities.",
    ),
)

_GROUP_MAP = {group.offset_seconds: group for group in CANONICAL_PULSE_GROUPS}
_SKILL_TO_GROUP = {
    skill_id: group
    for group in CANONICAL_PULSE_GROUPS
    for skill_id in group.skill_ids
}


def _normalize_skill_name(skill_name: str) -> str:
    normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    return RUNTIME_SKILL_ALIASES.get(normalized, normalized)


def get_skill_group_map() -> dict[int, SkillPulseGroup]:
    return dict(_GROUP_MAP)


def get_skill_group_for_skill(skill_name: str) -> SkillPulseGroup | None:
    return _SKILL_TO_GROUP.get(_normalize_skill_name(skill_name))