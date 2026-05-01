"""@calendar admin command - inspect the current game-time calendar state."""

from commands.command import Command
from world.calendar import get_calendar_state


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdCalendar(Command):
    """
    Show the current calendar state.

    Usage:
      @calendar
      gametime
    """

    key = "@calendar"
    aliases = ["gametime"]
    help_category = "Admin"
    locks = "cmd:perm(Admin) or perm(Developer)"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def func(self):
        if not self._is_admin():
            self.caller.msg("You do not have permission to use this command.")
            return

        state = get_calendar_state()
        real_world = state["real_world"]
        game_time = state["game_time"]
        configuration = state["configuration"]

        lines = [
            "DireEngine Calendar",
            "─" * 40,
            f"Real-world time:    {real_world['iso']} ({real_world['timezone']})",
            f"Real-world season:  {real_world['season']}",
            "",
            f"Game time elapsed:  {game_time['elapsed_days']}d {game_time['elapsed_hours']}h {game_time['elapsed_minutes']}m",
            f"Game time-of-day:   {game_time['time_of_day']}",
            "",
            f"Time factor:        {configuration['time_factor']}× real time",
            f"Ignore downtimes:   {configuration['ignore_downtimes']}",
            "Epoch:              "
            f"{configuration['epoch'] if configuration['epoch'] is not None else 'server first start'}",
        ]
        self.caller.msg("\n".join(lines))