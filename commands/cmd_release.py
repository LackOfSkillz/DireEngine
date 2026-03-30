from commands.command import Command


class CmdRelease(Command):
    """
    Release one or more empathic links.

    Examples:
        release
        release all
        release jekar
    """

    key = "release"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip()
        if args.lower() == "all":
            if hasattr(caller, "remove_empath_link") and caller.remove_empath_link(clear_all=True):
                caller.msg("You let your empathic links fade.")
                return
            caller.msg("You have no active empathic links.")
            return
        if args:
            target = caller.search(args, location=caller.location)
            if not target:
                return
            if hasattr(caller, "remove_empath_link") and caller.remove_empath_link(target=target):
                caller.msg(f"You release your bond with {target.key}.")
                return
            caller.msg("You are not linked to them.")
            return
        if hasattr(caller, "remove_empath_link") and caller.remove_empath_link():
            caller.msg("You let the empathic link fade.")
            return
        caller.msg("You have no active empathic link.")
