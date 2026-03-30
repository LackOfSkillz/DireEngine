from commands.command import Command


class CmdResurrect(Command):
    """
    Restore a dead soul from its corpse.

    Examples:
        resurrect corpse
        resurrect corpse of arannis
    """

    key = "resurrect"
    aliases = ["raise"]
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
            caller.msg("There is no corpse here to restore.")
            return

        corpses = [obj for obj in room.contents if getattr(getattr(obj, "db", None), "is_corpse", False)]
        if not corpses:
            caller.msg("There is no corpse here to restore.")
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
            caller.msg("Resurrect which corpse?")
            return

        restored = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        ok, message = caller.resurrect_from_corpse(corpse, caster=caller) if hasattr(caller, "resurrect_from_corpse") else (False, "You cannot perform that rite.")
        caller.msg(message)
        if ok:
            if restored and restored.location:
                quality = str(getattr(getattr(restored, 'db', None), 'last_recovery_quality', '') or '')
                room_message = f"{restored.key} stirs, breath returning."
                if quality == "perfect":
                    room_message = f"{restored.key} rises with startling clarity as life returns."
                elif quality in {"fragile", "flawed"}:
                    room_message = f"{restored.key} stirs weakly, breath returning with visible strain."
                restored.location.msg_contents(room_message, exclude=[restored])
