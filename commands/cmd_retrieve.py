from commands.command import Command


class CmdRetrieve(Command):
    """
    Retrieve an item from vault storage.

    Examples:
        retrieve sword
    """

    key = "retrieve"
    locks = "cmd:all()"
    help_category = "Equipment"

    def func(self):
        item_name = (self.args or "").strip()
        if not item_name:
            self.caller.msg("Retrieve what?")
            return
        self.caller.retrieve_vault_item(item_name)
