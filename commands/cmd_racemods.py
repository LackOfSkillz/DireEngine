from commands.command import Command


class CmdRaceMods(Command):
    """
    Inspect the canonical race modifiers on yourself or a target.

    Usage:
      @racemods
      @racemods <target>
    """

    key = "@racemods"
    help_category = "Staff"
    locks = "cmd:perm(Builder)"

    def func(self):
        caller = self.caller
        target = caller

        if self.args:
            target = caller.search(self.args.strip())
            if not target:
                return

        if not hasattr(target, "get_race_debug_payload"):
            caller.msg("That target does not expose race debug data.")
            return

        payload = target.get_race_debug_payload()
        lines = [
            f"Race mods for {target.key}",
            f"Race: {payload['name']} [{payload['race']}]",
            f"Size: {str(payload['size']).title()}",
            f"Carry Modifier: x{float(payload['carry_modifier']):.2f}",
            f"Max Carry: {float(payload['max_carry_weight']):.1f}",
            "Stat Modifiers:",
        ]

        for stat_name, value in payload.get("stat_modifiers", {}).items():
            lines.append(f"  {stat_name.title()}: {int(value):+d}")

        lines.append("Stat Caps:")
        for stat_name, value in payload.get("stat_caps", {}).items():
            lines.append(f"  {stat_name.title()}: {int(value)}")

        lines.append("Learning Modifiers:")
        for category, value in payload.get("learning_modifiers", {}).items():
            lines.append(f"  {category.title()}: x{float(value):.2f}")

        if hasattr(target, "validate_race_application"):
            ok, issues = target.validate_race_application()
            lines.append(f"Invariant: {'OK' if ok else 'MISMATCH'}")
            if not ok:
                lines.extend(f"  - {issue}" for issue in issues)

        caller.msg("\n".join(lines))