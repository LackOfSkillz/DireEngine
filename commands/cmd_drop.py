from commands.command import Command


class CmdDrop(Command):
    """
        Put down something you are carrying or wearing.

        Examples:
            drop sword
            drop cloak
    """

    key = "drop"
    help_category = "Equipment"

    def func(self):
        if not self.args:
            self.caller.msg("What do you want to drop?")
            return

        item, matches, base_query, index = self.caller.resolve_numbered_candidate(
            self.args,
            self.caller.contents,
            default_first=True,
        )
        if not item:
            item = self.caller.find_worn_item(self.args)
            if not item:
                if matches and index is not None:
                    self.caller.msg_numbered_matches(base_query, matches)
                else:
                    self.caller.search(base_query or self.args)
                return
            self.caller.unequip_item(item)

        if self.caller.get_weapon() == item:
            self.caller.clear_equipped_weapon()

        if not self.caller.location:
            self.caller.msg("There is nowhere here to drop that.")
            return

        item.move_to(self.caller.location, quiet=True, use_destination=False)
        self.caller.msg(f"You drop {item.key}.")