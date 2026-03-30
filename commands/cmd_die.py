from commands.command import Command


class CmdDie(Command):
    """
    Force a death event for testing.

    Examples:
        die
        die <target>
    """

    key = "die"
    locks = "cmd:perm(Developer) or perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if args:
            target = caller.search(args, global_search=True)
            if not target:
                return
        else:
            target = caller

        if not hasattr(target, "at_death") or not hasattr(target, "is_dead"):
            caller.msg("That target cannot die this way.")
            return

        if target.is_dead():
            caller.msg(f"{target.key} is already dead.")
            return

        corpse = target.at_death()
        if corpse is None:
            caller.msg(f"{target.key} is already dead.")
            return

        caller.msg(f"You force {target.key} to die.")
        if target != caller:
            target.msg("A divine force snuffs out your life.")