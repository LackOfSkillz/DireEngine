import random

from commands.command import Command


class CmdBribe(Command):
    key = "bribe"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        amount_text = str(self.args or "").strip()
        if not amount_text:
            caller.msg("Bribe how much?")
            return
        try:
            amount = max(1, int(amount_text))
        except ValueError:
            caller.msg("You must offer a whole number of coins.")
            return

        room = caller.location
        guard = next((obj for obj in getattr(room, "contents", []) if hasattr(obj, "is_guard") and obj.is_guard()), None)
        if not guard:
            caller.msg("There is no guard here to bribe.")
            return

        if int(getattr(caller.db, "coins", 0) or 0) < amount:
            caller.msg("You don't have that much coin.")
            return

        region = room.get_region() if room and hasattr(room, "get_region") else "default_region"
        warrants = dict(getattr(caller.db, "warrants", None) or {})
        data = dict(warrants.get(region, {}))
        if not data:
            caller.msg("The guard refuses your coin without cause.")
            return

        threshold = 50 - (amount // 10)
        if getattr(guard.db, "bribe_attempted", False):
            threshold += 20
        roll = random.randint(1, 100)
        success = roll > threshold
        caller.db.coins = int(getattr(caller.db, "coins", 0) or 0) - amount
        guard.db.bribe_attempted = True

        if success:
            data["severity"] = max(0, int(data.get("severity", 0) or 0) - 2)
            if data["severity"] <= 0:
                warrants.pop(region, None)
            else:
                warrants[region] = data
            caller.db.warrants = warrants
            caller.msg("The guard pockets your coin and looks the other way.")
            return

        data["severity"] = int(data.get("severity", 0) or 0) + 1
        warrants[region] = data
        caller.db.warrants = warrants
        caller.msg("The guard sneers: 'Trying to bribe an officer?'")