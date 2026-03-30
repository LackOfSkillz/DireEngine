import random

from commands.command import Command


class CmdFindPassage(Command):
        """
        Search the room for a concealed passage.

        Examples:
            find passage
        """

    key = "find passage"
    aliases = ["findpassage"]
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room or not hasattr(room, "has_passage") or not room.has_passage():
            caller.msg("You find nothing unusual.")
            return

        success_chance = 50
        if getattr(caller.db, "profession", None) == "thief":
            success_chance += 25

        if random.randint(1, 100) <= success_chance:
            known = list(getattr(caller.db, "known_passages", None) or [])
            if room.id not in known:
                known.append(room.id)
                caller.db.known_passages = known
            caller.msg("You notice subtle signs of a hidden passage.")
            return

        caller.msg("You fail to find anything.")