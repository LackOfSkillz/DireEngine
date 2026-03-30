from commands.command import Command


class CmdEnterPassage(Command):
    """
    Enter a hidden or discovered passage.

    Examples:
        enter passage
    """

    key = "enter passage"
    aliases = ["enterpassage"]
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room or not hasattr(room, "has_passage") or not room.has_passage():
            caller.msg("You are not sure where to enter.")
            return
        if getattr(room, "id", None) not in (getattr(caller.db, "known_passages", None) or []):
            caller.msg("You are not sure where to enter.")
            return

        caller.db.in_passage = True
        caller.msg("You slip into a hidden passage.")
