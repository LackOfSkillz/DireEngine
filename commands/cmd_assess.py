from commands.command import Command


class CmdAssess(Command):
    """
    Review the exact wound levels of your linked patient.

    Examples:
        assess
    """

    key = "assess"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        ok, lines = caller.assess_empath_link() if hasattr(caller, "assess_empath_link") else (False, ["You have no patient to assess."])
        for line in lines:
            caller.msg(line)
