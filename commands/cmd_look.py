from commands.command import Command


class CmdLook(Command):
    """
    Look at your surroundings or a visible target.

    Examples:
        look
        look twig
        l first twig
        ls
    """

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        raw_query = str(self.args or "").strip()
        if not raw_query:
            target = getattr(caller, "location", None)
            if not target:
                caller.msg("You have no location to look at!")
                return
        else:
            normalized = raw_query.lower()
            if normalized in {"me", "self", "myself"}:
                target = caller
            elif normalized in {"here", "room"}:
                target = getattr(caller, "location", None)
            else:
                target, matches, base_query, _index, _scope = self.resolve_target(
                    raw_query,
                    scopes=("inventory", "characters", "room"),
                )
                if not target and matches:
                    self.msg_target_matches(base_query or raw_query, matches)
                    return
                if not target:
                    target = caller.search(raw_query)
                    if not target:
                        return

        desc = caller.at_look(target)
        self.msg(text=(desc, {"type": "look"}), options=None)