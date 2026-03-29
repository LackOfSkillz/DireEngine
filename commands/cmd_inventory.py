from evennia import Command


class CmdInventory(Command):
    """
        See what you are carrying in your hands and pack.

        Examples:
            inventory
            inv
            i
    """

    key = "inventory"
    aliases = ["inv", "i"]
    help_category = "Equipment"

    def func(self):
        carried = [
            item for item in self.caller.contents
            if getattr(item.db, "worn_by", None) != self.caller
        ]
        if not carried:
            self.caller.msg("You are carrying nothing.")
            return

        lines = ["You are carrying:"]
        for item in carried:
            lines.append(f" {item.key}")
        self.caller.msg("\n".join(lines))