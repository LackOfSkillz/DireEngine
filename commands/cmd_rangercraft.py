from commands.command import Command


class CmdGather(Command):
    """
    Gather a visible Ranger resource from the room.

    Examples:
        gather grass
        gather stick
    """

    key = "gather"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        material = str(self.args or "").strip().lower()
        if not material:
            self.caller.msg("Gather what?")
            return
        if not hasattr(self.caller, "gather_ranger_resource"):
            self.caller.msg("You cannot gather that right now.")
            return
        self.caller.gather_ranger_resource(material)


class CmdBundle(Command):
    """
    Work gathered sticks into a sellable bundle.

    Examples:
        bundle sticks
    """

    key = "bundle"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        material = str(self.args or "").strip().lower()
        if not material:
            self.caller.msg("Bundle what?")
            return
        if not hasattr(self.caller, "transform_ranger_resource"):
            self.caller.msg("You cannot bundle that right now.")
            return
        self.caller.transform_ranger_resource("bundle", material)


class CmdBraid(Command):
    """
    Braid gathered grass into a sellable weave.

    Examples:
        braid grass
    """

    key = "braid"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        material = str(self.args or "").strip().lower()
        if not material:
            self.caller.msg("Braid what?")
            return
        if not hasattr(self.caller, "transform_ranger_resource"):
            self.caller.msg("You cannot braid that right now.")
            return
        self.caller.transform_ranger_resource("braid", material)