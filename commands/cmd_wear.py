from commands.command import Command


class CmdWear(Command):
    """
    Put on a piece of gear you are carrying.

    Examples:
      wear cloak
      wear belt sheath
      wea cap
    """

    key = "wear"
    aliases = ["wea"]
    help_category = "Equipment"

    def func(self):
        if not self.args:
            self.caller.msg("What do you want to wear?")
            return

        obj, matches, base_query, index = self.caller.resolve_numbered_candidate(
            self.args,
            self.caller.get_visible_carried_items(),
            default_first=True,
        )
        if not obj:
            if matches and index is not None:
                self.caller.msg_numbered_matches(base_query, matches)
            else:
                self.caller.search(base_query or self.args)
            return
        success, msg = self.caller.equip_item(obj)
        if success and getattr(obj.db, "is_sheath", False):
            self.caller.set_preferred_sheath(obj)
        self.caller.msg(msg)