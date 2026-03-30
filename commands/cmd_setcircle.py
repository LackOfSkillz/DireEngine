from evennia import Command


class CmdSetCircle(Command):
        """
        Set a character's profession circle for testing or admin work.

        Examples:
            setcircle ranger = 5
        """

    key = "setcircle"
    locks = "cmd:perm(Developer) or perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Usage: setcircle <player> <value>")
            return

        target_name, _, value_text = args.rpartition(" ")
        if not target_name or not value_text:
            caller.msg("Usage: setcircle <player> <value>")
            return

        target = caller.search(target_name.strip(), global_search=True)
        if not target:
            return

        try:
            circle = int(value_text)
        except ValueError:
            caller.msg("Circle must be a number.")
            return

        if not hasattr(target, "set_warrior_circle"):
            caller.msg("That target cannot have a Warrior circle.")
            return

        target.set_warrior_circle(circle, emit_messages=True)
        caller.msg(f"Set {target.key}'s Warrior circle to {target.get_warrior_circle()}.")
        if caller != target:
            target.msg(f"Your Warrior circle is now {target.get_warrior_circle()}.")
