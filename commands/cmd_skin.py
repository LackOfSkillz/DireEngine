from commands.command import Command


class CmdSkin(Command):
    """
    Skin a suitable corpse for salvageable materials.

    Examples:
        skin wolf
    """

    key = "skin"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Skin what?")
            return

        candidates = [obj for obj in list(getattr(getattr(self.caller, "location", None), "contents", []) or []) if obj != self.caller]
        target, matches, base_query, index = self.resolve_item_target(self.args.strip(), candidates, default_first=True)
        if not target and matches and index is not None:
            self.msg_item_matches(base_query, matches)
            return
        if not target:
            target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.skin_target(target)
