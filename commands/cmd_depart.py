from commands.command import Command


class CmdDepart(Command):
    """
    Leave death behind and return by the path your favor allows.

    Examples:
        depart
        depart grave
        depart coins
        depart items
        depart full
    """

    key = "depart"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "depart_self"):
            caller.msg("You cannot depart from here.")
            return
        if not hasattr(caller, "is_dead") or not caller.is_dead():
            caller.msg("You are not dead.")
            return

        mode = str(self.args or "").strip().lower() or None
        if mode == "help":
            mode = None
        corpse = caller.get_death_corpse() if hasattr(caller, "get_death_corpse") else None
        chosen_mode = caller.get_depart_mode(corpse=corpse, requested_mode=mode) if hasattr(caller, "get_depart_mode") else None

        if mode and chosen_mode is None:
            caller.msg("You do not have enough favor for that departure path. Choose grave, coins, items, or full.")
            return

        ok, message = caller.depart_self(mode=mode)
        caller.msg(message)
        if ok and getattr(caller, "location", None):
            caller.location.msg_contents(f"{caller.key} draws a ragged breath and returns from the edge of death.", exclude=[caller])
