from commands.command import Command


class CmdLayLow(Command):
    """
    Try to reduce heat from the justice system.

    Examples:
        laylow
    """

    key = "laylow"
    aliases = ["lay low"]
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        warrants = dict(getattr(caller.db, "warrants", None) or {})
        if not warrants:
            caller.msg("You keep your head down, but no one seems to be hunting you.")
            return

        for region, data in list(warrants.items()):
            data["severity"] = max(0, int(data.get("severity", 0) or 0) - 1)
            if data["severity"] <= 0:
                warrants.pop(region, None)
            else:
                warrants[region] = data

        caller.db.warrants = warrants
        caller.db.last_known_region = None
        if not warrants and not getattr(caller.db, "fine_due", 0):
            caller.db.crime_flag = False
        caller.msg("You keep a low profile and obscure your trail.")
