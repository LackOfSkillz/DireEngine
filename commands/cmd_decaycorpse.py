from commands.command import Command
from evennia.utils.search import search_object


class CmdDecayCorpse(Command):
    """
    Force a corpse to decay into its grave immediately.

    Examples:
        @decaycorpse corpse of kier
        @decaycorpse #123
    """

    key = "@decaycorpse"
    aliases = ["decaycorpse"]
    locks = "cmd:perm(Developer) or perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        query = str(self.args or "").strip()
        if not query:
            caller.msg("Decay which corpse?")
            return
        target = None
        if query.startswith("#"):
            matches = search_object(query)
            target = matches[0] if matches else None
        if target is None:
            target = caller.search(query, global_search=True)
        if not target:
            return
        if not getattr(getattr(target, "db", None), "is_corpse", False):
            caller.msg("That is not a corpse.")
            return
        grave = target.decay_to_grave() if hasattr(target, "decay_to_grave") else None
        if grave is None:
            caller.msg("That corpse cannot be decayed right now.")
            return
        caller.msg(f"You force {target.key} to decay into {grave.key}.")
