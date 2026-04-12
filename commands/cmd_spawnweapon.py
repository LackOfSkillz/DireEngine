from commands.command import Command
from evennia.utils.create import create_object

from typeclasses.weapons import Weapon


class CmdSpawnWeapon(Command):
    """
    Create a practice weapon in the room.

    Examples:
      spawnweapon
      spawnweapon dagger
      spawnweapon mace
      spw spear
    """

    key = "spawnweapon"
    aliases = ["spw"]
    help_category = "Builder"

    def func(self):
        weapon_type = (self.args.strip().lower() or "sword")
        weapon_profiles = {
            "dagger": {
                "key": "training dagger",
                "weapon_profile": {"type": "light_edge", "skill": "light_edge", "damage": 4, "balance": 60, "speed": 2.0, "damage_min": 2, "damage_max": 5, "roundtime": 2.0},
                "weapon_type": "light_edge",
                "balance_cost": 8,
                "fatigue_cost": 4,
                "damage_type": "slice",
                "damage_types": {"slice": 0.6, "impact": 0.1, "puncture": 0.3},
                "balance": 60,
                "damage": 4,
                "speed": 2.0,
                "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
                "skill_scaling": {
                    "light_edge": [
                        {"rank": 10, "effects": {"balance": 5}},
                        {"rank": 30, "effects": {"accuracy": 3}},
                        {"rank": 60, "effects": {"flavor": "blade_flourish"}},
                    ]
                },
            },
            "sword": {
                "key": "training sword",
                "weapon_profile": {"type": "light_edge", "skill": "light_edge", "damage": 5, "balance": 55, "speed": 3.0, "damage_min": 3, "damage_max": 6, "roundtime": 3.0},
                "weapon_type": "light_edge",
                "balance_cost": 10,
                "fatigue_cost": 5,
                "damage_type": "slice",
                "damage_types": {"slice": 0.7, "impact": 0.1, "puncture": 0.2},
                "balance": 55,
                "damage": 5,
                "speed": 3.0,
                "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
                "skill_scaling": {
                    "light_edge": [
                        {"rank": 10, "effects": {"balance": 5}},
                        {"rank": 30, "effects": {"accuracy": 3}},
                        {"rank": 60, "effects": {"flavor": "blade_flourish"}},
                    ]
                },
            },
            "mace": {
                "key": "training mace",
                "weapon_profile": {"type": "blunt", "skill": "blunt", "damage": 6, "balance": 45, "speed": 4.0, "damage_min": 4, "damage_max": 8, "roundtime": 4.0},
                "weapon_type": "blunt",
                "balance_cost": 14,
                "fatigue_cost": 7,
                "damage_type": "impact",
                "damage_types": {"slice": 0.0, "impact": 0.9, "puncture": 0.1},
                "balance": 45,
                "damage": 6,
                "speed": 4.0,
                "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
                "skill_scaling": {
                    "blunt": [
                        {"rank": 10, "effects": {"balance": 4}},
                        {"rank": 30, "effects": {"accuracy": 2}},
                        {"rank": 60, "effects": {"flavor": "blade_flourish"}},
                    ]
                },
            },
            "spear": {
                "key": "training spear",
                "weapon_profile": {"type": "polearm", "skill": "polearm", "damage": 5, "balance": 52, "speed": 4.0, "damage_min": 3, "damage_max": 7, "roundtime": 4.0},
                "weapon_type": "polearm",
                "balance_cost": 12,
                "fatigue_cost": 6,
                "damage_type": "puncture",
                "damage_types": {"slice": 0.1, "impact": 0.1, "puncture": 0.8},
                "balance": 52,
                "damage": 5,
                "speed": 4.0,
                "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
                "skill_scaling": {
                    "polearm": [
                        {"rank": 10, "effects": {"balance": 4}},
                        {"rank": 30, "effects": {"accuracy": 3}},
                        {"rank": 60, "effects": {"flavor": "blade_flourish"}},
                    ]
                },
            },
            "bow": {
                "key": "training bow",
                "weapon_profile": {"type": "attack", "skill": "attack", "damage": 5, "balance": 50, "speed": 4.0, "damage_min": 3, "damage_max": 7, "roundtime": 4.0, "range_band": "far", "weapon_range_type": "bow"},
                "weapon_type": "attack",
                "balance_cost": 10,
                "fatigue_cost": 5,
                "damage_type": "puncture",
                "damage_types": {"slice": 0.0, "impact": 0.1, "puncture": 0.9},
                "balance": 50,
                "damage": 5,
                "speed": 4.0,
                "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
                "is_ranged": True,
                "weapon_range_type": "bow",
                "range_band": "far",
                "skill_scaling": {
                    "attack": [
                        {"rank": 10, "effects": {"balance": 4}},
                        {"rank": 30, "effects": {"accuracy": 3}},
                        {"rank": 60, "effects": {"flavor": "archers_focus"}},
                    ]
                },
            },
            "crossbow": {
                "key": "training crossbow",
                "weapon_profile": {"type": "attack", "skill": "attack", "damage": 6, "balance": 45, "speed": 4.5, "damage_min": 4, "damage_max": 8, "roundtime": 4.5, "range_band": "far", "weapon_range_type": "crossbow"},
                "weapon_type": "attack",
                "balance_cost": 12,
                "fatigue_cost": 5,
                "damage_type": "puncture",
                "damage_types": {"slice": 0.0, "impact": 0.05, "puncture": 0.95},
                "balance": 45,
                "damage": 6,
                "speed": 4.5,
                "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
                "is_ranged": True,
                "weapon_range_type": "crossbow",
                "range_band": "far",
                "skill_scaling": {
                    "attack": [
                        {"rank": 10, "effects": {"balance": 3}},
                        {"rank": 30, "effects": {"accuracy": 4}},
                        {"rank": 60, "effects": {"flavor": "archers_focus"}},
                    ]
                },
            },
        }

        profile = weapon_profiles.get(weapon_type)
        if not profile:
            options = ", ".join(sorted(weapon_profiles))
            self.caller.msg(f"Choose one of these weapon types: {options}.")
            return

        weapon = create_object(Weapon, key=profile["key"], location=self.caller.location)
        weapon.db.weapon_profile = profile["weapon_profile"]
        weapon.db.weapon_type = profile["weapon_type"]
        weapon.db.damage_min = profile["weapon_profile"]["damage_min"]
        weapon.db.damage_max = profile["weapon_profile"]["damage_max"]
        weapon.db.roundtime = profile["weapon_profile"]["roundtime"]
        weapon.db.damage = profile["damage"]
        weapon.db.speed = profile["speed"]
        weapon.db.balance_cost = profile["balance_cost"]
        weapon.db.fatigue_cost = profile["fatigue_cost"]
        weapon.db.skill = profile["weapon_profile"]["skill"]
        weapon.db.damage_type = profile["damage_type"]
        weapon.db.damage_types = profile["damage_types"]
        weapon.db.balance = profile["balance"]
        weapon.db.unlocks = profile["unlocks"]
        weapon.db.is_ranged = profile.get("is_ranged", False)
        weapon.db.weapon_range_type = profile.get("weapon_range_type", None)
        weapon.db.range_band = profile.get("range_band", "melee")
        weapon.db.ammo_loaded = False
        weapon.db.ammo_type = "bolt" if profile.get("weapon_range_type") == "crossbow" else "arrow"
        weapon.db.skill_scaling = profile["skill_scaling"]
        if hasattr(weapon, "sync_profile_fields"):
            weapon.sync_profile_fields()
        if hasattr(weapon, "normalize_damage_types"):
            weapon.normalize_damage_types()
        self.caller.msg(f"You create {weapon.key}.")
