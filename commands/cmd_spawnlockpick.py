from commands.command import Command
from evennia.utils.create import create_object

from typeclasses.lockpick import Lockpick


class CmdSpawnLockpick(Command):
    """
    Spawn a test lockpick in the room.

    Examples:
        spawnlockpick
    """

    key = "spawnlockpick"
    aliases = ["spawnpick"]
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Builder"

    def func(self):
        grade_map = {
            "rough": ("rough", 5),
            "standard": ("standard", 10),
            "fine": ("fine", 15),
            "master": ("master", 20),
        }
        grade_name = (self.args.strip().lower() or "standard")
        if grade_name not in grade_map:
            self.caller.msg("Choose rough, standard, fine, or master.")
            return

        grade, durability = grade_map[grade_name]
        pick = create_object(Lockpick, key=f"{grade} lockpick", location=self.caller)
        pick.db.grade = grade
        pick.db.quality = pick.get_quality()
        pick.db.durability = durability
        self.caller.msg(f"You create {pick.key}.")
