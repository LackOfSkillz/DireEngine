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
from world.area_forge.character_api import send_character_update
from world.area_forge.map_api import send_map_update

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

VALID_GUILDS = (
    "barbarian",
    "bard",
    "cleric",
    "commoner",
    "empath",
    "moon_mage",
    "necromancer",
    "paladin",
    "ranger",
    "thief",
    "trader",
    "warrior_mage",
)

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

RANGE_BANDS = ["melee", "reach", "missile"]
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


def _copy_default_equipment():
    return {
        slot: value.copy() if isinstance(value, list) else value
        for slot, value in DEFAULT_EQUIPMENT.items()
    }


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
        for skill_name, baseline_rank in AVAILABLE_SKILL_BASELINES.items():
            self.learn_skill(skill_name, {"rank": baseline_rank, "mindstate": 0})

    def at_post_puppet(self, **kwargs):
        super().at_post_puppet(**kwargs)
        self.ensure_core_defaults()
        self.sync_client_state(include_map=True)

    def sync_client_state(self, include_map=False, session=None):
        sessions_attr = getattr(self, "sessions", None)
        sessions = [session] if session else list(sessions_attr.all()) if sessions_attr else []
        if not sessions:
            return
        if include_map:
            send_map_update(self, session=session)
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
                int(key): value
                for key, value in dict(self.db.combat_range).items()
                if value in RANGE_BANDS
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
        self.db.hp = max(0, min(value, self.db.max_hp))
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
        self.sync_client_state()

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
        self.db.bleed_state = "none"
        self.db.roundtime_end = 0
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
        return self.db.hp > 0

    def is_dead(self):
        self.ensure_core_defaults()
        return bool(self.db.is_dead) or (self.db.hp or 0) <= 0

    def is_empath(self):
        self.ensure_core_defaults()
        return bool(getattr(self.db, "is_empath", False))

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
            self.set_balance(self.db.balance + 2)

    def recover_fatigue(self):
        self.ensure_all_defaults()
        if self.db.fatigue > 0:
            self.set_fatigue(self.db.fatigue - 2)

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
        return stealth_rank + agility + reflex - stealth_hindrance

    def get_awareness(self):
        return self.get_state("awareness") or "normal"

    def set_awareness(self, level):
        self.set_state("awareness", level)

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

    def has_reaction_delay(self):
        return self.is_surprised()

    def break_stealth(self):
        self.clear_state("hidden")
        self.clear_state("sneaking")
        self.clear_state("stalking")
        self.clear_state("ambush_target")

    def can_detect(self, target):
        return self.can_perceive(target)

    def can_perceive(self, target):
        if not target or target == self:
            return True
        if not hasattr(target, "is_hidden"):
            return True
        if not target.is_hidden():
            return True

        perception = self.get_perception_total()
        if self.get_state("observing"):
            perception += 10

        return perception >= (target.get_stealth_total() + target.get_hidden_strength())

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
        return (self.db.combat_range or {}).get(target.id, "melee")

    def set_range(self, target, value, reciprocal=True):
        self.ensure_core_defaults()
        if not target or getattr(target, "id", None) is None:
            return

        band = value if value in RANGE_BANDS else "melee"
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
        if my_range == "missile" and their_range == "missile":
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
        lines = [self.key, desc]

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

        if hasattr(weapon, "normalize_damage_types"):
            weapon.normalize_damage_types()

        damage_types = getattr(weapon.db, "damage_types", None)
        if isinstance(damage_types, Mapping) and damage_types:
            profile["damage_types"] = dict(damage_types)

        if weapon.db.damage_type:
            profile["damage_type"] = weapon.db.damage_type
        elif profile["damage_types"]:
            profile["damage_type"] = max(profile["damage_types"], key=profile["damage_types"].get)

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

        gain, band = self.get_learning_amount(skill_name, difficulty)
        gain = int(gain * learning_multiplier)
        gain = int(gain * self.get_scholarship_learning_multiplier())

        if gain > 0:
            skill = self.db.skills.get(skill_name)
            if skill:
                cap = self.get_mindstate_cap()
                self.update_skill(skill_name, mindstate=min(skill.get("mindstate", 0) + gain, cap))

        if emit_placeholder:
            self.msg(f"You try to use {skill_name}, but it is not implemented.")
        if apply_roundtime:
            self.set_roundtime(3)
        if return_learning:
            return gain, band
        return True

    def use_ability(self, key, target=None):
        ability = get_ability(key)

        if not ability:
            self.msg("You don't know how to do that.")
            return

        if not self.passes_guild_check(ability):
            self.msg("You cannot use that ability.")
            return

        ok, msg = self.meets_ability_requirements(ability)
        if not ok:
            self.msg(msg)
            return

        ok, msg = ability.can_use(self, target)
        if not ok:
            self.msg(msg)
            return

        ability.execute(self, target)

        if hasattr(ability, "roundtime"):
            self.set_roundtime(ability.roundtime)

    def meets_ability_requirements(self, ability):
        req = getattr(ability, "required", {}) or {}
        skill = req.get("skill")
        rank = req.get("rank", 0)

        if skill:
            current_rank = self.get_skill(skill)
            if current_rank < rank:
                return False, f"You need {skill} rank {rank} to use {ability.key} (current: {current_rank})."

        return True, ""

    def passes_guild_check(self, ability):
        if not getattr(ability, "guilds", None):
            return True

        player_guild = getattr(self.db, "guild", None)
        return player_guild in ability.guilds

    def can_see_ability(self, ability):
        if not self.passes_guild_check(ability):
            return False

        vis = getattr(ability, "visible_if", {}) or {}
        skill = vis.get("skill")
        rank = vis.get("min_rank", 0)

        if skill and self.get_skill(skill) < rank:
            return False

        return True

    def get_visible_abilities(self):
        from typeclasses.abilities import ABILITY_REGISTRY

        return [
            ability for ability in ABILITY_REGISTRY.values()
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
        return self.get_guild() in guilds

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
        if guilds and self.get_guild() not in guilds:
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

        self.msg(f"Your {name} erupts outward!")
        if self.location:
            self.location.msg_contents(f"{self.key}'s {name} erupts outward!", exclude=[self])

        factor = self.get_multi_skill_factor("targeted_magic", "attunement")
        effective_power = float(power) * (0.5 + factor) * wild_modifier
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

    def at_pre_move(self, destination, **kwargs):
        if self.is_in_combat():
            self.msg("You cannot move while in combat.")
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
