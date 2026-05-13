from commands.command import Command
from evennia.utils.create import create_object

from typeclasses.armor import Armor
from typeclasses.npcs import NPC


def _spawn_dummy(location, *, armored=False):
    key = "armored training dummy" if armored else "training dummy"
    desc = (
        "A practice target outfitted for repeated armor mitigation checks."
        if armored
        else "A practice target meant for repeated combat validation."
    )
    dummy = create_object(NPC, key=key, location=location, home=location)
    dummy.db.desc = desc
    dummy.db.is_dummy = True
    if armored:
        armor = create_object(Armor, key="dummy chain shirt", location=dummy, home=dummy)
        armor.db.slot = "torso"
        armor.db.desc = "A blunt-force training shirt for combat smoke validation."
        armor.db.armor_type = "chain_armor"
        armor.db.absorption = 0.25
        armor.db.coverage = ["chest", "abdomen", "back", "arm"]
        armor.db.covers = list(armor.db.coverage)
        if hasattr(armor, "apply_armor_preset"):
            armor.apply_armor_preset()
        dummy.equip_item(armor)
    return dummy


class CmdSpawnDummy(Command):
    """
    Create a practice combat dummy in the room.

    Examples:
      spawndummy
      spawndummy armored
    """

    key = "spawndummy"
    aliases = ["spdummy"]
    help_category = "Builder"

    def func(self):
        arg = str(self.args or "").strip().lower()
        if arg not in {"", "armored"}:
            self.caller.msg("Usage: spawndummy or spawndummy armored")
            return
        dummy = _spawn_dummy(self.caller.location, armored=(arg == "armored"))
        self.caller.msg(f"You create {dummy.key}.")