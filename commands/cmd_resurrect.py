from commands.command import Command


class CmdResurrect(Command):
    """
    Restore a dead soul from its corpse.

    Examples:
        resurrect corpse
        resurrect corpse of arannis
    """

    key = "revive"
    aliases = ["resurrect", "raise"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if hasattr(caller, "is_dead") and caller.is_dead():
            caller.msg("The dead cannot perform a resurrection rite.")
            return
        if hasattr(caller, "is_profession") and not caller.is_profession("cleric"):
            caller.msg("Only a cleric can guide a soul back from its corpse.")
            return

        room = getattr(caller, "location", None)
        if room is None:
            caller.msg("There is no corpse here to revive.")
            return

        corpses = [obj for obj in room.contents if getattr(getattr(obj, "db", None), "is_corpse", False)]
        if not corpses:
            caller.msg("There is no corpse here to revive.")
            return

        query = str(self.args or "").strip()
        corpse = None
        if query:
            corpse, matches, base_query, index = caller.resolve_numbered_candidate(
                query,
                corpses,
                default_first=True,
            )
            if not corpse:
                if matches and index is not None:
                    caller.msg_numbered_matches(base_query, matches)
                else:
                    caller.search(base_query or query, candidates=corpses)
                return
        elif len(corpses) == 1:
            corpse = corpses[0]
        else:
            caller.msg("Revive which corpse?")
            return

        ok, message = caller.start_cleric_revive(corpse) if hasattr(caller, "start_cleric_revive") else (False, "You cannot perform that rite.")
        caller.msg(message)
