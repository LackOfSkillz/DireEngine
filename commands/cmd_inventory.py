from evennia import Command


class CmdInventory(Command):
    """
        See what you are carrying in your hands and pack.

        Examples:
            inventory
            inv
            i
    """

    key = "inventory"
    aliases = ["inv", "i"]
    help_category = "Equipment"

    def func(self):
        coin_text = self.caller.format_coins(int(getattr(self.caller.db, "coins", 0) or 0)) if hasattr(self.caller, "format_coins") else f"{int(getattr(self.caller.db, 'coins', 0) or 0)} coins"
        weight_text = None
        encumbrance_text = None
        race_text = None
        if hasattr(self.caller, "get_total_weight") and hasattr(self.caller, "get_max_carry_weight") and hasattr(self.caller, "get_encumbrance_state"):
            weight_text = f"Weight: {self.caller.get_total_weight():.1f} / {self.caller.get_max_carry_weight():.1f}"
            encumbrance_text = f"Encumbrance: {self.caller.get_encumbrance_state()}"
            if hasattr(self.caller, "get_encumbrance_race_message"):
                race_text = self.caller.get_encumbrance_race_message()
        carried = [
            item for item in self.caller.contents
            if getattr(item.db, "worn_by", None) != self.caller
        ]
        if not carried:
            lines = ["You are carrying nothing.", f"Coins: {coin_text}"]
            if weight_text:
                lines.append(weight_text)
            if encumbrance_text:
                lines.append(encumbrance_text)
            if race_text:
                lines.append(race_text)
            self.caller.msg("\n".join(lines))
            return

        lines = ["You are carrying:", f"Coins: {coin_text}"]
        if weight_text:
            lines.append(weight_text)
        if encumbrance_text:
            lines.append(encumbrance_text)
        if race_text:
            lines.append(race_text)
        for item in carried:
            lines.append(f" {item.key}")
        self.caller.msg("\n".join(lines))