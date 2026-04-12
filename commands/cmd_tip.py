import time

from commands.command import Command


class CmdTip(Command):
    """
    Offer a tip to the house healer in the room.

    Examples:
        tip 5
        tip 25
    """

    key = "tip"
    locks = "cmd:all()"
    help_category = "Character"

    def _find_healer(self, caller):
        room = getattr(caller, "location", None)
        if not room:
            return None
        for obj in getattr(room, "contents", []):
            if hasattr(obj, "get_tip_response") and bool(getattr(getattr(obj, "db", None), "is_house_healer", False)):
                return obj
        return None

    def func(self):
        caller = self.caller
        raw = str(self.args or "").strip()
        if not raw:
            caller.msg("Usage: tip <amount>")
            return
        try:
            amount = max(1, int(raw))
        except ValueError:
            caller.msg("Usage: tip <amount>")
            return
        healer = self._find_healer(caller)
        if not healer:
            caller.msg("There is no one here to tip.")
            return
        if hasattr(caller, "has_coins") and not caller.has_coins(amount):
            caller.msg("You do not have enough coins.")
            return
        if hasattr(caller, "remove_coins"):
            caller.remove_coins(amount)
        caller.db.total_tips = int(getattr(caller.db, "total_tips", 0) or 0) + amount
        caller.db.last_tip_amount = amount
        caller.db.last_tip_time = time.time()
        if hasattr(caller, "record_tip_history"):
            caller.record_tip_history(healer, amount)
        caller.msg(f"You offer {amount} coins to {healer.key}.")
        caller.msg(healer.get_tip_response(amount))
