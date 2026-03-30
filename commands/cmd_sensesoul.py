from commands.command import Command


class CmdSenseSoul(Command):
    """
    Sense the strength of a soul bound to a corpse.

    Examples:
        sense soul corpse
        sensesoul corpse of arannis
    """

    key = "sense soul"
    aliases = ["sensesoul"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if hasattr(caller, "is_dead") and caller.is_dead():
            caller.msg("The dead cannot search for another soul.")
            return
        if not hasattr(caller, "is_profession") or not caller.is_profession("cleric"):
            caller.msg("Only a cleric can search for a soul that way.")
            return

        room = getattr(caller, "location", None)
        if room is None:
            caller.msg("There is no corpse here to read.")
            return

        corpses = [obj for obj in room.contents if getattr(getattr(obj, "db", None), "is_corpse", False)]
        if not corpses:
            caller.msg("There is no corpse here to read.")
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
            caller.msg("Sense which soul?")
            return

        ok, lines = caller.sense_soul_from_corpse(corpse) if hasattr(caller, "sense_soul_from_corpse") else (False, ["You cannot read that soul."])
        for line in lines:
            caller.msg(line)
