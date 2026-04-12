from commands.command import Command


class CmdAssess(Command):
    """
    Review the exact wound levels of your linked patient.

    Examples:
        assess
        assess patient
    """

    key = "assess"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        target_query = str(self.args or "").strip()
        room = getattr(caller, "location", None)
        corpses = [obj for obj in getattr(room, "contents", []) if getattr(getattr(obj, "db", None), "is_corpse", False)] if room else []
        if hasattr(caller, "is_profession") and caller.is_profession("cleric"):
            corpse = None
            if target_query:
                corpse, matches, base_query, index = caller.resolve_numbered_candidate(target_query, corpses, default_first=True) if hasattr(caller, "resolve_numbered_candidate") else (None, [], target_query, None)
                if not corpse:
                    if matches and index is not None and hasattr(caller, "msg_numbered_matches"):
                        caller.msg_numbered_matches(base_query, matches)
                    else:
                        caller.msg("Assess which corpse?")
                    return
            elif len(corpses) == 1:
                corpse = corpses[0]
            elif corpses:
                caller.msg("Assess which corpse?")
                return
            if corpse and hasattr(caller, "assess_cleric_corpse"):
                ok, lines = caller.assess_cleric_corpse(corpse)
                for line in lines:
                    caller.msg(line)
                return
        if hasattr(caller, "is_profession") and caller.is_profession("empath") and target_query:
            corpse, matches, base_query, index = caller.resolve_numbered_candidate(target_query, corpses, default_first=True) if hasattr(caller, "resolve_numbered_candidate") else (None, [], target_query, None)
            if corpse and hasattr(caller, "assess_empath_corpse"):
                ok, lines = caller.assess_empath_corpse(corpse)
                for line in lines:
                    caller.msg(line)
                return
            if matches and index is not None and hasattr(caller, "msg_numbered_matches"):
                caller.msg_numbered_matches(base_query, matches)
                return
        ok, lines = caller.assess_empath_link(target_query=target_query) if hasattr(caller, "assess_empath_link") else (False, ["You have no patient to assess."])
        for line in lines:
            caller.msg(line)
