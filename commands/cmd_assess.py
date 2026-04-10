from commands.command import Command


class CmdAssess(Command):
    """
    Review the exact wound levels of your linked patient.

    Examples:
        assess
        assess patient
    """

    key = "assess"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        target_query = str(self.args or "").strip()
        ok, lines = caller.assess_empath_link(target_query=target_query) if hasattr(caller, "assess_empath_link") else (False, ["You have no patient to assess."])
        for line in lines:
            caller.msg(line)
