from commands.command import Command


class CmdDiagnose(Command):
    """
    Assess another character's injuries.

    Examples:
      diagnose jekar
    """

    key = "diagnose"
    help_category = "Character"

    def func(self):
        if not self.caller.is_empath():
            self.caller.msg("You lack the sensitivity to diagnose wounds.")
            return

        if not self.args:
            self.caller.msg("Diagnose whom?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        target.ensure_body_state()

        for part in target.db.injuries:
            body_part = target.get_body_part(part) or {}
            ext = target.get_injury_severity(body_part.get("external", 0))
            inte = target.get_injury_severity(body_part.get("internal", 0))
            if ext != "minor" or inte != "minor":
                self.caller.msg(f"{target.format_body_part_name(part)}: {ext} / {inte}")
            if body_part.get("bleed", 0) > 0:
                self.caller.msg(f"{target.format_body_part_name(part)} is bleeding.")

        total = sum(target.get_part_trauma(data) for data in (target.db.injuries or {}).values())
        self.caller.msg(f"Overall condition: {target.get_injury_severity(total)}")
        self.caller.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=max(10, total))