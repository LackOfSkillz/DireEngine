from evennia import Command

from typeclasses.characters import VALID_GUILDS


class CmdJoin(Command):
        """
        Join a guild or profession when eligible.

        Examples:
            join ranger
        """

    key = "join"
    locks = "cmd:all()"
    help_category = "Training & Lore"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if not args:
            options = ", ".join(profession.replace("_", " ") for profession in VALID_GUILDS if profession != "commoner")
            caller.msg(f"Join which profession? Options: {options}")
            return

        if not hasattr(caller, "join_profession"):
            caller.msg("You cannot join a profession right now.")
            return

        ok, message = caller.join_profession(args)
        caller.msg(message)
        if ok and hasattr(caller, "sync_client_state"):
            caller.sync_client_state()