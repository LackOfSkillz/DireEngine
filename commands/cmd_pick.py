from commands.command import Command


class CmdPick(Command):
    """
    Pick a lock on a container or door.

    Examples:
        pick chest
        pick gate
    """

    key = "pick"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Pick what?")
            return

        try:
            from systems import aftermath

            if aftermath.handle_pick(self.caller, self.args):
                return
        except Exception:
            pass

        if " with " in self.args:
            target_part, pick_part = self.args.split(" with ", 1)
        else:
            target_part = self.args
            pick_part = None

        target = self.caller.search(target_part.strip())
        if not target:
            return

        if not self.caller.is_box_target(target):
            self.caller.msg("You can't pick that.")
            return

        if pick_part:
            grade = pick_part.strip().lower()
            pick = self.caller.get_lockpick_by_grade(grade)
            if not pick:
                self.caller.msg(f"You don't have a {grade} pick.")
                return
        else:
            pick = self.caller.get_active_lockpick()

        self.caller.pick_box(target, pick=pick)
