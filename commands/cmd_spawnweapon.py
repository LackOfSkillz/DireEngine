from commands.command import Command
from evennia.utils.create import create_object

from server.systems.weapon_generator import BASE_WEAPON_PROFILES, generate_weapon_definition
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
        if weapon_type not in BASE_WEAPON_PROFILES:
            options = ", ".join(sorted(BASE_WEAPON_PROFILES))
            self.caller.msg(f"Choose one of these weapon types: {options}.")
            return

        generated = generate_weapon_definition(weapon_type, tier="low")
        profile = generated["runtime_profile"]

        weapon = create_object(Weapon, key=generated["name"], location=self.caller.location)
        weapon.db.desc = generated["description"]
        weapon.db.generated_item_payload = dict(generated["item_payload"])
        weapon.db.generated_style_stack = dict(generated["style_stack"])
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
