import time

from commands.command import Command


class CmdThrow(Command):
    """
    Throw an item or weapon at a target.

    Examples:
        throw dagger at goblin
    """

    key = "throw"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        raw_args = str(self.args or "").strip()
        if not raw_args.lower().startswith("tomato "):
            caller.msg("Throw tomato at whom?")
            return

        target_name = raw_args[7:].strip()
        if not target_name:
            caller.msg("Throw tomato at whom?")
            return

        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("tomato", 0) or 0):
            caller.msg("You need a moment before throwing another tomato.")
            return

        target = caller.search(target_name, location=caller.location)
        if not target:
            return
        if target.location != caller.location:
            return
        if not getattr(target.db, "in_stocks", False):
            caller.msg("They are not in the stocks.")
            return

        cooldowns["tomato"] = now + 2
        caller.ndb.cooldowns = cooldowns
        caller.msg(f"You throw a tomato at {target.key}!")
        target.msg(f"{caller.key} throws a tomato at you!")
        caller.location.msg_contents(f"{caller.key} pelts {target.key} with a tomato!", exclude=[caller, target])
