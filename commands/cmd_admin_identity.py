from evennia.objects.models import ObjectDB

from commands.command import Command
from systems.appearance.normalizer import inspect_character_identity, normalize_character_identity


ADMIN_PERMISSIONS = ("Admin", "Developer")
IDENTITY_AUDIT_TYPECLASS_PATHS = (
    "typeclasses.characters.Character",
    "typeclasses.npcs.NPC",
)


class CmdCheckIdentityIntegrity(Command):
    """
    Audit identity integrity across character-like objects.

    Usage:
      check_identity_integrity
    """

    key = "check_identity_integrity"
    aliases = ["checkidentity"]
    help_category = "Admin"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def _collect_results(self, *, apply_repairs=False, prefix_filter=None):
        results = {
            "missing_identity": [],
            "incomplete_identity": [],
            "non_renderable_identity": [],
            "fallback_used": [],
            "healed": [],
        }

        scanned = 0
        queryset = ObjectDB.objects.filter(db_typeclass_path__in=IDENTITY_AUDIT_TYPECLASS_PATHS).order_by("id")
        for obj in queryset:
            label = f"{obj.key}#{obj.id}"
            if prefix_filter and not str(getattr(obj, "key", "") or "").lower().startswith(prefix_filter):
                continue
            scanned += 1
            report = inspect_character_identity(obj)
            if report["missing_identity"]:
                results["missing_identity"].append(label)
            if report["needs_repair"]:
                results["incomplete_identity"].append(label)
            if not report["renderable"]:
                results["non_renderable_identity"].append(label)
            if report["fallback_used"]:
                results["fallback_used"].append(label)
            if apply_repairs and report["needs_repair"]:
                _, repaired = normalize_character_identity(obj, log_repairs=True)
                if repaired:
                    results["healed"].append(label)
        return scanned, results

    def _render_results(self, scanned, results, *, prefix_filter=None, mode_label="Audit"):
        scope = f" prefix={prefix_filter}" if prefix_filter else ""
        lines = [
            f"{mode_label} scope:{scope or ' all'}",
            f"Scanned: {scanned}",
            f"Missing identity: {len(results['missing_identity'])}",
            f"Incomplete identity: {len(results['incomplete_identity'])}",
            f"Non-renderable identity: {len(results['non_renderable_identity'])}",
            f"Fallback used this runtime: {len(results['fallback_used'])}",
        ]
        if "healed" in results:
            lines.append(f"Healed: {len(results['healed'])}")

        for key, title in (
            ("missing_identity", "Missing identity"),
            ("incomplete_identity", "Incomplete identity"),
            ("non_renderable_identity", "Non-renderable identity"),
            ("fallback_used", "Fallback used this runtime"),
            ("healed", "Healed"),
        ):
            if key not in results:
                continue
            entries = results[key]
            lines.append(f"{title}: {', '.join(entries) if entries else 'none'}")
        return "\n".join(lines)

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use check_identity_integrity.")
            return
        prefix_filter = str(self.args or "").strip().lower() or None
        scanned, results = self._collect_results(apply_repairs=False, prefix_filter=prefix_filter)
        self.caller.msg(self._render_results(scanned, results, prefix_filter=prefix_filter, mode_label="Identity audit"))


class CmdHealIdentityIntegrity(CmdCheckIdentityIntegrity):
    """
    Heal identity integrity across character-like objects.

    Usage:
      heal_identity_integrity
      heal_identity_integrity/apply
      heal_identity_integrity/apply <prefix>
    """

    key = "heal_identity_integrity"
    aliases = ["healidentity"]

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use heal_identity_integrity.")
            return

        prefix_filter = str(self.args or "").strip().lower() or None
        apply_repairs = "apply" in {switch.lower() for switch in getattr(self, "switches", [])}
        scanned, results = self._collect_results(apply_repairs=apply_repairs, prefix_filter=prefix_filter)
        mode_label = "Identity heal apply" if apply_repairs else "Identity heal dry-run"
        self.caller.msg(self._render_results(scanned, results, prefix_filter=prefix_filter, mode_label=mode_label))
        if not apply_repairs:
            self.caller.msg("Run heal_identity_integrity/apply to persist repairs.")