"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

import copy
from collections.abc import Mapping
import logging
import math
import re
import random
import time

from evennia.objects.objects import DefaultCharacter
from evennia.utils import delay
from evennia.utils.create import create_object
from evennia.utils.search import search_object, search_tag

from typeclasses.abilities import get_ability
from typeclasses.box import Box
from typeclasses.corpse import get_corpse_wounds as get_corpse_wounds_payload, is_near_stable as is_near_stable_corpse_wounds, is_stable as is_stable_corpse_wounds, normalize_corpse_wounds
from typeclasses.items.gem import QUALITY_NAMES, SIZE_NAMES, build_gem_data, create_gem, downgrade_gem_data
from typeclasses.lockpick import Lockpick
from typeclasses.spells import SPELLS, SPELLCASTING_GUILDS
from typeclasses.study_item import StudyItem
from typeclasses.trap_device import TrapDevice
from utils.contests import run_contest
from utils.survival_loot import create_harvest_bundle, create_simple_item
from utils.survival_messaging import msg_room
from world.area_forge.character_api import send_character_update, send_subsystem_update
from world.area_forge.map_api import send_map_update
from world.area_forge.utils.messages import _supports_structured_session
from utils.crime import check_liquidation, decay_warrants, release_from_stocks
from world.professions import (
    DEFAULT_PROFESSION,
    PROFESSION_PROFILES,
    PROFESSION_SKILL_WEIGHTS,
    PROFESSION_TO_GUILD,
    create_subsystem,
    get_profession_display_name,
    get_profession_profile,
    get_profession_rank_label,
    get_profession_social_standing,
    resolve_profession_name,
)
from world.languages import apply_accent, apply_comprehension, get_comprehension_level, get_language_display_name, get_languages_for_race, normalize_language_name
from world.races import (
    BASE_CARRY_WEIGHT,
    DEFAULT_AGE,
    DEFAULT_RACE,
    RACE_STATS,
    apply_race,
    build_race_state,
    get_race_age_descriptor,
    get_race_carry_modifier,
    get_race_debug_payload,
    get_race_description,
    get_race_display_name,
    get_race_learning_modifier,
    get_race_profile,
    get_race_stat_cap,
    get_race_stat_modifier,
    normalize_learning_category,
    resolve_age_bracket,
    resolve_race_name,
    validate_race_application,
)
from world.systems.warrior import (
    EXHAUSTION_GAIN_RATES,
    RECOVERY_RATES,
    WARRIOR_ABILITY_DATA,
    WARRIOR_PASSIVE_DATA,
    ROAR_DATA,
    format_berserk_name,
    format_roar_name,
    format_warrior_ability_name,
    format_warrior_tempo_state,
    get_exhaustion_profile,
    get_berserk_profile,
    get_next_warrior_unlock,
    get_roar_profile,
    get_warrior_abilities_for_circle,
    get_warrior_passives_for_circle,
    get_warrior_tempo_state,
)
from world.systems.ranger import (
    ENVIRONMENT_BOND_DELTAS,
    ENVIRONMENT_NATURE_FOCUS_DELTAS,
    NATURAL_TERRAIN_TYPES,
    NATURE_FOCUS_ACTION_GAINS,
    NATURE_FOCUS_MAX,
    PERCEPTION_BONUSES,
    RANGER_SNIPE_CONFIG,
    STEALTH_BONUSES,
    TERRAIN_SNIPE_RETENTION_BONUSES,
    TERRAIN_STEALTH_BONUSES,
    TERRAIN_TRACKING_BONUSES,
    TRACK_DIFFICULTY_BASE,
    TRACKING_BONUSES,
    get_terrain_label,
    get_wilderness_bond_profile,
)
from world.systems.ranger.companion import (
    get_companion_awareness_bonus,
    get_companion_label,
    get_companion_tracking_bonus,
    is_companion_active,
    normalize_ranger_companion,
)
from world.systems.ranger.beseech import get_beseech_kinds, get_beseech_profile
from world.systems.wounds import WOUND_RULES, apply_poison_tick, describe_wound, get_disease_penalty
from world.systems.interest import (
    clear_direct_interest,
    clear_subject_interest,
    direct_interest,
    sync_direct_interest,
    sync_subject_interest,
)
from world.systems.skills import MINDSTATE_MAX, SkillHandler, TEMPLATE_EXP_SKILLS, award_exp_skill, is_active
from world.systems.circles import (
    get_circle_requirements,
    get_highest_configured_circle,
    is_circle_location_enforced,
    is_valid_empath_circle_location,
)
from world.systems.empath_unlocks import (
    EMPATH_ABILITY_UNLOCKS,
    EMPATH_UNLOCKS,
    format_empath_unlock_name,
    get_empath_unlock,
    get_empath_unlock_rank,
    get_next_empath_unlock,
)

from .objects import ObjectParent


LOGGER = logging.getLogger(__name__)


DEFAULT_STATS = {
    "strength": 10,
    "stamina": 10,
    "agility": 10,
    "reflex": 10,
    "discipline": 10,
    "intelligence": 10,
    "wisdom": 10,
    "charisma": 10,
    "magic_resistance": 10,
}

XP_TAKE = 5
XP_TEND = 3
XP_PERCEIVE = 2
XP_SHIFT = 6

EMPATH_FIELD_XP = {
    "take": ("empathy", XP_TAKE, "empath_take"),
    "tend": ("first_aid", XP_TEND, "empath_tend"),
    "perceive": ("empathy", XP_PERCEIVE, "empath_perceive"),
    "shift": ("empathy", XP_SHIFT, "empath_shift"),
    "study_anatomy": ("scholarship", 4, "study_anatomy"),
}

VALID_GUILDS = tuple(PROFESSION_PROFILES.keys())

RANGER_JOIN_REQUIREMENTS = (
    ("strength", 8, "Strength"),
    ("stamina", 8, "Stamina"),
    ("agility", 8, "Agility"),
    ("reflex", 7, "Reflex"),
    ("intelligence", 7, "Intelligence"),
    ("charisma", 6, "Charisma"),
    ("wisdom", 6, "Wisdom"),
)

LIFE_STATE_ALIVE = "ALIVE"
LIFE_STATE_DEAD = "DEAD"
LIFE_STATE_DEPARTED = "DEPARTED"

DEAD_STATE_ALLOWED_COMMANDS = {
    "consent",
    "death",
    "depart",
    "exp",
    "experience",
    "favor",
    "health",
    "help",
    "hp",
    "l",
    "look",
    "pose",
    "raise",
    "resurrect",
    "corpse",
    "say",
    "score",
    "sta",
    "stats",
    "withdraw",
    "whisper",
    "xp",
}

CLIMB_OUTCOME_MESSAGES = {
    "low": {
        "cost": 5,
        "success": (
            "You catch the rhythm of the climb and pull yourself into the low blind.",
            "The lower route yields to you and you climb up cleanly.",
            "You find the easy holds and move into the blind above.",
        ),
        "cost": 10,
        "partial": (
            "You get partway up, then settle back onto the rope walk without losing ground.",
            "The lower climb wobbles under you and you stop to steady yourself.",
            "You test the route, but do not gain the blind this time.",
        ),
        "cost": 15,
        "failure": (
            "Your footing slips and you drop back onto the rope walk.",
            "The lower climb turns under you and you fall back to the start.",
            "You lose the easy hold and land back on the rope walk.",
        ),
        "cost": 15,
    },
    "mid": {
        "success": (
            "You work through the harder stretch and haul yourself into the middle fort.",
            "The demanding route gives way a hold at a time and you climb higher.",
            "You read the next sequence cleanly and reach the middle fort.",
        ),
        "partial": (
            "The middle climb makes you earn every reach, and you stall short of the fort.",
            "You gain a little height, then cling in place without finishing the climb.",
            "You fight for the next hold, but the route keeps you where you are.",
        ),
        "failure": (
            "The harder section throws you off and you drop back to the low blind.",
            "A demanding hold slips away and you fall back one level.",
            "You overreach on the middle climb and tumble back below.",
        ),
    },
    "high": {
        "success": (
            "You force your way through the hardest stretch and pull onto the high hide.",
            "The upper climb nearly turns you away, but you grind through and crest the perch.",
            "Against the branches and the height, you find a path and reach the high hide.",
        ),
        "partial": (
            "The high route holds you in place, refusing to give you the last reach.",
            "You find a moment of balance, but the high hide stays out of reach.",
            "You gain nothing on the upper climb but a sharper sense of where it beats you.",
        ),
        "failure": (
            "The upper climb wins and sends you back to the middle fort.",
            "You lose the high hold and fall back one level.",
            "The last stretch breaks your rhythm and drops you below.",
        ),
    },
}

CLIMB_LEARNING_FEEDBACK = (
    "You feel your balance improve.",
    "The route starts to make more sense to you.",
    "You begin to read the holds more cleanly.",
)

HIGH_HIDE_REJECTION_MESSAGE = "The climb rejects you immediately-you're not ready for it."
HIGH_HIDE_RARE_SUCCESS_MESSAGE = "You shouldn't have made that climb-but you did."

CLIMB_PRACTICE_STEP = 3
CLIMB_PRACTICE_CAP = 9

RANGER_RESOURCE_PROFILES = {
    "grass": {
        "room_label": "a patch of tall grass",
        "action": "gather grass",
        "key": "grass",
        "desc": "A handful of tall grass gathered for braiding or bundling.",
        "item_type": "raw_resource",
        "value": 1,
        "weight": 0.2,
        "gather_message": "You gather a workable length of tall grass.",
    },
    "stick": {
        "room_label": "a fallen branch",
        "action": "gather stick",
        "key": "stick",
        "desc": "A straight, workable stick cut down to a portable length.",
        "item_type": "raw_resource",
        "value": 1,
        "weight": 0.4,
        "gather_message": "You pick out a usable stick from the branchfall.",
    },
}

RANGER_RESOURCE_RECIPES = {
    "bundle": {
        "input": "stick",
        "output_key": "bundle",
        "output_desc": "A tight field bundle of cut sticks bound for sale or camp work.",
        "output_type": "bundle",
        "value": 3,
        "weight": 0.8,
        "success_message": "You bind the sticks into a saleable bundle.",
    },
    "braid": {
        "input": "grass",
        "output_key": "braided grass",
        "output_desc": "A braid of tough grass woven tight enough to keep its shape.",
        "output_type": "braid",
        "value": 3,
        "weight": 0.2,
        "success_message": "You braid the grass into something a buyer might want.",
    },
}

COPPER = 1
SILVER = 10
GOLD = 100
PLATINUM = 1000

COIN_DENOMINATIONS = (
    ("platinum", PLATINUM),
    ("gold", GOLD),
    ("silver", SILVER),
    ("copper", COPPER),
)

WEIGHT_UNIT = 1.0
COIN_WEIGHT = 0.002
MAX_CONTAINER_WEIGHT_DEPTH = 5

VENDOR_TYPES = ("general", "gem_buyer", "pawn", "fish_buyer")
VENDOR_PAYOUTS = {
    "general": {"default": 0.5, "gems": None},
    "gem_buyer": {"default": None, "gems": 0.9},
    "pawn": {"default": 0.6, "gems": 0.7},
    "fish_buyer": {"default": None, "gems": None},
}

STRICT_BOX_LOCK_DIFFICULTY = 35

SKILLSET_ALIASES = {
    "armor": "armor",
    "combat": "weapons",
    "general": "general",
    "lore": "lore",
    "magic": "magic",
    "survival": "survival",
    "weapon": "weapons",
    "weapons": "weapons",
}

EXP_SKILLSET_TIER_OVERRIDES = {
    "empathy": "primary",
    "first_aid": "secondary",
    "scholarship": "secondary",
}

MINDSTATE_LEVELS = [
    "clear",
    "dabbling",
    "learning",
    "thinking",
    "considering",
    "concentrating",
    "engaged",
    "focused",
    "very focused",
    "engrossed",
    "nearly locked",
    "mind locked",
]

SKILL_REGISTRY = {
    "attack": {"category": "combat", "visibility": "shared", "description": "general offensive combat training", "starter_rank": 0},
    "arcana": {"category": "magic", "visibility": "shared", "description": "ability to use magical devices and tools", "starter_rank": 1},
    "athletics": {"category": "survival", "visibility": "shared", "description": "climbing, swimming, and physical traversal", "starter_rank": 1},
    "backstab": {"category": "survival", "visibility": "guild_locked", "description": "precision attack from stealth", "starter_rank": 0},
    "blunt": {"category": "combat", "visibility": "shared", "description": "fighting with blunt weapons", "starter_rank": 0},
    "brigandine": {"category": "armor", "visibility": "shared", "description": "training in brigandine armor use", "starter_rank": 0},
    "brawling": {"category": "combat", "visibility": "shared", "description": "unarmed fighting", "starter_rank": 0},
    "chain_armor": {"category": "armor", "visibility": "shared", "description": "training in chain armor use", "starter_rank": 0},
    "combat": {"category": "combat", "visibility": "shared", "description": "general combat sense and technique", "starter_rank": 0},
    "debilitation": {"category": "magic", "visibility": "guild_locked", "guilds": SPELLCASTING_GUILDS, "description": "hindering and control magic", "starter_rank": 0},
    "disengage": {"category": "combat", "visibility": "shared", "description": "breaking away from combat pressure", "starter_rank": 0},
    "empathy": {"category": "magic", "visibility": "shared", "description": "transferring and reading wounds through empathy", "starter_rank": 0},
    "attunement": {"category": "magic", "visibility": "shared", "description": "ability to perceive and channel radiance", "starter_rank": 1},
    "evasion": {"category": "survival", "visibility": "shared", "description": "avoiding incoming attacks", "starter_rank": 1},
    "first_aid": {"category": "survival", "visibility": "shared", "description": "stabilizing wounds and suppressing bleeding", "starter_rank": 0},
    "heavy_edge": {"category": "combat", "visibility": "shared", "description": "fighting with heavy edged weapons", "starter_rank": 0},
    "instinct": {"category": "survival", "visibility": "guild_locked", "description": "survival intuition / danger sense placeholder", "starter_rank": 0},
    "light_armor": {"category": "armor", "visibility": "shared", "description": "training in light armor use", "starter_rank": 0},
    "light_edge": {"category": "combat", "visibility": "shared", "description": "fighting with light edged weapons", "starter_rank": 0},
    "locksmithing": {"category": "survival", "visibility": "shared", "description": "picking locks and disarming traps", "starter_rank": 0},
    "mechanical_lore": {"category": "lore", "visibility": "shared", "description": "understanding tools, rigs, and practical systems", "starter_rank": 0},
    "outdoorsmanship": {"category": "survival", "visibility": "shared", "description": "foraging, wilderness interaction, and natural gathering", "starter_rank": 0},
    "perception": {"category": "survival", "visibility": "shared", "description": "noticing hidden threats, traps, and subtle details", "starter_rank": 1},
    "plate_armor": {"category": "armor", "visibility": "shared", "description": "training in plate armor use", "starter_rank": 0},
    "polearm": {"category": "combat", "visibility": "shared", "description": "fighting with polearms", "starter_rank": 0},
    "appraisal": {"category": "lore", "visibility": "shared", "description": "evaluating items, creatures, and value", "starter_rank": 1},
    "scholarship": {"category": "lore", "visibility": "shared", "description": "improves learning and knowledge systems", "starter_rank": 0},
    "tactics": {"category": "lore", "visibility": "shared", "description": "improves combat awareness and positioning", "starter_rank": 0},
    "theurgy": {"category": "magic", "visibility": "guild_locked", "guilds": ("cleric",), "description": "ritual practice, communes, and divine mediation", "starter_rank": 0},
    "targeted_magic": {"category": "magic", "visibility": "guild_locked", "guilds": SPELLCASTING_GUILDS, "description": "direct offensive spellcasting", "starter_rank": 0},
    "trading": {"category": "lore", "visibility": "shared", "description": "improves buying and selling prices", "starter_rank": 1},
    "utility": {"category": "magic", "visibility": "guild_locked", "guilds": SPELLCASTING_GUILDS, "description": "general purpose magical effects", "starter_rank": 0},
    "augmentation": {"category": "magic", "visibility": "guild_locked", "guilds": SPELLCASTING_GUILDS, "description": "beneficial enhancement magic", "starter_rank": 0},
    "warding": {"category": "magic", "visibility": "guild_locked", "guilds": SPELLCASTING_GUILDS, "description": "protective and defensive magic", "starter_rank": 0},
    "skinning": {"category": "survival", "visibility": "shared", "description": "harvesting useful parts from slain creatures", "starter_rank": 0},
    "stealth": {"category": "survival", "visibility": "shared", "description": "hiding, sneaking, and stalking unseen", "starter_rank": 0},
    "thanatology": {"category": "survival", "visibility": "guild_locked", "description": "death/body handling placeholder", "starter_rank": 0},
    "thievery": {"category": "survival", "visibility": "guild_locked", "description": "illicit manipulation / theft placeholder", "starter_rank": 0},
}

STARTER_SKILLS = tuple(
    skill_name
    for skill_name, metadata in SKILL_REGISTRY.items()
    if metadata.get("starter_rank", 0) > 0
)

STARTER_SKILL_BASELINES = {
    skill_name: metadata.get("starter_rank", 0)
    for skill_name, metadata in SKILL_REGISTRY.items()
    if metadata.get("starter_rank", 0) > 0
}

AVAILABLE_SKILL_BASELINES = {
    skill_name: metadata.get("starter_rank", 0)
    for skill_name, metadata in SKILL_REGISTRY.items()
    if metadata.get("visibility") != "guild_locked"
}

SURVIVAL_TRAINING_HOOKS = {
    "athletics": ["climb", "swim", "traversal"],
    "evasion": ["combat defense"],
    "first_aid": ["tend", "bandage"],
    "locksmithing": ["pick", "disarm"],
    "outdoorsmanship": ["forage", "gather"],
    "perception": ["search", "observe", "detect"],
    "skinning": ["skin"],
    "stealth": ["hide", "sneak", "stalk"],
}

STEALTH_PRACTICE_CAPS = {
    "stealth": 15,
}
STEALTH_PRACTICE_BASE_MULTIPLIER = 0.4
STEALTH_PRACTICE_MIN_MULTIPLIER = 0.1
STEALTH_MARGIN_DIVISOR = 100.0
STEALTH_MARGIN_MIN = 0.5
STEALTH_MARGIN_MAX = 1.5
STEALTH_FAILURE_TERRIBLE_MARGIN = -50.0
STEALTH_FAILURE_NEAR_MISS_MARGIN = -10.0
STEALTH_FAILURE_TERRIBLE_MODIFIER = 0.1
STEALTH_FAILURE_MODERATE_MODIFIER = 0.25
STEALTH_FAILURE_NEAR_MISS_MODIFIER = 0.5
STEALTH_FATIGUE_STEP = 0.4
STEALTH_FATIGUE_WINDOW = 90.0
STEALTH_MOVE_ROUNDTIME = 0.5

DEFAULT_INJURIES = {
    "head": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 100, "vital": True},
    "chest": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 120, "vital": True},
    "abdomen": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 110, "vital": True},
    "back": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 110, "vital": True},
    "left_arm": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 80, "vital": False},
    "right_arm": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 80, "vital": False},
    "left_hand": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 60, "vital": False},
    "right_hand": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 60, "vital": False},
    "left_leg": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 90, "vital": False},
    "right_leg": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 90, "vital": False},
}

BODY_PART_ORDER = tuple(DEFAULT_INJURIES.keys())

DEFAULT_WEAPON_PROFILE = {
    "damage": 1,
    "damage_min": 1,
    "damage_max": 3,
    "roundtime": 2.0,
    "balance_cost": 10,
    "fatigue_cost": 5,
    "skill": "brawling",
    "balance": 50,
    "damage_type": "impact",
    "damage_types": {"slice": 0, "impact": 1, "puncture": 0},
    "range_band": "melee",
    "weapon_range_type": None,
}

DEFAULT_EQUIPMENT = {
    "head": None,
    "face": None,
    "neck": None,
    "shoulders": None,
    "torso": None,
    "back": None,
    "arms": None,
    "hands": None,
    "waist": None,
    "legs": None,
    "feet": None,
    "fingers": [],
    "belt_attach": [],
    "back_attach": [],
    "shoulder_attach": [],
}

DEFAULT_EMPATH_WOUNDS = {
    "fatigue": 0,
    "vitality": 0,
    "bleeding": 0,
    "poison": 0,
    "disease": 0,
}

EMPATH_WOUND_LABELS = {
    "fatigue": "Fatigue",
    "vitality": "Vitality",
    "bleeding": "Bleeding",
    "poison": "Poison",
    "disease": "Disease",
}

EMPATH_WOUND_ALIASES = {
    "health": "vitality",
}

EMPATH_SELECTIVE_TAKE_BUCKETS = {
    "arm": ("bleeding", "vitality"),
    "leg": ("bleeding", "vitality"),
    "chest": ("vitality", "bleeding"),
    "head": ("vitality", "bleeding"),
}
EMPATH_PARTIAL_TAKE_BUCKET_PRIORITY = ("bleeding", "poison", "disease")

EMPATH_TRANSFER_CONFIG = {
    "fatigue": {"default": 10},
    "vitality": {
        "default": 20,
        "risk": 0.45,
        "hp_ratio": 0.5,
        "fatigue_ratio": 0.35,
        "shock_ratio": 0.3,
    },
    "bleeding": {"default": 20},
    "poison": {"default": 20},
    "disease": {"default": 20},
}

EMPATH_LINK_TOUCH = "touch"
EMPATH_LINK_DIRECT = "direct"
EMPATH_LINK_STANDARD = EMPATH_LINK_DIRECT
EMPATH_LINK_PERSISTENT = "persistent"
EMPATH_LINK_GROUP = "group"
EMPATH_LINK_TYPES = {
    EMPATH_LINK_TOUCH,
    EMPATH_LINK_DIRECT,
    EMPATH_LINK_PERSISTENT,
    EMPATH_LINK_GROUP,
}
EMPATH_LINK_PRIORITY = {
    EMPATH_LINK_GROUP: 0,
    EMPATH_LINK_TOUCH: 1,
    EMPATH_LINK_DIRECT: 2,
    EMPATH_LINK_PERSISTENT: 3,
}
EMPATH_LINK_DURATIONS = {
    EMPATH_LINK_TOUCH: 30,
    EMPATH_LINK_DIRECT: 120,
    EMPATH_LINK_PERSISTENT: 300,
    EMPATH_LINK_GROUP: 90,
}
EMPATH_LINK_BASE_STRENGTH = {
    EMPATH_LINK_TOUCH: 60,
    EMPATH_LINK_DIRECT: 100,
    EMPATH_LINK_PERSISTENT: 90,
    EMPATH_LINK_GROUP: 45,
}
EMPATH_LINK_BASE_STABILITY = {
    EMPATH_LINK_TOUCH: 80,
    EMPATH_LINK_DIRECT: 100,
    EMPATH_LINK_PERSISTENT: 120,
}
EMPATH_LINK_STABILITY_RULES = {
    EMPATH_LINK_TOUCH: {"small_transfer": 10, "large_transfer": 20, "damage": 15},
    EMPATH_LINK_DIRECT: {"small_transfer": 6, "large_transfer": 15, "damage": 10},
    EMPATH_LINK_PERSISTENT: {"small_transfer": 4, "large_transfer": 12, "damage": 10},
}
EMPATH_UNITY_STABILITY_RULES = {
    "transfer": 15,
    "damage": 10,
    "shock_worsen": 15,
    "redirect": 20,
}
EMPATH_UNITY_SMOOTH_RATIO = 0.15
EMPATH_UNITY_MAX_TARGETS = 3
EMPATH_UNITY_DURATION = 90
EMPATH_UNITY_SHARE_RATIO = 0.4
EMPATH_SHOCK_THRESHOLDS = {
    "clear": 0,
    "strained": 20,
    "dull": 50,
    "disconnected": 80,
}
EMPATH_SYSTEM_CONFIG = {
    "shock_penalties": {
        "major_threshold": 80,
        "medium_threshold": 50,
        "minor_threshold": 20,
        "major_modifier": 0.35,
        "medium_modifier": 0.6,
        "minor_modifier": 0.85,
    },
    "link_strength": {
        "time_bonus_scale": 10.0,
        "max_time_bonus": 25,
        "local_bonus": 5,
        "remote_nonpersistent_penalty": 10,
        "deepen_bonus": 15,
        "deepen_fatigue_cost": 5,
        "decay_penalty_max": 20,
        "stress_decay_scale": 10.0,
        "stress_decay_max": 8,
    },
    "transfer": {
        "min_efficiency": 0.85,
        "max_efficiency": 1.45,
        "strength_scale": 180.0,
    },
    "backlash": {
        "max": 1.1,
        "min": 0.55,
        "strength_scale": 220.0,
    },
    "redirect": {
        "strain_ratio": 0.2,
        "fatigue_ratio": 0.35,
        "risk_base": 0.12,
        "risk_scale": 40.0,
        "fatigue_spike_min": 3,
    },
    "smoothing": {
        "tick_seconds": 12.0,
        "max_per_tick": 2,
        "wounds": ("vitality", "bleeding", "trauma"),
    },
    "overdraw": {
        "wound_threshold": 70,
        "fatigue_threshold": 65,
        "duration": 25.0,
    },
    "center": {
        "fatigue_cost": 10,
        "shock_reduction": 15,
        "roundtime": 2.5,
        "overdraw_clear_shock_threshold": 18,
        "overdraw_clear_fatigue_threshold": 50,
    },
}
EMPATH_GUILD_ZONE_TAGS = {
    "recovery": "empath_zone_recovery",
    "training": "empath_zone_training",
    "triage": "empath_zone_triage",
}
EMPATH_SCAR_RULES = {
    "severity_threshold": 45,
    "trauma_threshold": 70,
    "repeat_threshold": 15,
    "repeat_gate": 25,
    "max_scars": 10,
}
EMPATH_STABILIZE_RULES = {
    "base_duration": 10.0,
    "duration_scale": 0.08,
    "base_strength": 0.35,
    "strength_scale": 0.005,
    "max_strength": 1.0,
}
EMPATH_CHANNEL_RULES = {
    "pulse_interval": 4.0,
    "base_ratio": 0.4,
    "min_amount": 4,
    "fatigue_base": 2,
    "fatigue_escalation": 2,
    "shock_every": 2,
}
EMPATH_TRAINING_UNSET = 0
EMPATH_TRAINING_PATIENT = 1
EMPATH_TRAINING_BASIC = 2
EMPATH_TUTORIAL_LOCKED_ABILITIES = {"link", "unity", "redirect"}
EMPATH_TUTORIAL_WOUNDS = {"vitality", "bleeding"}

FAVOR_SYSTEM_CONFIG = {
    "base_cost": 1000,
    "scaling_factor": 0.18,
    "soft_cap_threshold": 16,
    "soft_cap_bonus_per_favor": 0.05,
    "low_favor_threshold": 2,
    "high_favor_threshold": 16,
    "soul_decay_base": 1.0,
    "soul_decay_modifier": 0.08,
    "soul_strength_base": 20,
    "soul_strength_bonus": 4,
    "resurrection_success_bonus": 0.03,
    "resurrection_cost_reduction": 0.04,
    "resurrection_quality_bonus": 0.025,
    "low_favor_failure_bias": 0.12,
    "death_favor_consumption_base": 1,
    "death_favor_consumption_streak_bonus": 1,
    "death_favor_consumption_streak_cap": 3,
    "route_xp_only": True,
    "depart_restore_hp_ratio": 0.5,
    "resurrection_restore_hp_ratio": 0.75,
    "resurrection_base_attunement_cost": 30,
    "shrine_regen_interval": 300.0,
    "pray_cooldown_seconds": 60.0,
    "favor_decay_seconds": 1800.0,
    "revive_cost": 1,
    "revive_delay_seconds": 5.0,
}

GRAVE_SYSTEM_CONFIG = {
    "expiry_seconds": 30 * 60,
    "base_coin_loss_ratio": 0.10,
    "high_favor_threshold": 3,
    "high_favor_loss_scale": 0.5,
    "moderate_sting_bonus_ratio": 0.02,
    "severe_sting_bonus_ratio": 0.05,
}

DEPART_CONFIRM_WINDOW_SECONDS = 8.0
DEATH_STING_MAX_STACKS = 5
DEATH_STING_DECAY_SECONDS = 600.0
DEATH_STING_HP_CAPS = {
    "light": 0.9,
    "moderate": 0.8,
    "severe": 0.7,
}

CLERIC_CORPSE_RITUAL_ACTIONS = {
    "prepare": {
        "cost": 5,
        "delay": 4.0,
        "start_message": "You begin preparing the body for the rites.",
        "room_message": "{actor} begins preparing {corpse} with measured, ritual care.",
    },
    "stabilize": {
        "cost": 10,
        "delay": 6.0,
        "start_message": "You begin stabilizing the body's fading pattern.",
        "room_message": "{actor} settles into a vigil over {corpse}, steadying the corpse's fading pattern.",
    },
    "restore": {
        "cost": 15,
        "delay": 8.0,
        "start_message": "You begin restoring the body's fragile memories.",
        "room_message": "{actor} traces a restorative rite over {corpse}, coaxing memory back into place.",
    },
    "bind": {
        "cost": 15,
        "delay": 8.0,
        "start_message": "You begin binding the soul securely to the body.",
        "room_message": "{actor} raises a binding rite over {corpse}, drawing the soul into a tighter orbit.",
    },
}

CLERIC_REVIVE_RITUAL_COST = 20

CLERIC_RITUAL_QUALITY_STEPS = {
    "prepare": 1,
    "stabilize": 2,
    "restore": 3,
    "bind": 3,
}

CLERIC_RITUAL_OUTCOME_BANDS = (
    {"minimum": 10, "label": "best", "hp_ratio": 0.6, "recovery_state": "revived_best", "aftereffect": "perfect", "message": "The soul returns cleanly, guided by steady hands."},
    {"minimum": 6, "label": "light", "hp_ratio": 0.4, "recovery_state": "revived_light", "aftereffect": "stable", "message": "The rite settles well enough, and life answers with only a slight shudder."},
    {"minimum": 3, "label": "moderate", "hp_ratio": 0.25, "recovery_state": "revived_moderate", "aftereffect": "fragile", "message": "Life returns unevenly, leaving the body strained and fragile."},
    {"minimum": 0, "label": "severe", "hp_ratio": 0.12, "recovery_state": "revived_severe", "aftereffect": "flawed", "message": "The body lurches back, barely whole."},
)
CLERIC_STAGE_SPECIALIZATIONS = {
    "prepare": "stabilizer",
    "stabilize": "stabilizer",
    "restore": "restorer",
    "bind": "binder",
    "revive": "binder",
}

DEATH_PROTECTION_CONFIG = {
    "max_rank": 3,
    "exp_debt_multiplier": 0.25,
    "sting_severity_scale": 0.5,
    "minimum_depart_mode": "full",
}

RESURRECTION_QUALITY_PROFILES = (
    (85, {"label": "perfect", "hp_ratio": 1.0, "sting_duration_scale": 0.15, "sting_severity_scale": 0.15, "exp_restore_scale": 1.35}),
    (60, {"label": "stable", "hp_ratio": 0.88, "sting_duration_scale": 0.35, "sting_severity_scale": 0.35, "exp_restore_scale": 1.1}),
    (35, {"label": "fragile", "hp_ratio": 0.72, "sting_duration_scale": 0.7, "sting_severity_scale": 0.7, "exp_restore_scale": 0.8}),
    (1, {"label": "flawed", "hp_ratio": 0.6, "sting_duration_scale": 0.9, "sting_severity_scale": 0.9, "exp_restore_scale": 0.6}),
)

CLERIC_DEVOTION_CONFIG = {
    "baseline": 100,
    "max_devotion": 100,
    "shrine_regen_amount": 5,
    "shrine_regen_interval": 60.0,
    "rituals": {
        "prayer": {
            "gain": 5,
            "cooldown": 60.0,
            "message": "You offer a quiet prayer, strengthening your connection.",
        },
        "focus": {
            "gain": 5,
            "cooldown": 60.0,
            "message": "You focus on the Immortals with measured intent, drawing their attention closer.",
        },
        "devotion": {
            "gain": 5,
            "cooldown": 60.0,
            "message": "You commit yourself to a fuller rite, and the divine answer with unmistakable warmth.",
        },
    },
    "communes": {
        "solace": {"cost": 8},
        "ward": {"cost": 14},
        "vigil": {"cost": 12},
    },
    "resurrection": {
        "low_threshold": 20,
        "high_threshold": 70,
    },
}

APPEARANCE_SLOT_ORDER = [
    "head",
    "face",
    "neck",
    "shoulders",
    "torso",
    "back",
    "arms",
    "hands",
    "waist",
    "legs",
    "feet",
    "fingers",
]

ARMOR_SKILLS = {
    "light": "light_armor",
    "light_armor": "light_armor",
    "chain": "chain_armor",
    "chain_armor": "chain_armor",
    "brigandine": "brigandine",
    "plate": "plate_armor",
    "plate_armor": "plate_armor",
}

RANGE_BANDS = ["melee", "near", "far"]
RECENT_TEND_WINDOW = 10
ARMOR_COVERAGE_WEIGHTS = {
    "head": 3,
    "chest": 4,
    "abdomen": 4,
    "back": 4,
    "left_arm": 2,
    "right_arm": 2,
    "left_leg": 2,
    "right_leg": 2,
    "left_hand": 1,
    "right_hand": 1,
}


def _copy_default_injuries():
    injuries = {}
    for part, data in DEFAULT_INJURIES.items():
        copied = data.copy()
        copied["tend"] = dict(data.get("tend", {"strength": 0, "duration": 0}))
        injuries[part] = copied
    return injuries


def _copy_default_weapon_profile():
    profile = DEFAULT_WEAPON_PROFILE.copy()
    profile["damage_types"] = dict(DEFAULT_WEAPON_PROFILE["damage_types"])
    return profile


def normalize_range_band(value, default="melee"):
    normalized = str(value or "").strip().lower()
    legacy_map = {"reach": "near", "missile": "far"}
    normalized = legacy_map.get(normalized, normalized)
    if normalized in RANGE_BANDS:
        return normalized
    return default


def _copy_default_equipment():
    return {
        slot: value.copy() if isinstance(value, list) else value
        for slot, value in DEFAULT_EQUIPMENT.items()
    }


def _copy_default_empath_wounds():
    return dict(DEFAULT_EMPATH_WOUNDS)


def _clear_combat_link(character):
    if not character:
        return

    opponent = getattr(character.db, "target", None)
    character.db.target = None
    character.db.in_combat = False
    character.db.aiming = None

    combat_range = dict(getattr(character.db, "combat_range", {}) or {})
    range_break_ticks = dict(getattr(character.db, "range_break_ticks", {}) or {})
    if opponent and getattr(opponent, "id", None) is not None:
        combat_range.pop(opponent.id, None)
        range_break_ticks.pop(opponent.id, None)
    character.db.combat_range = combat_range
    character.db.range_break_ticks = range_break_ticks

    if opponent and getattr(opponent.db, "target", None) == character:
        opponent.db.target = None
        opponent.db.in_combat = False
        opponent.db.aiming = None
        opponent_range = dict(getattr(opponent.db, "combat_range", {}) or {})
        opponent_ticks = dict(getattr(opponent.db, "range_break_ticks", {}) or {})
        if getattr(character, "id", None) is not None:
            opponent_range.pop(character.id, None)
            opponent_ticks.pop(character.id, None)
        opponent.db.combat_range = opponent_range
        opponent.db.range_break_ticks = opponent_ticks


class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.gender = "unknown"
        self.db.age = DEFAULT_AGE
        self.db.race = DEFAULT_RACE
        self.db.identity = {
            "race": DEFAULT_RACE,
            "gender": "unknown",
            "appearance": {},
        }
        self.db.languages = {"common": 1.0}
        self.db.active_language = "common"
        self.db.race_respec_used = False
        self.db.guild = None
        self.db.profession = "commoner"
        self.db.profession_rank = 1
        self.db.circle = 1
        self.db.wilderness_bond = 50
        self.db.ranger_instinct = 0
        self.db.nature_focus = 0
        self.db.ranger_companion = normalize_ranger_companion()
        self.db.empath_shock = 0
        self.db.empath_link = None
        self.db.active_link = None
        self.db.empath_links = {}
        self.db.empath_unity = None
        self.db.empath_circle_members = []
        self.db.empath_circle_leader = None
        self.db.empath_circle_invites = []
        self.db.wounds = _copy_default_empath_wounds()
        self.db.stabilized_until = 0.0
        self.db.warrior_circle = 1
        self.db.unlocked_warrior_abilities = []
        self.db.unlocked_warrior_passives = []
        self.db.war_tempo = 0
        self.db.max_war_tempo = 100
        self.db.war_tempo_state = "calm"
        self.db.exhaustion = 0
        self.db.active_warrior_berserk = None
        self.db.active_warrior_roars = {}
        self.db.warrior_roar_effects = {}
        self.db.pressure_level = 0
        self.db.combat_streak = 0
        self.db.last_combat_action_at = 0
        self.db.rhythm_break_until = 0
        self.db.debug_mode = True
        self.db.crime_flag = False
        self.db.crime_severity = 0
        self.db.awareness_bonus = 0
        self.db.awareness_state = {}
        self.db.stealthed = False
        self.db.stealth_value = 0
        self.db.last_hide_time = 0
        self.db.last_search_time = 0
        self.db.perception_cache = None
        self.db.repeat_theft_targets = {}
        self.db.pvp_open_until = 0
        self.db.last_mark_target = None
        self.db.last_mark_time = 0
        self.db.contacts = {}
        self.db.thief_reputation = 0
        self.db.wanted_level = 0
        self.db.last_wanted_update = 0
        self.db.shop_heat = 0
        self.db.shop_heat_updated_at = 0
        self.db.theft_attempt_log = {}
        self.db.is_captured = False
        self.db.confiscated_items = []
        self.db.confiscation_location = None
        self.db.fine_amount = 0
        self.db.fine_due = 0
        self.db.justice_debt = 0
        self.db.collateral_locked = False
        self.db.fine_due_timestamp = None
        self.db.sentence_type = None
        self.db.jail_timer = 0
        self.db.in_stocks = False
        self.db.in_pillory = False
        self.db.pillory_end_time = 0
        self.db.in_jail = False
        self.db.jail_end_time = 0
        self.db.crime_count = 0
        self.db.last_crime_time = 0
        self.db.last_crime_decay_time = 0
        self.db.law_reputation = 0
        self.db.last_law_reputation_decay_time = 0
        self.db.awaiting_plea = False
        self.db.plea = None
        self.db.surrendered = False
        self.db.warrants = {}
        self.db.active_bounty = None
        self.db.last_known_region = None
        self.db.is_hidden_from_tracking = False
        self.db.known_passages = []
        self.db.in_passage = False
        self.db.marked_target = None
        self.db.mark_data = {}
        self.db.khri_pool = 100
        self.db.khri_active = {}
        self.db.khri_limit = 2
        self.db.theft_memory = {}
        self.db.last_slip_time = 0
        self.db.slipping = False
        self.db.slip_bonus = 0
        self.db.slip_timer = 0
        self.db.escape_chain = 0
        self.db.intimidated = False
        self.db.intimidation_timer = 0
        self.db.roughed = False
        self.db.rough_timer = 0
        self.db.staggered = False
        self.db.stagger_timer = 0
        self.db.position_state = "neutral"
        self.db.position_changed_at = 0
        self.db.attention_state = "idle"
        self.db.attention_changed_at = 0
        self.db.disguised = False
        self.db.disguise_name = None
        self.db.disguise_profession = None
        self.db.recent_action = False
        self.db.recent_action_timer = 0
        self.db.post_ambush_grace = False
        self.db.post_ambush_grace_until = 0
        self.db.desc = "An unremarkable person."
        self.db.is_npc = False
        self.db.stats = DEFAULT_STATS.copy()
        self.db.max_hp = 100
        self.db.hp = 100
        self.db.balance = 100
        self.db.max_balance = 100
        self.db.fatigue = 0
        self.db.max_fatigue = 100
        self.db.attunement = 100
        self.db.max_attunement = 100
        self.db.bleed_state = "none"
        self.db.roundtime_end = 0
        self.db.coins = 0
        self.db.total_tips = 0
        self.db.last_tip_amount = 0
        self.db.last_tip_time = 0.0
        self.db.tip_history = {}
        self.db.empath_reputation_score = 0
        self.db.last_perceive_time = 0.0
        self.db.last_medical_decay_at = 0.0
        self.db.last_critical_warning_at = 0.0
        self.db.empath_overload_until = 0.0
        self.db.empath_triage_context = {}
        self.db.last_triage_scan_at = 0.0
        self.db.exp_debt = 0
        self.db.recovery_consent = []
        self.db.last_recovery_type = None
        self.db.last_recovery_helper = None
        self.db.last_recovery_time = 0.0
        self.db.last_death_time = 0.0
        self.db.death_analytics = {}
        self.db.death_protection = True
        self.db.skills = {}
        self.db.stance = {"offense": 50, "defense": 50}
        self.db.position = "standing"
        self.db.target_body_part = None
        self.db.stunned = False
        self.db.equipped_weapon = None
        self.db.preferred_sheath = None
        self.db.equipment = _copy_default_equipment()
        self.db.in_combat = False
        self.db.target = None
        self.db.combat_range = {}
        self.db.range_break_ticks = {}
        self.db.aiming = None
        self.db.states = {"awareness": "normal"}
        self.db.injuries = _copy_default_injuries()
        self.db.last_disarmed_trap = None
        self.db.last_disarmed_trap_difficulty = 0
        self.db.last_disarmed_trap_source = None
        apply_race(self, DEFAULT_RACE, sync=False)
        self._ensure_exp_skill_handler(refresh=True)
        self.get_subsystem()
        for skill_name, baseline_rank in AVAILABLE_SKILL_BASELINES.items():
            self.learn_skill(skill_name, {"rank": baseline_rank, "mindstate": 0})

    def _restore_onboarding_entry_if_needed(self):
        step = str(getattr(self.db, "onboarding_step", "") or "").strip().lower()
        if not step or step == "complete":
            return False
        room = getattr(self, "location", None)
        room_is_tutorial = bool(getattr(getattr(room, "db", None), "is_onboarding", False) or getattr(getattr(room, "db", None), "is_tutorial", False))
        try:
            from server.conf.at_server_startstop import _ensure_new_player_tutorial
            from systems import onboarding

            if not room_is_tutorial:
                room = _ensure_new_player_tutorial()
                if room:
                    self.home = room
                    self.move_to(room, quiet=True, use_destination=False)
            onboarding.ensure_onboarding_state(self)
            onboarding.handle_room_entry(self)
        except Exception:
            return False
        return True

    def _apply_web_new_player_spawn(self):
        if not bool(getattr(self.db, "new_player", False)):
            return False

        try:
            from systems import onboarding
            from systems.character.creation import apply_starting_gear, apply_starting_skills

            guild_room = onboarding._resolve_empath_guild_room()
            if not guild_room:
                raise RuntimeError("Empath Guild room could not be resolved.")

            self.home = guild_room
            self.move_to(guild_room, quiet=True, use_destination=False)

            apply_starting_gear(self)
            apply_starting_skills(self)
            self.db.new_player = False
            self.db.skip_chargen = False
            self.db.onboarding_step = None
            self.db.onboarding_complete = True
            self.msg("You awaken within the Empaths' Guild.")
            LOGGER.info("Web new-player spawn applied for %s", getattr(self, "key", self))
            return True
        except Exception:
            LOGGER.exception("Failed web new-player spawn for %s", getattr(self, "key", self))
            return False

    def at_post_puppet(self, *args, **kwargs):
        super().at_post_puppet(*args, **kwargs)
        self.ensure_core_defaults()
        self.refresh_death_sting(emit_message=False)
        spawned_from_web = self._apply_web_new_player_spawn()
        if not spawned_from_web:
            self._restore_onboarding_entry_if_needed()
        try:
            from systems import aftermath

            aftermath.refresh_new_player_state(self)
            aftermath.note_room_entry(self, getattr(self, "location", None))
        except Exception:
            pass
        self.get_subsystem()
        sync_subject_interest(self)
        self.sync_client_state(include_map=True)
        if self.is_dead():
            self.msg("You are dead. You must wait for resurrection or type DEPART to let go.")

    def at_post_unpuppet(self, *args, **kwargs):
        super().at_post_unpuppet(*args, **kwargs)
        if bool(getattr(self.ndb, "is_fishing", False)) or getattr(self.ndb, "fishing_session", None) is not None:
            from world.systems.fishing import cancel_fishing_session

            cancel_fishing_session(self)
        clear_subject_interest(self)
        self.reset_thief_pressure_states()

    def _ensure_exp_skill_handler(self, refresh=False):
        handler = getattr(self, "exp_skills", None)
        if refresh or not isinstance(handler, SkillHandler) or getattr(handler, "obj", None) is not self:
            self.exp_skills = SkillHandler(self)
        return self.exp_skills

    def _sync_exp_skill_state(self, skill_name, legacy_entry=None):
        handler = self._ensure_exp_skill_handler()
        skill = handler.get(skill_name)
        if legacy_entry is None:
            legacy_entry = ((self.db.skills or {}) if isinstance(self.db.skills, Mapping) else {}).get(skill_name, {})
        if not isinstance(legacy_entry, Mapping):
            legacy_entry = {}

        persisted_entry = self._get_exp_skill_store().get(skill_name, {})
        if not isinstance(persisted_entry, Mapping):
            persisted_entry = {}

        if persisted_entry:
            skill.rank = max(
                0,
                int(skill.rank or 0),
                int(persisted_entry.get("rank", 0) or 0),
            )
        else:
            skill.rank = max(
                0,
                int(skill.rank or 0),
                int(legacy_entry.get("rank", 0) or 0),
            )
        skill.rank_progress = max(0.0, float(persisted_entry.get("rank_progress", skill.rank_progress) or 0.0))
        skill.pool = max(0.0, float(persisted_entry.get("pool", skill.pool) or 0.0))
        skill.last_trained = max(0.0, float(persisted_entry.get("last_trained", skill.last_trained) or 0.0))
        skill.skillset = str(persisted_entry.get("skillset") or self.get_exp_skillset_tier(skill_name) or "primary")
        skill.recalc_pool()
        return skill

    def _seed_template_exp_skills(self):
        self.ensure_skill_defaults()
        handler = self._ensure_exp_skill_handler()
        current_skills = self.db.skills if isinstance(self.db.skills, Mapping) else {}
        for skill_name in TEMPLATE_EXP_SKILLS:
            self._sync_exp_skill_state(skill_name, current_skills.get(skill_name, {}))
        return handler

    def _get_exp_skill_store(self):
        store = getattr(self.db, "exp_skill_state", None)
        return dict(store) if isinstance(store, Mapping) else {}

    def _persist_exp_skill_state(self, skill):
        if skill is None:
            return None
        store = self._get_exp_skill_store()
        store[skill.name] = {
            "rank": int(getattr(skill, "rank", 0) or 0),
            "rank_progress": float(getattr(skill, "rank_progress", 0.0) or 0.0),
            "pool": float(getattr(skill, "pool", 0.0) or 0.0),
            "skillset": str(getattr(skill, "skillset", "primary") or "primary"),
            "mindstate": int(getattr(skill, "mindstate", 0) or 0),
            "last_trained": float(getattr(skill, "last_trained", 0.0) or 0.0),
        }
        self.db.exp_skill_state = store

        skills = dict(self.db.skills or {})
        legacy_entry = dict(skills.get(skill.name) or {"rank": 0, "mindstate": 0})
        legacy_entry["rank"] = max(int(legacy_entry.get("rank", 0) or 0), int(getattr(skill, "rank", 0) or 0))
        legacy_entry.setdefault("mindstate", int(legacy_entry.get("mindstate", 0) or 0))
        skills[skill.name] = legacy_entry
        self.db.skills = skills
        return skill

    def get_exp_skillset_tier(self, skill_name):
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in EXP_SKILLSET_TIER_OVERRIDES:
            return EXP_SKILLSET_TIER_OVERRIDES[normalized]
        metadata = self.get_skill_metadata(normalized)
        category = str(metadata.get("category", "") or "").strip().lower()
        if category in {"primary", "secondary", "tertiary"}:
            return category
        return "primary"

    def award_skill_experience(self, skill_name, difficulty, success=True, outcome=None, event_key=None, context_multiplier=1.0):
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            return 0.0
        exp_skill = self._sync_exp_skill_state(normalized)
        exp_skill.skillset = self.get_exp_skillset_tier(normalized)
        exp_skill.recalc_pool()
        gained = award_exp_skill(
            self,
            normalized,
            difficulty,
            success=success,
            outcome=outcome,
            event_key=event_key,
            context_multiplier=context_multiplier,
        )
        self._persist_exp_skill_state(exp_skill)
        return gained

    def award_field_xp(self, action_key, difficulty=None, success=True, outcome=None, context_multiplier=1.0):
        normalized_action = str(action_key or "").strip().lower()
        config = EMPATH_FIELD_XP.get(normalized_action)
        if not config:
            return 0.0
        skill_name, default_difficulty, event_key = config
        resolved_difficulty = int(default_difficulty if difficulty is None else difficulty)
        return self.award_skill_experience(
            skill_name,
            max(1, resolved_difficulty),
            success=success,
            outcome=outcome,
            event_key=event_key,
            context_multiplier=context_multiplier,
        )

    def compute_empathy_xp(self, action_key, difficulty, amount=0, target=None, wound_key=None, requested_fraction=None, rate_key=None, unity=False):
        normalized_action = str(action_key or "take").strip().lower() or "take"
        multiplier = {
            "link": 0.35,
            "unity": 0.6,
            "redirect": 0.85,
            "manipulate": 0.75,
            "perceive_health": 0.2,
            "perceive_target": 0.3,
            "take": 1.0,
            "channel": 0.7,
            "mend": 0.45,
            "purge": 0.55,
            "scar_heal": 0.5,
            "legacy_transfer": 0.9,
        }.get(normalized_action, 1.0)

        normalized_wound = self.normalize_empath_wound_key(wound_key) if wound_key else ""
        if normalized_wound == "vitality":
            multiplier *= 1.25
        elif normalized_wound in {"poison", "disease"}:
            multiplier *= 1.1

        if requested_fraction is not None:
            multiplier *= max(0.45, min(1.0, float(requested_fraction) + 0.25))
        if rate_key == "slow":
            multiplier *= 0.85
        elif rate_key == "fast":
            multiplier *= 1.1
        if unity:
            multiplier *= 1.1
        if target is not None and hasattr(target, "is_empath") and target.is_empath():
            multiplier *= 0.25
        if int(amount or 0) > 0:
            multiplier *= max(0.5, min(1.4, 0.65 + (int(amount or 0) / 40.0)))

        return {
            "difficulty": max(1, int(difficulty or 1)),
            "event_key": f"empathy_{normalized_action}",
            "context_multiplier": multiplier,
        }

    def award_empathy_experience(self, action_key, difficulty, amount=0, target=None, wound_key=None, requested_fraction=None, rate_key=None, unity=False):
        profile = self.compute_empathy_xp(
            action_key,
            difficulty,
            amount=amount,
            target=target,
            wound_key=wound_key,
            requested_fraction=requested_fraction,
            rate_key=rate_key,
            unity=unity,
        )
        return self.award_skill_experience(
            "empathy",
            profile["difficulty"],
            success=True,
            outcome="success",
            event_key=profile["event_key"],
            context_multiplier=profile["context_multiplier"],
        )

    def _get_first_aid_tend_profile(self, body_part):
        bleed = max(0, int((body_part or {}).get("bleed", 0) or 0))
        trauma = max(0, int(self.get_part_trauma(body_part) or 0)) if body_part else 0
        severity = max(1, (bleed * 12) + trauma)
        if severity >= 60:
            return {"difficulty": 22, "context_multiplier": 1.35, "severity": severity}
        if severity >= 30:
            return {"difficulty": 16, "context_multiplier": 1.05, "severity": severity}
        if severity >= 12:
            return {"difficulty": 12, "context_multiplier": 0.85, "severity": severity}
        return {"difficulty": 10, "context_multiplier": 0.65, "severity": severity}

    def start_first_aid_training_window(self, part, tender=None):
        body_part = self.get_body_part(part)
        if not body_part:
            return False
        tend_state = dict(body_part.get("tend") or {})
        now = time.time()
        training_until = float(tend_state.get("xp_window_until", 0.0) or 0.0)
        if training_until > now:
            body_part["tend"] = tend_state
            return True
        profile = self._get_first_aid_tend_profile(body_part)
        tender_id = int(getattr(tender or self, "id", 0) or 0)
        tend_state.update(
            {
                "xp_window_until": now + 300.0,
                "xp_next_at": now + 15.0,
                "xp_pulses": 0,
                "xp_tender_id": tender_id,
                "xp_severity": int(profile["severity"]),
            }
        )
        body_part["tend"] = tend_state
        return True

    def process_first_aid_tend_training(self, now=None):
        current_time = float(now or time.time())
        injuries = getattr(self.db, "injuries", None) or {}
        changed = False
        for _part_name, body_part in injuries.items():
            if not isinstance(body_part, Mapping):
                continue
            tend_state = dict(body_part.get("tend") or {})
            window_until = float(tend_state.get("xp_window_until", 0.0) or 0.0)
            next_at = float(tend_state.get("xp_next_at", 0.0) or 0.0)
            pulses = max(0, int(tend_state.get("xp_pulses", 0) or 0))
            tender_id = int(tend_state.get("xp_tender_id", 0) or 0)
            if window_until <= current_time or pulses >= 20 or next_at <= 0.0 or current_time < next_at:
                continue
            if int(body_part.get("bleed", 0) or 0) <= 0 and int(self.get_part_trauma(body_part) or 0) <= 0:
                tend_state["xp_window_until"] = 0.0
                tend_state["xp_next_at"] = 0.0
                body_part["tend"] = tend_state
                changed = True
                continue

            tender = self if tender_id == int(getattr(self, "id", 0) or 0) else None
            if tender is None and tender_id > 0:
                result = search_object(f"#{tender_id}")
                tender = result[0] if result else None
            if tender is None or not hasattr(tender, "award_skill_experience"):
                continue

            profile = self._get_first_aid_tend_profile(body_part)
            severity_multiplier = max(
                float(profile["context_multiplier"]),
                0.5 + (max(1, int(tend_state.get("xp_severity", profile["severity"]) or profile["severity"])) / 80.0),
            )
            tender.award_skill_experience(
                "first_aid",
                profile["difficulty"],
                success=True,
                outcome="success",
                event_key="first_aid_tend",
                context_multiplier=severity_multiplier,
            )
            tend_state["xp_pulses"] = pulses + 1
            tend_state["xp_next_at"] = current_time + 15.0
            body_part["tend"] = tend_state
            changed = True
        return changed

    def _is_anatomy_study_item(self, item):
        if not item:
            return False
        if bool(getattr(item.db, "anatomy_study", False) or getattr(item.db, "anatomy_chart", False)):
            return True
        raw_tags = list(getattr(item.db, "study_tags", None) or [])
        normalized_tags = {str(tag or "").strip().lower() for tag in raw_tags}
        if "anatomy" in normalized_tags:
            return True
        searchable = " ".join(
            [
                str(getattr(item, "key", "") or ""),
                str(getattr(item.db, "desc", "") or ""),
            ]
        ).lower()
        return "anatomy" in searchable or "anatomical" in searchable or "body chart" in searchable

    def at_after_move(self, source_location, **kwargs):
        super().at_after_move(source_location, **kwargs)
        self.ndb.is_busy = False
        self.ndb.is_walking = False
        try:
            from systems import aftermath

            aftermath.refresh_new_player_state(self)
            aftermath.note_room_entry(self, getattr(self, "location", None))
        except Exception:
            pass
        if getattr(self.db, "slipping", False):
            self.db.slip_bonus = int(getattr(self.db, "slip_bonus", 0) or 0) + 5
            self.db.escape_chain = int(getattr(self.db, "escape_chain", 0) or 0) + 1
        guild_tag = getattr(getattr(self, "location", None), "db", None)
        guild_tag = getattr(guild_tag, "guild_tag", None)
        if guild_tag:
            self.msg("You feel the presence of a guild here.")
        if hasattr(self.location, "is_lawless"):
            if self.location.is_lawless():
                self.msg("You feel the absence of law here.")
            else:
                self.msg("The presence of law is felt here.")
            if getattr(self.db, "debug_mode", False):
                print(f"{self} entered {self.location} with law={self.location.get_law_type()}")
        self.emit_profession_presence()
        for obj in getattr(self.location, "contents", []):
            if obj != self and hasattr(obj, "react_to"):
                obj.react_to(self, context="presence")
        if getattr(self.db, "warrants", None) and hasattr(self.location, "get_region"):
            self.db.last_known_region = self.location.get_region()
        if hasattr(self.location, "is_lawless"):
            self.db.is_hidden_from_tracking = bool(self.location.is_lawless())
        current_region = self.location.get_region() if hasattr(self.location, "get_region") else None
        if not getattr(self.db, "is_captured", False) and current_region and (getattr(self.db, "warrants", None) or {}).get(current_region) and not self.location.is_lawless():
            from utils.crime import call_guards

            call_guards(self.location, self)

    def sync_client_state(self, include_map=False, include_subsystem=True, include_character=True, session=None):
        sessions_attr = getattr(self, "sessions", None)
        sessions = [session] if session else list(sessions_attr.all()) if sessions_attr else []
        if not sessions:
            return
        structured_sessions = [active_session for active_session in sessions if _supports_structured_session(active_session)]
        if not structured_sessions:
            return
        if session:
            session = structured_sessions[0]
        if include_map:
            try:
                send_map_update(self, session=session)
            except Exception:
                LOGGER.exception("Failed to sync map state for %s in %s", getattr(self, "key", self), getattr(getattr(self, "location", None), "key", None))
        if include_subsystem:
            send_subsystem_update(self, session=session)
        if include_character:
            send_character_update(self, session=session)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if getattr(moved_obj, "destination", None) is None:
            self.db.encumbrance_dirty = True
            self.sync_client_state()

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        super().at_object_leave(moved_obj, target_location, **kwargs)
        if getattr(moved_obj, "destination", None) is None:
            self.db.encumbrance_dirty = True
            self.sync_client_state()

    def ensure_identity_defaults(self):
        from systems.appearance.normalizer import normalize_character_identity

        if self.db.gender is None:
            self.db.gender = "unknown"
        if self.db.age is None:
            self.db.age = DEFAULT_AGE
        if self.db.race is None:
            self.db.race = DEFAULT_RACE
        normalize_character_identity(self)
        stored_languages = getattr(self.db, "languages", None)
        if isinstance(stored_languages, Mapping):
            normalized_languages = {}
            for language_name, proficiency in dict(stored_languages).items():
                normalized = normalize_language_name(language_name, default=None)
                if not normalized:
                    continue
                try:
                    normalized_languages[normalized] = max(0.0, min(1.0, float(proficiency)))
                except (TypeError, ValueError):
                    normalized_languages[normalized] = 0.0
        elif isinstance(stored_languages, list):
            normalized_languages = {}
            for language_name in list(stored_languages or []):
                normalized = normalize_language_name(language_name, default=None)
                if normalized:
                    normalized_languages[normalized] = 1.0
        else:
            normalized_languages = {}

        if not normalized_languages:
            normalized_languages = {
                language_name: 1.0 for language_name in get_languages_for_race(getattr(self.db, "race", DEFAULT_RACE))
            }
        if not isinstance(getattr(self.db, "language_comprehension_overrides", None), Mapping):
            self.db.language_comprehension_overrides = {}
        if "common" not in normalized_languages:
            normalized_languages["common"] = 1.0
        self.db.languages = normalized_languages
        active_language = normalize_language_name(getattr(self.db, "active_language", None), default=None)
        if active_language not in normalized_languages:
            self.db.active_language = "common"
        else:
            self.db.active_language = active_language
        if self.db.race_respec_used is None:
            self.db.race_respec_used = False
        if self.db.onboarding_state is None:
            self.db.onboarding_state = None
        if self.db.onboarding_step is None:
            self.db.onboarding_step = None
        if self.db.onboarding_complete is None:
            self.db.onboarding_complete = False
        if self.db.first_area_state is None:
            self.db.first_area_state = None
        if self.db.guild is None:
            self.db.guild = None
        if self.db.profession is None:
            self.db.profession = self.normalize_profession_name(getattr(self.db, "guild", None)) or DEFAULT_PROFESSION
        if self.db.profession_rank is None:
            self.db.profession_rank = 1
        if self.db.life_state is None:
            self.db.life_state = LIFE_STATE_ALIVE
        if self.db.wilderness_bond is None:
            self.db.wilderness_bond = 50
        if self.db.ranger_instinct is None:
            self.db.ranger_instinct = 0
        if self.db.nature_focus is None:
            self.db.nature_focus = 0
        if self.db.ranger_companion is None:
            self.db.ranger_companion = normalize_ranger_companion()
        if self.db.empath_shock is None:
            self.db.empath_shock = 0
        if getattr(self.db, "empath_rank", None) is None:
            self.db.empath_rank = 0
        if getattr(self.db, "empath_xp", None) is None:
            self.db.empath_xp = 0
        if getattr(self.db, "empath_training_stage", None) is None:
            self.db.empath_training_stage = EMPATH_TRAINING_UNSET
        if getattr(self.db, "empath_tutorial_patient_id", None) is None:
            self.db.empath_tutorial_patient_id = None
        if getattr(self.db, "empath_link", None) is None:
            self.db.empath_link = None
        if self.db.active_link is None:
            self.db.active_link = None
        empath_links_missing = self.db.empath_links is None
        if empath_links_missing:
            self.db.empath_links = {}
        if self.db.empath_unity is None:
            self.db.empath_unity = None
        if getattr(self.db, "empath_circle_members", None) is None:
            self.db.empath_circle_members = []
        if getattr(self.db, "empath_circle_leader", None) is None:
            self.db.empath_circle_leader = None
        if getattr(self.db, "empath_circle_invites", None) is None:
            self.db.empath_circle_invites = []
        raw_link = getattr(self.db, "empath_link", None)
        if isinstance(raw_link, int):
            legacy_target_id = int(raw_link or 0)
            self.db.empath_link = {
                "target_id": legacy_target_id,
                "type": EMPATH_LINK_TOUCH,
                "strength": 60,
                "stability": 80,
                "created_at": time.time(),
            } if legacy_target_id > 0 else None
        elif isinstance(raw_link, Mapping) and int(raw_link.get("target_id", 0) or 0) > 0:
            link_type = str(raw_link.get("type") or EMPATH_LINK_TOUCH).strip().lower()
            if link_type in {"standard", "link", "strong", "deep"}:
                link_type = EMPATH_LINK_DIRECT
            self.db.empath_link = {
                "target_id": int(raw_link.get("target_id", 0) or 0),
                "type": link_type if link_type in EMPATH_LINK_TYPES else EMPATH_LINK_TOUCH,
                "strength": max(1, min(100, int(raw_link.get("strength", EMPATH_LINK_BASE_STRENGTH.get(link_type, 60)) or EMPATH_LINK_BASE_STRENGTH.get(link_type, 60)))),
                "stability": max(0, min(150, int(raw_link.get("stability", EMPATH_LINK_BASE_STABILITY.get(link_type, 100)) or EMPATH_LINK_BASE_STABILITY.get(link_type, 100)))),
                "created_at": float(raw_link.get("created_at", time.time()) or time.time()),
            }
        elif getattr(self.db, "active_link", None) and empath_links_missing:
            legacy_target_id = int(getattr(self.db, "active_link", 0) or 0)
            if legacy_target_id > 0:
                self.db.empath_link = {
                    "target_id": legacy_target_id,
                    "type": EMPATH_LINK_TOUCH,
                    "strength": 60,
                    "stability": 80,
                    "created_at": time.time(),
                }
        if self.db.wounds is None:
            self.db.wounds = _copy_default_empath_wounds()
        if self.db.warrior_circle is None:
            self.db.warrior_circle = 1
        if self.db.unlocked_warrior_abilities is None:
            self.db.unlocked_warrior_abilities = []
        if self.db.unlocked_warrior_passives is None:
            self.db.unlocked_warrior_passives = []
        if self.db.war_tempo is None:
            self.db.war_tempo = 0
        if self.db.max_war_tempo is None:
            self.db.max_war_tempo = 100
        if self.db.war_tempo_state is None:
            self.db.war_tempo_state = "calm"
        if self.db.active_warrior_berserk is None:
            self.db.active_warrior_berserk = None
        if self.db.active_warrior_roars is None:
            self.db.active_warrior_roars = {}
        if self.db.warrior_roar_effects is None:
            self.db.warrior_roar_effects = {}
        if self.db.pressure_level is None:
            self.db.pressure_level = 0
        if self.db.combat_streak is None:
            self.db.combat_streak = 0
        if self.db.last_combat_action_at is None:
            self.db.last_combat_action_at = 0
        if self.db.rhythm_break_until is None:
            self.db.rhythm_break_until = 0
        if self.db.total_xp is None:
            self.db.total_xp = 0
        if self.db.unabsorbed_xp is None:
            self.db.unabsorbed_xp = 0
        if self.db.exp_debt is None:
            self.db.exp_debt = 0
        if self.db.favor is None:
            self.db.favor = 0
        if self.db.cleric_ritual_timestamps is None:
            self.db.cleric_ritual_timestamps = {}
        if self.db.last_devotion_drift_at is None:
            self.db.last_devotion_drift_at = 0.0
        if self.db.death_favor_snapshot is None:
            self.db.death_favor_snapshot = None
        if self.db.soul_state is None:
            self.db.soul_state = None
        if self.db.last_corpse_id is None:
            self.db.last_corpse_id = None
        if self.db.death_sting is None:
            self.db.death_sting = 0
        if self.db.death_sting_active is None:
            self.db.death_sting_active = False
        if self.db.death_sting_end is None:
            self.db.death_sting_end = 0.0
        if self.db.death_sting_severity is None:
            self.db.death_sting_severity = 0.0
        if self.db.death_sting_hp_cap_ratio is None:
            self.db.death_sting_hp_cap_ratio = 1.0
        if self.db.death_sting_recovery_label is None:
            self.db.death_sting_recovery_label = "none"
        if self.db.death_penalty_applied is None:
            self.db.death_penalty_applied = False
        if self.db.depart_confirm_mode is None:
            self.db.depart_confirm_mode = None
        if self.db.depart_confirm_expires_at is None:
            self.db.depart_confirm_expires_at = 0.0
        if self.db.deaths_since_last_shrine is None:
            self.db.deaths_since_last_shrine = 0
        if self.db.last_low_favor_warning_at is None:
            self.db.last_low_favor_warning_at = 0.0
        if self.db.debug_mode is None:
            self.db.debug_mode = True
        if self.db.crime_flag is None:
            self.db.crime_flag = False
        if self.db.crime_severity is None:
            self.db.crime_severity = 0
        if self.db.is_captured is None:
            self.db.is_captured = False
        if self.db.confiscated_items is None:
            self.db.confiscated_items = []
        if self.db.confiscation_location is None:
            self.db.confiscation_location = None
        if self.db.fine_amount is None:
            self.db.fine_amount = 0
        if self.db.fine_due is None:
            self.db.fine_due = 0
        if self.db.justice_debt is None:
            self.db.justice_debt = 0
        if self.db.collateral_locked is None:
            self.db.collateral_locked = False
        if self.db.fine_due_timestamp is None:
            self.db.fine_due_timestamp = None
        if self.db.sentence_type is None:
            self.db.sentence_type = None
        if self.db.jail_timer is None:
            self.db.jail_timer = 0
        if self.db.in_stocks is None:
            self.db.in_stocks = False
        if self.db.in_pillory is None:
            self.db.in_pillory = False
        if self.db.pillory_end_time is None:
            self.db.pillory_end_time = 0
        if self.db.in_jail is None:
            self.db.in_jail = False
        if self.db.jail_end_time is None:
            self.db.jail_end_time = 0
        if self.db.crime_count is None:
            self.db.crime_count = 0
        if self.db.last_crime_time is None:
            self.db.last_crime_time = 0
        if self.db.last_crime_decay_time is None:
            self.db.last_crime_decay_time = 0
        if self.db.law_reputation is None:
            self.db.law_reputation = 0
        if self.db.last_law_reputation_decay_time is None:
            self.db.last_law_reputation_decay_time = 0
        if self.db.awaiting_plea is None:
            self.db.awaiting_plea = False
        if self.db.plea is None:
            self.db.plea = None
        if self.db.surrendered is None:
            self.db.surrendered = False
        if self.db.warrants is None:
            self.db.warrants = {}
        if self.db.active_bounty is None:
            self.db.active_bounty = None
        if self.db.last_known_region is None:
            self.db.last_known_region = None
        if self.db.is_hidden_from_tracking is None:
            self.db.is_hidden_from_tracking = False
        if self.db.known_passages is None:
            self.db.known_passages = []
        if self.db.in_passage is None:
            self.db.in_passage = False
        if self.db.marked_target is None:
            self.db.marked_target = None
        if self.db.mark_data is None:
            self.db.mark_data = {}
        if self.db.khri_pool is None:
            self.db.khri_pool = 100
        if self.db.khri_active is None:
            self.db.khri_active = {}
        if self.db.khri_limit is None:
            self.db.khri_limit = 2
        if self.db.theft_memory is None:
            self.db.theft_memory = {}
        if self.db.last_slip_time is None:
            self.db.last_slip_time = 0
        if self.db.slipping is None:
            self.db.slipping = False
        if self.db.slip_bonus is None:
            self.db.slip_bonus = 0
        if self.db.slip_timer is None:
            self.db.slip_timer = 0
        if self.db.escape_chain is None:
            self.db.escape_chain = 0
        if self.db.intimidated is None:
            self.db.intimidated = False
        if self.db.intimidation_timer is None:
            self.db.intimidation_timer = 0
        if self.db.roughed is None:
            self.db.roughed = False
        if self.db.rough_timer is None:
            self.db.rough_timer = 0
        if self.db.staggered is None:
            self.db.staggered = False
        if self.db.stagger_timer is None:
            self.db.stagger_timer = 0
        if self.db.position_state is None:
            self.db.position_state = "neutral"
        if self.db.position_changed_at is None:
            self.db.position_changed_at = 0
        if self.db.attention_state is None:
            self.db.attention_state = "idle"
        if self.db.attention_changed_at is None:
            self.db.attention_changed_at = 0
        if self.db.disguised is None:
            self.db.disguised = False
        if self.db.disguise_name is None:
            self.db.disguise_name = None
        if self.db.disguise_profession is None:
            self.db.disguise_profession = None
        if self.db.recent_action is None:
            self.db.recent_action = False
        if self.db.recent_action_timer is None:
            self.db.recent_action_timer = 0
        if self.db.post_ambush_grace is None:
            self.db.post_ambush_grace = False
        if self.db.post_ambush_grace_until is None:
            self.db.post_ambush_grace_until = 0
        if self.get_profession() == "warrior":
            self.sync_warrior_progression(emit_messages=False)
        if self.db.last_seen_magic is None:
            self.db.last_seen_magic = 0
        if self.db.awareness_bonus is None:
            self.db.awareness_bonus = 0
        if self.db.desc is None:
            self.db.desc = "An unremarkable person."
        if self.db.is_npc is None:
            self.db.is_npc = False
        if self.db.is_dead is None:
            self.db.is_dead = False
        if self.db.death_type is None:
            self.db.death_type = None
        if self.db.death_timestamp is None:
            self.db.death_timestamp = 0.0
        if self.db.death_location is None:
            self.db.death_location = None
        if self.db.recovery_state is None:
            self.db.recovery_state = "none"
        if self.db.corpse_id is None:
            self.db.corpse_id = None
        if self.db.favor_current is None:
            legacy_favor = getattr(self.db, "favor", None)
            self.db.favor_current = int(legacy_favor or 0) if legacy_favor is not None else 1
        if self.db.favor_max is None:
            self.db.favor_max = 5
        self.db.favor_current = max(0, min(int(self.db.favor_current or 0), int(self.db.favor_max or 0)))
        self.db.favor = self.db.favor_current
        if self.db.last_pray_time is None:
            self.db.last_pray_time = 0.0
        if self.db.last_favor_decay_at is None:
            self.db.last_favor_decay_at = 0.0
        if self.db.last_shrine_favor_regen_at is None:
            self.db.last_shrine_favor_regen_at = 0.0
        if self.db.recovery_consent is None:
            self.db.recovery_consent = []
        if self.db.last_recovery_type is None:
            self.db.last_recovery_type = None
        if self.db.last_recovery_quality is None:
            self.db.last_recovery_quality = None
        if self.db.resurrection_vitality_cap_ratio is None:
            self.db.resurrection_vitality_cap_ratio = 1.0
        if self.db.last_recovery_helper is None:
            self.db.last_recovery_helper = None
        if self.db.last_recovery_time is None:
            self.db.last_recovery_time = 0.0
        if self.db.last_death_time is None:
            self.db.last_death_time = 0.0
        if self.db.death_analytics is None:
            self.db.death_analytics = {}
        if self.db.death_protection is None:
            self.db.death_protection = True
        if self.db.stored_coins is None:
            self.db.stored_coins = 0
        if self.db.bank_coins is None:
            self.db.bank_coins = 0
        if self.db.max_carry_weight is None:
            self.db.max_carry_weight = 100.0
        if self.db.encumbrance_ratio is None:
            self.db.encumbrance_ratio = 0.0
        if self.db.coin_weight_notice_active is None:
            self.db.coin_weight_notice_active = False
        if self.db.searched is None:
            self.db.searched = False
        if self.db.coins_looted is None:
            self.db.coins_looted = False
        if self.db.gems_looted is None:
            self.db.gems_looted = False
        if self.db.box_looted is None:
            self.db.box_looted = False
        if self.db.loot_generated is None:
            self.db.loot_generated = False
        if self.db.has_gems is None:
            self.db.has_gems = False
        if self.db.has_box is None:
            self.db.has_box = False
        if self.db.has_coins is None:
            self.db.has_coins = False
        if self.db.coin_min is None:
            self.db.coin_min = 0
        if self.db.coin_max is None:
            self.db.coin_max = 0
        if self.db.drops_box is None:
            self.db.drops_box = False
        if self.db.vault_items is None:
            self.db.vault_items = []

    def ensure_race_defaults(self):
        race_key = resolve_race_name(getattr(self.db, "race", None), default=DEFAULT_RACE)
        if self.db.race != race_key:
            self.db.race = race_key

        canonical = build_race_state(race_key)
        if not isinstance(getattr(self.db, "stat_caps", None), Mapping) or dict(self.db.stat_caps) != canonical["stat_caps"]:
            self.db.stat_caps = dict(canonical["stat_caps"])
        if not isinstance(getattr(self.db, "learning_modifiers", None), Mapping) or dict(self.db.learning_modifiers) != canonical["learning_modifiers"]:
            self.db.learning_modifiers = dict(canonical["learning_modifiers"])
        if str(getattr(self.db, "size", "") or "").strip().lower() != canonical["size"]:
            self.db.size = canonical["size"]
        if abs(float(getattr(self.db, "carry_modifier", 1.0) or 1.0) - float(canonical["carry_modifier"])) > 0.0001:
            self.db.carry_modifier = float(canonical["carry_modifier"])
        if abs(float(getattr(self.db, "max_carry_weight", canonical["max_carry_weight"]) or canonical["max_carry_weight"]) - float(canonical["max_carry_weight"])) > 0.0001:
            self.db.max_carry_weight = float(canonical["max_carry_weight"])
        self.clamp_stats_to_race(emit_messages=False)

    def ensure_stat_defaults(self):
        current_stats = self.db.stats
        stats = dict(DEFAULT_STATS)
        if isinstance(current_stats, Mapping):
            stats.update({key: current_stats.get(key, value) for key, value in DEFAULT_STATS.items()})
        if not isinstance(current_stats, Mapping) or dict(current_stats) != stats:
            self.db.stats = stats

    def ensure_resource_defaults(self):
        if self.db.max_hp is None:
            self.db.max_hp = 100
        if self.db.hp is None:
            self.db.hp = self.db.max_hp
        if self.db.balance is None:
            self.db.balance = 100
        if self.db.max_balance is None:
            self.db.max_balance = 100
        if self.db.fatigue is None:
            self.db.fatigue = 0
        if self.db.max_fatigue is None:
            self.db.max_fatigue = 100
        if self.db.attunement is None:
            self.db.attunement = 100
        if self.db.max_attunement is None:
            self.db.max_attunement = 100
        if self.db.inner_fire is None:
            self.db.inner_fire = 10
        if self.db.max_inner_fire is None:
            self.db.max_inner_fire = 10
        if self.db.focus is None:
            self.db.focus = 10
        if self.db.max_focus is None:
            self.db.max_focus = 10
        if self.db.transfer_pool is None:
            self.db.transfer_pool = 10
        if self.db.max_transfer_pool is None:
            self.db.max_transfer_pool = 10
        if self.db.devotion_current is None:
            self.db.devotion_current = 0
        if self.db.devotion is None:
            self.db.devotion = int(getattr(self.db, "devotion_current", 0) or 0)
        if self.db.devotion_max is None:
            self.db.devotion_max = int(CLERIC_DEVOTION_CONFIG["max_devotion"] if self.is_profession("cleric") else 0)
        if self.db.max_devotion is None:
            self.db.max_devotion = int(getattr(self.db, "devotion_max", 0) or 0)
        if self.db.bleed_state is None:
            self.db.bleed_state = "none"
        if self.db.stabilized_until is None:
            self.db.stabilized_until = 0.0
        if self.db.stability_strength is None:
            self.db.stability_strength = 0.0
        if self.db.roundtime_end is None:
            self.db.roundtime_end = 0
        if self.db.coins is None:
            self.db.coins = 0
        if not self.attributes.has("last_disarmed_trap"):
            self.db.last_disarmed_trap = None
        if not self.attributes.has("last_disarmed_trap_difficulty"):
            self.db.last_disarmed_trap_difficulty = 0
        if not self.attributes.has("last_disarmed_trap_source"):
            self.db.last_disarmed_trap_source = None

    def ensure_combat_defaults(self):
        current_stance = self.db.stance
        if not isinstance(self.db.stance, Mapping):
            self.db.stance = {"offense": 50, "defense": 50}
        if self.db.position is None:
            self.db.position = "standing"
        if not self.attributes.has("target_body_part"):
            self.db.target_body_part = None
        if not self.attributes.has("stunned"):
            self.db.stunned = False
        if not self.attributes.has("equipped_weapon"):
            self.db.equipped_weapon = None
        if not self.attributes.has("preferred_sheath"):
            self.db.preferred_sheath = None
        if not self.attributes.has("in_combat"):
            self.db.in_combat = False
        if not self.attributes.has("target"):
            self.db.target = None
        if not isinstance(self.db.combat_range, Mapping):
            self.db.combat_range = {}
        else:
            normalized_range = {
                int(key): normalize_range_band(value)
                for key, value in dict(self.db.combat_range).items()
            }
            if dict(self.db.combat_range) != normalized_range:
                self.db.combat_range = normalized_range
        if not isinstance(self.db.range_break_ticks, Mapping):
            self.db.range_break_ticks = {}
        else:
            normalized_ticks = {
                int(key): int(value)
                for key, value in dict(self.db.range_break_ticks).items()
            }
            if dict(self.db.range_break_ticks) != normalized_ticks:
                self.db.range_break_ticks = normalized_ticks
        if self.db.aiming is not None:
            try:
                aiming = int(self.db.aiming)
                if aiming != self.db.aiming:
                    self.db.aiming = aiming
            except (TypeError, ValueError):
                self.db.aiming = None
        if not isinstance(self.db.states, Mapping):
            self.db.states = {}
        if not isinstance(current_stance, Mapping) or dict(self.db.stance) != dict(current_stance):
            self.normalize_stance()

    def ensure_equipment_defaults(self):
        current_equipment = self.db.equipment
        equipment = current_equipment if isinstance(current_equipment, Mapping) else {}
        normalized = _copy_default_equipment()

        for slot, default in normalized.items():
            if slot not in equipment:
                continue
            value = equipment.get(slot)
            if isinstance(default, list):
                if value is None:
                    normalized[slot] = []
                else:
                    try:
                        normalized[slot] = list(value)
                    except TypeError:
                        normalized[slot] = []
            else:
                normalized[slot] = value

        legacy_belt_item = equipment.get("belt")
        if normalized["waist"] is None and legacy_belt_item is not None:
            normalized["waist"] = legacy_belt_item

        if not isinstance(current_equipment, Mapping) or dict(current_equipment) != normalized:
            self.db.equipment = normalized

    def ensure_injury_defaults(self):
        current_injuries = self.db.injuries
        injuries = _copy_default_injuries()
        if isinstance(current_injuries, Mapping):
            for part_name, defaults in injuries.items():
                existing = current_injuries.get(part_name, {})
                if not isinstance(existing, Mapping):
                    continue

                merged = defaults.copy()
                merged.update(
                    {
                        "external": existing.get("external", defaults["external"]),
                        "internal": existing.get("internal", defaults["internal"]),
                        "bruise": existing.get("bruise", defaults["bruise"]),
                        "bleed": existing.get("bleed", existing.get("bleeding", defaults["bleed"])),
                        "scar": int(existing.get("scar", defaults["scar"]) or 0),
                        "tended": bool(existing.get("tended", defaults["tended"])),
                        "tend": {
                            "strength": int((existing.get("tend") or {}).get("strength", defaults["tend"]["strength"])),
                            "duration": int((existing.get("tend") or {}).get("duration", defaults["tend"]["duration"])),
                            "last_applied": float((existing.get("tend") or {}).get("last_applied", defaults["tend"]["last_applied"])),
                            "min_until": float((existing.get("tend") or {}).get("min_until", defaults["tend"]["min_until"])),
                        },
                        "max": existing.get("max", defaults["max"]),
                        "vital": existing.get("vital", defaults["vital"]),
                    }
                )
                injuries[part_name] = merged
        if not isinstance(current_injuries, Mapping) or dict(current_injuries) != injuries:
            self.db.injuries = injuries
        current_wounds = self.db.wounds
        wounds = _copy_default_empath_wounds()
        if isinstance(current_wounds, Mapping):
            for wound_name, default_value in wounds.items():
                wounds[wound_name] = max(0, min(100, int(current_wounds.get(wound_name, default_value) or 0)))
        if not isinstance(current_wounds, Mapping) or dict(current_wounds) != wounds:
            self.db.wounds = wounds

    def ensure_starter_skills(self):
        current_skills = dict(self.db.skills or {})
        skills = dict(current_skills)
        migrated = bool(getattr(self.db, "starter_skill_baseline_migrated", False))

        legacy_tend = skills.get("tend")
        if isinstance(legacy_tend, Mapping):
            first_aid = dict(skills.get("first_aid") or {"rank": 0, "mindstate": 0})
            first_aid["rank"] = max(first_aid.get("rank", 0), legacy_tend.get("rank", 0))
            first_aid["mindstate"] = max(first_aid.get("mindstate", 0), legacy_tend.get("mindstate", 0))
            skills["first_aid"] = first_aid
        skills.pop("tend", None)

        for skill_name, baseline_rank in AVAILABLE_SKILL_BASELINES.items():
            skills.setdefault(skill_name, {"rank": baseline_rank, "mindstate": 0})

            current = skills.get(skill_name, {})
            if not isinstance(current, Mapping):
                current = {"rank": baseline_rank, "mindstate": 0}

            if current.get("rank", 0) < baseline_rank and current.get("mindstate", 0) == 0:
                current = {"rank": baseline_rank, "mindstate": 0}

            skills[skill_name] = current

        if not migrated:
            self.db.starter_skill_baseline_migrated = True

        if self.get_profession() == "cleric":
            theurgy = dict(skills.get("theurgy") or {"rank": 0, "mindstate": 0})
            if int(theurgy.get("rank", 0) or 0) < 1 and int(theurgy.get("mindstate", 0) or 0) == 0:
                theurgy["rank"] = 1
                skills["theurgy"] = theurgy

        if skills != current_skills:
            self.db.skills = skills

    def ensure_core_defaults(self):
        if bool(getattr(self.ndb, "_core_defaults_ready", False)):
            return

        self._ensure_exp_skill_handler()
        self.ensure_identity_defaults()
        self.ensure_stat_defaults()
        self.ensure_race_defaults()
        self.ensure_resource_defaults()
        self.ensure_combat_defaults()
        self.ensure_equipment_defaults()
        self.ensure_injury_defaults()
        self.ensure_starter_skills()
        self.ensure_skill_defaults()
        self._seed_template_exp_skills()
        if getattr(self.db, "stealthed", None) is None:
            self.db.stealthed = False
        if getattr(self.db, "stealth_value", None) is None:
            self.db.stealth_value = 0
        if getattr(self.db, "last_hide_time", None) is None:
            self.db.last_hide_time = 0
        if getattr(self.db, "last_search_time", None) is None:
            self.db.last_search_time = 0
        if getattr(self.db, "perception_cache", None) is None:
            self.db.perception_cache = None
        if not isinstance(getattr(self.db, "awareness_state", None), Mapping):
            self.db.awareness_state = {}
        if not isinstance(getattr(self.db, "repeat_theft_targets", None), Mapping):
            self.db.repeat_theft_targets = {}
        if getattr(self.db, "pvp_open_until", None) is None:
            self.db.pvp_open_until = 0
        if getattr(self.db, "last_mark_target", None) is None:
            self.db.last_mark_target = None
        if getattr(self.db, "last_mark_time", None) is None:
            self.db.last_mark_time = 0
        if not isinstance(getattr(self.db, "contacts", None), Mapping):
            self.db.contacts = {}
        if getattr(self.db, "thief_reputation", None) is None:
            self.db.thief_reputation = 0
        if getattr(self.db, "wanted_level", None) is None:
            self.db.wanted_level = 0
        if getattr(self.db, "last_wanted_update", None) is None:
            self.db.last_wanted_update = 0
        if getattr(self.db, "guard_attention", None) is None:
            self.db.guard_attention = False
        if getattr(self.db, "detained", None) is None:
            self.db.detained = False
        if getattr(self.db, "detained_until", None) is None:
            self.db.detained_until = 0
        if getattr(self.db, "last_arrest_time", None) is None:
            self.db.last_arrest_time = 0
        if getattr(self.db, "last_surrender_time", None) is None:
            self.db.last_surrender_time = 0
        if getattr(self.db, "justice_hold_reason", None) is None:
            self.db.justice_hold_reason = None
        if getattr(self.db, "justice_flee_flag", None) is None:
            self.db.justice_flee_flag = False
        if getattr(self.db, "outstanding_fine", None) is None:
            self.db.outstanding_fine = 0
        if getattr(self.db, "fine_due", None) is None:
            self.db.fine_due = 0
        if getattr(self.db, "justice_incidents", None) is None:
            self.db.justice_incidents = []
        if getattr(self.db, "shop_heat", None) is None:
            self.db.shop_heat = 0
        if getattr(self.db, "shop_heat_updated_at", None) is None:
            self.db.shop_heat_updated_at = 0
        if not isinstance(getattr(self.db, "theft_attempt_log", None), Mapping):
            self.db.theft_attempt_log = {}
        if getattr(self.db, "exp_feedback", None) is None:
            self.db.exp_feedback = True
        if getattr(self.db, "circle", None) is None:
            self.db.circle = 1
        if "awareness" not in (self.db.states or {}):
            states = dict(self.db.states or {})
            states["awareness"] = "normal"
            self.db.states = states
        if not isinstance(getattr(self.db, "stealth_learning", None), Mapping):
            self.db.stealth_learning = {"pending": [], "attempts": {}, "last_contest": {}, "combat_state": False}
        if getattr(self.db, "empath_strain", None) is None:
            self.db.empath_strain = 0
        if getattr(self.db, "total_tips", None) is None:
            self.db.total_tips = 0
        if getattr(self.db, "last_tip_amount", None) is None:
            self.db.last_tip_amount = 0
        if getattr(self.db, "last_tip_time", None) is None:
            self.db.last_tip_time = 0.0
        if not isinstance(getattr(self.db, "tip_history", None), Mapping):
            self.db.tip_history = {}
        if getattr(self.db, "empath_reputation_score", None) is None:
            self.db.empath_reputation_score = 0
        if getattr(self.db, "last_perceive_time", None) is None:
            self.db.last_perceive_time = 0.0
        if getattr(self.db, "last_medical_decay_at", None) is None:
            self.db.last_medical_decay_at = 0.0
        if getattr(self.db, "last_critical_warning_at", None) is None:
            self.db.last_critical_warning_at = 0.0
        if getattr(self.db, "empath_overload_until", None) is None:
            self.db.empath_overload_until = 0.0
        if not isinstance(getattr(self.db, "empath_triage_context", None), Mapping):
            self.db.empath_triage_context = {}
        if getattr(self.db, "last_triage_scan_at", None) is None:
            self.db.last_triage_scan_at = 0.0

        self.ndb._core_defaults_ready = True

    def ensure_appearance_defaults(self):
        self.ensure_identity_defaults()
        self.ensure_resource_defaults()
        self.ensure_combat_defaults()

    def get_rendered_desc(self, viewer=None):
        from systems.appearance.renderer import render_appearance

        self.ensure_identity_defaults()
        return render_appearance(self, viewer)

    def get_hp(self):
        self.ensure_core_defaults()
        return self.db.hp, self.db.max_hp

    def set_hp(self, value):
        self.ensure_core_defaults()
        old_hp = int(self.db.hp or 0)
        self.db.hp = max(0, min(value, self.db.max_hp))
        if self.db.hp < old_hp:
            self.cancel_pending_cleric_ritual("Pain breaks your concentration.")
        if old_hp > 0 and (self.db.hp or 0) <= 0:
            if self.consume_resurrection_death_guard():
                self.db.hp = 1
                self.msg("Your returning life falters, but the rite holds for one heartbeat.")
            else:
                self.at_death(death_type="vitality")
        self.sync_empath_wounds_from_resources()
        self.sync_client_state()

    def ensure_all_defaults(self):
        self.ensure_core_defaults()

    def get_balance(self):
        self.ensure_all_defaults()
        return self.db.balance, self.db.max_balance

    def set_balance(self, value):
        self.ensure_all_defaults()
        self.db.balance = max(0, min(value, self.db.max_balance))
        self.sync_client_state()

    def get_fatigue(self):
        self.ensure_all_defaults()
        return self.db.fatigue, self.db.max_fatigue

    def set_fatigue(self, value):
        self.ensure_all_defaults()
        self.db.fatigue = max(0, min(value, self.db.max_fatigue))
        self.sync_empath_wounds_from_resources()
        self.sync_client_state()

    def get_unabsorbed_xp(self):
        self.ensure_core_defaults()
        return max(0, int(getattr(self.db, "unabsorbed_xp", 0) or 0))

    def adjust_unabsorbed_xp(self, amount):
        self.ensure_core_defaults()
        self.db.unabsorbed_xp = max(0, self.get_unabsorbed_xp() + int(amount or 0))
        self.sync_client_state()
        return self.db.unabsorbed_xp

    def spend_unabsorbed_xp(self, amount):
        cost = max(0, int(amount or 0))
        if cost <= 0:
            return True
        current = self.get_unabsorbed_xp()
        if current < cost:
            return False
        self.db.unabsorbed_xp = current - cost
        self.sync_client_state()
        return True

    def get_exp_debt(self):
        self.ensure_core_defaults()
        return max(0, int(getattr(self.db, "exp_debt", 0) or 0))

    def set_exp_debt(self, value):
        self.ensure_core_defaults()
        self.db.exp_debt = max(0, int(value or 0))
        self.sync_client_state()
        return self.db.exp_debt

    def adjust_exp_debt(self, amount):
        return self.set_exp_debt(self.get_exp_debt() + int(amount or 0))

    def reduce_exp_debt(self, amount, emit_clear_message=True):
        self.ensure_core_defaults()
        reduction = max(0, int(amount or 0))
        if reduction <= 0:
            return self.get_exp_debt()
        before = self.get_exp_debt()
        if before <= 0:
            return 0
        after = max(0, before - reduction)
        self.db.exp_debt = after
        self.sync_client_state()
        if emit_clear_message and before > 0 and after <= 0:
            self.msg("You feel your mind clearing as your experience debt fades.")
        return after

    def get_xp_debt_gain_multiplier(self):
        return 0.5 if self.get_exp_debt() > 0 else 1.0

    def capture_exp_debt_on_death(self, had_prior_penalty=False):
        self.ensure_core_defaults()
        current_field_exp = self.get_unabsorbed_xp()
        had_prior_penalty = bool(had_prior_penalty or self.get_exp_debt() > 0)
        if current_field_exp <= 0 and not had_prior_penalty:
            return 0
        multiplier = 1.25 if had_prior_penalty else 1.0
        protection = self.get_death_protection_state()
        if protection["active"]:
            multiplier *= float(protection["exp_debt_multiplier"])
        captured = int(round(current_field_exp * multiplier))
        if captured > 0:
            self.adjust_exp_debt(captured)
        self.db.unabsorbed_xp = 0
        self.sync_client_state()
        if captured > 0:
            self.msg("You feel your recent death weighing on your progress.")
        return captured

    def get_favor(self):
        self.ensure_core_defaults()
        self.refresh_favor_state(emit_message=False)
        current = getattr(self.db, "favor_current", None)
        if current is None:
            current = getattr(self.db, "favor", 0)
        maximum = self.get_favor_max()
        current = max(0, min(int(current or 0), maximum))
        self.db.favor_current = current
        self.db.favor = current
        return current

    def get_favor_max(self):
        self.ensure_core_defaults()
        maximum = max(1, int(getattr(self.db, "favor_max", 5) or 5))
        self.db.favor_max = maximum
        return maximum

    def msg_favor_change(self, delta, reason=None):
        delta_value = int(delta or 0)
        reason_key = str(reason or "").strip().lower()
        if delta_value > 0:
            if reason_key == "pray":
                self.msg("A faint sense of favor returns.")
            else:
                self.msg("You feel a small measure of favor return to you.")
            return
        if delta_value < 0:
            self.msg("A portion of your favor is spent.")

    def refresh_favor_state(self, emit_message=False, now=None):
        self.ensure_core_defaults()
        now = float(now or time.time())
        current = max(0, min(int(getattr(self.db, "favor_current", 0) or 0), self.get_favor_max()))
        if self.is_dead():
            self.db.favor_current = current
            self.db.favor = current
            return False
        last_decay = float(getattr(self.db, "last_favor_decay_at", 0.0) or 0.0)
        if last_decay <= 0.0:
            self.db.last_favor_decay_at = now
            self.db.favor_current = current
            self.db.favor = current
            return False
        interval = float(FAVOR_SYSTEM_CONFIG.get("favor_decay_seconds", 1800.0) or 1800.0)
        if current <= 1 or now < last_decay + interval:
            self.db.favor_current = current
            self.db.favor = current
            return False
        decay_steps = int((now - last_decay) // interval)
        if decay_steps <= 0:
            return False
        updated = max(1, current - decay_steps)
        self.db.last_favor_decay_at = last_decay + (decay_steps * interval)
        self.db.favor_current = updated
        self.db.favor = updated
        if emit_message and updated < current:
            self.msg("You feel your stored favor begin to fade.")
        self.sync_client_state()
        return updated != current

    def get_pray_cooldown_remaining(self, now=None):
        self.ensure_core_defaults()
        now = float(now or time.time())
        cooldown = float(FAVOR_SYSTEM_CONFIG.get("pray_cooldown_seconds", 60.0) or 60.0)
        last_pray = float(getattr(self.db, "last_pray_time", 0.0) or 0.0)
        if last_pray <= 0.0:
            return 0
        return max(0, int(math.ceil((last_pray + cooldown) - now)))

    def pray_for_favor(self):
        self.ensure_core_defaults()
        if self.is_dead():
            return False, "You are beyond such concerns."
        if self.is_in_combat():
            return False, "You cannot gather yourself for prayer in the middle of combat."
        remaining = self.get_pray_cooldown_remaining()
        if remaining > 0:
            return False, f"Your last prayer still lingers. Wait {remaining}s."
        current = self.get_favor()
        maximum = self.get_favor_max()
        if current >= maximum:
            return False, "Your favor is already full."
        gain = 2 if self.is_in_shrine() else 1
        updated = self.adjust_favor(gain, emit_message=True, reason="pray")
        self.db.last_pray_time = time.time()
        self.db.last_favor_decay_at = time.time()
        self.sync_client_state()
        if updated > current:
            if gain > 1 and updated - current > 1:
                return True, f"You kneel and pray. Favor rises to {updated}/{maximum}. The shrine answers more strongly here."
            return True, f"You kneel and pray. Favor rises to {updated}/{maximum}."
        return False, "Your prayer passes without effect."

    def set_favor(self, value, emit_message=False):
        self.ensure_core_defaults()
        before = self.get_favor()
        updated = max(0, min(self.get_favor_max(), int(value or 0)))
        self.db.favor_current = updated
        self.db.favor = updated
        if updated > before:
            self.db.last_favor_decay_at = time.time()
        if emit_message and updated != before:
            self.msg_favor_change(updated - before)
        self.sync_client_state()
        return updated

    def adjust_favor(self, amount, emit_message=False, reason=None):
        before = self.get_favor()
        updated = self.set_favor(before + int(amount or 0), emit_message=False)
        if emit_message and updated != before:
            self.msg_favor_change(updated - before, reason=reason)
        return updated

    def get_favor_state(self, favor=None):
        value = self.get_favor() if favor is None else max(0, int(favor or 0))
        if value <= 0:
            return "unprepared"
        if value <= 1:
            return "vulnerable"
        if value <= 2:
            return "prepared"
        return "anchored"

    def get_favor_state_message(self, favor=None):
        state = self.get_favor_state(favor=favor)
        return {
            "unprepared": "You feel exposed to what lies beyond.",
            "vulnerable": "You feel vulnerable before what lies beyond.",
            "prepared": "You feel reasonably prepared for death.",
            "anchored": "You feel strongly anchored to the divine.",
        }.get(state, "")

    def calculate_death_sting_severity(self, favor=None):
        stacks = max(0, min(DEATH_STING_MAX_STACKS, int(getattr(self.db, "death_sting", 0) or 0)))
        favor_value = self.get_favor() if favor is None else max(0, int(favor or 0))
        if stacks <= 1:
            severity = 0.10
        elif stacks <= 3:
            severity = 0.20
        else:
            severity = 0.30
        if favor_value <= 0:
            severity += 0.05
        elif favor_value >= 1:
            severity -= 0.03
        protection = self.get_death_protection_state()
        if protection["active"]:
            severity *= float(protection["sting_severity_scale"])
        return max(0.03, min(0.35, severity))

    def get_death_sting_count(self):
        self.ensure_core_defaults()
        return max(0, min(DEATH_STING_MAX_STACKS, int(getattr(self.db, "death_sting", 0) or 0)))

    def get_death_sting_recovery_label(self):
        count = self.get_death_sting_count()
        if count >= 4:
            return "severe"
        if count >= 2:
            return "moderate"
        if count >= 1:
            return "light"
        return "none"

    def refresh_death_sting(self, emit_message=False):
        self.ensure_core_defaults()
        active = bool(getattr(self.db, "death_sting_active", False) or self.get_death_sting_count() > 0)
        if not active:
            return False
        expires_at = float(getattr(self.db, "death_sting_end", 0.0) or 0.0)
        if expires_at > 0 and expires_at <= time.time():
            next_count = max(0, self.get_death_sting_count() - 1)
            self.db.death_sting = next_count
            if next_count <= 0:
                self.db.death_sting_active = False
                self.db.death_sting_end = 0.0
                self.db.death_sting_severity = 0.0
                self.db.death_sting_hp_cap_ratio = 1.0
                self.db.death_sting_recovery_label = "none"
                self.sync_client_state()
                if emit_message:
                    self.msg("You feel the last of death's grip release you.")
                return False
            self.db.death_sting_active = True
            self.db.death_sting_end = time.time() + DEATH_STING_DECAY_SECONDS
            self.db.death_sting_severity = self.calculate_death_sting_severity()
            self.db.death_sting_recovery_label = self.get_death_sting_recovery_label()
            self.db.death_sting_hp_cap_ratio = float(DEATH_STING_HP_CAPS.get(self.db.death_sting_recovery_label, 1.0))
            self.sync_client_state()
            if emit_message:
                self.msg("Death's grip loosens slightly.")
        return not self.is_dead() and active

    def is_death_sting_active(self):
        return self.refresh_death_sting(emit_message=False)

    def get_death_sting_severity(self):
        self.ensure_core_defaults()
        if self.is_death_sting_active():
            stored = float(getattr(self.db, "death_sting_severity", 0.0) or 0.0)
            if stored > 0:
                return stored
        return 0.0

    def get_death_sting_modifier(self):
        severity = self.get_death_sting_severity()
        return max(0.0, 1.0 - severity) if severity > 0 else 1.0

    def get_death_sting_time_remaining(self):
        if not self.is_death_sting_active():
            return 0
        expires_at = float(getattr(self.db, "death_sting_end", 0.0) or 0.0)
        return max(0, int(round(expires_at - time.time())))

    def get_death_sting_label(self):
        label = self.get_death_sting_recovery_label()
        if label == "severe":
            return "Severe"
        if label == "moderate":
            return "Moderate"
        if label == "light":
            return "Light"
        return "None"

    def apply_death_sting_recovery_effects(self, favor=None, via="depart"):
        self.ensure_core_defaults()
        if self.get_death_sting_count() <= 0:
            return "none"
        label = self.get_death_sting_recovery_label()
        severity = self.calculate_death_sting_severity(favor=favor)
        hp_cap_ratio = float(DEATH_STING_HP_CAPS.get(label, 1.0))
        if favor is not None and int(favor or 0) <= 0:
            hp_cap_ratio = max(0.6, hp_cap_ratio - 0.05)
        elif favor is not None and int(favor or 0) >= 1:
            hp_cap_ratio = min(0.95, hp_cap_ratio + 0.05)
        self.db.death_sting_active = True
        self.db.death_sting_severity = severity
        self.db.death_sting_end = time.time() + DEATH_STING_DECAY_SECONDS
        self.db.death_sting_hp_cap_ratio = hp_cap_ratio
        self.db.death_sting_recovery_label = label
        hp_cap = max(1, int(round((self.db.max_hp or 1) * hp_cap_ratio)))
        self.db.hp = min(int(self.db.hp or 0), hp_cap)
        if via == "depart":
            self.db.recovery_state = "weakened"
        if favor is not None and int(favor or 0) >= 1:
            self.msg("Your remaining favor softens the blow of death.")
        if label == "severe":
            self.msg("Death has left a deep mark on you.")
        else:
            self.msg("You feel the weight of death cling to you.")
        self.sync_client_state()
        return label

    def apply_death_sting_to_contest_value(self, base_value):
        value = float(base_value or 0.0)
        if not self.is_death_sting_active():
            return value
        return value * self.get_death_sting_modifier()

    def apply_death_sting_to_damage(self, base_damage):
        damage = float(base_damage or 0.0)
        if not self.is_death_sting_active():
            return damage
        return damage * self.get_death_sting_modifier()

    def get_death_status_lines(self):
        self.ensure_core_defaults()
        lines = [f"State: {str(getattr(self.db, 'life_state', LIFE_STATE_ALIVE) or LIFE_STATE_ALIVE).title()}", f"Favor: {self.get_favor()}"]
        if self.get_exp_debt() > 0:
            lines.append(f"Experience Debt: {self.get_exp_debt()}")
        if self.is_dead():
            corpse = self.get_death_corpse()
            if hasattr(self, "get_depart_mode"):
                lines.append(f"Depart Path: {self.get_depart_mode(corpse=corpse).title()}")
            soul_state = self.get_soul_state()
            if isinstance(soul_state, Mapping):
                lines.append(f"Soul: {self.get_soul_strength_label(soul_state=soul_state).title()}")
                lines.append(f"Soul Strength: {int(round(float(soul_state.get('strength', 0.0) or 0.0)))}/100")
            if corpse:
                if hasattr(corpse, "get_condition_tier"):
                    lines.append(f"Corpse Condition: {corpse.get_condition_tier()} ({int(round(corpse.get_condition()))}/100)")
                if hasattr(corpse, "get_memory_remaining"):
                    lines.append(f"Memory: {corpse.get_memory_state().title()}")
                    memory_remaining = int(round(corpse.get_memory_remaining()))
                    if memory_remaining > 0:
                        lines.append(f"Memory Decay: {memory_remaining}s")
                prep_stacks = int(getattr(corpse.db, "preparation_stacks", 0) or 0)
                if prep_stacks > 0:
                    lines.append(f"Preparation: {prep_stacks}")
                if bool(getattr(corpse.db, "stabilized", False)):
                    lines.append("Corpse: Stabilized")
                remaining = max(0, int(round(float(getattr(corpse.db, 'decay_time', 0.0) or 0.0) - time.time())))
                if remaining > 0:
                    lines.append(f"Corpse Decay: {remaining}s")
        if self.is_death_sting_active():
            lines.append("You are suffering from Death's Sting.")
            lines.append(f"Severity: {self.get_death_sting_label()} ({int(round(self.get_death_sting_severity() * 100))}% penalty)")
            lines.append(f"Time Remaining: {self.get_death_sting_time_remaining()}s")
        last_recovery = str(getattr(self.db, "last_recovery_type", "") or "").strip()
        if last_recovery:
            detail = f"Last Recovery: {last_recovery.title()}"
            quality = str(getattr(self.db, "last_recovery_quality", "") or "").strip()
            if quality:
                detail += f" ({quality.title()})"
            helper = str(getattr(self.db, "last_recovery_helper", "") or "").strip()
            if helper:
                detail += f" via {helper}"
            lines.append(detail)
        grave = self.get_owned_grave()
        if grave:
            item_count = len(list(grave.contents))
            lines.append(f"Grave Recovery: Available here ({item_count} item{'s' if item_count != 1 else ''})")
        fragility = self.get_state("resurrection_fragility")
        if fragility:
            lines.append(f"Recovery: {str(fragility.get('label', 'fragile')).title()}")
        instability = self.get_state("resurrection_instability")
        if instability:
            lines.append("State: Unstable")
        return lines

    def get_corpse_status_lines(self):
        corpse = self.get_death_corpse()
        if not corpse:
            return ["You have no linked corpse to inspect."]
        lines = [f"Corpse: {corpse.key}"]
        lines.append(f"Condition: {corpse.get_condition_tier()} ({int(round(corpse.get_condition()))}/100)")
        if hasattr(corpse, "get_decay_remaining"):
            lines.append(f"Time Until Decay: {int(round(corpse.get_decay_remaining()))}s")
        if hasattr(corpse, "get_memory_remaining"):
            lines.append(f"Memory: {corpse.get_memory_state().title()} ({int(round(corpse.get_memory_remaining()))}s)")
        if getattr(corpse, "location", None):
            lines.append(f"Location: {corpse.location.key}")
        if bool(getattr(corpse.db, "irrecoverable", False)):
            lines.append("Body State: Irrecoverable")
        prep = int(getattr(corpse.db, "preparation_stacks", 0) or 0)
        if prep > 0:
            lines.append(f"Preparation: {prep}")
        return lines

    def get_depart_preview_lines(self, corpse=None):
        corpse = corpse or self.get_death_corpse()
        snapshot = self.get_corpse_favor_detail_snapshot(corpse) if corpse else self.get_favor_death_snapshot() or {}
        available_favor = int(snapshot.get("favor_before", 0) or 0)
        lines = [f"You have {available_favor} favor{'s' if available_favor != 1 else ''}.", "Available options:"]
        for mode, cost in (("grave", 0), ("coins", 2), ("items", 2), ("full", 3)):
            chosen = self.get_depart_mode(corpse=corpse, requested_mode=mode)
            if chosen is None:
                continue
            default_text = " [default]" if mode == self.get_depart_mode(corpse=corpse) else ""
            lines.append(f"- depart {mode} (cost: {cost}){default_text}")
        lines.append("Type DEPART <mode> to choose, or DEPART DEFAULT to take the default path.")
        return lines

    def get_death_inspect_lines(self, target=None):
        subject = target or self
        corpse = subject.get_death_corpse() if hasattr(subject, "get_death_corpse") else None
        soul = subject.get_soul_state() if hasattr(subject, "get_soul_state") else None
        lines = [f"Target: {subject.key}"]
        lines.append(f"State: {str(getattr(subject.db, 'life_state', LIFE_STATE_ALIVE) or LIFE_STATE_ALIVE).title()}")
        lines.append(f"Favor: {subject.get_favor() if hasattr(subject, 'get_favor') else 0}")
        lines.append(f"XP Debt: {subject.get_exp_debt() if hasattr(subject, 'get_exp_debt') else 0}")
        lines.append(f"Last Death Time: {float(getattr(subject.db, 'last_death_time', 0.0) or 0.0):.0f}")
        if hasattr(subject, "get_recovery_consent_lines"):
            lines.extend(subject.get_recovery_consent_lines())
        if corpse:
            lines.append(f"Corpse ID: #{corpse.id}")
            lines.append(f"Corpse Condition: {int(round(corpse.get_condition()))}/100")
            lines.append(f"Corpse Decay: {int(round(corpse.get_decay_remaining()))}s")
            lines.append(f"Corpse Memory: {int(round(corpse.get_memory_remaining()))}s")
            lines.append(f"Corpse Irrecoverable: {bool(getattr(corpse.db, 'irrecoverable', False))}")
        if isinstance(soul, Mapping):
            lines.append(f"Soul Strength: {int(round(float(soul.get('strength', 0.0) or 0.0)))}/100")
            lines.append(f"Soul Recoverable: {bool(soul.get('recoverable', False))}")
        return lines

    def get_death_emote(self):
        return random.choice(
            [
                f"{self.key} collapses suddenly, life leaving their body.",
                f"{self.key} staggers, then falls motionless.",
                f"{self.key} crumples to the ground.",
            ]
        )

    def get_favor_cost_multiplier(self, favor=None):
        value = self.get_favor() if favor is None else max(0, int(favor or 0))
        config = FAVOR_SYSTEM_CONFIG
        multiplier = 1.0 + (value * float(config["scaling_factor"]))
        if value > int(config["soft_cap_threshold"]):
            multiplier += (value - int(config["soft_cap_threshold"])) * float(config["soft_cap_bonus_per_favor"])
        return multiplier * self.get_favor_level_modifier()

    def get_favor_level_modifier(self):
        return 1.0 + (max(0, int(getattr(self.db, "profession_rank", 1) or 1)) - 1) * 0.02

    def get_next_favor_cost(self, favor=None):
        return max(1, int(round(float(FAVOR_SYSTEM_CONFIG["base_cost"]) * self.get_favor_cost_multiplier(favor=favor))))

    def is_in_shrine(self):
        room = getattr(self, "location", None)
        if not room:
            return False
        if hasattr(room, "is_shrine_room"):
            return bool(room.is_shrine_room())
        if bool(getattr(getattr(room, "db", None), "is_shrine", False)):
            return True
        tags = getattr(room, "tags", None)
        return bool(tags and tags.get("shrine"))

    def pray_at_shrine(self):
        if not self.is_in_shrine():
            return False, "You feel no divine presence here."
        now = time.time()
        self.db.deaths_since_last_shrine = 0
        self.db.last_prayed_shrine_at = now
        favor_changed = False
        devotion_changed = False
        favor_interval = float(FAVOR_SYSTEM_CONFIG.get("shrine_regen_interval", 300.0) or 300.0)
        last_regen = float(getattr(self.db, "last_shrine_favor_regen_at", 0.0) or 0.0)
        if self.get_favor() < self.get_favor_max() and (last_regen <= 0.0 or now - last_regen >= favor_interval):
            self.set_favor(self.get_favor() + 1)
            self.db.last_shrine_favor_regen_at = now
            favor_changed = True
        if self.has_devotion_access():
            devotion_interval = float(CLERIC_DEVOTION_CONFIG.get("shrine_regen_interval", 60.0) or 60.0)
            last_devotion = float(getattr(self.db, "last_shrine_devotion_regen_at", 0.0) or 0.0)
            if self.get_devotion() < self.get_devotion_max() and (last_devotion <= 0.0 or now - last_devotion >= devotion_interval):
                self.adjust_devotion(int(CLERIC_DEVOTION_CONFIG.get("shrine_regen_amount", 5) or 5), sync=False)
                self.db.last_shrine_devotion_regen_at = now
                devotion_changed = True
        self.sync_client_state()
        if favor_changed and devotion_changed:
            return True, f"You kneel and prepare an offering. Favor and devotion return. Devotion: {self.get_devotion()}/{self.get_devotion_max()}."
        if devotion_changed:
            return True, f"You kneel and pray until your connection steadies. Devotion: {self.get_devotion()}/{self.get_devotion_max()}."
        if favor_changed:
            return True, "You kneel and prepare an offering. A measure of favor returns."
        if self.get_favor() >= self.get_favor_max() and (not self.has_devotion_access() or self.get_devotion() >= self.get_devotion_max()):
            return True, "You kneel and prepare an offering. Your favor and devotion are already full."
        remaining = []
        if self.get_favor() < self.get_favor_max():
            remaining.append(max(1, int(math.ceil(favor_interval - (now - last_regen)))))
        if self.has_devotion_access() and self.get_devotion() < self.get_devotion_max():
            devotion_interval = float(CLERIC_DEVOTION_CONFIG.get("shrine_regen_interval", 60.0) or 60.0)
            last_devotion = float(getattr(self.db, "last_shrine_devotion_regen_at", 0.0) or 0.0)
            remaining.append(max(1, int(math.ceil(devotion_interval - (now - last_devotion)))))
        wait_time = min(remaining) if remaining else 1
        return True, f"You kneel and prepare an offering. The shrine remains quiet for another {wait_time}s."

    def has_devotion_access(self):
        return bool(hasattr(self, "is_profession") and self.is_profession("cleric"))

    def get_devotion_max(self):
        self.ensure_core_defaults()
        maximum = int(CLERIC_DEVOTION_CONFIG["max_devotion"] if self.has_devotion_access() else 0)
        self.db.devotion_max = maximum
        self.db.max_devotion = maximum
        return maximum

    def get_devotion(self):
        self.ensure_core_defaults()
        if not self.has_devotion_access():
            self.db.devotion_current = 0
            self.db.devotion = 0
            self.db.devotion_max = 0
            self.db.max_devotion = 0
            return 0
        maximum = self.get_devotion_max()
        current = getattr(self.db, "devotion_current", None)
        if current is None:
            current = getattr(self.db, "devotion", CLERIC_DEVOTION_CONFIG["baseline"])
        current = max(0, min(maximum, int(current or 0)))
        self.db.devotion_current = current
        self.db.devotion = current
        return current

    def set_devotion(self, value, sync=True):
        self.ensure_core_defaults()
        maximum = self.get_devotion_max()
        updated = max(0, min(maximum, int(value or 0)))
        self.db.devotion_current = updated
        self.db.devotion = updated
        self.db.devotion_max = maximum
        self.db.max_devotion = maximum
        if sync:
            self.sync_client_state()
        return updated

    def adjust_devotion(self, amount, sync=True):
        return self.set_devotion(self.get_devotion() + int(amount or 0), sync=sync)

    def spend_devotion(self, amount, failure_message=None):
        cost = max(0, int(amount or 0))
        if cost <= 0:
            return True, self.get_devotion()
        if self.get_devotion() < cost:
            return False, str(failure_message or "You do not have the devotion required to continue the rite.")
        return True, self.adjust_devotion(-cost, sync=False)

    def get_cleric_specialization(self):
        if not self.is_profession("cleric"):
            return None
        specialization = str(getattr(self.db, "specialization", "") or "").strip().lower()
        if specialization not in {"stabilizer", "restorer", "binder"}:
            return None
        return specialization

    def get_cleric_specialization_label(self, specialization=None):
        specialization = str(specialization or self.get_cleric_specialization() or "").strip().lower()
        return {
            "stabilizer": "Stabilizer",
            "restorer": "Restorer",
            "binder": "Binder",
        }.get(specialization, "None")

    def get_cleric_stage_specialization(self, stage):
        return CLERIC_STAGE_SPECIALIZATIONS.get(str(stage or "").strip().lower())

    def get_cleric_specialization_unlock_message(self, specialization):
        return {
            "stabilizer": "Your practice settles into the patterns of stabilization.",
            "restorer": "Your instincts begin to favor restorative rites.",
            "binder": "Your focus sharpens around binding the soul.",
        }.get(str(specialization or "").strip().lower(), "")

    def get_cleric_specialization_match_feedback(self, stage):
        specialization = self.get_cleric_specialization()
        if not specialization or specialization != self.get_cleric_stage_specialization(stage):
            return ""
        return {
            "stabilizer": "Your practiced hands steady the work.",
            "restorer": "The rite comes more naturally to you.",
            "binder": "Your focus aligns cleanly with the ritual.",
        }.get(specialization, "")

    def announce_cleric_specialization_unlock(self, specialization):
        specialization = str(specialization or "").strip().lower()
        if not specialization or bool(getattr(self.db, "specialization_announced", False)):
            return ""
        self.db.specialization_announced = True
        return self.get_cleric_specialization_unlock_message(specialization)

    def maybe_define_cleric_specialization(self, stage):
        if not self.is_profession("cleric") or self.get_cleric_specialization():
            return self.get_cleric_specialization(), False
        stage_key = str(stage or "").strip().lower()
        repeats = dict(getattr(self.db, "cleric_stage_repeats", {}) or {})
        repeats[stage_key] = int(repeats.get(stage_key, 0) or 0) + 1
        self.db.cleric_stage_repeats = repeats
        specialization = self.get_cleric_stage_specialization(stage_key)
        if specialization and int(repeats.get(stage_key, 0) or 0) >= 2:
            self.db.specialization = specialization
            return specialization, True
        return self.get_cleric_specialization(), False

    def get_cleric_quality_band_label(self, quality):
        value = max(0, int(quality or 0))
        if value >= 10:
            return "best"
        if value >= 6:
            return "light"
        if value >= 3:
            return "moderate"
        return "severe"

    def get_other_pending_cleric_stage_participants(self, corpse, action):
        if not corpse:
            return []
        action_key = str(action or "").strip().lower()
        room = getattr(corpse, "location", None)
        participants = set()
        for obj in list(getattr(room, "contents", []) or []):
            if obj == self:
                continue
            pending = getattr(getattr(obj, "ndb", None), "pending_cleric_ritual_action", None)
            if not isinstance(pending, dict) or not bool(pending.get("active", False)):
                continue
            if str(pending.get("action", "") or "").strip().lower() != action_key:
                continue
            if int(pending.get("corpse_id", 0) or 0) != int(getattr(corpse, "id", 0) or 0):
                continue
            obj_id = int(getattr(obj, "id", 0) or 0)
            if obj_id > 0:
                participants.add(obj_id)
        return sorted(participants)

    def get_cleric_stage_delay(self, corpse, action):
        action_key = str(action or "").strip().lower()
        base_delay = float(CLERIC_CORPSE_RITUAL_ACTIONS.get(action_key, {}).get("delay", FAVOR_SYSTEM_CONFIG.get("revive_delay_seconds", 5.0)) or 5.0)
        if action_key == "revive":
            base_delay = float(FAVOR_SYSTEM_CONFIG.get("revive_delay_seconds", 5.0) or 5.0)
        if not corpse or not hasattr(corpse, "get_group_stage_bonus_count"):
            return base_delay
        pending_ids = self.get_other_pending_cleric_stage_participants(corpse, action_key)
        participant_count = corpse.get_group_stage_bonus_count(action_key if action_key != "revive" else "bind", pending_character_ids=pending_ids)
        bonus_factor = min(0.5, participant_count * 0.25)
        return max(base_delay * 0.5, base_delay / (1.0 + bonus_factor))

    def get_cleric_group_support_count(self, corpse):
        if not corpse:
            return 0
        participants = set(list(getattr(corpse.db, "ritual_participants", []) or []))
        room = getattr(corpse, "location", None)
        for obj in list(getattr(room, "contents", []) or []):
            pending = getattr(getattr(obj, "ndb", None), "pending_cleric_ritual_action", None)
            if not isinstance(pending, dict) or not bool(pending.get("active", False)):
                continue
            if int(pending.get("corpse_id", 0) or 0) != int(getattr(corpse, "id", 0) or 0):
                continue
            obj_id = int(getattr(obj, "id", 0) or 0)
            if obj_id > 0:
                participants.add(obj_id)
        return len(participants)

    def apply_cleric_group_contribution(self, corpse, action):
        if not corpse:
            return {"joined": False, "duplicate": False, "quality_bonus": 0, "specialization_bonus": 0}
        joined = False
        if hasattr(corpse, "add_ritual_participant"):
            _, joined = corpse.add_ritual_participant(self)
        duplicate = False
        added_stage = True
        if hasattr(corpse, "add_stage_contributor"):
            _, added_stage = corpse.add_stage_contributor(action, self)
            duplicate = not added_stage
        quality_bonus = 0
        if added_stage and hasattr(corpse, "add_quality_bonus_contributor"):
            _, added_quality = corpse.add_quality_bonus_contributor(self)
            if added_quality and hasattr(corpse, "adjust_ritual_quality"):
                corpse.adjust_ritual_quality(1)
                quality_bonus = 1
        specialization_bonus = 0
        specialization = self.get_cleric_specialization()
        desired = self.get_cleric_stage_specialization(action)
        if added_stage and specialization and specialization == desired and hasattr(corpse, "mark_specialization_bonus_stage"):
            _, added_specialization = corpse.mark_specialization_bonus_stage(action)
            if added_specialization and hasattr(corpse, "adjust_ritual_quality"):
                corpse.adjust_ritual_quality(1)
                specialization_bonus = 1
        return {
            "joined": joined,
            "duplicate": duplicate,
            "quality_bonus": quality_bonus,
            "specialization_bonus": specialization_bonus,
        }

    def get_pending_cleric_stage_actor_ids(self, corpse, action, include_self=False):
        if not corpse:
            return []
        action_key = str(action or "").strip().lower()
        room = getattr(corpse, "location", None)
        actor_ids = set()
        for obj in list(getattr(room, "contents", []) or []):
            if not include_self and obj == self:
                continue
            pending = getattr(getattr(obj, "ndb", None), "pending_cleric_ritual_action", None)
            if not isinstance(pending, dict) or not bool(pending.get("active", False)):
                continue
            if str(pending.get("action", "") or "").strip().lower() != action_key:
                continue
            if int(pending.get("corpse_id", 0) or 0) != int(getattr(corpse, "id", 0) or 0):
                continue
            obj_id = int(getattr(obj, "id", 0) or 0)
            if obj_id > 0:
                actor_ids.add(obj_id)
        return sorted(actor_ids)

    def emit_ritual_message(self, corpse, key, message, cooldown=2.0, exclude=None):
        if not corpse or not message:
            return False
        now = time.time()
        cache = dict(getattr(getattr(corpse, "ndb", None), "ritual_last_msg_time", {}) or {})
        if now - float(cache.get(key, 0.0) or 0.0) <= float(cooldown or 0.0):
            return False
        room = getattr(corpse, "location", None)
        if room:
            room.msg_contents(message, exclude=list(exclude or []))
        cache[key] = now
        corpse.ndb.ritual_last_msg_time = cache
        return True

    def should_emit_ritual_join_message(self, corpse, stage, actor=None, cooldown=6.0):
        if not corpse:
            return False
        actor = actor or self
        actor_id = int(getattr(actor, "id", 0) or 0)
        if actor_id <= 0:
            return False
        now = time.time()
        cache = dict(getattr(getattr(corpse, "ndb", None), "ritual_last_join_msg", {}) or {})
        stage_key = str(stage or "").strip().lower()
        stage_cache = dict(cache.get(stage_key, {}) or {})
        last_time = float(stage_cache.get(str(actor_id), 0.0) or 0.0)
        if now - last_time <= float(cooldown or 0.0):
            return False
        stage_cache[str(actor_id)] = now
        cache[stage_key] = stage_cache
        corpse.ndb.ritual_last_join_msg = cache
        return True

    def should_emit_ritual_specialization_join_message(self, corpse, stage, specialization):
        if not corpse:
            return False
        stage_key = str(stage or "").strip().lower()
        specialization_key = str(specialization or "").strip().lower()
        if not specialization_key:
            return False
        cache = dict(getattr(getattr(corpse, "ndb", None), "ritual_specialization_join_msg", {}) or {})
        announced = set(list(cache.get(stage_key, []) or []))
        if specialization_key in announced:
            return False
        announced.add(specialization_key)
        cache[stage_key] = sorted(announced)
        corpse.ndb.ritual_specialization_join_msg = cache
        return True

    def get_cleric_stage_start_room_message(self, action):
        return {
            "prepare": f"{self.key} begins preparing the body.",
            "stabilize": f"{self.key} begins a stabilization vigil.",
            "restore": f"{self.key} begins restoring the corpse's fading pattern.",
            "bind": f"{self.key} begins binding the wandering soul.",
        }.get(str(action or "").strip().lower(), "")

    def get_cleric_stage_join_room_message(self, action):
        action_key = str(action or "").strip().lower()
        specialization = self.get_cleric_specialization()
        expected = self.get_cleric_stage_specialization(action_key)
        if specialization and specialization == expected:
            return {
                "prepare": "A trained stabilizer joins the rite.",
                "stabilize": "A trained stabilizer joins the rite.",
                "restore": "A practiced restorer reinforces the work.",
                "bind": "A skilled binder lends focus to the ritual.",
            }.get(action_key, "")
        return {
            "prepare": f"{self.key} joins the preparation rite.",
            "stabilize": f"{self.key} joins the stabilization rite.",
            "restore": f"{self.key} joins the restorative rite.",
            "bind": f"{self.key} joins the binding rite.",
        }.get(action_key, "")

    def get_cleric_stage_completion_room_message(self, action):
        return {
            "prepare": "The body settles into ritual readiness.",
            "stabilize": "The fading pattern steadies.",
            "restore": "The corpse's memory coheres once more.",
            "bind": "The soul's tether tightens and holds.",
        }.get(str(action or "").strip().lower(), "")

    def get_cleric_dead_owner_transition_message(self, action):
        return {
            "prepare": "You feel distant hands preparing your body.",
            "stabilize": "You feel your fading self steady slightly.",
            "restore": "Something of you is being restored.",
            "bind": "A firm pull anchors you back toward your body.",
        }.get(str(action or "").strip().lower(), "")

    def notify_dead_owner_of_ritual_transition(self, corpse, action):
        owner = corpse.get_owner() if corpse and hasattr(corpse, "get_owner") else None
        if owner and owner.is_dead():
            owner.msg(self.get_cleric_dead_owner_transition_message(action))

    def get_cleric_revive_outcome_feedback(self, quality_label):
        return {
            "severe": "The body lurches back to life, strained and unstable.",
            "moderate": "The soul returns, but the bond is imperfect.",
            "light": "Life returns with steady breath and form.",
            "best": "The soul returns cleanly, guided by a flawless rite.",
        }.get(str(quality_label or "severe").strip().lower(), "The body lurches back to life, strained and unstable.")

    def get_devotion_state(self):
        devotion = self.get_devotion()
        if devotion < 15:
            return "distant"
        if devotion < 35:
            return "faint"
        if devotion < 60:
            return "steady"
        if devotion < 85:
            return "clear"
        return "radiant"

    def get_devotion_state_message(self):
        messages = {
            "distant": "Your connection feels distant.",
            "faint": "You feel only a faint answering presence.",
            "steady": "Your connection to the divine feels steady.",
            "clear": "The divine answers clearly.",
            "radiant": "Radiant certainty settles over your prayers.",
        }
        return messages.get(self.get_devotion_state(), "")

    def get_cleric_magic_modifier(self):
        if not self.is_profession("cleric"):
            return 1.0
        devotion = self.get_devotion()
        theurgy = self.get_skill("theurgy")
        modifier = 1.0 + min(0.15, theurgy / 200.0)
        if devotion < 15:
            modifier *= 0.8
        elif devotion < 35:
            modifier *= 0.92
        elif devotion >= 85:
            modifier *= 1.12
        elif devotion >= 60:
            modifier *= 1.05
        return modifier

    def get_corpse_memory_extension(self):
        return 60 + max(30, int(self.get_skill("theurgy") * 4))

    def get_theurgy_training_difficulty(self, base=12):
        return max(int(base or 0), int(base or 0) + int(self.get_skill("theurgy") * 0.75))

    def can_work_corpse(self, corpse):
        if not corpse or getattr(corpse, "location", None) != getattr(self, "location", None):
            return False, "That corpse is not here."
        if not getattr(getattr(corpse, "db", None), "is_corpse", False):
            return False, "You can only use that rite on a corpse."
        if self.is_profession("cleric"):
            return True, ""
        if hasattr(corpse, "is_recovery_allowed") and not corpse.is_recovery_allowed(self):
            return False, "You do not have permission to work with that corpse."
        owner = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        if owner and hasattr(owner, "notify_recovery_consent_use"):
            owner.notify_recovery_consent_use(self)
        return True, ""

    def get_cleric_assess_quality_label(self, quality):
        value = max(0, int(quality or 0))
        if value >= 10:
            return "Excellent"
        if value >= 6:
            return "Strong"
        if value >= 3:
            return "Unsteady"
        return "Poor"

    def get_cleric_ritual_state_label(self, corpse):
        state = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        return str(state or "unprepared").replace("_", " ").title()

    def get_cleric_assess_readiness_line(self, corpse):
        state = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        readiness_map = {
            "unprepared": "The body must be prepared before the rite can progress.",
            "prepared": "The rite is ready for stabilization.",
            "stabilized": "The rite is ready for restoration.",
            "restored": "The rite is ready for binding.",
            "bound": "The final rite may now be attempted.",
        }
        readiness = readiness_map.get(str(state or "unprepared"), "The body must be prepared before the rite can progress.")
        warning = self.get_corpse_survivability_warning(corpse)
        if warning:
            return f"{readiness} {warning}"
        return readiness

    def get_cleric_assess_blockers(self, corpse):
        blockers = []
        if not bool(getattr(corpse.db, "is_valid_for_revive", True)) or str(getattr(corpse.db, "death_type", "vitality") or "vitality") == "spirit":
            blockers.append("This death cannot be reversed by the rite.")
        if bool(getattr(corpse.db, "irrecoverable", False)):
            blockers.append("The body is too far gone to sustain another rite.")
        favor_snapshot = corpse.get_favor_snapshot() if hasattr(corpse, "get_favor_snapshot") else 0
        if int(favor_snapshot or 0) < 1:
            blockers.append("No favor remains to guide the soul.")
        if hasattr(corpse, "has_viable_memory") and not corpse.has_viable_memory():
            blockers.append("The corpse's memory has faded.")
        if not self.can_revive_in_room(room=getattr(corpse, "location", None)):
            blockers.append("This place is not suitable for the final rite.")
        ritual_state = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        if ritual_state != "bound" or not bool(getattr(corpse.db, "soul_bound", False)):
            blockers.append("The soul has not yet been bound.")
        return blockers

    def get_cleric_assess_stage_counts(self, corpse):
        if hasattr(corpse, "get_stage_contributors"):
            contributors = corpse.get_stage_contributors()
        else:
            contributors = dict(getattr(corpse.db, "stage_contributors", {}) or {})
        return {
            "prepare": len(list(contributors.get("prepare", []) or [])),
            "stabilize": len(list(contributors.get("stabilize", []) or [])),
            "restore": len(list(contributors.get("restore", []) or [])),
            "bind": len(list(contributors.get("bind", []) or [])),
        }

    def can_view_named_cleric_contributors(self, corpse):
        if not corpse:
            return False
        if hasattr(corpse, "get_ritual_participants") and int(getattr(self, "id", 0) or 0) in set(corpse.get_ritual_participants()):
            return True
        owner = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        if owner and owner == self:
            return True
        return bool(hasattr(corpse, "_has_admin_access") and corpse._has_admin_access(self))

    def get_cleric_assess_stage_names(self, corpse):
        contributors = corpse.get_stage_contributors() if hasattr(corpse, "get_stage_contributors") else dict(getattr(corpse.db, "stage_contributors", {}) or {})
        names_by_stage = {}
        for stage in ("prepare", "stabilize", "restore", "bind"):
            stage_names = []
            for char_id in list(contributors.get(stage, []) or []):
                if int(char_id or 0) <= 0:
                    continue
                result = search_object(f"#{int(char_id)}")
                if result:
                    stage_names.append(str(getattr(result[0], "key", "") or f"#{int(char_id)}"))
            names_by_stage[stage] = stage_names
        return names_by_stage

    def get_cleric_assess_specialized_support_lines(self, corpse):
        contributor_ids = set()
        contributors = corpse.get_stage_contributors() if hasattr(corpse, "get_stage_contributors") else dict(getattr(corpse.db, "stage_contributors", {}) or {})
        for stage_ids in list(contributors.values()):
            for char_id in list(stage_ids or []):
                if int(char_id or 0) > 0:
                    contributor_ids.add(int(char_id))
        lines = []
        for role in ("stabilizer", "restorer", "binder"):
            for char_id in contributor_ids:
                result = search_object(f"#{char_id}")
                actor = result[0] if result else None
                if actor and hasattr(actor, "get_cleric_specialization") and actor.get_cleric_specialization() == role:
                    if not lines:
                        lines.append("Specialized Support:")
                    lines.append(f"  {self.get_cleric_specialization_label(role)} present")
                    break
        return lines

    def perceive_cleric_corpse(self, corpse):
        if not self.is_profession("cleric"):
            return False, ["You do not know how to read a corpse that way."]
        ok, message = self.can_work_corpse(corpse)
        if not ok:
            return False, [message]
        lines = [f"You study {corpse.key} through a veil of divine perception."]
        condition_state = corpse.get_resurrection_condition_state() if hasattr(corpse, "get_resurrection_condition_state") else corpse.get_condition_tier().upper()
        condition = int(round(corpse.get_condition())) if hasattr(corpse, "get_condition") else int(getattr(corpse.db, "condition", 0) or 0)
        favor_snapshot = corpse.get_favor_snapshot() if hasattr(corpse, "get_favor_snapshot") else 0
        favor_present = int(favor_snapshot or 0) >= 1
        if bool(getattr(corpse.db, "irrecoverable", False)):
            condition_state = "IRRECOVERABLE"
        lines.append(f"Condition: {condition_state.title()} ({condition}/100)")
        lines.append(f"Favor Snapshot: {int(favor_snapshot or 0)}")
        lines.append(f"Favor: {'Present' if favor_present else 'Absent'}")
        ritual_state = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        lines.append(f"State: {ritual_state.title()}")
        if hasattr(corpse, "get_memory_state"):
            lines.append(f"Memory: {corpse.get_memory_state().title()}")
        lines.append(f"Memory Stability: {'Stable' if bool(getattr(corpse.db, 'memory_stable', False)) else 'Fading'}")
        lines.append(f"Soul Binding: {'Bound' if bool(getattr(corpse.db, 'soul_bound', False)) else 'Unbound'}")
        failures = int(getattr(corpse.db, "ritual_failures", 0) or 0)
        quality = int(getattr(corpse.db, "ritual_quality", 0) or 0)
        participant_count = len(list(getattr(corpse.db, "ritual_participants", []) or []))
        lines.append(f"Failures: {failures}")
        lines.append(f"Quality: {quality} ({self.get_cleric_quality_band_label(quality).title()})")
        if participant_count > 0:
            lines.append(f"Participants: {participant_count}")
        if hasattr(corpse, "get_memory_remaining"):
            lines.append(f"Memory Window: {int(round(corpse.get_memory_remaining()))}s")
        if hasattr(corpse, "get_decay_remaining"):
            lines.append(f"Decay Window: {int(round(corpse.get_decay_remaining()))}s")
        prep_stacks = int(getattr(corpse.db, "preparation_stacks", 0) or 0)
        if prep_stacks > 0:
            lines.append(f"Preparation: {prep_stacks} ritual layer{'s' if prep_stacks != 1 else ''}")
        viability = "Viable" if not bool(getattr(corpse.db, "irrecoverable", False)) and favor_present and condition >= 25 and getattr(corpse, "has_viable_memory", lambda: True)() else "Perilous"
        lines.append(f"Resurrection Outlook: {viability}")
        lines.append(f"Survivability: {self.get_corpse_revive_survivability_band(corpse).upper()}")
        warning = self.get_corpse_survivability_warning(corpse)
        if warning:
            lines.append(warning)
        self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(12))
        return True, lines

    def can_revive_in_room(self, room=None):
        room = room or self.location
        if not room:
            return False
        if hasattr(room, "is_no_resurrection_zone") and room.is_no_resurrection_zone():
            return False
        if hasattr(room, "is_shrine_room") and room.is_shrine_room():
            return True
        if hasattr(room, "is_consecrated_room") and room.is_consecrated_room():
            return True
        return bool(getattr(getattr(room, "db", None), "consecrated", False))

    def assess_cleric_corpse(self, corpse):
        if not self.is_profession("cleric"):
            return False, ["You do not know how to read a corpse that way."]
        ok, message = self.can_work_corpse(corpse)
        if not ok:
            return False, [message]
        stage_counts = self.get_cleric_assess_stage_counts(corpse)
        participant_count = len(corpse.get_ritual_participants()) if hasattr(corpse, "get_ritual_participants") else len(list(getattr(corpse.db, "ritual_participants", []) or []))
        failures = corpse.get_ritual_failures() if hasattr(corpse, "get_ritual_failures") else int(getattr(corpse.db, "ritual_failures", 0) or 0)
        quality_value = corpse.get_ritual_quality() if hasattr(corpse, "get_ritual_quality") else int(getattr(corpse.db, "ritual_quality", 0) or 0)
        quality_label = self.get_cleric_assess_quality_label(quality_value)
        blockers = self.get_cleric_assess_blockers(corpse)
        lines = [f"You assess {corpse.key} through the discipline of the rite."]
        lines.append(f"Ritual State: {self.get_cleric_ritual_state_label(corpse)}")
        lines.append(f"Participants: {participant_count}")
        lines.append(f"Failures: {failures}")
        lines.append(f"Quality: {quality_label}")
        lines.append("Contributors:")
        lines.append(f"  Prepare: {stage_counts['prepare']}")
        lines.append(f"  Stabilize: {stage_counts['stabilize']}")
        lines.append(f"  Restore: {stage_counts['restore']}")
        lines.append(f"  Bind: {stage_counts['bind']}")
        if self.can_view_named_cleric_contributors(corpse):
            stage_names = self.get_cleric_assess_stage_names(corpse)
            lines.append("Named Contributors:")
            lines.append(f"  Prepare: {', '.join(stage_names['prepare']) if stage_names['prepare'] else 'None'}")
            lines.append(f"  Stabilize: {', '.join(stage_names['stabilize']) if stage_names['stabilize'] else 'None'}")
            lines.append(f"  Restore: {', '.join(stage_names['restore']) if stage_names['restore'] else 'None'}")
            lines.append(f"  Bind: {', '.join(stage_names['bind']) if stage_names['bind'] else 'None'}")
            lines.extend(self.get_cleric_assess_specialized_support_lines(corpse))
        if participant_count > 1:
            lines.append("The rite is being strengthened by multiple hands.")
        lines.append(self.get_cleric_assess_readiness_line(corpse))
        lines.append(f"Survivability: {self.get_corpse_revive_survivability_band(corpse).upper()}")
        warning = self.get_corpse_survivability_warning(corpse)
        if warning:
            lines.append(warning)
        if blockers:
            lines.append("Revive Blockers:")
            for blocker in blockers:
                lines.append(f"  {blocker}")
        else:
            lines.append("No immediate blocker stands against the final rite.")
        self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(12))
        return True, lines

    def get_corpse_wounds(self, corpse):
        return get_corpse_wounds_payload(corpse)

    def build_corpse_wound_payload(self):
        self.ensure_core_defaults()
        return normalize_corpse_wounds({
            "empath": copy.deepcopy(self.get_empath_wounds()),
            "injuries": copy.deepcopy(dict(getattr(self.db, "injuries", {}) or {})),
            "baseline": {
                "external": max(0, sum(max(0, int((part or {}).get("external", 0) or 0)) for part in dict(getattr(self.db, "injuries", {}) or {}).values())),
                "internal": max(0, sum(max(0, int((part or {}).get("internal", 0) or 0)) for part in dict(getattr(self.db, "injuries", {}) or {}).values())),
                "bleeding": max(0, int(self.get_empath_wound("bleeding") or 0)),
                "vitality": max(0, int(self.get_empath_wound("vitality") or 0)),
            },
        })

    def apply_corpse_wound_payload(self, payload, sync=True):
        self.ensure_core_defaults()
        normalized = normalize_corpse_wounds(payload)
        self.db.wounds = copy.deepcopy(normalized.get("empath", {}))
        self.db.injuries = copy.deepcopy(normalized.get("injuries", {}))
        self.sync_resources_from_empath_wounds()
        self.update_bleed_state()
        if sync:
            self.sync_client_state()
        return normalized

    def get_corpse_internal_total(self, corpse):
        wounds = self.get_corpse_wounds(corpse)
        return max(0, sum(max(0, int((part or {}).get("internal", 0) or 0)) for part in wounds.get("injuries", {}).values()))

    def get_corpse_bleed_total(self, corpse):
        wounds = self.get_corpse_wounds(corpse)
        return max(0, sum(max(0, int((part or {}).get("bleed", 0) or 0)) for part in wounds.get("injuries", {}).values()))

    def get_effective_corpse_revive_loads(self, corpse):
        internal = self.get_corpse_internal_total(corpse)
        bleed = self.get_corpse_bleed_total(corpse)
        penalties = corpse.get_decay_stage_penalties() if corpse and hasattr(corpse, "get_decay_stage_penalties") else {}
        return {
            "internal": max(0, internal),
            "bleed": max(0, bleed),
            "decay_stage": int(penalties.get("stage", 0) or 0),
            "decay_label": str(penalties.get("label", "Fresh") or "Fresh"),
            "favor_penalty": 0,
            "chance_penalty": 0.0,
        }

    def get_corpse_revive_survivability_band(self, corpse):
        if not corpse or not getattr(getattr(corpse, "db", None), "is_corpse", False):
            return "stable"
        wounds = self.get_corpse_wounds(corpse)
        if is_stable_corpse_wounds(wounds):
            return "stable"
        if is_near_stable_corpse_wounds(wounds):
            return "critical"
        return "unsafe"

    def is_corpse_revive_survivable(self, corpse):
        if not corpse or not getattr(getattr(corpse, "db", None), "is_corpse", False):
            return True
        return self.get_corpse_revive_survivability_band(corpse) in {"stable", "critical"}

    def get_corpse_survivability_warning(self, corpse):
        band = self.get_corpse_revive_survivability_band(corpse)
        if band == "stable":
            return "This body is stable enough."
        if band == "critical":
            return "This body may not survive."
        return "This body may not survive the rite. This body will not survive the rite without better preparation."

    def preserve_corpse(self, corpse):
        if not self.is_profession("cleric"):
            return False, "Only a cleric can shield lingering memories that way."
        ok, message = self.can_work_corpse(corpse)
        if not ok:
            return False, message
        if not hasattr(corpse, "has_viable_memory") or not corpse.has_viable_memory():
            return False, "The corpse's memories have already faded beyond your reach."
        attunement_cost = 6
        if not self.spend_attunement(attunement_cost):
            return False, "You lack the attunement to preserve those memories."
        extension = self.get_corpse_memory_extension()
        remaining = corpse.extend_memory(extension)
        self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(16))
        if hasattr(corpse, "update_condition_description"):
            corpse.update_condition_description()
        return True, f"You shield the lingering memories from fading. Memory window: {int(round(remaining))}s."

    def prepare_corpse(self, corpse):
        if not self.is_profession("cleric"):
            return False, "Only a cleric can restore coherence to the dead that way."
        return self.start_cleric_corpse_ritual(corpse, "prepare")

    def get_cleric_ritual_profile(self, ritual_name):
        ritual = str(ritual_name or "prayer").strip().lower()
        if ritual == "pray":
            ritual = "prayer"
        return CLERIC_DEVOTION_CONFIG["rituals"].get(ritual)

    def get_cleric_ritual_cooldown_remaining(self, ritual_name):
        ritual = str(ritual_name or "prayer").strip().lower()
        if ritual == "pray":
            ritual = "prayer"
        profile = self.get_cleric_ritual_profile(ritual)
        if not profile:
            return 0.0
        timestamps = dict(getattr(self.db, "cleric_ritual_timestamps", None) or {})
        last_used = float(timestamps.get(ritual, 0.0) or 0.0)
        cooldown = float(profile.get("cooldown", 0.0) or 0.0)
        return max(0.0, cooldown - (time.time() - last_used))

    def perform_cleric_ritual(self, ritual_name):
        if not self.is_profession("cleric"):
            return False, "Only a cleric can maintain that rite."
        if self.is_dead():
            return False, "The dead cannot maintain devotional rites."
        ritual = str(ritual_name or "prayer").strip().lower() or "prayer"
        if ritual == "pray":
            ritual = "prayer"
        profile = self.get_cleric_ritual_profile(ritual)
        if not profile:
            return False, "You know only the rites: pray, pray focus, and pray devotion."
        ok, message = self.pray_at_shrine()
        if ok:
            self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(12))
        return ok, message

    def get_commune_profile(self, commune_name):
        return CLERIC_DEVOTION_CONFIG["communes"].get(str(commune_name or "").strip().lower())

    def get_resurrection_devotion_profile(self):
        devotion = self.get_devotion()
        config = CLERIC_DEVOTION_CONFIG["resurrection"]
        if devotion < int(config["low_threshold"]):
            return {
                "label": "strained",
                "failure_chance": 0.3,
                "hp_scale": 0.85,
                "exp_scale": 0.85,
                "sting_duration_scale": 1.15,
                "sting_severity_scale": 1.15,
            }
        if devotion >= int(config["high_threshold"]):
            return {
                "label": "radiant",
                "failure_chance": 0.03,
                "hp_scale": 1.1,
                "exp_scale": 1.1,
                "sting_duration_scale": 0.85,
                "sting_severity_scale": 0.85,
            }
        return {
            "label": "steady",
            "failure_chance": 0.1,
            "hp_scale": 1.0,
            "exp_scale": 1.0,
            "sting_duration_scale": 1.0,
            "sting_severity_scale": 1.0,
        }

    def get_resurrection_devotion_cost(self, corpse=None, snapshot=None):
        condition = 100.0
        if corpse is not None and hasattr(corpse, "get_condition"):
            condition = float(corpse.get_condition())
        elif corpse is not None:
            condition = float(getattr(getattr(corpse, "db", None), "condition", 100.0) or 100.0)
        favor_before = int(((snapshot or {}).get("favor_before", 0) if isinstance(snapshot, Mapping) else 0) or 0)
        damage_penalty = max(0, int((100 - condition) / 10))
        favor_discount = min(6, max(0, favor_before // 3))
        return max(8, 12 + damage_penalty - favor_discount)

    def commune_with_divine(self, commune_name, target=None):
        if not self.is_profession("cleric"):
            return False, "Only a cleric can call upon a commune."
        if self.is_dead():
            return False, "The dead cannot commune with the divine that way."

        commune_key = str(commune_name or "").strip().lower()
        profile = self.get_commune_profile(commune_key)
        if not profile:
            return False, "You may commune solace, ward, or vigil."

        cost = int(profile.get("cost", 0) or 0)
        if self.get_devotion() < cost:
            return False, f"You lack the devotion for that commune. {self.get_devotion_state_message()}"

        if commune_key == "solace":
            missing = max(0, int((self.db.max_attunement or 0) - (self.db.attunement or 0)))
            if missing <= 0:
                return False, "The commune finds nothing in you that needs soothing."
            restored = min(missing, 10 + max(0, self.get_profession_rank() * 2))
            self.db.attunement = min(int(self.db.max_attunement or 0), int(self.db.attunement or 0) + restored)
            self.adjust_devotion(-cost, sync=False)
            self.sync_client_state()
            self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(14))
            return True, "A quiet warmth settles through you, restoring your spiritual reserve."

        if commune_key == "ward":
            strength = max(1, 1 + int(self.get_profession_rank() / 3))
            duration = 8 + max(0, int(self.get_profession_rank() / 2))
            self.apply_warding_barrier(self, "commune ward", strength, duration)
            self.adjust_devotion(-cost, sync=False)
            self.sync_client_state()
            self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(16))
            return True, "You commune for protection, and a pale ward settles around you."

        corpse = target
        if corpse is None and self.location:
            corpses = [obj for obj in self.location.contents if getattr(getattr(obj, "db", None), "is_corpse", False)]
            corpse = corpses[0] if len(corpses) == 1 else None
        if not corpse or not getattr(getattr(corpse, "db", None), "is_corpse", False):
            return False, "Commune vigil requires a corpse here."
        if hasattr(corpse, "is_recovery_allowed") and not corpse.is_recovery_allowed(self):
            return False, "You do not have permission to watch over that corpse."
        owner = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        if owner and hasattr(owner, "notify_recovery_consent_use"):
            owner.notify_recovery_consent_use(self)
        corpse.db.stabilized = True
        if hasattr(corpse, "adjust_condition"):
            corpse.adjust_condition(5 + max(0, self.get_profession_rank()))
        corpse.db.devotional_vigil_until = time.time() + 300
        self.adjust_devotion(-cost, sync=False)
        self.sync_client_state()
        self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(18))
        return True, "You keep a brief vigil over the corpse, easing decay and steadying what remains."

    def process_cleric_tick(self):
        return True

    def get_cleric_ritual_failure_message(self, corpse, action, interrupted=False, regressed=False):
        state = corpse.get_ritual_state() if corpse and hasattr(corpse, "get_ritual_state") else "unprepared"
        failures = corpse.get_ritual_failures() if corpse and hasattr(corpse, "get_ritual_failures") else int(getattr(getattr(corpse, "db", None), "ritual_failures", 0) or 0)
        if failures >= 3 or not bool(getattr(getattr(corpse, "db", None), "is_valid_for_revive", True)):
            return "The soul slips further away, beyond the reach of another rite."
        if action == "revive":
            return "The ritual falters, and the soul slips further away."
        if state == "restored":
            return "The ritual falters, and the soul slips further away."
        if interrupted:
            if regressed:
                return "The ritual slips backward under the strain."
            return "The rite holds, but your part in it is lost."
        if regressed:
            return f"The ritual slips backward to a {state} state."
        return "The rite strains, but does not collapse."

    def apply_cleric_ritual_failure(self, corpse, action, interrupted=False):
        if not corpse or not getattr(getattr(corpse, "db", None), "is_corpse", False):
            return "The ritual falters."
        state_before = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        if hasattr(corpse, "record_ritual_failure"):
            corpse.record_ritual_failure(1)
        else:
            corpse.db.ritual_failures = int(getattr(corpse.db, "ritual_failures", 0) or 0) + 1
        if self.get_cleric_group_support_count(corpse) <= 1 and hasattr(corpse, "regress_ritual_state"):
            corpse.regress_ritual_state(action=action)
        state_after = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        return self.get_cleric_ritual_failure_message(corpse, action, interrupted=interrupted, regressed=(state_before != state_after))

    def get_cleric_revive_quality_profile(self, corpse):
        ritual_quality = corpse.get_ritual_quality() if hasattr(corpse, "get_ritual_quality") else max(0, min(15, int(getattr(corpse.db, "ritual_quality", 0) or 0)))
        failure_count = corpse.get_ritual_failures() if hasattr(corpse, "get_ritual_failures") else max(0, int(getattr(corpse.db, "ritual_failures", 0) or 0))
        effective_quality = max(0, min(15, ritual_quality + 1))
        selected_index = len(CLERIC_RITUAL_OUTCOME_BANDS) - 1
        for index, profile in enumerate(CLERIC_RITUAL_OUTCOME_BANDS):
            if effective_quality >= int(profile["minimum"]):
                selected_index = index
                break
        if failure_count > 0:
            selected_index = min(len(CLERIC_RITUAL_OUTCOME_BANDS) - 1, selected_index + 1)
        profile = dict(CLERIC_RITUAL_OUTCOME_BANDS[selected_index])
        profile["ritual_quality"] = ritual_quality
        profile["effective_quality"] = effective_quality
        profile["failure_count"] = failure_count
        return profile

    def sacrifice_for_favor(self, offered_amount):
        if not self.is_in_shrine():
            return False, ["You feel no divine presence here."]
        try:
            amount = max(0, int(offered_amount or 0))
        except (TypeError, ValueError):
            return False, ["Offer how much experience?"]
        if amount <= 0:
            return False, ["Offer how much experience?"]
        available = self.get_unabsorbed_xp()
        if available <= 0:
            return False, ["You lack the experience to offer."]
        if available < amount:
            return False, ["You do not have that much unabsorbed experience to offer."]
        next_cost = self.get_next_favor_cost()
        if amount < next_cost:
            return False, ["Your offering is not enough to earn favor."]

        spent = 0
        gained = 0
        remaining_offer = amount
        current_favor = self.get_favor()
        while remaining_offer > 0 and self.get_unabsorbed_xp() > 0:
            cost = self.get_next_favor_cost(favor=current_favor)
            if remaining_offer < cost or self.get_unabsorbed_xp() < cost:
                break
            self.spend_unabsorbed_xp(cost)
            spent += cost
            remaining_offer -= cost
            gained += 1
            current_favor += 1
        if gained <= 0:
            if self.get_unabsorbed_xp() < self.get_next_favor_cost():
                return False, ["You lack the experience to offer."]
            return False, ["Your offering is not enough to earn favor."]
        self.set_favor(current_favor)
        self.db.deaths_since_last_shrine = 0
        lines = ["You offer your experience to the divine and feel their favor grow."]
        if gained > 1:
            lines.append(f"Your offering earns {gained} favor.")
        lines.append(f"Favor: {self.get_favor()}  Unabsorbed XP: {self.get_unabsorbed_xp()}")
        if remaining_offer > 0 and self.get_unabsorbed_xp() < self.get_next_favor_cost():
            lines.append("You lack the experience to offer more right now.")
        return True, lines

    def get_soul_decay_rate(self, favor=None):
        value = self.get_favor() if favor is None else max(0, int(favor or 0))
        config = FAVOR_SYSTEM_CONFIG
        return float(config["soul_decay_base"]) / (1.0 + (value * float(config["soul_decay_modifier"])))

    def get_soul_strength_floor(self, favor=None):
        value = self.get_favor() if favor is None else max(0, int(favor or 0))
        config = FAVOR_SYSTEM_CONFIG
        return int(config["soul_strength_base"]) + (value * int(config["soul_strength_bonus"]))

    def get_soul_state(self):
        self.ensure_core_defaults()
        state = getattr(self.db, "soul_state", None)
        if state is None and self.is_dead() and isinstance(self.get_favor_death_snapshot(), Mapping):
            state = self.initialize_soul_state(snapshot=self.get_favor_death_snapshot())
        return dict(state) if isinstance(state, Mapping) else None

    def get_soul_strength_label(self, soul_state=None):
        state = soul_state if isinstance(soul_state, Mapping) else self.get_soul_state()
        if not isinstance(state, Mapping):
            return "lost"
        strength = max(0.0, float(state.get("strength", 0.0) or 0.0))
        if not bool(state.get("recoverable", False)) or strength <= 0:
            return "lost"
        if strength >= 70:
            return "strong"
        if strength >= 35:
            return "fading"
        return "barely present"

    def get_soul_recoverability_message(self, soul_state=None):
        label = self.get_soul_strength_label(soul_state=soul_state)
        return {
            "strong": "The soul is strong.",
            "fading": "The soul is fading.",
            "barely present": "The soul is barely present.",
            "lost": "The soul can no longer be reached.",
        }.get(label, "The soul cannot be read.")

    def calculate_initial_soul_strength(self, snapshot=None):
        snapshot = snapshot if isinstance(snapshot, Mapping) else self.get_favor_death_snapshot() or {}
        favor_before = max(0, int(snapshot.get("favor_before", 0) or 0))
        injuries = dict(getattr(self.db, "injuries", None) or {})
        trauma = 0.0
        for part in injuries.values():
            if not isinstance(part, Mapping):
                continue
            trauma += float(part.get("external", 0) or 0)
            trauma += float(part.get("internal", 0) or 0)
            trauma += float(part.get("bruise", 0) or 0) * 0.5
            trauma += float(part.get("bleed", 0) or 0) * 2.0
        trauma_penalty = min(45.0, trauma / 25.0)
        debt_penalty = min(12.0, float(self.get_exp_debt()) / 100.0)
        strength = 55.0 + (favor_before * 2.5) - trauma_penalty - debt_penalty
        return max(0.0, min(100.0, strength))

    def initialize_soul_state(self, snapshot=None):
        snapshot = snapshot if isinstance(snapshot, Mapping) else self.get_favor_death_snapshot() or {}
        strength = self.calculate_initial_soul_strength(snapshot=snapshot)
        soul_state = {
            "owner_id": int(self.id or 0),
            "strength": strength,
            "location": "spirit_plane",
            "recoverable": bool((snapshot.get("resurrection") or {}).get("can_resurrect", False)) and strength > 0,
            "decay_rate": float(snapshot.get("soul_decay_rate", self.get_soul_decay_rate(snapshot.get("favor_before", 0))) or 0.0),
            "captured_at": time.time(),
            "last_decay_at": time.time(),
        }
        self.db.soul_state = soul_state
        return dict(soul_state)

    def process_soul_tick(self):
        if not self.is_dead():
            return False
        soul_state = self.get_soul_state()
        if not isinstance(soul_state, Mapping):
            return False
        if not bool(soul_state.get("recoverable", False)):
            return False
        now = time.time()
        last_decay = float(soul_state.get("last_decay_at", soul_state.get("captured_at", now)) or now)
        elapsed = max(0.0, now - last_decay)
        if elapsed < 1.0:
            return False
        decay_rate = max(0.05, float(soul_state.get("decay_rate", 0.0) or 0.0))
        updated = dict(soul_state)
        updated["strength"] = max(0.0, float(updated.get("strength", 0.0) or 0.0) - (elapsed * decay_rate))
        updated["last_decay_at"] = now
        if updated["strength"] <= 0:
            updated["strength"] = 0.0
            updated["recoverable"] = False
        self.db.soul_state = updated
        return True

    def sense_soul_from_corpse(self, corpse):
        if not self.is_profession("cleric"):
            return False, ["Only a cleric can search for a soul that way."]
        ok, message = self.can_work_corpse(corpse)
        if not ok:
            return False, [message]
        owner = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        if not owner:
            return False, ["That corpse holds no soul you can identify."]
        soul_state = owner.get_soul_state() if hasattr(owner, "get_soul_state") else None
        if not isinstance(soul_state, Mapping):
            return False, ["You feel only silence where the soul should be."]
        lines = [f"You search beyond {corpse.key}, listening for the soul bound to it."]
        lines.append(self.get_soul_recoverability_message(soul_state=soul_state))
        lines.append(f"Soul Strength: {int(round(float(soul_state.get('strength', 0.0) or 0.0)))}/100")
        if bool(soul_state.get("recoverable", False)):
            lines.append("The soul remains recoverable.")
        else:
            lines.append("The soul has slipped beyond your reach.")
        self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(15))
        return True, lines

    def get_resurrection_favor_profile(self, favor=None):
        value = self.get_favor() if favor is None else max(0, int(favor or 0))
        config = FAVOR_SYSTEM_CONFIG
        low_favor = value <= int(config["low_favor_threshold"])
        return {
            "success_modifier": round(value * float(config["resurrection_success_bonus"]), 3),
            "cost_reduction": round(value * float(config["resurrection_cost_reduction"]), 3),
            "quality_modifier": round(value * float(config["resurrection_quality_bonus"]), 3),
            "failure_bias": round(float(config["low_favor_failure_bias"]) if low_favor else 0.0, 3),
            "can_resurrect": value > 0,
        }

    def get_resurrection_quality_profile(self, favor_before=None):
        value = self.get_favor() if favor_before is None else max(0, int(favor_before or 0))
        for threshold, profile in RESURRECTION_QUALITY_PROFILES:
            if value >= threshold:
                result = dict(profile)
                result["favor_before"] = value
                return result
        return {
            "label": "none",
            "hp_ratio": float(FAVOR_SYSTEM_CONFIG["resurrection_restore_hp_ratio"]),
            "sting_duration_scale": 1.0,
            "sting_severity_scale": 1.0,
            "exp_restore_scale": 0.5,
            "favor_before": value,
        }

    def get_corpse_favor_detail_snapshot(self, corpse):
        snapshot = corpse.get_favor_detail_snapshot() if corpse and hasattr(corpse, "get_favor_detail_snapshot") else None
        if isinstance(snapshot, Mapping):
            return dict(snapshot)
        favor_before = corpse.get_favor_snapshot() if corpse and hasattr(corpse, "get_favor_snapshot") else 0
        return {
            "favor_before": int(favor_before or 0),
            "resurrection": {"can_resurrect": int(favor_before or 0) >= 1},
        }

    def get_res_success_chance(self, favor):
        favor_value = max(0, int(favor or 0))
        if favor_value <= 0:
            return 0.0
        return min(0.25 + (favor_value * 0.15), 0.95)

    def roll_resurrection_success(self, favor, corpse=None, caster=None):
        base_chance = self.get_res_success_chance(favor)
        chance = base_chance
        band = "stable"
        decay_stage = 0
        if corpse is not None:
            loads = self.get_effective_corpse_revive_loads(corpse)
            band = self.get_corpse_revive_survivability_band(corpse)
            decay_stage = int(loads.get("decay_stage", 0) or 0)
            chance -= float(loads.get("chance_penalty", 0.0) or 0.0)
            if band == "critical":
                chance -= 0.08
            elif band == "unsafe":
                chance -= 0.22
        chance = max(0.0, min(0.95, chance))
        roll = random.random()
        success = roll < chance
        detail = {
            "favor": max(0, int(favor or 0)),
            "base_chance": base_chance,
            "chance": chance,
            "roll": roll,
            "success": success,
            "survivability_band": band,
            "decay_stage": decay_stage,
        }
        if corpse is not None:
            corpse.db.last_resurrection_roll = dict(detail)
        if caster is not None:
            caster.msg(
                f"Resurrection chance roll: favor={detail['favor']} base={base_chance:.2f} final={chance:.2f} band={band.upper()} decay={decay_stage} roll={roll:.2f} -> {'SUCCESS' if success else 'FAILURE'}."
            )
        return detail

    def get_resurrection_stabilization_state(self):
        state = getattr(self.db, "res_stabilization", None)
        return dict(state) if isinstance(state, Mapping) else None

    def begin_resurrection_stabilization(self, band="stable"):
        band_key = str(band or "stable").strip().lower() or "stable"
        profile = {"ticks_remaining": 1, "bleed_multiplier": 1.0, "internal_pause_ticks": 0, "death_guard_ticks": 1}
        state = {
            "band": band_key,
            "ticks_remaining": int(profile["ticks_remaining"]),
            "bleed_multiplier": float(profile["bleed_multiplier"]),
            "internal_pause_ticks": int(profile["internal_pause_ticks"]),
            "death_guard_ticks": int(profile["death_guard_ticks"]),
        }
        self.db.res_stabilization = state
        self.db.just_revived = True
        self.db.revive_protection_ticks = int(profile["death_guard_ticks"])
        return dict(state)

    def get_resurrection_bleed_multiplier(self):
        state = self.get_resurrection_stabilization_state()
        if not state:
            return 1.0
        return max(0.1, min(1.0, float(state.get("bleed_multiplier", 1.0) or 1.0)))

    def should_pause_resurrection_internal_decay(self):
        state = self.get_resurrection_stabilization_state()
        if not state:
            return False
        return int(state.get("internal_pause_ticks", 0) or 0) > 0

    def consume_resurrection_death_guard(self):
        state = self.get_resurrection_stabilization_state()
        if not state or int(state.get("death_guard_ticks", 0) or 0) <= 0:
            self.db.revive_protection_ticks = 0
            return False
        state["death_guard_ticks"] = max(0, int(state.get("death_guard_ticks", 0) or 0) - 1)
        self.db.res_stabilization = state
        self.db.revive_protection_ticks = int(state.get("death_guard_ticks", 0) or 0)
        return True

    def process_resurrection_stabilization_tick(self):
        state = self.get_resurrection_stabilization_state()
        if not state:
            self.db.just_revived = False
            self.db.revive_protection_ticks = 0
            return False
        state["ticks_remaining"] = max(0, int(state.get("ticks_remaining", 0) or 0) - 1)
        state["internal_pause_ticks"] = max(0, int(state.get("internal_pause_ticks", 0) or 0) - 1)
        if state["ticks_remaining"] <= 0:
            self.db.res_stabilization = None
            self.db.just_revived = False
            self.db.revive_protection_ticks = 0
        else:
            self.db.res_stabilization = state
            self.db.just_revived = int(state.get("death_guard_ticks", 0) or 0) > 0
            self.db.revive_protection_ticks = int(state.get("death_guard_ticks", 0) or 0)
        return True

    def calculate_resurrection_quality_score(self, corpse=None, caster=None, snapshot=None, soul_state=None):
        snapshot = snapshot if isinstance(snapshot, Mapping) else self.get_favor_death_snapshot() or {}
        soul_state = soul_state if isinstance(soul_state, Mapping) else self.get_soul_state() or {}
        favor_before = max(0, int(snapshot.get("favor_before", 0) or 0))
        condition = float(corpse.get_condition() if corpse and hasattr(corpse, "get_condition") else getattr(getattr(corpse, "db", None), "condition", 0.0) or 0.0)
        soul_strength = max(0.0, min(100.0, float(soul_state.get("strength", 0.0) or 0.0)))
        devotion = caster.get_devotion() if caster is not None and hasattr(caster, "get_devotion") else 0
        score = min(100.0, favor_before * 3.0)
        score += condition * 0.28
        score += soul_strength * 0.24
        score += devotion * 0.18
        if corpse is not None:
            score += min(12.0, int(getattr(corpse.db, "preparation_stacks", 0) or 0) * 3.0)
            score += min(6.0, int(getattr(corpse.db, "preserve_stacks", 0) or 0) * 1.5)
        return max(0.0, min(100.0, score))

    def get_resurrection_quality_result(self, corpse=None, caster=None, snapshot=None, soul_state=None):
        score = self.calculate_resurrection_quality_score(corpse=corpse, caster=caster, snapshot=snapshot, soul_state=soul_state)
        for threshold, profile in RESURRECTION_QUALITY_PROFILES:
            if score >= threshold:
                result = dict(profile)
                result["score"] = score
                return result
        result = dict(RESURRECTION_QUALITY_PROFILES[-1][1])
        result["score"] = score
        return result

    def apply_resurrection_aftereffects(self, quality):
        label = str((quality or {}).get("label", "stable") or "stable").lower()
        self.clear_state("resurrection_fragility")
        self.clear_state("resurrection_instability")
        self.db.resurrection_vitality_cap_ratio = 1.0
        if label == "perfect":
            return
        if label == "stable":
            self.db.resurrection_vitality_cap_ratio = 0.95
            return
        if label == "fragile":
            self.db.resurrection_vitality_cap_ratio = 0.75
            self.db.fatigue = min(int(self.db.max_fatigue or 100), max(int(self.db.fatigue or 0), 35))
            self.set_state("resurrection_fragility", {"duration": 20, "label": "fragile", "hp_cap_ratio": 0.75})
            self.db.hp = min(int(self.db.hp or 0), max(1, int(round((self.db.max_hp or 1) * 0.75))))
            return
        self.db.resurrection_vitality_cap_ratio = 0.6
        self.db.fatigue = min(int(self.db.max_fatigue or 100), max(int(self.db.fatigue or 0), 50))
        self.set_state("resurrection_fragility", {"duration": 30, "label": "flawed", "hp_cap_ratio": 0.6})
        self.set_state("resurrection_instability", {"duration": 18, "label": "unstable", "penalty": 0.15})
        self.db.hp = min(int(self.db.hp or 0), max(1, int(round((self.db.max_hp or 1) * 0.6))))
        injuries = dict(self.db.injuries or {})
        for part_name in ["head", "chest", "abdomen"]:
            part = dict(injuries.get(part_name) or {})
            if not part:
                continue
            part["bruise"] = min(int(part.get("max", 100) or 100), int(part.get("bruise", 0) or 0) + 8)
            injuries[part_name] = part
        self.db.injuries = injuries

    def process_resurrection_recovery_tick(self):
        changed = False
        fragility = self.get_state("resurrection_fragility")
        if fragility:
            updated = dict(fragility)
            updated["duration"] = int(updated.get("duration", 0) or 0) - 1
            if updated["duration"] <= 0:
                self.clear_state("resurrection_fragility")
                self.db.resurrection_vitality_cap_ratio = 1.0
            else:
                self.set_state("resurrection_fragility", updated)
            changed = True
        instability = self.get_state("resurrection_instability")
        if instability:
            updated = dict(instability)
            updated["duration"] = int(updated.get("duration", 0) or 0) - 1
            if updated["duration"] <= 0:
                self.clear_state("resurrection_instability")
            else:
                self.set_state("resurrection_instability", updated)
            changed = True
        return changed

    def _normalize_recovery_consent_entries(self):
        self.ensure_core_defaults()
        raw_entries = list(getattr(self.db, "recovery_consent", None) or [])
        now = time.time()
        normalized = {}
        changed = False
        for entry in raw_entries:
            target_id = 0
            expires_at = 0.0
            if isinstance(entry, Mapping):
                try:
                    target_id = int(entry.get("id", 0) or 0)
                except (TypeError, ValueError):
                    target_id = 0
                try:
                    expires_at = float(entry.get("expires_at", 0.0) or 0.0)
                except (TypeError, ValueError):
                    expires_at = 0.0
            else:
                try:
                    target_id = int(entry)
                except (TypeError, ValueError):
                    target_id = 0
            if target_id <= 0:
                changed = True
                continue
            if expires_at > 0 and expires_at <= now:
                changed = True
                continue
            current = normalized.get(target_id)
            if current is None or expires_at > float(current.get("expires_at", 0.0) or 0.0):
                normalized[target_id] = {"id": target_id, "expires_at": expires_at}
            if not isinstance(entry, Mapping):
                changed = True
        entries = [normalized[target_id] for target_id in sorted(normalized)]
        if changed or raw_entries != entries:
            self.db.recovery_consent = entries
        return entries

    def get_recovery_consent_ids(self):
        return {int(entry["id"]) for entry in self._normalize_recovery_consent_entries()}

    def get_recovery_consent_lines(self):
        entries = self._normalize_recovery_consent_entries()
        if not entries:
            return ["Recovery Consent: None"]
        lines = ["Recovery Consent:"]
        now = time.time()
        for entry in entries:
            target_id = int(entry.get("id", 0) or 0)
            result = search_object(f"#{target_id}") if target_id > 0 else []
            name = result[0].key if result else f"#{target_id}"
            expires_at = float(entry.get("expires_at", 0.0) or 0.0)
            if expires_at > now:
                lines.append(f"- {name} ({int(round(expires_at - now))}s remaining)")
            else:
                lines.append(f"- {name}")
        return lines

    def notify_recovery_consent_use(self, actor, action_text="begins assisting with your remains"):
        if not actor or actor == self or not self.is_recovery_consented(actor):
            return False
        self.msg(f"{actor.key} {action_text}.")
        return True

    def is_recovery_consented(self, other):
        other_id = int(getattr(other, "id", 0) or 0)
        return other_id > 0 and other_id in self.get_recovery_consent_ids()

    def sync_recovery_permissions(self):
        allowed = sorted(self.get_recovery_consent_ids() | {int(self.id or 0)})
        corpse = self.get_death_corpse()
        if corpse:
            corpse.db.recovery_allowed = allowed
        grave = self.get_owned_grave()
        if grave:
            grave.db.recovery_allowed = allowed
        return allowed

    def grant_recovery_consent(self, target, duration=None):
        if not target or int(getattr(target, "id", 0) or 0) <= 0:
            return False, "You can only grant consent to a present character."
        if target == self:
            return False, "You already have access to your own remains."
        entries = {int(entry["id"]): dict(entry) for entry in self._normalize_recovery_consent_entries()}
        expires_at = 0.0
        if duration is not None:
            expires_at = time.time() + max(1, int(duration or 0))
        entries[int(target.id)] = {"id": int(target.id), "expires_at": expires_at}
        self.db.recovery_consent = [entries[target_id] for target_id in sorted(entries)]
        self.sync_recovery_permissions()
        if expires_at > 0:
            return True, f"You grant {target.key} permission to aid your recovery for {int(duration)}s."
        return True, f"You grant {target.key} permission to aid your recovery."

    def withdraw_recovery_consent(self, target):
        if not target or int(getattr(target, "id", 0) or 0) <= 0:
            return False, "You can only withdraw consent from a present character."
        target_id = int(target.id)
        entries = {int(entry["id"]): dict(entry) for entry in self._normalize_recovery_consent_entries()}
        if target_id not in entries:
            return False, f"{target.key} does not currently have your consent."
        entries.pop(target_id, None)
        self.db.recovery_consent = [entries[entry_id] for entry_id in sorted(entries)]
        self.sync_recovery_permissions()
        return True, f"You withdraw {target.key}'s permission to aid your recovery."

    def resolve_recovery_point_reference(self, reference):
        if not reference:
            return None
        if hasattr(reference, "id") and getattr(reference, "id", None):
            return reference
        if isinstance(reference, int) or str(reference).isdigit():
            result = search_object(f"#{int(reference)}")
            return result[0] if result else None
        result = search_object(str(reference))
        return result[0] if result else None

    def get_recovery_region(self, room=None):
        source_room = room or self.location
        if source_room and hasattr(source_room, "get_recovery_region_override"):
            override = source_room.get_recovery_region_override()
            if override:
                return override
        if source_room and hasattr(source_room, "get_region"):
            return source_room.get_region()
        return str(getattr(self.db, "last_known_region", None) or "default_region")

    def get_nearest_recovery_point(self, room=None):
        source_room = room or self.location
        if source_room and hasattr(source_room, "get_recovery_point_reference"):
            resolved = self.resolve_recovery_point_reference(source_room.get_recovery_point_reference())
            if resolved:
                return resolved
        region = self.get_recovery_region(room=source_room)
        for candidate in search_tag("recovery_point", category="death"):
            if hasattr(candidate, "get_region") and candidate.get_region() == region:
                return candidate
        for candidate in search_tag("shrine"):
            if hasattr(candidate, "get_region") and candidate.get_region() == region:
                return candidate
        if self.home:
            return self.home
        return source_room

    def emit_death_event(self, event_name, **payload):
        event = str(event_name or "").strip()
        if not event:
            return False
        payload = dict(payload)
        payload.setdefault("character", self)
        payload.setdefault("timestamp", time.time())
        listeners = [self, getattr(self, "location", None)]
        fired = False
        for listener in listeners:
            if listener and hasattr(listener, event):
                getattr(listener, event)(**payload)
                fired = True
        LOGGER.info("death_event=%s payload=%s", event, {key: getattr(value, 'id', value) for key, value in payload.items()})
        return fired

    def update_death_analytics(self, event_name, favor_used=0, recovery_time=None):
        self.ensure_core_defaults()
        analytics = dict(getattr(self.db, "death_analytics", None) or {})
        analytics.setdefault("deaths", 0)
        analytics.setdefault("departs", 0)
        analytics.setdefault("resurrections", 0)
        analytics.setdefault("favor_spent", 0)
        analytics.setdefault("recovery_count", 0)
        analytics.setdefault("total_recovery_time", 0.0)
        if event_name == "death":
            analytics["deaths"] += 1
        elif event_name == "depart":
            analytics["departs"] += 1
        elif event_name == "resurrection":
            analytics["resurrections"] += 1
        analytics["favor_spent"] += max(0, int(favor_used or 0))
        if recovery_time is not None:
            analytics["recovery_count"] += 1
            analytics["total_recovery_time"] += max(0.0, float(recovery_time or 0.0))
            analytics["average_recovery_time"] = analytics["total_recovery_time"] / max(1, analytics["recovery_count"])
        self.db.death_analytics = analytics
        return analytics

    def get_death_protection_state(self):
        self.ensure_core_defaults()
        active = bool(getattr(self.db, "death_protection", False)) and not bool(getattr(self.db, "is_npc", False)) and int(getattr(self.db, "profession_rank", 1) or 1) <= int(DEATH_PROTECTION_CONFIG["max_rank"])
        return {
            "active": active,
            "exp_debt_multiplier": float(DEATH_PROTECTION_CONFIG["exp_debt_multiplier"]),
            "sting_severity_scale": float(DEATH_PROTECTION_CONFIG["sting_severity_scale"]),
            "minimum_depart_mode": str(DEATH_PROTECTION_CONFIG["minimum_depart_mode"]),
        }

    def get_favor_death_consumption(self):
        config = FAVOR_SYSTEM_CONFIG
        streak = min(int(config["death_favor_consumption_streak_cap"]), int(getattr(self.db, "deaths_since_last_shrine", 0) or 0))
        return int(config["death_favor_consumption_base"]) + (streak * int(config["death_favor_consumption_streak_bonus"]))

    def handle_favor_death_event(self):
        favor_before = self.get_favor()
        self.db.deaths_since_last_shrine = int(getattr(self.db, "deaths_since_last_shrine", 0) or 0) + 1
        self.db.death_favor_snapshot = {
            "favor_before": favor_before,
            "favor_consumed": 0,
            "favor_remaining": favor_before,
            "soul_decay_rate": self.get_soul_decay_rate(favor=favor_before),
            "soul_strength_floor": self.get_soul_strength_floor(favor=favor_before),
            "resurrection": self.get_resurrection_favor_profile(favor=favor_before),
            "captured_at": time.time(),
            "must_depart": favor_before <= 0,
        }
        if favor_before <= 0:
            self.msg("You have no favor left to call upon. You must depart.")
        elif favor_before >= int(FAVOR_SYSTEM_CONFIG["high_favor_threshold"]):
            self.msg("A steady reserve of favor holds fast against death.")
        elif favor_before <= int(FAVOR_SYSTEM_CONFIG["low_favor_threshold"]):
            self.msg("Your favor feels thin as death takes hold.")

    def get_favor_death_snapshot(self):
        self.ensure_core_defaults()
        snapshot = getattr(self.db, "death_favor_snapshot", None)
        return dict(snapshot) if isinstance(snapshot, Mapping) else None

    def can_attempt_resurrection(self):
        snapshot = self.get_favor_death_snapshot()
        if isinstance(snapshot, Mapping):
            soul_state = self.get_soul_state()
            soul_recoverable = bool((soul_state or {}).get("recoverable", False)) if isinstance(soul_state, Mapping) else True
            return not bool(snapshot.get("must_depart", False)) and bool((snapshot.get("resurrection") or {}).get("can_resurrect", False)) and soul_recoverable
        return self.get_favor() > 0

    def get_death_attunement_cost(self, snapshot=None):
        profile = ((snapshot or self.get_favor_death_snapshot() or {}).get("resurrection") or {}) if isinstance(snapshot or self.get_favor_death_snapshot(), Mapping) else {}
        reduction = min(0.75, max(0.0, float(profile.get("cost_reduction", 0.0) or 0.0)))
        return max(5, int(round(float(FAVOR_SYSTEM_CONFIG["resurrection_base_attunement_cost"]) * (1.0 - reduction))))

    def get_death_corpse(self):
        corpse_id = int(getattr(self.db, "corpse_id", 0) or getattr(self.db, "last_corpse_id", 0) or 0)
        if corpse_id <= 0:
            return None
        result = search_object(f"#{corpse_id}")
        corpse = result[0] if result else None
        if not corpse or not getattr(corpse.db, "is_corpse", False):
            self.db.last_corpse_id = None
            return None
        return corpse

    def get_owned_grave(self, location=None):
        room = location or self.location
        if not room:
            return None
        graves = []
        for obj in list(getattr(room, "contents", []) or []):
            if not getattr(getattr(obj, "db", None), "is_grave", False):
                continue
            if hasattr(obj, "is_owner") and obj.is_owner(self):
                graves.append(obj)
        if not graves:
            return None
        graves.sort(key=lambda grave: float(getattr(grave.db, "created_at", getattr(grave.db, "creation_time", 0.0)) or 0.0), reverse=True)
        return graves[0]

    def get_recoverable_grave(self, location=None):
        room = location or self.location
        if not room:
            return None
        owned = self.get_owned_grave(location=room)
        if owned:
            return owned
        return None

    def calculate_depart_coin_loss(self, coins):
        total_coins = max(0, int(coins or 0))
        if total_coins <= 0:
            return 0, 0
        config = GRAVE_SYSTEM_CONFIG
        lost_coins = int(total_coins * float(config.get("base_coin_loss_ratio", 0.10) or 0.10))
        if self.get_favor() >= int(config.get("high_favor_threshold", 3) or 3):
            lost_coins = int(round(lost_coins * float(config.get("high_favor_loss_scale", 0.5) or 0.5)))
        sting_count = self.get_death_sting_count()
        if sting_count >= 4:
            lost_coins += int(round(total_coins * float(config.get("severe_sting_bonus_ratio", 0.05) or 0.05)))
        elif sting_count >= 2:
            lost_coins += int(round(total_coins * float(config.get("moderate_sting_bonus_ratio", 0.02) or 0.02)))
        lost_coins = max(0, min(total_coins, lost_coins))
        return lost_coins, max(0, total_coins - lost_coins)

    def create_depart_grave(self, corpse=None, location=None):
        self.ensure_core_defaults()
        now = time.time()
        grave_location = location or getattr(corpse, "location", None) or self.location or self.home
        lost_coins = 0
        if corpse and hasattr(corpse, "decay_to_grave"):
            corpse_coins = max(0, int(getattr(corpse.db, "stored_coins", 0) or 0))
            lost_coins, kept_coins = self.calculate_depart_coin_loss(corpse_coins)
            corpse.db.stored_coins = kept_coins
            grave = corpse.decay_to_grave(stored_coins=kept_coins, expires_at=now + float(GRAVE_SYSTEM_CONFIG["expiry_seconds"]))
        else:
            grave = create_object("typeclasses.grave.Grave", key=f"grave of {self.key}", location=grave_location, home=grave_location)
            grave.db.owner_id = self.id
            grave.db.owner_name = self.key
            grave.db.created_at = now
            grave.db.creation_time = now
            grave.db.items = []
            grave.db.stored_items = []
            grave.db.coins = 0
            grave.db.stored_coins = 0
            grave.db.expires_at = now + float(GRAVE_SYSTEM_CONFIG["expiry_seconds"])
            grave.db.expiry_time = grave.db.expires_at
            grave.db.recovery_allowed = [int(self.id or 0)] if int(self.id or 0) > 0 else []
            if hasattr(grave, "refresh_description"):
                grave.refresh_description()
            if hasattr(grave, "sync_storage_metadata"):
                grave.sync_storage_metadata()
            grave.scripts.add("typeclasses.scripts.GraveMaintenanceScript")
        return grave, lost_coins

    def create_death_corpse(self):
        corpse = self.get_death_corpse()
        if corpse:
            return corpse
        corpse = create_object(
            "typeclasses.corpse.Corpse",
            key=f"corpse of {self.key}",
            location=self.location,
            home=self.location,
        )
        corpse.db.owner_id = self.id
        corpse.db.corpse_owner_id = self.id
        corpse.db.owner_name = self.key
        corpse.db.death_timestamp = float(getattr(self.db, "death_timestamp", 0.0) or time.time())
        corpse.db.death_type = str(getattr(self.db, "death_type", "vitality") or "vitality")
        corpse.db.location = getattr(self.location, "id", None)
        corpse.db.decay_end_time = corpse.db.death_timestamp + (30 * 60)
        corpse.db.decay_time = corpse.db.decay_end_time
        corpse.db.memory_time = time.time() + (7 * 60)
        corpse.db.memory_faded = False
        corpse.db.memory_loss_applied = False
        corpse.db.favor_snapshot = self.get_favor()
        corpse.db.favor_detail_snapshot = self.get_favor_death_snapshot()
        corpse.db.is_valid_for_revive = corpse.db.death_type != "spirit"
        corpse.db.condition = 100.0
        corpse.db.stabilized = False
        corpse.db.preserve_stacks = 0
        corpse.db.preparation_stacks = 0
        corpse.db.stored_coins = 0
        corpse.db.recovery_allowed = sorted(self.get_recovery_consent_ids() | {int(self.id or 0)})
        corpse.db.wounds = copy.deepcopy(self.build_corpse_wound_payload())
        if hasattr(corpse, "update_condition_description"):
            corpse.update_condition_description()
        corpse.scripts.add("typeclasses.scripts.CorpseDecayScript")
        if hasattr(corpse, "schedule_decay_transition"):
            corpse.schedule_decay_transition()
        self.db.last_corpse_id = corpse.id
        self.db.corpse_id = corpse.id
        return corpse

    def move_carried_items_to_corpse(self, corpse):
        moved = []
        if not corpse:
            return moved
        carried = list(self.get_visible_carried_items())
        weapon = self.get_weapon()
        for item in carried:
            if item == weapon:
                continue
            if item.move_to(corpse, quiet=True):
                moved.append(item)
        return moved

    def clear_death_corpse_link(self):
        self.db.last_corpse_id = None
        self.db.corpse_id = None

    def move_coins_to_corpse(self, corpse):
        if not corpse:
            return 0
        coins = max(0, int(getattr(self.db, "coins", 0) or 0))
        corpse.db.stored_coins = coins
        self.db.coins = 0
        return coins

    def apply_death_sting(self, duration=600, favor=None, had_prior_penalty=False):
        self.ensure_core_defaults()
        if not bool(getattr(self.db, "death_penalty_applied", False)):
            self.db.death_sting = min(DEATH_STING_MAX_STACKS, max(1, self.get_death_sting_count() + 1))
            self.db.death_penalty_applied = True
        else:
            self.db.death_sting = max(1, self.get_death_sting_count())
        self.db.death_sting_active = True
        severity = self.calculate_death_sting_severity(favor=favor)
        self.db.death_sting_severity = severity
        self.db.death_sting_end = time.time() + max(0.0, float(duration or DEATH_STING_DECAY_SECONDS))
        self.db.death_sting_hp_cap_ratio = float(DEATH_STING_HP_CAPS.get(self.get_death_sting_recovery_label(), 1.0))
        self.db.death_sting_recovery_label = self.get_death_sting_recovery_label()
        self.sync_client_state()

    def at_death(self, cause=None, death_type="vitality"):
        from world.systems.death import handle_death

        return handle_death(self, cause=cause, death_type=death_type)

    def revive_from_death(self, via="depart"):
        self.ensure_core_defaults()
        restore_ratio = float(FAVOR_SYSTEM_CONFIG["resurrection_restore_hp_ratio"] if via == "resurrection" else FAVOR_SYSTEM_CONFIG["depart_restore_hp_ratio"])
        self.db.life_state = LIFE_STATE_ALIVE
        self.db.is_dead = False
        self.db.death_type = None
        self.db.death_timestamp = 0.0
        self.db.death_location = None
        self.db.recovery_state = "revived_weak" if via == "resurrection" else "none"
        self.db.depart_confirm_mode = None
        self.db.depart_confirm_expires_at = 0.0
        self.db.in_combat = False
        self.db.target = None
        if via != "resurrection":
            self.clear_state("resurrection_fragility")
            self.clear_state("resurrection_instability")
            self.db.resurrection_vitality_cap_ratio = 1.0
            self.db.res_stabilization = None
            self.db.just_revived = False
            self.db.revive_protection_ticks = 0
        self.db.hp = max(1, int(round((self.db.max_hp or 1) * restore_ratio)))
        self.db.balance = max(0, int(round((self.db.max_balance or 1) * 0.5)))
        self.db.fatigue = min(self.db.max_fatigue or 100, max(int(self.db.fatigue or 0), int(round((self.db.max_fatigue or 100) * 0.35))))
        self.db.stunned = False
        self.db.soul_state = None
        self.sync_empath_wounds_from_resources()
        self.sync_client_state()
        return True

    def begin_depart_confirmation(self, depart_type="standard"):
        self.ensure_core_defaults()
        if self.can_confirm_depart(depart_type=depart_type):
            return False
        self.db.depart_confirm_mode = str(depart_type or "standard")
        self.db.depart_confirm_expires_at = time.time() + DEPART_CONFIRM_WINDOW_SECONDS
        return True

    def can_confirm_depart(self, depart_type="standard"):
        self.ensure_core_defaults()
        expires_at = float(getattr(self.db, "depart_confirm_expires_at", 0.0) or 0.0)
        pending = str(getattr(self.db, "depart_confirm_mode", "") or "").strip().lower()
        return pending == str(depart_type or "standard").strip().lower() and expires_at > time.time()

    def is_depart_blocked_by_active_revive(self, corpse=None):
        corpse = corpse or self.get_death_corpse()
        if not corpse:
            return False
        room = getattr(corpse, "location", None)
        corpse_id = int(getattr(corpse, "id", 0) or 0)
        for obj in list(getattr(room, "contents", []) or []):
            pending = getattr(getattr(obj, "ndb", None), "pending_cleric_ritual_action", None)
            if not isinstance(pending, dict) or not bool(pending.get("active", False)):
                continue
            if int(pending.get("corpse_id", 0) or 0) != corpse_id:
                continue
            if str(pending.get("action", "") or "").strip().lower() == "revive":
                return True
        return False

    def set_recovery_metadata(self, recovery_type, helper=None, quality=None):
        self.db.last_recovery_type = str(recovery_type or "unknown")
        self.db.last_recovery_quality = str(quality or "") or None
        helper_name = getattr(helper, "key", helper)
        self.db.last_recovery_helper = str(helper_name) if helper_name else None
        self.db.last_recovery_time = time.time()
        return {
            "type": self.db.last_recovery_type,
            "quality": self.db.last_recovery_quality,
            "helper": self.db.last_recovery_helper,
            "time": self.db.last_recovery_time,
        }

    def get_last_recovery_elapsed(self):
        last_death = float(getattr(self.db, "last_death_time", 0.0) or 0.0)
        if last_death <= 0:
            return None
        return max(0.0, time.time() - last_death)

    def get_depart_mode(self, corpse=None, requested_mode=None):
        snapshot = None
        if corpse:
            snapshot = self.get_corpse_favor_detail_snapshot(corpse)
        if not isinstance(snapshot, Mapping):
            snapshot = self.get_favor_death_snapshot() or {}
        available_favor = int(snapshot.get("favor_before", 0) or 0)
        requested = str(requested_mode or "").strip().lower()
        default_mode = "full" if available_favor >= 3 else "items" if available_favor >= 2 else "grave"
        protection = self.get_death_protection_state()
        if protection["active"] and not requested:
            default_mode = str(protection["minimum_depart_mode"])
        if not requested:
            return default_mode
        requirements = {"grave": 0, "coins": 2, "items": 2, "full": 3}
        if requested not in requirements:
            return None
        if protection["active"]:
            return requested
        if available_favor < requirements[requested]:
            return None
        return requested

    def depart_self(self, mode=None):
        if not self.is_dead():
            return False, "You are not dead."
        requested_mode = str(mode or "standard").strip().lower()
        corpse = self.get_death_corpse()
        depart_mode = requested_mode if requested_mode != "standard" else "grave"
        if corpse and self.is_depart_blocked_by_active_revive(corpse=corpse):
            return False, "You feel the pull of return. You cannot depart while the final rite is underway."
        destination = self.get_nearest_recovery_point(room=self.location) or self.home or self.location
        corpse_room = getattr(corpse, "location", None)
        grave, lost_coins = self.create_depart_grave(corpse=corpse, location=corpse_room or self.location)
        self.db.life_state = LIFE_STATE_DEPARTED
        self.revive_from_death(via="depart")
        self.db.life_state = LIFE_STATE_ALIVE
        favor_snapshot = 0
        if corpse and hasattr(corpse, "get_favor_snapshot"):
            favor_snapshot = int(corpse.get_favor_snapshot() or 0)
        elif hasattr(self, "get_favor_death_snapshot"):
            favor_snapshot = int((self.get_favor_death_snapshot() or {}).get("favor_before", 0) or 0)
        self.apply_death_sting_recovery_effects(favor=favor_snapshot, via="depart")
        if destination and self.location != destination:
            self.move_to(destination, quiet=True)
        self.set_recovery_metadata("depart", helper=None)
        recovery_time = self.get_last_recovery_elapsed()
        favor_cost = 0
        self.update_death_analytics("depart", favor_used=favor_cost, recovery_time=recovery_time)
        self.emit_death_event("on_depart", mode=depart_mode, destination=destination)
        self.db.soul_state = None
        if grave and hasattr(grave, "sync_storage_metadata"):
            grave.sync_storage_metadata()
        if corpse_room:
            corpse_room.msg_contents("A disturbed patch of ground marks where someone fell.", exclude=[])
        self.clear_death_corpse_link()
        if lost_coins > 0:
            self.msg("Some of your belongings fail to remain with the grave.")
        return True, "You release your hold on the body and leave a grave behind."

    def resurrect_from_corpse(self, corpse, caster=None):
        if not corpse or not getattr(corpse.db, "is_corpse", False):
            return False, "That is not a corpse that can be restored."
        if hasattr(corpse, "get_owner"):
            owner = corpse.get_owner()
        else:
            owner = None
        if not owner:
            return False, "That corpse has no valid owner link to restore."
        if not owner.is_dead():
            return False, "They are no longer dead."
        snapshot = self.get_corpse_favor_detail_snapshot(corpse) if corpse else owner.get_favor_death_snapshot()
        if not isinstance(snapshot, Mapping):
            return False, "The corpse holds no viable soul pattern."
        soul_state = owner.get_soul_state() if hasattr(owner, "get_soul_state") else None
        if not isinstance(soul_state, Mapping):
            return False, "The soul cannot be found."
        if bool(getattr(corpse.db, "irrecoverable", False)):
            return False, "The body can no longer sustain life."
        room = getattr(corpse, "location", None)
        if room and hasattr(room, "is_no_resurrection_zone") and room.is_no_resurrection_zone():
            return False, "Something about this place rejects the rite outright."
        res_profile = dict(snapshot.get("resurrection") or {})
        if not bool(res_profile.get("can_resurrect", False)):
            return False, "Their spirit cannot be called back. They lack the favor required."
        loads = self.get_effective_corpse_revive_loads(corpse)
        survivability_band = self.get_corpse_revive_survivability_band(corpse)
        adjusted_favor = max(0, int(snapshot.get("favor_before", 0) or 0) - int(loads.get("favor_penalty", 0) or 0))
        favor_roll = self.roll_resurrection_success(adjusted_favor, corpse=corpse, caster=caster)
        if not favor_roll["success"]:
            return False, "The rite fails to take hold. The remaining favor is not enough this time."
        if not bool(soul_state.get("recoverable", False)):
            return False, "Their soul has slipped beyond your reach."
        if hasattr(corpse, "has_viable_memory") and not corpse.has_viable_memory():
            return False, "The corpse's memories have faded too far to guide the soul home."
        if caster is not None and hasattr(corpse, "is_recovery_allowed") and not corpse.is_recovery_allowed(caster):
            return False, "You do not have permission to work with that corpse."
        if caster is not None:
            if hasattr(caster, "is_profession") and not caster.is_profession("cleric"):
                return False, "Only a cleric can guide that return."
            attunement_cost = owner.get_death_attunement_cost(snapshot=snapshot)
            if hasattr(caster, "spend_attunement") and not caster.spend_attunement(attunement_cost):
                return False, "You lack the attunement to complete the rite."
            devotion_cost = caster.get_resurrection_devotion_cost(corpse=corpse, snapshot=snapshot) if hasattr(caster, "get_resurrection_devotion_cost") else 0
            if devotion_cost and hasattr(caster, "get_devotion") and caster.get_devotion() < devotion_cost:
                return False, "Your connection is too faint to complete the rite."
        condition = float(corpse.get_condition() if hasattr(corpse, "get_condition") else getattr(corpse.db, "condition", 100.0) or 0.0)
        if condition < 25 and survivability_band == "unsafe":
            return False, "The corpse is too damaged to call back to life."
        quality = owner.get_resurrection_quality_result(corpse=corpse, caster=caster, snapshot=snapshot, soul_state=soul_state)
        if caster is not None and hasattr(caster, "get_resurrection_devotion_profile"):
            devotion_profile = caster.get_resurrection_devotion_profile()
            failure_chance = float(devotion_profile.get("failure_chance", 0.0) or 0.0) + float(res_profile.get("failure_bias", 0.0) or 0.0)
            if condition < 50:
                failure_chance += 0.1
            soul_strength = max(0.0, min(100.0, float(soul_state.get("strength", 0.0) or 0.0)))
            if soul_strength < 35:
                failure_chance += 0.15
            elif soul_strength < 70:
                failure_chance += 0.05
            death_timestamp = float(getattr(corpse.db, "death_timestamp", 0.0) or 0.0)
            age_penalty = min(0.25, max(0.0, (time.time() - death_timestamp) / 1200.0)) if death_timestamp > 0 else 0.0
            prep_bonus = min(0.2, int(getattr(corpse.db, "preparation_stacks", 0) or 0) * 0.05)
            preserve_bonus = min(0.1, int(getattr(corpse.db, "preserve_stacks", 0) or 0) * 0.02)
            failure_chance = max(0.0, failure_chance + age_penalty - prep_bonus - preserve_bonus)
            if random.random() < min(0.85, failure_chance):
                if devotion_cost:
                    caster.adjust_devotion(-max(1, int(round(devotion_cost / 2))), sync=False)
                    caster.sync_client_state()
                if hasattr(corpse, "adjust_condition"):
                    corpse.adjust_condition(-10)
                corpse.db.preparation_stacks = max(0, int(getattr(corpse.db, "preparation_stacks", 0) or 0) - 1)
                corpse.db.resurrection_failures = int(getattr(corpse.db, "resurrection_failures", 0) or 0) + 1
                updated_soul = dict(soul_state)
                updated_soul["strength"] = max(0.0, float(updated_soul.get("strength", 0.0) or 0.0) - 12.0)
                if updated_soul["strength"] <= 0:
                    updated_soul["recoverable"] = False
                owner.db.soul_state = updated_soul
                failed_condition = float(corpse.get_condition() if hasattr(corpse, "get_condition") else getattr(corpse.db, "condition", 0.0) or 0.0)
                if failed_condition <= 20 or (failed_condition <= 25 and int(getattr(corpse.db, "resurrection_failures", 0) or 0) >= 2):
                    corpse.db.irrecoverable = True
                caster.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=caster.get_theurgy_training_difficulty(20))
                if bool(getattr(corpse.db, "irrecoverable", False)):
                    return False, "The body can no longer sustain life."
                return False, "The connection falters."
            if devotion_cost:
                caster.adjust_devotion(-devotion_cost, sync=False)
                caster.sync_client_state()
            quality = dict(quality)
            quality["hp_ratio"] = max(0.5, min(1.0, float(quality["hp_ratio"]) * float(devotion_profile.get("hp_scale", 1.0) or 1.0)))
            quality["exp_restore_scale"] = max(0.4, float(quality["exp_restore_scale"]) * float(devotion_profile.get("exp_scale", 1.0) or 1.0))
            quality["sting_duration_scale"] = max(0.1, float(quality["sting_duration_scale"]) * float(devotion_profile.get("sting_duration_scale", 1.0) or 1.0))
            quality["sting_severity_scale"] = max(0.1, float(quality["sting_severity_scale"]) * float(devotion_profile.get("sting_severity_scale", 1.0) or 1.0))
            quality["exp_restore_scale"] *= 1.0 + min(0.2, int(getattr(corpse.db, "preparation_stacks", 0) or 0) * 0.04)
            quality["hp_ratio"] = min(1.0, float(quality["hp_ratio"]) + min(0.1, int(getattr(corpse.db, "preparation_stacks", 0) or 0) * 0.02))
            quality["hp_ratio"] = max(0.45, min(1.0, float(quality["hp_ratio"]) * (0.75 + (soul_strength / 400.0))))
            quality["exp_restore_scale"] = max(0.3, float(quality["exp_restore_scale"]) * (0.7 + (soul_strength / 250.0)))
        quality = dict(quality)
        if survivability_band == "critical":
            quality["label"] = "fragile"
            quality["hp_ratio"] = min(float(quality.get("hp_ratio", 1.0) or 1.0), 0.45)
            quality["exp_restore_scale"] = min(float(quality.get("exp_restore_scale", 1.0) or 1.0), 0.7)
        elif survivability_band == "unsafe":
            quality["label"] = "flawed"
            quality["hp_ratio"] = min(float(quality.get("hp_ratio", 1.0) or 1.0), 0.28)
            quality["exp_restore_scale"] = min(float(quality.get("exp_restore_scale", 1.0) or 1.0), 0.5)
        owner.revive_from_death(via="resurrection")
        owner.apply_death_sting_recovery_effects(favor=int(snapshot.get("favor_before", 0) or 0), via="resurrection")
        if owner.is_death_sting_active():
            owner.db.death_sting_severity = max(0.0, float(getattr(owner.db, "death_sting_severity", 0.0) or 0.0) * float(quality["sting_severity_scale"]))
            remaining = owner.get_death_sting_time_remaining()
            owner.db.death_sting_end = time.time() + max(1, int(round(remaining * float(quality["sting_duration_scale"])))) if remaining > 0 else 0.0
        owner.db.hp = max(owner.db.hp or 1, int(round((owner.db.max_hp or 1) * float(quality["hp_ratio"]))))
        restored_ratio = max(0.0, min(1.0, (condition / 100.0) * float(quality["exp_restore_scale"])))
        restored_exp = int(round(owner.get_exp_debt() * restored_ratio))
        if restored_exp > 0:
            owner.reduce_exp_debt(restored_exp, emit_clear_message=True)
        owner.apply_resurrection_aftereffects(quality)
        owner.begin_resurrection_stabilization(survivability_band)
        if owner.location != corpse.location and corpse.location:
            owner.move_to(corpse.location, quiet=True)
        restored_coins = int(getattr(corpse.db, "stored_coins", 0) or 0)
        if restored_coins > 0:
            owner.db.coins = int(getattr(owner.db, "coins", 0) or 0) + restored_coins
            corpse.db.stored_coins = 0
        for item in list(corpse.contents):
            item.move_to(owner, quiet=True)
        if owner.get_favor() > 0:
            owner.adjust_favor(-1, emit_message=True, reason="revive")
        owner.db.last_favor_decay_at = time.time()
        owner.db.death_favor_snapshot = None
        owner.db.soul_state = None
        owner.db.last_corpse_id = None
        label = str(quality.get("label", "stable") or "stable")
        owner.set_recovery_metadata("resurrection", helper=caster, quality=quality.get("label"))
        recovery_time = owner.get_last_recovery_elapsed()
        owner.update_death_analytics("resurrection", favor_used=1, recovery_time=recovery_time)
        owner.emit_death_event("on_resurrection", caster=caster, corpse=corpse, quality=label)
        owner.sync_client_state()
        if caster is not None:
            caster.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=caster.get_theurgy_training_difficulty(24))
        corpse.delete()
        if int(snapshot.get("favor_before", 0) or 0) >= int(FAVOR_SYSTEM_CONFIG["high_favor_threshold"]):
            owner.msg("Enough favor remains to steady your return.")
        elif int(snapshot.get("favor_before", 0) or 0) <= int(FAVOR_SYSTEM_CONFIG["low_favor_threshold"]):
            owner.msg("You return with little favor left to shield you.")
        if survivability_band == "critical":
            owner.msg("Your return holds, but only barely. You need help immediately.")
        elif survivability_band == "unsafe":
            owner.msg("You rip back into life in ruinous condition.")
        if label == "perfect":
            return True, f"Life returns as the soul finds its way back. {owner.key} rises in near-perfect form."
        if label == "stable":
            return True, f"Life returns as the soul finds its way back. {owner.key} is restored in stable condition."
        return True, f"{owner.key} is restored to life, but something feels off."

    def cancel_pending_cleric_ritual(self, message=None, emit_message=True):
        pending = getattr(self.ndb, "pending_cleric_ritual_action", None)
        if not isinstance(pending, dict) or not bool(pending.get("active", False)):
            return False
        action = str(pending.get("action", "") or "").strip().lower()
        corpse_id = int(pending.get("corpse_id", 0) or 0)
        result = search_object(f"#{corpse_id}") if corpse_id > 0 else []
        corpse = result[0] if result else None
        pending["active"] = False
        self.ndb.pending_cleric_ritual_action = pending
        if emit_message:
            state_before = corpse.get_ritual_state() if corpse and hasattr(corpse, "get_ritual_state") else None
            consequence = self.apply_cleric_ritual_failure(corpse, action, interrupted=True)
            state_after = corpse.get_ritual_state() if corpse and hasattr(corpse, "get_ritual_state") else None
            if corpse:
                self.emit_ritual_message(corpse, f"interrupt_{int(getattr(self, 'id', 0) or 0)}", f"{self.key}'s part of the rite falters.", cooldown=0.5, exclude=[self])
                if state_before != state_after:
                    self.emit_ritual_message(corpse, f"interrupt_regress_{action}", "The ritual slips backward under the strain.", cooldown=0.5, exclude=[self])
            self.msg(f"{message or 'Your ritual is interrupted.'} {consequence}".strip())
        return True

    def cancel_pending_revive(self, message=None, emit_message=True):
        return self.cancel_pending_cleric_ritual(message=message, emit_message=emit_message)

    def _complete_pending_cleric_ritual(self, token):
        pending = getattr(self.ndb, "pending_cleric_ritual_action", None)
        if not isinstance(pending, dict) or not bool(pending.get("active", False)) or str(pending.get("token", "")) != str(token or ""):
            return False
        action = str(pending.get("action", "") or "").strip().lower()
        corpse_id = int(pending.get("corpse_id", 0) or 0)
        result = search_object(f"#{corpse_id}") if corpse_id > 0 else []
        corpse = result[0] if result else None
        pending["active"] = False
        self.ndb.pending_cleric_ritual_action = pending
        if action == "revive":
            ok, message = self.perform_cleric_revive(corpse)
        else:
            ok, message = self.perform_cleric_corpse_ritual(corpse, action)
        if not ok:
            consequence = self.apply_cleric_ritual_failure(corpse, action, interrupted=False)
            message = f"{message} {consequence}".strip()
        self.msg(message)
        return ok

    def _finalize_revive_corpse_cleanup(self, corpse_id):
        corpse_id = int(corpse_id or 0)
        if corpse_id <= 0:
            return False
        result = search_object(f"#{corpse_id}")
        corpse = result[0] if result else None
        if not corpse:
            return True
        corpse.delete()
        return True

    def perform_cleric_revive(self, corpse):
        if self.is_dead():
            return False, "The dead cannot perform a revive."
        if not self.is_profession("cleric"):
            return False, "Only a cleric can guide a soul back."
        ok, message = self.can_work_corpse(corpse)
        if not ok:
            return False, message
        room = getattr(corpse, "location", None)
        if not self.can_revive_in_room(room=room):
            return False, "You can only revive someone in a shrine or consecrated place."
        ritual_state = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        if ritual_state == "unprepared":
            return False, "The body is not prepared for the rite."
        if bool(getattr(corpse.db, "irrecoverable", False)):
            return False, "This corpse can no longer sustain life."
        if not bool(getattr(corpse.db, "is_valid_for_revive", True)) or str(getattr(corpse.db, "death_type", "vitality") or "vitality") == "spirit":
            return False, "A spirit death cannot be reversed."
        if hasattr(corpse, "has_viable_memory") and not corpse.has_viable_memory():
            return False, "The corpse's memory has faded beyond recall."
        if not bool(getattr(corpse.db, "soul_bound", False)) or ritual_state != "bound":
            return False, "The soul has not been secured."
        owner = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        if not owner:
            return False, "That corpse has no soul to call back."
        if not owner.is_dead():
            return False, "They are no longer dead."
        favor_snapshot = corpse.get_favor_snapshot() if hasattr(corpse, "get_favor_snapshot") else 0
        if int(favor_snapshot or 0) < 1:
            return False, "There is not enough lingering favor to revive them."
        survivability_band = self.get_corpse_revive_survivability_band(corpse)
        revive_cost = max(1, int(FAVOR_SYSTEM_CONFIG.get("revive_cost", 1) or 1))
        restored_favor = max(0, min(owner.get_favor_max(), int(favor_snapshot or 0) - revive_cost))
        self.apply_cleric_group_contribution(corpse, "revive")
        corpse_wounds = self.get_corpse_wounds(corpse)
        vitality_burden = max(0, min(100, int(corpse_wounds.get("empath", {}).get("vitality", 0) or 0)))
        vitality_ratio = max(0.0, min(1.0, float(100 - vitality_burden) / 100.0))
        survivability_warning = self.get_corpse_survivability_warning(corpse)
        if survivability_warning:
            self.msg(survivability_warning)
        owner.revive_from_death(via="revive")
        owner.apply_corpse_wound_payload(corpse_wounds, sync=False)
        owner.apply_death_sting_recovery_effects(favor=int(favor_snapshot or 0), via="revive")
        owner.begin_resurrection_stabilization(survivability_band)
        owner.db.hp = max(1, int(round((owner.db.max_hp or 1) * vitality_ratio)))
        owner.db.favor_current = restored_favor
        owner.db.favor = restored_favor
        owner.db.last_favor_decay_at = time.time()
        owner.db.recovery_state = "revived_stable" if survivability_band == "stable" else "revived_unstable"
        owner.set_recovery_metadata("revive", helper=self, quality=survivability_band)
        owner.update_death_analytics("resurrection", favor_used=revive_cost, recovery_time=owner.get_last_recovery_elapsed())
        owner.emit_death_event("on_resurrection", caster=self, corpse=corpse, quality=survivability_band)
        owner.sync_client_state()
        owner.msg(f"{self.key} calls you back from death.")
        owner.msg("A portion of your favor is spent to complete the return.")
        if survivability_band == "stable":
            owner.msg("You return to life, weakened but stable.")
        else:
            owner.msg("You return to life, but your body is failing.")
        if room:
            self.emit_ritual_message(corpse, f"revive_outcome_{survivability_band}", f"{owner.key} jolts back to life.", cooldown=0.5, exclude=[owner, self])
        corpse_id = int(getattr(corpse, "id", 0) or 0)
        owner.clear_death_corpse_link()
        delay(0, self._finalize_revive_corpse_cleanup, corpse_id)
        return True, f"You complete the final rite and call {owner.key} back to life."

    def perform_cleric_corpse_ritual(self, corpse, action):
        if self.is_dead():
            return False, "The dead cannot perform that rite."
        if not self.is_profession("cleric"):
            return False, "Only a cleric can perform that rite."
        ok, message = self.can_work_corpse(corpse)
        if not ok:
            return False, message
        if bool(getattr(corpse.db, "irrecoverable", False)):
            return False, "This corpse can no longer sustain the rite."
        if not bool(getattr(corpse.db, "is_valid_for_revive", True)) or str(getattr(corpse.db, "death_type", "vitality") or "vitality") == "spirit":
            return False, "A spirit death cannot be reversed."
        current_state = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        contribution = self.apply_cleric_group_contribution(corpse, action)
        if action == "prepare":
            if current_state != "unprepared":
                return True, "You join the ongoing ritual, but your practiced hands add no new edge to the preparation."
            corpse.set_ritual_state("prepared") if hasattr(corpse, "set_ritual_state") else setattr(corpse.db, "ritual_state", "prepared")
            corpse.db.prepared_by = int(getattr(self, "id", 0) or 0)
            if hasattr(corpse, "adjust_ritual_quality"):
                corpse.adjust_ritual_quality(CLERIC_RITUAL_QUALITY_STEPS["prepare"])
            message = "You finish preparing the body for the rites."
            if contribution["joined"]:
                message = f"You join the ongoing ritual. {message}"
            if contribution["specialization_bonus"]:
                message = f"{message} {self.get_cleric_specialization_match_feedback(action)}"
            self.emit_ritual_message(corpse, "prepare_complete", self.get_cleric_stage_completion_room_message("prepare"), cooldown=0.5, exclude=[self])
            self.emit_ritual_message(corpse, "prepare_ready", self.get_cleric_assess_readiness_line(corpse), cooldown=0.5, exclude=[])
            self.notify_dead_owner_of_ritual_transition(corpse, "prepare")
            return True, message
        if action == "stabilize":
            if current_state == "unprepared":
                return False, "The body must be prepared before it can be stabilized."
            if current_state in {"stabilized", "restored", "bound"}:
                return True, "Another cleric steadies the rite beside you, but you add no further strength to this stage."
            corpse.set_ritual_state("stabilized") if hasattr(corpse, "set_ritual_state") else setattr(corpse.db, "ritual_state", "stabilized")
            corpse.db.stabilized = True
            if hasattr(corpse, "extend_memory"):
                corpse.extend_memory(180, stacks=0)
            if hasattr(corpse, "adjust_ritual_quality"):
                corpse.adjust_ritual_quality(CLERIC_RITUAL_QUALITY_STEPS["stabilize"])
            message = "You stabilize the body's fading pattern and hold its memories in place."
            if contribution["joined"]:
                message = f"You join the ongoing ritual. {message}"
            if contribution["specialization_bonus"]:
                message = f"{message} {self.get_cleric_specialization_match_feedback(action)}"
            self.emit_ritual_message(corpse, "stabilize_complete", self.get_cleric_stage_completion_room_message("stabilize"), cooldown=0.5, exclude=[self])
            self.emit_ritual_message(corpse, "stabilize_ready", self.get_cleric_assess_readiness_line(corpse), cooldown=0.5, exclude=[])
            self.notify_dead_owner_of_ritual_transition(corpse, "stabilize")
            return True, message
        if action == "restore":
            if current_state == "unprepared":
                return False, "The body must be prepared before its memories can be restored."
            if current_state == "prepared":
                return False, "The body must be stabilized before its memories can be restored."
            if current_state in {"restored", "bound"}:
                return True, "You join the ongoing ritual, but the memories are already as coherent as this stage allows."
            corpse.set_ritual_state("restored") if hasattr(corpse, "set_ritual_state") else setattr(corpse.db, "ritual_state", "restored")
            corpse.db.memory_stable = True
            corpse.db.memory_faded = False
            if hasattr(corpse, "adjust_ritual_quality"):
                corpse.adjust_ritual_quality(CLERIC_RITUAL_QUALITY_STEPS["restore"])
            message = "You restore coherence to the corpse's lingering memories."
            if contribution["joined"]:
                message = f"You join the ongoing ritual. {message}"
            if contribution["specialization_bonus"]:
                message = f"{message} {self.get_cleric_specialization_match_feedback(action)}"
            self.emit_ritual_message(corpse, "restore_complete", self.get_cleric_stage_completion_room_message("restore"), cooldown=0.5, exclude=[self])
            self.emit_ritual_message(corpse, "restore_ready", self.get_cleric_assess_readiness_line(corpse), cooldown=0.5, exclude=[])
            self.notify_dead_owner_of_ritual_transition(corpse, "restore")
            return True, message
        if action == "bind":
            if current_state == "unprepared":
                return False, "The body must be prepared before the soul can be bound."
            if current_state == "prepared":
                return False, "The body must be stabilized before the soul can be bound."
            if current_state == "stabilized":
                return False, "The memories must be restored before the soul can be bound."
            if current_state == "bound":
                return True, "You join the ongoing ritual, but the soul is already secured as tightly as this stage allows."
            corpse.set_ritual_state("bound") if hasattr(corpse, "set_ritual_state") else setattr(corpse.db, "ritual_state", "bound")
            corpse.db.soul_bound = True
            if hasattr(corpse, "adjust_ritual_quality"):
                corpse.adjust_ritual_quality(CLERIC_RITUAL_QUALITY_STEPS["bind"])
            message = "You secure the soul to the body and make the final rite possible."
            if contribution["joined"]:
                message = f"You join the ongoing ritual. {message}"
            if contribution["specialization_bonus"]:
                message = f"{message} {self.get_cleric_specialization_match_feedback(action)}"
            self.emit_ritual_message(corpse, "bind_complete", self.get_cleric_stage_completion_room_message("bind"), cooldown=0.5, exclude=[self])
            self.emit_ritual_message(corpse, "bind_ready", self.get_cleric_assess_readiness_line(corpse), cooldown=0.5, exclude=[])
            self.notify_dead_owner_of_ritual_transition(corpse, "bind")
            return True, message
        return False, "You cannot perform that rite."

    def start_cleric_revive(self, corpse):
        pending = getattr(self.ndb, "pending_cleric_ritual_action", None)
        if isinstance(pending, dict) and bool(pending.get("active", False)):
            return False, "You are already sustaining a rite."
        if self.is_dead():
            return False, "The dead cannot perform a revive."
        if not self.is_profession("cleric"):
            return False, "Only a cleric can guide a soul back."
        ok, message = self.can_work_corpse(corpse)
        if not ok:
            return False, message
        room = getattr(corpse, "location", None)
        if not self.can_revive_in_room(room=room):
            return False, "You can only revive someone in a shrine or consecrated place."
        ritual_state = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        if ritual_state == "unprepared":
            return False, "The body is not prepared for the rite."
        if bool(getattr(corpse.db, "irrecoverable", False)):
            return False, "This corpse can no longer sustain life."
        if not bool(getattr(corpse.db, "is_valid_for_revive", True)) or str(getattr(corpse.db, "death_type", "vitality") or "vitality") == "spirit":
            return False, "A spirit death cannot be reversed."
        if hasattr(corpse, "has_viable_memory") and not corpse.has_viable_memory():
            return False, "The corpse's memory has faded beyond recall."
        if not bool(getattr(corpse.db, "soul_bound", False)) or ritual_state != "bound":
            return False, "The soul has not been secured."
        favor_snapshot = corpse.get_favor_snapshot() if hasattr(corpse, "get_favor_snapshot") else 0
        if int(favor_snapshot or 0) < 1:
            return False, "There is not enough lingering favor to revive them."
        specialization = self.get_cleric_specialization()
        revive_cost = CLERIC_REVIVE_RITUAL_COST
        if specialization and specialization == self.get_cleric_stage_specialization("revive"):
            revive_cost = max(0, revive_cost - 1)
        spend_ok, spend_result = self.spend_devotion(revive_cost, failure_message="You do not have the devotion required to continue the rite.")
        if not spend_ok:
            return False, spend_result
        if hasattr(corpse, "add_ritual_participant"):
            corpse.add_ritual_participant(self)
        token = f"revive:{int(getattr(self, 'id', 0) or 0)}:{int(getattr(corpse, 'id', 0) or 0)}:{time.time():.6f}"
        self.ndb.pending_cleric_ritual_action = {
            "active": True,
            "action": "revive",
            "token": token,
            "corpse_id": int(getattr(corpse, "id", 0) or 0),
        }
        self.sync_client_state()
        owner = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        if owner:
            owner.msg("A distant rite tugs at the edge of your spirit.")
        delay(self.get_cleric_stage_delay(corpse, "revive"), self._complete_pending_cleric_ritual, token)
        join_text = " You join the ongoing ritual." if self.get_cleric_group_support_count(corpse) > 1 else ""
        return True, f"You begin the final rite over {corpse.key}.{join_text} Remain still and unhurt until it is complete."

    def start_cleric_corpse_ritual(self, corpse, action):
        action_key = str(action or "").strip().lower()
        pending = getattr(self.ndb, "pending_cleric_ritual_action", None)
        if isinstance(pending, dict) and bool(pending.get("active", False)):
            return False, "You are already sustaining a rite."
        if self.is_dead():
            return False, "The dead cannot perform that rite."
        if not self.is_profession("cleric"):
            return False, "Only a cleric can perform that rite."
        ok, message = self.can_work_corpse(corpse)
        if not ok:
            return False, message
        if action_key not in CLERIC_CORPSE_RITUAL_ACTIONS:
            return False, "You cannot perform that rite."
        if bool(getattr(corpse.db, "irrecoverable", False)):
            return False, "This corpse can no longer sustain the rite."
        if not bool(getattr(corpse.db, "is_valid_for_revive", True)) or str(getattr(corpse.db, "death_type", "vitality") or "vitality") == "spirit":
            return False, "A spirit death cannot be reversed."
        if hasattr(corpse, "has_viable_memory") and not corpse.has_viable_memory():
            return False, "The corpse's memory has faded beyond recall."
        current_state = corpse.get_ritual_state() if hasattr(corpse, "get_ritual_state") else str(getattr(corpse.db, "ritual_state", "unprepared") or "unprepared")
        if action_key == "prepare" and current_state != "unprepared":
            if hasattr(corpse, "has_stage_contributor") and corpse.has_stage_contributor(action_key, self):
                return False, "You have already lent your hand to that stage."
            return False, "The body is already prepared for the rite."
        if action_key == "stabilize":
            if current_state == "unprepared":
                return False, "The body must be prepared before it can be stabilized."
            if current_state in {"stabilized", "restored", "bound"}:
                if hasattr(corpse, "has_stage_contributor") and corpse.has_stage_contributor(action_key, self):
                    return False, "You have already lent your hand to that stage."
                return False, "The body's fading pattern is already stabilized."
        if action_key == "restore":
            if current_state == "unprepared":
                return False, "The body must be prepared before its memories can be restored."
            if current_state == "prepared":
                return False, "The body must be stabilized before its memories can be restored."
            if current_state in {"restored", "bound"}:
                if hasattr(corpse, "has_stage_contributor") and corpse.has_stage_contributor(action_key, self):
                    return False, "You have already lent your hand to that stage."
                return False, "The body's memories are already restored."
        if action_key == "bind":
            if current_state == "unprepared":
                return False, "The body must be prepared before the soul can be bound."
            if current_state == "prepared":
                return False, "The body must be stabilized before the soul can be bound."
            if current_state == "stabilized":
                return False, "The memories must be restored before the soul can be bound."
            if current_state == "bound":
                if hasattr(corpse, "has_stage_contributor") and corpse.has_stage_contributor(action_key, self):
                    return False, "You have already lent your hand to that stage."
                return False, "The soul is already secured."
        profile = CLERIC_CORPSE_RITUAL_ACTIONS[action_key]
        specialization, unlocked = self.maybe_define_cleric_specialization(action_key)
        devotion_cost = int(profile.get("cost", 0) or 0)
        if specialization and specialization == self.get_cleric_stage_specialization(action_key):
            devotion_cost = max(0, devotion_cost - 1)
        spend_ok, spend_result = self.spend_devotion(devotion_cost, failure_message="You do not have the devotion required to continue the rite.")
        if not spend_ok:
            return False, spend_result
        if hasattr(corpse, "add_ritual_participant"):
            corpse.add_ritual_participant(self)
        active_stage_actors = self.get_pending_cleric_stage_actor_ids(corpse, action_key, include_self=False)
        token = f"{action_key}:{int(getattr(self, 'id', 0) or 0)}:{int(getattr(corpse, 'id', 0) or 0)}:{time.time():.6f}"
        self.ndb.pending_cleric_ritual_action = {
            "active": True,
            "action": action_key,
            "token": token,
            "corpse_id": int(getattr(corpse, "id", 0) or 0),
        }
        self.sync_client_state()
        if not active_stage_actors:
            self.emit_ritual_message(corpse, f"{action_key}_start", self.get_cleric_stage_start_room_message(action_key), cooldown=0.5, exclude=[self])
        elif self.should_emit_ritual_join_message(corpse, action_key, actor=self, cooldown=6.0):
            specialization = self.get_cleric_specialization()
            expected_specialization = self.get_cleric_stage_specialization(action_key)
            join_message = self.get_cleric_stage_join_room_message(action_key)
            emitted_join = False
            if specialization and specialization == expected_specialization:
                if self.should_emit_ritual_specialization_join_message(corpse, action_key, specialization):
                    emitted_join = self.emit_ritual_message(corpse, f"{action_key}_join_specialization_{specialization}", join_message, cooldown=0.5, exclude=[self])
            else:
                emitted_join = self.emit_ritual_message(corpse, f"{action_key}_join_actor_{int(getattr(self, 'id', 0) or 0)}", join_message, cooldown=0.5, exclude=[self])
            if emitted_join:
                self.emit_ritual_message(corpse, f"{action_key}_join_reinforce_{int(getattr(self, 'id', 0) or 0)}", "Another set of practiced hands strengthens the ritual.", cooldown=0.5, exclude=[self])
        delay(self.get_cleric_stage_delay(corpse, action_key), self._complete_pending_cleric_ritual, token)
        message = str(profile.get("start_message", "You begin the rite.") or "You begin the rite.")
        if self.get_cleric_group_support_count(corpse) > 1:
            message = f"{message} You join the ongoing ritual."
        if unlocked:
            unlock_message = self.announce_cleric_specialization_unlock(specialization)
            if unlock_message:
                message = f"{message} {unlock_message}"
        return True, message

    def recover_grave_items(self, grave=None):
        self.ensure_core_defaults()
        if self.is_dead():
            return False, "You must return to life before you can recover anything."
        grave = grave or self.get_recoverable_grave()
        if not grave:
            return False, "You have nothing here to recover."
        if grave.location != self.location:
            return False, "You must stand where your grave rests to recover it."
        if hasattr(grave, "is_owner") and not grave.is_owner(self):
            return False, "You do not have permission to disturb that grave."
        moved = []
        available_weight = max(0.0, self.get_max_carry_weight() - self.get_total_weight()) if hasattr(self, "get_max_carry_weight") and hasattr(self, "get_total_weight") else None
        for item in list(grave.contents):
            item_weight = self.get_object_total_weight(item) if hasattr(self, "get_object_total_weight") else 0.0
            if available_weight is not None and item_weight > available_weight + 0.0001:
                continue
            if item.move_to(self, quiet=True):
                damage = int(getattr(getattr(item, "db", None), "grave_damage", 0) or 0)
                if hasattr(item, "at_grave_recovery"):
                    item.at_grave_recovery(damage)
                item.db.grave_damage = 0
                moved.append(item)
                if available_weight is not None:
                    available_weight = max(0.0, available_weight - item_weight)
        recovered_coins = int(getattr(grave.db, "stored_coins", 0) or 0)
        if recovered_coins > 0:
            self.db.coins = int(getattr(self.db, "coins", 0) or 0) + recovered_coins
            grave.db.coins = 0
            grave.db.stored_coins = 0
        owner_id = int(getattr(grave.db, "owner_id", 0) or 0)
        if owner_id > 0 and owner_id != int(self.id or 0):
            result = search_object(f"#{owner_id}")
            owner = result[0] if result else None
            if owner and hasattr(owner, "notify_recovery_consent_use"):
                owner.notify_recovery_consent_use(self, "begins assisting with your remains")
        self.emit_death_event("on_grave_recovered", grave=grave, actor=self)
        if hasattr(grave, "sync_storage_metadata"):
            grave.sync_storage_metadata()
        grave_empty = not list(grave.contents) and int(getattr(grave.db, "stored_coins", 0) or 0) <= 0
        if grave_empty:
            grave.delete()
        self.sync_client_state()
        if moved or recovered_coins > 0:
            if grave_empty:
                summary = "You recover what remains of your possessions."
            else:
                summary = "You recover what you can carry, but some items remain in the grave."
            if recovered_coins > 0:
                summary = f"{summary} You also recover {recovered_coins} coins."
            return True, summary
        return False, "You cannot carry anything else from the grave right now."

    def get_rejuvenation_strength(self, corpse):
        attunement = self.get_skill("attunement")
        theology = self.get_skill("magic")
        condition_penalty = max(0, int((100 - float(corpse.get_condition() if hasattr(corpse, "get_condition") else getattr(corpse.db, "condition", 100.0) or 100.0)) / 20))
        return max(8, min(30, 10 + int(attunement / 8) + int(theology / 12) - condition_penalty))

    def rejuvenate_corpse(self, corpse):
        if not self.is_profession("cleric"):
            return False, "Only a cleric can weave that rite through dead flesh."
        return self.start_cleric_corpse_ritual(corpse, "restore")

    def maybe_msg_death_sting_combat_feedback(self):
        if not self.is_death_sting_active():
            return False
        if random.random() > 0.25:
            return False
        self.msg("You feel sluggish from your recent death.")
        return True

    def force_resurrect(self, corpse=None, helper=None):
        target_corpse = corpse or self.get_death_corpse()
        if not self.is_dead():
            return False, "They are not dead."
        if target_corpse and getattr(target_corpse, "location", None) and self.location != target_corpse.location:
            self.move_to(target_corpse.location, quiet=True)
        self.revive_from_death(via="resurrection")
        if target_corpse:
            restored_coins = int(getattr(target_corpse.db, "stored_coins", 0) or 0)
            if restored_coins > 0:
                self.db.coins = int(getattr(self.db, "coins", 0) or 0) + restored_coins
                target_corpse.db.stored_coins = 0
            for item in list(target_corpse.contents):
                item.move_to(self, quiet=True)
            target_corpse.delete()
        self.db.soul_state = None
        self.db.last_corpse_id = None
        self.set_recovery_metadata("resurrection", helper=helper, quality="forced")
        self.update_death_analytics("resurrection", recovery_time=self.get_last_recovery_elapsed())
        self.emit_death_event("on_resurrection", caster=helper, corpse=target_corpse, quality="forced")
        return True, f"{self.key} is forced back into life."

    def reduce_death_sting(self, power):
        self.ensure_core_defaults()
        if not self.is_death_sting_active():
            return False, "They are not suffering from Death's Sting."
        power_value = max(0, int(power or 0))
        if power_value >= 75:
            self.db.death_sting = 0
            self.db.death_sting_active = False
            self.db.death_sting_end = 0.0
            self.db.death_sting_severity = 0.0
            self.db.death_sting_hp_cap_ratio = 1.0
            self.db.death_sting_recovery_label = "none"
            self.sync_client_state()
            return True, "Death's Sting is lifted completely."
        remaining = self.get_death_sting_time_remaining()
        if power_value >= 40:
            self.db.death_sting_severity = max(0.0, float(getattr(self.db, "death_sting_severity", 0.0) or 0.0) * 0.6)
            self.db.death_sting_end = time.time() + max(1, int(round(remaining * 0.4)))
            self.sync_client_state()
            return True, "Death's Sting loosens its grip."
        self.db.death_sting_end = time.time() + max(1, int(round(remaining * 0.6)))
        self.sync_client_state()
        return True, "The lingering ache of death eases slightly."

    def maybe_warn_low_favor(self):
        if self.get_favor() > int(FAVOR_SYSTEM_CONFIG["low_favor_threshold"]):
            return False
        now = time.time()
        if now < float(getattr(self.db, "last_low_favor_warning_at", 0.0) or 0.0) + 15.0:
            return False
        self.db.last_low_favor_warning_at = now
        self.msg("You feel unprepared for what may come.")
        return True

    def is_empath(self):
        return self.get_profession() == "empath"

    def get_empath_shock(self):
        return max(0, min(100, int(getattr(self.db, "empath_shock", 0) or 0)))

    def set_empath_shock(self, value):
        old_value = max(0, min(100, int(getattr(self.db, "empath_shock", 0) or 0)))
        old_state = self.get_empath_shock_state(old_value)
        self.db.empath_shock = max(0, min(100, int(value or 0)))
        new_state = self.get_empath_shock_state(self.db.empath_shock)
        if self.get_empath_shock_state_rank(new_state) > self.get_empath_shock_state_rank(old_state):
            self.decay_empath_unity_stability(event_key="shock_worsen", emit_message=True)
        if new_state != old_state:
            message = self.get_empath_shock_message(new_state)
            if message:
                self.msg(message)
        if new_state == "disconnected":
            self.break_empath_connections(reason="shock", emit_message=True)
        self.sync_client_state()
        return self.db.empath_shock

    def adjust_empath_shock(self, amount):
        return self.set_empath_shock(self.get_empath_shock() + int(amount or 0))

    def get_empath_circle_distribution_weights(self, members=None):
        weighted_members = []
        for member in list(members or self.get_empath_circle_members(include_self=True, validate=True)):
            if not member or not getattr(member, "is_empath", lambda: False)():
                continue
            risk = member.get_empath_transfer_risk_state() if hasattr(member, "get_empath_transfer_risk_state") else {}
            vitality = max(0, 100 - int(member.get_empath_wound("vitality") if hasattr(member, "get_empath_wound") else 0))
            shock = max(0, 100 - int(member.get_empath_shock() if hasattr(member, "get_empath_shock") else 0))
            fatigue = max(0, 100 - int(member.get_empath_wound("fatigue") if hasattr(member, "get_empath_wound") else 0))
            weight = max(0.25, (vitality * 0.45) + (shock * 0.35) + (fatigue * 0.20))
            tier = str(risk.get("tier") or "steady")
            if member.is_medically_critical() if hasattr(member, "is_medically_critical") else False:
                weight *= 0.55
            elif tier == "extreme":
                weight *= 0.6
            elif tier == "high":
                weight *= 0.75
            weighted_members.append((member, max(0.1, float(weight))))
        return weighted_members

    def distribute_circle_shock(self, amount, source="take"):
        amount = max(0, int(round(amount or 0)))
        members = self.get_empath_circle_members(include_self=True, validate=True)
        if amount <= 0 or len(members) <= 1:
            self.adjust_empath_shock(amount)
            return {int(getattr(self, "id", 0) or 0): amount}
        weighted_members = self.get_empath_circle_distribution_weights(members=members)
        if not weighted_members:
            self.adjust_empath_shock(amount)
            return {int(getattr(self, "id", 0) or 0): amount}
        total_weight = sum(weight for _member, weight in weighted_members)
        if total_weight <= 0:
            self.adjust_empath_shock(amount)
            return {int(getattr(self, "id", 0) or 0): amount}
        shares = {}
        remaining = amount
        for index, (member, weight) in enumerate(weighted_members):
            if index == len(weighted_members) - 1:
                share = remaining
            else:
                share = max(0, min(remaining, int(round((amount * weight) / total_weight))))
            remaining -= share
            shares[int(getattr(member, "id", 0) or 0)] = share
        if remaining > 0 and shares:
            first_member_id = int(getattr(weighted_members[0][0], "id", 0) or 0)
            shares[first_member_id] = int(shares.get(first_member_id, 0) or 0) + remaining
        for member, _weight in weighted_members:
            member_id = int(getattr(member, "id", 0) or 0)
            share = int(shares.get(member_id, 0) or 0)
            if share <= 0:
                continue
            member.set_empath_shock(member.get_empath_shock() + share)
            if member == self:
                member.msg("The strain spreads through your circle.")
            else:
                member.msg("You share in the burden.")
        self.maybe_trigger_empath_circle_cascade(trigger_amount=amount, source=source)
        return shares

    def get_empath_circle_cascade_risk(self):
        members = self.get_empath_circle_members(include_self=True, validate=True)
        near_limit = []
        for member in members:
            risk = member.get_empath_transfer_risk_state() if hasattr(member, "get_empath_transfer_risk_state") else {}
            if str(risk.get("tier") or "") in {"high", "extreme"} or member.get_empath_shock() >= 60:
                near_limit.append(member)
        return near_limit

    def maybe_trigger_empath_circle_cascade(self, trigger_amount=0, source="transfer"):
        members = self.get_empath_circle_members(include_self=True, validate=True)
        if len(members) <= 1:
            return False
        near_limit = self.get_empath_circle_cascade_risk()
        if len(near_limit) < 2 or int(trigger_amount or 0) < 8:
            return False
        shocked_members = []
        for member in near_limit[:3]:
            member.db.empath_overload_until = max(float(getattr(member.db, "empath_overload_until", 0.0) or 0.0), time.time() + 6.0)
            member.set_empath_wound("fatigue", member.get_empath_wound("fatigue") + 5)
            member.msg("You feel the collapse ripple through you.")
            shocked_members.append(member)
        room = getattr(self, "location", None)
        if room:
            room.msg_contents("The circle fractures under the strain.")
        return bool(shocked_members)

    def get_empath_shock_modifier(self):
        shock = self.get_empath_shock()
        penalties = EMPATH_SYSTEM_CONFIG["shock_penalties"]
        if shock >= int(penalties["major_threshold"]):
            modifier = float(penalties["major_modifier"])
        elif shock >= int(penalties["medium_threshold"]):
            modifier = float(penalties["medium_modifier"])
        elif shock >= int(penalties["minor_threshold"]):
            modifier = float(penalties["minor_modifier"])
        else:
            modifier = 1.0
        if self.is_empath_overdrawn():
            modifier *= 0.8
        return modifier

    def get_empath_strain(self):
        self.ensure_core_defaults()
        if not self.is_empath():
            return 0
        return max(0, min(100, int(getattr(self.db, "empath_strain", 0) or 0)))

    def set_empath_strain(self, value):
        self.ensure_core_defaults()
        if not self.is_empath():
            self.db.empath_strain = 0
            return 0
        old_value = self.get_empath_strain()
        self.db.empath_strain = max(0, min(100, int(value or 0)))
        new_value = self.get_empath_strain()
        if new_value >= 70 > old_value:
            self.msg("The press of nearby life starts to grate at your nerves.")
        elif new_value >= 40 > old_value:
            self.msg("A low empathic strain settles in behind your focus.")
        elif new_value < 20 <= old_value:
            self.msg("The empathic pressure eases off again.")
        self.sync_client_state()
        return new_value

    def adjust_empath_strain(self, amount):
        return self.set_empath_strain(self.get_empath_strain() + int(amount or 0))

    def get_empath_strain_fishing_modifier(self):
        strain = self.get_empath_strain()
        if strain >= 80:
            return 0.70
        if strain >= 60:
            return 0.82
        if strain >= 40:
            return 0.92
        return 1.0

    def get_empath_strain_tangle_modifier(self):
        strain = self.get_empath_strain()
        if strain >= 80:
            return 1.40
        if strain >= 60:
            return 1.22
        if strain >= 40:
            return 1.10
        return 1.0

    def apply_fishing_empath_strain(self, event_key, amount=0, fish_profile=None):
        if not self.is_empath():
            return 0
        difficulty = int((fish_profile or {}).get("difficulty", 0) or 0)
        event = str(event_key or "").strip().lower()
        delta = max(1, int(amount or 0))
        if event == "cast":
            delta = max(1, delta - 1)
        elif event == "hook":
            delta += max(1, int(round(difficulty * 0.04)))
        elif event == "struggle":
            delta += max(1, int(round(difficulty * 0.03)))
        elif event == "landed":
            delta += max(1, int(round(difficulty * 0.05)))
        return self.adjust_empath_strain(delta)

    def decay_empath_strain(self, amount=2):
        if not self.is_empath():
            return 0
        return self.adjust_empath_strain(-max(1, int(amount or 0)))

    def get_empath_shock_state(self, shock=None):
        value = self.get_empath_shock() if shock is None else max(0, min(100, int(shock or 0)))
        if value >= int(EMPATH_SHOCK_THRESHOLDS["disconnected"]):
            return "disconnected"
        if value >= int(EMPATH_SHOCK_THRESHOLDS["dull"]):
            return "dull"
        if value >= int(EMPATH_SHOCK_THRESHOLDS["strained"]):
            return "strained"
        return "clear"

    def get_empath_shock_state_rank(self, shock_state):
        return {"clear": 0, "strained": 1, "dull": 2, "disconnected": 3}.get(str(shock_state or "clear").strip().lower(), 0)

    def get_empath_shock_message(self, shock_state):
        return {
            "clear": "Your empathy steadies again.",
            "strained": "Your focus wavers slightly.",
            "dull": "Your connection feels distant and unreliable.",
            "disconnected": "You feel completely disconnected from others.",
        }.get(str(shock_state or "").strip().lower(), "")

    def get_empath_rank(self):
        return max(0, int(getattr(self.db, "empath_rank", 0) or 0))

    def get_empath_progression_rank(self):
        return self.get_progression_skill_rank("empathy")

    def get_empath_unlock_status(self, unlock_key):
        key = str(unlock_key or "").strip().lower()
        unlock_data = get_empath_unlock(key)
        required_rank = int(unlock_data.get("rank", 0) or 0)
        current_rank = self.get_empath_progression_rank()
        return {
            "key": key,
            "label": unlock_data.get("label", format_empath_unlock_name(key)),
            "required_rank": required_rank,
            "current_rank": current_rank,
            "unlocked": current_rank >= required_rank,
            "failure_message": unlock_data.get("failure_message") or f"You need more Empathy to use {format_empath_unlock_name(key)}.",
        }

    def has_empath_unlock(self, unlock_key):
        return bool(self.get_empath_unlock_status(unlock_key).get("unlocked"))

    def require_empath_unlock(self, unlock_key):
        status = self.get_empath_unlock_status(unlock_key)
        if status.get("unlocked"):
            return True, None
        return False, status.get("failure_message")

    def get_available_empath_unlocks(self):
        available = []
        for unlock_key in sorted(EMPATH_UNLOCKS, key=lambda key: (get_empath_unlock_rank(key), key)):
            status = self.get_empath_unlock_status(unlock_key)
            if status.get("unlocked"):
                available.append(status)
        return available

    def get_locked_empath_unlocks(self):
        locked = []
        for unlock_key in sorted(EMPATH_UNLOCKS, key=lambda key: (get_empath_unlock_rank(key), key)):
            status = self.get_empath_unlock_status(unlock_key)
            if not status.get("unlocked"):
                locked.append(status)
        return locked

    def get_next_empath_unlock_status(self):
        unlock_key, unlock_data = get_next_empath_unlock(self.get_empath_progression_rank())
        if not unlock_key or not unlock_data:
            return None
        return self.get_empath_unlock_status(unlock_key)

    def get_empath_training_stage(self):
        return max(0, int(getattr(self.db, "empath_training_stage", EMPATH_TRAINING_UNSET) or EMPATH_TRAINING_UNSET))

    def set_empath_training_stage(self, value):
        self.db.empath_training_stage = max(0, int(value or 0))
        self.sync_client_state()
        return self.get_empath_training_stage()

    def is_empath_tutorial_active(self):
        return self.get_empath_training_stage() == EMPATH_TRAINING_PATIENT

    def is_empath_apprentice(self):
        return self.get_empath_training_stage() in {EMPATH_TRAINING_PATIENT, EMPATH_TRAINING_BASIC} and self.get_empath_rank() < 1

    def is_empath_join_room(self, room=None):
        room = room or self.location
        return str(getattr(getattr(room, "db", None), "empath_guild_room", "") or "").strip().lower() == "office"

    def is_cleric_join_room(self, room=None):
        room = room or self.location
        return str(getattr(getattr(room, "db", None), "cleric_guild_room", "") or "").strip().lower() == "office"

    def can_begin_profession_oath(self):
        if self.is_dead():
            return False, "The dead do not swear guild oaths."
        if not getattr(self, "location", None):
            return False, "You must be somewhere real before taking an oath."
        return True, None

    def get_empath_tutorial_patient(self):
        patient_id = int(getattr(self.db, "empath_tutorial_patient_id", 0) or 0)
        if patient_id <= 0:
            return None
        result = search_object(f"#{patient_id}")
        patient = result[0] if result else None
        if not patient:
            self.db.empath_tutorial_patient_id = None
        return patient

    def clear_empath_tutorial_patient(self, delete_patient=True):
        patient = self.get_empath_tutorial_patient()
        self.db.empath_tutorial_patient_id = None
        if patient and delete_patient:
            try:
                patient.delete()
            except Exception:
                pass
        return patient

    def spawn_empath_tutorial_patient(self, room=None):
        patient = self.get_empath_tutorial_patient()
        target_room = room or getattr(self, "location", None)
        if not target_room:
            return None
        if not patient:
            patient = create_object(
                "typeclasses.npcs.EmpathTutorialPatient",
                key="Training Patient",
                aliases=["patient", "training patient"],
                location=target_room,
                home=target_room,
            )
            patient.db.empath_tutorial_owner = self.id
            self.db.empath_tutorial_patient_id = patient.id
        if getattr(patient, "location", None) != target_room:
            patient.move_to(target_room, quiet=True, use_destination=False)
        patient.db.desc = "A pale training patient lies on the cot, breathing shallowly but steadily while waiting for an apprentice to begin."
        patient.db.is_npc = True
        patient.db.is_training_dummy = True
        patient.db.is_tutorial_patient = True
        patient.db.empath_tutorial_owner = self.id
        patient.ensure_core_defaults()
        patient.db.hp = max(1, int(getattr(patient.db, "max_hp", 100) or 100) - 10)
        patient.set_empath_wound("vitality", 18)
        patient.set_empath_wound("bleeding", 8)
        patient.set_empath_wound("poison", 0)
        patient.set_empath_wound("disease", 0)
        patient.set_empath_wound("fatigue", 0)
        patient.set_empath_wound("trauma", 0)
        return patient

    def complete_empath_tutorial_if_ready(self, target=None):
        patient = target or self.get_empath_tutorial_patient()
        if not patient or int(getattr(patient, "id", 0) or 0) <= 0:
            return False
        if int(getattr(getattr(patient, "db", None), "empath_tutorial_owner", 0) or 0) != int(getattr(self, "id", 0) or 0):
            return False
        remaining = sum(int(value or 0) for value in dict(patient.get_empath_wounds() if hasattr(patient, "get_empath_wounds") else {}).values())
        if remaining > 0:
            return False
        self.break_empath_link(reason="collapse", emit_message=False)
        self.clear_empath_tutorial_patient(delete_patient=True)
        self.msg("The patient finally steadies under your hands.")
        self.msg("The lesson is not finished. Mend yourself before you call the transfer complete.")
        return True

    def begin_empath_apprenticeship(self, guide=None):
        from world.areas.crossing.empath_guild import ensure_crossing_empath_guildhall

        rooms = ensure_crossing_empath_guildhall()
        training_room = rooms.get("training") or getattr(self, "location", None)
        self.clear_empath_tutorial_patient(delete_patient=True)
        self.break_empath_connections(reason="collapse", emit_message=False)
        self.db.empath_rank = 0
        self.db.empath_xp = 0
        self.set_empath_training_stage(EMPATH_TRAINING_PATIENT)
        patient = self.spawn_empath_tutorial_patient(room=training_room)
        if training_room and getattr(self, "location", None) != training_room:
            self.move_to(training_room, quiet=True, use_destination=False)
        guide_name = getattr(guide, "key", "Merla") if guide else "Merla"
        message = (
            f"{guide_name} studies you for a long moment. 'If you are going to bear pain, you will start with a single body and no excuses.'\n"
            "You are now recognized as an Empath.\n"
            "A training patient waits on the cot before you. Touch the patient."
        )
        return patient, message

    def can_use_empath_ability(self, ability):
        if not self.is_empath():
            return False, "You lack empathic sensitivity."
        state = self.get_empath_shock_state()
        ability_key = str(ability or "").strip().lower()
        if ability_key in EMPATH_TUTORIAL_LOCKED_ABILITIES and self.is_empath_apprentice():
            return False, "You lack the discipline to shape that technique yet."
        unlock_key = EMPATH_ABILITY_UNLOCKS.get(ability_key)
        if unlock_key:
            unlocked, unlock_message = self.require_empath_unlock(unlock_key)
            if not unlocked:
                return False, unlock_message
        if state == "disconnected":
            if ability_key in {"perceive", "perceive_health", "perceive_target"}:
                return False, "You sense nothing."
            return False, "You feel completely cut off from others."
        if float(getattr(self.db, "empath_overload_until", 0.0) or 0.0) > time.time() and ability_key in {"take", "shift", "redirect", "channel"}:
            return False, "You have taken too much. Your senses still reel."
        if state == "dull" and ability_key in {"assess"}:
            return False, "Your senses are too dulled."
        return True, None

    def break_empath_connections(self, reason="shock", emit_message=True):
        changed = self.break_empath_link(reason=reason, emit_message=False)
        unity_changed = False
        if self.get_empath_unity_state():
            unity_changed = self.clear_empath_unity(sync_members=True, emit_message=False)
        if emit_message and (changed or unity_changed):
            if reason == "shock":
                self.msg("Every connection slips beyond your reach.")
            elif reason == "distance":
                self.msg("Distance tears the shared burden apart.")
            else:
                self.msg("Your connection slips away.")
        return changed or unity_changed

    def normalize_empath_wound_key(self, wound_type):
        key = str(wound_type or "").strip().lower()
        return EMPATH_WOUND_ALIASES.get(key, key)

    def normalize_empath_take_selector(self, selector):
        key = str(selector or "").strip().lower()
        return key if key in EMPATH_SELECTIVE_TAKE_BUCKETS else ""

    def resolve_empath_take_bucket(self, target, selector):
        selector_key = self.normalize_empath_take_selector(selector)
        if not selector_key or not target or not hasattr(target, "get_empath_wounds"):
            return ""
        target_wounds = target.get_empath_wounds()
        for bucket in EMPATH_SELECTIVE_TAKE_BUCKETS.get(selector_key, ()):
            value = target_wounds.get(bucket)
            if value and int(value) > 0:
                return bucket
        return ""

    def resolve_default_empath_take_bucket(self, target):
        if not target or not hasattr(target, "get_empath_wounds"):
            return ""
        target_wounds = target.get_empath_wounds()
        available = []
        for bucket in EMPATH_PARTIAL_TAKE_BUCKET_PRIORITY:
            value = target_wounds.get(bucket)
            if not value or int(value) <= 0:
                continue
            available.append((int(value), bucket))
        if not available:
            return ""
        available.sort(key=lambda entry: (-entry[0], EMPATH_PARTIAL_TAKE_BUCKET_PRIORITY.index(entry[1])))
        return available[0][1]

    def normalize_empath_wounds(self, wounds=None):
        normalized = dict(_copy_default_empath_wounds())
        source = dict(wounds or {})
        for old_key, new_key in EMPATH_WOUND_ALIASES.items():
            if old_key in source and new_key not in source:
                source[new_key] = source.get(old_key, 0)
        for key in normalized:
            normalized[key] = max(0, min(100, int(source.get(key, 0) or 0)))
        return normalized

    def get_empath_transfer_skill_modifier(self):
        skill = int(self.get_skill("empathy") if hasattr(self, "get_skill") else 0)
        return min(1.2, 0.85 + (skill / 300.0))

    def get_empath_mitigation(self):
        if not self.has_empath_unlock("wound_reduction"):
            return 1.0
        skill = int(self.get_empath_progression_rank())
        shock = int(self.get_empath_shock() if hasattr(self, "get_empath_shock") else getattr(self.db, "empath_shock", 0) or 0)
        base = 0.9 - (skill * 0.002)
        penalty = shock * 0.001
        return max(0.5, min(1.0, base + penalty))

    def get_empath_room_zone(self, room=None):
        current_room = room or getattr(self, "location", None)
        if not current_room:
            return ""
        for zone_name, tag_name in EMPATH_GUILD_ZONE_TAGS.items():
            try:
                if current_room.tags.has(tag_name):
                    return zone_name
            except Exception:
                continue
        return str(getattr(getattr(current_room, "db", None), "empath_zone", "") or "").strip().lower()

    def is_empath_zone(self, zone_name, room=None):
        return self.get_empath_room_zone(room=room) == str(zone_name or "").strip().lower()

    def get_empath_recovery_modifier(self):
        disease = self.get_empath_wound("disease") if hasattr(self, "get_empath_wound") else 0
        if disease <= 0:
            return 1.0
        return max(0.35, 1.0 - (int(disease) / 140.0))

    def get_empath_healing_modifier(self):
        return self.get_empath_shock_modifier() * self.get_empath_recovery_modifier()

    def normalize_empath_link_type(self, link_type):
        normalized = str(link_type or EMPATH_LINK_TOUCH).strip().lower()
        if normalized in {"standard", "link", "deep", "strong"}:
            normalized = EMPATH_LINK_DIRECT
        if normalized not in EMPATH_LINK_TYPES:
            normalized = EMPATH_LINK_TOUCH
        return normalized

    def get_empath_link_priority(self, link_type):
        return int(EMPATH_LINK_PRIORITY.get(self.normalize_empath_link_type(link_type), 0) or 0)

    def normalize_empath_link_state(self, link_state=None):
        raw = getattr(self.db, "empath_link", None) if link_state is None else link_state
        if raw in (None, False, 0, ""):
            return None
        if isinstance(raw, int):
            raw = {
                "target_id": int(raw),
                "type": EMPATH_LINK_TOUCH,
                "strength": 60,
                "stability": 80,
                "created_at": time.time(),
            }
        if not isinstance(raw, Mapping):
            return None
        target_id = int(raw.get("target_id", 0) or 0)
        if target_id <= 0:
            return None
        link_type = self.normalize_empath_link_type(raw.get("type"))
        default_strength = int(EMPATH_LINK_BASE_STRENGTH.get(link_type, 60) or 60)
        default_stability = int(EMPATH_LINK_BASE_STABILITY.get(link_type, 100) or 100)
        return {
            "target_id": target_id,
            "type": link_type,
            "strength": max(1, min(100, int(raw.get("strength", default_strength) or default_strength))),
            "stability": max(0, min(150, int(raw.get("stability", default_stability) or default_stability))),
            "link_bonus_skill": str(raw.get("link_bonus_skill", "") or "").strip().lower() or None,
            "link_bonus_value": max(0, int(raw.get("link_bonus_value", 0) or 0)),
            "link_bonus_tick_at": float(raw.get("link_bonus_tick_at", 0.0) or 0.0),
            "created_at": float(raw.get("created_at", time.time()) or time.time()),
        }

    def get_empath_link_target(self, target_id):
        lookup_id = 0
        if isinstance(target_id, Mapping):
            state = self.normalize_empath_link_state(target_id)
            if state:
                lookup_id = int(state.get("target_id", 0) or 0)
            else:
                lookup_id = int(target_id.get("target_id", target_id.get("id", 0)) or 0)
        elif hasattr(target_id, "id"):
            lookup_id = int(getattr(target_id, "id", 0) or 0)
        else:
            try:
                lookup_id = int(target_id or 0)
            except (TypeError, ValueError):
                lookup_id = 0
        if lookup_id <= 0:
            return None
        result = search_object(f"#{lookup_id}")
        return result[0] if result else None

    def get_empath_link_strength(self, link_data=None, target=None):
        state = self.normalize_empath_link_state(link_data)
        if not state:
            return 0
        return int(state.get("strength", 0) or 0)

    def get_empath_link_strength_label(self, strength):
        value = max(0, min(100, int(strength or 0)))
        if value >= 75:
            return "Strong"
        if value >= 45:
            return "Steady"
        if value >= 20:
            return "Weak"
        return "Fraying"

    def get_empath_link_condition(self, stability):
        value = max(0, min(100, int(stability or 0)))
        if value >= 75:
            return "steady"
        if value >= 40:
            return "strained"
        if value > 0:
            return "fragile"
        return "broken"

    def get_empath_unity_condition(self, stability):
        value = max(0, min(100, int(stability or 0)))
        if value >= 70:
            return "steady"
        if value >= 40:
            return "strained"
        if value > 0:
            return "fragile"
        return "broken"

    def sync_empath_link_pointer(self):
        state = self.normalize_empath_link_state()
        if not state:
            self.db.active_link = None
            self.db.empath_link = None
            self.db.empath_links = {}
            return
        self.db.empath_link = dict(state)
        self.db.active_link = int(state.get("target_id", 0) or 0)
        self.db.empath_links = {
            str(self.db.active_link): {
                "target_id": self.db.active_link,
                "type": state.get("type"),
                "strength": int(state.get("strength", 0) or 0),
                "stability": int(state.get("stability", 0) or 0),
                "link_bonus_skill": state.get("link_bonus_skill"),
                "link_bonus_value": int(state.get("link_bonus_value", 0) or 0),
                "link_bonus_tick_at": float(state.get("link_bonus_tick_at", 0.0) or 0.0),
                "created_at": float(state.get("created_at", time.time()) or time.time()),
            }
        }

    def set_empath_link_state(self, link_state, sync=True):
        if link_state in (None, False):
            self.db.empath_link = None
            self.sync_empath_link_pointer()
            if sync:
                self.sync_client_state()
            return None
        normalized = self.normalize_empath_link_state(link_state)
        self.db.empath_link = dict(normalized) if normalized else None
        self.sync_empath_link_pointer()
        if sync:
            self.sync_client_state()
        return dict(self.db.empath_link) if self.db.empath_link else None

    def set_empath_links(self, links, sync=True):
        normalized = None
        if isinstance(links, Mapping):
            candidates = []
            for raw_data in links.values():
                state = self.normalize_empath_link_state(raw_data)
                if state:
                    candidates.append(state)
            if candidates:
                candidates.sort(key=lambda entry: (self.get_empath_link_priority(entry.get("type")), int(entry.get("strength", 0) or 0)), reverse=True)
                normalized = candidates[0]
        else:
            normalized = self.normalize_empath_link_state(links)
        return self.set_empath_link_state(normalized, sync=sync)

    def prune_empath_links(self, sync=False):
        state = self.get_empath_link_state(require_local=False, emit_break_messages=False)
        if not state:
            if getattr(self.db, "empath_link", None) or getattr(self.db, "empath_links", None) or getattr(self.db, "active_link", None):
                self.set_empath_link_state(None, sync=sync)
            return {}
        self.sync_empath_link_pointer()
        if sync:
            self.sync_client_state()
        return dict(getattr(self.db, "empath_links", {}) or {})

    def get_empath_link_state(self, require_local=False, target=None, emit_break_messages=False):
        self.ensure_core_defaults()
        state = self.normalize_empath_link_state()
        if not state:
            self.sync_empath_link_pointer()
            return None
        target_obj = self.get_empath_link_target(state.get("target_id"))
        if not target_obj or target_obj == self:
            self.break_empath_link(reason="collapse", emit_message=emit_break_messages)
            return None
        if target is not None and int(getattr(target, "id", target) or 0) != int(state.get("target_id", 0) or 0):
            return None
        if self.get_empath_shock() >= int(EMPATH_SHOCK_THRESHOLDS["disconnected"]):
            self.break_empath_link(reason="shock", emit_message=emit_break_messages)
            return None
        is_local = getattr(target_obj, "location", None) == getattr(self, "location", None)
        if require_local and not is_local:
            self.break_empath_link(reason="distance", emit_message=emit_break_messages)
            return None
        enriched = {
            **dict(state),
            "target": target_obj,
            "is_local": is_local,
            "priority": self.get_empath_link_priority(state.get("type")),
            "strength_label": self.get_empath_link_strength_label(state.get("strength", 0)),
            "condition": self.get_empath_link_condition(state.get("stability", 0)),
            "remaining": 0,
        }
        self.db.empath_link = dict(state)
        self.sync_empath_link_pointer()
        return enriched

    def get_empath_links(self, require_local=False, include_group=False):
        state = self.get_empath_link_state(require_local=require_local, emit_break_messages=False)
        if not state:
            return []
        if not include_group and state.get("type") == EMPATH_LINK_GROUP:
            return []
        return [state]

    def get_primary_empath_link(self, require_local=False, include_group=False):
        links = self.get_empath_links(require_local=require_local, include_group=include_group)
        return links[0] if links else None

    def get_empath_link(self, target, require_local=False, include_group=False):
        target_id = int(getattr(target, "id", target) or 0)
        if target_id <= 0:
            return None
        for entry in self.get_empath_links(require_local=require_local, include_group=include_group):
            if int(entry.get("target_id", 0) or 0) == target_id:
                return entry
        return None

    def get_empath_link_transfer_modifier(self, target=None):
        primary = self.get_empath_link_state(require_local=False, target=target, emit_break_messages=False)
        if not primary:
            return 0.0
        return max(0.0, min(1.0, float(int(primary.get("strength", 0) or 0) / 100.0)))

    def get_empath_link_stability_cost(self, link_type, event_key):
        rules = EMPATH_LINK_STABILITY_RULES.get(self.normalize_empath_link_type(link_type), {})
        return max(0, int(rules.get(str(event_key or "").strip().lower(), 0) or 0))

    def get_empath_link_backlash_modifier(self, target=None):
        primary = self.get_empath_link_state(require_local=False, target=target, emit_break_messages=False)
        if not primary:
            return 1.1
        return max(0.55, 1.1 - (int(primary.get("strength", 0) or 0) / 200.0))

    def refresh_empath_link(self, target, bonus_seconds=0, deepen=False):
        state = self.get_empath_link_state(require_local=False, target=target, emit_break_messages=False)
        if not state:
            return None
        refreshed = dict(state)
        if deepen and refreshed.get("type") == EMPATH_LINK_TOUCH:
            refreshed["type"] = EMPATH_LINK_DIRECT
            refreshed["strength"] = 100
        refreshed["stability"] = max(0, min(100, int(refreshed.get("stability", 0) or 0) + int(bonus_seconds or 0)))
        return self.set_empath_link_state(refreshed, sync=False)

    def create_empath_link(self, target, link_type=EMPATH_LINK_TOUCH, deepen=False):
        if not self.is_empath():
            return False, ["You lack the sensitivity to establish an empathic link."]
        allowed, message = self.can_use_empath_ability("link" if self.normalize_empath_link_type(link_type) != EMPATH_LINK_TOUCH else "touch")
        if not allowed:
            return False, [message]
        if not target or target == self or getattr(target, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        link_type = self.normalize_empath_link_type(link_type)
        if link_type == EMPATH_LINK_GROUP:
            return False, ["You have not mastered that kind of bond yet."]
        if link_type == EMPATH_LINK_PERSISTENT and self.get_empath_unity_state():
            return False, ["You cannot settle into a persistent link while a shared burden is active."]
        link_state = {
            "target_id": target.id,
            "type": link_type,
            "strength": int(EMPATH_LINK_BASE_STRENGTH.get(link_type, 60) or 60),
            "stability": int(EMPATH_LINK_BASE_STABILITY.get(link_type, 80) or 80),
            "created_at": time.time(),
        }
        if deepen:
            link_state["type"] = EMPATH_LINK_DIRECT
            link_state["strength"] = 100
            link_state["stability"] = 100
        self.set_empath_link_state(link_state, sync=False)
        self.award_empathy_experience("link", max(10, sum(target.sync_empath_wounds_from_resources().values())), target=target)
        self.sync_client_state()
        return True, self.get_empath_link_state(require_local=False, emit_break_messages=False)

    def resolve_empath_link_target(self, query, require_local=True):
        lookup = str(query or "").strip().lower()
        if not lookup:
            return None
        entry = self.get_empath_link_state(require_local=require_local, emit_break_messages=False)
        target = entry.get("target") if entry else None
        if target:
            if target.key.lower() == lookup:
                return target
            aliases = [str(alias).lower() for alias in getattr(getattr(target, "aliases", None), "all", lambda: [])()]
            if lookup in aliases:
                return target
        return None

    def decay_empath_link_stability(self, amount=None, reason="strain", emit_message=True):
        state = self.get_empath_link_state(require_local=False, emit_break_messages=False)
        if not state:
            return None
        cost = self.get_empath_link_stability_cost(state.get("type"), reason) if amount is None else max(0, int(amount or 0))
        updated = dict(state)
        updated["stability"] = max(0, int(updated.get("stability", 0) or 0) - cost)
        if updated["stability"] <= 0:
            self.break_empath_link(reason="collapse", emit_message=emit_message)
            return None
        self.set_empath_link_state(updated, sync=True)
        return self.get_empath_link_state(require_local=False, emit_break_messages=False)

    def break_empath_link(self, reason="collapse", emit_message=True):
        state = self.normalize_empath_link_state()
        if not state:
            self.set_empath_link_state(None, sync=True)
            return False
        self.set_empath_link_state(None, sync=True)
        if emit_message:
            if reason == "shock":
                self.msg("You lose all sense of your patient.")
            elif reason == "distance":
                self.msg("Distance tears your connection apart.")
            else:
                self.msg("Your connection slips away.")
        return True

    def is_empath_overdrawn(self):
        state = self.get_state("empath_overdraw")
        if not isinstance(state, Mapping):
            return False
        expires_at = float(state.get("expires_at", 0) or 0)
        if expires_at and time.time() >= expires_at:
            self.clear_state("empath_overdraw")
            self.msg("Your senses steady again.")
            return False
        return True

    def maybe_trigger_empath_overdraw(self):
        if not self.is_empath():
            return False
        config = EMPATH_SYSTEM_CONFIG["overdraw"]
        carried = sum(int(value or 0) for value in self.get_empath_wounds().values())
        fatigue = int(self.db.fatigue or 0)
        if carried < int(config["wound_threshold"]) and fatigue < int(config["fatigue_threshold"]):
            return False
        if self.is_empath_overdrawn():
            return True
        self.set_state(
            "empath_overdraw",
            {
                "expires_at": time.time() + float(config["duration"]),
                "carried": carried,
                "fatigue": fatigue,
            },
        )
        self.msg("You have taken too much. Your senses falter.")
        return True

    def remove_empath_link(self, target=None, clear_all=False):
        state = self.normalize_empath_link_state()
        if not state:
            self.set_empath_link_state(None, sync=True)
            return False
        if not clear_all and target is not None:
            target_id = int(getattr(target, "id", target) or 0)
            if target_id != int(state.get("target_id", 0) or 0):
                return False
        self.set_empath_link_state(None, sync=True)
        self.clear_empath_unity(sync_members=True, emit_message=False)
        return True

    def get_empath_unity_state(self, emit_break_messages=False):
        self.ensure_core_defaults()
        data = getattr(self.db, "empath_unity", None)
        if not isinstance(data, Mapping):
            return None
        primary_target_id = int(data.get("primary_target_id", 0) or 0)
        secondary_target_id = int(data.get("secondary_target_id", 0) or 0)
        if primary_target_id <= 0 or secondary_target_id <= 0:
            self.clear_empath_unity(sync_members=True, emit_message=False)
            return None
        base_link = self.get_empath_link_state(require_local=True, emit_break_messages=False)
        if not base_link or int(base_link.get("target_id", 0) or 0) != primary_target_id:
            self.clear_empath_unity(sync_members=True, emit_message=False)
            if emit_break_messages:
                self.msg("Distance tears the shared burden apart.")
            return None
        primary_target = base_link.get("target")
        secondary_target = self.get_empath_link_target(secondary_target_id)
        if not secondary_target:
            self.clear_empath_unity(sync_members=True, emit_message=False)
            return None
        if getattr(primary_target, "location", None) != getattr(self, "location", None) or getattr(secondary_target, "location", None) != getattr(self, "location", None):
            self.clear_empath_unity(sync_members=True, emit_message=False)
            if emit_break_messages:
                self.msg("Distance tears the shared burden apart.")
            return None
        stability = max(0, min(100, int(data.get("stability", 80) or 80)))
        return {
            "primary_target_id": primary_target_id,
            "secondary_target_id": secondary_target_id,
            "primary_target": primary_target,
            "secondary_target": secondary_target,
            "stability": stability,
            "condition": self.get_empath_unity_condition(stability),
            "members": [primary_target, secondary_target],
        }

    def clear_empath_unity(self, sync_members=True, emit_message=False):
        unity = getattr(self.db, "empath_unity", None)
        if not isinstance(unity, Mapping):
            return False
        self.db.empath_unity = None
        self.sync_client_state()
        if emit_message:
            self.msg("The shared bond comes apart.")
        return True

    def _normalize_empath_circle_member_ids(self, raw_members=None):
        members = []
        for entry in list(raw_members if raw_members is not None else getattr(self.db, "empath_circle_members", []) or []):
            try:
                member_id = int(entry or 0)
            except (TypeError, ValueError):
                continue
            if member_id > 0 and member_id not in members:
                members.append(member_id)
        return members

    def _normalize_empath_circle_invites(self):
        invites = []
        now = time.time()
        for entry in list(getattr(self.db, "empath_circle_invites", []) or []):
            if not isinstance(entry, Mapping):
                continue
            leader_id = int(entry.get("leader_id", 0) or 0)
            expires_at = float(entry.get("expires_at", 0.0) or 0.0)
            if leader_id <= 0:
                continue
            if expires_at and now >= expires_at:
                continue
            invites.append({"leader_id": leader_id, "expires_at": expires_at, "created_at": float(entry.get("created_at", now) or now)})
        self.db.empath_circle_invites = invites
        return invites

    def get_empath_circle_leader_id(self):
        leader_id = int(getattr(self.db, "empath_circle_leader", 0) or 0)
        if leader_id > 0:
            return leader_id
        members = self._normalize_empath_circle_member_ids()
        if int(getattr(self, "id", 0) or 0) in members:
            return int(getattr(self, "id", 0) or 0)
        return 0

    def get_empath_circle_member_ids(self, include_self=True):
        leader_id = self.get_empath_circle_leader_id()
        members = self._normalize_empath_circle_member_ids()
        if leader_id > 0 and leader_id not in members:
            members.insert(0, leader_id)
        self_id = int(getattr(self, "id", 0) or 0)
        if include_self and self_id > 0 and self_id not in members and (leader_id == self_id or leader_id > 0):
            members.append(self_id)
        if not include_self:
            members = [member_id for member_id in members if member_id != self_id]
        return members[:3]

    def get_empath_circle_members(self, include_self=True, validate=False):
        if validate:
            self.validate_empath_circle_state(sync_members=True, emit_message=False)
        seen = []
        for member_id in self.get_empath_circle_member_ids(include_self=include_self):
            member = self.get_empath_link_target(member_id)
            if member and member not in seen:
                seen.append(member)
        return seen

    def is_in_empath_circle(self):
        return bool(self.get_empath_circle_leader_id())

    def is_empath_circle_leader(self):
        return int(getattr(self, "id", 0) or 0) > 0 and int(getattr(self, "id", 0) or 0) == self.get_empath_circle_leader_id()

    def get_empath_burden_soft_label(self):
        risk = self.get_empath_transfer_risk_state() if hasattr(self, "get_empath_transfer_risk_state") else {}
        tier = str(risk.get("tier") or "steady")
        if self.is_empath_overloaded() if hasattr(self, "is_empath_overloaded") else False:
            return "reeling"
        if tier == "extreme":
            return "breaking"
        if tier == "high":
            return "strained"
        if tier == "elevated":
            return "loaded"
        return "steady"

    def get_empath_reputation_label(self):
        score = int(getattr(self.db, "empath_reputation_score", 0) or 0)
        if score >= 4:
            return "trusted"
        if score <= -3:
            return "unreliable"
        return "unknown"

    def record_tip_history(self, target, amount):
        if not target:
            return {}
        history = dict(getattr(self.db, "tip_history", {}) or {})
        target_id = str(int(getattr(target, "id", 0) or 0))
        entry = dict(history.get(target_id, {}) or {})
        entry["total"] = int(entry.get("total", 0) or 0) + int(amount or 0)
        entry["last"] = time.time()
        entry["target"] = getattr(target, "key", "")
        history[target_id] = entry
        self.db.tip_history = history
        return entry

    def get_tip_history_for(self, target):
        if not target:
            return {}
        history = dict(getattr(self.db, "tip_history", {}) or {})
        return dict(history.get(str(int(getattr(target, "id", 0) or 0)), {}) or {})

    def adjust_empath_reputation(self, amount, reason=""):
        current = int(getattr(self.db, "empath_reputation_score", 0) or 0)
        updated = max(-20, min(20, current + int(amount or 0)))
        self.db.empath_reputation_score = updated
        return updated

    def note_empath_handler_activity(self, target, action="take", duration=12.0):
        if not target:
            return {}
        handlers = dict(getattr(getattr(target, "ndb", None), "empath_active_handlers", {}) or {})
        target_id = int(getattr(self, "id", 0) or 0)
        handlers[target_id] = {
            "handler": self,
            "handler_name": getattr(self, "key", ""),
            "action": str(action or "take"),
            "expires_at": time.time() + max(3.0, float(duration or 0.0)),
            "circle": bool(self.get_empath_circle_members(include_self=False, validate=True)),
        }
        target.ndb.empath_active_handlers = handlers
        return handlers

    def get_empath_active_handlers(self, target):
        if not target:
            return []
        now = time.time()
        handlers = []
        raw_handlers = dict(getattr(getattr(target, "ndb", None), "empath_active_handlers", {}) or {})
        normalized = {}
        for handler_id, payload in raw_handlers.items():
            if not isinstance(payload, Mapping):
                continue
            expires_at = float(payload.get("expires_at", 0.0) or 0.0)
            if expires_at and now >= expires_at:
                continue
            normalized[int(handler_id)] = dict(payload)
            handlers.append(dict(payload))
        target.ndb.empath_active_handlers = normalized
        return handlers

    def get_empath_transfer_pressure(self, target):
        handlers = self.get_empath_active_handlers(target)
        active_other_handlers = [entry for entry in handlers if int(getattr(entry.get("handler"), "id", 0) or 0) != int(getattr(self, "id", 0) or 0)]
        shared_circle = any(bool(entry.get("circle", False)) for entry in handlers)
        corpse_target = bool(getattr(getattr(target, "db", None), "is_corpse", False))
        return {
            "active_handlers": handlers,
            "other_handler_count": len(active_other_handlers),
            "efficiency_modifier": 1.0 if corpse_target or not active_other_handlers else max(0.6, 1.0 - (0.18 * len(active_other_handlers))),
            "instability_multiplier": 1.0 if corpse_target or not active_other_handlers else min(1.8, 1.0 + (0.25 * len(active_other_handlers))),
            "shared_circle": shared_circle,
        }

    def get_empath_queue_context_labels(self, target):
        labels = []
        pressure = self.get_empath_transfer_pressure(target)
        if pressure.get("other_handler_count", 0) > 0:
            labels.append("being handled")
        context = dict(getattr(self.db, "empath_triage_context", {}) or {})
        cached = dict(context.get(str(int(getattr(target, "id", 0) or 0)), {}) or {})
        if cached and time.time() - float(cached.get("last_seen_at", 0.0) or 0.0) > 30.0 and pressure.get("other_handler_count", 0) <= 0:
            labels.append("ignored")
        if pressure.get("shared_circle"):
            labels.append("shared load")
        return labels

    def clear_empath_circle(self, sync_members=True, emit_message=False):
        member_ids = self.get_empath_circle_member_ids(include_self=False)
        self.db.empath_circle_members = []
        self.db.empath_circle_leader = None
        if emit_message:
            self.msg("The shock circle comes apart.")
        if sync_members:
            for member_id in member_ids:
                member = self.get_empath_link_target(member_id)
                if not member or member == self:
                    continue
                member.db.empath_circle_members = []
                member.db.empath_circle_leader = None
        return True

    def validate_empath_circle_state(self, sync_members=True, emit_message=False):
        if not self.is_empath():
            return self.clear_empath_circle(sync_members=sync_members, emit_message=False)
        leader_id = self.get_empath_circle_leader_id()
        if leader_id <= 0:
            self.db.empath_circle_members = []
            self.db.empath_circle_leader = None
            return []
        leader = self.get_empath_link_target(leader_id)
        if not leader or not getattr(leader, "is_empath", lambda: False)():
            self.clear_empath_circle(sync_members=sync_members, emit_message=emit_message)
            return []
        room = getattr(self, "location", None)
        if not room or getattr(leader, "location", None) != room:
            self.clear_empath_circle(sync_members=sync_members, emit_message=emit_message)
            return []
        validated_ids = []
        for member_id in leader._normalize_empath_circle_member_ids(getattr(leader.db, "empath_circle_members", []) or []):
            member = self.get_empath_link_target(member_id)
            if not member or getattr(member, "location", None) != room or not getattr(member, "is_empath", lambda: False)():
                continue
            validated_ids.append(int(member.id))
        if leader_id not in validated_ids:
            validated_ids.insert(0, leader_id)
        validated_ids = validated_ids[:3]
        if len(validated_ids) <= 1:
            leader.db.empath_circle_members = []
            leader.db.empath_circle_leader = None
            if self != leader:
                self.db.empath_circle_members = []
                self.db.empath_circle_leader = None
            return []
        for member_id in validated_ids:
            member = self.get_empath_link_target(member_id)
            if not member:
                continue
            member.db.empath_circle_leader = leader_id
            member.db.empath_circle_members = list(validated_ids)
        return validated_ids

    def invite_empath_circle_member(self, target, duration=30.0):
        if not self.is_empath():
            return False, "Only empaths can form a shock circle."
        if not target or target == self or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        if not getattr(target, "is_empath", lambda: False)():
            return False, "Only another empath can share a circle with you."
        if target.is_in_empath_circle() and target.get_empath_circle_leader_id() != int(getattr(self, "id", 0) or 0):
            return False, f"{target.key} is already committed to another circle."
        member_ids = self.validate_empath_circle_state(sync_members=True, emit_message=False)
        leader_id = self.get_empath_circle_leader_id()
        if leader_id and leader_id != int(getattr(self, "id", 0) or 0):
            return False, "Only the circle leader can invite another empath."
        if not leader_id:
            self.db.empath_circle_leader = int(getattr(self, "id", 0) or 0)
            self.db.empath_circle_members = [int(getattr(self, "id", 0) or 0)]
        current_ids = member_ids or [int(getattr(self, "id", 0) or 0)]
        if len([member_id for member_id in current_ids if member_id > 0]) >= 3:
            return False, "Your shock circle is already full."
        invites = [entry for entry in target._normalize_empath_circle_invites() if int(entry.get("leader_id", 0) or 0) != int(getattr(self, "id", 0) or 0)]
        invites.append({"leader_id": int(getattr(self, "id", 0) or 0), "created_at": time.time(), "expires_at": time.time() + max(10.0, float(duration or 0.0))})
        target.db.empath_circle_invites = invites
        target.msg(f"{self.key} invites you into a shock circle. Use 'circle accept {self.key}'.")
        return True, f"You invite {target.key} into your shock circle."

    def accept_empath_circle_invite(self, target):
        if not self.is_empath():
            return False, "Only empaths can join a shock circle."
        if not target or target == self or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        if not getattr(target, "is_empath", lambda: False)():
            return False, "Only another empath can lead a shock circle."
        target.validate_empath_circle_state(sync_members=True, emit_message=False)
        invites = self._normalize_empath_circle_invites()
        if int(getattr(target, "id", 0) or 0) not in {int(entry.get("leader_id", 0) or 0) for entry in invites}:
            return False, f"{target.key} has not invited you into a shock circle."
        if self.is_in_empath_circle() and self.get_empath_circle_leader_id() != int(getattr(target, "id", 0) or 0):
            self.clear_empath_circle(sync_members=True, emit_message=False)
        current_ids = target.get_empath_circle_member_ids(include_self=True)
        if not current_ids:
            current_ids = [int(getattr(target, "id", 0) or 0)]
            target.db.empath_circle_leader = int(getattr(target, "id", 0) or 0)
            target.db.empath_circle_members = list(current_ids)
        if len([member_id for member_id in current_ids if member_id > 0]) >= 3 and int(getattr(self, "id", 0) or 0) not in current_ids:
            return False, f"{target.key}'s shock circle is already full."
        merged_ids = []
        for member_id in [*current_ids, int(getattr(self, "id", 0) or 0)]:
            if member_id > 0 and member_id not in merged_ids:
                merged_ids.append(member_id)
        merged_ids = merged_ids[:3]
        for member_id in merged_ids:
            member = self.get_empath_link_target(member_id)
            if not member:
                continue
            member.db.empath_circle_leader = int(getattr(target, "id", 0) or 0)
            member.db.empath_circle_members = list(merged_ids)
        self.db.empath_circle_invites = [entry for entry in invites if int(entry.get("leader_id", 0) or 0) != int(getattr(target, "id", 0) or 0)]
        return True, f"You join {target.key}'s shock circle."

    def leave_empath_circle(self):
        member_ids = self.get_empath_circle_member_ids(include_self=True)
        if len(member_ids) <= 1:
            self.clear_empath_circle(sync_members=True, emit_message=False)
            return False, "You are not part of a shock circle."
        self_id = int(getattr(self, "id", 0) or 0)
        remaining_ids = [member_id for member_id in member_ids if member_id != self_id]
        self.db.empath_circle_members = []
        self.db.empath_circle_leader = None
        if len(remaining_ids) <= 1:
            for member_id in remaining_ids:
                member = self.get_empath_link_target(member_id)
                if member:
                    member.db.empath_circle_members = []
                    member.db.empath_circle_leader = None
            return True, "You step out of the shock circle."
        new_leader_id = remaining_ids[0]
        for member_id in remaining_ids:
            member = self.get_empath_link_target(member_id)
            if not member:
                continue
            member.db.empath_circle_leader = new_leader_id
            member.db.empath_circle_members = list(remaining_ids)
        return True, "You step out of the shock circle."

    def get_empath_circle_status_lines(self):
        member_ids = self.validate_empath_circle_state(sync_members=True, emit_message=False)
        if not member_ids:
            invites = self._normalize_empath_circle_invites()
            lines = ["Shock Circle: none"]
            if invites:
                inviter_names = []
                for entry in invites:
                    inviter = self.get_empath_link_target(entry.get("leader_id"))
                    if inviter:
                        inviter_names.append(inviter.key)
                if inviter_names:
                    lines.append(f"Invites: {', '.join(inviter_names)}")
            return lines
        leader_id = self.get_empath_circle_leader_id()
        lines = [f"Shock Circle Leader: {getattr(self.get_empath_link_target(leader_id), 'key', self.key)}"]
        lines.append("Members:")
        for member in self.get_empath_circle_members(include_self=True):
            label = member.get_empath_burden_soft_label() if hasattr(member, "get_empath_burden_soft_label") else "steady"
            reputation = member.get_empath_reputation_label() if hasattr(member, "get_empath_reputation_label") else "unknown"
            lines.append(f"  {member.key}: {label} ({reputation})")
        return lines

    def create_empath_unity(self, targets):
        if not self.is_empath():
            return False, "You do not know how to weave unity."
        allowed, message = self.can_use_empath_ability("unity")
        if not allowed:
            return False, message
        base_link = self.get_empath_link_state(require_local=True, emit_break_messages=True)
        if not base_link or base_link.get("type") not in {EMPATH_LINK_DIRECT, EMPATH_LINK_PERSISTENT}:
            return False, "You need an active direct or persistent link first."
        if self.get_empath_unity_state():
            return False, "You are already holding a shared burden together."
        if isinstance(targets, (list, tuple)):
            target = targets[0] if targets else None
        else:
            target = targets
        if not target or target == self or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        if int(getattr(target, "id", 0) or 0) == int(base_link.get("target_id", 0) or 0):
            return False, "They are already your linked patient."
        self.db.empath_unity = {
            "primary_target_id": int(base_link.get("target_id", 0) or 0),
            "secondary_target_id": int(target.id),
            "stability": 80,
            "created_at": time.time(),
        }
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + 5)
        self.award_empathy_experience("unity", 20, amount=10, target=target, unity=True)
        self.sync_client_state()
        return True, "You weave a frail bond between burdens."

    def decay_empath_unity_stability(self, amount=None, event_key="transfer", emit_message=True):
        unity = self.get_empath_unity_state()
        if not unity:
            return None
        cost = max(0, int(amount if amount is not None else EMPATH_UNITY_STABILITY_RULES.get(str(event_key or "").strip().lower(), 0) or 0))
        if cost <= 0:
            return unity
        old_stability = int(unity.get("stability", 0) or 0)
        new_stability = max(0, old_stability - cost)
        self.db.empath_unity = {
            "primary_target_id": int(unity.get("primary_target_id", 0) or 0),
            "secondary_target_id": int(unity.get("secondary_target_id", 0) or 0),
            "stability": new_stability,
            "created_at": float(dict(getattr(self.db, "empath_unity", {}) or {}).get("created_at", time.time()) or time.time()),
        }
        self.sync_client_state()
        if new_stability <= 0:
            self.clear_empath_unity(sync_members=True, emit_message=emit_message)
            return None
        if emit_message and old_stability >= 40 and new_stability < 40:
            self.msg("The shared tension begins to fray.")
        return self.get_empath_unity_state()

    def redirect_empath_wound(self, wound_type, amount_spec, dest_target):
        if not self.is_empath():
            return False, "You do not know how to redirect pain that way."
        allowed, message = self.can_use_empath_ability("redirect")
        if not allowed:
            return False, message
        link_state = self.get_empath_link_state(require_local=True, emit_break_messages=True)
        if not link_state:
            return False, "You need an active link first."
        unity = self.get_empath_unity_state(emit_break_messages=True)
        if not unity:
            return False, "You need an active unity bond first."
        source_target = link_state.get("target")
        if not dest_target or getattr(dest_target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        if int(getattr(dest_target, "id", 0) or 0) != int(unity.get("secondary_target_id", 0) or 0):
            return False, "You can only redirect into your current unity partner."
        wound_key = self.normalize_empath_wound_key(wound_type)
        if wound_key not in DEFAULT_EMPATH_WOUNDS:
            return False, "You cannot redirect that wound."
        source_amount = source_target.get_empath_wound(wound_key)
        if source_amount <= 0:
            return False, f"{source_target.key} is not suffering from that wound."
        raw_spec = str(amount_spec or "").strip().lower()
        if raw_spec == "all":
            amount = source_amount
        else:
            try:
                amount = max(1, int(raw_spec or 10))
            except ValueError:
                return False, "Give a number or 'all'."
        amount = min(amount, source_amount)
        source_target.set_empath_wound(wound_key, source_amount - amount)
        dest_target.set_empath_wound(wound_key, dest_target.get_empath_wound(wound_key) + amount)
        empath_strain = max(1, int(amount * 0.25))
        if wound_key == "bleeding":
            self.set_empath_wound("bleeding", self.get_empath_wound("bleeding") + empath_strain + max(1, int(amount * 0.1)))
        else:
            self.set_empath_wound("vitality", self.get_empath_wound("vitality") + empath_strain)
        self.decay_empath_link_stability(amount=20, reason="redirect", emit_message=True)
        self.decay_empath_unity_stability(amount=20, event_key="redirect", emit_message=True)
        if amount > 25:
            self.adjust_empath_shock(5)
        self.award_empathy_experience("redirect", 18 + amount, amount=amount, target=source_target, wound_key=wound_key, unity=True)
        return True, "You channel the injury through yourself, shifting its burden."

    def get_empath_unity_effect(self):
        data = self.get_state("empath_unity")
        if not isinstance(data, Mapping):
            return None
        expires_at = float(data.get("expires_at", 0) or 0)
        if expires_at and time.time() >= expires_at:
            self.clear_state("empath_unity")
            return None
        anchor = self.get_empath_link_target(data.get("anchor_id"))
        if not anchor or not hasattr(anchor, "get_empath_unity_state"):
            self.clear_state("empath_unity")
            return None
        unity = anchor.get_empath_unity_state()
        if not unity or self.id not in unity.get("member_ids", []):
            self.clear_state("empath_unity")
            return None
        return {**dict(data), "anchor": anchor, "members": unity.get("members", [])}

    def smooth_empath_linked_wounds(self):
        links = [entry.get("target") for entry in self.get_empath_links(require_local=True, include_group=False) if entry.get("target")]
        if len(links) < 2:
            return False
        config = EMPATH_SYSTEM_CONFIG["smoothing"]
        changed = False
        for wound_key in tuple(config["wounds"]):
            ordered = sorted(links, key=lambda target: target.get_empath_wound(wound_key))
            low = ordered[0]
            high = ordered[-1]
            low_amount = low.get_empath_wound(wound_key)
            high_amount = high.get_empath_wound(wound_key)
            difference = high_amount - low_amount
            if difference < 4:
                continue
            shift = max(1, min(int(config["max_per_tick"]), difference // 4))
            high.set_empath_wound(wound_key, high_amount - shift)
            low.set_empath_wound(wound_key, low_amount + shift)
            changed = True
        return changed

    def apply_empath_unity_share(self, location, amount, damage_type="impact"):
        return int(amount or 0)

    def apply_incoming_damage(self, location, amount, damage_type="impact"):
        self.ensure_core_defaults()
        final_amount = self.apply_empath_unity_share(location, int(amount or 0), damage_type=damage_type)
        if final_amount <= 0:
            return 0
        self.set_hp((self.db.hp or 0) - final_amount)
        self.apply_damage(location, final_amount, damage_type)
        if self.is_empath() and self.get_empath_link_state(require_local=False, emit_break_messages=False):
            self.decay_empath_link_stability(amount=None, reason="damage", emit_message=True)
        if self.is_empath() and self.get_empath_unity_state():
            self.decay_empath_unity_stability(event_key="damage", emit_message=True)
        return final_amount

    def process_empath_links(self):
        if not self.is_empath():
            return False
        before = self.normalize_empath_link_state()
        self.get_empath_link_state(require_local=True, emit_break_messages=False)
        after = self.normalize_empath_link_state()
        if not before:
            if self.get_empath_unity_state():
                self.clear_empath_unity(sync_members=True, emit_message=False)
            return False
        if self.get_empath_shock() >= int(EMPATH_SHOCK_THRESHOLDS["disconnected"]):
            return self.break_empath_connections(reason="shock", emit_message=False)
        self.get_empath_unity_state()
        return before != after

    def get_empath_manipulate_profile(self, target):
        trait_values = [
            str(getattr(getattr(target, "db", None), key, "") or "").strip().lower()
            for key in ("creature_type", "npc_type", "species", "race")
        ]
        searchable = " ".join([str(getattr(target, "key", "") or "").lower(), str(getattr(getattr(target, "db", None), "desc", "") or "").lower(), *trait_values])
        if any(keyword in searchable for keyword in ("undead", "zombie", "skeleton", "ghost", "wraith")):
            return {"category": "undead", "bonus": -60, "backfire": True}
        if any(keyword in searchable for keyword in ("construct", "golem", "clockwork", "automaton")):
            return {"category": "construct", "bonus": -70, "backfire": True}
        intelligence = int(target.get_stat("intelligence") if hasattr(target, "get_stat") else 10)
        if any(keyword in searchable for keyword in ("wolf", "bear", "boar", "deer", "rat", "snake", "dog", "cat", "animal", "beast")) or intelligence <= 6:
            return {"category": "animal", "bonus": 20, "backfire": False}
        if intelligence <= 8:
            return {"category": "simple", "bonus": 10, "backfire": False}
        return {"category": "resistant", "bonus": 0, "backfire": False}

    def manipulate_empath_target(self, target):
        if not self.is_empath():
            return False, "You cannot impose calm that way."
        allowed, message = self.can_use_empath_ability("manipulate")
        if not allowed:
            return False, message
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        if target == self:
            return False, "You are already wrestling with your own feelings."
        profile = self.get_empath_manipulate_profile(target)
        empathy = int(self.get_skill("empathy") if hasattr(self, "get_skill") else 0)
        self_score = empathy + int(self.get_stat("charisma") if hasattr(self, "get_stat") else 10) + int(profile.get("bonus", 0) or 0) + random.randint(1, 40)
        target_score = int(target.get_stat("discipline") if hasattr(target, "get_stat") else 10) + int(target.get_stat("intelligence") if hasattr(target, "get_stat") else 10) + random.randint(1, 35)
        if profile.get("backfire") and self_score < target_score:
            if hasattr(target, "set_target"):
                target.set_target(self)
            if getattr(target.db, "in_combat", None) is not None:
                target.db.in_combat = True
            self.adjust_empath_shock(4)
            return False, f"Your attempt brushes against {target.key}'s wrongness and turns its attention toward you."
        if self_score < target_score:
            return False, f"{target.key} resists your attempt to calm them."
        duration = 25 if profile.get("category") == "animal" else 18
        target.set_state(
            "empath_manipulated",
            {
                "source_id": self.id,
                "expires_at": time.time() + duration,
                "category": profile.get("category"),
            },
        )
        if hasattr(target, "set_target"):
            target.set_target(None)
        if getattr(target.db, "in_combat", None) is not None:
            target.db.in_combat = False
        self.award_empathy_experience("manipulate", 18 + max(0, int(target_score / 6)), target=target)
        return True, f"You press calm into {target.key}'s thoughts, easing their aggression."

    def get_empath_transfer_profile(self, wound_type):
        return dict(EMPATH_TRANSFER_CONFIG.get(self.normalize_empath_wound_key(wound_type), {}))

    def get_medical_severity_state(self):
        wounds = self.get_empath_wounds() if hasattr(self, "get_empath_wounds") else {}
        vitality = int(wounds.get("vitality", 0) or 0)
        bleeding = int(wounds.get("bleeding", 0) or 0)
        poison = int(wounds.get("poison", 0) or 0)
        disease = int(wounds.get("disease", 0) or 0)
        trauma = int(wounds.get("trauma", 0) or 0)
        aggregate = vitality + bleeding + poison + disease + trauma
        if vitality >= 70 or bleeding >= 45 or poison >= 45 or disease >= 45 or trauma >= 45 or aggregate >= 120:
            return "critical"
        if vitality >= 45 or bleeding >= 25 or poison >= 25 or disease >= 25 or trauma >= 25 or aggregate >= 75:
            return "badly_injured"
        if vitality >= 20 or bleeding >= 10 or poison >= 10 or disease >= 10 or trauma >= 10 or aggregate >= 35:
            return "injured"
        return "stable"

    def is_medically_critical(self):
        return self.get_medical_severity_state() == "critical"

    def is_empath_triage_target(self, target):
        if not target or target == self:
            return False
        if bool(getattr(getattr(target, "db", None), "is_house_healer", False)):
            return False
        if not hasattr(target, "get_empath_wounds"):
            return False
        return True

    def get_empath_triage_social_label(self, target):
        if not target or bool(getattr(getattr(target, "db", None), "is_house_healer", False)):
            return ""
        last_tip_amount = int(getattr(getattr(target, "db", None), "last_tip_amount", 0) or 0)
        last_tip_time = float(getattr(getattr(target, "db", None), "last_tip_time", 0.0) or 0.0)
        if last_tip_amount >= 20 and last_tip_time > 0 and (time.time() - last_tip_time) <= 86400.0:
            return "generous"
        tip_history = self.get_tip_history_for(target) if hasattr(self, "get_tip_history_for") else {}
        if int(tip_history.get("total", 0) or 0) >= 20 and time.time() - float(tip_history.get("last", 0.0) or 0.0) <= 86400.0:
            return "generous"
        context = dict(getattr(self.db, "empath_triage_context", {}) or {})
        if str(int(getattr(target, "id", 0) or 0)) in context:
            return "known"
        return "no history"

    def update_empath_triage_context(self, targets=None, source="scan", scanned_at=None):
        if not self.is_empath():
            return {}
        scanned_at = float(scanned_at or time.time())
        context = dict(getattr(self.db, "empath_triage_context", {}) or {})
        target_list = list(targets or [])
        for index, target in enumerate(target_list):
            if not self.is_empath_triage_target(target):
                continue
            target_id = str(int(getattr(target, "id", 0) or 0))
            context[target_id] = {
                "target": getattr(target, "key", ""),
                "severity": target.get_medical_severity_state() if hasattr(target, "get_medical_severity_state") else "stable",
                "critical": bool(getattr(target, "is_medically_critical", lambda: False)()),
                "last_seen_at": scanned_at,
                "seen_order": index,
                "source": str(source or "scan"),
                "last_tip_amount": int(getattr(getattr(target, "db", None), "last_tip_amount", 0) or 0),
                "last_tip_time": float(getattr(getattr(target, "db", None), "last_tip_time", 0.0) or 0.0),
            }
        self.db.empath_triage_context = context
        self.db.last_triage_scan_at = scanned_at
        return context

    def get_empath_queue_entries(self):
        room = getattr(self, "location", None)
        if not room:
            return []
        context = dict(getattr(self.db, "empath_triage_context", {}) or {})
        entries = []
        for index, target in enumerate(getattr(room, "contents", [])):
            if not self.is_empath_triage_target(target):
                continue
            severity = target.get_medical_severity_state() if hasattr(target, "get_medical_severity_state") else "stable"
            if severity == "stable":
                continue
            cached = dict(context.get(str(int(getattr(target, "id", 0) or 0)), {}) or {})
            entries.append(
                {
                    "target": target,
                    "severity": severity,
                    "severity_rank": {"stable": 0, "injured": 1, "badly_injured": 2, "critical": 3}.get(severity, 0),
                    "social": self.get_empath_triage_social_label(target),
                    "context_labels": self.get_empath_queue_context_labels(target),
                    "tip_weight": 1 if self.get_empath_triage_social_label(target) == "generous" else 0,
                    "seen_order": int(cached.get("seen_order", index) or index),
                }
            )
        entries.sort(key=lambda entry: (-int(entry.get("severity_rank", 0) or 0), -int(entry.get("tip_weight", 0) or 0), int(entry.get("seen_order", 0) or 0), str(getattr(entry.get("target"), "key", ""))))
        return entries

    def get_empath_transfer_risk_state(self):
        wounds = self.get_empath_wounds()
        vitality = int(wounds.get("vitality", 0) or 0)
        fatigue = int(wounds.get("fatigue", 0) or 0)
        carried = sum(int(value or 0) for value in wounds.values())
        shock = int(self.get_empath_shock() if hasattr(self, "get_empath_shock") else 0)
        score = vitality + fatigue + shock + int(round(carried * 0.35))
        tier = "steady"
        efficiency_modifier = 1.0
        backlash_modifier = 1.0
        if score >= 170 or shock >= int(EMPATH_SHOCK_THRESHOLDS["disconnected"]):
            tier = "extreme"
            efficiency_modifier = 0.55
            backlash_modifier = 1.4
        elif score >= 130 or shock >= 60:
            tier = "high"
            efficiency_modifier = 0.7
            backlash_modifier = 1.25
        elif score >= 90 or shock >= 35:
            tier = "elevated"
            efficiency_modifier = 0.85
            backlash_modifier = 1.1
        return {
            "vitality": vitality,
            "fatigue": fatigue,
            "shock": shock,
            "carried_wounds": carried,
            "score": score,
            "tier": tier,
            "efficiency_modifier": efficiency_modifier,
            "backlash_modifier": backlash_modifier,
        }

    def is_empath_overloaded(self):
        risk = self.get_empath_transfer_risk_state()
        return str(risk.get("tier") or "") == "extreme" or self.is_empath_overdrawn()

    def maybe_warn_empath_transfer_risk(self, risk_state=None):
        risk = risk_state or self.get_empath_transfer_risk_state()
        tier = str(risk.get("tier") or "steady")
        if tier == "steady":
            return False
        now = time.time()
        next_warning_at = float(getattr(self.ndb, "next_empath_risk_warning_at", 0.0) or 0.0)
        if now < next_warning_at:
            return False
        self.msg("This may overwhelm you." if tier == "extreme" else "You are carrying too much already.")
        self.ndb.next_empath_risk_warning_at = now + 8.0
        return True

    def trigger_empath_overload(self, reason="transfer", duration=8.0):
        duration = max(4.0, float(duration or 0.0))
        self.db.empath_overload_until = max(float(getattr(self.db, "empath_overload_until", 0.0) or 0.0), time.time() + duration)
        self.msg("You have taken too much. Your senses falter.")
        if getattr(self, "location", None):
            self.location.msg_contents(f"{self.key} staggers under the weight of pain.", exclude=self)
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + 6)
        for member in self.get_empath_circle_members(include_self=False, validate=True):
            spill = 3
            if member.get_empath_shock() >= 60 or member.get_empath_wound("vitality") >= 60:
                spill = 2
            member.set_empath_shock(member.get_empath_shock() + spill)
            member.msg("The strain spreads through your circle.")
        self.maybe_trigger_empath_circle_cascade(trigger_amount=9, source=reason)
        if hasattr(self, "set_roundtime"):
            self.set_roundtime(3.0)
        return True

    def get_empath_trauma_value(self):
        self.ensure_core_defaults()
        injuries = getattr(self.db, "injuries", None) or {}
        if not injuries:
            return 0
        total_trauma = 0
        worst_trauma = 0
        for body_part in injuries.values():
            trauma = int(self.get_part_trauma(body_part) or 0)
            total_trauma += trauma
            worst_trauma = max(worst_trauma, trauma)
        return max(0, min(100, int(round((worst_trauma * 1.2) + (total_trauma * 0.35)))))

    def sync_empath_wounds_from_resources(self):
        self.ensure_core_defaults()
        wounds = self.normalize_empath_wounds(getattr(self.db, "wounds", None) or _copy_default_empath_wounds())
        self.db.wounds = wounds
        return wounds

    def sync_resources_from_empath_wounds(self):
        self.ensure_core_defaults()
        wounds = self.normalize_empath_wounds(getattr(self.db, "wounds", None) or _copy_default_empath_wounds())
        self.db.wounds = wounds
        return wounds

    def get_empath_wounds(self):
        self.ensure_core_defaults()
        return dict(self.sync_empath_wounds_from_resources())

    def get_empath_wound(self, wound_type):
        wound_key = self.normalize_empath_wound_key(wound_type)
        return max(0, min(100, int(self.get_empath_wounds().get(wound_key, 0) or 0)))

    def set_empath_wound(self, wound_type, value):
        self.ensure_core_defaults()
        wound_key = self.normalize_empath_wound_key(wound_type)
        if wound_key not in DEFAULT_EMPATH_WOUNDS:
            return 0
        wounds = self.get_empath_wounds()
        wounds[wound_key] = max(0, min(100, int(value or 0)))
        self.db.wounds = wounds
        self.sync_resources_from_empath_wounds()
        self.sync_client_state()
        return wounds[wound_key]

    def adjust_empath_wound(self, wound_type, amount):
        return self.set_empath_wound(wound_type, self.get_empath_wound(wound_type) + int(amount or 0))

    def get_empath_wound_label(self, value):
        return describe_wound(value)

    def format_empath_diagnosis(self, precise=False):
        wounds = self.sync_empath_wounds_from_resources()
        lines = []
        for key in ["vitality", "bleeding", "poison", "disease"]:
            label = EMPATH_WOUND_LABELS.get(key, key.title())
            value = int(wounds.get(key, 0) or 0)
            lines.append(f"{label}: {value}%" if precise else f"{label}: {self.get_empath_wound_label(value)}")
        return lines

    def get_empath_life_force_score(self, target=None):
        patient = target or self
        wounds = patient.get_empath_wounds() if hasattr(patient, "get_empath_wounds") else {}
        vitality = int(wounds.get("vitality", 0) or 0)
        bleeding = int(wounds.get("bleeding", 0) or 0)
        fatigue = int(wounds.get("fatigue", 0) or 0)
        trauma = int(wounds.get("trauma", 0) or 0)
        poison = int(wounds.get("poison", 0) or 0)
        disease = int(wounds.get("disease", 0) or 0)
        return max(0, min(100, int(round((vitality * 0.38) + (bleeding * 0.24) + (trauma * 0.16) + (fatigue * 0.07) + (poison * 0.09) + (disease * 0.06)))))

    def get_empath_perception_accuracy(self):
        shock = self.get_empath_shock()
        if shock >= int(EMPATH_SHOCK_THRESHOLDS["disconnected"]):
            return "poor"
        if shock >= int(EMPATH_SHOCK_THRESHOLDS["dull"]):
            return "blurred"
        if shock >= int(EMPATH_SHOCK_THRESHOLDS["strained"]):
            return "steady"
        return "keen"

    def get_empath_perceived_life_force_score(self, target=None):
        patient = target or self
        score = self.get_empath_life_force_score(patient)
        shock = self.get_empath_shock()
        if shock < 50:
            return score
        distortion_seed = int(getattr(patient, "id", 0) or 0) % 7
        distortion = (distortion_seed - 3) * (4 if shock >= 80 else 2)
        return max(0, min(100, score + distortion))

    def describe_empath_life_force(self, target=None, targeted=False):
        patient = target or self
        score = self.get_empath_perceived_life_force_score(patient)
        accuracy = self.get_empath_perception_accuracy()
        wounds = patient.get_empath_wounds() if hasattr(patient, "get_empath_wounds") else {}
        if score >= 85:
            base = "Their life force is near collapse." if targeted else "near collapse"
        elif score >= 60:
            base = "Their life force is unstable." if targeted else "weakened"
        elif score >= 35:
            base = "Their life force is strained." if targeted else "strained"
        else:
            base = "Their life force is steady." if targeted else "steady"
        if not targeted or accuracy == "poor":
            return base
        dominant_key = max(["vitality", "bleeding", "fatigue", "trauma", "poison", "disease"], key=lambda key: int(wounds.get(key, 0) or 0))
        if int(wounds.get(dominant_key, 0) or 0) < 15:
            return base
        dominant_line = {
            "vitality": "Vitality is draining away from them.",
            "bleeding": "Bleeding frays the edges of their life force.",
            "fatigue": "Exhaustion drags at the edges of their pattern.",
            "trauma": "Deep trauma knots beneath the surface.",
            "poison": "A poisonous corruption runs through them.",
            "disease": "A wasting sickness clings to their pattern.",
        }.get(dominant_key)
        return f"{base} {dominant_line}"

    def get_empath_perceive_targets(self, include_adjacent=False):
        room = getattr(self, "location", None)
        if not room:
            return []
        seen = []
        for obj in room.contents:
            if not self.is_empath_triage_target(obj):
                continue
            seen.append(obj)
        if include_adjacent:
            for nearby in room.contents_get(content_type="exit"):
                destination = getattr(nearby, "destination", None)
                if not destination:
                    continue
                for obj in getattr(destination, "contents", []):
                    if hasattr(obj, "get_empath_wounds") and obj not in seen and obj != self:
                        seen.append(obj)
        return seen

    def perceive_empath_health(self):
        if not self.is_empath():
            return False, ["You cannot read life forces that way."]
        allowed, message = self.can_use_empath_ability("perceive_health")
        if not allowed:
            return False, [message]
        targets = self.get_empath_perceive_targets(include_adjacent=False)
        if not targets:
            return True, ["You sense no other lifeforms nearby."]
        self.update_empath_triage_context(targets=targets, source="perceive_room")
        lines = []
        shock_state = self.get_empath_shock_state()
        if shock_state in {"strained", "dull"}:
            lines.append("Your senses are unclear.")
        for target in targets:
            wounds = target.get_empath_wounds() if hasattr(target, "get_empath_wounds") else {}
            severity_label = self.get_empath_room_scan_severity(wounds)
            if shock_state == "dull" and severity_label in {"critical", "badly injured"}:
                severity_label = "fading"
            lines.append(f"{target.key}: {severity_label}")
        self.award_field_xp(
            "perceive",
            difficulty=2 + len(targets),
            success=True,
            outcome="success",
            context_multiplier=min(2.0, 1.0 + (len(targets) * 0.1)),
        )
        return True, lines

    def perceive_empath_target(self, target):
        if not self.is_empath():
            return False, ["You cannot read life forces that way."]
        allowed, message = self.can_use_empath_ability("perceive_target")
        if not allowed:
            return False, [message]
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        if not hasattr(target, "get_empath_wounds"):
            return False, ["You find no living pattern to read there."]
        self.update_empath_triage_context(targets=[target], source="perceive_target")
        lines = self.format_empath_perceive_output(target)
        if self.get_empath_shock_state() in {"strained", "dull"}:
            return True, ["Your senses are unclear.", *lines]
        self.award_field_xp("perceive", difficulty=2, success=True, outcome="success")
        return True, lines

    def get_empath_room_scan_severity(self, wounds):
        wounds = dict(wounds or {})
        vitality = int(wounds.get("vitality", 0) or 0)
        bleeding = int(wounds.get("bleeding", 0) or 0)
        poison = int(wounds.get("poison", 0) or 0)
        disease = int(wounds.get("disease", 0) or 0)
        trauma = int(wounds.get("trauma", 0) or 0)
        aggregate = vitality + bleeding + poison + disease + trauma
        if vitality >= 70 or bleeding >= 45 or aggregate >= 120:
            return "critical"
        if vitality >= 45 or bleeding >= 25 or aggregate >= 75:
            return "badly injured"
        if vitality >= 20 or bleeding >= 10 or aggregate >= 35:
            return "injured"
        return "fine"

    def format_empath_perceive_output(self, target):
        wounds = target.get_empath_wounds() if hasattr(target, "get_empath_wounds") else {}
        shock_state = self.get_empath_shock_state()
        severity_state = target.get_medical_severity_state() if hasattr(target, "get_medical_severity_state") else self.get_empath_room_scan_severity(wounds)
        vitality = int(wounds.get("vitality", 0) or 0)
        vitality_state = "stable"
        if vitality > 60:
            vitality_state = "near collapse"
        elif vitality > 30:
            vitality_state = "unstable"
        wound_parts = []
        for key in ("bleeding", "poison", "disease", "fatigue", "trauma"):
            value = int(wounds.get(key, 0) or 0)
            if value > 0:
                wound_parts.append(f"{key} {value}%")
        if shock_state == "dull":
            lines = [
                f"Target: {target.key}",
                f"Condition: {severity_state.replace('_', ' ')}",
                f"Impression: {'; '.join(wound_parts[:2]) if wound_parts else 'their pattern is hard to read'}",
            ]
        else:
            lines = [
                f"Target: {target.key}",
                f"Vitality: {vitality_state}",
                f"Condition: {severity_state.replace('_', ' ')}",
                f"Wounds: {', '.join(wound_parts) if wound_parts else 'none'}",
            ]
        shock = int(target.get_empath_shock() if hasattr(target, "get_empath_shock") else getattr(getattr(target, "db", None), "empath_shock", 0) or 0)
        if shock > 0 and shock_state == "clear":
            lines.append(f"Shock: {shock}")
        return lines

    def has_empath_transfer_connection(self, target):
        if not target:
            return False
        return bool(self.get_empath_link_state(require_local=True, target=target, emit_break_messages=False))

    def take_empath_shock(self, target):
        if not self.is_empath():
            return False, "You cannot take on shock that way."
        allowed, message = self.can_use_empath_ability("take")
        if not allowed:
            return False, message
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        if not hasattr(target, "get_empath_shock"):
            return False, "You find no empathic burden to transfer there."
        if not self.has_empath_transfer_connection(target):
            return False, "You must be properly connected to transfer shock."
        target_shock = int(target.get_empath_shock() or 0)
        if target_shock <= 0:
            return False, f"{target.key} is carrying no shock."
        available_capacity = max(0, 100 - int(self.get_empath_shock() or 0))
        if available_capacity <= 0:
            return False, "You cannot تحمل more shock."
        transfer_amount = min(target_shock, available_capacity)
        target.adjust_empath_shock(-transfer_amount)
        self.adjust_empath_shock(transfer_amount)
        self.award_field_xp("take", success=True, outcome="success", context_multiplier=min(2.0, 0.75 + (transfer_amount / 20.0)))
        self.msg("You take on the strain.")
        target.msg("You feel your mental burden lighten.")
        if transfer_amount < target_shock:
            return True, "You cannot تحمل more shock."
        return True, "You take on the strain."

    def resolve_shift_destination_part(self, location_name):
        normalized = str(location_name or "").strip().lower()
        mapping = {
            "arm": "left_arm",
            "leg": "left_leg",
            "torso": "chest",
        }
        return mapping.get(normalized, "")

    def get_shift_source_part(self, target, destination_part):
        if not target:
            return ""
        injuries = dict(getattr(getattr(target, "db", None), "injuries", None) or {})
        best_part = ""
        best_total = 0
        for part_name in BODY_PART_ORDER:
            if part_name == destination_part:
                continue
            body_part = dict(injuries.get(part_name) or {})
            total = int(body_part.get("external", 0) or 0) + int(body_part.get("internal", 0) or 0) + int(body_part.get("bleed", 0) or 0)
            if total > best_total:
                best_total = total
                best_part = part_name
        return best_part

    def shift_empath_injury(self, target, location_name):
        if not self.is_empath():
            return False, "You do not know how to shift injuries that way."
        allowed, message = self.can_use_empath_ability("shift")
        if not allowed:
            return False, message
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        if not self.has_empath_transfer_connection(target):
            return False, "You must be properly connected to transfer shock."
        destination_part = self.resolve_shift_destination_part(location_name)
        if not destination_part:
            return False, "You can only shift toward an arm, leg, or torso."
        if not hasattr(target, "get_body_part"):
            return False, f"{target.key} has no wounds you can shift."
        source_part = self.get_shift_source_part(target, destination_part)
        if not source_part:
            return False, f"{target.key} has no wounds you can shift."
        injuries = dict(getattr(getattr(target, "db", None), "injuries", None) or {})
        source_body_part = dict(injuries.get(source_part) or {})
        destination_body_part = dict(injuries.get(destination_part) or {})
        moved_external = int(source_body_part.get("external", 0) or 0)
        moved_internal = int(source_body_part.get("internal", 0) or 0)
        moved_bleed = int(source_body_part.get("bleed", 0) or 0)
        moved_total = moved_external + moved_internal + moved_bleed
        if moved_total <= 0:
            return False, f"{target.key} has no wounds you can shift."
        destination_body_part["external"] = int(destination_body_part.get("external", 0) or 0) + moved_external
        destination_body_part["internal"] = int(destination_body_part.get("internal", 0) or 0) + moved_internal
        destination_body_part["bleed"] = int(destination_body_part.get("bleed", 0) or 0) + moved_bleed
        source_body_part["external"] = 0
        source_body_part["internal"] = 0
        source_body_part["bleed"] = 0
        injuries[source_part] = source_body_part
        injuries[destination_part] = destination_body_part
        target.db.injuries = injuries
        if hasattr(target, "update_bleed_state"):
            target.update_bleed_state()
        if random.random() < 0.1:
            self.msg("The shift destabilizes the injury.")
        self.award_field_xp("shift", success=True, outcome="success", context_multiplier=min(2.5, 1.0 + (moved_total / 20.0)))
        if hasattr(target, "sync_client_state"):
            target.sync_client_state()
        self.sync_client_state()
        return True, f"You shift the worst of {target.key}'s injuries toward the {self.format_body_part_name(destination_part)}."

    def get_linked_target(self):
        primary = self.get_empath_link_state(require_local=False, emit_break_messages=False)
        return primary.get("target") if primary else None

    def set_linked_target(self, target):
        ok, link_data = self.create_empath_link(target, link_type=EMPATH_LINK_TOUCH) if target else (True, None)
        if not target:
            self.remove_empath_link(clear_all=True)
            return None
        return link_data.get("target") if ok and isinstance(link_data, Mapping) else None

    def clear_linked_target(self):
        self.remove_empath_link(clear_all=True)

    def touch_empath_target(self, target):
        if not self.is_empath():
            return False, ["You lack the sensitivity to establish an empathic link."]
        allowed, message = self.can_use_empath_ability("touch")
        if not allowed:
            return False, [message]
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        if target == self:
            return False, ["You already feel every ache in your own body."]
        if int(getattr(getattr(target, "db", None), "empath_tutorial_owner", 0) or 0) not in {0, int(getattr(self, "id", 0) or 0)}:
            return False, ["That patient is under another empath's care."]
        existing = self.get_empath_link_state(require_local=True, emit_break_messages=False)
        if self.is_empath_tutorial_active() and existing:
            existing_target = existing.get("target")
            if existing_target == target:
                return False, ["You are already linked to that patient."]
            return False, ["Release your current patient before beginning again."]
        self.create_empath_link(target, link_type=EMPATH_LINK_TOUCH)
        return True, ["You reach out and sense the condition of your patient."]

    def link_empath_target(self, target, persistent=False, deepen=False):
        if not self.is_empath():
            return False, ["You do not know how to deepen a bond that way."]
        allowed, message = self.can_use_empath_ability("link")
        if not allowed:
            return False, [message]
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        if target == self:
            return False, ["You are already bound to your own hurts."]
        if persistent:
            unlocked, unlock_message = self.require_empath_unlock("persistent_link")
            if not unlocked:
                return False, [unlock_message]
        link_type = EMPATH_LINK_PERSISTENT if persistent else EMPATH_LINK_DIRECT
        ok, result = self.create_empath_link(target, link_type=link_type, deepen=deepen)
        if not ok:
            return False, result if isinstance(result, list) else [str(result)]
        if hasattr(self, "set_roundtime"):
            self.set_roundtime(2.5)
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + 5)
        if persistent:
            lines = ["You settle into a deeper, longer-held connection."]
        else:
            lines = ["You deepen your connection, taking in the shape of their suffering."]
        return True, lines

    def set_empath_link_focus(self, skill_name):
        if not self.is_empath():
            return False, "You cannot shape a borrowed focus that way."
        link_state = self.get_empath_link_state(require_local=True, emit_break_messages=True)
        if not link_state:
            return False, "You need an active local link first."
        target = link_state.get("target")
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            return False, "Focus on which skill?"
        target_rank = int(target.get_skill_rank(normalized) if hasattr(target, "get_skill_rank") else 0)
        if target_rank <= 0:
            return False, f"{target.key} has nothing to lend you there."
        bonus = max(1, int(target_rank * 0.2))
        updated = dict(link_state)
        updated["link_bonus_skill"] = normalized
        updated["link_bonus_value"] = bonus
        updated["link_bonus_tick_at"] = time.time() + 10.0
        self.set_empath_link_state(updated, sync=True)
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + 3)
        return True, f"You tune the link toward {self.format_skill_name(normalized)}."

    def clear_empath_link_focus(self, emit_message=False):
        link_state = self.get_empath_link_state(require_local=False, emit_break_messages=False)
        if not link_state or (not link_state.get("link_bonus_skill") and not int(link_state.get("link_bonus_value", 0) or 0)):
            return False
        updated = dict(link_state)
        updated["link_bonus_skill"] = None
        updated["link_bonus_value"] = 0
        updated["link_bonus_tick_at"] = 0.0
        self.set_empath_link_state(updated, sync=True)
        if emit_message:
            self.msg("You let the borrowed focus slip away.")
        return True

    def get_empath_link_focus_bonus(self, skill_name):
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            return 0
        link_state = self.get_empath_link_state(require_local=False, emit_break_messages=False)
        if not link_state:
            return 0
        if str(link_state.get("link_bonus_skill") or "") != normalized:
            return 0
        return max(0, int(link_state.get("link_bonus_value", 0) or 0))

    def deepen_empath_link(self, target):
        return self.link_empath_target(target, persistent=False, deepen=True)

    def assess_empath_link(self, target_query=None):
        if not self.is_empath():
            return False, ["You lack the sensitivity to assess a patient that way."]
        allowed, message = self.can_use_empath_ability("assess")
        if not allowed:
            return False, [message]
        link_state = self.get_empath_link_state(require_local=True, emit_break_messages=True)
        if not link_state:
            return False, ["You are not linked to anyone."]
        target = link_state.get("target")
        if target_query and not self.resolve_empath_link_target(target_query, require_local=True):
            return False, ["You must touch them before you can assess them."]
        wounds = target.get_empath_wounds() if hasattr(target, "get_empath_wounds") else {}
        if self.is_empath_tutorial_active():
            def _tutorial_label(value):
                amount = int(value or 0)
                if amount <= 0:
                    return "None"
                if amount <= 10:
                    return "Faint"
                if amount <= 25:
                    return "Noticeable"
                return self.get_empath_wound_label(amount).title()

            lines = [
                f"Vitality: {_tutorial_label(wounds.get('vitality', 0))}",
                f"Bleeding: {_tutorial_label(wounds.get('bleeding', 0))}",
                f"Poison: {_tutorial_label(wounds.get('poison', 0))}",
                f"Disease: {_tutorial_label(wounds.get('disease', 0))}",
            ]
        else:
            lines = [
                f"Vitality: {int(wounds.get('vitality', 0) or 0)}%",
                f"Bleeding: {int(wounds.get('bleeding', 0) or 0)}%",
                f"Poison: {int(wounds.get('poison', 0) or 0)}%",
                f"Disease: {int(wounds.get('disease', 0) or 0)}%",
            ]
        if link_state.get("type") in {EMPATH_LINK_DIRECT, EMPATH_LINK_PERSISTENT}:
            condition = str(link_state.get("condition") or "steady")
            if condition == "fragile":
                lines.append("Your connection feels fragile.")
            elif condition == "strained":
                lines.append("Your connection feels strained.")
            else:
                lines.append("Your connection feels steady.")
        return True, lines

    def assess_empath_corpse(self, corpse):
        if not self.is_empath():
            return False, ["You lack the sensitivity to assess a patient that way."]
        allowed, message = self.can_use_empath_ability("assess")
        if not allowed:
            return False, [message]
        if not corpse or getattr(corpse, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        if not getattr(getattr(corpse, "db", None), "is_corpse", False) or not hasattr(corpse, "get_empath_wounds"):
            return False, ["You find no pattern there you can assess."]
        wounds = corpse.get_empath_wounds()
        lines = [
            f"Vitality: {int(wounds.get('vitality', 0) or 0)}%",
            f"Bleeding: {int(wounds.get('bleeding', 0) or 0)}%",
            f"Poison: {int(wounds.get('poison', 0) or 0)}%",
            f"Disease: {int(wounds.get('disease', 0) or 0)}%",
            f"Internal Load: {self.get_corpse_internal_total(corpse)}",
            f"Bleed Load: {self.get_corpse_bleed_total(corpse)}",
            f"Survivability Band: {self.get_corpse_revive_survivability_band(corpse).upper()}",
        ]
        if hasattr(corpse, "get_decay_stage_penalties"):
            penalties = corpse.get_decay_stage_penalties()
            lines.append(f"Decay Stage: {int(penalties.get('stage', 0) or 0)} ({str(penalties.get('label', 'Fresh') or 'Fresh')})")
        if not self.is_corpse_revive_survivable(corpse):
            lines.append(self.get_corpse_survivability_warning(corpse))
            lines.append("They will not survive long without intervention.")
        if hasattr(corpse, "get_empath_prep_remaining") and corpse.get_empath_prep_remaining(self) <= 0:
            lines.append("You have pushed this body as far as your own hands can. Another empath may still help.")
        return True, lines

    def siphon_empath_bleeding(self, target, wound_amount):
        if not target or not hasattr(target, "get_bleeding_parts"):
            return 0
        remaining = max(0, int(math.ceil((int(wound_amount or 0)) / 5.0)))
        if remaining <= 0:
            return 0
        removed = 0
        for entry in target.get_bleeding_parts():
            if remaining <= 0:
                break
            body_part = target.get_body_part(entry.get("part")) if hasattr(target, "get_body_part") else None
            if not body_part:
                continue
            current_bleed = max(0, int(body_part.get("bleed", 0) or 0))
            if current_bleed <= 0:
                continue
            spent = min(current_bleed, remaining)
            body_part["bleed"] = current_bleed - spent
            remaining -= spent
            removed += spent
        if removed > 0 and hasattr(target, "update_bleed_state"):
            target.update_bleed_state()
        return removed

    def take_empath_wound(self, wound_type, amount_spec="", target=None, selector=None, requested_fraction=None, requested_rate=None, learning_action=None):
        if not self.is_empath():
            return False, "You cannot draw another's wounds into yourself."
        allowed, message = self.can_use_empath_ability("take")
        if not allowed:
            return False, message
        link_state = self.get_empath_link_state(require_local=True, emit_break_messages=True)
        if not link_state:
            return False, "You are not linked to a patient."
        target = link_state.get("target")
        selector_key = self.normalize_empath_take_selector(selector)
        if selector and not selector_key:
            return False, "You can't focus on that."
        rate_key = str(requested_rate or "").strip().lower()
        if rate_key and rate_key not in {"slow", "fast"}:
            return False, "You cannot shape the transfer that way."
        explicit_wound_key = self.normalize_empath_wound_key(wound_type)
        if selector_key:
            wound_key = self.resolve_empath_take_bucket(target, selector_key)
        elif requested_fraction is not None or rate_key:
            if explicit_wound_key in DEFAULT_EMPATH_WOUNDS:
                wound_key = explicit_wound_key
            else:
                wound_key = self.resolve_default_empath_take_bucket(target)
        else:
            wound_key = explicit_wound_key
        if wound_key not in DEFAULT_EMPATH_WOUNDS:
            if selector_key:
                return False, f"{target.key} has no wound there you can draw."
            if requested_fraction is not None or rate_key:
                return False, f"{target.key} has no wound you can draw that way."
            return False, "You cannot take that."
        if wound_key == "vitality" and requested_fraction is not None:
            return False, "You cannot carefully draw life force. It must be taken whole."
        if self.is_empath_tutorial_active() and wound_key not in EMPATH_TUTORIAL_WOUNDS:
            return False, "You are not ready to take poison or disease yet."
        if wound_key == "poison":
            unlocked, unlock_message = self.require_empath_unlock("poison_transfer")
            if not unlocked:
                return False, unlock_message
        if wound_key == "disease":
            unlocked, unlock_message = self.require_empath_unlock("disease_transfer")
            if not unlocked:
                return False, unlock_message
        target_wounds = target.get_empath_wounds() if hasattr(target, "get_empath_wounds") else {}
        target_value = target_wounds.get(wound_key)
        if not target_value or int(target_value) <= 0:
            return False, f"{target.key} is not suffering from that wound."
        target_amount = int(target_value)
        raw_spec = str(amount_spec or "").strip().lower()
        if (requested_fraction is not None or rate_key) and raw_spec not in {"", "all"}:
            return False, "Partial transfer does not use a direct amount."
        if selector_key and raw_spec and requested_fraction is None and not rate_key:
            return False, "Selective take draws the whole injury for now."
        if requested_fraction is not None:
            amount = max(1, int(target_amount * float(requested_fraction)))
        elif selector_key:
            amount = target_amount
        elif raw_spec == "all":
            amount = target_amount
        elif raw_spec:
            try:
                amount = max(1, int(raw_spec))
            except ValueError:
                return False, "Give a number or 'all'."
        else:
            amount = min(20, target_amount)
        amount = min(amount, target_amount)
        risk_before = self.get_empath_transfer_risk_state()
        self.maybe_warn_empath_transfer_risk(risk_before)
        transfer_pressure = self.get_empath_transfer_pressure(target)
        self.note_empath_handler_activity(target, action="take", duration=12.0)
        if self.is_empath_tutorial_active():
            target.set_empath_wound(wound_key, target_amount - amount)
            self.set_empath_wound(wound_key, self.get_empath_wound(wound_key) + amount)
            self.award_field_xp("take", success=True, outcome="success", context_multiplier=min(2.0, 1.0 + (amount / 20.0)))
            self.complete_empath_tutorial_if_ready(target=target)
            if requested_fraction is not None:
                if selector_key:
                    return True, f"You carefully draw only part of the hurt from their {selector_key}."
                return True, "You carefully draw only part of the injury into yourself."
            if rate_key == "slow":
                return True, "You carefully draw the injury into yourself."
            if rate_key == "fast":
                return True, "You force the injury across the link into yourself."
            if selector_key:
                return True, f"You focus on the hurt in their {selector_key} and draw it into yourself."
            return True, "You draw the wound into yourself."
        shock = self.get_empath_shock()
        penalty = 1 + (shock / 75.0)
        link_strength = max(1, int(link_state.get("strength", 0) or 0))
        effective_amount = max(0, int((amount * link_strength / 100.0) / penalty))
        effective_amount = max(0, int(round(effective_amount * float(risk_before.get("efficiency_modifier", 1.0) or 1.0))))
        effective_amount = max(0, int(round(effective_amount * float(transfer_pressure.get("efficiency_modifier", 1.0) or 1.0))))
        if requested_fraction is not None and amount > 0 and target_amount > 0:
            effective_amount = max(1, min(target_amount, effective_amount))
        if effective_amount <= 0:
            if shock > 50:
                return False, "Your connection feels dulled."
            return False, "You fail to draw the injury across the link."
        profile = self.get_empath_transfer_profile(wound_key)
        mitigation_factor = self.get_empath_mitigation()
        unity = None if wound_key == "vitality" else self.get_empath_unity_state()
        unity_target = None
        unity_smoothed = 0
        if unity and int(unity.get("primary_target_id", 0) or 0) == int(getattr(target, "id", 0) or 0):
            unity_target = unity.get("secondary_target")
            unity_smoothed = max(0, min(effective_amount - 1, int(effective_amount * EMPATH_UNITY_SMOOTH_RATIO)))
        if getattr(getattr(target, "db", None), "is_corpse", False) and hasattr(target, "reduce_corpse_wound"):
            actual_removed = target.reduce_corpse_wound(wound_key, effective_amount, selector=selector_key, handler=self)
            if actual_removed <= 0:
                if str(getattr(target.db, "last_empath_prep_result", "") or "") == "cap":
                    return False, "You have pushed the body as far as your own hands can for now. Another empath may still help."
                return False, f"{target.key} has no wound there you can draw."
            effective_amount = actual_removed
            amount = actual_removed
        else:
            target.set_empath_wound(wound_key, target_amount - effective_amount)
        if unity_target and unity_smoothed > 0:
            unity_target.set_empath_wound(wound_key, unity_target.get_empath_wound(wound_key) + unity_smoothed)
        empath_take_raw = max(1, effective_amount - unity_smoothed)
        empath_take = max(1, int(round(empath_take_raw * mitigation_factor * float(risk_before.get("backlash_modifier", 1.0) or 1.0) * float(transfer_pressure.get("instability_multiplier", 1.0) or 1.0))))
        overload_message = ""
        if wound_key == "poison":
            self.set_empath_wound("poison", self.get_empath_wound("poison") + empath_take)
            self.set_empath_wound("vitality", self.get_empath_wound("vitality") + int(empath_take * 0.3))
        elif wound_key == "vitality":
            fatigue_ratio = float(profile.get("fatigue_ratio", 0.35) or 0.35)
            shock_ratio = float(profile.get("shock_ratio", 0.3) or 0.3)
            hp_ratio = float(profile.get("hp_ratio", 0.5) or 0.5)
            fatigue_gain = max(1, int(effective_amount * fatigue_ratio))
            shock_gain = max(1, int(effective_amount * shock_ratio))
            hp_cost = max(1, int(effective_amount * hp_ratio))

            self.set_empath_wound("vitality", self.get_empath_wound("vitality") + empath_take)
            self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + fatigue_gain)
            self.distribute_circle_shock(shock_gain, source="vitality_take")
            self.set_hp(int(getattr(self.db, "hp", 0) or 0) - hp_cost)
            self.maybe_trigger_empath_overdraw()
            overload_message = self.apply_empath_transfer_overload(effective_amount, wound_key)
        elif wound_key == "disease":
            self.set_empath_wound("disease", self.get_empath_wound("disease") + empath_take)
        else:
            self.set_empath_wound(wound_key, self.get_empath_wound(wound_key) + empath_take)
        if wound_key == "bleeding" and not selector_key and requested_fraction is None and not rate_key:
            self.set_empath_wound("bleeding", self.get_empath_wound("bleeding") + int(amount * 0.2))
        rate_multiplier = 1.0
        if rate_key == "slow":
            rate_multiplier = 0.75
        elif rate_key == "fast":
            rate_multiplier = 1.25
        if rate_key:
            small_cost = max(1, int(round(self.get_empath_link_stability_cost(link_state.get("type"), "small_transfer") * rate_multiplier)))
            self.decay_empath_link_stability(amount=small_cost, reason="small_transfer", emit_message=True)
        else:
            self.decay_empath_link_stability(amount=None, reason="small_transfer", emit_message=True)
        if int(transfer_pressure.get("other_handler_count", 0) or 0) > 0 and not bool(getattr(getattr(target, "db", None), "is_corpse", False)):
            self.decay_empath_link_stability(amount=max(1, int(2 * float(transfer_pressure.get("instability_multiplier", 1.0) or 1.0))), reason="small_transfer", emit_message=False)
            self.msg("Too many hands on the same pain make the transfer less stable.")
        if wound_key != "vitality" and amount > 25:
            if rate_key:
                large_cost = max(1, int(round(self.get_empath_link_stability_cost(link_state.get("type"), "large_transfer") * rate_multiplier)))
                self.decay_empath_link_stability(amount=large_cost, reason="large_transfer", emit_message=True)
                self.adjust_empath_shock(max(1, int(round(5 * rate_multiplier))))
            else:
                self.decay_empath_link_stability(amount=None, reason="large_transfer", emit_message=True)
                self.adjust_empath_shock(5)
        if unity:
            self.decay_empath_unity_stability(event_key="transfer", emit_message=True)
        if self.get_empath_circle_members(include_self=False, validate=True):
            self.msg("You share in the burden.")
        self.ndb.empath_recent_healing_until = time.time() + 20.0
        self.award_field_xp(
            "take",
            success=True,
            outcome="success",
            context_multiplier=min(2.0, 0.75 + (amount / 25.0) + (0.15 if unity else 0.0)),
        )
        if target.is_medically_critical() if hasattr(target, "is_medically_critical") else False:
            self.adjust_empath_reputation(1, reason="critical_help")
        risk_after = self.get_empath_transfer_risk_state()
        if str(risk_after.get("tier") or "") == "extreme":
            overload_message = overload_message or "The weight of the transfer leaves you reeling."
            self.trigger_empath_overload(reason="transfer", duration=8.0)
        if overload_message:
            self.msg(overload_message)
        if shock >= int(EMPATH_SHOCK_THRESHOLDS["dull"]):
            self.msg("Your connection feels dulled.")
        if requested_fraction is not None:
            if selector_key:
                return True, f"You carefully draw only part of the hurt from their {selector_key}."
            return True, "You carefully draw only part of the injury into yourself."
        if rate_key == "slow":
            if selector_key:
                return True, f"You carefully draw the hurt from their {selector_key}."
            if empath_take < empath_take_raw:
                return True, "You carefully draw the injury into yourself, lessening the burden as you take it."
            return True, "You carefully draw the injury into yourself."
        if rate_key == "fast":
            if selector_key:
                return True, f"You force the hurt from their {selector_key} into yourself."
            if empath_take < empath_take_raw:
                return True, "You force the injury across the link, but lessen the burden as you take it."
            return True, "You force the injury across the link into yourself."
        if selector_key:
            if empath_take < empath_take_raw:
                return True, f"You focus on the hurt in their {selector_key} and lessen the burden as you take it."
            return True, f"You focus on the hurt in their {selector_key} and draw it into yourself."
        if wound_key == "vitality":
            if empath_take < empath_take_raw:
                return True, "You draw out living force, lessening the burden even as it tears through you."
            return True, "You draw out living force, and it tears through you on the way in."
        if empath_take < empath_take_raw:
            return True, "You lessen the burden as you take it."
        return True, "You draw the injury into yourself."

    def apply_empath_transfer_overload(self, requested, wound_key):
        profile = self.get_empath_transfer_profile(wound_key)
        if int(requested or 0) < 30:
            return ""
        overload_chance = min(0.7, ((int(requested or 0) - 20) / 50.0) + float(profile.get("risk", 0.0) or 0.0))
        if random.random() >= overload_chance:
            return ""
        fatigue_spike = max(2, int(round(int(requested or 0) * float(profile.get("risk", 0.0) or 0.0))))
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + fatigue_spike)
        self.set_state("empath_transfer_overload", {"expires_at": time.time() + 5.0, "requested": int(requested or 0), "wound": str(wound_key or "")})
        self.trigger_empath_overload(reason="transfer", duration=max(6.0, float(int(requested or 0)) / 6.0))
        if hasattr(self, "set_roundtime"):
            self.set_roundtime(max(1.5, min(4.0, float(int(requested or 0)) / 12.0)))
        return "The force of the transfer buckles you for a moment."

    def process_medical_decay(self, now=None):
        self.ensure_core_defaults()
        now = float(now or time.time())
        if bool(getattr(self.db, "is_dead", False)):
            return False
        wounds = self.get_empath_wounds()
        severity = self.get_medical_severity_state()
        if severity == "stable" and int(wounds.get("bleeding", 0) or 0) <= 0:
            self.db.last_medical_decay_at = now
            return False
        last_decay_at = float(getattr(self.db, "last_medical_decay_at", 0.0) or 0.0)
        if now - last_decay_at < 12.0:
            return False
        before_severity = severity
        bleeding = int(wounds.get("bleeding", 0) or 0)
        changed = False
        bleed_multiplier = self.get_resurrection_bleed_multiplier()
        if bleeding > 0:
            bleed_vitality_loss = 1
            if bleeding >= 35:
                bleed_vitality_loss = 3
            elif bleeding >= 15:
                bleed_vitality_loss = 2
            bleed_vitality_loss = int(round(bleed_vitality_loss * bleed_multiplier))
            if bleed_vitality_loss > 0:
                self.set_empath_wound("vitality", self.get_empath_wound("vitality") + bleed_vitality_loss)
                changed = True
        recently_stabilized = self.is_stabilized() if hasattr(self, "is_stabilized") else False
        if severity in {"badly_injured", "critical"} and not recently_stabilized and not self.should_pause_resurrection_internal_decay():
            worsening_key = max(("vitality", "bleeding", "poison", "disease"), key=lambda key: int(wounds.get(key, 0) or 0))
            worsen_amount = 2 if severity == "critical" else 1
            self.set_empath_wound(worsening_key, self.get_empath_wound(worsening_key) + worsen_amount)
            changed = True
        self.db.last_medical_decay_at = now
        after_severity = self.get_medical_severity_state()
        warning_due = now >= float(getattr(self.db, "last_critical_warning_at", 0.0) or 0.0) + 20.0
        if warning_due and after_severity == "critical":
            self.msg("You are slipping away." if before_severity != "critical" else "Your condition is worsening.")
            room = getattr(self, "location", None)
            if room:
                for obj in getattr(room, "contents", []):
                    if obj == self or not getattr(obj, "is_empath", lambda: False)():
                        continue
                    obj.msg(f"Your senses snag on {self.key}. They are fading.")
                    if hasattr(obj, "get_empath_active_handlers"):
                        active_handlers = obj.get_empath_active_handlers(self)
                        if not active_handlers:
                            obj.adjust_empath_reputation(-1, reason="ignored_critical")
            self.db.last_critical_warning_at = now
        self.process_resurrection_stabilization_tick()
        return changed

    def mend_empath_self(self):
        if not self.is_empath():
            return False, "You do not know how to mend yourself that way."
        wounds = self.get_empath_wounds()
        before_vitality = int(wounds.get("vitality", 0) or 0)
        before_bleeding = int(wounds.get("bleeding", 0) or 0)
        penalty = get_disease_penalty(self)
        heal_vitality = max(0, int(10 / penalty))
        heal_bleeding = max(0, int(5 / penalty))
        after_vitality = self.set_empath_wound("vitality", before_vitality - heal_vitality)
        after_bleeding = self.set_empath_wound("bleeding", before_bleeding - heal_bleeding)
        if before_vitality == after_vitality and before_bleeding == after_bleeding:
            return False, "You are already carrying no wounds that require mending."
        self.award_empathy_experience("mend", 15, amount=before_vitality + before_bleeding, target=self)
        if self.is_empath_tutorial_active():
            after_wounds = self.get_empath_wounds()
            if int(after_wounds.get("vitality", 0) or 0) <= 0 and int(after_wounds.get("bleeding", 0) or 0) <= 0:
                self.set_empath_training_stage(EMPATH_TRAINING_BASIC)
                return True, "You focus inward, stabilizing your condition. Merla gives a short nod. 'Good. Now you have actually finished the lesson.'"
        return True, "You focus inward, stabilizing your condition."

    def center_empath_self(self):
        if not self.is_empath():
            return False, "You do not know how to center yourself that way."
        overload = self.get_state("empath_transfer_overload")
        if isinstance(overload, Mapping) and time.time() < float(overload.get("expires_at", 0.0) or 0.0):
            return False, "You are still reeling from the last transfer."
        if self.get_state("empath_channel"):
            return False, "You cannot center yourself while actively channeling another's pain."
        config = EMPATH_SYSTEM_CONFIG["center"]
        shock_reduction = int(config["shock_reduction"])
        fatigue_cost = int(config["fatigue_cost"])
        roundtime = float(config["roundtime"])
        zone = self.get_empath_room_zone()
        if zone == "recovery":
            shock_reduction += 8
            fatigue_cost = max(4, fatigue_cost - 3)
        elif zone == "triage":
            shock_reduction += 3
        if getattr(self.db, "in_combat", False):
            shock_reduction = max(5, int(round(shock_reduction * 0.5)))
            fatigue_cost += 5
            roundtime += 1.0
        before_shock = self.get_empath_shock()
        before_fatigue = self.get_empath_wound("fatigue")
        self.adjust_empath_shock(-shock_reduction)
        self.set_empath_wound("fatigue", before_fatigue + fatigue_cost)
        if self.is_empath_overdrawn() and self.get_empath_shock() <= int(config["overdraw_clear_shock_threshold"]) and self.get_empath_wound("fatigue") <= int(config["overdraw_clear_fatigue_threshold"]):
            self.clear_state("empath_overdraw")
        if hasattr(self, "set_roundtime"):
            self.set_roundtime(roundtime)
        self.use_skill("attunement", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=14)
        if before_shock == self.get_empath_shock() and before_fatigue == self.get_empath_wound("fatigue"):
            return False, "You are already as centered as you can be."
        return True, "You steady yourself, regaining clarity."

    def get_empath_stabilize_strength(self):
        skill = int(self.get_skill("first_aid") if hasattr(self, "get_skill") else 0)
        config = EMPATH_STABILIZE_RULES
        strength = float(config["base_strength"]) + (skill * float(config["strength_scale"]))
        return max(0.0, min(float(config["max_strength"]), strength))

    def purge_empath_condition(self, wound_type):
        if not self.is_empath():
            return False, "You cannot purge corruption that way."
        wound_key = self.normalize_empath_wound_key(wound_type)
        if wound_key not in {"poison", "disease"}:
            return False, "You can only purge poison or disease."
        before = self.get_empath_wound(wound_key)
        if before <= 0:
            return False, f"You are not carrying any {wound_key}."
        reduction = 15 if wound_key == "poison" else 10
        self.set_empath_wound(wound_key, before - reduction)
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + 10)
        self.award_empathy_experience("purge", 18, amount=before, target=self, wound_key=wound_key)
        return True, "You force the corruption from your body."

    def register_empath_offensive_action(self, target=None, context="attack", amount=None):
        if not self.is_empath():
            return 0
        if target == self or target is None:
            return 0
        if not hasattr(target, "get_empath_wounds"):
            return 0
        if amount is not None:
            shock_gain = int(amount)
        elif context == "kill":
            shock_gain = 30
        elif context == "attack":
            shock_gain = 15
        else:
            shock_gain = 8
        return self.adjust_empath_shock(shock_gain)

    def process_wound_conditions(self):
        self.ensure_core_defaults()
        wounds = self.get_empath_wounds()
        poison = int(wounds.get("poison", 0) or 0)
        now = time.time()
        if poison > 0 and now >= float(getattr(self.ndb, "next_poison_tick_at", 0) or 0):
            apply_poison_tick(self)
            self.ndb.next_poison_tick_at = now + 6.0
        return False

    def get_stabilizable_parts(self):
        self.ensure_core_defaults()
        parts = []
        for part_name in BODY_PART_ORDER:
            body_part = self.get_body_part(part_name)
            if not body_part:
                continue
            bleed = max(0, int(body_part.get("bleed", 0) or 0))
            trauma = max(0, int(self.get_part_trauma(body_part) or 0))
            if bleed <= 0 and trauma <= 0:
                continue
            parts.append(
                {
                    "part": part_name,
                    "bleed": bleed,
                    "trauma": trauma,
                }
            )
        parts.sort(key=lambda entry: (entry["bleed"], entry["trauma"]), reverse=True)
        return parts

    def is_stabilized(self):
        return time.time() < float(getattr(self.db, "stabilized_until", 0.0) or 0.0)

    def refresh_stabilize_tend(self, part, tender=None):
        body_part = self.get_body_part(part)
        if not body_part:
            return False

        current_bleed = max(0, int(body_part.get("bleed", 0) or 0))
        if current_bleed <= 0:
            return False

        healer = tender or self
        skill = healer.get_skill("first_aid") if hasattr(healer, "get_skill") else 0
        base_duration = 12 + (skill // 2)
        base_strength = max(1, min(max(1, current_bleed // 2), max(1, current_bleed - 1)))
        tend_state = dict(body_part.get("tend") or {})
        existing_duration = max(0, int(tend_state.get("duration", 0) or 0))
        existing_strength = max(0, int(tend_state.get("strength", 0) or 0))
        existing_min_until = float(tend_state.get("min_until", 0.0) or 0.0)
        now = time.time()
        body_part["tend"] = {
            "strength": max(existing_strength, base_strength),
            "duration": max(existing_duration, base_duration),
            "last_applied": now,
            "min_until": max(existing_min_until, now + 120.0),
        }
        body_part["tended"] = True
        self.start_first_aid_training_window(part, tender=healer)
        return True

    def stabilize_empath_target(self, target):
        if not self.is_empath():
            return False, "You do not know how to stabilize wounds that way."
        allowed, message = self.can_use_empath_ability("stabilize")
        if not allowed:
            return False, message
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        stabilizable_parts = target.get_stabilizable_parts() if hasattr(target, "get_stabilizable_parts") else []
        if not stabilizable_parts:
            return False, f"{target.key} has no wounds you can stabilize."
        now = time.time()
        duration = float(EMPATH_STABILIZE_RULES["base_duration"]) + (int(self.get_skill("first_aid") if hasattr(self, "get_skill") else 0) * float(EMPATH_STABILIZE_RULES["duration_scale"]))
        if self.get_empath_room_zone() == "triage":
            duration += 4.0
        strength = self.get_empath_stabilize_strength()
        target.db.stabilized_until = max(float(getattr(target.db, "stabilized_until", 0.0) or 0.0), now) + duration
        target.db.stability_strength = max(float(getattr(target.db, "stability_strength", 0.0) or 0.0), strength)
        treated = 0
        part_limit = 3 if self.get_empath_room_zone() == "triage" else 2
        for entry in stabilizable_parts[:part_limit]:
            part_name = entry.get("part")
            if hasattr(target, "refresh_stabilize_tend") and target.refresh_stabilize_tend(part_name, tender=self):
                treated += 1
        target.sync_empath_wounds_from_resources()
        self.note_empath_handler_activity(target, action="stabilize", duration=16.0)
        if target.is_medically_critical() if hasattr(target, "is_medically_critical") else False:
            self.adjust_empath_reputation(1, reason="critical_stabilize")
        return True, "You steady their condition, slowing the damage."

    def start_empath_channel(self, wound_type):
        if not self.is_empath():
            return False, "You do not know how to channel another's pain."
        allowed, message = self.can_use_empath_ability("channel")
        if not allowed:
            return False, message
        link_state = self.get_empath_link_state(require_local=True, emit_break_messages=True)
        if not link_state:
            return False, "You need an active local link first."
        if self.get_state("empath_channel"):
            return False, "You are already sustaining a transfer."
        target = link_state.get("target")
        wound_key = self.normalize_empath_wound_key(wound_type)
        if wound_key not in DEFAULT_EMPATH_WOUNDS:
            return False, "You cannot channel that wound."
        if target.get_empath_wound(wound_key) <= 0:
            return False, f"{target.key} is not suffering from that wound."
        self.set_state(
            "empath_channel",
            {
                "wound": wound_key,
                "pulse_count": 0,
                "next_pulse_at": time.time() + float(EMPATH_CHANNEL_RULES["pulse_interval"]),
                "started_at": time.time(),
            },
        )
        return True, "You settle into a sustained channel."

    def stop_empath_channel(self, reason="manual", emit_message=True):
        state = self.get_state("empath_channel")
        if not isinstance(state, Mapping):
            return False
        self.clear_state("empath_channel")
        if emit_message:
            if reason == "broken":
                self.msg("The sustained channel slips away.")
            elif reason == "overdraw":
                self.msg("You lose the channel as your senses fail under the strain.")
            else:
                self.msg("You let the sustained channel go.")
        return True

    def process_empath_channel_tick(self, now=None):
        state = self.get_state("empath_channel")
        if not isinstance(state, Mapping):
            return False
        now = float(now or time.time())
        if now < float(state.get("next_pulse_at", 0.0) or 0.0):
            return False
        if self.is_empath_overdrawn():
            self.stop_empath_channel(reason="overdraw", emit_message=True)
            return False
        link_state = self.get_empath_link_state(require_local=True, emit_break_messages=True)
        if not link_state:
            self.stop_empath_channel(reason="broken", emit_message=True)
            return False
        wound_key = self.normalize_empath_wound_key(state.get("wound"))
        target = link_state.get("target")
        target_amount = int(target.get_empath_wound(wound_key) if hasattr(target, "get_empath_wound") else 0)
        if target_amount <= 0:
            self.stop_empath_channel(reason="manual", emit_message=True)
            return False
        profile = self.get_empath_transfer_profile(wound_key)
        pulse_amount = max(int(EMPATH_CHANNEL_RULES["min_amount"]), int(int(profile.get("default", 10) or 10) * float(EMPATH_CHANNEL_RULES["base_ratio"])))
        pulse_amount = min(target_amount, pulse_amount)
        ok, _message = self.take_empath_wound(wound_key, str(pulse_amount), learning_action="channel")
        if not ok:
            self.stop_empath_channel(reason="broken", emit_message=True)
            return False
        pulse_count = int(state.get("pulse_count", 0) or 0) + 1
        fatigue_gain = int(EMPATH_CHANNEL_RULES["fatigue_base"]) + (pulse_count * int(EMPATH_CHANNEL_RULES["fatigue_escalation"]))
        if self.get_empath_room_zone() == "training":
            fatigue_gain = max(1, int(round(fatigue_gain * 0.5)))
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + fatigue_gain)
        if pulse_count % int(EMPATH_CHANNEL_RULES["shock_every"]) == 0:
            self.adjust_empath_shock(1)
        self.set_state(
            "empath_channel",
            {
                "wound": wound_key,
                "pulse_count": pulse_count,
                "next_pulse_at": now + float(EMPATH_CHANNEL_RULES["pulse_interval"]),
                "started_at": float(state.get("started_at", now) or now),
            },
        )
        if self.is_empath_overdrawn():
            self.stop_empath_channel(reason="overdraw", emit_message=True)
        return True

    def stabilize_corpse(self, corpse):
        if not self.is_empath():
            return False, "You do not know how to stabilize deathly remains that way."
        if not corpse or getattr(corpse, "location", None) != getattr(self, "location", None):
            return False, "That corpse is not here."
        if not getattr(getattr(corpse, "db", None), "is_corpse", False):
            return False, "You can only stabilize a corpse."
        owner = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        if owner and hasattr(owner, "notify_recovery_consent_use"):
            owner.notify_recovery_consent_use(self)
        first_aid = self.get_skill("first_aid")
        condition_gain = max(6, min(20, 8 + int(first_aid / 5)))
        before = float(corpse.get_condition() if hasattr(corpse, "get_condition") else getattr(corpse.db, "condition", 100.0) or 0.0)
        corpse.db.stabilized = True
        after = corpse.adjust_condition(condition_gain) if hasattr(corpse, "adjust_condition") else before
        self.award_skill_experience("first_aid", 16, success=True, outcome="success", event_key="first_aid_corpse", context_multiplier=1.0)
        if after <= before and before >= 100:
            return False, "The corpse is already in the best condition you can preserve."
        return True, "You carefully tend to the corpse, slowing its decay."

    def process_empath_tick(self):
        if not self.is_empath() or not getattr(self, "location", None):
            return False
        now = time.time()
        changed = False
        if self.validate_empath_circle_state(sync_members=True, emit_message=False):
            changed = True
        before_links = {entry.get("target_id"): entry for entry in self.get_empath_links(require_local=False, include_group=False)}
        self.process_empath_links()
        after_links = {entry.get("target_id"): entry for entry in self.get_empath_links(require_local=False, include_group=False)}
        broken = [entry for target_id, entry in before_links.items() if target_id not in after_links]
        if broken:
            self.msg("Your connection slips away.")
            changed = True
        shock_tick_at = float(getattr(self.ndb, "next_empath_shock_decay_at", 0) or 0)
        if now >= shock_tick_at and self.get_empath_shock() > 0:
            recent_healing_until = float(getattr(self.ndb, "empath_recent_healing_until", 0) or 0)
            decay = 4 if now < recent_healing_until else 2
            if self.get_empath_room_zone() == "recovery":
                decay += 2
            self.adjust_empath_shock(-decay)
            self.ndb.next_empath_shock_decay_at = now + 10.0
            changed = True
        strain_tick_at = float(getattr(self.ndb, "next_empath_strain_decay_at", 0) or 0)
        if now >= strain_tick_at and self.get_empath_strain() > 0:
            strain_decay = 3 if self.get_empath_room_zone() == "recovery" else 2
            if self.get_state("empath_channel"):
                strain_decay = 1
            self.decay_empath_strain(strain_decay)
            self.ndb.next_empath_strain_decay_at = now + 20.0
            changed = True
        link_state = self.get_empath_link_state(require_local=False, emit_break_messages=False)
        if link_state and link_state.get("link_bonus_skill") and now >= float(link_state.get("link_bonus_tick_at", 0.0) or 0.0):
            upkeep = max(1, 1 + int(int(link_state.get("link_bonus_value", 0) or 0) / 5))
            if self.get_empath_room_zone() == "training":
                upkeep = max(1, int(round(upkeep * 0.5)))
            self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + upkeep)
            updated_link = dict(link_state)
            updated_link["link_bonus_tick_at"] = now + 10.0
            self.set_empath_link_state(updated_link, sync=True)
            changed = True
        self.process_empath_channel_tick(now=now)
        smoothing_tick_at = float(getattr(self.ndb, "next_empath_smoothing_at", 0) or 0)
        if now >= smoothing_tick_at:
            self.smooth_empath_linked_wounds()
            self.ndb.next_empath_smoothing_at = now + float(EMPATH_SYSTEM_CONFIG["smoothing"]["tick_seconds"])
            changed = True
        for target in self.get_empath_perceive_targets(include_adjacent=False):
            if hasattr(target, "process_medical_decay") and target.process_medical_decay(now=now):
                changed = True
        feedback_tick_at = float(getattr(self.ndb, "next_empath_feedback_at", 0) or 0)
        if now >= feedback_tick_at:
            primary = self.get_primary_empath_link(require_local=True, include_group=False)
            patient = primary.get("target") if primary else None
            carried_wounds = sum(int(value or 0) for value in self.get_empath_wounds().values())
            has_feedback_context = bool(patient) or self.is_empath_overdrawn() or carried_wounds >= 120 or self.get_empath_shock() > 15
            if has_feedback_context:
                if self.is_empath_overdrawn() or carried_wounds >= 120:
                    self.msg("You are carrying too much pain.")
                elif self.get_empath_strain() >= 70:
                    self.msg("The living patterns around you rasp against your nerves.")
                elif self.get_empath_strain() >= 40:
                    self.msg("You feel a low empathic strain under your thoughts.")
                elif patient and self.get_empath_shock() <= 15:
                    self.msg("Your senses are clear.")
                elif patient:
                    score = self.get_empath_life_force_score(patient)
                    if score >= 80:
                        self.msg(f"{patient.key}'s pain presses hard against the link.")
                    elif score >= 55:
                        self.msg(f"You feel the strain in {patient.key}'s pattern.")
            self.ndb.next_empath_feedback_at = now + 18.0
            changed = True
        next_ping = float(getattr(self.ndb, "empath_sensitivity_next_at", 0) or 0)
        if now < next_ping:
            return changed
        threshold = 85 if self.get_empath_perception_accuracy() == "poor" else 70
        for target in self.get_empath_perceive_targets(include_adjacent=False):
            if self.get_empath_life_force_score(target) >= threshold:
                self.msg("You feel a nearby life force faltering.")
                self.ndb.empath_sensitivity_next_at = now + 20
                return True
        return changed

    def normalize_stance(self):
        stance = dict(self.db.stance or {"offense": 50, "defense": 50})
        offense = int(stance.get("offense", 50))
        defense = int(stance.get("defense", 50))
        total = offense + defense
        if total == 0:
            offense = 50
            defense = 50
        else:
            offense = int((offense / total) * 100)
            defense = 100 - offense
        normalized = {"offense": offense, "defense": defense}
        if dict(self.db.stance or {}) != normalized:
            self.db.stance = normalized

    def set_stance(self, offense=None, defense=None):
        self.ensure_core_defaults()
        stance = dict(self.db.stance or {"offense": 50, "defense": 50})
        if offense is not None:
            stance["offense"] = max(0, min(100, int(offense)))
        if defense is not None:
            stance["defense"] = max(0, min(100, int(defense)))
        self.db.stance = stance
        self.normalize_stance()
        self.sync_client_state()

    def get_position_modifiers(self):
        self.ensure_core_defaults()
        pos = self.db.position or "standing"
        if pos == "prone":
            return {"offense": -30, "defense": -20}
        if pos == "kneeling":
            return {"offense": -10, "defense": 5}
        return {"offense": 0, "defense": 0}

    def resolve_targeted_body_part(self):
        self.ensure_core_defaults()
        target_part = self.db.target_body_part
        if not target_part:
            return None, None

        if target_part == "head":
            return "head", "head"
        if target_part == "chest":
            return "chest", "chest"
        if target_part == "arm":
            return random.choice(["left_arm", "right_arm"]), "arm"
        if target_part == "leg":
            return random.choice(["left_leg", "right_leg"]), "leg"
        return None, None

    def is_stunned(self):
        self.ensure_core_defaults()
        return bool(self.db.stunned)

    def consume_stun(self):
        self.ensure_core_defaults()
        if self.db.stunned:
            self.db.stunned = False
            return True
        return False

    def renew_state(self):
        self.ensure_core_defaults()
        self.db.hp = self.db.max_hp
        self.db.balance = self.db.max_balance
        self.db.fatigue = 0
        self.db.attunement = self.db.max_attunement
        self.db.war_tempo = 0
        self.db.war_tempo_state = "calm"
        self.db.exhaustion = 0
        self.db.active_warrior_berserk = None
        self.db.active_warrior_roars = {}
        self.db.warrior_roar_effects = {}
        self.db.pressure_level = 0
        self.db.combat_streak = 0
        self.db.last_combat_action_at = 0
        self.db.rhythm_break_until = 0
        self.db.bleed_state = "none"
        self.db.roundtime_end = 0
        self.db.life_state = LIFE_STATE_ALIVE
        self.db.is_dead = False
        self.db.death_sting = 0
        self.db.death_sting_active = False
        self.db.death_sting_end = 0.0
        self.db.death_sting_severity = 0.0
        self.db.death_sting_hp_cap_ratio = 1.0
        self.db.death_sting_recovery_label = "none"
        self.db.death_penalty_applied = False
        self.db.stunned = False
        self.db.target_body_part = None
        self.db.position = "standing"
        self.db.stance = {"offense": 50, "defense": 50}
        self.db.combat_range = {}
        self.db.range_break_ticks = {}
        self.db.aiming = None
        self.db.states = {}
        self.db.injuries = _copy_default_injuries()
        _clear_combat_link(self)

    def is_alive(self):
        self.refresh_death_sting(emit_message=False)
        return str(getattr(self.db, "life_state", LIFE_STATE_ALIVE) or LIFE_STATE_ALIVE).upper() == LIFE_STATE_ALIVE and (self.db.hp or 0) > 0

    def is_dead(self):
        return str(getattr(self.db, "life_state", LIFE_STATE_ALIVE) or LIFE_STATE_ALIVE).upper() == LIFE_STATE_DEAD or bool(self.db.is_dead) or (self.db.hp or 0) <= 0

    def can_execute_while_dead(self, raw_string):
        command_name = str(raw_string or "").strip().split(None, 1)[0].lower()
        if not command_name:
            return True
        return command_name in DEAD_STATE_ALLOWED_COMMANDS

    def is_in_onboarding(self):
        try:
            from systems import onboarding

            return onboarding.is_in_onboarding(self)
        except Exception:
            return False

    def execute_cmd(self, raw_string, session=None, **kwargs):
        from world.systems.metrics import increment_counter, measure
        from world.systems import justice

        command_name = str(raw_string or "").strip().split(None, 1)[0].lower()
        with measure(
            "command.execute",
            metadata={
                "character": str(getattr(self, "key", "") or ""),
                "command": command_name,
            },
        ):
            increment_counter("command.execute")
            if self.is_dead():
                self.msg("[You are dead. Type DEPART to return.]")
            if self.is_dead() and not self.can_execute_while_dead(raw_string):
                self.msg("You are dead. You can still look, speak, check your state, depart, or wait for resurrection.")
                return None
            try:
                from systems import aftermath
                from systems.chargen import mirror as chargen_mirror

                aftermath.refresh_new_player_state(self)
                if bool(getattr(self.db, "skip_chargen", False)):
                    remapped_command, immediate_message = raw_string, None
                else:
                    remapped_command, immediate_message = chargen_mirror.gate_chargen_input(self, raw_string)
                if immediate_message:
                    self.msg(immediate_message)
                    return None
                if remapped_command is not None:
                    raw_string = remapped_command
                from systems import onboarding

                if onboarding.is_onboarding_character(self):
                    remapped_command, immediate_message = onboarding.remap_onboarding_input(self, raw_string)
                    if immediate_message:
                        self.msg(immediate_message)
                        return None
                    if remapped_command == getattr(onboarding, "IGNORE_INPUT_COMMAND", None):
                        return None
                    if remapped_command:
                        raw_string = remapped_command
            except Exception:
                LOGGER.exception("Failed to process onboarding input remap for %s", getattr(self, "key", self))
            command_name = str(raw_string or "").strip().split(None, 1)[0].lower()
            block_message = justice.get_justice_command_block_message(self, command_name)
            if block_message:
                self.msg(block_message)
                return None
            if bool(getattr(self.db, "guard_attention", False)) and not justice.is_detained(self):
                justice.note_flee_attempt(self, command_name)
            if self.is_dead() and command_name in {"say", "whisper"}:
                self.msg("Your voice echoes faintly, barely heard.")
            return super().execute_cmd(raw_string, session=session, **kwargs)

    def is_empath(self):
        self.ensure_core_defaults()
        return self.get_profession() == "empath" or bool(getattr(self.db, "is_empath", False))

    def get_empath_load(self):
        self.ensure_core_defaults()
        total = 0
        for part in (self.db.injuries or {}).values():
            total += part.get("external", 0) + part.get("internal", 0)
        return total

    def is_overloaded(self):
        return self.get_empath_load() > 100

    def recover_balance(self):
        self.ensure_all_defaults()
        if self.db.balance < self.db.max_balance:
            recovery = 2
            if self.has_warrior_passive("balance_recovery_1"):
                recovery += 1
            disrupt_effect = self.get_warrior_roar_effect("disrupt") if hasattr(self, "get_warrior_roar_effect") else None
            if isinstance(disrupt_effect, Mapping):
                recovery = max(0, recovery - int(disrupt_effect.get("balance_recovery_penalty", 0) or 0))
            if hasattr(self, "get_exhaustion_balance_penalty"):
                recovery = max(0, recovery - self.get_exhaustion_balance_penalty())
            self.set_balance(self.db.balance + recovery)

    def recover_fatigue(self):
        self.ensure_all_defaults()
        if self.db.fatigue > 0:
            recovery = 2
            if self.has_warrior_passive("fatigue_resist_1"):
                recovery += 1
            if hasattr(self, "get_empath_recovery_modifier"):
                recovery = int(round(recovery * self.get_empath_recovery_modifier()))
            recovery = max(0, recovery)
            self.set_fatigue(self.db.fatigue - recovery)

    def regen_attunement(self):
        self.ensure_all_defaults()
        current = int(self.db.attunement or 0)
        maximum = int(self.db.max_attunement or 0)
        if current >= maximum:
            return False

        regen = 1 + int(self.get_skill("attunement") / 10)
        self.db.attunement = min(maximum, current + max(1, regen))
        return True

    def spend_attunement(self, amount):
        self.ensure_all_defaults()
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            return False

        if amount <= 0:
            return False

        current = int(self.db.attunement or 0)
        if current < amount:
            return False

        self.db.attunement = current - amount
        return True

    def get_stat(self, name):
        self.ensure_all_defaults()
        stat_name = str(name or "").strip().lower()
        default_value = DEFAULT_STATS.get(stat_name, 0)
        current_value = int(self.db.stats.get(stat_name, default_value) or default_value)
        cap = self.get_race_stat_cap(stat_name)
        if cap is not None and current_value > int(cap):
            self.set_stat(stat_name, cap)
            return int(cap)
        return current_value

    def set_stat(self, name, value, emit_cap_message=False):
        self.ensure_all_defaults()
        stat_name = str(name or "").strip().lower()
        if stat_name not in DEFAULT_STATS:
            raise ValueError(f"Unknown stat: {name}")

        stats = dict(self.db.stats or {})
        requested_value = int(value or 0)
        cap = self.get_race_stat_cap(stat_name)
        final_value = min(requested_value, int(cap)) if cap is not None else requested_value
        stats[stat_name] = final_value
        self.db.stats = stats

        if emit_cap_message and cap is not None and requested_value > int(cap):
            self.msg("You cannot improve that attribute further.")

        return final_value

    def get_race(self):
        self.ensure_identity_defaults()
        return resolve_race_name(getattr(self.db, "race", None), default=DEFAULT_RACE)

    def get_race_key(self):
        return self.get_race()

    def get_race_profile(self):
        return get_race_profile(self.get_race())

    def get_race_data(self):
        return self.get_race_profile()

    def get_race_display_name(self):
        return get_race_display_name(self.get_race())

    def get_race_description(self):
        return get_race_description(self.get_race())

    def get_age_bracket(self):
        return resolve_age_bracket(getattr(self.db, "age", DEFAULT_AGE), default="adult")

    def get_race_descriptor(self):
        return get_race_age_descriptor(getattr(self.db, "race", None), getattr(self.db, "age", DEFAULT_AGE))

    def get_known_languages(self):
        self.ensure_identity_defaults()
        languages = []
        for language_name, proficiency in dict(self.db.languages or {"common": 1.0}).items():
            try:
                if float(proficiency) > 0.0:
                    languages.append(language_name)
            except (TypeError, ValueError):
                continue
        return tuple(languages or ["common"])

    def get_language_proficiencies(self):
        self.ensure_identity_defaults()
        return dict(self.db.languages or {"common": 1.0})

    def get_language_proficiency(self, language_name):
        self.ensure_identity_defaults()
        language_key = normalize_language_name(language_name, default=None)
        if not language_key:
            return 0.0
        try:
            return max(0.0, min(1.0, float((self.db.languages or {}).get(language_key, 0.0))))
        except (TypeError, ValueError):
            return 0.0

    def knows_language(self, language_name):
        language_key = normalize_language_name(language_name, default=None)
        if not language_key:
            return False
        return self.get_language_proficiency(language_key) > 0.0

    def learn_language(self, language_name, amount):
        self.ensure_identity_defaults()
        language_key = normalize_language_name(language_name, default=None)
        if not language_key:
            return 0.0

        current = self.get_language_proficiency(language_key)
        try:
            delta = float(amount)
        except (TypeError, ValueError):
            delta = 0.0
        new_value = max(0.0, min(1.0, current + delta))
        languages = dict(self.db.languages or {"common": 1.0})
        languages[language_key] = new_value
        self.db.languages = languages
        return new_value

    def set_language(self, language_name):
        language_key = normalize_language_name(language_name, default=None)
        if not language_key or not self.knows_language(language_key):
            return False
        self.db.active_language = language_key
        return True

    def get_active_language(self):
        self.ensure_identity_defaults()
        active_language = normalize_language_name(getattr(self.db, "active_language", None), default="common")
        if not self.knows_language(active_language):
            active_language = "common"
            self.db.active_language = active_language
        return active_language

    def get_active_language_display_name(self):
        return get_language_display_name(self.get_active_language())

    def render_spoken_text(self, text, language=None):
        active_language = normalize_language_name(language, default=None) or self.get_active_language()
        return apply_accent(text, active_language)

    def get_language_comprehension(self, language_name):
        self.ensure_identity_defaults()
        return get_comprehension_level(self, language_name)

    def perceive_spoken_text(self, text, language_name, speaker=None):
        speaker_key = getattr(speaker, "id", None) or getattr(speaker, "key", "speaker")
        seed = f"{speaker_key}:{getattr(self, 'id', None) or getattr(self, 'key', 'listener')}:{normalize_language_name(language_name, default='common')}"
        return apply_comprehension(text, self.get_language_comprehension(language_name), seed=seed)

    def can_change_race(self):
        self.ensure_identity_defaults()
        return not bool(getattr(self.db, "race_respec_used", False))

    def mark_race_changed(self):
        self.db.race_respec_used = True

    def get_race_reference(self, capitalized=False):
        race_key = resolve_race_name(getattr(self.db, "race", None), default=None)
        if not race_key:
            phrase = self.get_race_descriptor()
        else:
            race_name = get_race_display_name(race_key).strip() or "Human"
            lower_name = race_name.lower()
            article = "an" if lower_name[:1] in "aeiou" else "a"
            phrase = f"{article} {lower_name}"
        if capitalized:
            return phrase[:1].upper() + phrase[1:]
        return phrase

    def get_self_race_line(self):
        race_name = self.get_race_display_name().strip() or "Human"
        article = "an" if race_name[:1].lower() in "aeiou" else "a"
        return f"You are {article} {race_name}."

    def get_other_race_line(self):
        return f"{self.get_race_reference(capitalized=True)} stands here."

    def get_race_size(self):
        profile = self.get_race_profile()
        return str(profile.get("size", "medium") or "medium").strip().lower()

    def get_race_stat_modifier(self, stat):
        return get_race_stat_modifier(self.get_race(), stat)

    def get_race_stat_cap(self, stat):
        return get_race_stat_cap(self.get_race(), stat)

    def get_race_learning_category(self, skill_name=None, category=None):
        if category is not None:
            normalized = normalize_learning_category(category)
            if not normalized:
                raise ValueError(f"Undefined race learning category: {category}")
            return normalized
        metadata = self.get_skill_metadata(skill_name) if skill_name else {}
        raw_category = metadata.get("category")
        normalized = normalize_learning_category(raw_category)
        if not normalized:
            raise ValueError(f"Skill {skill_name} does not define a valid race learning category.")
        return normalized

    def get_race_learning_modifier(self, skill_name=None, category=None):
        normalized_category = self.get_race_learning_category(skill_name=skill_name, category=category)
        return get_race_learning_modifier(self.get_race(), normalized_category)

    def get_race_carry_modifier(self):
        return get_race_carry_modifier(self.get_race())

    def get_race_debug_payload(self):
        payload = get_race_debug_payload(self.get_race())
        payload["max_carry_weight"] = self.get_max_carry_weight()
        return payload

    def get_race_profile_lines(self):
        payload = self.get_race_debug_payload()
        lines = [
            f"Race: {payload['name']}",
            self.get_race_description(),
            f"Size: {str(payload['size']).title()}",
            f"Carry Modifier: x{float(payload['carry_modifier']):.2f}",
            f"Carry Capacity: {float(payload['max_carry_weight']):.1f}",
            "Stat Biases:",
        ]

        for stat_name in RACE_STATS:
            modifier = int(payload.get("stat_modifiers", {}).get(stat_name, 0) or 0)
            cap = int(payload.get("stat_caps", {}).get(stat_name, 100) or 100)
            lines.append(f"  {stat_name.title()}: {modifier:+d} bias, cap {cap}")

        lines.append("Learning Biases:")
        for category, value in payload.get("learning_modifiers", {}).items():
            lines.append(f"  {category.title()}: x{float(value):.2f}")

        return [line for line in lines if line]

    def validate_race_application(self):
        return validate_race_application(self)

    def clamp_stats_to_race(self, emit_messages=False):
        self.ensure_stat_defaults()
        stats = dict(self.db.stats or {})
        changed = False
        for stat_name in RACE_STATS:
            current_value = int(stats.get(stat_name, DEFAULT_STATS.get(stat_name, 10)) or DEFAULT_STATS.get(stat_name, 10))
            cap = int(self.get_race_stat_cap(stat_name) or current_value)
            if current_value > cap:
                stats[stat_name] = cap
                changed = True
        if changed:
            self.db.stats = stats
            if emit_messages:
                self.msg("You cannot improve that attribute further.")
        return changed

    def set_race(self, race_name, sync=True, emit_messages=False):
        state = apply_race(self, race_name, sync=sync, emit_messages=emit_messages)
        return state["race"]

    def get_encumbrance_race_message(self):
        ratio = self.get_encumbrance_ratio()
        size = self.get_race_size()
        if size == "small" and ratio >= 0.8:
            return "The load feels especially burdensome for your size."
        if size == "large" and ratio < 0.3:
            return "You handle the weight with ease."
        return None

    def get_condition(self, hp=None, max_hp=None):
        if hp is None or max_hp is None:
            self.ensure_resource_defaults()
            hp = self.db.hp
            max_hp = self.db.max_hp
        ratio = hp / max_hp if max_hp else 0

        if hp <= 0:
            return "dead"
        elif ratio < 0.1:
            return "near death"
        elif ratio < 0.25:
            return "badly wounded"
        elif ratio < 0.5:
            return "wounded"
        elif ratio < 0.75:
            return "bruised"
        return "in good shape"

    def get_condition_text(self):
        self.ensure_resource_defaults()
        hp = self.db.hp or 0
        max_hp = self.db.max_hp or 1
        ratio = hp / max_hp if max_hp else 0
        self.ensure_body_state()

        worst_trauma = 0
        has_bleeding = False
        for part in (self.db.injuries or {}).values():
            trauma = self.get_part_trauma(part)
            worst_trauma = max(worst_trauma, trauma)
            if part.get("bleed", 0) > 0:
                has_bleeding = True

        if ratio == 1:
            if has_bleeding:
                return "bleeding"
            if worst_trauma >= 40:
                return "badly wounded"
            if worst_trauma >= 15:
                return "wounded"
            if worst_trauma > 0:
                return "bruised"
            return "in perfect health"
        if ratio > 0.75:
            if has_bleeding or worst_trauma >= 25:
                return "wounded"
            return "in good shape"
        if ratio > 0.5:
            return "slightly wounded"
        if ratio > 0.25:
            return "badly wounded"
        if ratio > 0:
            return "on the brink of collapse"
        return "dead"

    def get_possessive_name(self, looker=None):
        if looker == self:
            return "your"
        if self.key and self.key.endswith("s"):
            return f"{self.key}'"
        return f"{self.key}'s"

    def get_injury_display_lines(self, looker=None):
        self.ensure_core_defaults()
        lines = []

        for part_name in BODY_PART_ORDER:
            body_part = self.get_body_part(part_name)
            if not body_part:
                continue

            trauma = self.get_part_trauma(body_part)
            bleed = body_part.get("bleed", 0)
            tended = bool(body_part.get("tended", False))
            if trauma <= 0 and bleed <= 0:
                continue

            part_display = self.format_body_part_name(part_name)
            wound_text = self.describe_body_part_wounds(body_part)
            tended_text = " (tended)" if tended else ""

            if looker == self:
                if bleed > 0:
                    lines.append(f"You are bleeding from your {part_display}{tended_text}.")
                else:
                    lines.append(f"Your {part_display} is {wound_text}{tended_text}.")
                continue

            owner_name = self.get_possessive_name(looker=looker)
            if bleed > 0:
                lines.append(f"{owner_name.capitalize()} {part_display} is bleeding{tended_text}.")
            else:
                lines.append(f"{owner_name.capitalize()} {part_display} is {wound_text}{tended_text}.")

        return lines

    def get_flavor_text(self):
        return None

    def get_equipment_flavor(self):
        for piece in self.get_armor_items():
            effects = self.get_armor_effects(piece)
            if effects.get("flavor"):
                return "Your armor settles comfortably into place."
        return None

    def get_perception(self):
        self.ensure_core_defaults()
        return (self.db.stats or {}).get("intelligence", 10)

    def get_stealth(self):
        self.ensure_core_defaults()
        return self.get_skill("stealth")

    def get_room_observers(self):
        if not self.location:
            return []

        return [
            obj for obj in self.location.contents
            if obj != self and hasattr(obj, "get_perception")
        ]

    def get_detecting_observers(self):
        observers = self.get_room_observers()
        return [obs for obs in observers if obs.can_perceive(self)]

    def get_hidden_strength(self):
        hidden = self.get_state("hidden") or {}
        if not isinstance(hidden, Mapping):
            return 0
        return int(hidden.get("strength", 0))

    def get_stealth_total(self):
        self.ensure_core_defaults()
        stealth_rank = self.get_skill("stealth")
        agility = self.db.stats.get("agility", 10)
        reflex = self.db.stats.get("reflex", 10)
        _, stealth_hindrance = self.get_total_hindrance()
        total = stealth_rank + agility + reflex - stealth_hindrance
        if getattr(self.db, "in_passage", False):
            total += 20
        total += int(getattr(self.db, "slip_bonus", 0) or 0)
        if self.is_profession("ranger"):
            total += self.get_ranger_stealth_bonus()
        return total

    def _get_stealth_learning_store(self):
        self.ensure_core_defaults()
        store = dict(getattr(self.db, "stealth_learning", None) or {})
        pending = [dict(entry or {}) for entry in list(store.get("pending") or []) if isinstance(entry, Mapping)]
        attempts = dict(store.get("attempts") or {})
        now = time.time()
        current_combat_state = bool(self.is_in_combat())
        if bool(store.get("combat_state", current_combat_state)) != current_combat_state:
            attempts = {}

        pruned_attempts = {}
        for bucket, payload in attempts.items():
            if not isinstance(payload, Mapping):
                continue
            last_at = float(payload.get("last_at", 0.0) or 0.0)
            if now - last_at > STEALTH_FATIGUE_WINDOW:
                continue
            pruned_attempts[str(bucket)] = {
                "count": max(0, int(payload.get("count", 0) or 0)),
                "last_at": last_at,
            }

        store["pending"] = pending
        store["attempts"] = pruned_attempts
        store["last_contest"] = dict(store.get("last_contest") or {})
        store["combat_state"] = current_combat_state
        self.db.stealth_learning = store
        return store

    def _save_stealth_learning_store(self, store):
        self.db.stealth_learning = dict(store or {})

    def _build_stealth_award_schedule_key(self, nonce):
        object_id = int(getattr(self, "id", 0) or 0)
        if object_id > 0:
            return f"exp:stealth-award:{object_id}-{nonce}"
        dbref = str(getattr(self, "dbref", "") or "").strip().lstrip("#")
        if dbref.isdigit():
            return f"exp:stealth-award:{dbref}-{nonce}"
        stable_name = str(getattr(self, "key", "character") or "character").strip().lower().replace(" ", "-")
        return f"exp:stealth-award:{stable_name}-{nonce}"

    def _get_stealth_target_bucket(self, target=None):
        if target is not None and getattr(target, "id", None):
            return f"target:{int(target.id)}"
        if self.location is not None and getattr(self.location, "id", None):
            return f"room:{int(self.location.id)}"
        return "global"

    def _pop_pending_stealth_learning(self, nonce):
        store = self._get_stealth_learning_store()
        pending = []
        match = None
        for entry in list(store.get("pending") or []):
            if str((entry or {}).get("nonce", "") or "") == str(nonce or "") and match is None:
                match = dict(entry or {})
                continue
            pending.append(dict(entry or {}))
        store["pending"] = pending
        self._save_stealth_learning_store(store)
        return match

    def _get_stealth_position_modifier(self, pending):
        modifier = 1.0
        position_state = str((pending or {}).get("position_state", "neutral") or "neutral").strip().lower()
        if position_state == "advantaged":
            modifier *= 1.2
        elif position_state == "exposed":
            modifier *= 0.8

        if str((pending or {}).get("range_band", "") or "").strip().lower() == "melee":
            modifier *= 0.7
        return modifier

    def _get_stealth_failure_margin_modifier(self, margin):
        if margin is None:
            return 1.0

        margin_value = float(margin)
        if margin_value < STEALTH_FAILURE_TERRIBLE_MARGIN:
            return STEALTH_FAILURE_TERRIBLE_MODIFIER
        if margin_value < STEALTH_FAILURE_NEAR_MISS_MARGIN:
            return STEALTH_FAILURE_MODERATE_MODIFIER
        return STEALTH_FAILURE_NEAR_MISS_MODIFIER

    def _get_stealth_practice_context(self, skill_name):
        normalized_skill = str(skill_name or "stealth").strip().lower() or "stealth"
        practice_cap = int(STEALTH_PRACTICE_CAPS.get(normalized_skill, 0) or 0)
        skill = getattr(getattr(self, "exp_skills", None), "get", lambda *_: None)(normalized_skill)
        skill_rank = int(getattr(skill, "rank", 0) or 0)
        if practice_cap <= 0 or skill_rank >= practice_cap:
            return False, 0.0, skill_rank, practice_cap

        progress = float(skill_rank) / float(practice_cap)
        practice_scale = max(STEALTH_PRACTICE_MIN_MULTIPLIER, 1.0 - progress)
        return True, STEALTH_PRACTICE_BASE_MULTIPLIER * practice_scale, skill_rank, practice_cap

    def _emit_stealth_learning_debug(self, pending, *, xp_mod=1.0, context_multiplier=1.0, gained=0.0, practice_mode=False):
        if not self.check_permstring("Developer"):
            return

        print(
            "[STEALTH] "
            f"action={pending.get('action', 'stealth')} "
            f"outcome={pending.get('outcome', 'success')} "
            f"margin={pending.get('margin')} "
            f"observer_count={int(pending.get('observer_count', 0) or 0)} "
            f"observer_pressure={float(pending.get('observer_pressure', 0.0) or 0.0):.3f} "
            f"support_pressure={float(pending.get('support_pressure', 0.0) or 0.0):.3f} "
            f"crowd_penalty={float(pending.get('crowd_penalty', 0.0) or 0.0):.3f} "
            f"practice_mode={bool(practice_mode)} "
            f"xp_mod={float(xp_mod):.3f} "
            f"context={float(context_multiplier):.3f} "
            f"gained={float(gained):.3f}"
        )

    def record_stealth_contest(self, action, difficulty, result=None, target=None, roundtime=0.0, event_key="stealth", require_hidden=True):
        from world.systems.scheduler import schedule
        from world.systems.time_model import SCHEDULED_EXPIRY

        store = self._get_stealth_learning_store()
        now = time.time()
        bucket = self._get_stealth_target_bucket(target=target)
        attempts = dict(store.get("attempts") or {})
        payload = dict(attempts.get(bucket) or {})
        attempt_count = max(0, int(payload.get("count", 0) or 0)) + 1
        attempts[bucket] = {"count": attempt_count, "last_at": now}
        store["attempts"] = attempts

        contest_result = dict(result or {}) if isinstance(result, Mapping) else {}
        difficulty_value = max(1, int(difficulty or 1))
        nonce = f"{int(now * 1000)}-{random.randint(100, 999)}"
        range_band = None
        if target is not None and hasattr(self, "get_range"):
            try:
                range_band = self.get_range(target)
            except Exception:
                range_band = None

        pending_entry = {
            "nonce": nonce,
            "action": str(action or "stealth").strip().lower() or "stealth",
            "difficulty": difficulty_value,
            "event_key": str(event_key or "stealth").strip().lower() or "stealth",
            "contest_occurred": bool(contest_result),
            "outcome": str(contest_result.get("outcome", "success") or "success").strip().lower(),
            "margin": contest_result.get("diff"),
            "observer_count": int(contest_result.get("observer_count", 0) or 0),
            "observer_pressure": float(contest_result.get("observer_pressure", 0.0) or 0.0),
            "support_pressure": float(contest_result.get("support_pressure", 0.0) or 0.0),
            "crowd_penalty": float(contest_result.get("crowd_penalty", 0.0) or 0.0),
            "target_bucket": bucket,
            "attempt_count": attempt_count,
            "position_state": str(getattr(self.db, "position_state", "neutral") or "neutral"),
            "range_band": range_band,
            "require_hidden": bool(require_hidden),
            "created_at": now,
        }
        pending = list(store.get("pending") or [])
        pending.append(pending_entry)
        store["pending"] = pending
        store["last_contest"] = {
            "action": pending_entry["action"],
            "target_bucket": bucket,
            "margin": pending_entry["margin"],
            "outcome": pending_entry["outcome"],
            "difficulty": difficulty_value,
            "contest_occurred": pending_entry["contest_occurred"],
            "observer_count": pending_entry["observer_count"],
            "observer_pressure": pending_entry["observer_pressure"],
            "support_pressure": pending_entry["support_pressure"],
            "crowd_penalty": pending_entry["crowd_penalty"],
            "recorded_at": now,
        }
        self._save_stealth_learning_store(store)

        delay_seconds = max(0.0, float(roundtime or 0.0))
        schedule(
            delay_seconds,
            self.finalize_stealth_learning,
            key=self._build_stealth_award_schedule_key(nonce),
            system="exp.stealth",
            timing_mode=SCHEDULED_EXPIRY,
            nonce=nonce,
        )
        return pending_entry

    def finalize_stealth_learning(self, nonce=None):
        pending = self._pop_pending_stealth_learning(nonce)
        if not pending:
            return 0.0

        if bool(pending.get("require_hidden", True)) and not self.is_hidden():
            return 0.0

        context_multiplier = 1.0
        xp_mod = 1.0
        practice_mode = False
        if not bool(pending.get("contest_occurred", False)):
            practice_mode, practice_multiplier, _, _ = self._get_stealth_practice_context("stealth")
            if not practice_mode:
                self._emit_stealth_learning_debug(
                    pending,
                    xp_mod=0.0,
                    context_multiplier=0.0,
                    gained=0.0,
                    practice_mode=False,
                )
                return 0.0
            context_multiplier *= practice_multiplier

        outcome = str(pending.get("outcome", "success") or "success").strip().lower()
        margin = pending.get("margin")
        if margin is not None:
            if outcome == "fail":
                xp_mod = self._get_stealth_failure_margin_modifier(margin)
            else:
                xp_mod = max(STEALTH_MARGIN_MIN, min(STEALTH_MARGIN_MAX, float(margin) / STEALTH_MARGIN_DIVISOR))
            context_multiplier *= xp_mod

        attempt_count = max(1, int(pending.get("attempt_count", 1) or 1))
        context_multiplier *= 1.0 / (1.0 + max(0, attempt_count - 1) * STEALTH_FATIGUE_STEP)
        context_multiplier *= self._get_stealth_position_modifier(pending)

        gained = award_exp_skill(
            self,
            "stealth",
            max(1, int(pending.get("difficulty", 1) or 1)),
            success=outcome != "fail",
            outcome=outcome,
            event_key=pending.get("event_key", "stealth"),
            context_multiplier=context_multiplier,
        )
        self._emit_stealth_learning_debug(
            pending,
            xp_mod=xp_mod,
            context_multiplier=context_multiplier,
            gained=gained,
            practice_mode=practice_mode,
        )
        return gained

    def get_awareness(self):
        return self.get_state("awareness") or "normal"

    def set_awareness(self, level):
        self.set_state("awareness", level)

    def get_awareness_bonus(self):
        self.ensure_core_defaults()
        bonus = int(getattr(self.db, "awareness_bonus", 0) or 0)
        if "sight" in (getattr(self.db, "khri_active", None) or {}):
            bonus += 5
        if self.is_profession("ranger"):
            bonus += self.get_ranger_companion_awareness_bonus()
            bonus += self.get_ranger_beseech_bonus("detection_bonus")
        return bonus

    def adjust_awareness_bonus(self, amount):
        self.ensure_core_defaults()
        self.db.awareness_bonus = max(0, self.get_awareness_bonus() + int(amount or 0))
        return self.db.awareness_bonus

    def get_awareness_score(self, extra_bonus=0):
        base = {
            "unaware": 10,
            "normal": 30,
            "alert": 50,
            "searching": 65,
        }.get(str(self.get_awareness()).lower(), 30)
        return base + self.get_awareness_bonus() + int(extra_bonus or 0)

    def add_crime(self, severity=1):
        self.ensure_core_defaults()
        room = getattr(self, "location", None)
        if room and hasattr(room, "is_lawless") and room.is_lawless():
            return int(getattr(self.db, "crime_severity", 0) or 0)

        self.db.crime_flag = True
        self.db.crime_severity = int(getattr(self.db, "crime_severity", 0) or 0) + int(severity or 0)
        if not self.db.warrants:
            self.db.warrants = {}
        region = room.get_region() if room and hasattr(room, "get_region") else "default_region"
        entry = dict(self.db.warrants.get(region, {"severity": 0, "timestamp": time.time()}))
        entry["severity"] = int(entry.get("severity", 0) or 0) + 1
        entry["bounty"] = int(entry.get("bounty", 0) or 0) + 10 + (int(severity or 0) * 5)
        entry["timestamp"] = time.time()
        self.db.warrants[region] = entry
        self.db.last_known_region = region
        if getattr(self.db, "debug_mode", False):
            print(f"[WARRANT] {self} in {region} severity={entry['severity']}")
        return self.db.crime_severity

    def is_criminal(self):
        warrants = getattr(self.db, "warrants", None) or {}
        return bool(getattr(self.db, "crime_flag", False) or warrants)

    def has_unpaid_fine(self):
        return bool(getattr(self.db, "fine_due", 0) and getattr(self.db, "fine_due", 0) > 0)

    def get_confiscated_items(self):
        items = []
        for item_id in getattr(self.db, "confiscated_items", None) or []:
            result = search_object(item_id)
            if result:
                items.append(result[0])
        return items

    def get_bounty_target(self):
        target_id = getattr(self.db, "active_bounty", None)
        if target_id is None:
            return None
        result = search_object(f"#{target_id}")
        return result[0] if result else None

    def can_trade(self):
        return not self.has_unpaid_fine()

    def process_justice_tick(self):
        if self.has_unpaid_fine():
            check_liquidation(self)

        if getattr(self.db, "warrants", None):
            decay_warrants(self)

        from world.systems import justice

        justice.process_justice_state_tick(self)

        if getattr(self.db, "awaiting_plea", False) and time.time() >= float(getattr(self.ndb, "plea_deadline", 0) or 0):
            from utils.crime import resolve_justice_case

            self.db.plea = "guilty"
            self.db.awaiting_plea = False
            resolve_justice_case(self)

    def process_thief_tick(self):
        now = time.time()

        mark_data = dict(getattr(self.db, "mark_data", None) or {})
        if getattr(self.db, "marked_target", None) and now - float(mark_data.get("timestamp", 0) or 0) > 60:
            self.db.marked_target = None
            self.db.mark_data = {}

        khri_active = dict(getattr(self.db, "khri_active", None) or {})
        if khri_active:
            drain = len(khri_active)
            self.db.khri_pool = max(0, int(getattr(self.db, "khri_pool", 0) or 0) - drain)
            if getattr(self.db, "khri_pool", 0) <= 0:
                self.db.khri_active = {}
                self.msg("Your focus collapses.")

        theft_memory = dict(getattr(self.db, "theft_memory", None) or {})
        changed_memory = False
        for thief_id, memory in list(theft_memory.items()):
            if now - float((memory or {}).get("last_attempt", 0) or 0) > 600:
                memory["count"] = max(0, int(memory.get("count", 0) or 0) - 1)
                if memory["count"] <= 0:
                    theft_memory.pop(thief_id, None)
                else:
                    theft_memory[thief_id] = memory
                changed_memory = True
        if changed_memory:
            self.db.theft_memory = theft_memory

        if getattr(self.db, "slipping", False) and now - float(getattr(self.db, "slip_timer", 0) or 0) > 5:
            self.db.slip_bonus = 0
            self.db.slipping = False

        if getattr(self.db, "intimidated", False) and now - float(getattr(self.db, "intimidation_timer", 0) or 0) > 10:
            self.db.intimidated = False

        if getattr(self.db, "roughed", False) and now - float(getattr(self.db, "rough_timer", 0) or 0) > 8:
            self.db.roughed = False

        if getattr(self.db, "staggered", False) and now - float(getattr(self.db, "stagger_timer", 0) or 0) > 5:
            self.clear_stagger()

        position_changed_at = float(getattr(self.db, "position_changed_at", 0) or 0)
        if getattr(self.db, "position_state", "neutral") != "neutral" and position_changed_at and now - position_changed_at > 8:
            self.db.position_state = "neutral"
            self.db.position_changed_at = now

        if getattr(self.db, "attention_state", "idle") != "idle" and now - float(getattr(self.db, "attention_changed_at", 0) or 0) > 10:
            self.db.attention_state = "idle"
            self.db.attention_changed_at = now

        if getattr(self.db, "recent_action", False) and now - float(getattr(self.db, "recent_action_timer", 0) or 0) > 3:
            self.db.recent_action = False

        if getattr(self.db, "post_ambush_grace", False) and now >= float(getattr(self.db, "post_ambush_grace_until", 0) or 0):
            self.db.post_ambush_grace = False
            self.db.post_ambush_grace_until = 0

    def process_warrior_tick(self):
        states = dict(getattr(self.db, "states", None) or {})
        changed = False
        now = time.time()
        frenzy_ended = False

        for key in [
            "warrior_surge",
            "warrior_crush",
            "warrior_press",
            "warrior_sweep",
            "warrior_whirl",
            "warrior_hold",
            "warrior_frenzy",
        ]:
            state = states.get(key)
            if not isinstance(state, Mapping):
                continue
            expires_at = float(state.get("expires_at", 0) or 0)
            if expires_at and now >= expires_at:
                if key == "warrior_frenzy":
                    frenzy_ended = True
                states.pop(key, None)
                changed = True

        active_berserk = self.get_active_warrior_berserk()
        if active_berserk:
            drain = max(1, int(active_berserk.get("drain_per_tick", 1) or 1))
            current_tempo = self.get_war_tempo()
            if current_tempo <= drain:
                self.db.active_warrior_berserk = None
                self.db.war_tempo = 0
                self.update_war_tempo_state()
                self.msg(active_berserk.get("end_message") or "The fury fades, leaving you exposed.")
                changed = True
            else:
                before_tempo = current_tempo
                self.set_war_tempo(current_tempo - drain, sync=False)
                changed = changed or self.get_war_tempo() != before_tempo
                sustain = int((EXHAUSTION_GAIN_RATES.get("berserk_tick") or {}).get(active_berserk.get("key"), 0) or 0)
                if sustain > 0:
                    before_exhaustion = self.get_exhaustion()
                    self.add_exhaustion(sustain, emit_messages=False, sync=False)
                    changed = changed or self.get_exhaustion() != before_exhaustion

        if getattr(self.db, "in_combat", False):
            before_exhaustion = self.get_exhaustion()
            self.add_exhaustion(int(EXHAUSTION_GAIN_RATES.get("combat_tick", 0) or 0), emit_messages=False, sync=False)
            changed = changed or self.get_exhaustion() != before_exhaustion
        else:
            before_exhaustion = self.get_exhaustion()
            self.set_exhaustion(self.get_exhaustion() - int(RECOVERY_RATES.get("out_of_combat", 0) or 0), emit_messages=False, sync=False)
            changed = changed or self.get_exhaustion() != before_exhaustion

        if frenzy_ended:
            spike = int(EXHAUSTION_GAIN_RATES.get("frenzy_end_spike", 0) or 0)
            if spike > 0:
                before_exhaustion = self.get_exhaustion()
                self.add_exhaustion(spike, sync=False)
                changed = changed or self.get_exhaustion() != before_exhaustion
                self.msg("The frenzy leaves your body shaking with exhaustion.")

        active_roars = dict(getattr(self.db, "active_warrior_roars", None) or {})
        for slot, roar_data in list(active_roars.items()):
            expires_at = float((roar_data or {}).get("expires_at", 0) or 0)
            if expires_at and now >= expires_at:
                active_roars.pop(slot, None)
                changed = True
        if changed:
            self.db.active_warrior_roars = active_roars

        roar_effects = dict(getattr(self.db, "warrior_roar_effects", None) or {})
        for key, effect in list(roar_effects.items()):
            expires_at = float((effect or {}).get("expires_at", 0) or 0)
            if expires_at and now >= expires_at:
                roar_effects.pop(key, None)
                changed = True
        if changed:
            self.db.warrior_roar_effects = roar_effects

        if now - float(getattr(self.db, "last_combat_action_at", 0) or 0) > 10 and int(getattr(self.db, "combat_streak", 0) or 0) > 0:
            changed = self.break_combat_rhythm(show_message=True, sync=False) or changed

        pressure = self.get_pressure_level() if hasattr(self, "get_pressure_level") else 0
        if pressure > 0 and not getattr(self.db, "in_combat", False):
            decay = 8 if not getattr(self.db, "target", None) else 5
            updated_pressure = self.set_pressure_level(pressure - decay, emit_messages=False, sync=False)
            changed = changed or updated_pressure != pressure

        if changed:
            self.db.states = states
            self.sync_client_state()

    def process_ranger_tick(self):
        if not self.is_profession("ranger"):
            return False
        return self.tick_ranger_state()

    def release_from_stocks(self):
        release_from_stocks(self)

    def get_perception_total(self):
        self.ensure_core_defaults()
        perception_rank = self.get_skill("perception")
        intelligence = self.db.stats.get("intelligence", 10)
        wisdom = self.db.stats.get("wisdom", 10)
        awareness = self.get_awareness()
        head_damage = (self.get_body_part("head") or {}).get("external", 0)

        if awareness == "alert":
            perception_rank += 5
        elif awareness == "searching":
            perception_rank += 10
        elif awareness == "unaware":
            perception_rank -= 10

        perception_rank -= head_damage // 4
        if self.is_profession("ranger"):
            perception_rank += self.get_ranger_perception_bonus()
            perception_rank += self.get_ranger_beseech_bonus("perception_bonus")

        return perception_rank + intelligence + wisdom

    def ensure_body_state(self):
        self.ensure_injury_defaults()

    def get_injury_severity(self, value):
        if value <= 0:
            return "minor"
        elif value <= 5:
            return "minor"
        elif value <= 15:
            return "light"
        elif value <= 30:
            return "moderate"
        elif value <= 60:
            return "severe"
        return "critical"

    def transfer_bodypart(self, target, part, skill, transfer_budget):
        self.ensure_body_state()
        target.ensure_body_state()

        source_part = target.get_body_part(part)
        empath_part = self.get_body_part(part)
        if not source_part or not empath_part or transfer_budget <= 0:
            return {"external": 0, "internal": 0, "bleed": 0, "spent": 0}

        remaining = max(0, transfer_budget)
        external_transfer = min(source_part.get("external", 0), remaining)
        remaining -= external_transfer
        internal_transfer = min(source_part.get("internal", 0), remaining)
        remaining -= internal_transfer
        bleed_transfer = min(source_part.get("bleed", 0), remaining)
        spent = external_transfer + internal_transfer + bleed_transfer

        source_part["external"] -= external_transfer
        source_part["internal"] -= internal_transfer
        source_part["bleed"] -= bleed_transfer

        empath_part["external"] += external_transfer
        empath_part["internal"] += internal_transfer
        empath_part["bleed"] += bleed_transfer

        instability_chance = min(0.5, self.get_empath_load() / 150) if spent > 0 else 0
        if spent > 0 and random.random() < instability_chance:
            self.msg("The transfer slips unevenly!")
            empath_part["internal"] += 2

        return {
            "external": external_transfer,
            "internal": internal_transfer,
            "bleed": bleed_transfer,
            "spent": spent,
        }

    def transfer_wounds(self, target):
        self.ensure_body_state()
        target.ensure_body_state()

        if self.is_overloaded():
            self.msg("You are too overwhelmed to continue healing!")
            return False

        skill = self.get_skill("empathy")
        transferred_any = False
        transfer_budget = max(1, skill // 5)
        total_damage = 0
        part_totals = {}

        for part in BODY_PART_ORDER:
            body_part = target.get_body_part(part) or {}
            part_total = int(body_part.get("external", 0)) + int(body_part.get("internal", 0)) + int(body_part.get("bleed", 0))
            if part_total > 0:
                part_totals[part] = part_total
                total_damage += part_total

        if total_damage <= 0:
            return False

        remaining_budget = transfer_budget
        ordered_parts = [part for part in BODY_PART_ORDER if part in part_totals]

        for index, part in enumerate(ordered_parts):
            if remaining_budget <= 0:
                break
            if index == len(ordered_parts) - 1:
                part_budget = remaining_budget
            else:
                share = part_totals[part] / total_damage
                part_budget = max(1, int(round(transfer_budget * share)))
                part_budget = min(part_budget, remaining_budget)

            transferred = self.transfer_bodypart(target, part, skill, part_budget)
            remaining_budget -= transferred.get("spent", 0)
            if any(value for key, value in transferred.items() if key != "spent"):
                transferred_any = True

        self.update_bleed_state()
        target.update_bleed_state()

        if self.get_empath_load() > 80:
            self.msg("You feel overwhelmed by accumulated injuries.")

        if self.get_empath_load() > 120:
            self.msg("The pain overwhelms you!")
            self.set_hp((self.db.hp or 0) - 5)

        if transferred_any:
            self.msg(f"You draw wounds from {target.key}.")
            target.msg("Your pain lessens as your wounds are drawn away.")
            self.award_empathy_experience("legacy_transfer", skill + 10, amount=transfer_budget, target=target)

        return transferred_any

    def describe_bodypart(self, part):
        body_part = self.get_body_part(part) or {}
        external = self.get_injury_severity(body_part.get("external", 0))
        internal = self.get_injury_severity(body_part.get("internal", 0))
        part_display = self.format_body_part_name(part)
        return f"Your {part_display} is {external} wounded and {internal} internally injured."

    def is_box_target(self, obj):
        return bool(obj and getattr(obj.db, "is_box", False))

    def describe_lock_difficulty(self, difficulty):
        skill = self.get_skill("locksmithing")
        diff = difficulty - skill

        if diff <= -20:
            return "simple"
        elif diff <= 0:
            return "manageable"
        elif diff <= 20:
            return "tricky"
        return "dangerous"

    def inspect_box(self, box):
        self.msg("You study the box carefully.")

        lock_desc = self.describe_lock_difficulty(box.db.lock_difficulty)
        self.msg(f"It appears to have a {lock_desc} lock.")

        if box.db.trap_present:
            trap_desc = self.describe_lock_difficulty(box.db.trap_difficulty)
            if self.get_skill("locksmithing") >= max(1, box.db.trap_difficulty - 10):
                self.msg(f"You suspect a {trap_desc} trap may be present.")
            else:
                self.msg("You cannot tell whether it has been trapped.")
        else:
            self.msg("You notice no obvious sign of a trap.")

        award_exp_skill(
            self,
            "locksmithing",
            max(10, int(box.db.lock_difficulty or 0)),
            success=True,
            outcome="success",
            event_key="locksmithing",
        )

    def locksmith_contest(self, difficulty, stat="intelligence"):
        skill = self.get_skill("locksmithing")
        stat_val = self.db.stats.get(stat, 10)
        return run_contest(skill + stat_val, difficulty, attacker=self)

    def disarm_box(self, box):
        if not box.db.trap_present:
            self.msg("You find no trap.")
            return

        if box.db.disarmed:
            self.msg("The trap has already been disarmed.")
            return

        self.msg("You carefully attempt to disarm the trap...")
        msg_room(self, f"{self.key} examines a box carefully.", exclude=[self])

        result = self.locksmith_contest(box.db.trap_difficulty)
        if result.get("diff", 0) < -30:
            self.trigger_box_trap(box)
            return

        outcome = result["outcome"]
        if outcome == "fail":
            self.msg("You fail to locate the trap mechanism.")
            return

        if outcome == "partial":
            self.msg("You think you understand part of the trap, but not enough to safely disarm it.")
            award_exp_skill(
                self,
                "locksmithing",
                max(10, int(box.db.trap_difficulty or 0)),
                success=False,
                outcome="partial",
                event_key="trap_disarm",
            )
            return

        if outcome in ("success", "strong"):
            box.db.disarmed = True
            box.db.last_disarmed_trap = box.db.trap_type
            self.db.last_disarmed_trap = box.db.trap_type
            self.db.last_disarmed_trap_difficulty = int(box.db.trap_difficulty or 0)
            self.db.last_disarmed_trap_source = getattr(box, "id", None)
            self.msg("You successfully disarm the trap.")
            award_exp_skill(
                self,
                "locksmithing",
                max(10, int(box.db.trap_difficulty or 0)),
                success=True,
                outcome=outcome,
                event_key="trap_disarm",
            )

    def trigger_box_trap(self, box):
        trap_type = box.db.trap_type or "generic"
        self.msg("You trigger the trap!")
        msg_room(self, f"{self.key} triggers a trap on a box!", exclude=[self])
        self.apply_box_trap_effect(trap_type)

    def apply_box_trap_effect(self, trap_type):
        current_hp = self.db.hp or 0
        if trap_type == "needle":
            self.set_hp(current_hp - 5)
            self.msg("You feel a sharp sting from a hidden needle!")
        elif trap_type == "blade":
            self.set_hp(current_hp - 8)
            self.msg("A concealed blade slices into you!")
        elif trap_type == "gas":
            self.set_hp(current_hp - 4)
            self.msg("A cloud of gas bursts into your face!")
            self.set_awareness("unaware")
        elif trap_type == "explosive":
            self.set_hp(current_hp - 12)
            self.msg("The trap erupts violently!")
        elif trap_type == "alarm":
            self.msg("A sharp noise rings out!")
            if self.location:
                for obj in self.location.contents:
                    if hasattr(obj, "set_awareness"):
                        obj.set_awareness("alert")
        elif trap_type == "smoke":
            self.msg("Smoke fills your eyes!")
            self.db.temp_perception_penalty = 5
        elif trap_type == "barb":
            self.msg("A hidden barb tears into you!")
            self.set_hp(current_hp - 4)
            body_part = self.get_body_part("right_arm") or self.get_body_part("left_arm")
            if body_part is not None:
                body_part["bleed"] = int(body_part.get("bleed", 0)) + 2
            self.update_bleed_state()
        else:
            self.set_hp(current_hp - 3)
            self.msg("The trap injures you.")

    def get_active_lockpick(self):
        for item in self.contents:
            if getattr(item.db, "is_lockpick", False):
                return item
        return None

    def get_lockpick_by_grade(self, grade):
        for item in self.contents:
            if getattr(item.db, "is_lockpick", False) and getattr(item.db, "grade", None) == grade:
                return item
        return None

    def has_lockpick(self):
        return self.get_active_lockpick() is not None

    def analyze_trap(self, box):
        trap = box.db.last_disarmed_trap

        if not trap:
            self.msg("There is no trap to analyze.")
            return

        self.msg("You carefully analyze the trap mechanism.")

        if trap == "needle":
            self.msg("It appears to be a needle-based trap.")
        elif trap == "gas":
            self.msg("It uses a gas-release mechanism.")
        elif trap == "blade":
            self.msg("It relies on a concealed blade trigger.")
        elif trap == "explosive":
            self.msg("It looks built around a volatile explosive charge.")
        else:
            self.msg("You cannot determine its exact function.")

        award_exp_skill(
            self,
            "locksmithing",
            max(10, int(box.db.trap_difficulty or 0)),
            success=True,
            outcome="success",
            event_key="trap_disarm",
        )

    def create_trap_component(self, trap_type):
        return self.create_trap_component_with_tier(trap_type, "standard", rare=False)

    def create_trap_component_with_tier(self, trap_type, tier, rare=False):
        prefix = "rare " if rare else ""
        key = f"{prefix}{tier} {trap_type} component".strip()
        desc = f"A {prefix}{tier} trap component recovered from a disarmed {trap_type} mechanism.".strip()
        return create_simple_item(
            self,
            key=key,
            desc=desc,
            trap_component=True,
            trap_type=trap_type,
            component_tier=tier,
            rare_component=rare,
        )

    def harvest_trap(self, box):
        trap = box.db.last_disarmed_trap

        if not trap:
            self.msg("There is nothing to harvest.")
            return

        result = self.locksmith_contest(box.db.trap_difficulty)
        outcome = result["outcome"]

        if outcome == "fail":
            self.msg("You fail to recover anything useful.")
            return

        if outcome == "partial":
            self.msg("You recover a few damaged components.")
            self.create_trap_component_with_tier(trap, "low", rare=False)
            award_exp_skill(
                self,
                "locksmithing",
                max(10, int(box.db.trap_difficulty or 0)),
                success=False,
                outcome="partial",
                event_key="trap_disarm",
            )
        elif outcome in ("success", "strong"):
            self.msg("You successfully recover useful trap components.")
            tier = "standard" if outcome == "success" else "high"
            rare = random.random() < 0.1
            self.create_trap_component_with_tier(trap, tier, rare=rare)
            award_exp_skill(
                self,
                "locksmithing",
                max(10, int(box.db.trap_difficulty or 0)),
                success=True,
                outcome=outcome,
                event_key="trap_disarm",
            )
        box.db.last_disarmed_trap = None
        if getattr(self.db, "last_disarmed_trap_source", None) == getattr(box, "id", None):
            self.db.last_disarmed_trap = None
            self.db.last_disarmed_trap_difficulty = 0
            self.db.last_disarmed_trap_source = None

    def get_deployable_trap_device(self):
        for obj in self.contents:
            if getattr(obj.db, "is_trap_device", False):
                return obj
        return None

    def rework_trap(self):
        trap = self.db.last_disarmed_trap
        if not trap:
            self.msg("You have no trap to rework.")
            return

        difficulty = max(20, int(self.db.last_disarmed_trap_difficulty or 0))
        result = self.locksmith_contest(difficulty)
        outcome = result.get("outcome")

        if outcome == "fail":
            self.msg("You fail to rework the trap.")
            return

        device = self.get_deployable_trap_device()
        if device:
            self.msg("You are already carrying a deployable device.")
            return

        device = create_object(
            TrapDevice,
            key="concealed device",
            location=self,
            home=self,
        )
        device.db.trap_type = trap
        device.db.owner = self
        device.db.expire_time = 30 if outcome == "partial" else 60

        if outcome == "partial":
            self.msg("You manage to produce a fragile device.")
        else:
            self.msg("You successfully rework the trap into a deployable device.")

        self.db.last_disarmed_trap = None
        self.db.last_disarmed_trap_difficulty = 0
        self.db.last_disarmed_trap_source = None
        award_exp_skill(
            self,
            "locksmithing",
            difficulty,
            success=outcome != "partial",
            outcome=outcome,
            event_key="trap_disarm",
        )

    def deploy_trap(self):
        if not self.location:
            self.msg("You have nowhere to set a trap.")
            return

        device = self.get_deployable_trap_device()
        if not device:
            self.msg("You have no device to deploy.")
            return

        for obj in self.location.contents:
            if not getattr(obj.db, "is_trap_device", False):
                continue
            if obj.db.owner == self and getattr(obj, "pk", None):
                self.msg("You already have a trap set here.")
                return

        device.move_to(self.location, quiet=True)
        device.db.owner = self
        device.db.hidden = True
        device.db.armed = True
        device.db.triggered = False
        device.db.placed_time = time.time()
        device.db.concealment = self.get_skill("stealth") + self.get_stat("agility")
        device.db.detected_by = []
        if hasattr(device, "schedule_expiry"):
            device.schedule_expiry()

        self.msg("You carefully set a concealed device.")
        msg_room(self, f"{self.key} crouches briefly near the ground.", exclude=[self])

    def detect_traps_in_room(self):
        if not self.location:
            return []

        detected = []
        perception_total = self.get_skill("perception") + self.get_stat("wisdom")
        for obj in self.location.contents:
            if not getattr(obj.db, "is_trap_device", False):
                continue
            if not hasattr(obj, "is_active") or not obj.is_active():
                continue
            if obj.db.owner == self:
                continue

            concealment = int(obj.db.concealment or 0)
            if perception_total <= concealment:
                continue

            obj.remember_detection(self)
            detected.append(obj)

        if detected:
            self.msg("You notice something unusual on the ground.")
            self.use_skill(
                "perception",
                apply_roundtime=False,
                emit_placeholder=False,
                require_known=False,
                difficulty=max(10, max(int(obj.db.concealment or 0) for obj in detected)),
            )

        return detected

    def get_item_value(self, item):
        if not item:
            return 0

        explicit_value = getattr(item.db, "value", None)
        if explicit_value is not None:
            return max(1, int(explicit_value))

        explicit = getattr(item.db, "item_value", None)
        if explicit is not None:
            return max(1, int(explicit))

        if getattr(item.db, "is_gem", False):
            return max(1, int(getattr(item.db, "final_value", 1) or 1))

        if getattr(item.db, "box_loot", False):
            difficulty = int(getattr(item.db, "loot_difficulty", 10) or 10)
            return max(5, difficulty)

        if getattr(item.db, "trap_component", False):
            tier_bonus = {
                "low": 6,
                "standard": 12,
                "high": 20,
            }.get(str(getattr(item.db, "component_tier", "standard") or "standard").lower(), 12)
            return tier_bonus + (8 if getattr(item.db, "rare_component", False) else 0)

        if getattr(item.db, "item_type", None) == "weapon" or getattr(item.db, "weapon_type", None):
            damage_min = int(getattr(item.db, "damage_min", 1) or 1)
            damage_max = int(getattr(item.db, "damage_max", 4) or 4)
            balance = int(getattr(item.db, "balance", 50) or 50)
            return max(5, (damage_min + damage_max) * 3 + max(0, balance - 35))

        if getattr(item.db, "item_type", None) == "armor" or getattr(item.db, "armor_type", None):
            protection = int(getattr(item.db, "protection", 1) or 1)
            hindrance = int(getattr(item.db, "hindrance", 0) or 0)
            coverage = len(getattr(item.db, "coverage", None) or getattr(item.db, "covers", None) or [])
            return max(5, (protection * 8) + (coverage * 3) - hindrance)

        if getattr(item.db, "is_box", False):
            return max(8, int(getattr(item.db, "lock_difficulty", 0) or 0) + int(getattr(item.db, "trap_difficulty", 0) or 0))

        return max(1, len(str(getattr(item, "key", "") or "")))

    def format_coins(self, amount):
        remaining = max(0, int(amount or 0))
        if remaining <= 0:
            return "0 copper"
        parts = []
        for name, value in COIN_DENOMINATIONS:
            count, remaining = divmod(remaining, value)
            if count <= 0:
                continue
            label = name if count == 1 else f"{name}s"
            parts.append(f"{count} {label}")
        return ", ".join(parts) if parts else "0 copper"

    def add_coins(self, amount):
        value = max(0, int(amount or 0))
        self.db.coins = max(0, int(getattr(self.db, "coins", 0) or 0) + value)
        self.update_encumbrance_state()
        self.update_coin_weight_notice()
        return int(self.db.coins or 0)

    def has_coins(self, amount):
        return int(getattr(self.db, "coins", 0) or 0) >= max(0, int(amount or 0))

    def remove_coins(self, amount):
        value = max(0, int(amount or 0))
        if not self.has_coins(value):
            return False
        self.db.coins = int(getattr(self.db, "coins", 0) or 0) - value
        self.update_encumbrance_state()
        self.update_coin_weight_notice()
        return True

    def get_max_carry_weight(self):
        self.ensure_race_defaults()
        max_carry = max(float(WEIGHT_UNIT), float(BASE_CARRY_WEIGHT) * self.get_race_carry_modifier())
        if abs(float(getattr(self.db, "max_carry_weight", max_carry) or max_carry) - max_carry) > 0.0001:
            self.db.max_carry_weight = max_carry
        return max_carry

    def get_coin_weight(self, coins=None):
        return max(0, int(getattr(self.db, "coins", 0) if coins is None else coins or 0)) * COIN_WEIGHT

    def get_object_total_weight(self, obj, depth=0, seen=None):
        if not obj:
            return 0.0
        seen = set(seen or set())
        object_id = int(getattr(obj, "id", 0) or 0)
        if object_id and object_id in seen:
            return 0.0
        if object_id:
            seen.add(object_id)

        if depth >= MAX_CONTAINER_WEIGHT_DEPTH:
            LOGGER.error("Container weight calculation exceeded max depth for %s", obj)
            weight = getattr(getattr(obj, "db", None), "weight", 0.0)
            try:
                return max(0.0, float(weight or 0.0))
            except (TypeError, ValueError):
                return 0.0

        if hasattr(obj, "get_total_weight"):
            try:
                return max(0.0, float(obj.get_total_weight(depth=depth, max_depth=MAX_CONTAINER_WEIGHT_DEPTH, seen=seen) or 0.0))
            except TypeError:
                return max(0.0, float(obj.get_total_weight() or 0.0))

        weight = getattr(getattr(obj, "db", None), "weight", None)
        if weight is None:
            if not getattr(getattr(obj, "ndb", None), "missing_weight_logged", False):
                LOGGER.error("Missing weight on object %s", obj)
                obj.ndb.missing_weight_logged = True
            return 0.0
        try:
            return max(0.0, float(weight))
        except (TypeError, ValueError):
            LOGGER.error("Invalid weight on object %s", obj)
            return 0.0

    def get_total_weight(self):
        total = self.get_coin_weight()
        for item in list(getattr(self, "contents", []) or []):
            total += self.get_object_total_weight(item)
        for item in self.get_worn_items():
            total += self.get_object_total_weight(item)
        return float(total)

    def update_encumbrance_state(self):
        ratio = self.get_total_weight() / max(WEIGHT_UNIT, self.get_max_carry_weight())
        self.db.encumbrance_ratio = float(ratio)
        self.db.encumbrance_dirty = False
        return self.db.encumbrance_ratio

    def get_encumbrance_ratio(self):
        cached = getattr(self.db, "encumbrance_ratio", None)
        dirty = bool(getattr(self.db, "encumbrance_dirty", False))
        if cached is None or dirty:
            return float(self.update_encumbrance_state())
        try:
            return float(cached)
        except (TypeError, ValueError):
            return float(self.update_encumbrance_state())

    def get_encumbrance_state(self):
        ratio = self.get_encumbrance_ratio()
        if ratio < 0.5:
            return "Light"
        if ratio < 0.8:
            return "Moderate"
        if ratio < 1.0:
            return "Heavy"
        return "Overloaded"

    def update_coin_weight_notice(self):
        threshold = self.get_max_carry_weight() * 0.1
        noticeable = self.get_coin_weight() >= threshold if threshold > 0 else False
        if noticeable and not bool(getattr(self.db, "coin_weight_notice_active", False)):
            self.msg("The weight of your coins is becoming noticeable.")
        self.db.coin_weight_notice_active = noticeable

    def can_pick_up_item(self, item):
        if self.get_encumbrance_ratio() >= 1.0:
            self.msg("You are carrying too much to pick that up.")
            return False
        if self.get_object_total_weight(item) <= 0 and getattr(getattr(item, "db", None), "weight", None) is None:
            self.msg("That cannot be carried right now.")
            return False
        return True

    def get_bank_coins(self):
        return max(0, int(getattr(self.db, "bank_coins", 0) or 0))

    def add_bank_coins(self, amount):
        value = max(0, int(amount or 0))
        self.db.bank_coins = self.get_bank_coins() + value
        return self.db.bank_coins

    def remove_bank_coins(self, amount):
        value = max(0, int(amount or 0))
        current = self.get_bank_coins()
        if current < value:
            return False
        self.db.bank_coins = current - value
        return True

    def is_in_bank(self):
        room = getattr(self, "location", None)
        if not room:
            return False
        if hasattr(room, "is_bank_room"):
            return bool(room.is_bank_room())
        return bool(getattr(getattr(room, "db", None), "is_bank", False))

    def is_in_vault(self):
        room = getattr(self, "location", None)
        if not room:
            return False
        if hasattr(room, "is_vault_room"):
            return bool(room.is_vault_room())
        return bool(getattr(getattr(room, "db", None), "is_vault", False))

    def parse_coin_amount(self, amount_text, available):
        text = str(amount_text or "").strip().lower()
        if text == "all":
            return max(0, int(available or 0))
        try:
            amount = int(text)
        except (TypeError, ValueError):
            return None
        if amount <= 0:
            return None
        return amount

    def can_use_bank_account(self):
        if self.is_dead():
            self.msg("You cannot access your account in this state.")
            return False
        return True

    def deposit_coins(self, amount_text):
        if not self.can_use_bank_account():
            return False
        if not self.is_in_bank():
            self.msg("You must be at a bank to do that.")
            return False
        amount = self.parse_coin_amount(amount_text, int(getattr(self.db, "coins", 0) or 0))
        if amount is None or amount > int(getattr(self.db, "coins", 0) or 0):
            self.msg("You do not have that much.")
            return False
        self.remove_coins(amount)
        self.add_bank_coins(amount)
        self.msg(f"You deposit {self.format_coins(amount)} into your account.")
        return True

    def withdraw_coins(self, amount_text):
        if not self.can_use_bank_account():
            return False
        if not self.is_in_bank():
            self.msg("You must be at a bank to do that.")
            return False
        amount = self.parse_coin_amount(amount_text, self.get_bank_coins())
        if amount is None or amount > self.get_bank_coins():
            self.msg("You do not have that much in your account.")
            return False
        self.remove_bank_coins(amount)
        self.add_coins(amount)
        self.msg(f"You withdraw {self.format_coins(amount)} from your account.")
        return True

    def show_bank_balance(self):
        if not self.can_use_bank_account():
            return False
        self.msg(f"On hand: {self.format_coins(int(getattr(self.db, 'coins', 0) or 0))}\nIn bank: {self.format_coins(self.get_bank_coins())}")
        return True

    def get_vault_item_ids(self):
        raw = list(getattr(self.db, "vault_items", None) or [])
        valid_ids = []
        for entry in raw:
            try:
                value = int(entry)
            except (TypeError, ValueError):
                continue
            if value > 0:
                valid_ids.append(value)
        if valid_ids != raw:
            self.db.vault_items = valid_ids
        return valid_ids

    def get_vault_items(self):
        items = []
        kept_ids = []
        for item_id in self.get_vault_item_ids():
            result = search_object(f"#{item_id}")
            item = result[0] if result else None
            if not item:
                continue
            if int(getattr(getattr(item, "db", None), "vault_owner_id", 0) or 0) not in {0, int(self.id or 0)}:
                continue
            kept_ids.append(item_id)
            items.append(item)
        if kept_ids != self.get_vault_item_ids():
            self.db.vault_items = kept_ids
        return items

    def is_item_stored(self, item):
        if not item:
            return False
        return int(getattr(item, "id", 0) or 0) in set(self.get_vault_item_ids())

    def is_item_equipped_or_worn(self, item):
        if not item:
            return False
        if getattr(item.db, "worn_by", None) == self:
            return True
        if self.get_wielded_weapon() == item:
            return True
        return item in self.get_worn_items()

    def store_vault_item(self, item_name):
        if not self.is_in_vault():
            self.msg("You must be in a vault to do that.")
            return False
        item, matches, base_query, index = self.resolve_numbered_candidate(
            item_name,
            self.get_visible_carried_items(),
            default_first=True,
        )
        if not item:
            if matches and index is not None:
                self.msg_numbered_matches(base_query, matches)
            else:
                self.msg("You are not carrying that.")
            return False
        if self.is_item_equipped_or_worn(item):
            self.msg("You must remove that before storing it.")
            return False
        item.location = None
        item.db.vault_owner_id = int(self.id or 0)
        stored_ids = self.get_vault_item_ids()
        stored_ids.append(int(item.id))
        self.db.vault_items = stored_ids
        self.update_encumbrance_state()
        self.msg(f"You place {item.key} into storage.")
        return True

    def retrieve_vault_item(self, item_name):
        if not self.is_in_vault():
            self.msg("You must be in a vault to do that.")
            return False
        item, matches, base_query, index = self.resolve_numbered_candidate(
            item_name,
            self.get_vault_items(),
            default_first=True,
        )
        if not item:
            if matches and index is not None:
                self.msg_numbered_matches(base_query, matches)
            else:
                self.msg("You do not have that in storage.")
            return False
        stored_ids = [item_id for item_id in self.get_vault_item_ids() if item_id != int(item.id)]
        self.db.vault_items = stored_ids
        item.db.vault_owner_id = None
        item.move_to(self, quiet=True)
        self.update_encumbrance_state()
        self.msg(f"You retrieve {item.key} from storage.")
        return True

    def get_gem_pouch(self):
        for item in list(getattr(self, "contents", []) or []):
            if bool(getattr(item.db, "is_gem_pouch", False)):
                return item
        return None

    def store_loot_item(self, item):
        if not item:
            return False
        if bool(getattr(item.db, "is_gem", False)):
            pouch = self.get_gem_pouch()
            if pouch and item.location != pouch:
                return item.move_to(pouch, quiet=True)
        if item.location != self:
            return item.move_to(self, quiet=True)
        return True

    def get_total_gem_value(self, gems):
        total = 0
        for gem in list(gems or []):
            total += int(getattr(getattr(gem, "db", None), "final_value", 0) or getattr(getattr(gem, "db", None), "value", 0) or 0)
        return total

    def cap_corpse_gem_value(self, holder, max_total=1500):
        gems = [item for item in list(getattr(holder, "contents", []) or []) if bool(getattr(item.db, "is_gem", False))]
        while gems and self.get_total_gem_value(gems) > max_total:
            highest = max(gems, key=lambda gem: int(getattr(gem.db, "final_value", 0) or getattr(gem.db, "value", 0) or 0))
            before = (
                str(getattr(highest.db, "gem_type", "quartz") or "quartz"),
                int(getattr(highest.db, "quality_tier", 1) or 1),
                int(getattr(highest.db, "size_tier", 1) or 1),
            )
            downgraded = downgrade_gem_data(
                {
                    "gem_type": before[0],
                    "quality_tier": before[1],
                    "size_tier": before[2],
                }
            )
            after = (
                str(downgraded["gem_type"]),
                int(downgraded["quality_tier"]),
                int(downgraded["size_tier"]),
            )
            if after == before:
                break
            highest.db.gem_type = downgraded["gem_type"]
            highest.db.quality_tier = downgraded["quality_tier"]
            highest.db.size_tier = downgraded["size_tier"]
            highest.sync_gem_state()

    def get_box_contents_value(self, contents):
        total = 0
        for entry in list(contents or []):
            kind = str(entry.get("kind", "") or "").lower()
            if kind == "coins":
                total += max(0, int(entry.get("amount", 0) or 0))
            elif kind == "gem":
                total += max(0, int((entry.get("data") or {}).get("final_value", 0) or 0))
        return total

    def cap_box_contents_value(self, contents, max_total=2000):
        adjusted = [dict(entry) for entry in list(contents or [])]
        while adjusted and self.get_box_contents_value(adjusted) > max_total:
            highest_index = None
            highest_value = -1
            for index, entry in enumerate(adjusted):
                if str(entry.get("kind", "") or "").lower() != "gem":
                    continue
                gem_value = int((entry.get("data") or {}).get("final_value", 0) or 0)
                if gem_value > highest_value:
                    highest_index = index
                    highest_value = gem_value
            if highest_index is not None:
                current_data = dict(adjusted[highest_index].get("data") or {})
                downgraded = downgrade_gem_data(current_data)
                if downgraded == current_data:
                    highest_index = None
                else:
                    adjusted[highest_index]["data"] = downgraded
                    continue

            for entry in adjusted:
                if str(entry.get("kind", "") or "").lower() == "coins" and int(entry.get("amount", 0) or 0) > 0:
                    overflow = self.get_box_contents_value(adjusted) - max_total
                    entry["amount"] = max(0, int(entry.get("amount", 0) or 0) - max(1, overflow))
                    break
            else:
                break

        return adjusted

    def get_loot_gems(self, target):
        return [item for item in list(getattr(target, "contents", []) or []) if bool(getattr(item.db, "is_gem", False))]

    def get_loot_boxes(self, target):
        return [item for item in list(getattr(target, "contents", []) or []) if bool(getattr(item.db, "is_box", False))]

    def is_loot_target_empty(self, target):
        return (
            not bool(getattr(target.db, "has_coins", False))
            and not bool(getattr(target.db, "has_gems", False))
            and not bool(getattr(target.db, "has_box", False))
        )

    def search_loot_target(self, target):
        if not target or not bool(getattr(getattr(target, "db", None), "is_npc", False)):
            self.msg("You cannot search that.")
            return False
        if not hasattr(target, "is_dead") or not target.is_dead():
            self.msg("You cannot search that.")
            return False
        if hasattr(target, "generate_npc_loot"):
            target.generate_npc_loot()
        if bool(getattr(target.db, "searched", False)):
            self.msg("You have already searched this.")
            return False

        target.db.searched = True
        lines = ["You search the corpse carefully."]
        if bool(getattr(target.db, "has_coins", False)):
            lines.append("You find:")
            lines.append("- some coins")
            if bool(getattr(target.db, "has_gems", False)):
                gem_count = len(self.get_loot_gems(target))
                lines.append("- a gemstone" if gem_count == 1 else "- gemstones")
            if bool(getattr(target.db, "has_box", False)):
                lines.append("- a small box")
        else:
            found_any = False
            if bool(getattr(target.db, "has_gems", False)):
                lines.append("You find:")
                gem_count = len(self.get_loot_gems(target))
                lines.append("- a gemstone" if gem_count == 1 else "- gemstones")
                found_any = True
            if bool(getattr(target.db, "has_box", False)):
                if not found_any:
                    lines.append("You find:")
                lines.append("- a small box")
                found_any = True
            if not found_any:
                lines.append("You find nothing of value.")
        self.msg("\n".join(lines))
        return True

    def create_loot_box(self, holder=None):
        box = create_object(Box, key="small box", location=holder or self, home=getattr(self, "location", None) or self)
        box.db.strict_loot_box = True
        box.db.locked = True
        box.db.is_locked = True
        box.db.opened = False
        box.db.is_open = False
        box.db.lock_difficulty = STRICT_BOX_LOCK_DIFFICULTY
        box.db.contents = []
        box.db.weight = 5.0
        box.db.item_value = 25
        box.db.value = 25
        return box

    def populate_loot_box_contents(self, box):
        if not box:
            return []
        contents = [{"kind": "coins", "amount": random.randint(50, 200)}]
        contents.append({"kind": "gem", "data": build_gem_data()})
        if random.random() < 0.2:
            contents.append({"kind": "gem", "data": build_gem_data()})
        box.db.contents = self.cap_box_contents_value(contents, max_total=2000)
        return list(box.db.contents)

    def generate_npc_loot(self):
        if not bool(getattr(self.db, "is_npc", False)) or bool(getattr(self.db, "loot_generated", False)):
            return False
        coin_min = max(0, int(getattr(self.db, "coin_min", 0) or 0))
        coin_max = max(coin_min, int(getattr(self.db, "coin_max", 0) or 0))
        generated_coins = min(random.randint(coin_min, coin_max), 200) if coin_max > 0 else 0
        self.db.stored_coins = generated_coins
        self.db.searched = False
        self.db.coins_looted = False
        self.db.gems_looted = False
        self.db.box_looted = False
        self.db.has_coins = generated_coins > 0

        gem_roll = random.random()
        gem_count = 2 if gem_roll < 0.05 else 1 if gem_roll < 0.35 else 0
        self.db.has_gems = gem_count > 0
        for _ in range(gem_count):
            create_gem(self)
        self.cap_corpse_gem_value(self, max_total=1500)

        self.db.has_box = False
        if bool(getattr(self.db, "drops_box", False)) and random.random() < 0.25:
            box = self.create_loot_box(holder=self)
            self.populate_loot_box_contents(box)
            self.db.has_box = True

        self.db.loot_generated = True
        return True

    def loot_target(self, target):
        if not target or not bool(getattr(getattr(target, "db", None), "is_npc", False)):
            self.msg("You cannot loot that.")
            return False
        if not hasattr(target, "is_dead") or not target.is_dead():
            self.msg("You cannot loot that.")
            return False
        if hasattr(target, "generate_npc_loot"):
            target.generate_npc_loot()
        if not bool(getattr(target.db, "searched", False)):
            self.msg("You need to search the corpse first.")
            return False

        if self.is_loot_target_empty(target):
            self.msg("There is nothing else of value here.")
            return False

        lines = []
        coins = int(getattr(target.db, "stored_coins", 0) or 0)
        if coins > 0 and not bool(getattr(target.db, "coins_looted", False)):
            self.add_coins(coins)
            target.db.coins_looted = True
            target.db.stored_coins = 0
            target.db.has_coins = False
            lines.append(f"You collect {self.format_coins(coins)}.")

        gem_names = []
        if bool(getattr(target.db, "has_gems", False)) and not bool(getattr(target.db, "gems_looted", False)):
            for item in self.get_loot_gems(target):
                if self.store_loot_item(item):
                    gem_names.append(item.key)
            target.db.gems_looted = True
            target.db.has_gems = False
        if gem_names:
            lines.append(f"You gather {', '.join(gem_names)}.")

        box_names = []
        if bool(getattr(target.db, "has_box", False)) and not bool(getattr(target.db, "box_looted", False)):
            for item in self.get_loot_boxes(target):
                if item.location == target and item.move_to(self, quiet=True):
                    box_names.append(item.key)
            target.db.box_looted = True
            target.db.has_box = False
        if box_names:
            lines.append(f"You gather {', '.join(box_names)}.")

        if not lines:
            self.msg("There is nothing else of value here.")
            return False

        self.msg("\n".join(lines))
        return True

    def describe_weapon(self, weapon, skill):
        tier = self.get_appraisal_tier()
        balance = int(getattr(weapon.db, "balance", 10) or 10)

        if tier == "vague":
            self.msg("It looks like a weapon.")
        elif tier == "basic":
            self.msg("It appears somewhat balanced." if balance >= 45 else "It appears somewhat unwieldy.")
        elif tier == "clear":
            self.msg("It seems reasonably balanced and usable." if balance >= 45 else "It seems awkward and somewhat difficult to handle.")
        else:
            if balance >= 60:
                self.msg("It appears very well balanced and likely well suited to practiced hands.")
            elif balance >= 45:
                self.msg("It seems competently balanced, though not exceptional.")
            else:
                self.msg("It appears poorly balanced and likely demanding to use well.")

    def describe_armor(self, armor, skill):
        tier = self.get_appraisal_tier()
        protection = int(getattr(armor.db, "protection", 1) or 1)
        hindrance = int(getattr(armor.db, "hindrance", 0) or 0)

        if tier == "vague":
            self.msg("It looks like armor.")
        elif tier == "basic":
            self.msg("It appears to offer some protection.")
        elif tier == "clear":
            self.msg("It seems to provide solid protection at the cost of some movement.")
        else:
            if protection >= 5 or hindrance >= 3:
                self.msg("It appears to offer strong protection, though it may hinder movement noticeably.")
            else:
                self.msg("It appears to offer respectable protection without much hindrance.")

    def get_appraisal_tier(self):
        skill = self.get_skill("appraisal")

        if skill < 5:
            return "vague"
        if skill < 15:
            return "basic"
        if skill < 30:
            return "clear"
        return "precise"

    def appraise_target(self, target):
        if not target:
            self.msg("Appraise what?")
            return

        if self.is_in_roundtime():
            self.msg_roundtime_block()
            return

        if hasattr(target, "is_hidden") and target.is_hidden() and not self.can_perceive(target):
            self.msg("You cannot get a clear look at it.")
            return

        skill = self.get_skill("appraisal")
        tier = self.get_appraisal_tier()
        perception = self.get_skill("perception")

        if perception < 5:
            self.msg("You struggle to make out enough detail.")
            tier = "vague"
        elif perception < 10 and tier in {"clear", "precise"}:
            tier = "basic"
        elif perception < 15 and tier == "precise":
            tier = "clear"

        self.msg(f"You study {target.key} carefully.")

        if getattr(target.db, "is_gem", False):
            size_name = SIZE_NAMES.get(int(getattr(target.db, "size_tier", 2) or 2), "medium")
            quality_name = QUALITY_NAMES.get(int(getattr(target.db, "quality_tier", 2) or 2), "average")
            gem_type = str(getattr(target.db, "gem_type", "quartz") or "quartz")
            self.msg(f"This appears to be a {size_name} {gem_type} of {quality_name} make.")
            award_exp_skill(self, "appraisal", 10)
            return

        if getattr(target.db, "is_box", False):
            if bool(getattr(target.db, "strict_loot_box", False)):
                self.msg("This appears to be a locked container of moderate weight.")
                award_exp_skill(self, "appraisal", 10)
                return
            lock_desc = self.describe_lock_difficulty(int(getattr(target.db, "lock_difficulty", 0) or 0))
            if tier == "vague":
                self.msg("It appears to be some sort of container.")
            elif tier == "basic":
                self.msg(f"It appears to be a container with a {lock_desc} lock.")
            else:
                self.msg(f"It appears to be a container with a {lock_desc} lock.")
                if getattr(target.db, "trap_present", False):
                    trap_desc = self.describe_lock_difficulty(int(getattr(target.db, "trap_difficulty", 0) or 0))
                    self.msg(f"You suspect signs of a {trap_desc} trap mechanism.")
                else:
                    self.msg("You notice no obvious sign of a trap.")

        if getattr(target.db, "item_type", None) == "weapon" or getattr(target.db, "weapon_type", None):
            self.describe_weapon(target, skill)

        if getattr(target.db, "item_type", None) == "armor" or getattr(target.db, "armor_type", None):
            self.describe_armor(target, skill)

        if hasattr(target, "set_hp") and getattr(target.db, "hp", None) is not None and target != self:
            self.msg("You size them up carefully.")
            if tier == "vague":
                self.msg("They seem dangerous.")
            elif tier in {"basic", "clear"}:
                self.msg("They appear to be a moderate threat.")
            else:
                self.msg("You gauge their strength with some confidence.")
        else:
            value = self.get_item_value(target)
            if tier == "vague":
                self.msg("It might be worth something.")
            elif tier == "basic":
                self.msg("It seems to have modest value.")
            elif tier == "clear":
                self.msg("It looks like it could sell for a fair amount.")
            else:
                self.msg(f"You judge it to be worth about {self.format_coins(value)}.")

        award_exp_skill(self, "appraisal", 10)
        self.set_roundtime(5)

    def compare_items(self, first_item, second_item):
        if self.is_in_roundtime():
            self.msg_roundtime_block()
            return

        self.msg(f"You compare {first_item.key} with {second_item.key}.")

        first_value = self.get_item_value(first_item)
        second_value = self.get_item_value(second_item)

        if first_value > second_value:
            self.msg(f"{first_item.key} appears more valuable.")
        elif second_value > first_value:
            self.msg(f"{second_item.key} appears more valuable.")
        else:
            self.msg("They seem roughly equal in value.")

        award_exp_skill(self, "appraisal", 10)
        self.set_roundtime(5)

    def is_vendor_target(self, obj):
        return bool(obj and getattr(obj.db, "is_vendor", False))

    def trading_contest(self, vendor):
        trading = self.get_skill("trading")
        scholarship = self.get_skill("scholarship")
        charisma = self.db.stats.get("charisma", 10)
        vendor_difficulty = getattr(vendor.db, "trade_difficulty", 20)
        return run_contest(trading + scholarship + charisma, vendor_difficulty, attacker=self)

    def haggle_with(self, vendor):
        if not self.is_vendor_target(vendor):
            self.msg("You can't haggle with that.")
            return

        self.msg(f"You attempt to negotiate with {vendor.key}.")
        if self.location:
            self.location.msg_contents(f"{self.key} quietly negotiates with {vendor.key}.", exclude=[self])

        result = self.trading_contest(vendor)
        outcome = result.get("outcome")

        if outcome == "fail":
            self.msg("You fail to improve the deal.")
            return

        if outcome == "partial":
            self.msg("You think you may have gained a slight edge.")
            self.set_state("haggle_bonus", 0.05)
            self.use_skill("trading", apply_roundtime=False, emit_placeholder=False, require_known=False)
            return

        if outcome in ("success", "strong"):
            self.msg("You negotiate a better deal.")
            self.set_state("haggle_bonus", 0.10 if outcome == "success" else 0.15)
            self.use_skill("trading", apply_roundtime=False, emit_placeholder=False, require_known=False)

    def get_vendor_type(self, vendor):
        vendor_type = str(getattr(getattr(vendor, "db", None), "vendor_type", "general") or "general").lower()
        return vendor_type if vendor_type in VENDOR_TYPES else "general"

    def vendor_accepts_item(self, vendor, item):
        from world.systems import fishing_economy

        vendor_type = self.get_vendor_type(vendor)
        is_gem = bool(getattr(getattr(item, "db", None), "is_gem", False))
        is_fish = bool(fishing_economy.is_fish_trade_item(item))
        if vendor_type == "general":
            accepted = not is_gem and not is_fish
        elif vendor_type == "gem_buyer":
            accepted = is_gem
        elif vendor_type == "fish_buyer":
            accepted = is_fish
        elif vendor_type == "pawn":
            accepted = True
        else:
            accepted = False
        if not accepted:
            return False

        accepted_item_types = list(getattr(getattr(vendor, "db", None), "accepted_item_types", []) or [])
        if accepted_item_types:
            item_type = str(getattr(getattr(item, "db", None), "item_type", "") or "").lower()
            if is_gem:
                item_type = "gem"
            return item_type in {str(entry).lower() for entry in accepted_item_types}
        return True

    def get_vendor_sale_multiplier(self, vendor, item):
        from world.systems import fishing_economy

        vendor_type = self.get_vendor_type(vendor)
        is_gem = bool(getattr(getattr(item, "db", None), "is_gem", False))
        is_fish = bool(fishing_economy.is_fish_trade_item(item))
        if vendor_type == "fish_buyer":
            return 1.0 if is_fish else None
        payout_profile = VENDOR_PAYOUTS.get(vendor_type, VENDOR_PAYOUTS["general"])
        return payout_profile["gems"] if is_gem else payout_profile["default"]

    def get_nearby_vendor(self, item=None):
        if not self.location:
            return None
        fallback = None
        for obj in self.location.contents:
            if self.is_vendor_target(obj):
                if item is not None and self.vendor_accepts_item(obj, item):
                    return obj
                if fallback is None:
                    fallback = obj
        return fallback

    def get_vendor_inventory_entries(self, vendor):
        inventory = getattr(getattr(vendor, "db", None), "inventory", []) or []
        return [str(entry).strip() for entry in inventory if str(entry or "").strip()]

    def get_vendor_price(self, vendor, item_name):
        normalized = str(item_name or "").strip().lower()
        custom_prices = getattr(getattr(vendor, "db", None), "price_map", None)
        if isinstance(custom_prices, Mapping) and normalized in custom_prices:
            try:
                return max(0, int(custom_prices.get(normalized, 0) or 0))
            except (TypeError, ValueError):
                return 0

        price_map = {
            "lockpick": 20,
            "trap kit": 20,
            "book": 20,
            "gem pouch": 25,
        }
        return max(1, int(price_map.get(normalized, 20)))

    def resolve_vendor_inventory_entry(self, vendor, item_name):
        entries = self.get_vendor_inventory_entries(vendor)
        base_query, index = self.split_numbered_query(item_name)
        normalized = base_query.strip().lower()
        if not normalized:
            return None, entries, base_query, index

        exact = [entry for entry in entries if entry.lower() == normalized]
        prefix = [entry for entry in entries if entry.lower().startswith(normalized)]
        contains = [entry for entry in entries if normalized in entry.lower()]
        matches = exact or prefix or contains
        if not matches:
            return None, matches, base_query, index

        if index is not None:
            if 1 <= index <= len(matches):
                return matches[index - 1], matches, base_query, index
            return None, matches, base_query, index

        if len(matches) == 1:
            return matches[0], matches, base_query, index

        return None, matches, base_query, index

    def msg_vendor_matches(self, query, matches):
        base_query = (query or "").strip()
        if not matches:
            return

        lines = [f"More than one item matches '{base_query}' (use '{base_query} <number>' to choose one):"]
        for index, match in enumerate(matches, start=1):
            lines.append(f" {index}. {match}")
        self.msg("\n".join(lines))

    def list_vendor_inventory(self):
        vendor = self.get_nearby_vendor()
        if not vendor:
            self.msg("There is no vendor here.")
            return False

        ok, trade_message = self.can_trade_with(vendor)
        if not ok:
            self.msg(trade_message)
            return False

        entries = self.get_vendor_inventory_entries(vendor)
        if not entries:
            self.msg(f"{vendor.key} has nothing for sale right now.")
            return False

        lines = []
        if hasattr(vendor, "get_vendor_interaction_lines"):
            lines.extend(list(vendor.get_vendor_interaction_lines(self, action="shop") or []))
        lines.append(f"{vendor.key} offers:")
        for entry in entries:
            price = self.get_vendor_price(vendor, entry)
            lines.append(f" {entry} - {self.format_coins(price)}")
        lines.append("Use 'buy <item>' to purchase something.")
        self.msg("\n".join(lines))
        try:
            from systems import first_area

            first_area.note_vendor_interaction(self, vendor=vendor, action="shop")
        except Exception:
            pass
        return True

    def sell_item(self, item_name):
        from world.systems import fishing_economy

        candidates = list(self.get_visible_carried_items())
        for carried in list(getattr(self, "contents", []) or []):
            if fishing_economy.is_fish_string(carried):
                candidates.extend([entry for entry in list(getattr(carried, "contents", []) or []) if fishing_economy.is_fish_trade_item(entry)])

        item, matches, base_query, index = self.resolve_numbered_candidate(
            item_name,
            candidates,
            default_first=True,
        )
        if not item:
            if matches and index is not None:
                self.msg_numbered_matches(base_query, matches)
            else:
                self.msg("You are not carrying that.")
            return False

        vendor = self.get_nearby_vendor(item=item)
        if not vendor:
            self.msg("There is no vendor here.")
            return False

        ok, trade_message = self.can_trade_with(vendor)
        if not ok:
            self.msg(trade_message)
            return False

        if self.get_vendor_type(vendor) == "fish_buyer":
            allowed, rate_limit_message = fishing_economy.can_use_fish_buyer(vendor, self)
            if not allowed:
                self.msg(rate_limit_message)
                return False

        multiplier = self.get_vendor_sale_multiplier(vendor, item)
        if multiplier is None:
            self.msg("They are not interested in that.")
            return False

        base_value = self.get_item_value(item)
        value = max(1, int(base_value * float(multiplier)))
        if fishing_economy.is_fish_trade_item(item) and self.get_vendor_type(vendor) == "fish_buyer":
            value = fishing_economy.get_fish_vendor_sale_value(item, vendor=vendor)
        self.add_coins(value)
        sale_message = None
        if hasattr(vendor, "get_vendor_sale_message"):
            sale_message = vendor.get_vendor_sale_message(self, item, value)
        self.msg(sale_message or f"The shopkeeper hands you {self.format_coins(value)}.")
        if self.location:
            self.location.msg_contents(f"{self.key} sells {item.key}.", exclude=[self])
        item.delete()
        self.use_skill("trading", apply_roundtime=False, emit_placeholder=False, require_known=False)
        try:
            from systems import onboarding

            completed, awarded = onboarding.note_trade_action(self, "sell")
            if completed and awarded:
                self.msg(onboarding.format_token_feedback(onboarding.ensure_onboarding_state(self)))
        except Exception:
            pass
        return True

    def sell_all_fish(self):
        from world.systems import fishing_economy

        vendor = self.get_nearby_vendor()
        if not vendor:
            self.msg("There is no vendor here.")
            return False

        ok, trade_message = self.can_trade_with(vendor)
        if not ok:
            self.msg(trade_message)
            return False
        if self.get_vendor_type(vendor) != "fish_buyer":
            self.msg("No one here is buying fish or salvage.")
            return False

        allowed, rate_limit_message = fishing_economy.can_use_fish_buyer(vendor, self)
        if not allowed:
            self.msg(rate_limit_message)
            return False

        fish_items = [item for item in list(self.get_visible_carried_items()) if fishing_economy.is_fish_trade_item(item)]
        for item in list(getattr(self, "contents", []) or []):
            if not fishing_economy.is_fish_string(item):
                continue
            fish_items.extend([entry for entry in list(getattr(item, "contents", []) or []) if fishing_economy.is_fish_trade_item(entry)])

        deduped = []
        seen_ids = set()
        for item in fish_items:
            item_id = int(getattr(item, "id", 0) or 0)
            if item_id and item_id in seen_ids:
                continue
            if item_id:
                seen_ids.add(item_id)
            deduped.append(item)
        fish_items = deduped

        if not fish_items:
            self.msg("You are not carrying any fishing finds to sell.")
            return False

        total = 0
        for fish in fish_items:
            value = fishing_economy.get_fish_vendor_sale_value(fish, vendor=vendor)
            total += value

        summary = fishing_economy.get_bulk_sale_summary(fish_items, total)

        for fish in fish_items:
            fish.delete()

        self.add_coins(total)
        if summary["only_fish"]:
            self.msg(f"You sell {summary['count']} fish for a total of {self.format_coins(summary['total_value'])}.")
        elif summary["mixed"]:
            self.msg(f"You sell {summary['count']} items (fish and salvage) for a total of {self.format_coins(summary['total_value'])}.")
        elif summary["only_salvage"]:
            salvage_label = "salvage item" if int(summary["count"] or 0) == 1 else "salvage items"
            self.msg(f"You sell {summary['count']} {salvage_label} for a total of {self.format_coins(summary['total_value'])}.")
        else:
            self.msg(f"You sell {summary['count']} items for a total of {self.format_coins(summary['total_value'])}.")
        if self.location:
            self.location.msg_contents(f"{self.key} sells a bundled catch to {vendor.key}.", exclude=[self])
        self.use_skill("trading", apply_roundtime=False, emit_placeholder=False, require_known=False)
        return True

    def sell_all_items(self):
        from world.systems import fishing_economy

        vendor = self.get_nearby_vendor()
        if not vendor:
            self.msg("There is no vendor here.")
            return False

        ok, trade_message = self.can_trade_with(vendor)
        if not ok:
            self.msg(trade_message)
            return False

        if self.get_vendor_type(vendor) == "fish_buyer":
            return self.sell_all_fish()

        total = 0
        sold_any = False
        for item in list(self.get_visible_carried_items()):
            if fishing_economy.is_fish_trade_item(item):
                continue
            if not self.vendor_accepts_item(vendor, item):
                continue
            multiplier = self.get_vendor_sale_multiplier(vendor, item)
            if multiplier is None:
                continue
            base_value = self.get_item_value(item)
            value = max(1, int(base_value * float(multiplier)))
            total += value
            sold_any = True
            item.delete()

        if not sold_any:
            self.msg("They are not interested in anything you are carrying.")
            return False

        self.add_coins(total)
        self.msg(f"You sell several items for a total of {self.format_coins(total)}.")
        if self.location:
            self.location.msg_contents(f"{self.key} sells several items.", exclude=[self])
        self.use_skill("trading", apply_roundtime=False, emit_placeholder=False, require_known=False)
        try:
            from systems import onboarding

            completed, awarded = onboarding.note_trade_action(self, "sell")
            if completed and awarded:
                self.msg(onboarding.format_token_feedback(onboarding.ensure_onboarding_state(self)))
        except Exception:
            pass
        return True

    def weigh_fish(self, item_name):
        from world.systems import fishing_economy

        station = fishing_economy.get_nearby_weigh_station(self)
        if not station:
            self.msg("There is no weigh station here.")
            return False

        candidates = list(self.get_visible_carried_items())
        for item in list(getattr(self, "contents", []) or []):
            if fishing_economy.is_fish_string(item):
                candidates.extend(list(getattr(item, "contents", []) or []))

        fish, matches, base_query, index = self.resolve_numbered_candidate(item_name, candidates, default_first=True)
        if not fish or not fishing_economy.is_fish_item(fish):
            if matches and index is not None:
                self.msg_numbered_matches(base_query, matches)
            else:
                self.msg("You do not have that fish.")
            return False

        self.msg(fishing_economy.format_fish_inspection(fish))
        return True

    def recall_knowledge(self, topic):
        scholarship = self.get_skill("scholarship")

        self.msg(f"You try to recall what you know about {topic}.")
        if scholarship < 5:
            self.msg("You struggle to recall anything useful.")
        elif scholarship < 15:
            self.msg("You vaguely recall something about it.")
        elif scholarship < 30:
            self.msg("You recall some useful details.")
        else:
            self.msg("You recall detailed and useful knowledge.")

        self.award_skill_experience("scholarship", max(10, scholarship), success=True, outcome="success", event_key="scholarship_recall", context_multiplier=0.5)

    def study_item(self, item):
        if not getattr(item.db, "is_study_item", False):
            self.msg("You can't study that.")
            return False

        study_uses = int(getattr(item.db, "study_uses", 0) or 0)
        if study_uses > 10:
            self.msg("You feel you have learned all you can from this.")
            return False

        skill_name = getattr(item.db, "skill", "scholarship") or "scholarship"
        difficulty = int(getattr(item.db, "difficulty", 10) or 10)
        skill = self.get_skill(skill_name)

        self.msg(f"You begin studying {item.key}.")
        if skill < difficulty:
            self.msg("You struggle to make sense of the material.")
            return False

        item.db.study_uses = study_uses + 1
        self.msg("You gain some insight from your study.")
        normalized_skill = str(skill_name or "scholarship").strip().lower().replace("-", "_").replace(" ", "_")
        anatomy_study = self._is_anatomy_study_item(item)
        if anatomy_study:
            self.award_skill_experience("scholarship", difficulty, success=True, outcome="success", event_key="study_anatomy", context_multiplier=1.0)
            self.award_skill_experience("first_aid", max(8, difficulty - 2), success=True, outcome="success", event_key="study_anatomy", context_multiplier=0.55)
            self.award_skill_experience("empathy", max(6, difficulty - 4), success=True, outcome="success", event_key="empathy_study", context_multiplier=0.12)
        elif normalized_skill in {"scholarship", "first_aid"}:
            self.award_skill_experience(normalized_skill, difficulty, success=True, outcome="success", event_key="study", context_multiplier=1.0)
        else:
            self.use_skill(normalized_skill, apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=difficulty)
        return True

    def create_vendor_inventory_item(self, item_name):
        normalized = str(item_name or "").strip().lower()
        if normalized == "basic cloak":
            item = create_object("typeclasses.wearables.Wearable", key="basic cloak", location=self, home=self)
            item.db.slot = "torso"
            item.db.item_type = "armor"
            item.db.armor_type = "light_armor"
            item.db.protection = 1
            item.db.hindrance = 0
            item.db.weight = 1.5
            item.db.item_value = 8
            item.db.value = 8
            item.db.desc = "A plain weather cloak cut for hard use rather than style."
            item.aliases.add("cloak")
            return item
        if normalized == "lightweight ranger cloak":
            item = create_object("typeclasses.wearables.Wearable", key="lightweight ranger cloak", location=self, home=self)
            item.db.slot = "torso"
            item.db.item_type = "armor"
            item.db.armor_type = "light_armor"
            item.db.protection = 2
            item.db.hindrance = 0
            item.db.weight = 1.0
            item.db.item_value = 16
            item.db.value = 16
            item.db.desc = "A lighter cloak stitched to move quietly through brush and branches."
            item.aliases.add("cloak")
            item.aliases.add("ranger cloak")
            return item
        if normalized == "simple boots":
            item = create_object("typeclasses.wearables.Wearable", key="simple boots", location=self, home=self)
            item.db.slot = "feet"
            item.db.weight = 1.0
            item.db.item_value = 6
            item.db.value = 6
            item.db.desc = "A cheap pair of boots meant to survive mud and trail dust."
            item.aliases.add("boots")
            return item
        if normalized == "balanced climbing gloves":
            item = create_object("typeclasses.wearables.Wearable", key="balanced climbing gloves", location=self, home=self)
            item.db.slot = "hands"
            item.db.weight = 0.4
            item.db.item_value = 18
            item.db.value = 18
            item.db.desc = "Supple gloves reinforced across the palm where rope and bark bite hardest."
            item.aliases.add("gloves")
            item.aliases.add("climbing gloves")
            return item
        if normalized == "starter pack":
            item = create_simple_item(
                self,
                key="starter pack",
                desc="A simple field pack with enough room for a beginner's tools and gathered goods.",
                item_value=9,
                value=9,
                weight=1.2,
                item_type="container",
            )
            item.aliases.add("pack")
            return item
        if normalized == "rope":
            return create_simple_item(
                self,
                key="rope",
                desc="A coil of plain rope with enough life left in it to stay useful.",
                item_value=5,
                value=5,
                weight=1.5,
                item_type="tool",
            )
        if normalized == "reinforced rope":
            item = create_simple_item(
                self,
                key="reinforced rope",
                desc="A better rope wrapped and stitched for repeated hard climbs.",
                item_value=14,
                value=14,
                weight=1.4,
                item_type="tool",
            )
            item.aliases.add("rope")
            return item
        if normalized == "basic knife":
            item = create_object("typeclasses.objects.Object", key="basic knife", location=self, home=self)
            item.db.item_type = "weapon"
            item.db.weapon_type = "light_edge"
            item.db.skill = "light_edge"
            item.db.damage_type = "slice"
            item.db.damage_types = {"slice": 1.0, "impact": 0.0, "puncture": 0.0}
            item.db.damage_min = 1
            item.db.damage_max = 3
            item.db.roundtime = 2.5
            item.db.weight = 0.5
            item.db.item_value = 6
            item.db.value = 6
            item.db.desc = "A serviceable utility knife that can still pull field duty."
            item.aliases.add("knife")
            return item
        if normalized == "fine skinning knife":
            item = create_object("typeclasses.objects.Object", key="fine skinning knife", location=self, home=self)
            item.db.item_type = "weapon"
            item.db.weapon_type = "light_edge"
            item.db.skill = "light_edge"
            item.db.damage_type = "slice"
            item.db.damage_types = {"slice": 1.0, "impact": 0.0, "puncture": 0.0}
            item.db.damage_min = 1
            item.db.damage_max = 4
            item.db.roundtime = 2.0
            item.db.weight = 0.4
            item.db.item_value = 18
            item.db.value = 18
            item.db.desc = "A finely balanced knife made to separate hide from flesh with less waste."
            item.aliases.add("knife")
            item.aliases.add("skinning knife")
            return item
        if normalized == "lockpick":
            item = create_object(Lockpick, key="basic lockpick", location=self, home=self)
            item.db.item_value = 10
            item.db.value = 10
            item.db.weight = 0.2
            return item
        if normalized == "book":
            item = create_object(StudyItem, key="study book", location=self, home=self)
            item.db.skill = "scholarship"
            item.db.difficulty = 10
            item.db.item_value = 10
            item.db.value = 10
            item.db.weight = 1.0
            item.db.desc = "A compact study text full of practical notes and marginalia."
            return item
        if normalized == "gem pouch":
            item = create_object("typeclasses.items.gem_pouch.GemPouch", key="gem pouch", location=self, home=self)
            return item
        if normalized == "trail bread":
            item = create_simple_item(
                self,
                key="trail bread",
                desc="A dense heel of bread wrapped in paper, simple enough to be given away without ceremony.",
                item_value=1,
                value=1,
                weight=0.2,
            )
            return item

        item = create_simple_item(
            self,
            key=normalized,
            desc=f"A {normalized} purchased from a local merchant.",
            item_value=10,
            value=10,
            weight=1.0,
        )
        return item

    def buy_item(self, item_name):
        vendor = self.get_nearby_vendor()
        if not vendor:
            self.msg("There is no vendor here.")
            return False

        ok, trade_message = self.can_trade_with(vendor)
        if not ok:
            self.msg(trade_message)
            return False

        stock_name, matches, base_query, index = self.resolve_vendor_inventory_entry(vendor, item_name)
        if not stock_name:
            if matches:
                self.msg_vendor_matches(base_query, matches)
            else:
                self.msg("They don't sell that. Try 'shop' to see what is available.")
            return False
        normalized = stock_name.lower()

        price = self.get_vendor_price(vendor, normalized)

        if not self.has_coins(price):
            self.msg("You can't afford that.")
            return False

        self.remove_coins(price)
        self.create_vendor_inventory_item(normalized)
        purchase_message = None
        if hasattr(vendor, "get_vendor_purchase_message"):
            purchase_message = vendor.get_vendor_purchase_message(self, stock_name, price)
        self.msg(purchase_message or f"You purchase {stock_name} for {self.format_coins(price)}.")
        self.use_skill("trading", apply_roundtime=False, emit_placeholder=False, require_known=False)
        try:
            from systems import onboarding

            completed, awarded = onboarding.note_trade_action(self, "buy")
            if completed and awarded:
                self.msg(onboarding.format_token_feedback(onboarding.ensure_onboarding_state(self)))
        except Exception:
            pass
        try:
            from systems import first_area

            first_area.note_vendor_interaction(self, vendor=vendor, action="buy")
        except Exception:
            pass
        return True

    def charge_luminar(self, args):
        amount_text = str(args or "").strip()
        try:
            requested = int(amount_text) if amount_text else 10
        except ValueError:
            self.msg("Charge it with how much attunement?")
            return False

        if requested <= 0:
            self.msg("You must channel a positive amount of attunement.")
            return False

        luminar = None
        for obj in self.contents:
            if getattr(obj.db, "is_luminar", False):
                luminar = obj
                break

        if not luminar:
            self.msg("You have no luminar.")
            return False

        capacity = int(getattr(luminar.db, "capacity", 0) or 0)
        charge = int(getattr(luminar.db, "charge", 0) or 0)
        safe_limit = self.get_luminar_safe_charge(luminar)
        max_charge = max(safe_limit + max(5, capacity // 2), capacity)
        remaining = max(0, max_charge - charge)
        if remaining <= 0:
            self.msg(f"{luminar.key} is already fully charged.")
            return False

        amount = min(requested, remaining)
        if not self.spend_attunement(amount):
            self.msg("You lack the focus to charge it.")
            return False

        luminar.db.charge = charge + amount
        if luminar.db.charge > safe_limit and random.random() < 0.3:
            self.msg("The luminar destabilizes violently!")
            luminar.db.charge = 0
            return False

        self.msg(f"You channel Radiance into {luminar.key} ({luminar.db.charge}/{capacity}).")
        self.use_skill("arcana", apply_roundtime=False, emit_placeholder=False, require_known=False)
        return True

    def invoke_luminar(self, requested=None):
        for obj in self.contents:
            if getattr(obj.db, "is_luminar", False) and int(getattr(obj.db, "charge", 0) or 0) > 0:
                available = int(obj.db.charge or 0)
                amount = available if requested is None else min(available, max(0, int(requested)))
                obj.db.charge = max(0, available - amount)

                arcana = self.get_skill("arcana")
                efficiency = 0.5 + (arcana / 200.0)
                return int(amount * efficiency)
        return 0

    def prepare_spell(self, args):
        parts = [part for part in str(args or "").split() if part]
        if not parts:
            self.msg("Prepare what?")
            return False

        spell_name = parts[0].lower()
        ok, msg = self.can_access_spell(spell_name)
        if not ok:
            self.msg(msg)
            return False

        try:
            mana = int(parts[1]) if len(parts) > 1 else 10
        except ValueError:
            self.msg("You must specify a whole number of attunement to prepare.")
            return False

        spell_def = self.get_spell_def(spell_name)
        if not spell_def:
            self.msg("You do not know how to prepare that spell.")
            return False

        if mana <= 0:
            self.msg("You must prepare at least some Radiance.")
            return False

        mana_min = int(spell_def.get("mana_min", 1) or 1)
        mana_max = int(spell_def.get("mana_max", mana_min) or mana_min)
        if mana < mana_min or mana > mana_max:
            self.msg(f"You can only prepare between {mana_min} and {mana_max} Radiance for that spell.")
            return False

        if not self.spend_attunement(mana):
            self.msg("You cannot gather enough Radiance.")
            return False

        stability = self.calculate_preparation_stability(mana, spell_def["category"])
        self.set_state(
            "prepared_spell",
            {
                "name": spell_name,
                "mana": mana,
                "category": spell_def["category"],
                "stability": stability,
                "target_mode": spell_def.get("target_mode", "self"),
            },
        )
        self.msg(f"You begin preparing {spell_name}.")
        self.use_skill("attunement", apply_roundtime=False, emit_placeholder=False, require_known=False)
        if self.is_profession("cleric"):
            self.use_skill("theurgy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=self.get_theurgy_training_difficulty(max(8, mana)))
        return True

    def cast_spell(self, target_name=None):
        data = self.get_state("prepared_spell")
        if not data:
            self.msg("You have no spell prepared.")
            return False

        spell_name = str(data.get("name") or "spell")
        if self.get_state(f"cooldown_{spell_name}"):
            self.msg("You are not ready to cast that again yet.")
            return False

        spell_metadata = self.get_spell_metadata(spell_name) or {}
        category = data.get("category") or spell_metadata.get("category", "targeted_magic")
        target_mode = spell_metadata.get("target_mode", data.get("target_mode", "self"))
        mana = int(data.get("mana", 0) or 0)
        luminar_bonus = self.invoke_luminar()
        if luminar_bonus > 0:
            self.msg("Your luminar flares as it feeds power into the spell.")
            if self.location:
                self.location.msg_contents(f"{self.key}'s luminar flares brightly.", exclude=[self])

        target = self.resolve_cast_target(target_name, spell_metadata)
        if target_mode == "single" and not target:
            self.msg("You must specify a target.")
            return False

        total_mana = mana + luminar_bonus
        backlash = self.resolve_spell_backlash(total_mana, category)
        if backlash == "fizzle":
            self.msg("The spell slips from your control and dissipates.")
            self.clear_state("prepared_spell")
            return False

        if backlash == "backlash":
            self.msg("The spell recoils painfully through you!")
            self.set_hp((self.db.hp or 0) - max(1, int(total_mana / 4)))
            self.clear_state("prepared_spell")
            return False

        wild_modifier = 0.75 if backlash == "wild" else 1.0
        if backlash == "wild":
            self.msg("The spell surges out in an unstable burst!")

        quality = self.resolve_cast_quality(data.get("stability", 1.0))
        total_power = self.get_spell_power(category, total_mana)

        if spell_metadata.get("cyclic"):
            if not self.start_cyclic_spell(spell_name, total_power):
                return False
            self.set_spell_cooldown(spell_name, max(2, int(total_power / 10)))
            self.msg(f"You sustain {spell_name}.")
            if category == "targeted_magic":
                award_exp_skill(self, "targeted_magic", max(10, int(total_power)), success=True)
            else:
                self.use_skill(category, apply_roundtime=False, emit_placeholder=False, require_known=False)
            self.clear_state("prepared_spell")
            return True

        self.msg(f"You release {spell_name}.")
        if target_mode == "single" and target is not None:
            with direct_interest(self, [target], channel="spell"):
                resolved = self.resolve_spell(
                    spell_name,
                    total_power,
                    spell_def=spell_metadata,
                    quality=quality,
                    target=target,
                    wild_modifier=wild_modifier,
                )
        else:
            resolved = self.resolve_spell(
                spell_name,
                total_power,
                spell_def=spell_metadata,
                quality=quality,
                target=target,
                wild_modifier=wild_modifier,
            )
        if not resolved:
            return False

        self.set_spell_cooldown(spell_name, max(2, int(total_power / 10)))
        if category != "targeted_magic":
            self.use_skill(
                category,
                apply_roundtime=False,
                emit_placeholder=False,
                require_known=False,
            )
        self.clear_state("prepared_spell")
        return True

    def resolve_spell(self, name, power, spell_def=None, quality="normal", target=None, wild_modifier=1.0):
        spell_name = str(name or "spell").lower()
        spell_def = spell_def or self.get_spell_def(spell_name) or {}
        category = spell_def.get("category", "utility")

        if spell_name == "cleanse":
            return self.resolve_cleanse_spell(power, quality)

        if category == "targeted_magic" and spell_def.get("target_mode") == "room":
            return self.resolve_room_targeted_spell(spell_name, power, spell_def, quality, wild_modifier=wild_modifier)
        if category == "targeted_magic":
            return self.resolve_targeted_spell(spell_name, power, target, spell_def, quality, wild_modifier=wild_modifier)
        if category == "augmentation":
            return self.resolve_augmentation_spell(spell_name, power, spell_def, quality)
        if category == "debilitation":
            return self.resolve_debilitation_spell(spell_name, power, target, spell_def, quality, wild_modifier=wild_modifier)
        if category == "warding" and spell_def.get("target_mode") == "group":
            return self.resolve_group_warding_spell(spell_name, power, spell_def, quality)
        if category == "warding":
            return self.resolve_warding_spell(spell_name, power, spell_def, quality)
        if category == "utility":
            return self.resolve_utility_spell(spell_name, power, spell_def, quality)

        self.msg(f"{spell_name} takes effect.")
        return True

    def check_room_traps_for_enemy(self, attacker):
        if not self.location or not attacker:
            return False

        triggered = False
        for obj in list(self.location.contents):
            if not getattr(obj.db, "is_trap_device", False):
                continue
            if obj.db.owner != self:
                continue
            if hasattr(obj, "check_trigger") and obj.check_trigger(attacker):
                triggered = True
        return triggered

    def pick_box(self, box, pick=None):
        if pick is None:
            pick = self.get_active_lockpick()

        if not pick:
            self.msg("You need a lockpick.")
            return

        if not box.db.locked:
            self.msg("It is already unlocked.")
            return

        self.msg(f"You begin working on the lock with a {pick.db.grade} pick...")
        msg_room(self, f"{self.key} works carefully on a box lock.", exclude=[self])

        quality_bonus = float(pick.get_quality() if hasattr(pick, "get_quality") else getattr(pick.db, "quality", 0))
        skill_total = self.get_skill("locksmithing") + self.db.stats.get("intelligence", 10) + quality_bonus
        result = run_contest(skill_total, box.db.lock_difficulty, attacker=self)

        difficulty = box.db.lock_difficulty
        skill = self.get_skill("locksmithing")
        quality = max(0.1, quality_bonus)
        break_chance = max(0.02, (difficulty - skill) / 100)
        break_chance /= quality

        if random.random() < break_chance:
            self.msg("Your lockpick snaps!")
            if pick and pick.pk:
                pick.delete()
            return

        if pick:
            wear = max(1, int(box.db.lock_difficulty / 10))
            pick.db.durability = int((pick.db.durability or 0) - wear)
            if pick.db.durability <= 2 and pick.db.durability > 0:
                self.msg("Your lockpick is on the verge of breaking.")
            if pick.db.durability <= 0:
                self.msg("Your lockpick snaps!")
                pick.delete()
                return

        outcome = result["outcome"]
        if outcome == "fail":
            self.msg("You fail to make progress.")
            return

        if outcome == "partial":
            self.msg("You make a little progress, but the lock still resists you.")
            award_exp_skill(
                self,
                "locksmithing",
                max(10, int(box.db.lock_difficulty or 0)),
                success=False,
                outcome="partial",
                event_key="locksmithing",
            )
            return

        if outcome in ("success", "strong"):
            box.db.locked = False
            self.msg("You successfully pick the lock.")
            award_exp_skill(
                self,
                "locksmithing",
                max(10, int(box.db.lock_difficulty or 0)),
                success=True,
                outcome=outcome,
                event_key="locksmithing",
            )

    def unlock_box(self, box):
        if not self.is_box_target(box):
            self.msg("You can't unlock that.")
            return False

        if not bool(getattr(box.db, "strict_loot_box", False)):
            self.msg("You will need to pick that lock the old-fashioned way.")
            return False

        if bool(getattr(box.db, "is_open", getattr(box.db, "opened", False))):
            self.msg("The box is empty.")
            return False

        if not bool(getattr(box.db, "is_locked", getattr(box.db, "locked", True))):
            self.msg("It is already unlocked.")
            return False

        if random.random() < 0.7:
            box.db.locked = False
            box.db.is_locked = False
            self.msg("You unlock the box.")
            return True

        self.msg("You fail to unlock the box.")
        return False

    def generate_box_loot(self, box):
        if not self.location:
            return None

        difficulty = int(box.db.lock_difficulty or 0) + int(box.db.trap_difficulty or 0)
        if difficulty < 20:
            item = "small coin pile"
            desc = "A modest spill of coins from an easy box."
        elif difficulty < 40:
            item = "gem pouch"
            desc = "A small pouch filled with a few marketable stones."
        else:
            item = "valuable treasure"
            desc = "A compact haul of valuables from a difficult box."

        if random.random() < 0.2:
            item = "rare gem"
            desc = "A rare gem flashes as it tumbles free of the box."

        loot = create_simple_item(
            self.location,
            key=item,
            desc=desc,
            box_loot=True,
            loot_difficulty=difficulty,
        )
        self.location.msg_contents("Something falls out of the box.", exclude=[self])
        return loot

    def open_box(self, box):
        if bool(getattr(box.db, "strict_loot_box", False)):
            if bool(getattr(box.db, "is_open", getattr(box.db, "opened", False))):
                self.msg("The box is empty.")
                return

            if bool(getattr(box.db, "is_locked", getattr(box.db, "locked", True))):
                self.msg("The box is locked.")
                return

            box.db.opened = True
            box.db.is_open = True
            total_coins = 0
            item_names = []
            for entry in list(getattr(box.db, "contents", None) or []):
                kind = str(entry.get("kind", "") or "").lower()
                if kind == "coins":
                    total_coins += max(0, int(entry.get("amount", 0) or 0))
                elif kind == "gem":
                    gem = create_gem(self, gem_data=dict(entry.get("data") or {}))
                    self.store_loot_item(gem)
                    item_names.append(gem.key)
            box.db.contents = []

            if total_coins > 0:
                self.add_coins(total_coins)

            self.msg("You open the box.")
            if total_coins > 0:
                self.msg(f"You collect {self.format_coins(total_coins)}.")
            if item_names:
                self.msg(f"You find {', '.join(item_names)}.")
            if total_coins <= 0 and not item_names:
                self.msg("The box is empty.")
            return

        if box.db.opened:
            self.msg("It is already open.")
            return

        if box.db.locked:
            self.msg("The box is still locked.")
            return

        if hasattr(box, "has_active_trap") and box.has_active_trap():
            self.msg("You hesitate, sensing danger.")
            return

        box.db.opened = True
        self.msg("You open the box.")
        msg_room(self, f"{self.key} opens a box.", exclude=[self])
        self.generate_box_loot(box)

    def get_arm_penalty(self):
        right_arm = (self.get_body_part("right_arm") or {}).get("external", 0)
        left_arm = (self.get_body_part("left_arm") or {}).get("external", 0)
        return min(25, int(math.sqrt(max(right_arm, left_arm))))

    def get_leg_penalty(self):
        left_leg = (self.get_body_part("left_leg") or {}).get("external", 0)
        right_leg = (self.get_body_part("right_leg") or {}).get("external", 0)
        return min(25, int(math.sqrt(max(left_leg, right_leg))))

    def get_hand_penalty(self):
        left_hand = (self.get_body_part("left_hand") or {}).get("external", 0)
        right_hand = (self.get_body_part("right_hand") or {}).get("external", 0)
        return min(25, int(math.sqrt(max(left_hand, right_hand))))

    def get_coverage_weight(self, coverage):
        normalized = self.normalize_body_part_name(coverage)
        return ARMOR_COVERAGE_WEIGHTS.get(normalized, 1)

    def is_hidden(self):
        from world.systems.stealth import sync_stealth_cache

        return sync_stealth_cache(self)

    def is_sneaking(self):
        return bool(self.get_state("sneaking"))

    def is_stalking(self):
        return self.has_state("stalking")

    def get_stalk_target_id(self):
        return self.get_state("stalking")

    def is_ambushing(self):
        return self.has_state("ambush_target")

    def get_ambush_target_id(self):
        return self.get_state("ambush_target")

    def is_surprised(self):
        return self.get_state("surprised") is True

    def apply_surprise(self):
        self.set_state("surprised", True)

    def clear_surprise(self):
        self.clear_state("surprised")

    def is_staggered(self):
        return bool(getattr(self.db, "staggered", False))

    def clear_stagger(self):
        self.db.staggered = False
        self.db.stagger_timer = 0

    def has_reaction_delay(self):
        return self.is_surprised()

    def break_stealth(self):
        self.db.stealthed = False
        self.db.stealth_value = 0
        self.clear_state("hidden")
        self.clear_state("sneaking")
        self.clear_state("stalking")
        self.clear_state("ambush_target")
        if getattr(self.db, "position_state", "neutral") == "advantaged":
            self.db.position_state = "neutral"

    def reveal(self):
        self.break_stealth()

    def get_marked_target(self):
        target_id = getattr(self.db, "marked_target", None)
        if not target_id:
            return None
        mark_data = dict(getattr(self.db, "mark_data", None) or {})
        if time.time() - float(mark_data.get("timestamp", 0) or 0) > 60:
            self.db.marked_target = None
            self.db.mark_data = {}
            return None
        result = search_object(f"#{target_id}")
        return result[0] if result else None

    def has_recent_action_risk(self):
        return bool(getattr(self.db, "recent_action", False))

    def set_attention_state(self, state):
        self.db.attention_state = state
        self.db.attention_changed_at = time.time()

    def set_position_state(self, state):
        self.db.position_state = state
        self.db.position_changed_at = time.time()

    def clear_disguise(self):
        self.db.disguised = False
        self.db.disguise_name = None
        self.db.disguise_profession = None

    def reset_thief_pressure_states(self):
        self.db.slipping = False
        self.db.slip_bonus = 0
        self.db.escape_chain = 0
        self.db.in_passage = False
        self.db.post_ambush_grace = False
        self.db.post_ambush_grace_until = 0

    def can_detect(self, target):
        return self.can_perceive(target)

    def can_perceive(self, target):
        from world.systems.stealth import can_detect

        return can_detect(self, target)

    def skin_target(self, target):
        from world.systems import fishing_economy

        if not target:
            self.msg("You can't skin that.")
            return False

        if fishing_economy.is_fish_item(target):
            return self.skin_fish_target(target)

        if bool(getattr(target.db, "skinned", False)):
            self.msg("There is nothing left worth taking from that.")
            return False

        if hasattr(target, "is_dead"):
            is_dead_target = bool(target.is_dead())
        elif hasattr(target, "is_alive"):
            is_dead_target = not bool(target.is_alive())
        else:
            is_dead_target = bool(getattr(target.db, "dead", False) or getattr(target.db, "is_corpse", False))

        if not is_dead_target or not bool(getattr(target.db, "skinnable", False)):
            self.msg("You can't skin that.")
            return False

        if not self.is_wielding("skinning knife"):
            self.msg("You need a skinning knife to properly skin that.")
            return False

        msg_room(self, f"{self.key} kneels over {target.key}, working carefully.", exclude=[self])

        skill_total = self.get_skill("skinning") + self.get_stat("agility") + self.get_stat("discipline")
        difficulty = int(getattr(target.db, "skin_difficulty", 35) or 35)
        result = run_contest(skill_total, difficulty, attacker=self)
        outcome = result["outcome"]

        if outcome == "fail":
            self.msg("You ruin the remains and recover nothing useful.")
            target.db.skinned = True
        else:
            if outcome == "partial":
                self.msg("You recover a few usable parts.")
                quality = "poor"
            elif outcome == "success":
                self.msg("You skillfully harvest useful materials.")
                quality = "normal"
            else:
                self.msg("You skillfully harvest exceptional materials.")
                quality = "fine"

            quality_values = {
                "poor": 2,
                "normal": 5,
                "fine": 9,
            }

            create_harvest_bundle(
                self,
                key=f"{quality} hide bundle",
                desc=f"A {quality} bundle of materials harvested from {target.key}.",
                harvested_from=target.key,
                skinning_quality=quality,
                item_type="hide",
                item_value=quality_values.get(quality, 2),
                value=quality_values.get(quality, 2),
            )
            target.db.skinned = True

        self.use_skill(
            "skinning",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=difficulty,
        )
        return True

    def skin_fish_target(self, target):
        from world.systems import fishing_economy

        if not target or not fishing_economy.is_fish_item(target):
            self.msg("You can't skin that.")
            return False
        if getattr(target, "location", None) not in {self, getattr(self, "location", None)}:
            self.msg("You need the fish in front of you before you can clean it.")
            return False
        if not self.is_wielding("skinning knife"):
            self.msg("You need a skinning knife to properly clean that fish.")
            return False

        profile = fishing_economy.get_fish_processing_profile(target)
        skill_total = self.get_skill("skinning") + self.get_stat("agility") + self.get_stat("discipline")
        difficulty = int(profile.get("difficulty", 12) or 12)
        result = run_contest(skill_total, difficulty, attacker=self)
        outcome = str(result.get("outcome", "failure") or "failure")
        species = str(profile.get("species", getattr(target, "key", "fish")) or getattr(target, "key", "fish"))

        meat_yield = int(profile.get("meat_yield", 1) or 1)
        skin_yield = int(profile.get("skin_yield", 1) or 1)
        if outcome == "fail":
            meat_yield = max(0, meat_yield - 1)
            skin_yield = 0
            self.msg(f"You make a mess of {species} and salvage very little.")
        elif outcome == "partial":
            skin_yield = max(0, skin_yield - 1)
            self.msg(f"You clean {species} well enough to save a few usable cuts.")
        elif outcome == "success":
            self.msg(f"You clean {species} with practiced strokes, saving meat and skin.")
        else:
            meat_yield += 1
            skin_yield += 1
            self.msg(f"You clean {species} flawlessly, wasting almost nothing.")

        created = []
        if meat_yield > 0:
            meat = create_object("typeclasses.items.fish_material.FishMaterial", key=f"{species} fillet", location=self, home=self)
            meat.db.item_type = "fish_meat"
            meat.db.quantity = meat_yield
            meat.db.processed_from = species
            meat.db.value = max(1, int(profile.get("meat_value", 2) or 2))
            meat.db.item_value = meat.db.value
            meat.db.desc = f"Clean fillets trimmed from {species}, ready for cooking or sale."
            created.append(meat)
        if skin_yield > 0:
            skin = create_object("typeclasses.items.fish_material.FishMaterial", key=f"{species} skin", location=self, home=self)
            skin.db.item_type = "fish_skin"
            skin.db.quantity = skin_yield
            skin.db.processed_from = species
            skin.db.value = max(1, int(profile.get("skin_value", 1) or 1))
            skin.db.item_value = skin.db.value
            skin.db.desc = f"A cleaned strip of {species} skin, kept intact for tanning or trade."
            created.append(skin)

        if created:
            created_names = ", ".join(str(getattr(obj, "key", "material") or "material") for obj in created)
            self.msg(f"You finish with {created_names}.")
        else:
            self.msg("Nothing worth selling survives your work.")
        if self.location:
            msg_room(self, f"{self.key} cleans {species} with quick, careful motions.", exclude=[self])
        target.delete()
        self.use_skill(
            "skinning",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=difficulty,
        )
        return True

    def _resolve_terrain_target(self, raw_target, attr_name):
        target_name = (raw_target or "").strip()
        if target_name:
            target = self.search(target_name)
            if not target:
                return None
            if bool(getattr(target.db, attr_name, False)):
                return target
            return False

        if self.location and bool(getattr(self.location.db, attr_name, False)):
            return self.location
        return None

    def _get_climb_exit_names(self, exit_obj):
        names = set()
        key = str(getattr(exit_obj, "key", "") or "").strip().lower()
        if key:
            names.add(key)

        aliases = getattr(getattr(exit_obj, "aliases", None), "all", lambda: [])()
        for alias in aliases:
            alias_text = str(alias or "").strip().lower()
            if alias_text:
                names.add(alias_text)

        action_command = str(getattr(exit_obj.db, "climb_action_command", "") or "").strip().lower()
        if action_command:
            names.add(action_command)
            if action_command.startswith("climb "):
                suffix = action_command.split(" ", 1)[1].strip()
                if suffix:
                    names.add(suffix)

        return names

    def _resolve_climb_exit(self, raw_target=""):
        room = getattr(self, "location", None)
        if not room:
            return None

        exits = [
            exit_obj
            for exit_obj in (room.contents_get(content_type="exit") or [])
            if bool(getattr(exit_obj.db, "climb_contest", False))
        ]
        if not exits:
            return None

        target_name = str(raw_target or "").strip().lower()
        if target_name:
            for exit_obj in exits:
                if target_name in self._get_climb_exit_names(exit_obj):
                    return exit_obj
            return None

        for exit_obj in exits:
            if bool(getattr(exit_obj.db, "climb_default_action", False)):
                return exit_obj
        return exits[0] if len(exits) == 1 else None

    def _resolve_room_reference(self, value):
        if not value:
            return None
        if hasattr(value, "id"):
            return value

        text = str(value or "").strip()
        if not text:
            return None
        matches = search_object(text if text.startswith("#") else text)
        return matches[0] if matches else None

    def _get_climb_practice_key(self, exit_obj):
        object_id = getattr(exit_obj, "id", None)
        if object_id is not None:
            return f"exit:{int(object_id)}"
        return f"exit:{str(getattr(exit_obj, 'key', 'climb') or 'climb').strip().lower()}"

    def _get_climb_practice_bonus(self, exit_obj):
        practice = getattr(getattr(self, "ndb", None), "climb_practice", None) or {}
        return int(practice.get(self._get_climb_practice_key(exit_obj), 0) or 0)

    def _get_climb_tier(self, exit_obj):
        tier = str(getattr(exit_obj.db, "climb_tier", "low") or "low").strip().lower()
        return tier if tier in CLIMB_OUTCOME_MESSAGES else "low"

    def _get_climb_skill_total(self, exit_obj):
        athletics = int(self.get_skill("athletics") or 0)
        agility = int(self.get_stat("agility") or 0)
        strength = int(self.get_stat("strength") or 0)
        practice_bonus = self._get_climb_practice_bonus(exit_obj)
        stat_bonus = max(0, (agility + strength) // 10)
        return athletics + stat_bonus + practice_bonus

    def _set_climb_practice_bonus(self, exit_obj, value):
        practice = dict(getattr(getattr(self, "ndb", None), "climb_practice", None) or {})
        practice[self._get_climb_practice_key(exit_obj)] = max(0, min(CLIMB_PRACTICE_CAP, int(value or 0)))
        self.ndb.climb_practice = practice

    def _adjust_climb_practice_bonus(self, exit_obj, amount):
        current = self._get_climb_practice_bonus(exit_obj)
        self._set_climb_practice_bonus(exit_obj, current + int(amount or 0))

    def _clear_climb_practice_bonus(self, exit_obj):
        practice = dict(getattr(getattr(self, "ndb", None), "climb_practice", None) or {})
        practice.pop(self._get_climb_practice_key(exit_obj), None)
        self.ndb.climb_practice = practice

    def _normalize_climb_outcome(self, outcome):
        normalized = str(outcome or "fail").strip().lower()
        if normalized == "strong":
            return "success"
        if normalized == "fail":
            return "failure"
        return normalized

    def _resolve_climb_outcome(self, skill_total, difficulty):
        if int(skill_total or 0) >= int(difficulty or 0) + 5:
            return "success"
        if int(skill_total or 0) >= int(difficulty or 0):
            return "partial"
        return "failure"

    def _get_climb_message(self, exit_obj, outcome):
        tier = self._get_climb_tier(exit_obj)
        readiness_rank = int(getattr(exit_obj.db, "climb_readiness_rank", 0) or 0)
        athletics = int(self.get_skill("athletics") or 0)
        if tier == "high" and readiness_rank > 0 and athletics < readiness_rank:
            if outcome == "failure":
                return HIGH_HIDE_REJECTION_MESSAGE
            if outcome == "success":
                return HIGH_HIDE_RARE_SUCCESS_MESSAGE
        pool = CLIMB_OUTCOME_MESSAGES.get(tier, {}).get(outcome, ())
        if not pool:
            return "You climb."
        return random.choice(pool)

    def _apply_climb_balance_penalty(self, amount):
        self.ensure_core_defaults()
        self.set_balance((self.db.balance or 0) - max(0, int(amount or 0)))

    def _maybe_emit_climb_learning_feedback(self, gained, practice_bonus=0):
        if float(gained or 0.0) <= 0.0:
            return
        if practice_bonus < 10 and random.random() > 0.3:
            return
        self.msg(random.choice(CLIMB_LEARNING_FEEDBACK))

    def resolve_climb_exit(self, exit_obj, target_location=None):
        if not exit_obj or not bool(getattr(exit_obj.db, "climb_contest", False)):
            return None
        if self.is_in_roundtime():
            self.msg_roundtime_block()
            return False

        current_room = getattr(self, "location", None)
        target_location = target_location or getattr(exit_obj, "destination", None)
        difficulty = int(getattr(exit_obj.db, "climb_difficulty", 35) or 35)
        contest_total = self._get_climb_skill_total(exit_obj)
        outcome = self._resolve_climb_outcome(contest_total, difficulty)

        gained = award_exp_skill(
            self,
            "athletics",
            difficulty,
            success=outcome != "failure",
            outcome=outcome,
            event_key="climbing",
        )

        if outcome == "success":
            self._clear_climb_practice_bonus(exit_obj)
            if current_room:
                msg_room(self, f"{self.key} finds a hold and climbs on.", exclude=[self])
            self.msg(self._get_climb_message(exit_obj, outcome))
            self.set_roundtime(float(getattr(exit_obj.db, "climb_success_roundtime", 1.0) or 1.0))
            self._maybe_emit_climb_learning_feedback(gained, practice_bonus=contest_total)
            return self.move_to(target_location, move_hooks=True)

        if outcome == "partial":
            self._adjust_climb_practice_bonus(exit_obj, CLIMB_PRACTICE_STEP)
            if current_room:
                msg_room(self, f"{self.key} slips and catches before falling.", exclude=[self])
            self.msg(self._get_climb_message(exit_obj, outcome))
            self._apply_climb_balance_penalty(getattr(exit_obj.db, "climb_partial_balance_cost", 6))
            self.set_roundtime(float(getattr(exit_obj.db, "climb_partial_roundtime", 1.5) or 1.5))
            self._maybe_emit_climb_learning_feedback(gained, practice_bonus=self._get_climb_practice_bonus(exit_obj))
            return False

        self._adjust_climb_practice_bonus(exit_obj, CLIMB_PRACTICE_STEP)
        if current_room:
            msg_room(self, f"{self.key} loses their grip and drops back down.", exclude=[self])
        self.msg(self._get_climb_message(exit_obj, outcome))
        self._apply_climb_balance_penalty(getattr(exit_obj.db, "climb_failure_balance_cost", 12))
        self.set_roundtime(float(getattr(exit_obj.db, "climb_failure_roundtime", 2.5) or 2.5))
        self._maybe_emit_climb_learning_feedback(gained, practice_bonus=self._get_climb_practice_bonus(exit_obj))

        failure_destination = self._resolve_room_reference(getattr(exit_obj.db, "climb_failure_destination", None))
        if failure_destination and current_room and getattr(failure_destination, "id", None) != getattr(current_room, "id", None):
            self.move_to(failure_destination, move_hooks=True)
        return False

    def attempt_climb(self, raw_target=""):
        climb_exit = self._resolve_climb_exit(raw_target)
        if climb_exit:
            return self.resolve_climb_exit(climb_exit, getattr(climb_exit, "destination", None))

        if self.is_in_roundtime():
            self.msg_roundtime_block()
            return False

        target = self._resolve_terrain_target(raw_target, "climbable")
        if target is None or target is False:
            self.msg("There is nothing here to climb.")
            return False

        msg_room(self, f"{self.key} attempts to climb.", exclude=[self])
        difficulty = int(getattr(target.db, "climb_difficulty", 35) or 35)
        result = run_contest(self.get_skill("athletics") + self.get_stat("agility") + self.get_stat("strength"), difficulty, attacker=self)
        outcome = self._normalize_climb_outcome(result.get("outcome"))
        if outcome == "failure":
            self.msg(random.choice(CLIMB_OUTCOME_MESSAGES["mid"]["failure"]))
            self._apply_climb_balance_penalty(8)
            self.set_roundtime(2.0)
        elif outcome == "partial":
            self.msg(random.choice(CLIMB_OUTCOME_MESSAGES["mid"]["partial"]))
            self._apply_climb_balance_penalty(4)
            self.set_roundtime(1.5)
        else:
            self.msg(random.choice(CLIMB_OUTCOME_MESSAGES["mid"]["success"]))
            self.set_roundtime(1.0)

        gained = award_exp_skill(self, "athletics", difficulty, success=outcome != "failure", outcome=outcome, event_key="athletics")
        self._maybe_emit_climb_learning_feedback(gained)
        return True

    def attempt_swim(self, raw_target=""):
        target = self._resolve_terrain_target(raw_target, "swimmable")
        if target is None or target is False:
            self.msg("There is nowhere here to swim.")
            return False

        msg_room(self, f"{self.key} attempts to swim.", exclude=[self])
        difficulty = int(getattr(target.db, "swim_difficulty", 35) or 35)
        result = run_contest(self.get_skill("athletics") + self.get_stat("stamina") + self.get_stat("agility"), difficulty, attacker=self)
        if result["outcome"] == "fail":
            self.msg("You fail to find a workable path through the water.")
        elif result["outcome"] == "partial":
            self.msg("You manage a few strokes, but make little progress.")
        else:
            self.msg("You swim successfully.")

        award_exp_skill(self, "athletics", difficulty, success=result["outcome"] != "fail")
        return True

    def split_numbered_query(self, query):
        raw_query = (query or "").strip()
        if not raw_query:
            return "", None

        match = re.match(r"^(?P<name>.+?)\s+(?P<index>\d+)$", raw_query)
        if not match:
            return raw_query, None

        return match.group("name").strip(), max(1, int(match.group("index")))

    def get_name_matches(self, query, candidates):
        target = (query or "").strip().lower()
        if not target:
            return []

        exact = []
        partial = []
        contains = []
        for obj in candidates or []:
            if not obj:
                continue

            names = []
            key = str(getattr(obj, "key", "") or "").strip().lower()
            if key:
                names.append(key)

            aliases = getattr(obj, "aliases", None)
            if aliases and hasattr(aliases, "all"):
                try:
                    names.extend(str(alias).strip().lower() for alias in aliases.all())
                except Exception:
                    pass

            if target in names:
                exact.append(obj)
                continue

            if any(name.startswith(target) for name in names if name):
                partial.append(obj)
                continue

            if any(target in name for name in names if name):
                contains.append(obj)

        return exact or partial or contains

    def resolve_numbered_candidate(self, query, candidates, default_first=True):
        base_query, index = self.split_numbered_query(query)
        matches = self.get_name_matches(base_query, candidates)
        if not matches:
            return None, matches, base_query, index

        if index is not None:
            if 1 <= index <= len(matches):
                return matches[index - 1], matches, base_query, index
            return None, matches, base_query, index

        if default_first or len(matches) == 1:
            return matches[0], matches, base_query, index

        return None, matches, base_query, index

    def msg_numbered_matches(self, query, matches):
        base_query = (query or "").strip()
        if not matches:
            return

        lines = [f"More than one match for '{base_query}' (use '{base_query} <number>' to choose one):"]
        for index, match in enumerate(matches, start=1):
            name = match.get_display_name(self) if hasattr(match, "get_display_name") else getattr(match, "key", str(match))
            lines.append(f" {index}. {name}")

        self.msg("\n".join(lines))

    def get_visible_carried_items(self):
        carried = []
        for item in self.contents:
            if getattr(item.db, "worn_by", None) == self:
                continue
            carried.append(item)
        return carried

    def get_armor_items(self):
        armor = []
        equipment = self.get_equipment()

        for slot, item in equipment.items():
            if self.is_multi_slot(slot):
                for obj in item:
                    if getattr(obj.db, "item_type", None) == "armor":
                        armor.append(obj)
            else:
                if item and getattr(item.db, "item_type", None) == "armor":
                    armor.append(item)

        return armor

    def body_part_matches_coverage(self, body_part, coverage):
        normalized_body_part = self.normalize_body_part_name(body_part)
        raw_coverage = str(coverage).strip().lower()
        normalized_coverage = self.normalize_body_part_name(coverage)

        if normalized_body_part == normalized_coverage:
            return True
        if raw_coverage == "arm":
            return normalized_body_part in {"left_arm", "right_arm"}
        if raw_coverage == "leg":
            return normalized_body_part in {"left_leg", "right_leg"}
        if raw_coverage == "hand":
            return normalized_body_part in {"left_hand", "right_hand"}
        return False

    def get_armor_covering(self, body_part):
        armor = self.get_armor_items()
        return [
            piece for piece in armor
            if any(
                self.body_part_matches_coverage(body_part, covered)
                for covered in (piece.db.coverage or piece.db.covers or [])
            )
        ]

    def get_worn_armor(self):
        return self.get_armor_items()

    def get_armor_for_bodypart(self, body_part):
        return self.get_armor_covering(body_part)

    def get_armor_types(self):
        return {piece.db.armor_type for piece in self.get_armor_items() if piece.db.armor_type}

    def get_armor_skill_bonus(self, armor):
        skill_name = ARMOR_SKILLS.get(getattr(armor.db, "armor_type", None))
        if not skill_name:
            return 0
        return self.get_skill_rank(skill_name) * 0.01

    def get_armor_protection_value(self, armor):
        base_protection = float(getattr(armor.db, "protection", 0) or 0)
        skill_name = ARMOR_SKILLS.get(getattr(armor.db, "armor_type", None))
        skill_rank = self.get_skill_rank(skill_name) if skill_name else 0

        if skill_rank < 10:
            base_protection *= 0.8
        elif skill_rank > 30:
            base_protection *= 1.2

        for threshold, effect in sorted((getattr(armor.db, "unlocks", None) or {}).items()):
            try:
                threshold_rank = int(threshold)
            except (TypeError, ValueError):
                continue
            if skill_rank >= threshold_rank:
                base_protection += (effect or {}).get("protection_bonus", 0)

        return max(0, base_protection)

    def get_total_armor_protection(self, body_part):
        armor_list = self.get_armor_for_bodypart(body_part)
        if not armor_list:
            return 0

        total_base = sum(float(getattr(armor.db, "protection", 0) or 0) for armor in armor_list)
        total_unlock_bonus = 0
        weighted_modifier_sum = 0.0
        total_weight = 0.0

        for armor in armor_list:
            skill_name = ARMOR_SKILLS.get(getattr(armor.db, "armor_type", None))
            skill_rank = self.get_skill_rank(skill_name) if skill_name else 0
            modifier = 0.0
            if skill_rank < 10:
                modifier = -0.2
            elif skill_rank > 30:
                modifier = 0.2

            coverage_entries = list(getattr(armor.db, "coverage", None) or getattr(armor.db, "covers", None) or [])
            matching_weights = [
                self.get_coverage_weight(entry)
                for entry in coverage_entries
                if self.body_part_matches_coverage(body_part, entry)
            ]
            armor_weight = max(matching_weights) if matching_weights else self.get_coverage_weight(body_part)
            weighted_modifier_sum += modifier * armor_weight
            total_weight += armor_weight

            for threshold, effect in sorted((getattr(armor.db, "unlocks", None) or {}).items()):
                try:
                    threshold_rank = int(threshold)
                except (TypeError, ValueError):
                    continue
                if skill_rank >= threshold_rank:
                    total_unlock_bonus += (effect or {}).get("protection_bonus", 0)

            average_modifier = (weighted_modifier_sum / total_weight) if total_weight else 0
        return max(0, (total_base * (1 + average_modifier)) + total_unlock_bonus)

    def get_armor_hindrance_value(self, armor):
        base_hindrance = float(
            getattr(armor.db, "hindrance", None)
            if getattr(armor.db, "hindrance", None) is not None
            else max(getattr(armor.db, "maneuver_hindrance", 0) or 0, getattr(armor.db, "stealth_hindrance", 0) or 0)
        )
        skill_name = ARMOR_SKILLS.get(getattr(armor.db, "armor_type", None))
        skill_rank = self.get_skill_rank(skill_name) if skill_name else 0

        if skill_rank > 30:
            base_hindrance *= 0.8

        for threshold, effect in sorted((getattr(armor.db, "unlocks", None) or {}).items()):
            try:
                threshold_rank = int(threshold)
            except (TypeError, ValueError):
                continue
            if skill_rank >= threshold_rank:
                base_hindrance -= (effect or {}).get("hindrance_reduction", 0)

        return max(0, base_hindrance)

    def get_armor_effects(self, armor):
        effects = {}
        skill_name = ARMOR_SKILLS.get(getattr(armor.db, "armor_type", None))
        if not skill_name:
            return effects

        rank = self.get_skill_rank(skill_name)
        for tier in (armor.db.skill_scaling or {}).get(skill_name, []):
            if rank >= tier.get("rank", 0):
                effects.update(tier.get("effects", {}))
        return effects

    def get_total_hindrance(self):
        armor = self.get_armor_items()
        maneuver = 0
        stealth = 0

        for piece in armor:
            effects = self.get_armor_effects(piece)
            base_hindrance = self.get_armor_hindrance_value(piece)
            maneuver += max(0, base_hindrance - effects.get("maneuver_hindrance", 0))
            stealth += max(0, base_hindrance - effects.get("stealth_hindrance", 0))

        armor_types = self.get_armor_types()
        if len(armor_types) > 1:
            maneuver += (len(armor_types) - 1) * 5

        return maneuver, stealth

    def get_grouped_worn_display_lines(self, looker=None):
        equipment = self.get_equipment()
        lines = []

        if looker == self:
            section_header = "You are wearing:"
        else:
            section_header = f"{self.key} is wearing:"

        section_lines = []
        for slot in APPEARANCE_SLOT_ORDER:
            item = equipment.get(slot)
            if self.is_multi_slot(slot):
                if not item:
                    continue
                names = ", ".join(obj.key for obj in item)
                if looker == self:
                    section_lines.append(f"  {slot}: {names}")
                else:
                    section_lines.append(f"  {names}")
                continue

            if not item:
                continue

            if looker == self:
                section_lines.append(f"  {slot}: {item.key}")
            else:
                section_lines.append(f"  {item.key}")

        if section_lines:
            lines.append(section_header)
            lines.extend(section_lines)
        return lines

    def get_attack_verb(self):
        return random.choice(
            [
                ("swing at", "swings at"),
                ("slash at", "slashes at"),
                ("strike", "strikes"),
                ("lunge at", "lunges at"),
            ]
        )

    def get_hit_result(self, damage):
        if damage <= 2:
            return "barely hit"
        elif damage <= 4:
            return "hit"
        return "land a solid hit"

    def get_attack_phrases(self, weapon_name):
        actor_verb, third_person_verb = self.get_attack_verb()
        weapon_phrase = "your fists" if weapon_name == "fists" else f"your {weapon_name}"
        target_weapon_phrase = "fists" if weapon_name == "fists" else weapon_name
        return {
            "actor": f"{actor_verb} {{target}} with {weapon_phrase}",
            "target": f"{third_person_verb} you with {target_weapon_phrase}",
            "room": f"{third_person_verb} {{target}} with {target_weapon_phrase}",
        }

    def ensure_skill_defaults(self):
        current_skills = self.db.skills
        if current_skills is None:
            self.db.skills = {}
            current_skills = {}

        normalized = {}
        for skill_name, skill_data in (current_skills or {}).items():
            if not isinstance(skill_data, Mapping):
                skill_data = {}

            normalized[skill_name] = {
                "rank": skill_data.get("rank", 0),
                "mindstate": skill_data.get("mindstate", 0),
            }

        if dict(current_skills or {}) != normalized:
            self.db.skills = normalized

    def update_skill(self, skill_name, **updates):
        self.ensure_skill_defaults()
        skills = dict(self.db.skills)
        current = dict(skills.get(skill_name, {"rank": 0, "mindstate": 0}))
        current.update(updates)
        skills[skill_name] = current
        self.db.skills = skills
        self._sync_exp_skill_state(skill_name, current)

    def get_mindstate_label(self, value):
        if value <= 0:
            return MINDSTATE_LEVELS[0]
        index = min(((value - 1) // 10) + 1, len(MINDSTATE_LEVELS) - 1)
        return MINDSTATE_LEVELS[index]

    def get_mindstate_cap(self):
        intelligence = self.get_stat("intelligence")
        return 110 + (intelligence * 2)

    def get_learning_drain(self):
        wisdom = self.get_stat("wisdom")
        return 5 + (wisdom // 10)

    def get_scholarship_learning_multiplier(self):
        scholarship = self.get_skill("scholarship")
        return 1 + (scholarship / 100.0)

    def start_teaching(self, skill_name, target):
        if not target or not hasattr(target, "get_skill"):
            self.msg("You cannot teach that to them.")
            return

        if self.get_skill(skill_name) <= target.get_skill(skill_name):
            self.msg("You are not experienced enough to teach that skill to them.")
            return

        self.set_state("teaching", {"skill": skill_name, "target": target.id})
        target.set_state("learning_from", {"skill": skill_name, "teacher": self.id})

        self.msg(f"You begin teaching {skill_name} to {target.key}.")
        target.msg(f"{self.key} begins teaching you {skill_name}.")

    def get_teaching_strength(self):
        scholarship = self.get_skill("scholarship")
        return 1 + (scholarship / 100.0)

    def process_teaching_pulse(self):
        learning = self.get_state("learning_from")
        if not learning:
            return

        skill_name = learning.get("skill")
        teacher_id = learning.get("teacher")
        if not self.location:
            self.clear_state("learning_from")
            return

        teacher = None
        for obj in self.location.contents:
            if obj.id == teacher_id:
                teacher = obj
                break

        if not teacher or teacher.location != self.location:
            self.clear_state("learning_from")
            return

        if self.get_skill(skill_name) >= teacher.get_skill(skill_name) - 2:
            self.msg("You are no longer learning much from this.")
            return

        gain = teacher.get_teaching_strength()
        self.use_skill(
            skill_name,
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            learning_multiplier=gain,
        )
        self.msg(f"You continue learning under {teacher.key}'s guidance.")
        teacher.msg("You continue teaching.")

    def assess_stance(self, target):
        tactics = self.get_skill("tactics")

        self.msg(f"You study {target.key}'s stance carefully.")

        if tactics < 5:
            self.msg("You struggle to read their intentions.")
        elif tactics < 15:
            self.msg("You get a rough sense of how they carry themselves in combat.")
        elif tactics < 30:
            self.msg("You begin to recognize strengths and weaknesses in their stance.")
        else:
            self.msg("You read their stance with confidence, noting likely strengths and openings.")

        self.set_state(
            "tactics_prep",
            {
                "target": target.id,
                "bonus": min(10, 1 + self.get_skill("tactics") // 10),
            },
        )
        self.use_skill("tactics", apply_roundtime=False, emit_placeholder=False, require_known=False)

    def get_weapon(self):
        self.ensure_core_defaults()
        weapon = self.db.equipped_weapon
        if not weapon:
            return None

        if weapon.location != self:
            self.db.equipped_weapon = None
            return None

        return weapon

    def get_wielded_weapon(self):
        self.ensure_core_defaults()
        return self.get_weapon()

    def is_wielding(self, item_name):
        weapon = self.get_wielded_weapon()
        if not weapon:
            return False

        normalized = str(item_name or "").strip().lower()
        if not normalized:
            return False

        known_names = {str(getattr(weapon, "key", "") or "").strip().lower()}
        aliases = getattr(weapon, "aliases", None)
        if aliases:
            for alias in list(aliases.all() or []):
                alias_text = str(alias or "").strip().lower()
                if alias_text:
                    known_names.add(alias_text)
        return normalized in known_names

    def _get_ranger_resource_state(self):
        state = getattr(getattr(self, "ndb", None), "ranger_resource_state", None)
        if not isinstance(state, dict):
            state = {}
            self.ndb.ranger_resource_state = state
        return state

    def _get_ranger_resource_state_key(self, room, resource_key):
        room_id = getattr(room, "id", None) or str(getattr(room, "key", "room") or "room")
        return f"{room_id}:{str(resource_key or '').strip().lower()}"

    def get_room_ranger_resources(self, room=None):
        room = room or getattr(self, "location", None)
        resources = list(getattr(getattr(room, "db", None), "ranger_resources", []) or [])
        normalized = []
        for entry in resources:
            key = str(entry or "").strip().lower()
            if key in RANGER_RESOURCE_PROFILES and key not in normalized:
                normalized.append(key)
        return normalized

    def get_available_ranger_resources(self, room=None):
        room = room or getattr(self, "location", None)
        if not room or not self.is_profession("ranger"):
            return []
        state = self._get_ranger_resource_state()
        available = []
        for resource_key in self.get_room_ranger_resources(room):
            if state.get(self._get_ranger_resource_state_key(room, resource_key)):
                continue
            available.append(resource_key)
        return available

    def get_ranger_room_render_lines(self, room=None):
        room = room or getattr(self, "location", None)
        if not room:
            return []

        lines = []
        for resource_key in self.get_available_ranger_resources(room):
            label = str(RANGER_RESOURCE_PROFILES.get(resource_key, {}).get("room_label", "") or "").strip()
            if label:
                lines.append(label)

        return lines

    def get_ranger_room_action_entries(self, room=None):
        room = room or getattr(self, "location", None)
        entries = []
        for resource_key in self.get_available_ranger_resources(room):
            command = str(RANGER_RESOURCE_PROFILES.get(resource_key, {}).get("action", "") or "").strip()
            if command:
                entries.append({"command": command, "label": command})
        return entries

    def gather_ranger_resource(self, resource_name):
        room = getattr(self, "location", None)
        normalized = str(resource_name or "").strip().lower()
        profile = RANGER_RESOURCE_PROFILES.get(normalized)
        if not room or not profile:
            self.msg("You don't find that here.")
            return False
        if normalized not in self.get_available_ranger_resources(room):
            self.msg("You don't find that here.")
            return False

        create_simple_item(
            self,
            key=profile["key"],
            desc=profile["desc"],
            item_type=profile["item_type"],
            ranger_resource_kind=normalized,
            item_value=profile["value"],
            value=profile["value"],
            weight=profile["weight"],
            forage_kind=normalized,
        )
        state = self._get_ranger_resource_state()
        state[self._get_ranger_resource_state_key(room, normalized)] = True
        self.ndb.ranger_resource_state = state
        self.db.forage_uses = int(getattr(self.db, "forage_uses", 0) or 0) + 1
        self.msg(profile["gather_message"])
        if self.location:
            self.location.msg_contents(f"{self.key} gathers {profile['key']}.", exclude=[self])
        self.use_skill("outdoorsmanship", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=10)
        return True

    def _match_ranger_resource_item(self, item, resource_key):
        if not item:
            return False
        normalized = str(resource_key or "").strip().lower()
        item_kind = str(getattr(getattr(item, "db", None), "ranger_resource_kind", "") or "").strip().lower()
        if item_kind == normalized:
            return True
        item_key = str(getattr(item, "key", "") or "").strip().lower()
        return item_key == normalized or item_key == f"{normalized}s"

    def transform_ranger_resource(self, action_key, resource_name):
        recipe = RANGER_RESOURCE_RECIPES.get(str(action_key or "").strip().lower())
        if not recipe:
            self.msg("You can't work that into anything useful.")
            return False

        requested = str(resource_name or "").strip().lower()
        if requested.endswith("s") and not requested.endswith("ss"):
            requested = requested[:-1]
        if requested and requested != recipe["input"]:
            self.msg("That recipe won't take that material.")
            return False

        carried = list(self.get_visible_carried_items())
        match = next((item for item in carried if self._match_ranger_resource_item(item, recipe["input"])), None)
        if not match:
            self.msg("You are not carrying the material you need.")
            return False

        match.key = recipe["output_key"]
        match.db.desc = recipe["output_desc"]
        match.db.item_type = recipe["output_type"]
        match.db.ranger_resource_kind = recipe["input"]
        match.db.item_value = recipe["value"]
        match.db.value = recipe["value"]
        match.db.weight = recipe["weight"]
        self.msg(recipe["success_message"])
        self.use_skill("outdoorsmanship", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=12)
        return match

    def clear_equipped_weapon(self):
        self.ensure_core_defaults()
        self.db.equipped_weapon = None
        self.sync_client_state()

    def get_equipment(self):
        self.ensure_core_defaults()
        return self.db.equipment or _copy_default_equipment()

    def is_multi_slot(self, slot):
        return slot in ["fingers", "belt_attach", "back_attach", "shoulder_attach"]

    def get_slot_capacity(self, slot):
        capacities = {
            "fingers": 10,
            "belt_attach": 4,
            "back_attach": 2,
            "shoulder_attach": 2,
        }
        return capacities.get(slot, 1)

    def normalize_equipment_slot(self, slot):
        if slot == "belt":
            return "waist"
        return slot

    def is_slot_free(self, slot):
        equipment = self.get_equipment()
        if self.is_multi_slot(slot):
            return True
        return equipment.get(slot) is None

    def get_worn_items(self):
        worn = []
        for slot, item in self.get_equipment().items():
            if self.is_multi_slot(slot):
                worn.extend(item)
            elif item:
                worn.append(item)
        return worn

    def find_worn_item(self, item_name):
        item, matches, base_query, index = self.resolve_numbered_candidate(
            item_name,
            self.get_worn_items(),
            default_first=True,
        )
        if item:
            return item
        if matches and index is not None:
            self.msg_numbered_matches(base_query, matches)
        return None

    def clear_equipment_item(self, item):
        equipment = self.get_equipment()
        for slot, equipped in equipment.items():
            if self.is_multi_slot(slot):
                if item in equipped:
                    equipped.remove(item)
                    if getattr(item.db, "worn_by", None) == self:
                        item.db.worn_by = None
                    if self.db.preferred_sheath == item:
                        self.db.preferred_sheath = None
                    return True
                continue

            if equipped == item:
                equipment[slot] = None
                if getattr(item.db, "worn_by", None) == self:
                    item.db.worn_by = None
                if self.db.preferred_sheath == item:
                    self.db.preferred_sheath = None
                return True
        return False

    def equip_item(self, item):
        if not getattr(item.db, "wearable", False):
            return False, "You cannot wear that."

        slot = self.normalize_equipment_slot(getattr(item.db, "slot", None))
        if not slot or slot not in self.get_equipment():
            return False, "That item cannot be worn."

        if item.location != self:
            return False, "You must be holding that to wear it."

        equipment = self.get_equipment()

        if self.is_multi_slot(slot):
            current = equipment.get(slot, [])
            if len(current) >= self.get_slot_capacity(slot):
                return False, f"You cannot wear anything more on your {slot}."
            current.append(item)
        else:
            if not self.is_slot_free(slot):
                return False, f"Your {slot} is already occupied."
            equipment[slot] = item

        item.location = None
        item.db.worn_by = self
        item.db.slot = slot
        if getattr(item.db, "is_sheath", False) and not self.db.preferred_sheath:
            self.db.preferred_sheath = item
        self.sync_client_state()
        message = f"You wear {item.key}."
        try:
            from systems import onboarding

            completed, override_message = onboarding.note_equipment_action(self, item)
            if completed and override_message:
                message = override_message
        except Exception:
            pass
        return True, message

    def unequip_item(self, item):
        equipment = self.get_equipment()
        for slot, equipped in equipment.items():
            if self.is_multi_slot(slot):
                if item in equipped:
                    equipped.remove(item)
                    item.location = self
                    item.db.worn_by = None
                    if self.db.preferred_sheath == item:
                        self.db.preferred_sheath = None
                    self.sync_client_state()
                    return True, f"You remove {item.key}."
                continue

            if equipped == item:
                equipment[slot] = None
                item.location = self
                item.db.worn_by = None
                if self.db.preferred_sheath == item:
                    self.db.preferred_sheath = None
                self.sync_client_state()
                return True, f"You remove {item.key}."

        return False, "You are not wearing that."

    def get_worn_sheaths(self):
        self.ensure_core_defaults()
        return [obj for obj in self.get_worn_items() if getattr(obj.db, "is_sheath", False)]

    def get_worn_containers(self):
        self.ensure_core_defaults()
        return [obj for obj in self.get_worn_items() if getattr(obj.db, "is_container", False)]

    def get_worn_container_by_name(self, container_name):
        self.ensure_core_defaults()
        container, matches, base_query, index = self.resolve_numbered_candidate(
            container_name,
            self.get_worn_containers(),
            default_first=True,
        )
        if container:
            return container
        if matches and index is not None:
            self.msg_numbered_matches(base_query, matches)
        return None

    def get_preferred_sheath(self):
        self.ensure_core_defaults()
        sheath = self.db.preferred_sheath
        if not sheath:
            return None
        if sheath not in self.get_worn_sheaths():
            self.db.preferred_sheath = None
            return None
        return sheath

    def set_preferred_sheath(self, sheath):
        self.ensure_core_defaults()
        if sheath and sheath in self.get_worn_sheaths():
            self.db.preferred_sheath = sheath
        else:
            self.db.preferred_sheath = None

    def get_stowed_weapon(self, weapon_name):
        self.ensure_core_defaults()
        base_query, index = self.split_numbered_query(weapon_name)
        if not base_query:
            return None, None

        matches = []
        for sheath in self.get_worn_sheaths():
            for item in sheath.get_stored_items() if hasattr(sheath, "get_stored_items") else sheath.contents:
                matches.append((item, sheath))

        if not matches:
            return None, None

        matched_items = self.get_name_matches(base_query, [item for item, _ in matches])
        matched_pairs = [pair for pair in matches if pair[0] in matched_items]
        if not matched_pairs:
            return None, None

        if index is not None:
            if 1 <= index <= len(matched_pairs):
                return matched_pairs[index - 1]
            self.msg_numbered_matches(base_query, [item for item, _ in matched_pairs])
            return None, None

        return matched_pairs[0]

    def get_worn_sheath_by_name(self, sheath_name):
        self.ensure_core_defaults()
        sheath, matches, base_query, index = self.resolve_numbered_candidate(
            sheath_name,
            self.get_worn_sheaths(),
            default_first=True,
        )
        if sheath:
            return sheath
        if matches and index is not None:
            self.msg_numbered_matches(base_query, matches)
        return None

    def resolve_stow_sheath(self):
        self.ensure_core_defaults()
        preferred = self.get_preferred_sheath()
        if preferred:
            return preferred, None

        sheaths = self.get_worn_sheaths()
        if not sheaths:
            return None, "You are not wearing a sheath."
        if len(sheaths) > 1:
            return None, "You are wearing more than one sheath. Specify which sheath to use first."
        sheath = sheaths[0]
        self.set_preferred_sheath(sheath)
        return sheath, None

    def get_equipment_display_lines(self, looker=None):
        self.ensure_core_defaults()
        lines = []
        weapon = self.get_weapon()
        if weapon:
            if looker == self:
                lines.append(f"You are wielding {weapon.key}.")
            else:
                lines.append(f"They are wielding {weapon.key}.")

        worn_lines = self.get_grouped_worn_display_lines(looker=looker)
        if worn_lines:
            lines.append("")
            lines.extend(worn_lines)

        if looker != self and self.get_visible_carried_items():
            lines.append("")
            lines.append("They are carrying some items.")

        return lines

    def get_range(self, target):
        self.ensure_core_defaults()
        if not target or getattr(target, "id", None) is None:
            return "melee"
        return normalize_range_band((self.db.combat_range or {}).get(target.id, "melee"))

    def set_range(self, target, value, reciprocal=True):
        self.ensure_core_defaults()
        if not target or getattr(target, "id", None) is None:
            return

        band = normalize_range_band(value)
        combat_range = dict(self.db.combat_range or {})
        combat_range[target.id] = band
        self.db.combat_range = combat_range

        range_break_ticks = dict(self.db.range_break_ticks or {})
        range_break_ticks[target.id] = 0
        self.db.range_break_ticks = range_break_ticks

        if reciprocal and hasattr(target, "set_range"):
            target.set_range(self, band, reciprocal=False)

    def clear_range(self, target, reciprocal=True):
        self.ensure_core_defaults()
        if not target or getattr(target, "id", None) is None:
            return

        combat_range = dict(self.db.combat_range or {})
        combat_range.pop(target.id, None)
        self.db.combat_range = combat_range

        range_break_ticks = dict(self.db.range_break_ticks or {})
        range_break_ticks.pop(target.id, None)
        self.db.range_break_ticks = range_break_ticks

        if reciprocal and hasattr(target, "clear_range"):
            target.clear_range(self, reciprocal=False)

    def clear_aim(self):
        self.ensure_core_defaults()
        self.db.aiming = None
        self.clear_state("aiming")
        self.clear_state("ranger_aiming")
        self.clear_state("ranger_snipe")
        clear_direct_interest(self, channel="aim")

    def get_pressure(self, target=None):
        self.ensure_core_defaults()
        stance = self.db.stance or {"offense": 50, "defense": 50}
        return self.get_skill("combat") + stance.get("offense", 50)

    def process_combat_range_tick(self):
        self.ensure_core_defaults()
        self.sync_combat_state()
        target = self.db.target
        if not self.db.in_combat or not target or not getattr(target, "pk", None):
            return

        if getattr(self, "id", 0) > getattr(target, "id", 0):
            return

        my_range = self.get_range(target)
        their_range = target.get_range(self) if hasattr(target, "get_range") else my_range
        if my_range == "far" and their_range == "far":
            range_break_ticks = dict(self.db.range_break_ticks or {})
            ticks = range_break_ticks.get(target.id, 0) + 1
            range_break_ticks[target.id] = ticks
            self.db.range_break_ticks = range_break_ticks
            if ticks >= 2:
                self.msg(f"You lose contact with {target.key}.")
                if hasattr(target, "msg"):
                    target.msg(f"You lose contact with {self.key}.")
                self.clear_range(target)
                _clear_combat_link(self)
            return

        range_break_ticks = dict(self.db.range_break_ticks or {})
        if range_break_ticks.get(target.id):
            range_break_ticks[target.id] = 0
            self.db.range_break_ticks = range_break_ticks

    def return_appearance(self, looker):
        self.ensure_appearance_defaults()
        if looker and hasattr(looker, "can_perceive") and not looker.can_perceive(self):
            return "You see nothing unusual."

        desc = self.get_rendered_desc(looker)
        descriptor = self.get_race_descriptor()
        identity_line = self.get_display_name(looker)
        if descriptor:
            identity_line = f"{identity_line} ({descriptor})"

        lines = [identity_line, desc]
        if looker == self:
            lines.append(self.get_self_race_line())
        else:
            lines.append(self.get_other_race_line())

        lines.extend(self.get_equipment_display_lines(looker=looker))

        flavor = self.get_flavor_text()
        if flavor:
            lines.append("")
            lines.append(flavor)

        equipment_flavor = self.get_equipment_flavor()
        if equipment_flavor:
            lines.append("")
            lines.append(equipment_flavor)

        injury_lines = self.get_injury_display_lines(looker=looker)
        condition = self.get_condition_text()
        if injury_lines or condition:
            lines.append("")
            lines.extend(injury_lines)

        if looker == self:
            lines.append(f"You are {condition}.")
        else:
            lines.append(f"They are {condition}.")

        return "\n".join(lines)

    def get_display_name(self, looker=None, **kwargs):
        if getattr(self.db, "disguised", False) and looker != self:
            return getattr(self.db, "disguise_name", None) or self.key
        return self.key

    def get_weapon_profile(self):
        self.ensure_core_defaults()
        weapon = self.get_weapon()
        profile = _copy_default_weapon_profile()
        if not weapon:
            return profile

        weapon_profile = None
        if hasattr(weapon, "get_weapon_profile"):
            weapon_profile = weapon.get_weapon_profile()
        elif isinstance(getattr(weapon.db, "weapon_profile", None), Mapping):
            weapon_profile = dict(weapon.db.weapon_profile)

        if isinstance(weapon_profile, Mapping):
            profile.update({key: value for key, value in weapon_profile.items() if value is not None})

        if weapon.db.damage_min is not None:
            profile["damage_min"] = weapon.db.damage_min
        if weapon.db.damage_max is not None:
            profile["damage_max"] = weapon.db.damage_max
        if weapon.db.damage is not None:
            profile["damage"] = weapon.db.damage
        if weapon.db.roundtime is not None:
            profile["roundtime"] = weapon.db.roundtime
        if weapon.db.balance_cost is not None:
            profile["balance_cost"] = weapon.db.balance_cost
        if weapon.db.fatigue_cost is not None:
            profile["fatigue_cost"] = weapon.db.fatigue_cost
        if weapon.db.balance is not None:
            profile["balance"] = weapon.db.balance

        if hasattr(weapon, "get_weapon_skill"):
            profile["skill"] = weapon.get_weapon_skill() or profile["skill"]
        elif weapon.db.skill:
            profile["skill"] = weapon.db.skill

        range_band = getattr(weapon.db, "range_band", None)
        if range_band is not None:
            profile["range_band"] = normalize_range_band(range_band)
        range_type = getattr(weapon.db, "weapon_range_type", None)
        if range_type:
            profile["weapon_range_type"] = str(range_type).strip().lower()
        if bool(getattr(weapon.db, "is_ranged", False)) and not profile.get("weapon_range_type"):
            profile["weapon_range_type"] = "bow"
        if profile.get("weapon_range_type"):
            profile["range_band"] = normalize_range_band(profile.get("range_band"), default="far")

        if hasattr(weapon, "normalize_damage_types"):
            weapon.normalize_damage_types()

        damage_types = getattr(weapon.db, "damage_types", None)
        if isinstance(damage_types, Mapping) and damage_types:
            profile["damage_types"] = dict(damage_types)

        if weapon.db.damage_type:
            profile["damage_type"] = weapon.db.damage_type
        elif profile["damage_types"]:
            profile["damage_type"] = max(profile["damage_types"], key=profile["damage_types"].get)

        damage_min = profile.get("damage_min")
        damage_max = profile.get("damage_max")
        if damage_min is None:
            damage_min = profile.get("damage") or 1
            profile["damage_min"] = damage_min
        if damage_max is None:
            damage_max = max(int(damage_min or 1), int(profile.get("damage") or damage_min or 1))
            profile["damage_max"] = damage_max
        if profile.get("damage") is None:
            profile["damage"] = max(1, int(round((int(damage_min or 1) + int(damage_max or damage_min or 1)) / 2)))

        if self.has_warrior_passive("weapon_handling_1"):
            profile["roundtime"] = max(1.0, float(profile.get("roundtime", 3.0) or 3.0) - 0.25)

        return profile

    def is_in_roundtime(self):
        self.ensure_core_defaults()
        return time.time() < (self.db.roundtime_end or 0)

    def get_remaining_roundtime(self):
        self.ensure_core_defaults()
        remaining = (self.db.roundtime_end or 0) - time.time()
        return max(0, round(remaining, 2))

    def _get_roundtime_schedule_key(self):
        object_id = int(getattr(self, "id", 0) or 0)
        if object_id > 0:
            return f"combat:roundtime:{object_id}"
        dbref = str(getattr(self, "dbref", "") or "").strip().lstrip("#")
        if dbref.isdigit():
            return f"combat:roundtime:{dbref}"
        stable_name = str(getattr(self, "key", "character") or "character").strip().lower().replace(" ", "-")
        return f"combat:roundtime:{stable_name}"

    def _expire_roundtime(self, expected_end=None):
        self.ensure_core_defaults()
        current_end = float(self.db.roundtime_end or 0.0)
        if current_end <= 0.0:
            return False
        if expected_end is not None and current_end > float(expected_end or 0.0) + 0.01:
            return False
        if time.time() + 0.01 < current_end:
            return False
        self.db.roundtime_end = 0
        self.sync_client_state()
        return True

    def set_roundtime(self, seconds):
        self.ensure_core_defaults()
        from world.systems.scheduler import cancel, schedule
        from world.systems.time_model import SCHEDULED_EXPIRY

        seconds = max(0.0, float(seconds or 0.0))
        if seconds <= 0.0:
            self.db.roundtime_end = 0
            cancel(self._get_roundtime_schedule_key())
            self.sync_client_state()
            return 0.0

        target_end = time.time() + seconds
        self.db.roundtime_end = target_end
        schedule(
            seconds,
            self._expire_roundtime,
            key=self._get_roundtime_schedule_key(),
            system="combat.roundtime",
            timing_mode=SCHEDULED_EXPIRY,
            expected_end=target_end,
        )
        self.sync_client_state()
        return target_end

    def apply_thief_roundtime(self, seconds, minimum=0.5):
        self.ensure_core_defaults()
        from world.systems.scheduler import schedule
        from world.systems.time_model import SCHEDULED_EXPIRY

        seconds = max(float(minimum), float(seconds))
        current_end = float(self.db.roundtime_end or 0)
        now = time.time()
        target_end = max(current_end, now) + seconds
        self.db.roundtime_end = target_end
        schedule(
            max(0.0, target_end - now),
            self._expire_roundtime,
            key=self._get_roundtime_schedule_key(),
            system="thief.roundtime",
            timing_mode=SCHEDULED_EXPIRY,
            expected_end=target_end,
        )
        self.sync_client_state()
        return target_end

    def msg_roundtime_block(self):
        remaining = self.get_remaining_roundtime()
        self.msg(f"You must wait {remaining:.2f} seconds before acting.")

    def use_skill(self, skill_name, *args, **kwargs):
        self.ensure_core_defaults()
        apply_roundtime = kwargs.get("apply_roundtime", True)
        emit_placeholder = kwargs.get("emit_placeholder", True)
        require_known = kwargs.get("require_known", True)
        difficulty = kwargs.get("difficulty", 10)
        return_learning = kwargs.get("return_learning", False)
        learning_multiplier = max(0, kwargs.get("learning_multiplier", 1))

        if self.is_dead():
            self.msg("You cannot learn or practice while dead.")
            return (0, "dead") if return_learning else False

        if apply_roundtime and self.is_in_roundtime():
            self.msg_roundtime_block()
            return (0, "blocked") if return_learning else False

        if require_known and not self.has_skill(skill_name):
            self.msg("You do not know that skill.")
            return (0, "unknown") if return_learning else False

        amount, band = self.get_learning_amount(skill_name, difficulty)
        skillset = self.get_skillset(skill_name)
        weight = self.get_skill_weight(skillset)
        amount *= weight
        print(f"[XP] {self} {skillset} x{weight}")
        amount *= learning_multiplier
        amount *= self.get_scholarship_learning_multiplier()
        amount *= self.get_race_learning_modifier(skill_name=skill_name)
        amount = int(amount) if amount > 0 else 0
        if amount > 0:
            amount = max(1, amount)

        debt_multiplier = self.get_xp_debt_gain_multiplier()
        if amount > 0 and debt_multiplier < 1.0:
            amount = max(1, int(round(amount * debt_multiplier)))

        if amount > 0:
            self.db.total_xp = int(getattr(self.db, "total_xp", 0) or 0) + amount
            self.adjust_unabsorbed_xp(amount)
            self.reduce_exp_debt(amount)
            if not bool(FAVOR_SYSTEM_CONFIG.get("route_xp_only", False)):
                skill = self.db.skills.get(skill_name)
                if skill:
                    cap = self.get_mindstate_cap()
                    self.update_skill(skill_name, mindstate=min(skill.get("mindstate", 0) + amount, cap))

        if emit_placeholder:
            self.msg(f"You try to use {skill_name}, but it is not implemented.")
        if apply_roundtime:
            self.set_roundtime(3)
        if return_learning:
            return amount, band
        return True

    def use_ability(self, key, target=None):
        # profession ability injection here
        before_subsystem = self.get_subsystem() if hasattr(self, "get_subsystem") else None
        ability = get_ability(key, self)

        if getattr(self.db, "is_captured", False):
            self.msg("You are restrained and cannot do that.")
            return
        if getattr(self.db, "in_stocks", False):
            self.msg("You cannot do that while restrained in the stocks.")
            return

        if not ability:
            self.msg("You don't know how to do that.")
            return

        if self.is_hidden_warrior_ability(ability):
            self.msg("You have not yet learned how to do that.")
            return

        if getattr(self.ndb, "is_busy", False):
            self.msg("You are still committed to another action.")
            return

        now = time.time()
        cooldowns = self.get_ability_cooldowns()
        cooldown_until = float(cooldowns.get(ability.key, 0) or 0)
        if now < cooldown_until:
            self.msg(f"{ability.key.title()} is not ready yet.")
            return

        self.ndb.is_walking = False
        before_feedback = self.format_subsystem_snapshot(before_subsystem)
        if before_feedback:
            self.msg(before_feedback)

        if not self.passes_guild_check(ability):
            self.msg("That is not your path.")
            return

        ok, msg = self.meets_ability_requirements(ability)
        if not ok:
            self.msg(msg)
            return

        ok, msg = ability.can_use(self, target)
        if not ok:
            self.msg(self.normalize_ability_failure_message(msg, before_subsystem))
            return

        self.ndb.is_busy = True
        self.debug_log(f"[ABILITY] {self} triggers {ability.key}{f' -> {target}' if target else ''}")
        self.msg(f"You prepare to {ability.key}...")
        try:
            ability.execute(self, target)
        finally:
            self.ndb.is_busy = False

        cooldown_duration = float(getattr(ability, "cooldown", getattr(ability, "roundtime", 0)) or 0)
        if cooldown_duration > 0:
            cooldowns[ability.key] = time.time() + cooldown_duration
            self.ndb.cooldowns = cooldowns

        feedback = self.format_subsystem_feedback(before_subsystem, self.get_subsystem() if hasattr(self, "get_subsystem") else None)
        if feedback:
            self.msg(feedback)
            self.debug_log(f"[SUBSYSTEM] {self} {feedback}")

        if hasattr(ability, "roundtime"):
            self.set_roundtime(ability.roundtime)
        else:
            self.sync_client_state()

        self.emit_ability_presence(ability)

    def meets_ability_requirements(self, ability):
        req = getattr(ability, "required", {}) or {}
        skill = req.get("skill")
        rank = req.get("rank", 0)

        if skill:
            current_rank = self.get_skill(skill)
            if current_rank < rank:
                return False, "You are not experienced enough."

        return True, ""

    def passes_guild_check(self, ability):
        if not getattr(ability, "guilds", None):
            return True

        player_profession = self.get_profession()
        return player_profession in ability.guilds

    def is_hidden_warrior_ability(self, ability_or_key):
        ability_key = getattr(ability_or_key, "key", ability_or_key)
        ability_key = str(ability_key or "").strip().lower()
        if ability_key not in WARRIOR_ABILITY_DATA:
            return False
        if not self.is_profession("warrior"):
            return False
        return ability_key not in set(self.get_unlocked_warrior_abilities())

    def can_see_ability(self, ability):
        if not self.passes_guild_check(ability):
            return False
        if self.is_hidden_warrior_ability(ability):
            return False

        vis = getattr(ability, "visible_if", {}) or {}
        skill = vis.get("skill")
        rank = vis.get("min_rank", 0)

        if skill and self.get_skill(skill) < rank:
            return False

        return True

    def get_visible_abilities(self):
        from typeclasses.abilities import get_ability_map

        return [
            ability for ability in get_ability_map(self).values()
            if self.can_see_ability(ability)
        ]

    def set_state(self, key, value):
        self.ensure_core_defaults()
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states
        self.sync_client_state()

    def get_state(self, key):
        states = getattr(self.db, "states", None)
        if not isinstance(states, Mapping):
            return None
        return states.get(key)

    def has_state(self, key):
        states = getattr(self.db, "states", None)
        return bool(isinstance(states, Mapping) and key in states)

    def clear_state(self, key):
        self.ensure_core_defaults()
        if self.db.states and key in self.db.states:
            states = dict(self.db.states)
            del states[key]
            self.db.states = states
            self.sync_client_state()

    def clear_all_states(self):
        self.ensure_core_defaults()
        self.db.states = {}

    def has_skill(self, skill_name):
        self.ensure_core_defaults()
        return skill_name in (self.db.skills or {})

    def learn_skill(self, skill_name, data=None):
        self.ensure_core_defaults()
        skill_data = dict(data) if isinstance(data, Mapping) else {}
        default_rank = self.get_skill_baseline(skill_name)
        self.update_skill(
            skill_name,
            rank=skill_data.get("rank", default_rank),
            mindstate=skill_data.get("mindstate", 0),
        )

    def get_skill_rank(self, skill_name):
        self.ensure_core_defaults()
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        legacy_skill = (self.db.skills or {}).get(normalized, {})
        legacy_rank = int((legacy_skill or {}).get("rank", 0) or 0) if isinstance(legacy_skill, Mapping) else 0
        exp_rank = 0
        handler = getattr(self, "exp_skills", None)
        if isinstance(handler, SkillHandler):
            exp_rank = int(getattr(handler.get(normalized), "rank", 0) or 0)
        return max(legacy_rank, exp_rank)

    def get_skill(self, skill_name):
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        return self.get_skill_rank(normalized) + self.get_empath_link_focus_bonus(normalized)

    def get_progression_skill_rank(self, skill_name):
        self.ensure_core_defaults()
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            return 0
        persisted_entry = self._get_exp_skill_store().get(normalized, {})
        if isinstance(persisted_entry, Mapping):
            return max(0, int(persisted_entry.get("rank", 0) or 0))
        return 0

    def format_skill_name(self, skill_name):
        return str(skill_name).replace("_", " ").title()

    def get_skill_metadata(self, skill_name):
        metadata = dict(SKILL_REGISTRY.get(skill_name, {}))
        metadata.setdefault("category", None)
        metadata.setdefault("visibility", "shared")
        metadata.setdefault("guilds", None)
        metadata.setdefault("description", "No description is available yet.")
        metadata.setdefault("starter_rank", 0)
        category = metadata.get("category")
        if category is not None and not normalize_learning_category(category):
            raise ValueError(f"Skill {skill_name} defines an invalid learning category: {category}")
        return metadata

    def normalize_guild_name(self, guild_name):
        normalized = str(guild_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        return normalized or None

    def normalize_profession_name(self, profession_name):
        return resolve_profession_name(profession_name, default=None)

    def is_profession(self, key):
        return self.get_profession() == self.normalize_profession_name(key)

    def get_profession_guild_tag(self):
        return PROFESSION_TO_GUILD.get(self.get_profession())

    def get_subsystem(self):
        profession = self.get_profession()
        controller = getattr(self.ndb, "subsystem_controller", None)

        if not controller or getattr(controller, "profession", None) != profession:
            controller = create_subsystem(profession)
            self.ndb.subsystem_controller = controller

        subsystem = controller.get_state(self)
        self.ndb.subsystem = subsystem
        return subsystem

    def get_profession(self):
        profession = self.normalize_profession_name(getattr(self.db, "profession", None))
        if profession:
            return profession
        legacy = self.normalize_profession_name(getattr(self.db, "guild", None))
        return legacy or DEFAULT_PROFESSION

    def get_profession_key(self):
        return self.get_profession()

    def get_profession_profile(self):
        return get_profession_profile(self.get_profession())

    def get_profession_display_name(self):
        return get_profession_display_name(self.get_profession())

    def get_profession_rank(self):
        return int(getattr(self.db, "profession_rank", 1) or 1)

    def get_profession_rank_label(self):
        return get_profession_rank_label(self.get_profession(), self.get_profession_rank())

    def get_circle(self):
        self.ensure_core_defaults()
        profession = self.get_profession()
        if profession == "warrior":
            return self.get_warrior_circle()
        if profession == "ranger":
            return max(1, int(getattr(self.db, "ranger_circle", getattr(self.db, "circle", 1)) or 1))
        return max(1, int(getattr(self.db, "circle", 1) or 1))

    def get_circle_progression_status(self, enforce_location=None):
        current_circle = self.get_circle()
        next_circle = current_circle + 1
        requirements = get_circle_requirements(next_circle)
        current_ranks = {skill_name: self.get_progression_skill_rank(skill_name) for skill_name in requirements}
        missing_requirements = {
            skill_name: required_rank
            for skill_name, required_rank in requirements.items()
            if int(current_ranks.get(skill_name, 0) or 0) < int(required_rank or 0)
        }
        location_required = is_circle_location_enforced() if enforce_location is None else bool(enforce_location)
        location_ok = True
        location_message = None
        if location_required:
            location_ok, location_message = is_valid_empath_circle_location(self)
        return {
            "current_circle": current_circle,
            "next_circle": next_circle if requirements else None,
            "requirements": requirements,
            "current_ranks": current_ranks,
            "missing_requirements": missing_requirements,
            "location_required": location_required,
            "location_ok": location_ok,
            "location_message": location_message,
            "highest_circle": get_highest_configured_circle(),
        }

    def can_advance_circle(self, enforce_location=None):
        if not self.is_profession("empath"):
            return False, ["Only Empaths can circle this way."], None
        status = self.get_circle_progression_status(enforce_location=enforce_location)
        if not status.get("requirements"):
            return False, ["You have reached the highest configured Empath circle."], status
        reasons = []
        if status.get("location_required") and not status.get("location_ok"):
            reasons.append(status.get("location_message") or "You cannot circle here.")
        for skill_name, required_rank in status.get("missing_requirements", {}).items():
            current_rank = int(status.get("current_ranks", {}).get(skill_name, 0) or 0)
            reasons.append(f"{self.format_skill_name(skill_name)} {current_rank}/{int(required_rank or 0)}")
        return len(reasons) == 0, reasons, status

    def advance_circle(self, enforce_location=None):
        can_advance, reasons, status = self.can_advance_circle(enforce_location=enforce_location)
        if not can_advance:
            if reasons and status and status.get("missing_requirements"):
                return False, ["You are not yet ready to circle.", *reasons], status
            return False, reasons, status
        next_circle = int(status.get("next_circle", self.get_circle() + 1) or (self.get_circle() + 1))
        self.db.circle = max(1, next_circle)
        if hasattr(self, "sync_client_state"):
            self.sync_client_state()
        lines = [f"You advance to Empath Circle {self.db.circle}."]
        lines.append("Your formal circle rises, but your techniques remain tied to your Empathy skill.")
        return True, lines, status

    def set_ranger_circle(self, value):
        amount = max(1, int(value or 1))
        self.db.circle = amount
        self.db.ranger_circle = amount
        if hasattr(self, "sync_client_state"):
            self.sync_client_state()
        return amount

    def get_wilderness_bond(self):
        return max(0, min(100, int(getattr(self.db, "wilderness_bond", 50) or 0)))

    def get_wilderness_bond_profile(self):
        return get_wilderness_bond_profile(self.get_wilderness_bond())

    def get_wilderness_bond_state(self):
        return str(self.get_wilderness_bond_profile().get("key", "attuned") or "attuned")

    def get_nature_focus(self):
        return max(0, min(NATURE_FOCUS_MAX, int(getattr(self.db, "nature_focus", 0) or 0)))

    def set_nature_focus(self, value):
        amount = max(0, min(NATURE_FOCUS_MAX, int(value or 0)))
        self.db.nature_focus = amount
        self.sync_client_state()
        return amount

    def adjust_nature_focus(self, amount):
        return self.set_nature_focus(self.get_nature_focus() + int(amount or 0))

    def get_ranger_focus_gain_bonus(self):
        if not self.is_profession("ranger"):
            return 0
        bonus = 0
        bond = self.get_wilderness_bond()
        if bond >= 80:
            bonus += 2
        elif bond >= 50:
            bonus += 1
        if self.has_active_ranger_companion():
            bonus += 1
        return bonus

    def get_ranger_companion(self):
        companion = normalize_ranger_companion(getattr(self.db, "ranger_companion", None))
        self.db.ranger_companion = companion
        return companion

    def set_ranger_companion(self, data):
        companion = normalize_ranger_companion(data)
        self.db.ranger_companion = companion
        self.sync_client_state()
        return companion

    def has_active_ranger_companion(self):
        return is_companion_active(self.get_ranger_companion())

    def get_ranger_companion_tracking_bonus(self):
        return int(get_companion_tracking_bonus(self.get_ranger_companion()) or 0)

    def get_ranger_companion_awareness_bonus(self):
        return int(get_companion_awareness_bonus(self.get_ranger_companion()) or 0)

    def get_ranger_companion_label(self):
        return get_companion_label(self.get_ranger_companion())

    def get_active_ranger_beseech(self, kind=None):
        if kind:
            kinds = [str(kind).strip().lower()]
        else:
            kinds = list(get_beseech_kinds())
        now = time.time()
        active = []
        for key in kinds:
            state_key = f"ranger_beseech_{key}"
            data = self.get_state(state_key)
            if not isinstance(data, Mapping):
                continue
            expires_at = float(data.get("expires_at", 0) or 0)
            if expires_at and now >= expires_at:
                self.clear_state(state_key)
                continue
            active.append(dict(data))
        if kind:
            return active[0] if active else None
        return active

    def clear_other_ranger_beseeches(self, allowed_kind=None):
        allowed = str(allowed_kind or "").strip().lower()
        for kind in get_beseech_kinds():
            if kind == allowed:
                continue
            self.clear_state(f"ranger_beseech_{kind}")

    def get_ranger_beseech_bonus(self, bonus_key):
        total = 0
        for effect in self.get_active_ranger_beseech() or []:
            effects = effect.get("effects") if isinstance(effect, Mapping) else None
            if isinstance(effects, Mapping):
                total += int(effects.get(bonus_key, 0) or 0)
        return total

    def get_ranger_mark_effect_on(self):
        data = self.get_state("ranger_marked")
        if not isinstance(data, Mapping):
            return None
        expires_at = float(data.get("expires_at", 0) or 0)
        if expires_at and time.time() >= expires_at:
            self.clear_state("ranger_marked")
            return None
        return dict(data)

    def get_ranger_mark_tracking_bonus(self, target=None):
        if not target or not hasattr(target, "get_ranger_mark_effect_on"):
            return 0
        effect = target.get_ranger_mark_effect_on()
        if not isinstance(effect, Mapping):
            return 0
        return int(effect.get("tracking_bonus", 0) or 0)

    def get_ranger_environment_type(self):
        room = getattr(self, "location", None)
        if room and hasattr(room, "get_environment_type"):
            return room.get_environment_type()
        return "urban"

    def get_ranger_terrain_type(self):
        room = getattr(self, "location", None)
        if room and hasattr(room, "get_terrain_type"):
            return room.get_terrain_type()
        environment = self.get_ranger_environment_type()
        if environment == "wilderness":
            return "forest"
        return environment

    def is_favorable_ranger_terrain(self):
        terrain = self.get_ranger_terrain_type()
        environment = self.get_ranger_environment_type()
        return terrain in NATURAL_TERRAIN_TYPES or environment in {"wilderness", "coastal"}

    def is_hostile_ranger_terrain(self):
        return self.get_ranger_terrain_type() == "urban" or self.get_ranger_environment_type() == "urban"

    def get_ranger_tracking_bonus(self):
        if not self.is_profession("ranger"):
            return 0
        state = self.get_wilderness_bond_state()
        bonus = int(TRACKING_BONUSES.get(state, 0) or 0)
        bonus += int(TERRAIN_TRACKING_BONUSES.get(self.get_ranger_terrain_type(), 0) or 0)
        if self.is_favorable_ranger_terrain():
            if state == "attuned":
                bonus += 3
            elif state == "wildbound":
                bonus += 6
        elif self.is_hostile_ranger_terrain():
            if state == "distant":
                bonus -= 2
            elif state == "disconnected":
                bonus -= 6
        bonus += self.get_ranger_companion_tracking_bonus()
        bonus += self.get_ranger_beseech_bonus("tracking_bonus")
        return bonus

    def get_ranger_stealth_bonus(self):
        if not self.is_profession("ranger"):
            return 0
        state = self.get_wilderness_bond_state()
        bonus = int(STEALTH_BONUSES.get(state, 0) or 0)
        bonus += int(TERRAIN_STEALTH_BONUSES.get(self.get_ranger_terrain_type(), 0) or 0)
        if self.is_favorable_ranger_terrain():
            if state == "attuned":
                bonus += 2
            elif state == "wildbound":
                bonus += 4
        elif self.is_hostile_ranger_terrain():
            if state == "distant":
                bonus -= 1
            elif state == "disconnected":
                bonus -= 4
        bonus += self.get_ranger_beseech_bonus("stealth_bonus")
        return bonus

    def get_ranger_perception_bonus(self):
        if not self.is_profession("ranger"):
            return 0
        state = self.get_wilderness_bond_state()
        bonus = int(PERCEPTION_BONUSES.get(state, 0) or 0)
        if self.is_favorable_ranger_terrain():
            if state == "attuned":
                bonus += 1
            elif state == "wildbound":
                bonus += 3
        elif self.is_hostile_ranger_terrain() and state == "disconnected":
            bonus -= 2
        bonus += self.get_ranger_companion_awareness_bonus()
        return bonus

    def get_ranger_trail_read_bonus(self, trail=None):
        if not self.is_profession("ranger"):
            return 0
        state = self.get_wilderness_bond_state()
        bonus = {
            "disconnected": -12,
            "distant": -5,
            "attuned": 8,
            "wildbound": 15,
        }.get(state, 0)
        if self.is_favorable_ranger_terrain():
            bonus += 4
        elif self.is_hostile_ranger_terrain():
            bonus -= 4
        bonus += int(self.get_ranger_instinct() / 12)
        return bonus

    def get_ranger_tracking_depth(self):
        score = self.get_ranger_trail_read_bonus() + self.get_ranger_tracking_bonus()
        if score >= 30:
            return "keen"
        if score >= 15:
            return "clear"
        if score >= 0:
            return "standard"
        return "vague"

    def get_ranger_aim_stability_bonus(self):
        if not self.is_profession("ranger"):
            return 0
        state = self.get_wilderness_bond_state()
        bonus = {
            "disconnected": -10,
            "distant": -4,
            "attuned": 6,
            "wildbound": 12,
        }.get(state, 0)
        if self.is_favorable_ranger_terrain():
            bonus += 5
        elif self.is_hostile_ranger_terrain():
            bonus -= 5
        return bonus

    def get_ranger_snipe_retention_bonus(self):
        if not self.is_profession("ranger"):
            return 0
        state = self.get_wilderness_bond_state()
        bonus = int(TERRAIN_SNIPE_RETENTION_BONUSES.get(self.get_ranger_terrain_type(), 0) or 0)
        bonus += {
            "disconnected": -12,
            "distant": -5,
            "attuned": 6,
            "wildbound": 12,
        }.get(state, 0)
        if self.is_favorable_ranger_terrain() and state in {"attuned", "wildbound"}:
            bonus += 4
        elif self.is_hostile_ranger_terrain() and state in {"distant", "disconnected"}:
            bonus -= 4
        bonus += self.get_ranger_beseech_bonus("stealth_retention_bonus")
        if self.get_wilderness_bond() >= int(RANGER_SNIPE_CONFIG.get("mastery_bond_threshold", 80) or 80) and self.get_nature_focus() >= int(RANGER_SNIPE_CONFIG.get("mastery_focus_threshold", 60) or 60):
            bonus += int(RANGER_SNIPE_CONFIG.get("mastery_retention_bonus", 10) or 10)
        return bonus

    def get_ranger_aim_focus_accuracy_bonus(self):
        return int(self.get_nature_focus() / max(1, int(RANGER_SNIPE_CONFIG.get("focus_accuracy_scale", 12) or 12)))

    def get_ranger_aim_focus_damage_multiplier(self):
        return 1.0 + (self.get_nature_focus() / max(1, float(RANGER_SNIPE_CONFIG.get("focus_damage_scale", 20) or 20))) * 0.05

    def get_ranger_bond_accuracy_bonus(self):
        bond = max(0, self.get_wilderness_bond() - 50)
        return int(bond / max(1, int(RANGER_SNIPE_CONFIG.get("bond_accuracy_scale", 8) or 8)))

    def can_beseech_ranger_aspect(self, kind):
        profile = get_beseech_profile(kind)
        if not profile:
            return False, "You do not know how to call that aspect."
        requirement = str(profile.get("requires", "") or "").strip().lower()
        terrain = self.get_ranger_terrain_type()
        environment = self.get_ranger_environment_type()
        if requirement == "airflow":
            valid = environment != "underground"
        elif requirement == "natural":
            valid = terrain in NATURAL_TERRAIN_TYPES
        elif requirement == "open_sky":
            valid = environment in {"wilderness", "coastal"} and terrain != "underground"
        else:
            valid = True
        if not valid:
            return False, "There is nothing here to answer your call."
        return True, ""

    def beseech_ranger_aspect(self, kind):
        if not self.is_profession("ranger"):
            return False, "That call goes unanswered."
        profile = get_beseech_profile(kind)
        if not profile:
            return False, "Beseech what? Choose wind, earth, or sky."
        ok, message = self.can_beseech_ranger_aspect(kind)
        if not ok:
            return False, message
        cost = int(profile.get("cost", 0) or 0)
        if self.get_nature_focus() < cost:
            return False, "You do not have enough nature focus to call on that power."
        duration = int(profile.get("duration", 15) or 15)
        effect = {
            "kind": str(kind).strip().lower(),
            "effects": dict(profile.get("effects") or {}),
            "duration": duration,
            "expires_at": time.time() + duration,
            "timestamp": time.time(),
        }
        self.clear_other_ranger_beseeches(allowed_kind=effect["kind"])
        self.adjust_nature_focus(-cost)
        self.set_state(f"ranger_beseech_{effect['kind']}", effect)
        if getattr(self, "location", None):
            room_message = str(profile.get("room_message", "") or "")
            if room_message:
                self.location.msg_contents(room_message.format(name=self.key), exclude=[self])
        return True, str(profile.get("self_message", "You call, and something in the land answers."))

    def focus_ranger_nature(self):
        if not self.is_profession("ranger"):
            return False, "You cannot gather that kind of focus."
        if getattr(self.db, "in_combat", False):
            return False, "You need a quiet moment before drawing in the land's focus."
        gain = int(NATURE_FOCUS_ACTION_GAINS.get("focus", 12) or 12) + self.get_ranger_focus_gain_bonus()
        if self.is_favorable_ranger_terrain():
            gain += 3
        elif self.is_hostile_ranger_terrain():
            gain = max(4, gain - 4)
        before = self.get_nature_focus()
        after = self.adjust_nature_focus(gain)
        if after == before:
            return True, "Your nature focus is already at its peak."
        return True, "You settle your breathing and draw in the living pulse of the land."

    def gain_ranger_nature_focus(self, source, base_amount=None):
        if not self.is_profession("ranger"):
            return 0
        amount = int(base_amount if base_amount is not None else NATURE_FOCUS_ACTION_GAINS.get(source, 0) or 0)
        if amount <= 0:
            return 0
        amount += self.get_ranger_focus_gain_bonus()
        if self.is_favorable_ranger_terrain():
            amount += 1
        elif self.is_hostile_ranger_terrain():
            amount = max(1, amount - 2)
        before = self.get_nature_focus()
        after = self.adjust_nature_focus(amount)
        return after - before

    def set_wilderness_bond(self, value, emit_messages=True):
        previous = self.get_wilderness_bond_profile()
        amount = max(0, min(100, int(value or 0)))
        self.db.wilderness_bond = amount
        current = self.get_wilderness_bond_profile()
        if emit_messages and current.get("key") != previous.get("key") and self.is_profession("ranger"):
            messages = {
                "wildbound": "You feel deeply rooted in the wild.",
                "attuned": "You feel closer to the wild.",
                "distant": "The city presses in around you.",
                "disconnected": "The wild does not follow.",
            }
            message = messages.get(current.get("key"))
            if message:
                self.msg(message)
        self.sync_client_state()
        return amount

    def adjust_wilderness_bond(self, amount, emit_messages=True):
        return self.set_wilderness_bond(self.get_wilderness_bond() + int(amount or 0), emit_messages=emit_messages)

    def get_ranger_instinct(self):
        return max(int(getattr(self.db, "ranger_instinct", 0) or 0), int(self.get_skill("instinct") or 0))

    def tick_ranger_state(self):
        if not self.is_profession("ranger"):
            return False
        room = getattr(self, "location", None)
        if not room or not hasattr(room, "get_environment_type"):
            return False
        environment = room.get_environment_type()
        delta = int(ENVIRONMENT_BOND_DELTAS.get(environment, 0) or 0)
        focus_delta = int(ENVIRONMENT_NATURE_FOCUS_DELTAS.get(environment, 0) or 0)
        if hasattr(room, "get_terrain_type"):
            terrain = room.get_terrain_type()
            if terrain in NATURAL_TERRAIN_TYPES and delta > 0:
                delta += 1
                if focus_delta > 0:
                    focus_delta += 1
            elif terrain == "urban" and delta < 0:
                delta -= 1
                if focus_delta < 0:
                    focus_delta -= 1
        if self.has_active_ranger_companion():
            if delta > 0:
                delta += 1
            elif delta < 0:
                delta += 1
        if focus_delta > 0:
            focus_delta += self.get_ranger_focus_gain_bonus()
        elif focus_delta < 0 and self.get_wilderness_bond() >= 80:
            focus_delta += 1
        before = self.get_wilderness_bond()
        after = self.set_wilderness_bond(before + delta) if delta else before
        before_focus = self.get_nature_focus()
        after_focus = self.set_nature_focus(before_focus + focus_delta) if focus_delta else before_focus
        now = time.time()
        for kind in get_beseech_kinds():
            state_key = f"ranger_beseech_{kind}"
            data = self.get_state(state_key)
            if not isinstance(data, Mapping):
                continue
            if now >= float(data.get("expires_at", 0) or 0):
                self.clear_state(state_key)
        return before != after or before_focus != after_focus

    def resolve_ranger_track_target(self, target_name):
        target = self.search(str(target_name or "").strip(), global_search=True)
        if not target:
            return None, "You cannot find any sign of that quarry."
        if not hasattr(target, "location") or not getattr(target, "location", None):
            return None, "That trail goes cold immediately."
        if target == self:
            return None, "You already know where you stand."
        if not bool(getattr(target.db, "is_npc", False)):
            return None, "You cannot yet track other adventurers that way."
        return target, ""

    def attempt_ranger_track(self, target_name):
        if not self.is_profession("ranger"):
            return False, "You lack the instincts to follow that trail."
        target, message = self.resolve_ranger_track_target(target_name)
        if not target:
            return False, message
        room = getattr(self, "location", None)
        if not room or not hasattr(room, "get_trails_for_target"):
            return False, "You cannot make sense of the ground here."
        trails = room.get_trails_for_target(target)
        if not trails:
            return False, "You fail to find any clear sign of their passage."
        trail = trails[0]
        environment = room.get_environment_type() if hasattr(room, "get_environment_type") else "urban"
        difficulty = int(TRACK_DIFFICULTY_BASE.get(environment, 50) or 50)
        strength = int(trail.get("effective_strength", trail.get("strength", 0)) or 0)
        score = self.get_ranger_instinct() + self.get_ranger_tracking_bonus() + self.get_ranger_mark_tracking_bonus(target) + strength
        if score < difficulty:
            if self.get_ranger_tracking_depth() == "vague":
                return False, "You find broken hints of passage, but the land refuses to give you a clear read."
            return False, "You find scraps of sign, but not enough to follow with confidence."
        direction = str(trail.get("direction", "") or "").strip().lower()
        if not direction:
            return False, "The trail twists into confusion."
        quality = ""
        if hasattr(room, "describe_trail"):
            trail_entry = dict(trail)
            trail_entry["apparent_strength"] = strength + self.get_ranger_trail_read_bonus(trail)
            quality = room.describe_trail(trail_entry, observer=self)
        self.set_state(
            "last_track",
            {
                "target": target.key,
                "direction": direction,
                "timestamp": time.time(),
            },
        )
        if quality:
            depth = self.get_ranger_tracking_depth()
            self.gain_ranger_nature_focus("track")
            if depth == "keen":
                return True, f"{quality} You read the pace of the trail clearly enough to press on without hesitation."
            if depth == "clear":
                return True, f"{quality} The nearby ground still speaks plainly."
            return True, quality
        return True, f"You find signs leading {direction}."

    def attempt_ranger_hunt(self):
        if not self.is_profession("ranger"):
            return False, ["You do not know how to read the nearby signs of life."]
        room = getattr(self, "location", None)
        if not room:
            return False, ["There is nowhere here to hunt."]
        sightings = []
        for obj in getattr(room, "contents", []):
            if obj != self and bool(getattr(obj.db, "is_npc", False)) and getattr(obj.db, "hp", None) is not None:
                sightings.append("You sense game close at hand.")
                break
        if not sightings:
            for exit_obj in room.contents_get(content_type="exit"):
                destination = getattr(exit_obj, "destination", None)
                if not destination:
                    continue
                if any(bool(getattr(obj.db, "is_npc", False)) and getattr(obj.db, "hp", None) is not None for obj in getattr(destination, "contents", [])):
                    sightings.append(f"You catch signs of life to the {str(getattr(exit_obj, 'key', '') or '').lower()}.")
        if not sightings:
            return False, ["You scan the area for signs of life but find nothing convincing."]
        return True, ["You scan the area for signs of life.", *sightings]

    def attempt_ranger_scout(self):
        if not self.is_profession("ranger"):
            return False, ["You do not know what signs to scout for."]
        room = getattr(self, "location", None)
        if not room:
            return False, ["You cannot scout from here."]
        visible_trails = room.get_visible_trails_for(self) if hasattr(room, "get_visible_trails_for") else []
        if not visible_trails:
            return True, ["You scout the area but find no obvious trail signs."]

        lines = ["You scout the area and notice:"]
        for trail in visible_trails[:3]:
            if hasattr(room, "describe_trail"):
                lines.append(room.describe_trail(trail, observer=self))
            else:
                lines.append(f"Tracks lead {trail.get('direction', 'somewhere')}.")
        self.adjust_wilderness_bond(1)
        self.gain_ranger_nature_focus("scout")
        return True, lines

    def attempt_ranger_follow_trail(self, target_name):
        if not self.is_profession("ranger"):
            return False, "You do not know how to follow trails that way."
        room = getattr(self, "location", None)
        if not room:
            return False, "There is nowhere here to follow a trail."
        trails = room.get_trails_for_target(target_name) if hasattr(room, "get_trails_for_target") else []
        if not trails:
            return False, f"You cannot find a trail for {target_name}."

        trail = trails[0]
        strength = int(trail.get("effective_strength", trail.get("strength", 0)) or 0)
        difficulty = max(10, 60 - strength)
        score = self.get_ranger_instinct() + self.get_ranger_tracking_bonus() + random.randint(1, 30)
        if score < difficulty:
            return False, "You lose the trail before it reveals the way onward."

        direction = str(trail.get("direction", "") or "").strip().lower()
        if not direction:
            return False, "The trail is too muddled to follow."

        exit_obj = None
        for candidate in room.contents_get(content_type="exit"):
            aliases = [alias.lower() for alias in getattr(candidate.aliases, "all", lambda: [])()]
            if candidate.key.lower() == direction or direction in aliases:
                exit_obj = candidate
                break
        if not exit_obj or not getattr(exit_obj, "destination", None):
            return False, "The trail points onward, but you cannot continue from here."

        destination = exit_obj.destination
        room.msg_contents(f"$You() follow a trail {direction}.", from_obj=self, exclude=[self])
        self.move_to(destination, quiet=True, move_type="follow")
        self.adjust_wilderness_bond(1)
        self.gain_ranger_nature_focus("follow_trail")
        self.set_state(
            "last_track",
            {
                "target": str(trail.get("target_key", target_name) or target_name),
                "direction": direction,
                "timestamp": time.time(),
            },
        )
        return True, f"You follow the trail {direction} into {destination.get_display_name(self)}."

    def begin_covering_tracks(self):
        if not self.is_profession("ranger"):
            return False, "You do not know how to mask your trail."
        self.set_state(
            "ranger_cover_tracks",
            {
                "strength_penalty": 25,
                "timestamp": time.time(),
            },
        )
        self.adjust_wilderness_bond(1)
        return True, "You begin masking your tracks as you move."

    def attempt_ranger_pounce(self, target_name):
        if not self.is_profession("ranger"):
            return False, "You do not know how to strike from the trail.", False
        if not self.is_hidden():
            return False, "You need to be hidden before you can pounce.", False
        room = getattr(self, "location", None)
        target = self.search(str(target_name or "").strip(), candidates=getattr(room, "contents", None)) if room else None
        if not target:
            return False, "Pounce whom?", False
        if target == self:
            return False, "You cannot pounce on yourself.", False

        last_track = self.get_state("last_track")
        tracked_name = str(last_track.get("target", "") or "") if isinstance(last_track, dict) else ""
        if tracked_name and tracked_name.lower() != target.key.lower():
            return False, f"You have not been tracking {target.key} closely enough to pounce.", False

        self.set_target(target)
        self.set_state(
            "ranger_pounce",
            {
                "target_id": target.id,
                "accuracy_bonus": 20,
                "damage_bonus": 0.25,
                "timestamp": time.time(),
            },
        )
        self.clear_state("ranger_cover_tracks")
        return True, f"You coil low and surge toward {target.key} from hiding.", True

    def has_ranged_weapon_equipped(self):
        weapon = self.get_wielded_weapon() if hasattr(self, "get_wielded_weapon") else self.get_weapon()
        if not weapon:
            return False
        if bool(getattr(weapon.db, "is_ranged", False)):
            return True
        return bool(str(getattr(weapon.db, "weapon_range_type", None) or "").strip().lower())

    def get_equipped_ranged_weapon(self):
        if self.has_ranged_weapon_equipped():
            return self.get_wielded_weapon() if hasattr(self, "get_wielded_weapon") else self.get_weapon()
        return None

    def get_equipped_ammo_state(self):
        weapon = self.get_equipped_ranged_weapon()
        if not weapon:
            return None
        return {
            "loaded": bool(getattr(weapon.db, "ammo_loaded", False)),
            "ammo_type": str(getattr(weapon.db, "ammo_type", "arrow") or "arrow").strip().lower(),
            "weapon": weapon,
        }

    def load_ranged_weapon(self, weapon_name=""):
        weapon = self.get_equipped_ranged_weapon()
        if weapon_name:
            weapon = self.search(weapon_name, candidates=[obj for obj in self.contents if getattr(obj.db, "item_type", None) == "weapon" or obj == weapon])
            if not weapon:
                return False, "You do not have that weapon."
        if not weapon or not (bool(getattr(weapon.db, "is_ranged", False)) or getattr(weapon.db, "weapon_range_type", None)):
            return False, "That weapon cannot be loaded."
        if bool(getattr(weapon.db, "ammo_loaded", False)):
            return False, f"{weapon.key} is already loaded."
        if getattr(weapon.db, "ammo_type", None) is None:
            weapon.db.ammo_type = "arrow"
        weapon.db.ammo_loaded = True
        return True, f"You load {weapon.key}."

    def consume_loaded_ammo(self):
        weapon = self.get_equipped_ranged_weapon()
        if not weapon or not bool(getattr(weapon.db, "ammo_loaded", False)):
            return False
        weapon.db.ammo_loaded = False
        return True

    def get_ranger_aim_data(self):
        data = self.get_state("ranger_aiming")
        return dict(data) if isinstance(data, Mapping) else None

    def get_ranger_aim_stacks(self, target=None):
        data = self.get_ranger_aim_data()
        if not data:
            return 0
        if target is not None and data.get("target_id") != getattr(target, "id", None):
            return 0
        return max(0, int(data.get("stacks", 0) or 0))

    def build_ranger_aim(self, target):
        if not target:
            return False, "Aim at whom?"
        if not self.has_ranged_weapon_equipped():
            return False, "You need a ranged weapon ready before aiming."
        data = self.get_ranger_aim_data() or {}
        stacks = min(3, int(data.get("stacks", 0) or 0) + 1) if data.get("target_id") == target.id else 1
        self.db.aiming = target.id
        self.set_state("aiming", target.id)
        self.set_state("ranger_aiming", {"target_id": target.id, "stacks": stacks, "timestamp": time.time()})
        sync_direct_interest(self, [target], channel="aim")
        return True, stacks

    def maybe_break_ranger_aim_on_hit(self, damage_amount):
        aim_data = self.get_ranger_aim_data()
        if not aim_data:
            return False
        chance = min(85, 30 + max(0, int(damage_amount or 0)) * 5)
        chance -= self.get_ranger_aim_stability_bonus()
        chance = max(10, min(90, chance))
        if random.randint(1, 100) > chance:
            return False
        self.clear_aim()
        self.msg("The impact ruins your carefully lined-up aim.")
        return True

    def get_ranger_keep_distance_bonus(self):
        if not self.is_profession("ranger"):
            return 0
        bonus = 5
        if self.has_ranged_weapon_equipped():
            bonus += 10
        bonus += max(0, int((self.get_wilderness_bond() - 50) / 10))
        if self.is_favorable_ranger_terrain():
            bonus += 5
        return bonus

    def attempt_ranger_blend(self):
        if not self.is_profession("ranger"):
            return False, "You do not know how to blend into the land."
        room = getattr(self, "location", None)
        if not room:
            return False, "You have nowhere to draw cover from here."
        pressure_penalty = self.get_pressure_level() if hasattr(self, "get_pressure_level") else 0
        score = self.get_stealth_total() + self.get_ranger_instinct() + random.randint(1, 40) - pressure_penalty
        difficulty = 70
        if self.is_favorable_ranger_terrain():
            difficulty -= 12
        elif self.is_hostile_ranger_terrain():
            difficulty += 12
        if getattr(self.db, "in_combat", False):
            difficulty += 8
        if score < difficulty:
            return False, "You reach for nearby cover, but nothing around you is enough to hide your movement."
        current_hidden = self.get_hidden_strength() if self.is_hidden() else 0
        hidden_strength = 18 + max(0, self.get_ranger_stealth_bonus()) + int(self.get_wilderness_bond() / 10)
        hidden_strength = max(current_hidden + 8, hidden_strength)
        self.set_state(
            "hidden",
            {
                "strength": hidden_strength,
                "timestamp": time.time(),
                "source": "blend",
            },
        )
        self.adjust_wilderness_bond(1)
        self.gain_ranger_nature_focus("blend")
        return True, "You draw into the natural cover around you."

    def attempt_ranger_read_land(self):
        if not self.is_profession("ranger"):
            return False, ["You do not know how to listen to the land that way."]
        room = getattr(self, "location", None)
        if not room:
            return False, ["You cannot read anything from here."]
        terrain = get_terrain_label(self.get_ranger_terrain_type())
        environment = self.get_ranger_environment_type().title()
        lines = ["The land is alive with subtle movement."]
        lines.append(f"Environment: {environment}. Terrain: {terrain}.")

        tracking_bonus = self.get_ranger_tracking_bonus()
        stealth_bonus = self.get_ranger_stealth_bonus()
        retention_bonus = self.get_ranger_snipe_retention_bonus()
        if tracking_bonus >= 12:
            lines.append("Tracks are easier to follow here.")
        elif tracking_bonus <= -4:
            lines.append("The ground fights you, blurring spoor and passage.")
        if stealth_bonus >= 8:
            lines.append("The cover here rewards patience and stillness.")
        elif stealth_bonus <= -3:
            lines.append("There is little cover here to hide a careful stalk.")
        if retention_bonus >= 12:
            lines.append("A concealed firing lane could be held here a little longer.")
        elif retention_bonus <= -4:
            lines.append("Any shot taken here is likely to expose you.")

        nearby_creatures = [
            obj for obj in getattr(room, "contents", [])
            if obj != self and bool(getattr(obj.db, "is_npc", False)) and getattr(obj.db, "hp", None) is not None
        ]
        if nearby_creatures:
            lines.append("You sense the presence of nearby creatures moving through the area.")
        else:
            for exit_obj in room.contents_get(content_type="exit"):
                destination = getattr(exit_obj, "destination", None)
                if not destination:
                    continue
                if any(bool(getattr(obj.db, "is_npc", False)) and getattr(obj.db, "hp", None) is not None for obj in getattr(destination, "contents", [])):
                    lines.append(f"The sign of life seems stronger to the {str(getattr(exit_obj, 'key', '') or '').lower()}.")
                    break

        if self.has_active_ranger_companion():
            lines.append(f"Your {self.get_ranger_companion_label().lower()} ranges nearby, sharpening your awareness.")
        self.adjust_wilderness_bond(1 if self.is_favorable_ranger_terrain() else 0)
        self.gain_ranger_nature_focus("read_land")
        return True, lines

    def call_ranger_companion(self):
        if not self.is_profession("ranger"):
            return False, "You have no bond to call upon."
        if self.is_hostile_ranger_terrain():
            return False, "The press of the city keeps your companion away."
        companion = self.get_ranger_companion()
        if companion.get("state") == "active":
            return False, f"Your {self.get_ranger_companion_label().lower()} is already with you."
        companion["state"] = "active"
        companion["bond"] = min(100, int(companion.get("bond", 50) or 0) + 2)
        self.set_ranger_companion(companion)
        self.adjust_wilderness_bond(2)
        return True, f"A {self.get_ranger_companion_label().lower()} emerges from the brush and joins you."

    def dismiss_ranger_companion(self):
        if not self.is_profession("ranger"):
            return False, "You have no companion to dismiss."
        companion = self.get_ranger_companion()
        if companion.get("state") != "active":
            return False, "Your companion is not currently with you."
        companion["state"] = "inactive"
        self.set_ranger_companion(companion)
        return True, f"Your {self.get_ranger_companion_label().lower()} slips back into the wild."

    def attempt_ranger_reposition(self):
        if not self.is_profession("ranger"):
            return False, "You do not know how to reposition through a fight."
        target = self.get_target() if hasattr(self, "get_target") else None
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "You need an active opponent to reposition around."
        current_range = self.get_range(target)
        pressure_penalty = self.get_pressure_level() if hasattr(self, "get_pressure_level") else 0
        score = self.get_stat("agility") + self.get_ranger_keep_distance_bonus() + random.randint(1, 100) - pressure_penalty
        enemy_score = target.get_stat("reflex") + random.randint(1, 100)
        if hasattr(target, "get_pressure"):
            enemy_score += int(target.get_pressure(self) * 0.25)

        if score > enemy_score + 15:
            desired_range = "far" if current_range != "far" else "far"
            self.set_range(target, desired_range)
            hide_roll = random.randint(1, 100) + self.get_ranger_keep_distance_bonus()
            if hide_roll >= 70:
                self.set_state("hidden", {"strength": 20 + self.get_ranger_aim_stacks(target) * 5, "timestamp": time.time()})
                return True, f"You slip away from {target.key}, widen the distance, and vanish from clear sight."
            return True, f"You reposition away from {target.key} and open the range to {desired_range}."
        if score > enemy_score:
            self.set_range(target, "near")
            return True, f"You shift your footing and keep {target.key} from closing fully."
        return False, f"You fail to carve out a better firing lane against {target.key}."

    def prepare_ranger_snipe(self, target_name):
        if not self.is_profession("ranger"):
            return False, "You do not know how to snipe.", False
        if not self.is_hidden():
            return False, "You are not properly positioned to snipe.", False
        weapon = self.get_equipped_ranged_weapon()
        if not weapon or not bool(getattr(weapon.db, "ammo_loaded", False)):
            return False, "You are not properly positioned to snipe.", False
        room = getattr(self, "location", None)
        target = self.search(str(target_name or "").strip(), candidates=getattr(room, "contents", None)) if room else None
        if not target:
            return False, "Snipe whom?", False
        aim_stacks = self.get_ranger_aim_stacks(target)
        accuracy_bonus = 25 + (aim_stacks * 8) + self.get_ranger_bond_accuracy_bonus() + self.get_ranger_aim_focus_accuracy_bonus()
        damage_multiplier = (1.35 + (aim_stacks * 0.1)) * self.get_ranger_aim_focus_damage_multiplier()
        self.set_target(target)
        self.set_state(
            "ranger_snipe",
            {
                "target_id": target.id,
                "accuracy_bonus": accuracy_bonus,
                "damage_multiplier": damage_multiplier,
                "stealth_bonus": 10 + (aim_stacks * 8),
                "timestamp": time.time(),
            },
        )
        return True, "You release a carefully placed shot from concealment.", True

    def apply_ranger_mark(self, target):
        if not self.is_profession("ranger"):
            return False, "You do not know how to mark prey that way."
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        if target == self:
            return False, "You already know your own movements."
        duration = 18
        mark_state = {
            "source_id": self.id,
            "source_key": self.key,
            "accuracy_bonus": 10,
            "tracking_bonus": 12,
            "expires_at": time.time() + duration,
            "timestamp": time.time(),
        }
        target.set_state("ranger_marked", mark_state)
        self.db.marked_target = target.id
        self.db.mark_data = {"kind": "ranger", "timestamp": time.time()}
        return True, f"You mark your target, revealing {target.key}'s movements."

    def get_warrior_circle(self):
        return max(1, int(getattr(self.db, "warrior_circle", 1) or 1))

    def get_unlocked_warrior_abilities(self):
        return list(getattr(self.db, "unlocked_warrior_abilities", None) or [])

    def get_unlocked_warrior_passives(self):
        return list(getattr(self.db, "unlocked_warrior_passives", None) or [])

    def has_warrior_passive(self, passive_key):
        if not self.is_profession("warrior"):
            return False
        return passive_key in set(self.get_unlocked_warrior_passives())

    def get_max_war_tempo(self):
        return max(0, int(getattr(self.db, "max_war_tempo", 100) or 100))

    def get_war_tempo(self):
        return max(0, int(getattr(self.db, "war_tempo", 0) or 0))

    def get_war_tempo_state(self):
        state = str(getattr(self.db, "war_tempo_state", "calm") or "calm").strip().lower()
        if state in {"calm", "building", "surging", "frenzied"}:
            return state
        return "calm"

    def update_war_tempo_state(self):
        tempo = self.get_war_tempo()
        maximum = self.get_max_war_tempo()
        desired = get_warrior_tempo_state(tempo, maximum)
        active_berserk = self.get_active_warrior_berserk()
        if active_berserk:
            minimum_state = str(active_berserk.get("minimum_state", "building") or "building").strip().lower()
            state_order = {"calm": 0, "building": 1, "surging": 2, "frenzied": 3}
            if state_order.get(desired, 0) < state_order.get(minimum_state, 1):
                desired = minimum_state

        previous = self.get_war_tempo_state()
        if desired == previous:
            return False

        self.db.war_tempo_state = desired
        transition_messages = {
            "building": "You feel the fight rising in you.",
            "surging": "You are fully engaged.",
            "frenzied": "You are on the edge of losing control.",
            "calm": "The rhythm of battle slips away.",
        }
        sessions_attr = getattr(self, "sessions", None)
        if sessions_attr and sessions_attr.count():
            message = transition_messages.get(desired)
            if message:
                self.msg(message)
        return True

    def get_active_warrior_berserk(self):
        data = getattr(self.db, "active_warrior_berserk", None)
        if not isinstance(data, Mapping):
            return None
        key = str(data.get("key", "") or "").strip().lower()
        profile = get_berserk_profile(key)
        if not profile:
            return None
        profile.update(dict(data))
        profile["key"] = key
        return profile

    def get_active_warrior_roars(self):
        active = {}
        for slot, data in dict(getattr(self.db, "active_warrior_roars", None) or {}).items():
            if not isinstance(data, Mapping):
                continue
            profile = get_roar_profile(data.get("key"))
            if not profile:
                continue
            merged = dict(profile)
            merged.update(dict(data))
            active[str(slot)] = merged
        return active

    def get_exhaustion(self):
        return max(0, min(100, int(getattr(self.db, "exhaustion", 0) or 0)))

    def get_exhaustion_profile(self):
        return get_exhaustion_profile(self.get_exhaustion())

    def get_exhaustion_stage(self):
        return str(self.get_exhaustion_profile().get("key", "fresh") or "fresh")

    def set_exhaustion(self, value, emit_messages=True, sync=True):
        previous = self.get_exhaustion_profile()
        amount = max(0, min(100, int(value or 0)))
        self.db.exhaustion = amount
        current = self.get_exhaustion_profile()

        states = dict(getattr(self.db, "states", None) or {})
        is_overextended = amount >= 90
        if is_overextended:
            states["warrior_overextended"] = {"started_at": time.time()}
        else:
            states.pop("warrior_overextended", None)
        self.db.states = states

        if emit_messages and current.get("key") != previous.get("key"):
            messages = {
                "strained": "The fight starts to weigh on you.",
                "faltering": "Your breathing turns ragged.",
                "severe": "Your limbs feel heavy and slow.",
                "collapse": "You are on the verge of collapse.",
                "fresh": "You regain your wind.",
            }
            message = messages.get(current.get("key"))
            if message:
                self.msg(message)

        if sync:
            self.sync_client_state()
        return amount

    def add_exhaustion(self, amount, emit_messages=True, sync=True):
        return self.set_exhaustion(self.get_exhaustion() + int(amount or 0), emit_messages=emit_messages, sync=sync)

    def get_exhaustion_fatigue_multiplier(self):
        return float(self.get_exhaustion_profile().get("fatigue_multiplier", 1.0) or 1.0)

    def get_exhaustion_tempo_gain_multiplier(self):
        return float(self.get_exhaustion_profile().get("tempo_gain_multiplier", 1.0) or 1.0)

    def get_exhaustion_balance_penalty(self):
        return int(self.get_exhaustion_profile().get("balance_recovery_penalty", 0) or 0)

    def get_exhaustion_accuracy_penalty(self):
        return int(self.get_exhaustion_profile().get("accuracy_penalty", 0) or 0)

    def get_exhaustion_defense_penalty(self):
        return int(self.get_exhaustion_profile().get("defense_penalty", 0) or 0)

    def get_overextended_action_delay_chance(self):
        return float(self.get_exhaustion_profile().get("action_delay_chance", 0.0) or 0.0)

    def get_collapse_chance(self):
        return float(self.get_exhaustion_profile().get("collapse_chance", 0.0) or 0.0)

    def is_warrior_overextended(self):
        return self.get_exhaustion() >= 90

    def recover_warrior_exhaustion(self):
        if self.get_exhaustion() <= 0:
            return False, "You are already breathing steadily."

        reduction = int(EXHAUSTION_GAIN_RATES.get("recover_amount", 0) or 0)
        if getattr(self.db, "in_combat", False):
            reduction = max(10, reduction - 10)
        if hasattr(self, "get_pressure_state") and self.get_pressure_state() == "medium":
            reduction = max(10, reduction - 5)

        before = self.get_exhaustion()
        after = self.set_exhaustion(before - reduction)
        return True, f"You force yourself to slow down and recover. Exhaustion {before} -> {after}."

    def get_warrior_roar_effect(self, key):
        effects = dict(getattr(self.db, "warrior_roar_effects", None) or {})
        effect = effects.get(str(key or "").strip().lower())
        if not isinstance(effect, Mapping):
            return None
        expires_at = float(effect.get("expires_at", 0) or 0)
        if expires_at and time.time() >= expires_at:
            effects.pop(str(key or "").strip().lower(), None)
            self.db.warrior_roar_effects = effects
            return None
        return dict(effect)

    def apply_warrior_roar_effect(self, key, data):
        effects = dict(getattr(self.db, "warrior_roar_effects", None) or {})
        effects[str(key or "").strip().lower()] = dict(data or {})
        self.db.warrior_roar_effects = effects

    def get_available_warrior_roars(self):
        unlocked = set(self.get_unlocked_warrior_abilities())
        available = []
        for roar_key, data in ROAR_DATA.items():
            if data.get("foundation") in unlocked:
                available.append(roar_key)
        return sorted(available)

    def get_pressure_level(self):
        return max(0, min(100, int(getattr(self.db, "pressure_level", 0) or 0)))

    def get_pressure_state(self):
        pressure = self.get_pressure_level()
        if pressure >= 85:
            return "extreme"
        if pressure >= 60:
            return "high"
        if pressure >= 30:
            return "medium"
        return "low"

    def set_pressure_level(self, value, emit_messages=True, sync=True):
        previous_state = self.get_pressure_state()
        self.db.pressure_level = max(0, min(100, int(value or 0)))
        current_state = self.get_pressure_state()
        if emit_messages and current_state != previous_state:
            messages = {
                "medium": "You feel uneasy under the pressure.",
                "high": "The fight is getting to you.",
                "extreme": "You hesitate under the assault.",
                "low": "You regain your composure.",
            }
            message = messages.get(current_state)
            if message:
                self.msg(message)
        if sync:
            self.sync_client_state()
        return self.get_pressure_level()

    def add_pressure(self, amount, emit_messages=True, sync=True):
        return self.set_pressure_level(self.get_pressure_level() + int(amount or 0), emit_messages=emit_messages, sync=sync)

    def get_pressure_accuracy_penalty(self):
        penalties = {"low": 0, "medium": 4, "high": 9, "extreme": 14}
        penalty = penalties.get(self.get_pressure_state(), 0)
        if self.has_warrior_passive("overwhelmed_penalty_1"):
            penalty = max(0, penalty - 2)
        return penalty

    def get_pressure_hesitation_chance(self):
        chances = {"low": 0.0, "medium": 0.0, "high": 0.12, "extreme": 0.25}
        chance = float(chances.get(self.get_pressure_state(), 0.0))
        if self.has_warrior_passive("overwhelmed_penalty_1"):
            chance = max(0.0, chance - 0.04)
        return chance

    def get_combat_streak(self):
        return max(0, min(10, int(getattr(self.db, "combat_streak", 0) or 0)))

    def get_combat_rhythm_state(self):
        streak = self.get_combat_streak()
        if streak >= 8:
            return "perfect"
        if streak >= 5:
            return "flowing"
        if streak >= 2:
            return "building"
        return "broken"

    def get_rhythm_break_penalty_active(self):
        return time.time() < float(getattr(self.db, "rhythm_break_until", 0) or 0)

    def get_rhythm_accuracy_bonus(self):
        bonuses = {"broken": 0, "building": 2, "flowing": 4, "perfect": 6}
        bonus = bonuses.get(self.get_combat_rhythm_state(), 0)
        if self.get_rhythm_break_penalty_active():
            bonus = max(-3, bonus - 3)
        return bonus

    def get_rhythm_tempo_bonus(self):
        bonuses = {"broken": 0, "building": 1, "flowing": 3, "perfect": 5}
        bonus = bonuses.get(self.get_combat_rhythm_state(), 0)
        active_roars = self.get_active_warrior_roars()
        group_roar = active_roars.get("group")
        if isinstance(group_roar, Mapping):
            bonus += int(group_roar.get("rhythm_gain_bonus", 0) or 0)
        return bonus

    def get_rhythm_fatigue_discount(self):
        discounts = {"broken": 0, "building": 1, "flowing": 2, "perfect": 3}
        return discounts.get(self.get_combat_rhythm_state(), 0)

    def advance_combat_rhythm(self, hit=False):
        increment = 2 if hit else 1
        active_roars = self.get_active_warrior_roars()
        group_roar = active_roars.get("group")
        if isinstance(group_roar, Mapping):
            increment += int(group_roar.get("rhythm_gain_bonus", 0) or 0)
        self.db.combat_streak = min(10, self.get_combat_streak() + increment)
        self.db.last_combat_action_at = time.time()

    def break_combat_rhythm(self, show_message=True, sync=True):
        if self.get_combat_streak() <= 0:
            return False
        self.db.combat_streak = 0
        self.db.last_combat_action_at = 0
        self.db.rhythm_break_until = time.time() + 10
        if show_message:
            self.msg("You lose your rhythm.")
        if sync:
            self.sync_client_state()
        return True

    def activate_warrior_roar(self, roar_key, target_name=""):
        profile = get_roar_profile(roar_key)
        if not profile:
            return False, "Unknown roar."
        if not self.is_profession("warrior"):
            return False, "Only Warriors can use roars."
        if profile["key"] not in self.get_available_warrior_roars():
            return False, "You have not yet learned that roar."

        tempo_cost = int(profile.get("tempo_cost", 0) or 0)
        if self.get_war_tempo() < tempo_cost:
            return False, "You are not yet worked into a battle state."

        targets = []
        target_scope = str(profile.get("target_scope", "self") or "self")
        if target_scope == "single":
            target = None
            if target_name:
                target = self.search(target_name, location=self.location)
                if not target:
                    return False, "No such target."
            elif hasattr(self, "get_target"):
                target = self.get_target()
            if not target:
                return False, "You need a target for that roar."
            targets = [target]
        elif target_scope == "multi":
            current_target = self.get_target() if hasattr(self, "get_target") else None
            room = getattr(self, "location", None)
            if room:
                for obj in room.contents:
                    if obj == self or not hasattr(obj, "db"):
                        continue
                    if obj == current_target or getattr(obj.db, "target", None) == self:
                        targets.append(obj)
            if not targets and current_target:
                targets = [current_target]

        current_tempo = self.get_war_tempo()
        scale = 1.0 + min(0.5, current_tempo / max(1, self.get_max_war_tempo()))
        self.spend_war_tempo(tempo_cost)

        duration = int(profile.get("duration", 10) or 10)
        if self.has_warrior_passive("roar_duration_1"):
            duration += 3
        expires_at = time.time() + duration
        slot = str(profile.get("slot", "group") or "group")
        active_roars = dict(getattr(self.db, "active_warrior_roars", None) or {})
        active_roars[slot] = {
            "key": profile["key"],
            "expires_at": expires_at,
            "defense_bonus": int(round(float(profile.get("defense_bonus", 0) or 0) * scale)),
            "rhythm_gain_bonus": int(round(float(profile.get("rhythm_gain_bonus", 0) or 0) * scale)),
        }
        self.db.active_warrior_roars = active_roars

        if profile.get("balance_restore"):
            self.set_balance(min(int(self.db.max_balance or 100), int(self.db.balance or 0) + int(round(profile.get("balance_restore", 0) * scale))))
        if profile.get("fatigue_restore"):
            self.set_fatigue(max(0, int(self.db.fatigue or 0) - int(round(profile.get("fatigue_restore", 0) * scale))))

        for target in targets:
            effect_data = {
                "source_id": getattr(self, "id", None),
                "expires_at": expires_at,
                "accuracy_penalty": int(round(float(profile.get("target_accuracy_penalty", 0) or 0) * scale)),
                "balance_recovery_penalty": int(round(float(profile.get("balance_recovery_penalty", 0) or 0) * scale)),
                "challenged_by": getattr(self, "id", None) if profile["key"] == "challenge" else None,
            }
            if hasattr(target, "apply_warrior_roar_effect"):
                target.apply_warrior_roar_effect(profile["key"], effect_data)
            if hasattr(target, "add_pressure"):
                target.add_pressure(int(round(float(profile.get("pressure_gain", 0) or 0) * scale)))

        self.sync_client_state()
        return True, profile.get("start_message") or f"You roar {format_roar_name(profile['key'])}."

    def clear_warrior_berserk(self, show_message=True):
        active = self.get_active_warrior_berserk()
        if not active:
            return False
        self.db.active_warrior_berserk = None
        self.update_war_tempo_state()
        self.sync_client_state()
        if show_message:
            self.msg(active.get("end_message") or "The fury fades, leaving you exposed.")
        return True

    def activate_warrior_berserk(self, berserk_key):
        profile = get_berserk_profile(berserk_key)
        if not profile:
            return False, "Unknown berserk."
        if not self.is_profession("warrior"):
            return False, "Only Warriors can enter a berserk."

        minimum_ratio = float(profile.get("minimum_tempo_ratio", 0.5) or 0.5)
        minimum_tempo = max(1, int(round(self.get_max_war_tempo() * minimum_ratio)))
        if self.get_war_tempo() < minimum_tempo:
            return False, "You are not yet worked into a battle state."

        if self.get_active_warrior_berserk():
            self.clear_warrior_berserk(show_message=False)

        self.db.active_warrior_berserk = {
            "key": profile["key"],
            "started_at": time.time(),
            "drain_per_tick": int(profile.get("drain_per_tick", 1) or 1),
            "minimum_state": profile.get("minimum_state", "building"),
            "end_message": profile.get("end_message") or "The fury fades, leaving you exposed.",
        }
        self.update_war_tempo_state()
        self.sync_client_state()
        self.msg(profile.get("start_message") or "You give yourself over to the rhythm of battle.")
        return True, f"You enter the {profile.get('name', 'Unknown')} berserk."

    def set_war_tempo(self, value, sync=True):
        maximum = self.get_max_war_tempo()
        self.db.war_tempo = max(0, min(maximum, int(value or 0)))
        self.update_war_tempo_state()
        if sync:
            self.sync_client_state()

    def gain_war_tempo(self, amount):
        if not self.is_profession("warrior"):
            return 0
        amount = max(0, int(amount or 0))
        if self.get_war_tempo_state() == "calm" and amount > 0:
            amount = max(1, int(round(amount * 0.6)))
        if self.get_rhythm_break_penalty_active():
            amount = max(1, int(round(amount * 0.6)))
        amount += self.get_rhythm_tempo_bonus()
        if self.has_warrior_passive("tempo_gain_1"):
            amount += 2
        if amount > 0:
            amount = max(1, int(round(amount * self.get_exhaustion_tempo_gain_multiplier())))
        before = self.get_war_tempo()
        self.set_war_tempo(before + amount)
        return self.get_war_tempo() - before

    def spend_war_tempo(self, amount):
        amount = max(0, int(amount or 0))
        before = self.get_war_tempo()
        self.set_war_tempo(before - amount)
        return before - self.get_war_tempo()

    def get_next_warrior_unlocks(self):
        return list(get_next_warrior_unlock(self.get_warrior_circle()))

    def sync_warrior_progression(self, emit_messages=False):
        circle = self.get_warrior_circle()
        current_abilities = self.get_unlocked_warrior_abilities()
        current_passives = self.get_unlocked_warrior_passives()
        desired_abilities = list(get_warrior_abilities_for_circle(circle))
        desired_passives = list(get_warrior_passives_for_circle(circle))
        new_abilities = [key for key in desired_abilities if key not in current_abilities]
        new_passives = [key for key in desired_passives if key not in current_passives]

        self.db.unlocked_warrior_abilities = desired_abilities
        self.db.unlocked_warrior_passives = desired_passives
        self.db.max_war_tempo = max(100, int(getattr(self.db, "max_war_tempo", 100) or 100))
        self.update_war_tempo_state()

        if emit_messages:
            for passive_key in new_passives:
                message = WARRIOR_PASSIVE_DATA.get(passive_key, {}).get("message")
                if message:
                    self.msg(message)
            for ability_key in new_abilities:
                message = WARRIOR_ABILITY_DATA.get(ability_key, {}).get("unlock_message")
                if message:
                    self.msg(message)

        return {"abilities": new_abilities, "passives": new_passives}

    def set_warrior_circle(self, value, emit_messages=False):
        self.db.warrior_circle = max(1, int(value or 1))
        result = self.sync_warrior_progression(emit_messages=emit_messages)
        self.sync_client_state()
        return result

    def gain_warrior_circle(self, amount=1):
        amount = max(1, int(amount or 1))
        self.db.warrior_circle = self.get_warrior_circle() + amount
        return self.sync_warrior_progression(emit_messages=True)

    def get_warrior_help_text(self):
        if not self.is_profession("warrior"):
            return "Warrior progression is only available to members of the Warrior guild."

        categories = {"strikes": [], "roars": [], "survival": []}
        for ability_key in self.get_unlocked_warrior_abilities():
            category = WARRIOR_ABILITY_DATA.get(ability_key, {}).get("category", "strikes")
            categories.setdefault(category, []).append(format_warrior_ability_name(ability_key))

        lines = [
            f"Warrior Circle: {self.get_warrior_circle()}",
            f"War Tempo: {self.get_war_tempo()}/{self.get_max_war_tempo()}",
            f"Tempo State: {format_warrior_tempo_state(self.get_war_tempo_state())}",
            f"Pressure: {self.get_pressure_level()}",
            f"Combat Rhythm: {self.get_combat_rhythm_state().title()}",
            "",
            "Unlocked Warrior Abilities:",
        ]
        active_berserk = self.get_active_warrior_berserk()
        if active_berserk:
            lines.insert(5, f"Active Berserk: {format_berserk_name(active_berserk.get('key'))}")
        available_roars = self.get_available_warrior_roars()
        if available_roars:
            lines.extend(["", f"Roars: {', '.join(format_roar_name(key) for key in available_roars)}"])
        for category in ["strikes", "roars", "survival"]:
            entries = sorted(categories.get(category, []))
            if not entries:
                continue
            lines.append(f"{category.title()}: {', '.join(entries)}")

        next_unlocks = self.get_next_warrior_unlocks()
        if next_unlocks:
            unlock_circle, ability_key = next_unlocks[0]
            lines.extend(["", f"Next Unlock: {format_warrior_ability_name(ability_key)} (Circle {unlock_circle})"])

        return "\n".join(lines)

    def get_social_standing(self):
        return get_profession_social_standing(self.get_profession())

    def get_profession_skill_weights(self):
        return dict(PROFESSION_SKILL_WEIGHTS.get(self.get_profession(), {}))

    def get_profession_reaction_message(self, context="presence", observer=None):
        profession = self.get_profession()
        profile = self.get_profession_profile()
        if context == "presence":
            if profession == "empath":
                return "seems to relax a little in your presence."
            if profession == "barbarian":
                return "takes your measure with the caution reserved for dangerous fighters."
        if context == "trade" and profession == "thief":
            return "watches your hands instead of your face."
        if context == "magic" and profile.get("magic_text"):
            return f"cannot ignore that you {profile['magic_text']}."
        return None

    def emit_profession_presence(self):
        location = getattr(self, "location", None)
        if not location:
            return

        presence_text = self.get_profession_profile().get("presence_text")
        if presence_text:
            location.msg_contents(f"{self.key} arrives. {presence_text}", exclude=[self])

    def emit_ability_presence(self, ability):
        location = getattr(self, "location", None)
        if not location or not ability:
            return

        profession = self.get_profession()
        ability_category = str(getattr(ability, "category", "") or "").strip().lower()
        if profession == "thief" and ability_category == "stealth":
            location.msg_contents(f"{self.key} moves with unsettling subtlety.", exclude=[self])
            return

        magic_text = self.get_profession_profile().get("magic_text")
        if magic_text and ability_category == "magic":
            self.db.last_seen_magic = time.time()
            location.msg_contents(f"{self.key} {magic_text}.", exclude=[self])
            for obj in getattr(location, "contents", []):
                if obj != self and hasattr(obj, "react_to"):
                    obj.react_to(self, context="magic")

    def can_trade_with(self, vendor):
        if not self.can_trade():
            return False, "The shopkeeper refuses to deal with you until your debts are settled."
        if vendor and hasattr(vendor, "can_trade"):
            return vendor.can_trade(self)
        return True, ""

    def room_matches_profession_join_site(self, profession_name, room=None):
        profession = self.normalize_profession_name(profession_name)
        room = room or self.location
        if not profession or not room:
            return False

        target_guild_tag = PROFESSION_TO_GUILD.get(profession)
        if not target_guild_tag:
            return True

        room_tag = getattr(getattr(room, "db", None), "guild_tag", None)
        if room_tag == target_guild_tag:
            return True

        tags = getattr(room, "tags", None)
        if not tags:
            return False

        return bool(tags.get(target_guild_tag) or tags.get(f"guild_{profession}") or tags.get(f"{profession}_guild"))

    def get_profession_join_guide(self, profession_name, room=None):
        profession = self.normalize_profession_name(profession_name)
        room = room or self.location
        if not profession or not room:
            return None

        for obj in list(getattr(room, "contents", []) or []):
            if obj == self:
                continue
            role = str(getattr(getattr(obj, "db", None), "guild_role", "") or "").strip().lower()
            teaches = self.normalize_profession_name(getattr(getattr(obj, "db", None), "trains_profession", None))
            if role == "guildmaster" and teaches == profession:
                return obj
        return None

    def can_join_ranger(self):
        missing = []
        for stat_name, minimum, label in RANGER_JOIN_REQUIREMENTS:
            current = self.get_stat(stat_name)
            if current < minimum:
                missing.append(f"{label} {minimum} (you have {current})")
        return not missing, missing

    def get_ranger_join_requirement_text(self):
        return ", ".join(f"{label} {minimum}" for _, minimum, label in RANGER_JOIN_REQUIREMENTS)

    def get_ranger_join_success_message(self, guide=None):
        guide_name = getattr(guide, "key", "Elarion") if guide else "Elarion"
        return (
            f"{guide_name} inclines their head. \"Then stand with us. Mind the land, learn its signs, and do not waste what it gives.\"\n"
            "You are now recognized as a Ranger."
        )

    def get_ranger_join_failure_message(self, missing_requirements):
        joined = "; ".join(str(entry) for entry in list(missing_requirements or []) if str(entry).strip())
        if not joined:
            joined = self.get_ranger_join_requirement_text()
        return f"Elarion studies you for a long moment. \"Not yet. A Ranger must show at least {joined}.\""

    def get_cleric_join_success_message(self, guide=None):
        guide_name = getattr(guide, "key", "Esuin") if guide else "Esuin"
        return (
            f"{guide_name} bows their head for a measured moment. \"Then take the vow with full knowledge of its weight. Serve with discipline, and do not turn from the burdens set before you.\"\n"
            "You are now recognized as a Cleric."
        )

    def can_advance_ranger(self):
        if not self.is_profession("ranger"):
            return False, ["You are not a Ranger."]

        reasons = []
        forage_uses = int(getattr(self.db, "forage_uses", 0) or 0)
        awareness_rank = int(self.get_skill("perception") or 0)

        if forage_uses < 1:
            reasons.append("You have not yet learned to gather from the wild.")

        if awareness_rank < 5:
            reasons.append("Your awareness of the wild is still too shallow.")

        if reasons:
            return False, reasons

        return True, None

    def join_profession(self, profession_name):
        profession = self.normalize_profession_name(profession_name)
        if profession not in VALID_GUILDS or profession == DEFAULT_PROFESSION:
            options = ", ".join(name.replace("_", " ") for name in VALID_GUILDS if name != DEFAULT_PROFESSION)
            return False, f"You may join one of these professions: {options}"

        if profession != "empath" and not self.room_matches_profession_join_site(profession):
            return False, "You must stand inside the proper guildhall to join that profession."

        if self.get_profession() == profession:
            return False, f"You already belong to the {self.get_profession_display_name()} profession."

        guide = self.get_profession_join_guide(profession)
        if profession == "empath":
            ready, ready_message = self.can_begin_profession_oath()
            if not ready:
                return False, ready_message
            if not self.room_matches_profession_join_site(profession) or not self.is_empath_join_room():
                return False, "You must stand in the guildleader's office to join the Empaths."
            if not guide:
                return False, "No Empath guildleader is here to judge your oath."
            self.set_profession(profession)
            self.set_guild(profession)
            _patient, message = self.begin_empath_apprenticeship(guide=guide)
            return True, message
        if profession == "ranger":
            if not guide:
                return False, "No Ranger guildmaster is here to receive your oath."
            eligible, missing_requirements = self.can_join_ranger()
            if not eligible:
                return False, self.get_ranger_join_failure_message(missing_requirements)
        if profession == "cleric":
            ready, ready_message = self.can_begin_profession_oath()
            if not ready:
                return False, ready_message
            if not self.room_matches_profession_join_site(profession) or not self.is_cleric_join_room():
                return False, "You must stand in the guildleader's office to join the Clerics."
            if not guide:
                return False, "No Cleric guildleader is here to receive your vow."

        self.set_profession(profession)
        self.set_guild(profession)
        if profession == "ranger":
            self.db.circle = max(1, int(getattr(self.db, "circle", 1) or 1))
            self.db.ranger_circle = max(1, int(getattr(self.db, "ranger_circle", 1) or 1))
            self.db.ranger_joined_at = time.time()
            return True, self.get_ranger_join_success_message(guide=guide)
        if profession == "cleric":
            self.db.circle = max(1, int(getattr(self.db, "circle", 1) or 1))
            self.db.cleric_joined_at = time.time()
            return True, self.get_cleric_join_success_message(guide=guide)
        return True, f"You are accepted into the {self.get_profession_display_name()} profession."

    def advance_profession(self):
        trainer = self.get_room_trainer()
        ok, message = self.can_train_with(trainer)
        if not ok:
            return False, message

        current_rank = self.get_profession_rank()
        if current_rank >= 5:
            return False, "You have already mastered your profession."

        required_xp = current_rank * 100
        total_xp = int(getattr(self.db, "total_xp", 0) or 0)
        if total_xp and total_xp < required_xp:
            return False, f"You need {required_xp} total experience before advancing again."

        self.db.profession_rank = current_rank + 1
        return True, f"Under {trainer.key}'s guidance, you advance to {self.get_profession_rank_label()}."

    def debug_log(self, text):
        if getattr(self.db, "debug_mode", False):
            print(text)

    def get_ability_cooldowns(self):
        cooldowns = getattr(self.ndb, "cooldowns", None)
        if not isinstance(cooldowns, dict):
            cooldowns = {}
            self.ndb.cooldowns = cooldowns
        return cooldowns

    def execute_ability_input(self, key, target=None, target_name=None):
        ability_key = str(key or "").strip().lower()
        if not ability_key:
            self.msg("Use which ability?")
            return

        self.ndb.is_busy = False
        self.ndb.is_walking = False

        if target is None and target_name:
            target = self.search(str(target_name).strip())
            if not target:
                return

        self.use_ability(ability_key, target=target)

    def set_profession(self, profession_name):
        normalized = self.normalize_profession_name(profession_name)
        if normalized not in VALID_GUILDS:
            return False
        self.db.profession = normalized
        self.db.guild = normalized
        self.ndb.subsystem = None
        self.ndb.subsystem_controller = None
        if normalized == "warrior":
            self.db.warrior_circle = max(1, int(getattr(self.db, "warrior_circle", 1) or 1))
            self.sync_warrior_progression(emit_messages=True)
            self.update_war_tempo_state()
        elif normalized == "ranger":
            self.db.wilderness_bond = max(0, min(100, int(getattr(self.db, "wilderness_bond", 50) or 50)))
            self.db.ranger_instinct = max(0, int(getattr(self.db, "ranger_instinct", 0) or 0))
            self.db.circle = max(1, int(getattr(self.db, "circle", 1) or 1))
            self.db.ranger_circle = max(1, int(getattr(self.db, "ranger_circle", 1) or 1))
        elif normalized == "cleric":
            self.db.devotion_max = int(CLERIC_DEVOTION_CONFIG["max_devotion"])
            self.db.max_devotion = self.db.devotion_max
            self.set_devotion(max(int(CLERIC_DEVOTION_CONFIG["baseline"]), self.get_devotion()), sync=False)
            self.db.favor_max = max(5, int(getattr(self.db, "favor_max", 5) or 5))
            self.db.favor_current = min(self.db.favor_max, max(0, int(getattr(self.db, "favor_current", self.db.favor_max) or self.db.favor_max)))
            self.db.favor = self.db.favor_current
            skills = dict(self.db.skills or {})
            theurgy = dict(skills.get("theurgy") or {"rank": 0, "mindstate": 0})
            theurgy["rank"] = max(1, int(theurgy.get("rank", 0) or 0))
            skills["theurgy"] = theurgy
            self.db.skills = skills
        elif normalized == "empath":
            self.db.circle = max(1, int(getattr(self.db, "circle", 1) or 1))
            self.db.empath_rank = max(0, int(getattr(self.db, "empath_rank", 0) or 0))
            self.db.empath_xp = max(0, int(getattr(self.db, "empath_xp", 0) or 0))
            self.db.empath_training_stage = max(0, int(getattr(self.db, "empath_training_stage", EMPATH_TRAINING_UNSET) or EMPATH_TRAINING_UNSET))
        else:
            self.db.devotion_current = 0
            self.db.devotion = 0
            self.db.devotion_max = 0
            self.db.max_devotion = 0
        self.get_subsystem()
        return True

    def get_skillset(self, skill_name):
        return self.get_exp_skillset_tier(skill_name)

    def get_skill_weight(self, skillset):
        profession = self.get_profession()
        weights = PROFESSION_SKILL_WEIGHTS.get(profession, {})
        return float(weights.get(skillset, 1.0))

    def tick_subsystem_state(self):
        controller = getattr(self.ndb, "subsystem_controller", None)
        if not controller or getattr(controller, "profession", None) != self.get_profession():
            self.get_subsystem()
            controller = getattr(self.ndb, "subsystem_controller", None)
        if not controller:
            return False
        changed = controller.tick(self)
        if changed:
            self.ndb.subsystem = controller.get_state(self)
        return changed

    def format_subsystem_feedback(self, before, after):
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            return None

        resource_map = {
            "devotion": ("Devotion", "max_devotion"),
            "fire": ("Inner Fire", "max_fire"),
            "focus": ("Focus", "max_focus"),
            "tempo": ("War Tempo", "max_tempo"),
            "transfer_pool": ("Transfer", "max_pool"),
            "attunement": ("Attunement", "max_attunement"),
        }

        if before.get("key") == "ranger" and after.get("key") == "ranger":
            before_bond = int(before.get("wilderness_bond", 0) or 0)
            after_bond = int(after.get("wilderness_bond", 0) or 0)
            if before_bond != after_bond:
                return f"Wilderness Bond: {before_bond} -> {after_bond}"

        for key, (label, _max_key) in resource_map.items():
            before_value = before.get(key)
            after_value = after.get(key)
            if before_value is None or after_value is None or before_value == after_value:
                continue
            return f"[{label}: {before_value} -> {after_value}]"

        return None

    def format_subsystem_snapshot(self, subsystem):
        if not isinstance(subsystem, Mapping):
            return None

        resource_map = {
            "devotion": "Devotion",
            "fire": "Inner Fire",
            "focus": "Focus",
            "tempo": "War Tempo",
            "transfer_pool": "Transfer",
            "attunement": "Attunement",
        }

        for key, label in resource_map.items():
            value = subsystem.get(key)
            if value is None:
                continue
            return f"[{label}: {value}]"

        return None

    def normalize_ability_failure_message(self, message, subsystem=None):
        text = str(message or "").strip()
        lower = text.lower()
        subsystem_label = self.format_subsystem_snapshot(subsystem)

        if any(token in lower for token in ("inner fire", "focus", "tempo", "attunement", "transfer", "sufficient", "insufficient", "lack")):
            if subsystem_label and "Inner Fire" in subsystem_label:
                return "You lack the inner fire."
            if subsystem_label and "War Tempo" in subsystem_label:
                return "You are not yet worked into a battle state."
            return text or "You lack the required resource."

        if "experienced" in lower or ("need" in lower and "rank" in lower):
            return "You are not experienced enough."

        if "cannot use" in lower or "not your" in lower:
            return "That is not your path."

        return text or "That fails."

    def get_room_trainer(self):
        room = self.location
        if not room:
            return None
        return next(
            (
                obj for obj in room.contents
                if getattr(obj.db, "is_trainer", False)
            ),
            None,
        )

    def can_train_with(self, trainer):
        if not trainer:
            return False, "There is no trainer here."
        if trainer.db.trains_profession != self.get_profession():
            return False, "That trainer does not teach your profession."
        return True, ""

    def get_guild(self):
        return self.normalize_guild_name(getattr(self.db, "guild", None))

    def set_guild(self, guild_name):
        normalized = self.normalize_guild_name(guild_name)
        if normalized not in VALID_GUILDS:
            return False
        self.db.guild = normalized
        return True

    def has_skill_guild_access(self, skill_name):
        metadata = self.get_skill_metadata(skill_name)
        guilds = metadata.get("guilds") or ()
        if not guilds:
            return False
        return self.get_profession() in guilds

    def get_skill_baseline(self, skill_name):
        return int(self.get_skill_metadata(skill_name).get("starter_rank", 0))

    def is_skill_visible(self, skill_name):
        metadata = self.get_skill_metadata(skill_name)
        if metadata.get("visibility") != "guild_locked":
            return True
        return self.get_skill_rank(skill_name) > 0 or self.has_skill_guild_access(skill_name)

    def get_spell_def(self, name):
        normalized = str(name or "").strip().lower().replace("-", "_")
        if normalized not in SPELLS:
            return None
        return dict(SPELLS.get(normalized, {}))

    def get_spell_metadata(self, spell_name):
        return self.get_spell_def(spell_name)

    def can_access_spell(self, spell_name):
        metadata = self.get_spell_def(spell_name)
        if not metadata:
            return False, "You do not know how to prepare that spell."

        guilds = metadata.get("guilds") or ()
        if guilds and self.get_profession() not in guilds:
            return False, "Your guild does not have access to that spell."

        return True, ""

    def get_safe_mana_limit(self, category=None):
        attunement = self.get_skill("attunement")
        category_skill = self.get_skill(category) if category else 0
        return max(5, 10 + int((attunement + category_skill) / 15))

    def get_luminar_safe_charge(self, luminar):
        capacity = int(getattr(luminar.db, "capacity", 0) or 0)
        return capacity + int(self.get_skill("arcana") / 2)

    def get_magic_resistance(self):
        stats = self.db.stats or {}
        base = int(stats.get("magic_resistance", stats.get("magic_resist", 10)) or 10)
        ward = self.get_state("warding_barrier")
        if ward:
            base += int(ward.get("strength", 0) or 0)
        return base

    def apply_magic_resistance(self, incoming_power):
        resist = self.get_magic_resistance()
        return max(1.0, float(incoming_power) * (100.0 / (100.0 + resist)))

    def calculate_preparation_stability(self, mana, category):
        skill = self.get_skill(category)
        attunement = self.get_skill("attunement")
        control = skill + attunement
        if self.is_profession("cleric"):
            control *= self.get_cleric_magic_modifier()
        difficulty = int(mana) * 10
        stability = control / max(1, difficulty)
        return max(0.0, min(1.0, stability))

    def get_spell_power(self, category, mana):
        skill = self.get_skill(category)
        attunement = self.get_skill("attunement")
        power = float(mana) * (1 + (skill + attunement) / 200.0)
        if self.is_profession("cleric"):
            power *= self.get_cleric_magic_modifier()
        return power

    def resolve_spell_backlash(self, mana, category):
        safe_limit = self.get_safe_mana_limit(category)
        if mana <= safe_limit:
            return "stable"

        excess = mana - safe_limit
        roll = random.random()
        if roll < min(0.25, excess / 40.0):
            return "fizzle"
        if roll < min(0.50, excess / 25.0):
            return "backlash"
        return "wild"

    def resolve_cast_quality(self, stability):
        roll = random.random()
        if roll > stability:
            return "weak"
        if roll > stability * 0.45:
            return "normal"
        return "strong"

    def get_multi_skill_factor(self, primary, secondary):
        primary_skill = self.get_skill(primary)
        secondary_skill = self.get_skill(secondary)
        return min(primary_skill, secondary_skill) / max(1, max(primary_skill, secondary_skill))

    def get_effect_priority(self, effect_name):
        priorities = {
            "warding_barrier": 3,
            "augmentation_buff": 2,
            "debilitated": 2,
            "exposed_magic": 1,
        }
        return priorities.get(effect_name, 0)

    def set_spell_cooldown(self, spell, duration):
        self.set_state(f"cooldown_{spell}", {"duration": max(1, int(duration))})

    def resolve_hit_quality(self, offense, defense):
        ratio = offense / max(1, defense)
        if ratio < 0.5:
            return "miss"
        if ratio < 0.8:
            return "graze"
        if ratio < 1.2:
            return "hit"
        return "strong"

    def resolve_cast_target(self, target_name, spell_def):
        if spell_def.get("target_mode", "self") != "single":
            return self

        if target_name:
            return self.search(str(target_name).strip())

        if hasattr(self, "get_target"):
            return self.get_target()
        return None

    def start_cyclic_spell(self, name, power):
        if self.get_state("active_cyclic"):
            self.msg("You are already sustaining a spell.")
            return False

        spell_def = self.get_spell_def(name) or {}
        self.set_state(
            "active_cyclic",
            {
                "name": name,
                "power": power,
                "drain": max(1, int(power / 5)),
                "category": spell_def.get("category", "augmentation"),
                "mode": spell_def.get("target_mode", "self"),
            },
        )
        return True

    def process_cyclic(self):
        data = self.get_state("active_cyclic")
        if not data:
            return False

        drain = int(data.get("drain", 0) or 0)
        if not self.spend_attunement(drain):
            bonus = self.invoke_luminar(drain)
            if bonus < drain:
                self.msg("You lose control of your sustained spell.")
                self.clear_state("active_cyclic")
                return False

        self.apply_cyclic_effect()
        return True

    def apply_cyclic_effect(self):
        data = self.get_state("active_cyclic")
        if not data:
            return False

        power = float(data.get("power", 0) or 0)
        category = data.get("category", "augmentation")
        if category == "augmentation":
            self.set_state(
                "augmentation_buff",
                {
                    "name": data.get("name", "cyclic spell"),
                    "strength": max(1, int(power / 10)),
                    "duration": 2,
                },
            )
            return True

        if category == "warding":
            self.apply_warding_barrier(
                self,
                data.get("name", "cyclic spell"),
                max(1, int(power / 12)),
                2,
            )
            return True

        if category == "utility":
            self.set_state(
                "utility_light",
                {
                    "name": data.get("name", "cyclic spell"),
                    "duration": 2,
                },
            )
            return True

        return False

    def get_spell_recipients(self, target_mode, target=None):
        if target_mode == "self":
            return [self]

        if target_mode == "single":
            return [target] if target else []

        if not self.location:
            return []

        if target_mode == "room":
            return [
                obj for obj in self.location.contents
                if obj != self and hasattr(obj, "set_hp") and getattr(obj.db, "hp", None) is not None
            ]

        if target_mode == "group":
            recipients = [self]
            recipients.extend(
                obj for obj in self.location.contents
                if obj != self and getattr(obj, "account", None) and hasattr(obj, "get_state")
            )
            return recipients

        return []

    def can_apply_buff(self):
        return not self.get_state("augmentation_buff")

    def apply_exposed_state(self, target, duration=6):
        target.set_state("exposed_magic", {"duration": duration})

    def apply_warding_barrier(self, target, name, strength, duration):
        existing = target.get_state("warding_barrier")
        if existing and int(existing.get("strength", 0) or 0) > strength and existing.get("name") != name:
            refreshed = dict(existing)
            refreshed["duration"] = max(int(refreshed.get("duration", 0) or 0), duration)
            target.set_state("warding_barrier", refreshed)
            if target.get_state("exposed_magic"):
                target.clear_state("exposed_magic")
            return True

        if existing and existing.get("name") == name:
            refreshed = dict(existing)
            refreshed["duration"] = max(int(refreshed.get("duration", 0) or 0), duration)
            refreshed["strength"] = max(int(refreshed.get("strength", 0) or 0), strength)
            target.set_state("warding_barrier", refreshed)
        else:
            target.set_state(
                "warding_barrier",
                {"name": name, "strength": strength, "duration": duration},
            )

        if target.get_state("exposed_magic"):
            target.clear_state("exposed_magic")
        return True

    def apply_ward_absorption(self, target, damage):
        ward = target.get_state("warding_barrier")
        if not ward:
            return damage

        absorbed = min(max(0, int(damage)), int(ward.get("strength", 0) or 0))
        if absorbed <= 0:
            return damage

        remaining = max(0, int(damage) - absorbed)
        updated = dict(ward)
        updated["strength"] = max(0, int(updated.get("strength", 0) or 0) - absorbed)
        if updated["strength"] <= 0:
            target.clear_state("warding_barrier")
        else:
            target.set_state("warding_barrier", updated)
        return remaining

    def resolve_targeted_spell(self, name, power, target, spell_def, quality, wild_modifier=1.0):
        if not target or target == self:
            self.msg("You need a valid target for that spell.")
            return False

        if not hasattr(target, "set_hp") or getattr(target.db, "hp", None) is None:
            self.msg("That is not a valid target for this spell.")
            return False

        self.register_empath_offensive_action(target=target, context="targeted_magic", amount=8)

        factor = self.get_multi_skill_factor("targeted_magic", "attunement")
        effective_power = float(power) * (0.5 + factor) * wild_modifier
        setattr(target, "incoming_attackers", getattr(target, "incoming_attackers", 0) + 1)
        offense = effective_power + self.get_skill("targeted_magic")
        debuff = self.get_state("debilitated")
        if debuff:
            debuff_type = debuff.get("type", "accuracy")
            if debuff_type in {"accuracy", "offense"}:
                offense -= int(debuff.get("penalty", 0) or 0)
        exposed = target.get_state("exposed_magic")
        if exposed:
            offense += 5
        defense = target.get_skill("evasion") + target.db.stats.get("reflex", 10)
        target_debuff = target.get_state("debilitated")
        if target_debuff and target_debuff.get("type") == "evasion":
            defense -= int(target_debuff.get("penalty", 0) or 0)
        attackers = getattr(target, "incoming_attackers", 1)
        pressure_penalty = int(attackers ** 0.5)
        defense = max(1, defense - pressure_penalty)

        hit_quality = self.resolve_hit_quality(offense, defense)
        if hit_quality == "miss":
            award_exp_skill(self, "targeted_magic", max(10, int(defense)), success=False)
            award_exp_skill(target, "evasion", max(10, int(offense)), success=True)
            self.msg(f"Your {name} misses {target.key}.")
            target.msg(f"{self.key}'s {name} misses you.")
            return True

        award_exp_skill(self, "targeted_magic", max(10, int(defense)), success=True)
        award_exp_skill(target, "evasion", max(10, int(offense)), success=False)

        multiplier = {"graze": 0.5, "hit": 1.0, "strong": 1.5}[hit_quality]
        if quality == "weak":
            multiplier *= 0.75
        elif quality == "strong":
            multiplier *= 1.25

        damage = max(1, int(effective_power * multiplier / 3))
        damage = max(1, int(target.apply_magic_resistance(damage)))
        damage = max(0, self.apply_ward_absorption(target, damage))
        damage = max(1, damage)

        if hasattr(target, "apply_incoming_damage"):
            target.apply_incoming_damage("chest", damage, "impact")
        else:
            target.set_hp((target.db.hp or 0) - damage)
        self.msg(f"Your {name} {hit_quality}s {target.key} for {damage} damage.")
        target.msg(f"{self.key}'s {name} {hit_quality}s you for {damage} damage.")
        if self.location:
            self.location.msg_contents(
                f"{self.key}'s {name} {hit_quality}s {target.key}.",
                exclude=[self, target],
            )
        return True

    def resolve_room_targeted_spell(self, name, power, spell_def, quality, wild_modifier=1.0):
        recipients = self.get_spell_recipients("room")
        if not recipients:
            self.msg(f"Your {name} finds no targets.")
            return False

        self.adjust_empath_shock(10) if self.is_empath() else None

        self.msg(f"Your {name} erupts outward!")
        if self.location:
            self.location.msg_contents(f"{self.key}'s {name} erupts outward!", exclude=[self])

        factor = self.get_multi_skill_factor("targeted_magic", "attunement")
        effective_power = float(power) * (0.5 + factor) * wild_modifier
        hit_any = False
        for target in recipients:
            setattr(target, "incoming_attackers", getattr(target, "incoming_attackers", 0) + 1)
            offense = effective_power + self.get_skill("targeted_magic")
            defense = target.get_skill("evasion") + target.db.stats.get("reflex", 10)
            target_debuff = target.get_state("debilitated")
            if target_debuff and target_debuff.get("type") == "evasion":
                defense -= int(target_debuff.get("penalty", 0) or 0)
            attackers = getattr(target, "incoming_attackers", 1)
            pressure_penalty = int(attackers ** 0.5)
            defense = max(1, defense - pressure_penalty)
            hit_quality = self.resolve_hit_quality(offense, defense)
            if hit_quality == "miss":
                award_exp_skill(target, "evasion", max(10, int(offense)), success=True)
                continue

            award_exp_skill(target, "evasion", max(10, int(offense)), success=False)

            multiplier = {"graze": 0.5, "hit": 1.0, "strong": 1.5}[hit_quality]
            if quality == "weak":
                multiplier *= 0.75
            elif quality == "strong":
                multiplier *= 1.25

            damage = max(1, int(effective_power * multiplier / 4))
            damage = max(1, int(target.apply_magic_resistance(damage)))
            damage = max(0, self.apply_ward_absorption(target, damage))
            damage = max(1, damage)
            hit_any = True
            if hasattr(target, "apply_incoming_damage"):
                target.apply_incoming_damage("chest", damage, "impact")
            else:
                target.set_hp((target.db.hp or 0) - damage)
            if getattr(target, "account", None):
                target.msg(f"{self.key}'s {name} washes over you!")

        award_exp_skill(self, "targeted_magic", max(10, int(effective_power)), success=hit_any)

        return True

    def resolve_augmentation_spell(self, name, power, spell_def, quality):
        if self.get_state("active_cyclic") and spell_def.get("category") == "augmentation":
            self.msg("Your sustained magic interferes with that spell.")
            return False

        strength = 1 + int(power / 10)
        duration = 10 + int(power / 2)
        if quality == "weak":
            strength = max(1, strength - 1)
        elif quality == "strong":
            strength += 1

        existing = self.get_state("augmentation_buff")
        if existing:
            existing_strength = int(existing.get("strength", 0) or 0)
            if existing_strength > strength:
                refreshed = dict(existing)
                refreshed["duration"] = max(int(refreshed.get("duration", 0) or 0), duration)
                self.set_state("augmentation_buff", refreshed)
                self.msg("You are already under a stronger similar effect.")
                return True

        self.set_state("augmentation_buff", {"name": name, "strength": strength, "duration": duration})
        self.msg(f"You feel {name} settle into place around you.")
        return True

    def resolve_debilitation_spell(self, name, power, target, spell_def, quality, wild_modifier=1.0):
        if not target or target == self:
            self.msg("You need a valid target for that spell.")
            return False

        self.register_empath_offensive_action(target=target, context="debilitation", amount=6)

        factor = self.get_multi_skill_factor("debilitation", "attunement")
        effective_power = float(power) * (0.5 + factor) * wild_modifier
        offense = effective_power + self.get_skill("debilitation")
        defense = target.get_skill("warding") + target.db.stats.get("discipline", 10)
        defense += target.get_magic_resistance()
        ratio = offense / max(1, defense)
        if ratio < 0.7:
            self.msg(f"{target.key} resists your {name}.")
            target.msg(f"You resist {self.key}'s {name}.")
            award_exp_skill(self, "debilitation", max(10, int(defense)), success=False)
            return True

        penalty = int(effective_power / 10)
        duration = 6 + int(effective_power / 3)
        debuff_type = spell_def.get("debuff_type", "accuracy")
        if ratio < 1.0:
            penalty = max(1, penalty // 2)
        existing = target.get_state("debilitated")
        if existing:
            penalty = max(1, penalty // 2)
        if quality == "strong":
            penalty += 1

        if existing:
            existing_penalty = int(existing.get("penalty", 0) or 0)
            if existing_penalty > penalty and existing.get("type") == debuff_type:
                refreshed = dict(existing)
                refreshed["duration"] = max(int(refreshed.get("duration", 0) or 0), duration)
                target.set_state("debilitated", refreshed)
                self.apply_exposed_state(target, duration=6)
                self.msg(f"Your {name} reinforces the lingering hindrance on {target.key}.")
                target.msg(f"{self.key}'s {name} intensifies the pressure already on you.")
                award_exp_skill(self, "debilitation", max(10, int(defense)), success=True)
                return True

        target.set_state("debilitated", {"penalty": penalty, "duration": duration, "type": debuff_type})
        self.apply_exposed_state(target, duration=6)
        self.msg(f"Your {name} hampers {target.key}.")
        target.msg(f"You feel your movements hindered by {self.key}'s {name}.")
        award_exp_skill(self, "debilitation", max(10, int(defense)), success=True)
        return True

    def resolve_warding_spell(self, name, power, spell_def, quality):
        strength = 1 + int(power / 10)
        duration = 10 + int(power / 2)
        if quality == "strong":
            strength += 1
        self.apply_warding_barrier(self, name, strength, duration)
        self.msg("A protective barrier settles around you.")
        return True

    def resolve_group_warding_spell(self, name, power, spell_def, quality):
        recipients = self.get_spell_recipients("group")
        if not recipients:
            self.msg(f"{name} finds no one to protect.")
            return False

        strength = 1 + int(power / 12)
        duration = 8 + int(power / 3)
        if quality == "strong":
            strength += 1

        for target in recipients:
            self.apply_warding_barrier(target, name, strength, duration)
            if getattr(target, "account", None) and target != self:
                target.msg(f"A protective field settles over you from {self.key}'s magic.")

        self.msg(f"You extend {name} over your group.")
        if self.location:
            self.location.msg_contents(f"{self.key} extends a protective spell over the group.", exclude=[self])
        return True

    def resolve_utility_spell(self, name, power, spell_def, quality):
        duration = 20 + int(power)
        self.set_state("utility_light", {"name": name, "duration": duration})
        self.msg("A soft light forms around you.")
        return True

    def resolve_cleanse_spell(self, power, quality):
        removed = False
        for state_name in ["debilitated", "exposed_magic"]:
            if self.get_state(state_name):
                self.clear_state(state_name)
                removed = True

        if removed:
            self.msg("You feel lingering effects wash away.")
        else:
            self.msg("You feel momentarily refreshed.")
        return True

    def process_magic_states(self):
        for key in ["augmentation_buff", "debilitated", "warding_barrier", "utility_light", "exposed_magic"]:
            data = self.get_state(key)
            if not data:
                continue
            updated = dict(data)
            updated["duration"] = int(updated.get("duration", 0) or 0) - 1
            if updated["duration"] <= 0:
                self.clear_state(key)
            else:
                self.set_state(key, updated)

        for key in list((self.db.states or {}).keys()):
            if not str(key).startswith("cooldown_"):
                continue
            data = self.get_state(key)
            if not data:
                continue
            updated = dict(data)
            updated["duration"] = int(updated.get("duration", 0) or 0) - 1
            if updated["duration"] <= 0:
                self.clear_state(key)
            else:
                self.set_state(key, updated)

    def get_available_skills(self):
        self.ensure_core_defaults()
        available = {}

        for skill_name, metadata in SKILL_REGISTRY.items():
            if self.is_skill_visible(skill_name):
                available[skill_name] = dict(metadata)

        for skill_name, data in (self.db.skills or {}).items():
            if data.get("rank", 0) > 0 and skill_name not in available:
                available[skill_name] = self.get_skill_metadata(skill_name)

        return dict(sorted(available.items(), key=lambda item: self.format_skill_name(item[0]).lower()))

    def get_survival_skills(self):
        return {
            skill_name: metadata
            for skill_name, metadata in self.get_available_skills().items()
            if metadata.get("category") == "survival"
        }

    def get_shared_survival_skills(self):
        return {
            skill_name: metadata
            for skill_name, metadata in self.get_survival_skills().items()
            if metadata.get("visibility") != "guild_locked"
        }

    def get_hidden_survival_skills(self):
        hidden = {}
        for skill_name, metadata in SKILL_REGISTRY.items():
            if metadata.get("category") != "survival":
                continue
            if metadata.get("visibility") != "guild_locked":
                continue
            if self.get_skill_rank(skill_name) > 0:
                continue
            hidden[skill_name] = dict(metadata)
        return dict(sorted(hidden.items(), key=lambda item: self.format_skill_name(item[0]).lower()))

    def get_skill_detail_entry(self, skill_name):
        self.ensure_core_defaults()
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            return None
        if normalized not in SKILL_REGISTRY and normalized not in (self.db.skills or {}):
            return None
        if not self.is_skill_visible(normalized) and self.get_skill_rank(normalized) <= 0:
            return None

        metadata = self.get_skill_metadata(normalized)
        legacy_skills = self.db.skills if isinstance(self.db.skills, Mapping) else {}
        legacy_entry = legacy_skills.get(normalized, {})
        if not isinstance(legacy_entry, Mapping):
            legacy_entry = {}
        exp_skill = self._sync_exp_skill_state(normalized, legacy_entry)
        points = int(exp_skill.mindstate or 0)
        return {
            "skill": normalized,
            "display": self.format_skill_name(normalized),
            "rank": int(exp_skill.rank or self.get_skill_rank(normalized) or 0),
            "mindstate": points,
            "label": exp_skill.mindstate_name(),
            "cap": MINDSTATE_MAX,
            "category": metadata.get("category", "general"),
            "visibility": metadata.get("visibility", "shared"),
            "description": metadata.get("description", "No description is available yet."),
        }

    def get_skill_entries(self, include_zero=False):
        self.ensure_core_defaults()
        cap = MINDSTATE_MAX
        entries = []
        legacy_skills = self.db.skills if isinstance(self.db.skills, Mapping) else {}

        skill_names = list(self.get_available_skills().keys()) if include_zero else list(legacy_skills.keys())

        for skill_name in skill_names:
            if skill_name == "tend":
                continue

            data = dict(legacy_skills.get(skill_name, {}))
            rank = data.get("rank", 0)
            if not include_zero and rank <= 0:
                continue

            exp_skill = self._sync_exp_skill_state(skill_name, data)
            points = int(exp_skill.mindstate or 0)
            metadata = self.get_skill_metadata(skill_name)
            entries.append(
                {
                    "skill": skill_name,
                    "display": self.format_skill_name(skill_name),
                    "rank": int(exp_skill.rank or rank or 0),
                    "mindstate": points,
                    "label": exp_skill.mindstate_name(),
                    "cap": cap,
                    "active": points > 0 and is_active(exp_skill),
                    "category": metadata.get("category", "general"),
                    "visibility": metadata.get("visibility", "shared"),
                    "description": metadata.get("description", "No description is available yet."),
                }
            )

        entries.sort(key=lambda entry: (entry["category"], not entry["active"], entry["display"].lower()))
        return entries

    def get_active_learning_entries(self):
        entries = [entry for entry in self.get_skill_entries(include_zero=False) if entry.get("active")]
        entries.sort(key=lambda entry: (-entry.get("mindstate", 0), entry.get("display", entry.get("skill", "")).lower()))
        return entries

    def calculate_difficulty_ratio(self, skill_name, difficulty):
        rank = self.get_skill_rank(skill_name)
        if difficulty <= 0:
            return 2.0
        return rank / difficulty

    def get_difficulty_band(self, ratio):
        if ratio > 1.5:
            return "trivial"
        elif ratio > 1.2:
            return "easy"
        elif ratio > 0.8:
            return "optimal"
        elif ratio > 0.5:
            return "hard"
        return "too_hard"

    def get_learning_gain(self, band):
        return {
            "trivial": 0,
            "easy": 1,
            "optimal": 3,
            "hard": 2,
            "too_hard": 1,
        }.get(band, 0)

    def get_learning_amount(self, skill_name, difficulty):
        ratio = self.calculate_difficulty_ratio(skill_name, difficulty)
        band = self.get_difficulty_band(ratio)
        return self.get_learning_gain(band), band

    def process_learning_pulse(self):
        # Legacy mindstate/rank pulse is retired. Active learning now drains and
        # progresses through the transient exp_skills ticker in world.systems.exp_pulse.
        return

    def get_inactive_skill_entries(self):
        self.ensure_core_defaults()
        cap = self.get_mindstate_cap()
        entries = []

        for skill_name, data in (self.db.skills or {}).items():
            points = data.get("mindstate", 0)
            if points > 0:
                continue
            entries.append(
                {
                    "skill": skill_name,
                    "rank": data.get("rank", 0),
                    "mindstate": points,
                    "label": self.get_mindstate_label(points),
                    "cap": cap,
                }
            )

        entries.sort(key=lambda entry: entry["skill"].lower())
        return entries

    def get_bleeding_parts(self):
        self.ensure_core_defaults()
        parts = []

        for part_name, data in (self.db.injuries or {}).items():
            bleed = data.get("bleed", 0)
            if bleed <= 0:
                continue
            parts.append(
                {
                    "part": part_name,
                    "display": self.format_body_part_name(part_name, title=True),
                    "bleed": bleed,
                    "injury": self.get_injury_level(self.get_part_trauma(data)),
                }
            )

        parts.sort(key=lambda entry: entry["bleed"], reverse=True)
        return parts

    def get_first_bleeding_part(self, include_tended=False):
        self.ensure_core_defaults()
        injuries = self.db.injuries or {}

        for part_name in BODY_PART_ORDER:
            body_part = injuries.get(part_name) or {}
            if body_part.get("bleed", 0) > 0 and (include_tended or not self.is_tended(part_name)):
                return part_name

        for part_name, body_part in injuries.items():
            if body_part.get("bleed", 0) > 0 and (include_tended or not self.is_tended(part_name)):
                return part_name

        if include_tended:
            return None

        for part_name in BODY_PART_ORDER:
            body_part = injuries.get(part_name) or {}
            if body_part.get("bleed", 0) > 0:
                return part_name

        for part_name, body_part in injuries.items():
            if body_part.get("bleed", 0) > 0:
                return part_name

        return None

    def is_tended(self, part):
        body_part = self.get_body_part(part)
        if not body_part:
            return False
        tend_state = body_part.get("tend") or {}
        return int(tend_state.get("duration", 0)) > 0 or time.time() < float(tend_state.get("min_until", 0.0))

    def get_tend_strength(self, part):
        body_part = self.get_body_part(part)
        if not body_part:
            return 0
        return int((body_part.get("tend") or {}).get("strength", 0))

    def get_tend_duration(self, part):
        body_part = self.get_body_part(part)
        if not body_part:
            return 0
        tend_state = body_part.get("tend") or {}
        duration = int(tend_state.get("duration", 0))
        min_remaining = max(0, int(float(tend_state.get("min_until", 0.0)) - time.time()))
        return max(duration, min_remaining)

    def apply_tend(self, part, tender=None):
        body_part = self.get_body_part(part)
        if not body_part:
            return False

        healer = tender or self
        skill = healer.get_skill("first_aid") if hasattr(healer, "get_skill") else 0
        current_bleed = int(body_part.get("bleed", 0))
        strength = max(3, current_bleed + 1, 2 + (skill // 6))
        duration = 12 + (skill // 2)
        last_applied = float((body_part.get("tend") or {}).get("last_applied", 0.0))
        recently_tended = self.is_tended(part) or ((time.time() - last_applied) < RECENT_TEND_WINDOW)

        if recently_tended:
            strength = max(2, int(strength * 0.6))
            duration = max(6, int(duration * 0.6))

        body_part["tend"] = {
            "strength": strength,
            "duration": duration,
            "last_applied": time.time(),
            "min_until": time.time() + 120,
        }
        body_part["tended"] = True
        self.start_first_aid_training_window(part, tender=healer)
        return True

    def normalize_body_part_name(self, part):
        if not part:
            return ""
        normalized = str(part).strip().lower().replace("-", "_")
        tokens = [token for token in normalized.split() if token]
        while tokens and tokens[0] in {"my", "the", "your", "a", "an"}:
            tokens.pop(0)
        part_name = "_".join(tokens)
        aliases = {
            "arm": "left_arm",
            "hand": "left_hand",
            "leg": "left_leg",
        }
        return aliases.get(part_name, part_name)

    def format_body_part_name(self, part, title=False):
        part_key = self.normalize_body_part_name(part)
        part_display = part_key.replace("_", " ")
        return part_display.title() if title else part_display

    def get_body_part(self, part):
        self.ensure_core_defaults()
        if not self.db.injuries:
            return None

        body_part = self.db.injuries.get(self.normalize_body_part_name(part))
        if not body_part:
            return None

        if "bleeding" in body_part and "bleed" not in body_part:
            body_part["bleed"] = body_part.pop("bleeding")
        else:
            body_part.pop("bleeding", None)

        body_part.pop("hp", None)
        body_part.pop("max_hp", None)
        return body_part

    def get_part_trauma(self, body_part):
        if not body_part:
            return 0
        return max(
            body_part.get("external", 0),
            body_part.get("internal", 0),
            body_part.get("bruise", 0),
        )

    def get_body_part_wound_descriptions(self, body_part):
        if not body_part:
            return []

        severity_phrases = {
            "light": "lightly",
            "moderate": "moderately",
            "severe": "severely",
            "critical": "critically",
        }
        descriptions = []

        bruise = body_part.get("bruise", 0)
        if bruise > 0:
            severity = self.get_injury_level(bruise)
            descriptions.append(f"{severity_phrases[severity]} bruised")

        external = body_part.get("external", 0)
        if external > 0:
            severity = self.get_injury_level(external)
            descriptions.append(f"{severity_phrases[severity]} wounded")

        internal = body_part.get("internal", 0)
        if internal > 0:
            severity = self.get_injury_level(internal)
            descriptions.append(f"{severity_phrases[severity]} internally injured")
        scars = int(body_part.get("scar", 0) or 0)
        if scars > 0:
            descriptions.append("marked by old scarring" if scars == 1 else "marked by heavy scarring")

        return descriptions

    def get_part_scar_count(self, part):
        body_part = self.get_body_part(part)
        if not body_part:
            return 0
        return max(0, int(body_part.get("scar", 0) or 0))

    def apply_scar_progress(self, location, before_part=None):
        body_part = self.get_body_part(location)
        if not body_part:
            return 0
        previous = dict(before_part or {})
        previous_peak = max(int(previous.get("external", 0) or 0), int(previous.get("internal", 0) or 0))
        previous_trauma = int(previous.get("external", 0) or 0) + int(previous.get("internal", 0) or 0)
        current_peak = max(int(body_part.get("external", 0) or 0), int(body_part.get("internal", 0) or 0))
        current_trauma = int(body_part.get("external", 0) or 0) + int(body_part.get("internal", 0) or 0)
        scar_gain = 0
        if previous_peak < int(EMPATH_SCAR_RULES["severity_threshold"]) <= current_peak:
            scar_gain += 1
        if previous_trauma < int(EMPATH_SCAR_RULES["trauma_threshold"]) <= current_trauma:
            scar_gain += 1
        if previous_trauma >= int(EMPATH_SCAR_RULES["repeat_gate"]) and (current_trauma - previous_trauma) >= int(EMPATH_SCAR_RULES["repeat_threshold"]):
            scar_gain += 1
        if scar_gain <= 0:
            return 0
        body_part["scar"] = min(int(EMPATH_SCAR_RULES["max_scars"]), int(body_part.get("scar", 0) or 0) + scar_gain)
        return scar_gain

    def describe_body_part_wounds(self, body_part):
        descriptions = self.get_body_part_wound_descriptions(body_part)
        if not descriptions:
            return "uninjured"
        return ", ".join(descriptions)

    def apply_damage(self, location, amount, damage_type="impact"):
        self.ensure_core_defaults()
        if location not in self.db.injuries:
            return

        self.maybe_break_ranger_aim_on_hit(amount)

        if getattr(self.db, "disguised", False):
            self.clear_disguise()
        if getattr(self.db, "post_ambush_grace", False) and time.time() < float(getattr(self.db, "post_ambush_grace_until", 0) or 0):
            amount = max(0, int(round(amount * 0.8)))

        if bool(getattr(self.db, "is_npc", False)) and self.is_surprised():
            self.set_awareness("alert")

        body_part = self.db.injuries[location]
        before_part = dict(body_part)
        damage_kind = (damage_type or "impact").lower()

        if damage_kind == "impact":
            body_part["tended"] = False
            previous_bruise = body_part.get("bruise", 0)
            body_part["bruise"] += amount

            if amount >= 8:
                body_part["internal"] += max(1, amount // 4)

            head_thresholds = (8, 18, 30)
            if location == "head":
                bleed_gain = sum(
                    1 for threshold in head_thresholds if previous_bruise < threshold <= body_part["bruise"]
                )
                if bleed_gain:
                    body_part["bleed"] += bleed_gain
                    body_part["external"] += bleed_gain
            elif amount >= 10:
                body_part["bleed"] += 1
        else:
            body_part["tended"] = False
            body_part["external"] += amount
            if damage_kind in {"slice", "pierce", "stab"}:
                if amount >= 4:
                    body_part["bleed"] += 1 + (1 if amount >= 8 else 0)
            elif amount >= 10:
                body_part["bleed"] += 1

        body_part["external"] = min(body_part.get("external", 0), 100)
        body_part["internal"] = min(body_part.get("internal", 0), 100)
        scar_gain = self.apply_scar_progress(location, before_part=before_part)

        if self.get_injury_severity(body_part.get("external", 0)) == "severe":
            self.msg(f"Your {self.format_body_part_name(location)} is badly damaged!")
        if scar_gain > 0:
            self.msg(f"The hurt leaves lasting damage in your {self.format_body_part_name(location)}.")

        if location == "chest" and body_part.get("internal", 0) > 50:
            self.msg("You are in critical condition!")

        self.update_bleed_state()

        if self.is_vital_destroyed():
            self.db.is_dead = True

    def is_vital_destroyed(self):
        self.ensure_core_defaults()
        for part, data in self.db.injuries.items():
            if data["vital"] and data["external"] >= data["max"]:
                return True
        return False

    def stop_bleeding(self, part):
        bp = self.get_body_part(part)
        if not bp:
            return

        bp["bleed"] = 0
        bp["tended"] = True
        bp["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}
        self.update_bleed_state()

    def heal_body_part(self, part, amount):
        bp = self.get_body_part(part)
        if not bp:
            return

        remaining = amount
        if bp.get("external", 0) > 0:
            healed = min(bp["external"], remaining)
            bp["external"] -= healed
            remaining -= healed
        if remaining > 0 and bp.get("bruise", 0) > 0:
            bp["bruise"] = max(0, bp["bruise"] - remaining)
        if self.get_part_trauma(bp) <= 0 and bp.get("bleed", 0) <= 0:
            bp["tended"] = False
            bp["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}

        self.update_bleed_state()

    def get_most_scarred_part(self):
        self.ensure_core_defaults()
        best_part = None
        best_value = 0
        for part_name in BODY_PART_ORDER:
            body_part = self.get_body_part(part_name)
            if not body_part:
                continue
            scars = int(body_part.get("scar", 0) or 0)
            if scars > best_value:
                best_part = part_name
                best_value = scars
        return best_part

    def heal_empath_scars(self, target=None):
        subject = target or self
        if not self.is_empath():
            return False, "You do not know how to ease scars that way."
        unlock_key = "internal_scar_transfer" if subject == self else "external_scar_transfer"
        unlocked, unlock_message = self.require_empath_unlock(unlock_key)
        if not unlocked:
            return False, unlock_message
        if getattr(subject, "location", None) != getattr(self, "location", None) and subject != self:
            return False, "They are not here."
        part_name = subject.get_most_scarred_part() if hasattr(subject, "get_most_scarred_part") else None
        if not part_name:
            return False, f"{subject.key if subject != self else 'You'} bear no scars you can heal."
        body_part = subject.get_body_part(part_name) if hasattr(subject, "get_body_part") else None
        if not body_part or int(body_part.get("scar", 0) or 0) <= 0:
            return False, f"{subject.key if subject != self else 'You'} bear no scars you can heal."
        body_part["scar"] = max(0, int(body_part.get("scar", 0) or 0) - 1)
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + 12)
        self.adjust_empath_shock(3)
        if hasattr(self, "set_roundtime"):
            self.set_roundtime(3.5)
        self.award_empathy_experience("scar_heal", 18, amount=int(body_part.get("scar", 0) or 0) + 1, target=subject)
        part_display = subject.format_body_part_name(part_name) if hasattr(subject, "format_body_part_name") else str(part_name).replace("_", " ")
        if subject != self:
            subject.msg(f"The old pull in your {part_display} eases a little.")
            return True, f"You work at the old scarring in {subject.key}'s {part_display}."
        return True, f"You work at the old scarring in your {part_display}."

    def get_bleed_severity(self, total_bleed):
        if total_bleed == 0:
            return "none"
        elif total_bleed <= 2:
            return "light"
        elif total_bleed <= 5:
            return "moderate"
        elif total_bleed <= 10:
            return "severe"
        else:
            return "critical"

    def get_total_bleed(self):
        self.ensure_core_defaults()
        if not self.db.injuries:
            return 0
        return sum(part["bleed"] for part in self.db.injuries.values())

    def get_effective_bleed_total(self):
        self.ensure_core_defaults()
        total = 0
        for part in (self.db.injuries or {}).values():
            bleed = int(part.get("bleed", 0) or 0)
            tend_state = part.get("tend") or {}
            duration = int(tend_state.get("duration", 0) or 0)
            min_until = float(tend_state.get("min_until", 0.0) or 0.0)
            strength = int(tend_state.get("strength", 0) or 0)
            if duration > 0 or time.time() < min_until:
                bleed = max(0, bleed - strength)
            total += bleed
        return total

    def update_bleed_state(self):
        self.ensure_core_defaults()
        total_bleed = self.get_total_bleed()
        new_state = self.get_bleed_severity(total_bleed)
        old_state = self.db.bleed_state

        if new_state != old_state:
            self.db.bleed_state = new_state
            self.on_bleed_state_change(old_state, new_state)

    def on_bleed_state_change(self, old, new):
        if new == "none":
            self.msg("Your bleeding has stopped.")
        elif new == "light":
            self.msg("You are bleeding.")
        elif new == "moderate":
            self.msg("Your wounds are bleeding steadily.")
        elif new == "severe":
            self.msg("Your wounds are bleeding heavily.")
        elif new == "critical":
            self.msg("Blood is pouring from your wounds!")

    def is_bleeding(self):
        self.ensure_core_defaults()
        return self.get_total_bleed() > 0

    def get_injury_level(self, value):
        if value == 0:
            return "none"
        elif value <= 10:
            return "light"
        elif value <= 25:
            return "moderate"
        elif value <= 50:
            return "severe"
        else:
            return "critical"

    def process_bleed(self):
        self.ensure_core_defaults()
        if not self.db.injuries:
            return

        now = time.time()
        stabilized_until = float(getattr(self.db, "stabilized_until", 0.0) or 0.0)
        is_stabilized = now < stabilized_until
        stability_strength = max(0.0, min(1.0, float(getattr(self.db, "stability_strength", 0.0) or 0.0))) if is_stabilized else 0.0
        total_bleed = 0
        for part_name, part in self.db.injuries.items():
            if part.get("internal", 0) > 20:
                worsening_rate = 1.0
                if is_stabilized:
                    worsening_rate *= max(0.0, 1.0 - stability_strength)
                bleed_gain = int(worsening_rate)
                fractional = max(0.0, worsening_rate - bleed_gain)
                if fractional > 0.0 and random.random() < fractional:
                    bleed_gain += 1
                if bleed_gain > 0:
                    part["bleed"] += bleed_gain

            tend_state = part.get("tend") or {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}
            duration = int(tend_state.get("duration", 0))
            strength = int(tend_state.get("strength", 0))
            min_until = float(tend_state.get("min_until", 0.0))
            was_tended = bool(part.get("tended", False))

            effective_bleed = part.get("bleed", 0)
            if duration > 0 or now < min_until:
                effective_bleed = max(0, effective_bleed - strength)
                if now >= min_until and duration > 0:
                    duration -= 1
                    if part.get("external", 0) > 45:
                        duration -= 1
                    if self.db.in_combat:
                        duration -= 1
                tend_state["duration"] = max(0, duration)
                part["tend"] = tend_state
                part["tended"] = tend_state["duration"] > 0 or now < min_until
                if was_tended and not part["tended"] and part.get("bleed", 0) > 0:
                    self.msg(f"Your {self.format_body_part_name(part_name)} begins bleeding again!")

            total_bleed += max(0, effective_bleed)

        self.process_first_aid_tend_training(now=now)

        if total_bleed > 0:
            hp_loss = total_bleed + int(total_bleed * 0.3)
            if total_bleed > 10:
                hp_loss -= (total_bleed - 10)
            hp_loss = max(1, hp_loss)
            hp_loss = max(1, int(round(hp_loss * self.get_resurrection_bleed_multiplier())))
            self.set_hp((self.db.hp or 0) - hp_loss)
            self.msg("You bleed from your wounds.")
            if total_bleed > 5:
                self.msg("You are bleeding heavily!")
            if (self.db.hp or 0) <= 0:
                if self.consume_resurrection_death_guard():
                    self.db.hp = 1
                    self.msg("Your returning life falters, but the rite holds for one heartbeat.")
                else:
                    self.db.is_dead = True

    def sync_combat_state(self):
        self.ensure_core_defaults()
        if self.db.in_combat and not self.db.target:
            self.db.in_combat = False
        elif self.db.in_combat and self.db.target:
            if self.db.target.location != self.location:
                self.clear_range(self.db.target)
                self.set_target(None)
                self.msg("You are no longer in combat.")

    def is_in_combat(self):
        if not bool(getattr(self.db, "in_combat", False)):
            return False
        self.sync_combat_state()
        return self.db.in_combat

    def set_target(self, target):
        self.ensure_core_defaults()
        old_target = self.db.target
        if target and not target.pk:
            self.db.target = None
            self.db.in_combat = False
            self.db.aiming = None
            clear_direct_interest(self, channel="combat")
            self.sync_client_state()
            return

        if old_target and old_target != target:
            self.clear_range(old_target)

        self.db.target = target
        self.db.in_combat = target is not None
        sync_direct_interest(self, [target] if target is not None else [], channel="combat")
        if target is not None and old_target != target:
            self.maybe_warn_low_favor()
        if target is None:
            self.db.aiming = None
        self.sync_client_state()

    def get_target(self):
        self.ensure_core_defaults()
        target = self.db.target
        if not target:
            return None
        if target.location != self.location:
            return None
        return target

    def is_engaged_with(self, target):
        self.ensure_core_defaults()
        return self.get_target() == target and bool(self.db.in_combat)

    def break_aim_for_movement(self, emit_message=True):
        if self.db.aiming is None and not self.get_state("ranger_aiming"):
            return False
        self.clear_aim()
        if emit_message:
            self.msg("Movement breaks your aim.")
        return True

    def move_to(self, destination, quiet=False, *args, **kwargs):
        origin = self.location
        travel_direction = getattr(self.ndb, "last_traverse_direction", None)
        if destination and destination != self.location:
            self.break_aim_for_movement(emit_message=not quiet)
        moved = super().move_to(destination, quiet=quiet, *args, **kwargs)
        if moved and origin and destination and destination != origin and bool(getattr(self.db, "stealthed", False)):
            self.break_stealth()
        if moved and origin and destination and destination != origin:
            self.cancel_pending_revive("You break the rite by moving.", emit_message=not quiet)
        if moved and origin and destination and destination != origin and self.is_empath():
            self.break_empath_connections(reason="distance", emit_message=not quiet)
        if moved and origin and destination and destination != origin and bool(getattr(self.ndb, "is_fishing", False)):
            from world.systems.fishing import cancel_fishing_session

            cancel_fishing_session(self)
            if not quiet:
                self.msg("You disturb the line.")
        if moved and origin and destination and destination != origin:
            try:
                from world.systems.fishing import return_borrowed_gear

                return_borrowed_gear(self, source_location=origin, direction=travel_direction)
            except Exception:
                LOGGER.exception("Failed to return borrowed fishing gear for %s", getattr(self, "key", self))
        return moved

    def at_pre_move(self, destination, **kwargs):
        if self.is_dead():
            self.msg("You cannot move while dead.")
            return False
        if getattr(self.db, "is_captured", False):
            self.msg("You are restrained and cannot move.")
            return False
        if getattr(self.db, "in_stocks", False):
            self.msg("You are locked in the stocks.")
            return False
        if self.is_in_combat():
            self.msg("You cannot move while in combat.")
            return False
        if self.get_encumbrance_ratio() >= 1.2:
            self.msg("You are too encumbered to move.")
            return False

        if destination and hasattr(destination, "allows_profession") and not destination.allows_profession(self.get_profession()):
            self.msg("You are not permitted to enter there as a member of your profession.")
            return False

        direction = getattr(self.ndb, "last_traverse_direction", None)
        self.ndb.sneak_reveal_observer_ids = []
        self.ndb.sneak_partial_observer_ids = []
        self.ndb.sneak_move_active = False

        if self.is_sneaking() and direction:
            reveal_ids = []
            partial_ids = []
            self.ndb.sneak_move_active = True
            outcome_rank = {"fail": 0, "partial": 1, "success": 2, "strong": 3}
            aggregate_outcome = "strong"
            lowest_margin = None
            highest_difficulty = 10

            for observer in self.get_room_observers():
                result = run_contest(self.get_stealth_total(), observer.get_perception_total(), attacker=self, defender=observer)
                outcome = result["outcome"]
                highest_difficulty = max(highest_difficulty, int(observer.get_perception_total() or 0))
                margin = int(result.get("diff", 0) or 0)
                if lowest_margin is None or margin < lowest_margin:
                    lowest_margin = margin
                if outcome_rank.get(outcome, 0) < outcome_rank.get(aggregate_outcome, 0):
                    aggregate_outcome = outcome

                if outcome == "fail":
                    reveal_ids.append(observer.id)
                    continue

                if outcome == "partial":
                    partial_ids.append(observer.id)

            self.ndb.sneak_reveal_observer_ids = reveal_ids
            self.ndb.sneak_partial_observer_ids = partial_ids
            self.ndb.sneak_result = {"outcome": aggregate_outcome, "diff": lowest_margin if lowest_margin is not None else 0}
            self.ndb.sneak_difficulty = highest_difficulty
        return True

    def announce_move_from(self, destination, **kwargs):
        origin = self.location
        if not origin:
            return

        direction = getattr(self.ndb, "last_traverse_direction", None)
        if self.ndb.sneak_move_active and self.is_sneaking() and direction:
            reveal_ids = set(self.ndb.sneak_reveal_observer_ids or [])
            partial_ids = set(self.ndb.sneak_partial_observer_ids or [])
            for observer in origin.contents:
                if observer == self or not hasattr(observer, "msg"):
                    continue
                if getattr(observer, "id", None) in reveal_ids:
                    observer.msg(f"{self.key} slips {direction}, trying to remain unnoticed.")
                elif getattr(observer, "id", None) in partial_ids:
                    observer.msg("You notice movement nearby.")
            return

        super().announce_move_from(destination, **kwargs)

    def at_post_move(self, source_location, **kwargs):
        super().at_post_move(source_location, **kwargs)
        sync_subject_interest(self, previous_room=source_location)
        try:
            from systems.onboarding import handle_room_entry

            handle_room_entry(self)
        except Exception:
            pass
        try:
            from systems.first_area import handle_room_entry as handle_first_area_entry

            handle_first_area_entry(self)
        except Exception:
            pass
        if self.is_in_shrine():
            self.msg("This is a place where your fate can be secured.")
        injuries = getattr(self.db, "injuries", None)
        if isinstance(injuries, Mapping):
            now = time.time()
            for part_name in BODY_PART_ORDER:
                body_part = injuries.get(part_name)
                if not body_part:
                    continue
                if "bleeding" in body_part and "bleed" not in body_part:
                    body_part["bleed"] = body_part.pop("bleeding")
                else:
                    body_part.pop("bleeding", None)
                body_part.pop("hp", None)
                body_part.pop("max_hp", None)
                tend_state = body_part.get("tend") or {"strength": 0, "duration": 0, "min_until": 0.0}
                duration = int(tend_state.get("duration", 0))
                if duration <= 0 or now < float(tend_state.get("min_until", 0.0)):
                    continue
                tend_state["duration"] = max(0, duration - 1)
                body_part["tend"] = tend_state
                body_part["tended"] = tend_state["duration"] > 0 or now < float(tend_state.get("min_until", 0.0))

        direction = getattr(self.ndb, "last_traverse_direction", None)
        if self.ndb.sneak_move_active and self.is_sneaking() and direction:
            self.msg(f"You move quietly to the {direction}.")
            self.set_fatigue((self.db.fatigue or 0) + 2)
            self.record_stealth_contest(
                "sneak",
                max(10, int(getattr(self.ndb, "sneak_difficulty", 10) or 10)),
                result=getattr(self.ndb, "sneak_result", None),
                target=source_location,
                roundtime=STEALTH_MOVE_ROUNDTIME,
                event_key="stealth",
                require_hidden=True,
            )

        if self.is_stalking():
            target_id = self.get_stalk_target_id()
            target = next((obj for obj in (self.location.contents if self.location else []) if obj.id == target_id), None)
            if target:
                self.msg(f"You continue stalking {target.key}.")
                hidden = self.get_state("hidden") or {}
                if isinstance(hidden, Mapping):
                    hidden["strength"] = hidden.get("strength", 10) + 2
                    self.set_state("hidden", hidden)
                self.set_fatigue((self.db.fatigue or 0) + 1)
            else:
                self.clear_state("stalking")
                self.msg("You lose your target.")

        self.detect_traps_in_room()

        self.sync_client_state(include_map=True, include_subsystem=False, include_character=False)

        self.ndb.sneak_move_active = False
        self.ndb.sneak_partial_observer_ids = []
        self.ndb.sneak_reveal_observer_ids = []
        self.ndb.sneak_result = None
        self.ndb.sneak_difficulty = 0
        self.ndb.last_traverse_direction = None

    def get_status(self):
        self.ensure_core_defaults()
        return {
            "hp": self.db.hp,
            "max_hp": self.db.max_hp,
            "bleeding": self.is_bleeding(),
            "bleed_state": self.db.bleed_state,
            "in_combat": self.db.in_combat,
            "target": self.db.target.key if self.db.target else None,
        }

    def get_bleeding_summary(self):
        self.ensure_core_defaults()
        bleeding_parts = self.get_bleeding_parts()
        if not bleeding_parts:
            return "none"

        severity = self.get_bleed_severity(self.get_total_bleed())
        parts = ", ".join(entry["display"].lower() for entry in bleeding_parts)
        return f"{severity} ({parts})"

    def get_engagement_summary(self):
        self.ensure_core_defaults()
        self.sync_combat_state()
        if not self.db.in_combat or not self.db.target:
            return "You are not engaged in combat."
        return f"You are engaged with {self.db.target.key} at {self.get_range(self.db.target)} range."
