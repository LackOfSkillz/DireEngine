import time

from evennia.utils.search import search_object

from commands.command import Command


class CmdRequestHealing(Command):
    """
    Request treatment from a house healer.

    Examples:
        request healing
        request healing confirm
    """

    key = "request healing"
    locks = "cmd:all()"
    help_category = "Character"

    def _find_healer(self, caller):
        room = getattr(caller, "location", None)
        if not room:
            return None
        for obj in getattr(room, "contents", []):
            if hasattr(obj, "quote_healing_cost") and bool(getattr(getattr(obj, "db", None), "is_house_healer", False)):
                return obj
        return None

    def _clear_pending(self, caller):
        caller.db.pending_healing_request = None

    def func(self):
        caller = self.caller
        raw = str(self.args or "").strip().lower()
        if raw == "confirm":
            pending = dict(getattr(caller.db, "pending_healing_request", None) or {})
            if not pending:
                caller.msg("You have no pending healing request.")
                return
            if time.time() > float(pending.get("expires_at", 0.0) or 0.0):
                self._clear_pending(caller)
                caller.msg("Your healing request has expired.")
                return
            healer_id = int(pending.get("healer_id", 0) or 0)
            matches = search_object(f"#{healer_id}") if healer_id > 0 else []
            healer = matches[0] if matches else None
            if not healer or getattr(healer, "location", None) != getattr(caller, "location", None):
                self._clear_pending(caller)
                caller.msg("The healer is no longer here.")
                return
            cost = int(pending.get("cost", 0) or 0)
            if hasattr(caller, "has_coins") and not caller.has_coins(cost):
                self._clear_pending(caller)
                caller.msg("You do not have enough coins.")
                return
            if hasattr(caller, "remove_coins"):
                caller.remove_coins(cost)
            ok, message = healer.perform_healing(caller)
            self._clear_pending(caller)
            caller.msg(message)
            return

        healer = self._find_healer(caller)
        if not healer:
            caller.msg("There is no house healer here.")
            return
        ok, cost, message = healer.quote_healing_cost(caller)
        caller.msg(message)
        if ok:
            caller.db.pending_healing_request = {
                "healer_id": int(getattr(healer, "id", 0) or 0),
                "cost": int(cost or 0),
                "expires_at": time.time() + 30.0,
            }
