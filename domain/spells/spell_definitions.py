# RULE:
# This file contains DATA ONLY.
# No logic, no calculations, no service calls.

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Spell:
    id: str
    name: str
    abbr: str
    mana_type: str
    spell_type: str
    cast_style: str
    allowed_professions: list[str]
    min_circle: int
    min_skill: dict[str, int]
    safe_mana: int
    base_difficulty: int
    scaling: str
    spellbook: str
    acquisition_methods: list[str]
    slot_cost: int = 0
    apprentice_until_circle: int | None = None
    mana_min: int = 1
    mana_max: int = 0
    target_type: str = "self"
    min_prep_time: int = 10
    expiry_window: int = 300
    canon_status: str = "prototype"
    flags: list[str] = field(default_factory=list)
    effect_profile: dict[str, object] = field(default_factory=dict)


SPELL_REGISTRY: dict[str, Spell] = {}

SPELLCASTING_PROFESSIONS = [
    "bard",
    "cleric",
    "empath",
    "moon_mage",
    "necromancer",
    "paladin",
    "ranger",
    "trader",
    "warrior_mage",
]

SPELL_REGISTRY["empath_heal"] = Spell(
    id="empath_heal",
    name="Heal",
    abbr="hl",
    mana_type="life",
    spell_type="healing",
    cast_style="standard",
    allowed_professions=["empath"],
    min_circle=1,
    min_skill={"primary_magic": 10},
    safe_mana=10,
    base_difficulty=20,
    scaling="linear",
    spellbook="Healing",
    acquisition_methods=["npc", "player"],
)

SPELL_REGISTRY["cleric_minor_heal"] = Spell(
    id="cleric_minor_heal",
    name="Minor Heal",
    abbr="mh",
    mana_type="holy",
    spell_type="healing",
    cast_style="standard",
    allowed_professions=["cleric"],
    min_circle=1,
    min_skill={"primary_magic": 10},
    safe_mana=10,
    base_difficulty=20,
    scaling="linear",
    spellbook="Spirit Manipulation",
    acquisition_methods=["npc", "player", "book"],
)

SPELL_REGISTRY["bolster"] = Spell(
    id="bolster",
    name="Bolster",
    abbr="bol",
    mana_type="elemental",
    spell_type="augmentation",
    cast_style="standard",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=1,
    min_skill={"primary_magic": 10},
    safe_mana=10,
    base_difficulty=18,
    scaling="linear",
    spellbook="Fundamentals",
    acquisition_methods=["npc", "player", "book"],
    effect_profile={
        "contest_modifiers": {
            "magic_attack": 1.0,
            "magic_defense": 1.0,
        },
    },
)

SPELL_REGISTRY["minor_barrier"] = Spell(
    id="minor_barrier",
    name="Minor Barrier",
    abbr="mb",
    mana_type="holy",
    spell_type="warding",
    cast_style="standard",
    allowed_professions=["cleric"],
    min_circle=3,
    min_skill={"primary_magic": 20},
    safe_mana=12,
    base_difficulty=25,
    scaling="linear",
    spellbook="Holy Defense",
    acquisition_methods=["npc", "player", "book"],
)

SPELL_REGISTRY["shielding"] = Spell(
    id="shielding",
    name="Shielding",
    abbr="sh",
    mana_type="holy",
    spell_type="warding",
    cast_style="standard",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=1,
    min_skill={"primary_magic": 10},
    safe_mana=10,
    base_difficulty=18,
    scaling="linear",
    spellbook="Fundamentals",
    acquisition_methods=["npc", "player", "book"],
)

SPELL_REGISTRY["flare"] = Spell(
    id="flare",
    name="Flare",
    abbr="fl",
    mana_type="elemental",
    spell_type="targeted_magic",
    cast_style="standard",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=3,
    min_skill={"primary_magic": 20},
    safe_mana=12,
    base_difficulty=24,
    scaling="linear",
    spellbook="Elemental Targeting",
    acquisition_methods=["npc", "player"],
)

SPELL_REGISTRY["arc_burst"] = Spell(
    id="arc_burst",
    name="Arc Burst",
    abbr="ab",
    mana_type="elemental",
    spell_type="aoe",
    cast_style="room",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=5,
    min_skill={"primary_magic": 40},
    safe_mana=16,
    base_difficulty=32,
    scaling="linear",
    spellbook="Elemental Targeting",
    acquisition_methods=["npc", "player", "book"],
    target_type="room",
    effect_profile={
        "max_targets": 5,
        "aoe_scale": "sqrt_split",
    },
)

SPELL_REGISTRY["radiant_burst"] = Spell(
    id="radiant_burst",
    name="Radiant Burst",
    abbr="rb",
    mana_type="holy",
    spell_type="aoe",
    cast_style="room",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=4,
    min_skill={"primary_magic": 30},
    safe_mana=14,
    base_difficulty=30,
    scaling="linear",
    spellbook="Fundamentals",
    acquisition_methods=["npc", "player", "book"],
    target_type="room",
    effect_profile={
        "max_targets": 5,
        "aoe_scale": "sqrt_split",
    },
)

SPELL_REGISTRY["daze"] = Spell(
    id="daze",
    name="Daze",
    abbr="dz",
    mana_type="lunar",
    spell_type="debilitation",
    cast_style="targeted",
    allowed_professions=["moon_mage"],
    min_circle=4,
    min_skill={"primary_magic": 25},
    safe_mana=14,
    base_difficulty=28,
    scaling="linear",
    spellbook="Psychic Projection",
    acquisition_methods=["npc", "player", "book"],
    effect_profile={
        "effect_type": "daze",
        "base_strength": 1,
        "strength_scale": 0.08,
        "base_duration": 4,
        "duration_scale": 0.5,
        "contest_modifiers": {
            "accuracy": 1.0,
            "evasion": 1.0,
            "magic_attack": 1.0,
            "magic_defense": 1.0,
        },
    },
)

SPELL_REGISTRY["hinder"] = Spell(
    id="hinder",
    name="Hinder",
    abbr="hin",
    mana_type="lunar",
    spell_type="debilitation",
    cast_style="targeted",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=3,
    min_skill={"primary_magic": 20},
    safe_mana=12,
    base_difficulty=24,
    scaling="linear",
    spellbook="Fundamentals",
    acquisition_methods=["npc", "player", "book"],
    effect_profile={
        "effect_type": "hinder",
        "base_strength": 1,
        "strength_scale": 0.08,
        "base_duration": 4,
        "duration_scale": 0.6,
        "contest_modifiers": {
            "accuracy": 1.0,
            "magic_attack": 1.0,
        },
    },
)

SPELL_REGISTRY["slow"] = Spell(
    id="slow",
    name="Slow",
    abbr="sl",
    mana_type="holy",
    spell_type="debilitation",
    cast_style="targeted",
    allowed_professions=["cleric"],
    min_circle=4,
    min_skill={"primary_magic": 25},
    safe_mana=14,
    base_difficulty=28,
    scaling="linear",
    spellbook="Spirit Manipulation",
    acquisition_methods=["npc", "player", "book"],
    effect_profile={
        "effect_type": "slow",
        "base_strength": 1,
        "strength_scale": 0.06,
        "base_duration": 5,
        "duration_scale": 0.75,
        "contest_modifiers": {
            "evasion": 1.0,
            "magic_defense": 1.0,
        },
    },
)

SPELL_REGISTRY["regenerate"] = Spell(
    id="regenerate",
    name="Regenerate",
    abbr="reg",
    mana_type="life",
    spell_type="cyclic",
    cast_style="self",
    allowed_professions=["empath"],
    min_circle=5,
    min_skill={"primary_magic": 35},
    safe_mana=12,
    base_difficulty=30,
    scaling="linear",
    spellbook="Healing",
    acquisition_methods=["npc", "player", "book"],
    effect_profile={
        "target_mode": "self",
        "tick_effect": "healing",
        "tick_scale": 0.18,
        "mana_per_tick_scale": 0.15,
        "interrupt_on_debilitation": True,
    },
)

SPELL_REGISTRY["wither"] = Spell(
    id="wither",
    name="Wither",
    abbr="wth",
    mana_type="lunar",
    spell_type="cyclic",
    cast_style="targeted",
    allowed_professions=["moon_mage"],
    min_circle=5,
    min_skill={"primary_magic": 40},
    safe_mana=14,
    base_difficulty=34,
    scaling="linear",
    spellbook="Psychic Projection",
    acquisition_methods=["npc", "player", "book"],
    effect_profile={
        "target_mode": "single",
        "tick_effect": "damage_over_time",
        "tick_scale": 0.14,
        "mana_per_tick_scale": 0.16,
        "contest_required": True,
        "contest_primary_skill": "debilitation",
        "contest_defense_skill": "warding",
        "contest_defense_stat": "discipline",
        "include_magic_resistance": True,
    },
)

SPELL_REGISTRY["storm_field"] = Spell(
    id="storm_field",
    name="Storm Field",
    abbr="sf",
    mana_type="elemental",
    spell_type="cyclic",
    cast_style="room",
    allowed_professions=["warrior_mage"],
    min_circle=5,
    min_skill={"primary_magic": 40},
    safe_mana=16,
    base_difficulty=36,
    scaling="linear",
    spellbook="Elemental Targeting",
    acquisition_methods=["npc", "player", "book"],
    target_type="room",
    effect_profile={
        "target_mode": "room",
        "tick_effect": "aoe_damage_over_time",
        "tick_scale": 0.14,
        "mana_per_tick_scale": 0.18,
        "max_targets": 5,
    },
)

SPELL_REGISTRY["shared_guard"] = Spell(
    id="shared_guard",
    name="Shared Guard",
    abbr="sg",
    mana_type="holy",
    spell_type="warding",
    cast_style="standard",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=3,
    min_skill={"primary_magic": 25},
    safe_mana=14,
    base_difficulty=26,
    scaling="linear",
    spellbook="Fundamentals",
    acquisition_methods=["npc", "player", "book"],
    target_type="group",
)

SPELL_REGISTRY["glimmer"] = Spell(
    id="glimmer",
    name="Glimmer",
    abbr="gli",
    mana_type="elemental",
    spell_type="utility",
    cast_style="standard",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=1,
    min_skill={"primary_magic": 10},
    safe_mana=10,
    base_difficulty=16,
    scaling="linear",
    spellbook="Fundamentals",
    acquisition_methods=["npc", "player", "book"],
    effect_profile={
        "effect_type": "light",
        "base_duration": 20,
        "duration_scale": 1.0,
    },
)

SPELL_REGISTRY["cleanse"] = Spell(
    id="cleanse",
    name="Cleanse",
    abbr="cln",
    mana_type="holy",
    spell_type="utility",
    cast_style="standard",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=3,
    min_skill={"primary_magic": 20},
    safe_mana=12,
    base_difficulty=22,
    scaling="linear",
    spellbook="Fundamentals",
    acquisition_methods=["npc", "player", "book"],
    effect_profile={
        "effect_type": "cleanse",
    },
)

SPELL_REGISTRY["burden"] = Spell(
    id="burden",
    name="Burden",
    abbr="bur",
    mana_type="lunar",
    spell_type="debilitation",
    cast_style="targeted",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=1,
    min_skill={"primary_magic": 10},
    safe_mana=33,
    mana_min=1,
    mana_max=33,
    base_difficulty=20,
    scaling="linear",
    spellbook="Analogous Patterns",
    acquisition_methods=["scroll", "book"],
    slot_cost=1,
    apprentice_until_circle=10,
    target_type="single",
    min_prep_time=3,
    expiry_window=180,
    canon_status="canonical",
    effect_profile={
        "effect_type": "burden",
        "base_strength": 2,
        "strength_scale": 0.08,
        "base_duration": 600,
        "duration_scale": 0.0,
        "contest_modifiers": {},
        "stat_debuffs": {"strength": -2},
        "encumbrance_modifier": 5,
        "stacking": "non_stacking",
    },
)

SPELL_REGISTRY["gauge_flow"] = Spell(
    id="gauge_flow",
    name="Gauge Flow",
    abbr="gf",
    mana_type="lunar",
    spell_type="utility",
    cast_style="standard",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=1,
    min_skill={"primary_magic": 10},
    safe_mana=100,
    mana_min=5,
    mana_max=100,
    base_difficulty=18,
    scaling="linear",
    spellbook="Analogous Patterns",
    acquisition_methods=["scroll", "book"],
    slot_cost=2,
    target_type="self",
    min_prep_time=8,
    expiry_window=300,
    canon_status="canonical",
    effect_profile={
        "effect_type": "gauge_flow",
        "base_duration": 1800,
        "duration_scale": 6.0,
        "utility_behavior": "gauge_flow",
        "capability_flag": "gauge_flow_active",
        "potency_scaling": "research_time_reduction",
    },
)

SPELL_REGISTRY["strange_arrow"] = Spell(
    id="strange_arrow",
    name="Strange Arrow",
    abbr="sa",
    mana_type="lunar",
    spell_type="targeted_magic",
    cast_style="targeted",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=1,
    min_skill={"primary_magic": 10},
    safe_mana=50,
    mana_min=1,
    mana_max=50,
    base_difficulty=20,
    scaling="linear",
    spellbook="Analogous Patterns",
    acquisition_methods=["scroll", "book"],
    slot_cost=1,
    apprentice_until_circle=10,
    target_type="single",
    min_prep_time=3,
    expiry_window=120,
    canon_status="canonical",
    effect_profile={
        "damage_components": [["puncture", 8], ["electrical", 6]],
        "mana_scaling": "linear",
        "roundtime_seconds": 1,
    },
)

SPELL_REGISTRY["manifest_force"] = Spell(
    id="manifest_force",
    name="Manifest Force",
    abbr="maf",
    mana_type="analogous_patterns",
    spell_type="warding",
    cast_style="standard",
    allowed_professions=list(SPELLCASTING_PROFESSIONS),
    min_circle=1,
    min_skill={"primary_magic": 0},
    safe_mana=100,
    mana_min=1,
    mana_max=100,
    base_difficulty=18,
    scaling="linear",
    spellbook="Analogous Patterns",
    acquisition_methods=["scroll"],
    slot_cost=1,
    apprentice_until_circle=10,
    target_type="self",
    min_prep_time=1,
    expiry_window=600,
    canon_status="canonical",
    effect_profile={
        "absorbs_physical": True,
        "min_capacity": 30,
        "capacity_per_mana": 0.5,
        "base_duration": 600,
        "max_duration": 2400,
        "refresh_behavior": "replace",
        "ward_slot_cost": 1,
    },
)


def get_spell(spell_id: str) -> Spell | None:
    return SPELL_REGISTRY.get(spell_id)