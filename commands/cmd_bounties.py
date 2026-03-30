from evennia.objects.models import ObjectDB

from commands.command import Command


def _find_board(room):
    if not room:
        return None
    return next((obj for obj in room.contents if str(getattr(obj, "key", "") or "").lower() == "a bounty board"), None)


class CmdBounties(Command):
        """
        List the bounties currently available to you.

        Examples:
            bounties
        """

    key = "bounties"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        if not _find_board(caller.location):
            caller.msg("There is no bounty board here.")
            return

        found = False
        for obj in ObjectDB.objects.filter(db_typeclass_path__in=["typeclasses.characters.Character", "typeclasses.npcs.NPC"]):
            if getattr(getattr(obj, "db", None), "is_npc", False):
                continue
            warrants = getattr(getattr(obj, "db", None), "warrants", None) or {}
            for _region, data in warrants.items():
                bounty = int((data or {}).get("bounty", 0) or 0)
                if bounty <= 0:
                    continue
                caller.msg(f"{obj.key} - {bounty} coins")
                found = True

        if not found:
            caller.msg("No active bounties are posted right now.")