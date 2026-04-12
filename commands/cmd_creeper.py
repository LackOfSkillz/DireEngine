from commands.command import Command
from evennia.accounts.models import AccountDB

from utils.creeper import get_creeper_config
from utils.creeper import set_creeper_all
from utils.creeper import start_creeper_for_player
from utils.creeper import stop_all_creeper
from utils.creeper import stop_creeper_for_player


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdCreeper(Command):
    """
    Toggle command logging for selected players.

    Usage:
      creeper <playername>
      creeper all
      creeper stop <playername>
      creeper stop all
    """

    key = "creeper"
    help_category = "Admin"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def _find_account_name(self, query):
        query = (query or "").strip()
        if not query:
            return None

        account = AccountDB.objects.filter(username__iexact=query).first()
        if account:
            return account.username

        for candidate in AccountDB.objects.all().order_by("id"):
            if str(candidate.username).lower().startswith(query.lower()):
                return candidate.username

        target = self.caller.search(query, global_search=True, quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if target and getattr(target, "account", None):
            return target.account.username
        if target and getattr(target, "key", None):
            return target.key
        return None

    def _render_status(self, config):
        watched = ", ".join(config.get("players", [])) or "none"
        all_enabled = "on" if config.get("all") else "off"
        return f"Creeper status: all={all_enabled}; watched={watched}."

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use creeper.")
            return

        arg = (self.args or "").strip()
        if not arg:
            self.caller.msg(self._render_status(get_creeper_config()))
            self.caller.msg("Usage: creeper <playername> | creeper all | creeper stop <playername> | creeper stop all")
            return

        lowered = arg.lower()
        if lowered == "all":
            config = set_creeper_all(True)
            self.caller.msg("Creeper now logs commands for all players.")
            self.caller.msg(self._render_status(config))
            return

        if lowered == "stop all":
            config = stop_all_creeper()
            self.caller.msg("Creeper logging has been fully disabled.")
            self.caller.msg(self._render_status(config))
            return

        if lowered.startswith("stop "):
            player_name = self._find_account_name(arg[5:].strip())
            if not player_name:
                self.caller.msg("No matching player was found to stop logging.")
                return
            config = stop_creeper_for_player(player_name)
            self.caller.msg(f"Creeper stopped logging {player_name}.")
            self.caller.msg(self._render_status(config))
            return

        player_name = self._find_account_name(arg)
        if not player_name:
            self.caller.msg("No matching player was found to log.")
            return

        config = start_creeper_for_player(player_name)
        self.caller.msg(f"Creeper now logs commands for {player_name}.")
        self.caller.msg(self._render_status(config))