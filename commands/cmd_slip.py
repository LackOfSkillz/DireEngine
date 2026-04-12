import time

from commands.command import Command


class CmdSlip(Command):
    """
    Slip out of sight or out of a dangerous position.

    Examples:
        slip
    """

    key = "slip"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        if getattr(caller.db, "is_captured", False) or getattr(caller.db, "in_stocks", False):
            caller.msg("You cannot slip while restrained.")
            return

        now = time.time()
        last_slip = float(getattr(caller.db, "last_slip_time", 0) or 0)
        if now - last_slip < 10:
            caller.msg("You need a moment before slipping again.")
            return

        caller.db.slipping = True
        caller.db.last_slip_time = now
        caller.db.pursuers = []
        caller.db.is_pursued = False
        caller.db.slip_bonus = 20
        caller.db.slip_timer = now
        caller.db.escape_chain = 0
        caller.db.recent_action = True
        caller.db.recent_action_timer = now
        if hasattr(caller, "set_position_state"):
            caller.set_position_state("advantaged")

        caller.msg("You slip through the chaos, avoiding notice.")
        caller.execute_ability_input("hide")
        if not caller.is_hidden():
            caller.msg("You fail to fully disappear.")

        rt = 2
        if getattr(caller.db, "position_state", "neutral") == "advantaged":
            rt -= 1
        caller.apply_thief_roundtime(max(1, min(rt, 5)))
