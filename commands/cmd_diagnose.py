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
        if not self.args:
            self.caller.msg("Diagnose whom?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        if hasattr(target, "format_empath_diagnosis"):
            for line in target.format_empath_diagnosis(precise=False):
                self.caller.msg(line)
        if hasattr(target, "get_pressure_level"):
            self.caller.msg(f"Pressure: {target.get_pressure_level()}")
        if hasattr(target, "get_exhaustion") and hasattr(target, "get_exhaustion_profile"):
            self.caller.msg(f"Exhaustion: {target.get_exhaustion()}/100 ({target.get_exhaustion_profile().get('label', 'Fresh')})")
        if hasattr(target, "get_combat_rhythm_state"):
            self.caller.msg(f"Combat Rhythm: {target.get_combat_rhythm_state().title()}")
        if hasattr(self.caller, "use_skill") and hasattr(target, "get_empath_wounds"):
            self.caller.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=max(10, sum(target.get_empath_wounds().values())))