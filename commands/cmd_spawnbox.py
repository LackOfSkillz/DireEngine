import random

from evennia import Command
from evennia.utils.create import create_object

from typeclasses.box import Box


class CmdSpawnBox(Command):
    key = "spawnbox"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Builder"

    def func(self):
        args = {part.strip().lower() for part in self.args.split() if part.strip()}
        trapped = "trap" in args
        hard = "hard" in args

        box = create_object(Box, key="practice box", location=self.caller.location)
        box.db.locked = True
        box.db.opened = False
        box.db.lock_difficulty = 45 if hard else 20
        box.db.trap_present = trapped
        box.db.trap_difficulty = 40 if trapped and hard else 20 if trapped else 0
        box.db.trap_type = random.choice(["needle", "blade", "gas", "explosive"]) if trapped else None
        box.db.disarmed = False
        box.db.last_disarmed_trap = None

        summary = ["locked"]
        if trapped:
            summary.append(f"trapped ({box.db.trap_type})")
        if hard:
            summary.append("hard")
        self.caller.msg(f"You create a practice box: {', '.join(summary)}.")