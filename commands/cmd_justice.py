from commands.command import Command


class CmdJustice(Command):
    key = "justice"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        law = room.get_law_type() if room and hasattr(room, "get_law_type") else "standard"
        caller.msg(f"Justice in this area: {law}")

        warrants = getattr(caller.db, "warrants", None) or {}
        if not warrants:
            caller.msg("You have no active warrants.")
            return

        for region, data in warrants.items():
            severity = int((data or {}).get("severity", 0) or 0)
            caller.msg(f"{region}: severity {severity}")