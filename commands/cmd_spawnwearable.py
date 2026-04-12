from commands.command import Command
from evennia.utils.create import create_object

from typeclasses.armor import Armor
from typeclasses.wearables import Wearable


class CmdSpawnWearable(Command):
    """
    Create a practice piece of wearable gear.

    Examples:
      spawnwearable
      spawnwearable ring
      spawnwearable armor
      spwa sleeves
    """

    key = "spawnwearable"
    aliases = ["spwa"]
    help_category = "Builder"

    def func(self):
      arg = (self.args or "").strip().lower()
      options = {
        "": ("test cloak", "torso", "A simple test cloak used for equipment validation."),
        "cloak": ("test cloak", "torso", "A simple test cloak used for equipment validation."),
        "ring": ("gold ring", "fingers", "A plain gold ring sized for repeated slot testing."),
        "head": ("test cap", "head", "A simple cap used to validate head-slot behavior."),
        "cap": ("test cap", "head", "A simple cap used to validate head-slot behavior."),
      }
      armor_options = {
        "armor": {
          "key": "test leather armor",
          "slot": "torso",
          "desc": "A suit of light leather armor for armor-system validation.",
          "armor_type": "light_armor",
          "protection": 2,
          "hindrance": 1,
          "absorption": 0.15,
          "maneuver_hindrance": 4,
          "stealth_hindrance": 3,
          "coverage": ["chest", "abdomen", "back"],
          "unlocks": {20: {"protection_bonus": 1}, 40: {"hindrance_reduction": 1}},
          "skill_scaling": {
            "light_armor": [
              {"rank": 10, "effects": {"stealth_hindrance": 1}},
              {"rank": 30, "effects": {"maneuver_hindrance": 2}},
              {"rank": 50, "effects": {"flavor": "cloak_flare"}},
            ]
          },
        },
        "sleeves": {
          "key": "test leather sleeves",
          "slot": "arms",
          "desc": "A pair of reinforced sleeves that protect the arms.",
          "armor_type": "light_armor",
          "protection": 1,
          "hindrance": 1,
          "absorption": 0.1,
          "maneuver_hindrance": 2,
          "stealth_hindrance": 1,
          "coverage": ["arm"],
          "unlocks": {20: {"protection_bonus": 1}, 40: {"hindrance_reduction": 1}},
          "skill_scaling": {},
        },
      }

      if arg in armor_options:
        profile = armor_options[arg]
        item = create_object(Armor, key=profile["key"], location=self.caller)
        item.db.slot = profile["slot"]
        item.db.desc = profile["desc"]
        item.db.armor_type = profile["armor_type"]
        item.db.protection = profile["protection"]
        item.db.hindrance = profile["hindrance"]
        item.db.absorption = profile["absorption"]
        item.db.maneuver_hindrance = profile["maneuver_hindrance"]
        item.db.stealth_hindrance = profile["stealth_hindrance"]
        item.db.coverage = profile["coverage"]
        item.db.covers = profile["coverage"]
        item.db.unlocks = profile["unlocks"]
        item.db.skill_scaling = profile["skill_scaling"]
        if hasattr(item, "apply_armor_preset"):
          item.apply_armor_preset()
        self.caller.msg(f"You create {item.key}.")
        return

      profile = options.get(arg)
      if not profile:
        self.caller.msg("Try spawnwearable cloak, spawnwearable ring, spawnwearable armor, or spawnwearable sleeves.")
        return

      key, slot, desc = profile
      item = create_object(Wearable, key=key, location=self.caller)
      item.db.slot = slot
      item.db.desc = desc
      self.caller.msg(f"You create {item.key}.")