from commands.command import Command


class CmdSlots(Command):
    """
        Show which worn slots are filled.

        Examples:
            slots
            slt
    """

    key = "slots"
    aliases = ["slt"]
    help_category = "Equipment"

    def func(self):
        equipment = self.caller.get_equipment()
        lines = ["Worn Slots:"]
        for slot, stack in equipment.items():
            display = ", ".join(obj.key for obj in stack) if stack else "empty"
            lines.append(f"  {slot}: {display}")
        self.caller.msg("\n".join(lines))