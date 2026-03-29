from evennia import Command


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
        for slot, item in equipment.items():
            if self.caller.is_multi_slot(slot):
                display = ", ".join(obj.key for obj in item) if item else "empty"
            else:
                display = item.key if item else "empty"
            lines.append(f"  {slot}: {display}")
        self.caller.msg("\n".join(lines))