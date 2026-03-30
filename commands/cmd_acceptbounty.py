from evennia import search_object

from commands.command import Command
from commands.cmd_bounties import _find_board


def _find_character(name):
    results = search_object(name)
    for obj in results:
        if hasattr(obj, "db") and not getattr(obj.db, "is_npc", False):
            return obj
    return None


class CmdAcceptBounty(Command):
    """
    Accept an available bounty contract.

    Examples:
        acceptbounty 3
    """

    key = "acceptbounty"
    aliases = ["accept bounty"]
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        if not _find_board(caller.location):
            caller.msg("There is no bounty board here.")
            return
        if getattr(caller.db, "active_bounty", None):
            caller.msg("You are already pursuing a bounty.")
            return

        target_name = str(self.args or "").strip()
        if not target_name:
            caller.msg("Accept bounty on whom?")
            return

        target = _find_character(target_name)
        if not target:
            caller.msg("No such bounty target is posted.")
            return
        warrants = getattr(target.db, "warrants", None) or {}
        if not any(int((data or {}).get("bounty", 0) or 0) > 0 for data in warrants.values()):
            caller.msg("No such bounty target is posted.")
            return

        caller.db.active_bounty = target.id
        caller.msg(f"You accept the bounty on {target.key}.")
