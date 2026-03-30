from commands.command import Command
from evennia.utils.search import search_object


class CmdRes(Command):
    """
    Force a dead player back to life, bypassing normal requirements.

    Examples:
        @res kier
    """

    key = "@res"
    aliases = ["forceres", "res"]
    locks = "cmd:perm(Developer) or perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        query = str(self.args or "").strip()
        if not query:
            caller.msg("Resurrect whom?")
            return
        target = None
        if query.startswith("#"):
            matches = search_object(query)
            target = matches[0] if matches else None
        if target is None:
            target = caller.search(query, global_search=True)
        if not target:
            return
        if not hasattr(target, "force_resurrect"):
            caller.msg("That target cannot be resurrected this way.")
            return
        corpse = target.get_death_corpse() if hasattr(target, "get_death_corpse") else None
        ok, message = target.force_resurrect(corpse=corpse, helper=caller)
        caller.msg(message)
        if ok and target != caller:
            target.msg("A divine force drags you back into life.")