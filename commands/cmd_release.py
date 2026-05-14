from commands.command import Command


class CmdRelease(Command):
    """
    Release a prepared spell, held mana, cyclic spell, or empathic link.

    Examples:
        release
        release spell
        release mana
        release cyclic
        release link
    """

    key = "release"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        self.caller.release_magic(self.args)
