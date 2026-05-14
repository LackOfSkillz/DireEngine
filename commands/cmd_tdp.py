from commands.command import Command


ADMIN_PERMISSIONS = ("Admin", "Developer")


def can_view_tdp_pool(caller):
    account = getattr(caller, "account", None) or caller
    if account is None or not hasattr(account, "check_permstring"):
        return False
    return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)


class CmdTDP(Command):
    """
    Review your Time Development Point totals.

    Examples:
        tdp
    """

    key = "tdp"
    locks = "cmd:all()"
    help_category = "Training & Lore"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()

        lines = [f"Time Development Points: {int(getattr(caller.db, 'tdp', 0) or 0)}"]
        if can_view_tdp_pool(caller):
            lines.append(f"TDP Pool Progress: {int(getattr(caller.db, 'tdp_pool', 0) or 0)}/200")
        caller.msg("\n".join(lines))