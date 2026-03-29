import time

from commands.command import Command

from utils.crime import JUDGE_ROOM_KEY, _resolve_room


class CmdCapture(Command):
    key = "capture"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        target_name = str(self.args or "").strip()
        if not target_name:
            caller.msg("Capture whom?")
            return
        if getattr(caller.db, "active_bounty", None) is None:
            caller.msg("You are not pursuing a bounty.")
            return

        target = caller.search(target_name, location=caller.location)
        if not target:
            return
        if getattr(target, "id", None) != getattr(caller.db, "active_bounty", None):
            caller.msg("That is not your contracted target.")
            return
        if not hasattr(target, "is_criminal") or not target.is_criminal():
            caller.msg("They are not wanted.")
            return
        if not getattr(target.db, "is_captured", False):
            caller.msg("They must already be subdued.")
            return

        region = caller.location.get_region() if getattr(caller, "location", None) and hasattr(caller.location, "get_region") else "default_region"
        if not (getattr(target.db, "warrants", None) or {}).get(region):
            caller.msg("There is no active bounty for them in this region.")
            return

        judge_room = _resolve_room(JUDGE_ROOM_KEY)
        if judge_room:
            target.move_to(judge_room, quiet=True, move_type="bounty_capture")
        target.db.awaiting_plea = True
        target.db.plea = None
        target.ndb.plea_deadline = time.time() + 30

        data = dict((getattr(target.db, "warrants", None) or {}).get(region) or {})
        reward = int(data.get("bounty", 0) or 0)
        caller.db.coins = int(getattr(caller.db, "coins", 0) or 0) + reward
        warrants = dict(getattr(target.db, "warrants", None) or {})
        warrants.pop(region, None)
        target.db.warrants = warrants
        if not warrants and not getattr(target.db, "fine_due", 0):
            target.db.crime_flag = False
        caller.db.active_bounty = None
        caller.msg(f"You receive {reward} coins for the capture.")