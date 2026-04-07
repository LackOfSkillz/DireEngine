from commands.command import Command
from systems.chargen.mirror import cycle_current_option, is_chargen_active


class CmdTouch(Command):
    """
    Establish an empathic diagnostic link with a patient.

    Examples:
        touch jekar
    """

    key = "touch"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if is_chargen_active(caller) and self.args and self.args.strip().lower() == "mirror":
            result = cycle_current_option(caller)
            if result.get("error"):
                caller.msg(result["error"])
            if result.get("message"):
                caller.msg(result["message"])
            if result.get("prompt"):
                caller.msg(result["prompt"])
            return
        if not caller.is_empath():
            caller.msg("You lack the sensitivity to establish that sort of link.")
            return
        if not self.args:
            caller.msg("Touch whom?")
            return
        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        ok, lines = caller.touch_empath_target(target) if hasattr(caller, "touch_empath_target") else (False, ["You fail to form a diagnostic link."])
        for line in lines:
            caller.msg(line)
