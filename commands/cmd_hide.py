from commands.command import Command
import time

from engine.services.skill_service import SkillService
from world.systems.stealth import detect, enter_stealth


class CmdHide(Command):
    """
    Attempt to hide from view.

    Examples:
        hide
    """

    key = "hide"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller

        if bool(getattr(caller.db, "stealthed", False)) or caller.is_hidden():
            caller.msg("You are already hidden.")
            return

        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        now = time.time()
        caller.db.last_hide_time = now
        score = enter_stealth(caller)
        if not score:
            caller.apply_thief_roundtime(2)
            caller.msg("You fail to find a place to conceal yourself.")
            return

        caller.apply_thief_roundtime(2)
        SkillService.award_xp(caller, "stealth", 1, source={"mode": "difficulty"}, success=True, outcome="success", event_key="stealth")
        caller.msg("You blend into the surroundings.")

        room = caller.location
        if not room:
            return

        for obj in list(room.contents):
            if obj == caller or not hasattr(obj, "msg"):
                continue

            if detect(obj, caller, award_xp=True):
                obj.msg(f"You notice {caller.key} trying to hide.")
            else:
                obj.msg("Something shifts nearby, but you can't pinpoint it.")
