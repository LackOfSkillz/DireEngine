import random

from commands.command import Command

from utils.crime import release_from_stocks


class CmdPleadRelease(Command):
    key = "pleadrelease"
    aliases = ["plead release"]
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        if not getattr(caller.db, "in_stocks", False):
            caller.msg("You are not in the stocks.")
            return

        if random.randint(1, 100) > 70:
            caller.msg("The guard relents and releases you early.")
            release_from_stocks(caller)
            return

        caller.msg("The guard ignores your pleas.")