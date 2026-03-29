from evennia import Command


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdSurvivalDebug(Command):
    """
    Inspect survival-skill visibility state.

    Usage:
      survivaldebug
      survivaldebug <target>
    """

    key = "survivaldebug"
    help_category = "Admin"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use survivaldebug.")
            return

        target = self.caller
        if (self.args or "").strip():
            target = self.caller.search(self.args.strip())
            if not target:
                return

        if not hasattr(target, "get_shared_survival_skills"):
            self.caller.msg(f"{target.key} does not expose survival skill helpers.")
            return

        shared_visible = ", ".join(target.format_skill_name(name) for name in target.get_shared_survival_skills()) or "none"
        hidden = ", ".join(target.format_skill_name(name) for name in target.get_hidden_survival_skills()) or "none"
        learned = ", ".join(
            target.format_skill_name(name)
            for name, data in (target.db.skills or {}).items()
            if target.get_skill_metadata(name).get("category") == "survival" and data.get("rank", 0) > 0
        ) or "none"

        self.caller.msg(
            "\n".join(
                [
                    f"Survival visibility for {target.key}:",
                    f"Shared visible: {shared_visible}",
                    f"Hidden: {hidden}",
                    f"Learned: {learned}",
                ]
            )
        )