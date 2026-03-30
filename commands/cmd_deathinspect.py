from commands.command import Command
from evennia.utils.search import search_object


class CmdDeathInspect(Command):
    """
    Inspect a character's full death-state data.

    Examples:
        @deathinspect kier
    """

    key = "@deathinspect"
    aliases = ["deathinspect"]
    locks = "cmd:perm(Developer) or perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        query = str(self.args or "").strip()
        if not query:
            caller.msg("Inspect whom?")
            return
        target = None
        if query.startswith("#"):
            matches = search_object(query)
            target = matches[0] if matches else None
        if target is None:
            target = caller.search(query, global_search=True)
        if not target:
            return
        if not hasattr(target, "get_death_inspect_lines"):
            caller.msg("That target has no death-state data to inspect.")
            return
        caller.msg("\n".join(target.get_death_inspect_lines()))