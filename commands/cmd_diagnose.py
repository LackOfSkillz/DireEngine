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
        if hasattr(self.caller, "use_skill") and hasattr(target, "get_empath_wounds"):
            self.caller.use_skill("empathy", apply_roundtime=False, emit_placeholder=False, require_known=False, difficulty=max(10, sum(target.get_empath_wounds().values())))