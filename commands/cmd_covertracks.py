from commands.command import Command


class CmdCoverTracks(Command):
    """
    Mask your trail as you move through the area.

    Examples:
        covertracks
        cover tracks
    """

    key = "covertracks"
    aliases = ["cover tracks"]
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        ok, message = caller.begin_covering_tracks() if hasattr(caller, "begin_covering_tracks") else (False, "You cannot cover your tracks.")
        caller.msg(message)
