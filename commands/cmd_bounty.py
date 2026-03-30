from commands.command import Command


class CmdBounty(Command):
        """
        Review or manage your current bounty target.

        Examples:
            bounty
        """

    key = "bounty"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        warrants = getattr(caller.db, "warrants", None) or {}
        if not warrants:
            caller.msg("You have no active bounties on your head.")
            return

        for region, data in warrants.items():
            caller.msg(f"{region}: bounty {int((data or {}).get('bounty', 0) or 0)}")