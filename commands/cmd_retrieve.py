from commands.command import Command
from world.systems.justice import retrieve_confiscated_items


class CmdRetrieve(Command):
    """
    Retrieve an item from vault storage or reclaim confiscated belongings.

    Examples:
        retrieve sword
        retrieve items
    """

    key = "retrieve"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        item_name = (self.args or "").strip()
        if not item_name:
            self.caller.msg("Retrieve what?")
            return
        if item_name.lower() == "items":
            result = retrieve_confiscated_items(self.caller)
            if not result.get("ok"):
                self.caller.msg(str(result.get("reason") or "You cannot reclaim your belongings right now."))
            return
        self.caller.retrieve_vault_item(item_name)
