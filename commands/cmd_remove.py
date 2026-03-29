from evennia import Command


class CmdRemove(Command):
    """
        Take off something you are wearing.

        Examples:
            remove cloak
            rem ring
    """

    key = "remove"
    aliases = ["rem"]
    help_category = "Equipment"

    def func(self):
        if not self.args:
            self.caller.msg("What do you want to remove?")
            return

        item = self.caller.find_worn_item(self.args)
        if not item:
            self.caller.msg("You are not wearing that.")
            return

        success, msg = self.caller.unequip_item(item)
        self.caller.msg(msg)