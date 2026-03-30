from commands.command import Command


class CmdStore(Command):
    """
    Place an item into vault storage.

    Examples:
        store sword
    """

    key = "store"
    locks = "cmd:all()"
    help_category = "Equipment"

    def func(self):
        item_name = (self.args or "").strip()
        if not item_name:
            self.caller.msg("Store what?")
            return
        self.caller.store_vault_item(item_name)
