from evennia import Command
from evennia.objects.models import ObjectDB


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdRenew(Command):
    """
    Fully restore yourself or another target.

    This is an admin command.

    Examples:
      renew
      renew jekar
      renew training dummy
      renew room
      renew all
    """

    key = "renew"
    aliases = ["ren"]
    help_category = "Admin"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def _get_renewable_room_targets(self):
        if not self.caller.location:
            return [self.caller] if hasattr(self.caller, "renew_state") else []

        targets = []
        seen_ids = set()
        for obj in self.caller.location.contents:
            if not hasattr(obj, "renew_state"):
                continue
            if obj.id in seen_ids:
                continue
            seen_ids.add(obj.id)
            targets.append(obj)
        return targets

    def _get_renewable_global_targets(self):
        targets = []
        seen_ids = set()
        for obj in ObjectDB.objects.all().order_by("id"):
            if not hasattr(obj, "renew_state"):
                continue
            if obj.id in seen_ids:
                continue
            seen_ids.add(obj.id)
            targets.append(obj)
        return targets

    def _renew_targets(self, targets):
        renewed = []
        for target in targets:
            if not hasattr(target, "renew_state"):
                continue
            target.renew_state()
            renewed.append(target)
        return renewed

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use renew.")
            return

        arg = (self.args or "").strip().lower()

        if not arg:
            self.caller.renew_state()
            self.caller.msg("You renew yourself completely.")
            return

        if arg == "room":
            renewed = self._renew_targets(self._get_renewable_room_targets())
            if not renewed:
                self.caller.msg("There is no one here to renew.")
                return
            for target in renewed:
                if target != self.caller:
                    target.msg("A restorative force washes over you. Your body is fully renewed.")
            self.caller.msg(f"You renew the room completely. ({len(renewed)} targets)")
            return

        if arg == "all":
            renewed = self._renew_targets(self._get_renewable_global_targets())
            if not renewed:
                self.caller.msg("There is no one to renew.")
                return
            for target in renewed:
                if target != self.caller:
                    target.msg("A restorative force washes over you. Your body is fully renewed.")
            self.caller.msg(f"You renew all renewable targets. ({len(renewed)} targets)")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        if not hasattr(target, "renew_state"):
            self.caller.msg(f"You cannot renew {target.key}.")
            return

        target.renew_state()
        if target == self.caller:
            self.caller.msg("You renew yourself completely.")
            return

        self.caller.msg(f"You renew {target.key} completely.")
        target.msg("A restorative force washes over you. Your body is fully renewed.")