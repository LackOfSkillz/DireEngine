from evennia import Command
from evennia.objects.models import ObjectDB
import time

from world.systems.engine_flags import is_enabled
from world.systems.metrics import increment_counter, record_event
from world.systems.target_scope import get_active_targets, get_nearby_targets, get_visible_targets


ADMIN_PERMISSIONS = ("Admin", "Developer")
RENEWABLE_TYPECLASS_PATHS = (
    "typeclasses.characters.Character",
    "typeclasses.npcs.NPC",
)


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
        scanned_count = 0
        for obj in ObjectDB.objects.filter(db_typeclass_path__in=RENEWABLE_TYPECLASS_PATHS).order_by("id"):
            scanned_count += 1
            if not hasattr(obj, "renew_state"):
                continue
            if obj.id in seen_ids:
                continue
            seen_ids.add(obj.id)
            targets.append(obj)
        return targets, scanned_count

    def _is_renewable_target(self, obj):
        return hasattr(obj, "renew_state")

    def _get_renewable_scoped_targets(self):
        visible = get_visible_targets(self.caller, predicate=self._is_renewable_target)
        nearby = get_nearby_targets(self.caller, predicate=self._is_renewable_target, radius=1)
        active = get_active_targets(self.caller, predicate=self._is_renewable_target)

        targets = []
        seen_ids = set()
        for obj in [*visible, *nearby, *active]:
            obj_id = getattr(obj, "id", None)
            marker = obj_id if obj_id is not None else id(obj)
            if marker in seen_ids:
                continue
            seen_ids.add(marker)
            targets.append(obj)
        scope = {
            "visible_count": len(visible),
            "nearby_count": len(nearby),
            "active_count": len(active),
            "scanned_count": len(targets),
        }
        return targets, scope

    def _select_renew_all_targets(self):
        started = time.perf_counter()
        if is_enabled("interest_activation"):
            mode = "scoped"
            targets, scope = self._get_renewable_scoped_targets()
        else:
            mode = "legacy-global"
            targets, scanned_count = self._get_renewable_global_targets()
            scope = {
                "visible_count": 0,
                "nearby_count": 0,
                "active_count": 0,
                "scanned_count": int(scanned_count or 0),
            }

        duration_ms = (time.perf_counter() - started) * 1000.0
        increment_counter(f"command.renew.target_select.{mode}")
        record_event(
            "command.renew.target_select",
            duration_ms,
            metadata={
                "mode": mode,
                "target_count": len(targets),
                "scanned_count": int(scope.get("scanned_count", 0) or 0),
                "visible_count": int(scope.get("visible_count", 0) or 0),
                "nearby_count": int(scope.get("nearby_count", 0) or 0),
                "active_count": int(scope.get("active_count", 0) or 0),
            },
        )
        return targets, mode, scope

    def _renew_targets(self, targets):
        started = time.perf_counter()
        renewed = []
        for target in targets:
            if not hasattr(target, "renew_state"):
                continue
            target.renew_state()
            renewed.append(target)
        record_event(
            "command.renew.execute",
            (time.perf_counter() - started) * 1000.0,
            metadata={"target_count": len(renewed)},
        )
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
            targets, mode, scope = self._select_renew_all_targets()
            renewed = self._renew_targets(targets)
            if not renewed:
                self.caller.msg("There is no one to renew.")
                return
            for target in renewed:
                if target != self.caller:
                    target.msg("A restorative force washes over you. Your body is fully renewed.")
            if mode == "scoped":
                self.caller.msg(
                    f"You renew nearby active renewable targets. ({len(renewed)} targets; visible={int(scope.get('visible_count', 0) or 0)}, nearby={int(scope.get('nearby_count', 0) or 0)}, active={int(scope.get('active_count', 0) or 0)})"
                )
            else:
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