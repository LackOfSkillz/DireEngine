from commands.command import Command

from server.systems.loot import roll_loot


class CmdLootDebug(Command):
    """
    Simulate a loot table roll without spawning items.

    Usage:
      @lootdebug <loot_table_id>
    """

    key = "@lootdebug"
    aliases = ["lootdebug"]
    locks = "cmd:perm(Developer) or perm(Admin)"
    help_category = "Admin"

    def func(self):
        loot_id = str(self.args or "").strip()
        if not loot_id:
            self.caller.msg("Usage: @lootdebug <loot_table_id>")
            return

        try:
            drops = roll_loot(loot_id)
        except ValueError as error:
            self.caller.msg(str(error))
            return

        if not drops:
            self.caller.msg(f"{loot_id}: no drops")
            return

        self.caller.msg("\n".join(f"{entry['item_id']} x{entry['count']}" for entry in drops))