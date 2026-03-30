"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from collections.abc import Mapping
import math
import re
import random
import time

from evennia import search_object
from evennia.objects.objects import DefaultCharacter
from evennia.utils.create import create_object

from typeclasses.abilities import get_ability
from typeclasses.lockpick import Lockpick
from typeclasses.spells import SPELLS, SPELLCASTING_GUILDS
from typeclasses.study_item import StudyItem
from typeclasses.trap_device import TrapDevice
from utils.contests import run_contest
from utils.survival_loot import create_harvest_bundle, create_simple_item
from utils.survival_messaging import msg_room
from world.area_forge.character_api import send_character_update, send_subsystem_update
from world.area_forge.map_api import send_map_update
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

from .objects import ObjectParent


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

VALID_GUILDS = tuple(PROFESSION_PROFILES.keys())

LIFE_STATE_ALIVE = "ALIVE"
LIFE_STATE_DEAD = "DEAD"
LIFE_STATE_DEPARTED = "DEPARTED"

DEAD_STATE_ALLOWED_COMMANDS = {
    "depart",
    "favor",
    "health",
    "help",
    "hp",
    "l",
    "look",
    "pose",
    "raise",
    "resurrect",
    "say",
    "sta",
    "stats",
    "whisper",
    "xp",
}

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
    "outdoorsmanship": {"category": "survival", "visibility": "shared", "description": "foraging, wilderness interaction, and natural gathering", "starter_rank": 0},
    "perception": {"category": "survival", "visibility": "shared", "description": "noticing hidden threats, traps, and subtle details", "starter_rank": 1},
    "plate_armor": {"category": "armor", "visibility": "shared", "description": "training in plate armor use", "starter_rank": 0},
    "polearm": {"category": "combat", "visibility": "shared", "description": "fighting with polearms", "starter_rank": 0},
    "appraisal": {"category": "lore", "visibility": "shared", "description": "evaluating items, creatures, and value", "starter_rank": 1},
    "scholarship": {"category": "lore", "visibility": "shared", "description": "improves learning and knowledge systems", "starter_rank": 0},
    "tactics": {"category": "lore", "visibility": "shared", "description": "improves combat awareness and positioning", "starter_rank": 0},
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

DEFAULT_INJURIES = {
    "head": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 100, "vital": True},
    "chest": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 120, "vital": True},
    "abdomen": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 110, "vital": True},
    "back": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 110, "vital": True},
    "left_arm": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 80, "vital": False},
    "right_arm": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 80, "vital": False},
    "left_hand": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 60, "vital": False},
    "right_hand": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 60, "vital": False},
    "left_leg": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 90, "vital": False},
    "right_leg": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 90, "vital": False},
}

BODY_PART_ORDER = tuple(DEFAULT_INJURIES.keys())

DEFAULT_WEAPON_PROFILE = {
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
    "vitality": 0,
    "bleeding": 0,
    "fatigue": 0,
    "trauma": 0,
    "poison": 0,
    "disease": 0,
}

EMPATH_WOUND_LABELS = {
    "vitality": "Vitality",
    "bleeding": "Bleeding",
    "fatigue": "Fatigue",
    "trauma": "Trauma",
    "poison": "Poison",
    "disease": "Disease",
}

EMPATH_WOUND_ALIASES = {
    "health": "vitality",
}

EMPATH_TRANSFER_CONFIG = {
    "vitality": {"default": 18, "efficiency": 1.0, "self_tax": 0.10, "risk": 0.12},
    "bleeding": {"default": 26, "efficiency": 1.1, "self_tax": 0.25, "risk": 0.28},
    "fatigue": {"default": 24, "efficiency": 1.2, "self_tax": 0.05, "risk": 0.06},
    "trauma": {"default": 12, "efficiency": 0.75, "self_tax": 0.18, "risk": 0.22},
    "poison": {"default": 14, "efficiency": 0.85, "self_tax": 0.20, "risk": 0.26},
    "disease": {"default": 10, "efficiency": 0.80, "self_tax": 0.16, "risk": 0.20},
}

EMPATH_LINK_TOUCH = "touch"
EMPATH_LINK_STANDARD = "link"
EMPATH_LINK_PERSISTENT = "persistent"
EMPATH_LINK_GROUP = "group"
EMPATH_LINK_TYPES = {
    EMPATH_LINK_TOUCH,
    EMPATH_LINK_STANDARD,
    EMPATH_LINK_PERSISTENT,
    EMPATH_LINK_GROUP,
}
EMPATH_LINK_PRIORITY = {
    EMPATH_LINK_GROUP: 0,
    EMPATH_LINK_TOUCH: 1,
    EMPATH_LINK_STANDARD: 2,
    EMPATH_LINK_PERSISTENT: 3,
}
EMPATH_LINK_DURATIONS = {
    EMPATH_LINK_TOUCH: 30,
    EMPATH_LINK_STANDARD: 120,
    EMPATH_LINK_PERSISTENT: 300,
    EMPATH_LINK_GROUP: 90,
}
EMPATH_LINK_BASE_STRENGTH = {
    EMPATH_LINK_TOUCH: 30,
    EMPATH_LINK_STANDARD: 55,
    EMPATH_LINK_PERSISTENT: 70,
    EMPATH_LINK_GROUP: 45,
}
EMPATH_UNITY_MAX_TARGETS = 3
EMPATH_UNITY_DURATION = 90
EMPATH_UNITY_SHARE_RATIO = 0.4
EMPATH_SYSTEM_CONFIG = {
    "shock_penalties": {
        "major_threshold": 80,
        "medium_threshold": 50,
        "minor_threshold": 20,
        "major_modifier": 0.4,
        "medium_modifier": 0.7,
        "minor_modifier": 0.9,
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
        "fatigue_reduction": 14,
        "shock_reduction": 6,
        "wound_reduction": 8,
        "roundtime": 2.5,
        "overdraw_clear_shock_threshold": 18,
        "overdraw_clear_fatigue_threshold": 50,
    },
}

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
        self.db.guild = None
        self.db.profession = "commoner"
        self.db.profession_rank = 1
        self.db.wilderness_bond = 50
        self.db.ranger_instinct = 0
        self.db.nature_focus = 0
        self.db.ranger_companion = normalize_ranger_companion()
        self.db.empath_shock = 0
        self.db.active_link = None
        self.db.empath_links = {}
        self.db.empath_unity = None
        self.db.wounds = _copy_default_empath_wounds()
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
        self.db.is_captured = False
        self.db.confiscated_items = []
        self.db.fine_amount = 0
        self.db.fine_due = 0
        self.db.collateral_locked = False
        self.db.fine_due_timestamp = None
        self.db.sentence_type = None
        self.db.jail_timer = 0
        self.db.in_stocks = False
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
        self.get_subsystem()
        for skill_name, baseline_rank in AVAILABLE_SKILL_BASELINES.items():
            self.learn_skill(skill_name, {"rank": baseline_rank, "mindstate": 0})

    def at_post_puppet(self, **kwargs):
        super().at_post_puppet(**kwargs)
        self.ensure_core_defaults()
        self.get_subsystem()
        self.sync_client_state(include_map=True)

    def at_post_unpuppet(self, **kwargs):
        super().at_post_unpuppet(**kwargs)
        self.reset_thief_pressure_states()

    def at_after_move(self, source_location, **kwargs):
        super().at_after_move(source_location, **kwargs)
        self.ndb.is_busy = False
        self.ndb.is_walking = False
        if getattr(self.db, "slipping", False):
            self.db.slip_bonus = int(getattr(self.db, "slip_bonus", 0) or 0) + 5
            self.db.escape_chain = int(getattr(self.db, "escape_chain", 0) or 0) + 1
        self.sync_client_state(include_map=True)
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

    def sync_client_state(self, include_map=False, session=None):
        sessions_attr = getattr(self, "sessions", None)
        sessions = [session] if session else list(sessions_attr.all()) if sessions_attr else []
        if not sessions:
            return
        if include_map:
            send_map_update(self, session=session)
        send_subsystem_update(self, session=session)
        send_character_update(self, session=session)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if getattr(moved_obj, "destination", None) is None:
            self.sync_client_state()

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        super().at_object_leave(moved_obj, target_location, **kwargs)
        if getattr(moved_obj, "destination", None) is None:
            self.sync_client_state()

    def ensure_identity_defaults(self):
        if self.db.gender is None:
            self.db.gender = "unknown"
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
        if self.db.active_link is None:
            self.db.active_link = None
        empath_links_missing = self.db.empath_links is None
        if empath_links_missing:
            self.db.empath_links = {}
        if self.db.empath_unity is None:
            self.db.empath_unity = None
        if getattr(self.db, "active_link", None) and empath_links_missing:
            legacy_target_id = int(getattr(self.db, "active_link", 0) or 0)
            if legacy_target_id > 0:
                now = time.time()
                self.db.empath_links = {
                    str(legacy_target_id): {
                        "target_id": legacy_target_id,
                        "type": EMPATH_LINK_TOUCH,
                        "created_at": now,
                        "expires_at": now + EMPATH_LINK_DURATIONS[EMPATH_LINK_TOUCH],
                    }
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
        if self.db.favor is None:
            self.db.favor = 0
        if self.db.death_favor_snapshot is None:
            self.db.death_favor_snapshot = None
        if self.db.last_corpse_id is None:
            self.db.last_corpse_id = None
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
        if self.db.fine_amount is None:
            self.db.fine_amount = 0
        if self.db.fine_due is None:
            self.db.fine_due = 0
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
        if self.db.bleed_state is None:
            self.db.bleed_state = "none"
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

        if skills != current_skills:
            self.db.skills = skills

    def ensure_core_defaults(self):
        self.ensure_identity_defaults()
        self.ensure_stat_defaults()
        self.ensure_resource_defaults()
        self.ensure_combat_defaults()
        self.ensure_equipment_defaults()
        self.ensure_injury_defaults()
        self.ensure_skill_defaults()
        self.ensure_starter_skills()
        if "awareness" not in (self.db.states or {}):
            states = dict(self.db.states or {})
            states["awareness"] = "normal"
            self.db.states = states

    def ensure_appearance_defaults(self):
        self.ensure_identity_defaults()
        self.ensure_resource_defaults()
        self.ensure_combat_defaults()

    def get_hp(self):
        self.ensure_core_defaults()
        return self.db.hp, self.db.max_hp

    def set_hp(self, value):
        self.ensure_core_defaults()
        old_hp = int(self.db.hp or 0)
        self.db.hp = max(0, min(value, self.db.max_hp))
        if (self.db.hp or 0) <= 0:
            self.db.is_dead = True
        if old_hp > 0 and (self.db.hp or 0) <= 0:
            self.at_death()
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

    def get_favor(self):
        self.ensure_core_defaults()
        return max(0, int(getattr(self.db, "favor", 0) or 0))

    def set_favor(self, value, emit_message=False):
        self.ensure_core_defaults()
        before = self.get_favor()
        self.db.favor = max(0, int(value or 0))
        if emit_message and self.db.favor < before:
            self.msg("A thread of divine favor is consumed.")
        self.sync_client_state()
        return self.db.favor

    def adjust_favor(self, amount, emit_message=False):
        return self.set_favor(self.get_favor() + int(amount or 0), emit_message=emit_message)

    def get_favor_state(self, favor=None):
        value = self.get_favor() if favor is None else max(0, int(favor or 0))
        if value <= 0:
            return "unprepared"
        if value <= 5:
            return "vulnerable"
        if value <= 15:
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
        self.db.deaths_since_last_shrine = 0
        self.db.last_prayed_shrine_at = time.time()
        return True, "You kneel and prepare an offering."

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

    def get_favor_death_consumption(self):
        config = FAVOR_SYSTEM_CONFIG
        streak = min(int(config["death_favor_consumption_streak_cap"]), int(getattr(self.db, "deaths_since_last_shrine", 0) or 0))
        return int(config["death_favor_consumption_base"]) + (streak * int(config["death_favor_consumption_streak_bonus"]))

    def handle_favor_death_event(self):
        favor_before = self.get_favor()
        consumed = min(favor_before, self.get_favor_death_consumption()) if favor_before > 0 else 0
        if consumed > 0:
            self.adjust_favor(-consumed, emit_message=True)
        self.db.deaths_since_last_shrine = int(getattr(self.db, "deaths_since_last_shrine", 0) or 0) + 1
        remaining = self.get_favor()
        self.db.death_favor_snapshot = {
            "favor_before": favor_before,
            "favor_consumed": consumed,
            "favor_remaining": remaining,
            "soul_decay_rate": self.get_soul_decay_rate(favor=favor_before),
            "soul_strength_floor": self.get_soul_strength_floor(favor=favor_before),
            "resurrection": self.get_resurrection_favor_profile(favor=favor_before),
            "captured_at": time.time(),
            "must_depart": favor_before <= 0,
        }
        if favor_before <= 0:
            self.msg("You have no anchor to return. You must depart.")
        elif favor_before >= int(FAVOR_SYSTEM_CONFIG["high_favor_threshold"]):
            self.msg("The divine bond strengthens your return.")
            self.msg("Your soul remains firmly tethered.")
        elif favor_before <= int(FAVOR_SYSTEM_CONFIG["low_favor_threshold"]):
            self.msg("Your return is strained and uncertain.")
            self.msg("Your soul feels tenuous and unanchored.")

    def get_favor_death_snapshot(self):
        self.ensure_core_defaults()
        snapshot = getattr(self.db, "death_favor_snapshot", None)
        return dict(snapshot) if isinstance(snapshot, Mapping) else None

    def can_attempt_resurrection(self):
        snapshot = self.get_favor_death_snapshot()
        if isinstance(snapshot, Mapping):
            return not bool(snapshot.get("must_depart", False)) and bool((snapshot.get("resurrection") or {}).get("can_resurrect", False))
        return self.get_favor() > 0

    def get_death_attunement_cost(self, snapshot=None):
        profile = ((snapshot or self.get_favor_death_snapshot() or {}).get("resurrection") or {}) if isinstance(snapshot or self.get_favor_death_snapshot(), Mapping) else {}
        reduction = min(0.75, max(0.0, float(profile.get("cost_reduction", 0.0) or 0.0)))
        return max(5, int(round(float(FAVOR_SYSTEM_CONFIG["resurrection_base_attunement_cost"]) * (1.0 - reduction))))

    def get_death_corpse(self):
        corpse_id = int(getattr(self.db, "last_corpse_id", 0) or 0)
        if corpse_id <= 0:
            return None
        result = search_object(f"#{corpse_id}")
        corpse = result[0] if result else None
        if not corpse or not getattr(corpse.db, "is_corpse", False):
            self.db.last_corpse_id = None
            return None
        return corpse

    def create_death_corpse(self):
        corpse = self.get_death_corpse()
        if corpse and corpse.location == self.location:
            return corpse
        corpse = create_object(
            "typeclasses.corpse.Corpse",
            key=f"corpse of {self.key}",
            location=self.location,
            home=self.location,
        )
        corpse.db.owner_id = self.id
        corpse.db.owner_name = self.key
        corpse.db.death_timestamp = time.time()
        corpse.db.decay_time = time.time() + (30 * 60)
        corpse.db.favor_snapshot = self.get_favor_death_snapshot()
        corpse.db.desc = f"The lifeless body of {self.key} lies here."
        self.db.last_corpse_id = corpse.id
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

    def at_death(self):
        self.ensure_core_defaults()
        if self.db.life_state == LIFE_STATE_DEAD:
            return None
        self.db.life_state = LIFE_STATE_DEAD
        self.db.is_dead = True
        self.db.in_combat = False
        self.db.target = None
        self.db.aiming = None
        self.handle_favor_death_event()
        corpse = self.create_death_corpse()
        self.move_carried_items_to_corpse(corpse)
        if self.location:
            self.location.msg_contents(f"{self.key} collapses and dies.", exclude=[self])
        self.msg("You have died.")
        return corpse

    def revive_from_death(self, via="depart"):
        self.ensure_core_defaults()
        restore_ratio = float(FAVOR_SYSTEM_CONFIG["resurrection_restore_hp_ratio"] if via == "resurrection" else FAVOR_SYSTEM_CONFIG["depart_restore_hp_ratio"])
        self.db.life_state = LIFE_STATE_ALIVE
        self.db.is_dead = False
        self.db.in_combat = False
        self.db.target = None
        self.db.hp = max(1, int(round((self.db.max_hp or 1) * restore_ratio)))
        self.db.balance = max(0, int(round((self.db.max_balance or 1) * 0.5)))
        self.db.fatigue = min(self.db.max_fatigue or 100, max(int(self.db.fatigue or 0), int(round((self.db.max_fatigue or 100) * 0.35))))
        self.db.stunned = False
        self.sync_empath_wounds_from_resources()
        self.sync_client_state()
        return True

    def get_depart_mode(self, corpse=None, requested_mode=None):
        snapshot = None
        if corpse and hasattr(corpse, "get_favor_snapshot"):
            snapshot = corpse.get_favor_snapshot()
        if not isinstance(snapshot, Mapping):
            snapshot = self.get_favor_death_snapshot() or {}
        available_favor = int(snapshot.get("favor_before", 0) or 0)
        requested = str(requested_mode or "").strip().lower()
        default_mode = "full" if available_favor >= 3 else "items" if available_favor >= 2 else "grave"
        if not requested:
            return default_mode
        requirements = {"grave": 0, "coins": 2, "items": 2, "full": 3}
        if requested not in requirements:
            return None
        if available_favor < requirements[requested]:
            return None
        return requested

    def depart_self(self, mode=None):
        if not self.is_dead():
            return False, "You are not dead."
        corpse = self.get_death_corpse()
        depart_mode = self.get_depart_mode(corpse=corpse, requested_mode=mode)
        if depart_mode is None:
            return False, "You do not have enough favor for that kind of departure."
        keep_items = depart_mode in {"items", "full"}
        keep_coins = depart_mode in {"coins", "full"}
        if corpse and keep_items:
            for item in list(corpse.contents):
                item.move_to(self, quiet=True)
        if not keep_coins:
            self.db.coins = 0
        destination = self.home or self.location
        if destination and self.location != destination:
            self.move_to(destination, quiet=True)
        self.db.life_state = LIFE_STATE_DEPARTED
        self.revive_from_death(via="depart")
        self.db.life_state = LIFE_STATE_ALIVE
        if corpse and (keep_items or not corpse.contents):
            corpse.delete()
            self.clear_death_corpse_link()
        return True, f"You depart and return to life by the {depart_mode} path."

    def resurrect_from_corpse(self, corpse, caster=None):
        if not corpse or not getattr(corpse.db, "is_corpse", False):
            return False, "That is not a corpse that can be restored."
        if hasattr(corpse, "get_owner"):
            owner = corpse.get_owner()
        else:
            owner = None
        if not owner:
            return False, "No soul remains tied to that corpse."
        snapshot = corpse.get_favor_snapshot() if hasattr(corpse, "get_favor_snapshot") else owner.get_favor_death_snapshot()
        if not isinstance(snapshot, Mapping):
            return False, "The corpse holds no viable soul pattern."
        res_profile = dict(snapshot.get("resurrection") or {})
        if not bool(res_profile.get("can_resurrect", False)):
            return False, "They have no anchor to return by resurrection."
        if caster is not None:
            if hasattr(caster, "is_profession") and not caster.is_profession("cleric"):
                return False, "Only a cleric can guide that return."
            attunement_cost = owner.get_death_attunement_cost(snapshot=snapshot)
            if hasattr(caster, "spend_attunement") and not caster.spend_attunement(attunement_cost):
                return False, "You lack the attunement to complete the rite."
        owner.revive_from_death(via="resurrection")
        if owner.location != corpse.location and corpse.location:
            owner.move_to(corpse.location, quiet=True)
        for item in list(corpse.contents):
            item.move_to(owner, quiet=True)
        owner.db.death_favor_snapshot = None
        owner.db.last_corpse_id = None
        corpse.delete()
        if int(snapshot.get("favor_before", 0) or 0) >= int(FAVOR_SYSTEM_CONFIG["high_favor_threshold"]):
            owner.msg("The divine bond strengthens your return.")
        elif int(snapshot.get("favor_before", 0) or 0) <= int(FAVOR_SYSTEM_CONFIG["low_favor_threshold"]):
            owner.msg("Your return is strained and uncertain.")
        return True, f"{owner.key} is restored to life."

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
        if new_state != old_state:
            message = self.get_empath_shock_message(new_state)
            if message:
                self.msg(message)
        self.sync_client_state()
        return self.db.empath_shock

    def adjust_empath_shock(self, amount):
        return self.set_empath_shock(self.get_empath_shock() + int(amount or 0))

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

    def get_empath_shock_state(self, shock=None):
        value = self.get_empath_shock() if shock is None else max(0, min(100, int(shock or 0)))
        if value >= 80:
            return "numb"
        if value >= 50:
            return "disconnected"
        if value >= 20:
            return "dulled"
        return "clear"

    def get_empath_shock_message(self, shock_state):
        return {
            "clear": "Your empathy steadies again.",
            "dulled": "Your connection dulls.",
            "disconnected": "You feel disconnected from others.",
            "numb": "You struggle to sense clearly.",
        }.get(str(shock_state or "").strip().lower(), "")

    def normalize_empath_wound_key(self, wound_type):
        key = str(wound_type or "").strip().lower()
        return EMPATH_WOUND_ALIASES.get(key, key)

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

    def get_empath_recovery_modifier(self):
        disease = self.get_empath_wound("disease") if hasattr(self, "get_empath_wound") else 0
        if disease <= 0:
            return 1.0
        return max(0.35, 1.0 - (int(disease) / 140.0))

    def get_empath_healing_modifier(self):
        return self.get_empath_shock_modifier() * self.get_empath_recovery_modifier()

    def normalize_empath_link_type(self, link_type):
        normalized = str(link_type or EMPATH_LINK_TOUCH).strip().lower()
        if normalized in {"standard", "deep", "strong"}:
            normalized = EMPATH_LINK_STANDARD
        if normalized not in EMPATH_LINK_TYPES:
            normalized = EMPATH_LINK_TOUCH
        return normalized

    def get_empath_link_priority(self, link_type):
        return int(EMPATH_LINK_PRIORITY.get(self.normalize_empath_link_type(link_type), 0) or 0)

    def normalize_empath_links(self, links=None):
        source = dict(links or {})
        normalized = {}
        for raw_key, raw_data in source.items():
            if not isinstance(raw_data, Mapping):
                continue
            target_id = int(raw_data.get("target_id", raw_key) or 0)
            if target_id <= 0:
                continue
            link_type = self.normalize_empath_link_type(raw_data.get("type"))
            created_at = float(raw_data.get("created_at", time.time()) or time.time())
            expires_at = float(raw_data.get("expires_at", 0) or 0)
            if expires_at <= 0:
                expires_at = created_at + float(EMPATH_LINK_DURATIONS.get(link_type, 30) or 30)
            normalized[str(target_id)] = {
                "target_id": target_id,
                "type": link_type,
                "created_at": created_at,
                "expires_at": expires_at,
                "deepened": bool(raw_data.get("deepened", False)),
            }
        return normalized

    def get_empath_link_target(self, target_id):
        lookup_id = int(target_id or 0)
        if lookup_id <= 0:
            return None
        result = search_object(f"#{lookup_id}")
        return result[0] if result else None

    def get_empath_link_strength(self, link_data, target=None):
        if not isinstance(link_data, Mapping):
            return 0
        config = EMPATH_SYSTEM_CONFIG["link_strength"]
        link_type = self.normalize_empath_link_type(link_data.get("type"))
        created_at = float(link_data.get("created_at", 0) or 0)
        expires_at = float(link_data.get("expires_at", 0) or 0)
        elapsed = max(0.0, time.time() - created_at)
        base_strength = int(EMPATH_LINK_BASE_STRENGTH.get(link_type, 30) or 30)
        time_bonus = min(int(config["max_time_bonus"]), int(elapsed / float(config["time_bonus_scale"])))
        shock_penalty = int(self.get_empath_shock() * 0.35)
        fatigue_penalty = int(self.get_empath_wound("fatigue") * 0.20)
        if target and getattr(target, "location", None) == getattr(self, "location", None):
            proximity_bonus = int(config["local_bonus"])
        else:
            proximity_bonus = 0 if link_type == EMPATH_LINK_PERSISTENT else -int(config["remote_nonpersistent_penalty"])
        deepen_bonus = int(config["deepen_bonus"] if bool(link_data.get("deepened", False)) else 0)
        default_duration = max(1.0, float(EMPATH_LINK_DURATIONS.get(link_type, 30) or 30))
        remaining_ratio = max(0.0, min(1.0, (expires_at - time.time()) / default_duration)) if expires_at else 1.0
        decay_penalty = int(round((1.0 - remaining_ratio) * float(config["decay_penalty_max"])))
        return max(1, min(100, base_strength + time_bonus + proximity_bonus + deepen_bonus - decay_penalty - shock_penalty - fatigue_penalty))

    def get_empath_link_strength_label(self, strength):
        value = max(0, min(100, int(strength or 0)))
        if value >= 75:
            return "Strong"
        if value >= 45:
            return "Steady"
        if value >= 20:
            return "Weak"
        return "Fraying"

    def sync_empath_link_pointer(self):
        primary = self.get_primary_empath_link(require_local=False, include_group=False)
        self.db.active_link = int(primary.get("target_id", 0) or 0) if primary else None

    def set_empath_links(self, links, sync=True):
        self.db.empath_links = self.normalize_empath_links(links)
        self.sync_empath_link_pointer()
        if sync:
            self.sync_client_state()
        return dict(self.db.empath_links)

    def prune_empath_links(self, sync=False):
        self.ensure_core_defaults()
        now = time.time()
        changed = False
        shock_break = self.get_empath_shock() >= 85
        current = self.normalize_empath_links(getattr(self.db, "empath_links", None) or {})
        kept = {}
        for link_data in current.values():
            target = self.get_empath_link_target(link_data.get("target_id"))
            if not target or target == self:
                changed = True
                continue
            link_type = self.normalize_empath_link_type(link_data.get("type"))
            expires_at = float(link_data.get("expires_at", 0) or 0)
            if expires_at and now >= expires_at:
                changed = True
                continue
            if shock_break:
                changed = True
                continue
            if link_type != EMPATH_LINK_PERSISTENT and getattr(target, "location", None) != getattr(self, "location", None):
                changed = True
                continue
            kept[str(target.id)] = dict(link_data)
        if changed or len(kept) != len(current):
            self.db.empath_links = kept
            self.sync_empath_link_pointer()
            if sync:
                self.sync_client_state()
        return dict(self.db.empath_links)

    def get_empath_links(self, require_local=False, include_group=False):
        self.ensure_core_defaults()
        links = self.prune_empath_links(sync=False)
        enriched = []
        for link_data in links.values():
            link_type = self.normalize_empath_link_type(link_data.get("type"))
            if not include_group and link_type == EMPATH_LINK_GROUP:
                continue
            target = self.get_empath_link_target(link_data.get("target_id"))
            if not target:
                continue
            is_local = getattr(target, "location", None) == getattr(self, "location", None)
            if require_local and not is_local:
                continue
            strength = self.get_empath_link_strength(link_data, target=target)
            enriched.append(
                {
                    **dict(link_data),
                    "target": target,
                    "is_local": is_local,
                    "priority": self.get_empath_link_priority(link_type),
                    "strength": strength,
                    "strength_label": self.get_empath_link_strength_label(strength),
                    "remaining": max(0, int(round(float(link_data.get("expires_at", 0) or 0) - time.time()))),
                }
            )
        enriched.sort(
            key=lambda entry: (
                1 if entry.get("is_local") else 0,
                1 if entry.get("deepened") else 0,
                self.get_empath_link_priority(entry.get("type")),
                int(entry.get("strength", 0) or 0),
                float(entry.get("created_at", 0) or 0),
            ),
            reverse=True,
        )
        return enriched

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
        primary = self.get_primary_empath_link(require_local=False, include_group=False)
        if not primary:
            return 0.85
        if target is not None and getattr(primary.get("target"), "id", None) != getattr(target, "id", None):
            primary = next((entry for entry in self.get_empath_links(require_local=False, include_group=False) if getattr(entry.get("target"), "id", None) == getattr(target, "id", None)), None)
            if not primary:
                return 0.85
        strength = int(primary.get("strength", 0) or 0)
        config = EMPATH_SYSTEM_CONFIG["transfer"]
        bonus = strength / max(1.0, float(config["strength_scale"]))
        if bool(primary.get("deepened", False)):
            bonus += 0.08
        return max(float(config["min_efficiency"]), min(float(config["max_efficiency"]), float(config["min_efficiency"]) + bonus))

    def get_empath_link_backlash_modifier(self, target=None):
        primary = self.get_primary_empath_link(require_local=False, include_group=False)
        if not primary:
            return 1.1
        if target is not None and getattr(primary.get("target"), "id", None) != getattr(target, "id", None):
            primary = next((entry for entry in self.get_empath_links(require_local=False, include_group=False) if getattr(entry.get("target"), "id", None) == getattr(target, "id", None)), None)
            if not primary:
                return 1.1
        strength = int(primary.get("strength", 0) or 0)
        config = EMPATH_SYSTEM_CONFIG["backlash"]
        reduction = strength / max(1.0, float(config["strength_scale"]))
        if bool(primary.get("deepened", False)):
            reduction += 0.08
        return max(float(config["min"]), min(float(config["max"]), float(config["max"]) - reduction))

    def refresh_empath_link(self, target, bonus_seconds=0, deepen=False):
        links = self.normalize_empath_links(getattr(self.db, "empath_links", None) or {})
        target_id = int(getattr(target, "id", target) or 0)
        if target_id <= 0 or str(target_id) not in links:
            return None
        link_data = dict(links[str(target_id)])
        link_type = self.normalize_empath_link_type(link_data.get("type"))
        link_data["expires_at"] = time.time() + float(EMPATH_LINK_DURATIONS.get(link_type, 30) or 30) + float(bonus_seconds or 0)
        if deepen:
            link_data["deepened"] = True
        links[str(target_id)] = link_data
        self.set_empath_links(links, sync=False)
        return link_data

    def create_empath_link(self, target, link_type=EMPATH_LINK_TOUCH, deepen=False):
        if not self.is_empath():
            return False, ["You lack the sensitivity to establish an empathic link."]
        if not target or target == self or getattr(target, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        link_type = self.normalize_empath_link_type(link_type)
        now = time.time()
        links = self.normalize_empath_links(getattr(self.db, "empath_links", None) or {})
        existing = dict(links.get(str(target.id), {}) or {})
        existing_type = self.normalize_empath_link_type(existing.get("type")) if existing else None
        if existing and self.get_empath_link_priority(existing_type) > self.get_empath_link_priority(link_type):
            link_type = existing_type
        created_at = float(existing.get("created_at", now) or now)
        if existing_type != link_type:
            created_at = now
        links[str(target.id)] = {
            "target_id": target.id,
            "type": link_type,
            "created_at": created_at,
            "expires_at": now + float(EMPATH_LINK_DURATIONS.get(link_type, 30) or 30),
            "deepened": bool(existing.get("deepened", False) or deepen),
        }
        self.set_empath_links(links, sync=False)
        self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=max(10, sum(target.sync_empath_wounds_from_resources().values())))
        self.sync_client_state()
        return True, self.get_primary_empath_link(require_local=False, include_group=False)

    def resolve_empath_link_target(self, query, require_local=True):
        lookup = str(query or "").strip().lower()
        if not lookup:
            return None
        for entry in self.get_empath_links(require_local=require_local, include_group=False):
            target = entry.get("target")
            if not target:
                continue
            if target.key.lower() == lookup:
                return target
            aliases = [str(alias).lower() for alias in getattr(getattr(target, "aliases", None), "all", lambda: [])()]
            if lookup in aliases:
                return target
        return None

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
        links = self.normalize_empath_links(getattr(self.db, "empath_links", None) or {})
        if clear_all:
            changed = bool(links)
            links = {}
        else:
            if target is None:
                primary = self.get_primary_empath_link(require_local=False, include_group=False)
                target_id = int(primary.get("target_id", 0) or 0) if primary else 0
            else:
                target_id = int(getattr(target, "id", target) or 0)
            changed = bool(target_id and str(target_id) in links)
            if changed:
                links.pop(str(target_id), None)
        if changed:
            self.set_empath_links(links, sync=True)
        return changed

    def get_empath_unity_state(self):
        self.ensure_core_defaults()
        data = getattr(self.db, "empath_unity", None)
        if not isinstance(data, Mapping):
            return None
        expires_at = float(data.get("expires_at", 0) or 0)
        if expires_at and time.time() >= expires_at:
            self.clear_empath_unity(sync_members=True, emit_message=False)
            return None
        member_ids = [int(entry or 0) for entry in (data.get("member_ids") or []) if int(entry or 0) > 0]
        members = []
        for member_id in member_ids:
            target = self.get_empath_link_target(member_id)
            if not target or getattr(target, "location", None) != getattr(self, "location", None):
                continue
            members.append(target)
        if len(members) < 2:
            self.clear_empath_unity(sync_members=True, emit_message=False)
            return None
        return {**dict(data), "member_ids": member_ids, "members": members}

    def clear_empath_unity(self, sync_members=True, emit_message=False):
        unity = getattr(self.db, "empath_unity", None)
        if not isinstance(unity, Mapping):
            return False
        member_ids = [int(entry or 0) for entry in (unity.get("member_ids") or []) if int(entry or 0) > 0]
        self.db.empath_unity = None
        if sync_members:
            for member_id in member_ids:
                target = self.get_empath_link_target(member_id)
                if target and hasattr(target, "clear_state"):
                    target.clear_state("empath_unity")
        self.sync_client_state()
        if emit_message:
            self.msg("The shared bond unravels.")
        return True

    def create_empath_unity(self, targets):
        if not self.is_empath():
            return False, "You cannot weave that kind of bond."
        members = []
        seen = set()
        for target in list(targets or []):
            if not target or target == self or getattr(target, "location", None) != getattr(self, "location", None):
                continue
            if getattr(target, "id", None) in seen:
                continue
            seen.add(target.id)
            members.append(target)
        if len(members) < 2:
            return False, "You need at least two nearby allies to weave unity."
        if len(members) > EMPATH_UNITY_MAX_TARGETS:
            return False, f"You can only sustain unity across {EMPATH_UNITY_MAX_TARGETS} allies right now."
        expires_at = time.time() + EMPATH_UNITY_DURATION
        self.db.empath_unity = {
            "member_ids": [member.id for member in members],
            "created_at": time.time(),
            "expires_at": expires_at,
        }
        for member in members:
            if hasattr(member, "set_state"):
                member.set_state(
                    "empath_unity",
                    {
                        "anchor_id": self.id,
                        "member_ids": [ally.id for ally in members],
                        "expires_at": expires_at,
                    },
                )
        self.set_fatigue((self.db.fatigue or 0) + max(2, len(members)))
        self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=20 + (len(members) * 4))
        self.sync_client_state()
        return True, "You weave a shared bond between your allies."

    def redirect_empath_wound(self, wound_type, amount_spec, source_target, dest_target):
        if not self.is_empath():
            return False, "You cannot redirect pain that way."
        if self.is_empath_overdrawn():
            return False, "You have taken too much already. You cannot channel more pain right now."
        if not source_target or not dest_target or source_target == dest_target:
            return False, "You need two different linked patients for that."
        if getattr(source_target, "location", None) != getattr(self, "location", None) or getattr(dest_target, "location", None) != getattr(self, "location", None):
            return False, "Both patients must be here."
        if not self.resolve_empath_link_target(source_target.key, require_local=True) or not self.resolve_empath_link_target(dest_target.key, require_local=True):
            return False, "You need active links to both patients first."
        wound_key = self.normalize_empath_wound_key(wound_type)
        if wound_key not in DEFAULT_EMPATH_WOUNDS:
            return False, "You can only redirect vitality, bleeding, fatigue, trauma, poison, or disease."
        source_amount = source_target.get_empath_wound(wound_key)
        if source_amount <= 0:
            return False, f"{source_target.key} is not suffering from that wound."
        raw_spec = str(amount_spec or "").strip().lower()
        if raw_spec == "all":
            requested = source_amount
        else:
            try:
                requested = max(1, int(raw_spec or 10))
            except ValueError:
                return False, "Give a number or 'all'."
        moved = min(requested, source_amount)
        source_target.set_empath_wound(wound_key, source_amount - moved)
        dest_target.set_empath_wound(wound_key, dest_target.get_empath_wound(wound_key) + moved)
        redirect_cfg = EMPATH_SYSTEM_CONFIG["redirect"]
        strain = max(1, int(round(moved * float(redirect_cfg["strain_ratio"]))))
        fatigue_spike = max(int(redirect_cfg["fatigue_spike_min"]), int(round(moved * float(redirect_cfg["fatigue_ratio"]))))
        self.set_fatigue((self.db.fatigue or 0) + fatigue_spike)
        if wound_key in {"vitality", "bleeding", "trauma"}:
            self.set_empath_wound(wound_key, self.get_empath_wound(wound_key) + strain)
        else:
            self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") + max(1, strain // 2))
        risk = float(redirect_cfg["risk_base"]) + (moved / max(1.0, float(redirect_cfg["risk_scale"])))
        if random.random() < min(0.75, risk):
            self.set_fatigue((self.db.fatigue or 0) + max(2, fatigue_spike // 2))
            self.msg("The force of the redirection jars you badly.")
        self.refresh_empath_link(source_target, bonus_seconds=8)
        self.refresh_empath_link(dest_target, bonus_seconds=8)
        self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=16 + moved)
        self.maybe_trigger_empath_overdraw()
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
        if int(amount or 0) <= 1 or bool(getattr(self.ndb, "unity_share_in_progress", False)):
            return int(amount or 0)
        unity = self.get_empath_unity_effect()
        if not unity:
            return int(amount or 0)
        recipients = [member for member in unity.get("members", []) if member != self and getattr(member, "location", None) == getattr(self, "location", None)]
        if not recipients:
            return int(amount or 0)
        share_ratio = EMPATH_UNITY_SHARE_RATIO if len(recipients) > 1 else 0.3
        shared_total = max(1, min(int(amount or 0) - 1, int(round(int(amount or 0) * share_ratio))))
        if shared_total <= 0:
            return int(amount or 0)
        local_amount = max(1, int(amount or 0) - shared_total)
        per_target = shared_total // len(recipients)
        remainder = shared_total % len(recipients)
        anchor = unity.get("anchor")
        for index, recipient in enumerate(recipients):
            share_amount = per_target + (1 if index < remainder else 0)
            if share_amount <= 0:
                continue
            recipient.msg("You share part of the blow through your unity bond.")
            recipient.ndb.unity_share_in_progress = True
            try:
                recipient.apply_incoming_damage(location, share_amount, damage_type)
            finally:
                recipient.ndb.unity_share_in_progress = False
        self.msg("Your unity bond diffuses part of the blow.")
        if anchor and anchor != self:
            anchor.msg(f"You feel {self.key}'s pain spread across the shared bond.")
        return local_amount

    def apply_incoming_damage(self, location, amount, damage_type="impact"):
        self.ensure_core_defaults()
        final_amount = self.apply_empath_unity_share(location, int(amount or 0), damage_type=damage_type)
        if final_amount <= 0:
            return 0
        self.set_hp((self.db.hp or 0) - final_amount)
        self.apply_damage(location, final_amount, damage_type)
        return final_amount

    def process_empath_links(self):
        if not self.is_empath():
            return False
        now = time.time()
        self.prune_empath_links(sync=False)
        changed = False
        if self.get_empath_shock() >= 85:
            changed = self.remove_empath_link(clear_all=True) or changed
            if self.get_empath_unity_state():
                self.clear_empath_unity(sync_members=True, emit_message=True)
                changed = True
        unity = self.get_empath_unity_state()
        if now >= float(getattr(self.ndb, "next_empath_link_drain_at", 0) or 0):
            drain = len([entry for entry in self.get_empath_links(require_local=False, include_group=False) if entry.get("type") == EMPATH_LINK_PERSISTENT])
            if unity:
                drain += len(unity.get("member_ids", []))
            if drain > 0:
                self.set_fatigue((self.db.fatigue or 0) + drain)
            stress_config = EMPATH_SYSTEM_CONFIG["link_strength"]
            stress_load = self.get_empath_shock() + self.get_empath_wound("fatigue")
            extra_decay = min(int(stress_config["stress_decay_max"]), int(stress_load / max(1.0, float(stress_config["stress_decay_scale"]))))
            if extra_decay > 0:
                links = self.normalize_empath_links(getattr(self.db, "empath_links", None) or {})
                for link_id, link_data in list(links.items()):
                    link_type = self.normalize_empath_link_type(link_data.get("type"))
                    if link_type == EMPATH_LINK_GROUP:
                        continue
                    link_data = dict(link_data)
                    link_data["expires_at"] = max(now + 1.0, float(link_data.get("expires_at", now) or now) - extra_decay)
                    links[link_id] = link_data
                self.set_empath_links(links, sync=False)
            self.ndb.next_empath_link_drain_at = now + 12.0
        return changed

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
        self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=18 + max(0, int(target_score / 6)))
        return True, f"You press calm into {target.key}'s thoughts, easing their aggression."

    def get_empath_transfer_profile(self, wound_type):
        return dict(EMPATH_TRANSFER_CONFIG.get(self.normalize_empath_wound_key(wound_type), {}))

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
        max_hp = max(1, int(getattr(self.db, "max_hp", 100) or 100))
        hp = max(0, int(getattr(self.db, "hp", max_hp) or max_hp))
        max_fatigue = max(1, int(getattr(self.db, "max_fatigue", 100) or 100))
        fatigue = max(0, int(getattr(self.db, "fatigue", 0) or 0))
        wounds["vitality"] = max(0, min(100, int(round((1 - (hp / max_hp)) * 100))))
        wounds["fatigue"] = max(0, min(100, int(round((fatigue / max_fatigue) * 100))))
        wounds["trauma"] = self.get_empath_trauma_value()
        raw_bleed = self.get_total_bleed()
        effective_bleed = self.get_effective_bleed_total() if hasattr(self, "get_effective_bleed_total") else raw_bleed
        bleeding_from_injuries = max(0, min(100, int(effective_bleed * 5)))
        cached_bleeding = max(0, min(100, int(wounds.get("bleeding", 0) or 0)))
        bleed_state = str(getattr(self.db, "bleed_state", "none") or "none").strip().lower()
        if raw_bleed > 0:
            wounds["bleeding"] = bleeding_from_injuries
        elif bleed_state != "none":
            wounds["bleeding"] = max(bleeding_from_injuries, cached_bleeding)
        else:
            wounds["bleeding"] = bleeding_from_injuries
        self.db.wounds = wounds
        return wounds

    def sync_resources_from_empath_wounds(self):
        self.ensure_core_defaults()
        wounds = self.normalize_empath_wounds(getattr(self.db, "wounds", None) or _copy_default_empath_wounds())
        max_hp = max(1, int(getattr(self.db, "max_hp", 100) or 100))
        max_fatigue = max(1, int(getattr(self.db, "max_fatigue", 100) or 100))
        self.db.hp = max(0, min(max_hp, int(round(max_hp * (1 - (int(wounds.get("vitality", 0) or 0) / 100))))))
        self.db.fatigue = max(0, min(max_fatigue, int(round(max_fatigue * (int(wounds.get("fatigue", 0) or 0) / 100)))))
        bleed_amount = int(wounds.get("bleeding", 0) or 0)
        if bleed_amount <= 0:
            self.db.bleed_state = "none"
        elif bleed_amount < 20:
            self.db.bleed_state = "light"
        elif bleed_amount < 50:
            self.db.bleed_state = "moderate"
        else:
            self.db.bleed_state = "severe"
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
        amount = max(0, min(100, int(value or 0)))
        if amount <= 0:
            return "None"
        if amount < 15:
            return "Minor"
        if amount < 35:
            return "Light"
        if amount < 60:
            return "Moderate"
        if amount < 85:
            return "Heavy"
        return "Severe"

    def format_empath_diagnosis(self, precise=False):
        wounds = self.sync_empath_wounds_from_resources()
        lines = []
        for key in ["vitality", "bleeding", "fatigue", "trauma", "poison", "disease"]:
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
        if shock >= 80:
            return "poor"
        if shock >= 50:
            return "blurred"
        if shock >= 25:
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
            if obj == self or not hasattr(obj, "get_empath_wounds"):
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
        targets = self.get_empath_perceive_targets(include_adjacent=False)
        if not targets:
            return True, ["You sense no other lifeforms nearby."]
        accuracy = self.get_empath_perception_accuracy()
        lines = ["You sense one lifeform nearby." if len(targets) == 1 else "You sense several lifeforms nearby."]
        buckets = {"near collapse": 0, "weakened": 0, "strained": 0, "steady": 0}
        for target in targets:
            label = self.describe_empath_life_force(target, targeted=False)
            buckets[label] = buckets.get(label, 0) + 1
        if accuracy == "poor":
            lines.append("Your reading blurs at the edges.")
            troubled = buckets.get("near collapse", 0) + buckets.get("weakened", 0)
            if troubled:
                lines.append("At least one life force nearby is troubled.")
            elif buckets.get("strained", 0):
                lines.append("A nearby life force feels strained.")
        else:
            for key in ["near collapse", "weakened", "strained"]:
                count = buckets.get(key, 0)
                if count <= 0:
                    continue
                quantifier = "One" if count == 1 else f"{count}"
                verb = "is" if count == 1 else "are"
                lines.append(f"{quantifier} {verb} {key}.")
        if hasattr(self, "use_skill"):
            self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=10 + (len(targets) * 2))
            self.use_skill("attunement", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=10)
        return True, lines

    def perceive_empath_target(self, target):
        if not self.is_empath():
            return False, ["You cannot read life forces that way."]
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        if not hasattr(target, "get_empath_wounds"):
            return False, ["You find no living pattern to read there."]
        line = self.describe_empath_life_force(target, targeted=True)
        if self.get_empath_perception_accuracy() == "poor":
            line = f"{line} The pattern slips in and out of focus."
        if hasattr(self, "use_skill"):
            self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=12 + int(self.get_empath_life_force_score(target) / 8))
        return True, [line]

    def get_linked_target(self):
        primary = self.get_primary_empath_link(require_local=False, include_group=False)
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
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        if target == self:
            return False, ["You already feel every ache in your own body."]
        self.create_empath_link(target, link_type=EMPATH_LINK_TOUCH)
        return True, ["You reach out and sense the condition of your patient.", *target.format_empath_diagnosis(precise=True)]

    def link_empath_target(self, target, persistent=False, deepen=False):
        if not self.is_empath():
            return False, ["You do not know how to deepen a bond that way."]
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, ["They are not here."]
        if target == self:
            return False, ["You are already bound to your own hurts."]
        link_type = EMPATH_LINK_PERSISTENT if persistent else EMPATH_LINK_STANDARD
        self.create_empath_link(target, link_type=link_type, deepen=deepen)
        if hasattr(self, "set_roundtime"):
            self.set_roundtime(2.5 if not persistent else 3.0)
        if persistent:
            self.set_fatigue((self.db.fatigue or 0) + 4)
        if deepen:
            self.set_fatigue((self.db.fatigue or 0) + int(EMPATH_SYSTEM_CONFIG["link_strength"]["deepen_fatigue_cost"]))
        lines = ["You deepen your connection, sensing their condition clearly."]
        if persistent:
            lines.append("The bond settles into a lingering thread that will tax you while it endures.")
        if deepen:
            lines.append("Your connection deepens, their pain becoming clearer.")
        lines.extend(target.format_empath_diagnosis(precise=True))
        return True, lines

    def deepen_empath_link(self, target):
        return self.link_empath_target(target, persistent=False, deepen=True)

    def assess_empath_link(self):
        if not self.is_empath():
            return False, ["You lack the sensitivity to assess a patient that way."]
        link = self.get_primary_empath_link(require_local=False, include_group=False)
        target = link.get("target") if link else None
        if not target or not link:
            return False, ["You have no active empathic link."]
        lines = [f"You focus on {target.key}'s condition."]
        lines.append(f"Link: {str(link.get('type', EMPATH_LINK_TOUCH)).title()} ({link.get('strength_label', 'Weak')}, priority {int(link.get('priority', 0) or 0)}).")
        if link.get("deepened"):
            lines.append("The bond is unusually deep and responsive.")
        other_links = [entry for entry in self.get_empath_links(require_local=False, include_group=False) if getattr(entry.get("target"), "id", None) != getattr(target, "id", None)]
        if other_links:
            lines.append("Other links: " + ", ".join(f"{entry['target'].key} ({entry['strength_label']}, p{int(entry.get('priority', 0) or 0)})" for entry in other_links[:5]))
        lines.extend(target.format_empath_diagnosis(precise=True))
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

    def take_empath_wound(self, wound_type, amount_spec="", target=None):
        if not self.is_empath():
            return False, "You cannot draw another's wounds into yourself."
        if self.is_empath_overdrawn():
            return False, "Your senses are overloaded. Center yourself before taking on more pain."
        if isinstance(target, str):
            target = self.resolve_empath_link_target(target, require_local=True)
        if target is not None:
            link = self.get_empath_link(target, require_local=True)
        else:
            link = self.get_primary_empath_link(require_local=True, include_group=False)
            target = link.get("target") if link else None
        if not target:
            return False, "You need an active link before you can take a wound."
        if not link:
            return False, "You do not have an active link to that patient."
        wound_key = self.normalize_empath_wound_key(wound_type)
        if wound_key not in DEFAULT_EMPATH_WOUNDS:
            return False, "You can only take vitality, bleeding, fatigue, trauma, poison, or disease."
        target_amount = target.get_empath_wound(wound_key)
        if target_amount <= 0:
            return False, f"{target.key} is not suffering from that wound."
        profile = self.get_empath_transfer_profile(wound_key)
        raw_spec = str(amount_spec or "").strip().lower()
        if raw_spec == "all":
            requested = target_amount
        elif raw_spec:
            try:
                requested = max(1, int(raw_spec))
            except ValueError:
                return False, "Give a number or 'all'."
        else:
            requested = min(int(profile.get("default", 20) or 20), target_amount)
        requested = min(requested, target_amount)
        relief_modifier = self.get_empath_shock_modifier() * self.get_empath_transfer_skill_modifier() * self.get_empath_link_transfer_modifier(target=target) * float(profile.get("efficiency", 1.0) or 1.0)
        actual_relief = max(1, min(target_amount, int(round(requested * relief_modifier))))
        inefficiency = max(0, requested - actual_relief)
        extra_self_tax = max(0, int(round(requested * float(profile.get("self_tax", 0.0) or 0.0) * self.get_empath_link_backlash_modifier(target=target))))
        total_self_gain = min(100, self.get_empath_wound(wound_key) + actual_relief + inefficiency + extra_self_tax)
        if wound_key == "bleeding":
            siphoned = self.siphon_empath_bleeding(target, actual_relief)
            target.sync_empath_wounds_from_resources()
            remaining_relief = max(0, actual_relief - int(siphoned or 0))
            if remaining_relief > 0:
                target.set_empath_wound("bleeding", target.get_empath_wound("bleeding") - remaining_relief)
        else:
            target.set_empath_wound(wound_key, target_amount - actual_relief)
        self.set_empath_wound(wound_key, total_self_gain)
        overload_warning = self.apply_empath_transfer_overload(requested, wound_key)
        self.refresh_empath_link(target, bonus_seconds=10)
        self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=max(10, requested))
        self.maybe_trigger_empath_overdraw()
        if actual_relief < requested and overload_warning:
            return True, f"You draw the injury into yourself, but shock blunts the relief you provide. {overload_warning}"
        if actual_relief < requested:
            return True, "You draw the injury into yourself, but shock blunts the relief you provide."
        if overload_warning:
            return True, f"You draw the injury into yourself. {overload_warning}"
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
        if hasattr(self, "set_roundtime"):
            self.set_roundtime(max(1.5, min(4.0, float(int(requested or 0)) / 12.0)))
        return "The force of the transfer buckles you for a moment."

    def mend_empath_self(self):
        if not self.is_empath():
            return False, "You do not know how to mend yourself that way."
        modifier = self.get_empath_healing_modifier()
        healed = []
        for wound_key, base_amount in (("vitality", 12), ("bleeding", 10), ("fatigue", 14), ("trauma", 8), ("poison", 4), ("disease", 3)):
            before = self.get_empath_wound(wound_key)
            after = self.set_empath_wound(wound_key, before - max(1, int(round(base_amount * modifier))))
            if after != before:
                healed.append(f"{wound_key} {before}->{after}")
        if not healed:
            return False, "You are already carrying no wounds that require mending."
        self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=15)
        return True, "You draw your own pain into stillness."

    def center_empath_self(self):
        if not self.is_empath():
            return False, "You do not know how to center yourself that way."
        if getattr(self.db, "in_combat", False):
            return False, "You cannot center yourself while heavy combat still grips you."
        config = EMPATH_SYSTEM_CONFIG["center"]
        shock_reduction = int(config["shock_reduction"])
        fatigue_reduction = int(config["fatigue_reduction"])
        wound_reduction = int(config["wound_reduction"])
        before_shock = self.get_empath_shock()
        before_fatigue = int(self.db.fatigue or 0)
        self.adjust_empath_shock(-shock_reduction)
        self.set_fatigue(before_fatigue - fatigue_reduction)
        self.set_empath_wound("fatigue", self.get_empath_wound("fatigue") - wound_reduction)
        if self.is_empath_overdrawn() and self.get_empath_shock() <= int(config["overdraw_clear_shock_threshold"]) and int(self.db.fatigue or 0) <= int(config["overdraw_clear_fatigue_threshold"]):
            self.clear_state("empath_overdraw")
        if hasattr(self, "set_roundtime"):
            self.set_roundtime(float(config["roundtime"]))
        self.use_skill("attunement", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=14)
        if before_shock == self.get_empath_shock() and before_fatigue == int(self.db.fatigue or 0):
            return False, "You are already as centered as you can be."
        return True, "You steady yourself, regaining clarity."

    def purge_empath_condition(self, wound_type):
        if not self.is_empath():
            return False, "You cannot purge corruption that way."
        wound_key = self.normalize_empath_wound_key(wound_type)
        if wound_key not in {"poison", "disease"}:
            return False, "You can only purge poison or disease."
        before = self.get_empath_wound(wound_key)
        if before <= 0:
            return False, f"You are not carrying any {wound_key}."
        modifier = self.get_empath_healing_modifier()
        reduction = max(4, int(round((14 if wound_key == 'poison' else 10) * modifier)))
        self.set_empath_wound(wound_key, before - reduction)
        fatigue_spike = 10 + int(before / 12)
        self.set_fatigue((self.db.fatigue or 0) + fatigue_spike)
        if hasattr(self, "use_skill"):
            self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=18 + int(before / 8))
        return True, "You force the corruption from your body."

    def register_empath_offensive_action(self, target=None, context="attack", amount=None):
        if not self.is_empath():
            return 0
        if target == self or target is None:
            return 0
        if not hasattr(target, "get_empath_wounds"):
            return 0
        shock_gain = int(amount if amount is not None else (10 if context == "attack" else 8))
        return self.adjust_empath_shock(shock_gain)

    def process_wound_conditions(self):
        self.ensure_core_defaults()
        wounds = self.get_empath_wounds()
        poison = int(wounds.get("poison", 0) or 0)
        disease = int(wounds.get("disease", 0) or 0)
        now = time.time()
        if poison > 0 and now >= float(getattr(self.ndb, "next_poison_tick_at", 0) or 0):
            hp_loss = max(1, int(math.ceil(poison / 25.0)))
            self.set_hp((self.db.hp or 0) - hp_loss)
            if poison < 100:
                self.set_empath_wound("poison", poison + 1)
            self.ndb.next_poison_tick_at = now + 6.0
        if disease > 0 and now >= float(getattr(self.ndb, "next_disease_tick_at", 0) or 0):
            fatigue_gain = max(1, int(math.ceil(disease / 30.0)))
            self.set_fatigue((self.db.fatigue or 0) + fatigue_gain)
            self.ndb.next_disease_tick_at = now + 8.0
        return False

    def stabilize_empath_target(self, target):
        if not self.is_empath():
            return False, "You do not know how to stabilize wounds that way."
        if not target or getattr(target, "location", None) != getattr(self, "location", None):
            return False, "They are not here."
        bleeding_parts = target.get_bleeding_parts() if hasattr(target, "get_bleeding_parts") else []
        if not bleeding_parts:
            return False, f"{target.key} is not bleeding."
        treated = 0
        for entry in bleeding_parts[:2]:
            part_name = entry.get("part")
            if hasattr(target, "apply_tend") and target.apply_tend(part_name, tender=self):
                body_part = target.get_body_part(part_name) if hasattr(target, "get_body_part") else None
                if body_part:
                    current_bleed = max(0, int(body_part.get("bleed", 0) or 0))
                    tend_state = dict(body_part.get("tend") or {})
                    if current_bleed > 0:
                        tend_state["strength"] = max(1, min(max(1, current_bleed // 2), max(1, current_bleed - 1)))
                        body_part["tend"] = tend_state
                treated += 1
        if treated <= 0:
            return False, "You fail to get their bleeding under control."
        target.sync_empath_wounds_from_resources()
        self.use_skill("first_aid", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=12 + (treated * 3))
        return True, "You steady their condition, slowing the damage."

    def process_empath_tick(self):
        if not self.is_empath() or not getattr(self, "location", None):
            return False
        now = time.time()
        before_links = {entry.get("target_id"): entry for entry in self.get_empath_links(require_local=False, include_group=False)}
        self.process_empath_links()
        after_links = {entry.get("target_id"): entry for entry in self.get_empath_links(require_local=False, include_group=False)}
        broken = [entry for target_id, entry in before_links.items() if target_id not in after_links]
        if broken:
            self.msg("Your connection slips away.")
        shock_tick_at = float(getattr(self.ndb, "next_empath_shock_decay_at", 0) or 0)
        if now >= shock_tick_at and self.get_empath_shock() > 0:
            decay = 1
            if not getattr(self.db, "in_combat", False):
                decay += 1
            if self.get_linked_target() or any(int(value or 0) > 0 for value in self.get_empath_wounds().values()):
                decay += 1
            decay = max(1, int(round(decay * self.get_empath_recovery_modifier())))
            self.adjust_empath_shock(-decay)
            self.ndb.next_empath_shock_decay_at = now + 10.0
        smoothing_tick_at = float(getattr(self.ndb, "next_empath_smoothing_at", 0) or 0)
        if now >= smoothing_tick_at:
            self.smooth_empath_linked_wounds()
            self.ndb.next_empath_smoothing_at = now + float(EMPATH_SYSTEM_CONFIG["smoothing"]["tick_seconds"])
        feedback_tick_at = float(getattr(self.ndb, "next_empath_feedback_at", 0) or 0)
        if now >= feedback_tick_at:
            primary = self.get_primary_empath_link(require_local=True, include_group=False)
            patient = primary.get("target") if primary else None
            if self.is_empath_overdrawn() or sum(int(value or 0) for value in self.get_empath_wounds().values()) >= 120:
                self.msg("You are carrying too much pain.")
            elif self.get_empath_shock() <= 15:
                self.msg("Your senses are clear.")
            elif patient:
                score = self.get_empath_life_force_score(patient)
                if score >= 80:
                    self.msg(f"{patient.key}'s pain presses hard against the link.")
                elif score >= 55:
                    self.msg(f"You feel the strain in {patient.key}'s pattern.")
            self.ndb.next_empath_feedback_at = now + 18.0
        next_ping = float(getattr(self.ndb, "empath_sensitivity_next_at", 0) or 0)
        if now < next_ping:
            return False
        threshold = 85 if self.get_empath_perception_accuracy() == "poor" else 70
        for target in self.get_empath_perceive_targets(include_adjacent=False):
            if self.get_empath_life_force_score(target) >= threshold:
                self.msg("You feel a nearby life force faltering.")
                self.ndb.empath_sensitivity_next_at = now + 20
                return False
        return False

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
        self.ensure_core_defaults()
        return str(getattr(self.db, "life_state", LIFE_STATE_ALIVE) or LIFE_STATE_ALIVE).upper() == LIFE_STATE_ALIVE and (self.db.hp or 0) > 0

    def is_dead(self):
        self.ensure_core_defaults()
        return str(getattr(self.db, "life_state", LIFE_STATE_ALIVE) or LIFE_STATE_ALIVE).upper() == LIFE_STATE_DEAD or bool(self.db.is_dead) or (self.db.hp or 0) <= 0

    def can_execute_while_dead(self, raw_string):
        command_name = str(raw_string or "").strip().split(None, 1)[0].lower()
        if not command_name:
            return True
        return command_name in DEAD_STATE_ALLOWED_COMMANDS

    def execute_cmd(self, raw_string, session=None, **kwargs):
        if self.is_dead() and not self.can_execute_while_dead(raw_string):
            self.msg("You are dead. You can still look, speak, check your state, depart, or wait for resurrection.")
            return None
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
        return self.db.stats.get(name, 0)

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

        if getattr(self.db, "awaiting_plea", False) and time.time() >= float(getattr(self.ndb, "plea_deadline", 0) or 0):
            from utils.crime import resolve_justice_case

            self.db.plea = "guilty"
            self.db.awaiting_plea = False
            resolve_justice_case(self)

        if getattr(self.db, "in_stocks", False):
            next_msg_at = float(getattr(self.ndb, "stocks_msg_at", 0) or 0)
            if time.time() >= next_msg_at:
                self.msg("The crowd watches you.")
                self.ndb.stocks_msg_at = time.time() + 60
            next_room_msg_at = float(getattr(self.ndb, "stocks_room_msg_at", 0) or 0)
            if getattr(self, "location", None) and getattr(getattr(self.location, "db", None), "is_stocks", False) and time.time() >= next_room_msg_at:
                if random.random() < 0.1:
                    self.location.msg_contents("A passerby jeers at the prisoners in the stocks.", exclude=[])
                self.ndb.stocks_room_msg_at = time.time() + 60

        if getattr(self.db, "jail_timer", 0):
            self.db.jail_timer = max(0, int(getattr(self.db, "jail_timer", 0) or 0) - 1)

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
                self.sync_client_state()
                self.msg(active_berserk.get("end_message") or "The fury fades, leaving you exposed.")
                changed = True
            else:
                self.set_war_tempo(current_tempo - drain)
                sustain = int((EXHAUSTION_GAIN_RATES.get("berserk_tick") or {}).get(active_berserk.get("key"), 0) or 0)
                if sustain > 0:
                    self.add_exhaustion(sustain, emit_messages=False)

        if getattr(self.db, "in_combat", False):
            self.add_exhaustion(int(EXHAUSTION_GAIN_RATES.get("combat_tick", 0) or 0), emit_messages=False)
        else:
            self.set_exhaustion(self.get_exhaustion() - int(RECOVERY_RATES.get("out_of_combat", 0) or 0), emit_messages=False)

        if frenzy_ended:
            spike = int(EXHAUSTION_GAIN_RATES.get("frenzy_end_spike", 0) or 0)
            if spike > 0:
                self.add_exhaustion(spike)
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
            self.break_combat_rhythm(show_message=True)

        pressure = self.get_pressure_level() if hasattr(self, "get_pressure_level") else 0
        if pressure > 0 and not getattr(self.db, "in_combat", False):
            decay = 8 if not getattr(self.db, "target", None) else 5
            self.set_pressure_level(pressure - decay, emit_messages=False)

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
            self.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=skill + 10)

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

        self.use_skill(
            "locksmithing",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=max(10, int(box.db.lock_difficulty or 0)),
        )

    def locksmith_contest(self, difficulty, stat="intelligence"):
        skill = self.get_skill("locksmithing")
        stat_val = self.db.stats.get(stat, 10)
        return run_contest(skill + stat_val, difficulty)

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
            self.use_skill(
                "locksmithing",
                apply_roundtime=False,
                emit_placeholder=False,
                require_known=False,
                difficulty=max(10, int(box.db.trap_difficulty or 0)),
            )
            return

        if outcome in ("success", "strong"):
            box.db.disarmed = True
            box.db.last_disarmed_trap = box.db.trap_type
            self.db.last_disarmed_trap = box.db.trap_type
            self.db.last_disarmed_trap_difficulty = int(box.db.trap_difficulty or 0)
            self.db.last_disarmed_trap_source = getattr(box, "id", None)
            self.msg("You successfully disarm the trap.")
            self.use_skill(
                "locksmithing",
                apply_roundtime=False,
                emit_placeholder=False,
                require_known=False,
                difficulty=max(10, int(box.db.trap_difficulty or 0)),
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

        self.use_skill(
            "locksmithing",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=max(10, int(box.db.trap_difficulty or 0)),
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
        elif outcome in ("success", "strong"):
            self.msg("You successfully recover useful trap components.")
            tier = "standard" if outcome == "success" else "high"
            rare = random.random() < 0.1
            self.create_trap_component_with_tier(trap, tier, rare=rare)

        self.use_skill(
            "locksmithing",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=max(10, int(box.db.trap_difficulty or 0)),
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
        self.use_skill(
            "locksmithing",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=difficulty,
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

        explicit = getattr(item.db, "item_value", None)
        if explicit is not None:
            return max(1, int(explicit))

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

        if getattr(target.db, "is_box", False):
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
                self.msg(f"You judge it to be worth about {value} coins.")

        self.use_skill("appraisal", apply_roundtime=False, emit_placeholder=False, require_known=False)
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

        self.use_skill("appraisal", apply_roundtime=False, emit_placeholder=False, require_known=False)
        self.set_roundtime(5)

    def is_vendor_target(self, obj):
        return bool(obj and getattr(obj.db, "is_vendor", False))

    def trading_contest(self, vendor):
        trading = self.get_skill("trading")
        scholarship = self.get_skill("scholarship")
        charisma = self.db.stats.get("charisma", 10)
        vendor_difficulty = getattr(vendor.db, "trade_difficulty", 20)
        return run_contest(trading + scholarship + charisma, vendor_difficulty)

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

    def get_nearby_vendor(self):
        if not self.location:
            return None
        for obj in self.location.contents:
            if self.is_vendor_target(obj):
                return obj
        return None

    def sell_item(self, item_name):
        vendor = self.get_nearby_vendor()
        if not vendor:
            self.msg("There is no vendor here.")
            return False

        ok, trade_message = self.can_trade_with(vendor)
        if not ok:
            self.msg(trade_message)
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

        base_value = self.get_item_value(item)
        trading = self.get_skill("trading")
        bonus = 1 + (trading / 100)
        value = int(base_value * bonus)
        haggle_bonus = self.get_state("haggle_bonus") or 0
        value = int(value * (1 + haggle_bonus))
        if haggle_bonus:
            self.clear_state("haggle_bonus")
        value = max(1, value)
        value = min(value, base_value * 2)

        self.db.coins = int(self.db.coins or 0) + value
        self.msg(f"You sell {item.key} for {value} coins.")
        if trading > 10:
            self.msg("You negotiate a better price.")
        if self.location:
            self.location.msg_contents(f"{self.key} sells {item.key}.", exclude=[self])
        item.delete()
        self.use_skill("trading", apply_roundtime=False, emit_placeholder=False, require_known=False)
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

        self.use_skill("scholarship", apply_roundtime=False, emit_placeholder=False, require_known=False)

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
        self.use_skill(skill_name, apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=difficulty)
        return True

    def create_vendor_inventory_item(self, item_name):
        normalized = str(item_name or "").strip().lower()
        if normalized == "lockpick":
            item = create_object(Lockpick, key="basic lockpick", location=self, home=self)
            item.db.item_value = 10
            return item
        if normalized == "book":
            item = create_object(StudyItem, key="study book", location=self, home=self)
            item.db.skill = "scholarship"
            item.db.difficulty = 10
            item.db.item_value = 10
            item.db.desc = "A compact study text full of practical notes and marginalia."
            return item

        item = create_simple_item(
            self,
            key=normalized,
            desc=f"A {normalized} purchased from a local merchant.",
            item_value=10,
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

        normalized = str(item_name or "").strip().lower()
        inventory = [str(entry).strip().lower() for entry in (vendor.db.inventory or [])]
        if normalized not in inventory:
            self.msg("They don't sell that.")
            return False

        price_map = {
            "lockpick": 20,
            "trap kit": 20,
            "book": 20,
        }
        base_price = price_map.get(normalized, 20)
        trading = self.get_skill("trading")
        discount = 1 - (trading / 200)
        price = max(1, int(base_price * discount))

        if int(self.db.coins or 0) < price:
            self.msg("You can't afford that.")
            return False

        self.db.coins = int(self.db.coins or 0) - price
        self.create_vendor_inventory_item(normalized)
        self.msg(f"You buy {normalized} for {price} coins.")
        self.use_skill("trading", apply_roundtime=False, emit_placeholder=False, require_known=False)
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
            self.use_skill(category, apply_roundtime=False, emit_placeholder=False, require_known=False)
            self.clear_state("prepared_spell")
            return True

        self.msg(f"You release {spell_name}.")
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
        result = run_contest(skill_total, box.db.lock_difficulty)

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
            self.use_skill(
                "locksmithing",
                apply_roundtime=False,
                emit_placeholder=False,
                require_known=False,
                difficulty=max(10, int(box.db.lock_difficulty or 0)),
            )
            return

        if outcome in ("success", "strong"):
            box.db.locked = False
            self.msg("You successfully pick the lock.")
            self.use_skill(
                "locksmithing",
                apply_roundtime=False,
                emit_placeholder=False,
                require_known=False,
                difficulty=max(10, int(box.db.lock_difficulty or 0)),
            )

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
        return self.has_state("hidden")

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
        if not target or target == self:
            return True
        if not hasattr(target, "is_hidden"):
            return True
        if not target.is_hidden():
            return True

        perception_bonus = 0
        stealth_bonus = 0
        if hasattr(target, "is_profession") and target.is_profession("thief"):
            stealth_bonus += 10
        if self.is_profession("empath"):
            perception_bonus += 5

        perception = self.get_perception_total() + perception_bonus
        if self.get_state("observing"):
            perception += 10

        return perception >= (target.get_stealth_total() + target.get_hidden_strength() + stealth_bonus)

    def skin_target(self, target):
        if not target:
            self.msg("You can't skin that.")
            return False

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

        msg_room(self, f"{self.key} kneels over {target.key}, working carefully.", exclude=[self])

        skill_total = self.get_skill("skinning") + self.get_stat("agility") + self.get_stat("discipline")
        difficulty = int(getattr(target.db, "skin_difficulty", 35) or 35)
        result = run_contest(skill_total, difficulty)
        outcome = result["outcome"]

        if outcome == "fail":
            self.msg("You ruin the remains and recover nothing useful.")
            target.db.skinned = True
        else:
            if outcome == "partial":
                self.msg("You recover a few usable parts.")
                quality = "rough"
            elif outcome == "success":
                self.msg("You skillfully harvest useful materials.")
                quality = "usable"
            else:
                self.msg("You skillfully harvest useful materials.")
                quality = "fine"

            create_harvest_bundle(
                self,
                key=f"{quality} hide bundle",
                desc=f"A {quality} bundle of materials harvested from {target.key}.",
                harvested_from=target.key,
                skinning_quality=quality,
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

    def attempt_climb(self, raw_target=""):
        target = self._resolve_terrain_target(raw_target, "climbable")
        if target is None or target is False:
            self.msg("There is nothing here to climb.")
            return False

        msg_room(self, f"{self.key} attempts to climb.", exclude=[self])
        difficulty = int(getattr(target.db, "climb_difficulty", 35) or 35)
        result = run_contest(self.get_skill("athletics") + self.get_stat("agility") + self.get_stat("strength"), difficulty)
        if result["outcome"] == "fail":
            self.msg("You fail to make any progress climbing.")
        elif result["outcome"] == "partial":
            self.msg("You start climbing, but struggle to gain ground.")
        else:
            self.msg("You climb successfully.")

        self.use_skill(
            "athletics",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=difficulty,
        )
        return True

    def attempt_swim(self, raw_target=""):
        target = self._resolve_terrain_target(raw_target, "swimmable")
        if target is None or target is False:
            self.msg("There is nowhere here to swim.")
            return False

        msg_room(self, f"{self.key} attempts to swim.", exclude=[self])
        difficulty = int(getattr(target.db, "swim_difficulty", 35) or 35)
        result = run_contest(self.get_skill("athletics") + self.get_stat("stamina") + self.get_stat("agility"), difficulty)
        if result["outcome"] == "fail":
            self.msg("You fail to find a workable path through the water.")
        elif result["outcome"] == "partial":
            self.msg("You manage a few strokes, but make little progress.")
        else:
            self.msg("You swim successfully.")

        self.use_skill(
            "athletics",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=difficulty,
        )
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
        return True, f"You wear {item.key}."

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

        desc = self.db.desc or "An unremarkable person."
        lines = [self.get_display_name(looker), desc]

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

    def set_roundtime(self, seconds):
        self.ensure_core_defaults()
        self.db.roundtime_end = time.time() + seconds
        self.sync_client_state()

    def apply_thief_roundtime(self, seconds, minimum=0.5):
        self.ensure_core_defaults()
        seconds = max(float(minimum), float(seconds))
        current_end = float(self.db.roundtime_end or 0)
        now = time.time()
        self.db.roundtime_end = max(current_end, now) + seconds
        self.sync_client_state()

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
        amount = int(amount) if amount > 0 else 0
        if amount > 0:
            amount = max(1, amount)

        if amount > 0:
            self.db.total_xp = int(getattr(self.db, "total_xp", 0) or 0) + amount
            self.adjust_unabsorbed_xp(amount)
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
        self.ensure_core_defaults()
        if not self.db.states:
            return None
        return self.db.states.get(key)

    def has_state(self, key):
        self.ensure_core_defaults()
        return key in (self.db.states or {})

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
        skill = self.db.skills.get(skill_name)
        if not skill:
            return 0
        return skill.get("rank", 0)

    def get_skill(self, skill_name):
        return self.get_skill_rank(skill_name)

    def format_skill_name(self, skill_name):
        return str(skill_name).replace("_", " ").title()

    def get_skill_metadata(self, skill_name):
        metadata = dict(SKILL_REGISTRY.get(skill_name, {}))
        metadata.setdefault("category", "general")
        metadata.setdefault("visibility", "shared")
        metadata.setdefault("guilds", None)
        metadata.setdefault("description", "No description is available yet.")
        metadata.setdefault("starter_rank", 0)
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
                "distant": "The wild feels farther away.",
                "disconnected": "The city dulls your senses.",
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

    def set_exhaustion(self, value, emit_messages=True):
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

        self.sync_client_state()
        return amount

    def add_exhaustion(self, amount, emit_messages=True):
        return self.set_exhaustion(self.get_exhaustion() + int(amount or 0), emit_messages=emit_messages)

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

    def set_pressure_level(self, value, emit_messages=True):
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
        self.sync_client_state()
        return self.get_pressure_level()

    def add_pressure(self, amount, emit_messages=True):
        return self.set_pressure_level(self.get_pressure_level() + int(amount or 0), emit_messages=emit_messages)

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

    def break_combat_rhythm(self, show_message=True):
        if self.get_combat_streak() <= 0:
            return False
        self.db.combat_streak = 0
        self.db.last_combat_action_at = 0
        self.db.rhythm_break_until = time.time() + 10
        if show_message:
            self.msg("You lose your rhythm.")
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

    def set_war_tempo(self, value):
        maximum = self.get_max_war_tempo()
        self.db.war_tempo = max(0, min(maximum, int(value or 0)))
        self.update_war_tempo_state()
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

    def join_profession(self, profession_name):
        profession = self.normalize_profession_name(profession_name)
        if profession not in VALID_GUILDS or profession == DEFAULT_PROFESSION:
            options = ", ".join(name.replace("_", " ") for name in VALID_GUILDS if name != DEFAULT_PROFESSION)
            return False, f"You may join one of these professions: {options}"

        target_guild_tag = PROFESSION_TO_GUILD.get(profession)
        room_tag = getattr(getattr(self.location, "db", None), "guild_tag", None)
        if target_guild_tag and room_tag != target_guild_tag:
            return False, "You must stand inside the proper guildhall to join that profession."

        if self.get_profession() == profession:
            return False, f"You already belong to the {self.get_profession_display_name()} profession."

        self.set_profession(profession)
        self.set_guild(profession)
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
        self.get_subsystem()
        return True

    def get_skillset(self, skill_name):
        metadata = self.get_skill_metadata(skill_name)
        category = str(metadata.get("category", "general") or "general").strip().lower()
        return SKILLSET_ALIASES.get(category, category or "general")

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
        difficulty = int(mana) * 10
        stability = control / max(1, difficulty)
        return max(0.0, min(1.0, stability))

    def get_spell_power(self, category, mana):
        skill = self.get_skill(category)
        attunement = self.get_skill("attunement")
        return float(mana) * (1 + (skill + attunement) / 200.0)

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
            self.msg(f"Your {name} misses {target.key}.")
            target.msg(f"{self.key}'s {name} misses you.")
            return True

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
                continue

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
                return True

        target.set_state("debilitated", {"penalty": penalty, "duration": duration, "type": debuff_type})
        self.apply_exposed_state(target, duration=6)
        self.msg(f"Your {name} hampers {target.key}.")
        target.msg(f"You feel your movements hindered by {self.key}'s {name}.")
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
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            return None
        if normalized not in SKILL_REGISTRY and normalized not in (self.db.skills or {}):
            return None
        if not self.is_skill_visible(normalized) and self.get_skill_rank(normalized) <= 0:
            return None

        metadata = self.get_skill_metadata(normalized)
        points = (self.db.skills or {}).get(normalized, {}).get("mindstate", 0)
        return {
            "skill": normalized,
            "display": self.format_skill_name(normalized),
            "rank": self.get_skill_rank(normalized),
            "mindstate": points,
            "label": self.get_mindstate_label(points),
            "cap": self.get_mindstate_cap(),
            "category": metadata.get("category", "general"),
            "visibility": metadata.get("visibility", "shared"),
            "description": metadata.get("description", "No description is available yet."),
        }

    def get_skill_entries(self, include_zero=False):
        self.ensure_core_defaults()
        cap = self.get_mindstate_cap()
        entries = []

        skill_names = list(self.get_available_skills().keys()) if include_zero else list((self.db.skills or {}).keys())

        for skill_name in skill_names:
            if skill_name == "tend":
                continue

            data = dict((self.db.skills or {}).get(skill_name, {}))
            rank = data.get("rank", 0)
            if not include_zero and rank <= 0:
                continue

            points = data.get("mindstate", 0)
            metadata = self.get_skill_metadata(skill_name)
            entries.append(
                {
                    "skill": skill_name,
                    "display": self.format_skill_name(skill_name),
                    "rank": rank,
                    "mindstate": points,
                    "label": self.get_mindstate_label(points),
                    "cap": cap,
                    "active": points > 0,
                    "category": metadata.get("category", "general"),
                    "visibility": metadata.get("visibility", "shared"),
                    "description": metadata.get("description", "No description is available yet."),
                }
            )

        entries.sort(key=lambda entry: (entry["category"], not entry["active"], entry["display"].lower()))
        return entries

    def get_active_learning_entries(self):
        entries = [entry for entry in self.get_skill_entries(include_zero=False) if entry.get("mindstate", 0) > 0]
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
        skills = dict(self.db.skills or {})
        changed = False
        drain = self.get_learning_drain()

        for skill_name, data in skills.items():
            current = dict(data)
            mindstate = current.get("mindstate", 0)
            if mindstate <= 0:
                continue
            if mindstate < 5:
                continue

            old_rank = current.get("rank", 1)
            gain = max(1, mindstate // 20)
            current["rank"] = old_rank + gain
            current["mindstate"] = max(0, mindstate - drain)
            skills[skill_name] = current
            changed = True

        if changed:
            self.db.skills = skills

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

        return descriptions

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

        if self.get_injury_severity(body_part.get("external", 0)) == "severe":
            self.msg(f"Your {self.format_body_part_name(location)} is badly damaged!")

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

        total_bleed = 0
        for part_name, part in self.db.injuries.items():
            if part.get("internal", 0) > 20:
                part["bleed"] += 1

            tend_state = part.get("tend") or {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}
            duration = int(tend_state.get("duration", 0))
            strength = int(tend_state.get("strength", 0))
            min_until = float(tend_state.get("min_until", 0.0))
            was_tended = bool(part.get("tended", False))

            effective_bleed = part.get("bleed", 0)
            if duration > 0 or time.time() < min_until:
                effective_bleed = max(0, effective_bleed - strength)
                if time.time() >= min_until and duration > 0:
                    duration -= 1
                    if part.get("external", 0) > 45:
                        duration -= 1
                    if self.db.in_combat:
                        duration -= 1
                tend_state["duration"] = max(0, duration)
                part["tend"] = tend_state
                part["tended"] = tend_state["duration"] > 0 or time.time() < min_until
                if was_tended and not part["tended"] and part.get("bleed", 0) > 0:
                    self.msg(f"Your {self.format_body_part_name(part_name)} begins bleeding again!")

            total_bleed += max(0, effective_bleed)

        if total_bleed > 0:
            hp_loss = total_bleed + int(total_bleed * 0.3)
            if total_bleed > 10:
                hp_loss -= (total_bleed - 10)
            hp_loss = max(1, hp_loss)
            self.set_hp((self.db.hp or 0) - hp_loss)
            self.msg("You bleed from your wounds.")
            if total_bleed > 5:
                self.msg("You are bleeding heavily!")
            if (self.db.hp or 0) <= 0:
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
        self.ensure_core_defaults()
        self.sync_combat_state()
        return self.db.in_combat

    def set_target(self, target):
        self.ensure_core_defaults()
        old_target = self.db.target
        if target and not target.pk:
            self.db.target = None
            self.db.in_combat = False
            self.db.aiming = None
            self.sync_client_state()
            return

        if old_target and old_target != target:
            self.clear_range(old_target)

        self.db.target = target
        self.db.in_combat = target is not None
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
        if destination and destination != self.location:
            self.break_aim_for_movement(emit_message=not quiet)
        return super().move_to(destination, quiet=quiet, *args, **kwargs)

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

            for observer in self.get_room_observers():
                result = run_contest(self.get_stealth_total(), observer.get_perception_total())
                outcome = result["outcome"]

                if outcome == "fail":
                    reveal_ids.append(observer.id)
                    continue

                if outcome == "partial":
                    partial_ids.append(observer.id)

            self.ndb.sneak_reveal_observer_ids = reveal_ids
            self.ndb.sneak_partial_observer_ids = partial_ids
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
        if self.is_in_shrine():
            self.msg("This is a place where your fate can be secured.")
        for part_name in BODY_PART_ORDER:
            body_part = self.get_body_part(part_name)
            if not body_part:
                continue
            tend_state = body_part.get("tend") or {"strength": 0, "duration": 0, "min_until": 0.0}
            duration = int(tend_state.get("duration", 0))
            if duration <= 0 or time.time() < float(tend_state.get("min_until", 0.0)):
                continue
            tend_state["duration"] = max(0, duration - 1)
            body_part["tend"] = tend_state
            body_part["tended"] = tend_state["duration"] > 0 or time.time() < float(tend_state.get("min_until", 0.0))

        direction = getattr(self.ndb, "last_traverse_direction", None)
        if self.ndb.sneak_move_active and self.is_sneaking() and direction:
            self.msg(f"You move quietly to the {direction}.")
            self.set_fatigue((self.db.fatigue or 0) + 2)
            self.use_skill("stealth", apply_roundtime=False, emit_placeholder=False)

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

        self.sync_client_state(include_map=True)

        self.ndb.sneak_move_active = False
        self.ndb.sneak_partial_observer_ids = []
        self.ndb.sneak_reveal_observer_ids = []
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
