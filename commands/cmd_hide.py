from commands.command import Command
import time

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
            if hasattr(caller, "record_stealth_contest"):
                caller.record_stealth_contest(
                    "hide",
                    10,
                    result={"outcome": "fail", "diff": -20, "observer_count": 0},
                    target=caller.location,
                    roundtime=2.0,
                    event_key="stealth",
                    require_hidden=False,
                )
            return

        caller.apply_thief_roundtime(2)
        caller.msg("You blend into the surroundings.")

        room = caller.location
        if not room:
            if hasattr(caller, "record_stealth_contest"):
                caller.record_stealth_contest(
                    "hide",
                    10,
                    result=None,
                    target=None,
                    roundtime=2.0,
                    event_key="stealth",
                    require_hidden=True,
                )
            return

        highest_difficulty = 10
        observer_count = 0
        spotted = False
        for obj in list(room.contents):
            if obj == caller or not hasattr(obj, "msg"):
                continue
            if not hasattr(obj, "_sync_exp_skill_state"):
                continue

            observer_count += 1
            if hasattr(obj, "get_perception_total"):
                try:
                    highest_difficulty = max(highest_difficulty, int(obj.get_perception_total() or 0))
                except Exception:
                    pass

            if detect(obj, caller, award_xp=True):
                spotted = True
                obj.msg(f"You notice {caller.key} trying to hide.")
            else:
                obj.msg("Something shifts nearby, but you can't pinpoint it.")

        if hasattr(caller, "record_stealth_contest"):
            caller.record_stealth_contest(
                "hide",
                highest_difficulty,
                result={
                    "outcome": "fail" if spotted else "success",
                    "diff": -1 if spotted else 1,
                    "observer_count": observer_count,
                },
                target=caller.location,
                roundtime=2.0,
                event_key="stealth",
                require_hidden=True,
            )
