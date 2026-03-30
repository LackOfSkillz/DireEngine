from evennia import Command


class CmdDisguise(Command):
    """
    Adopt or remove a disguise identity.

    Examples:
        disguise traveler
        disguise clear
    """

    key = "disguise"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if getattr(caller.db, "in_combat", False):
            caller.msg("You cannot disguise yourself right now.")
            return

        if not args:
            if getattr(caller.db, "disguised", False):
                caller.msg(f"You are currently disguised as {caller.db.disguise_name}.")
            else:
                caller.msg("You are not wearing a disguise.")
            return

        if args.lower() in {"clear", "remove", "off"}:
            caller.clear_disguise()
            caller.msg("You let your borrowed identity fall away.")
            return

        caller.db.disguised = True
        caller.db.disguise_name = args
        caller.db.disguise_profession = caller.get_profession() if hasattr(caller, "get_profession") else None
        caller.msg("You adjust your appearance, blending into a new identity.")
