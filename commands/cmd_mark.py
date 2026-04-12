import random
import time

from commands.command import Command
from engine.services.skill_service import SkillService
from world.systems.theft import record_mark_attempt


class CmdMark(Command):
    """
    Mark a target for thief abilities and ambush setup.

    Examples:
        mark goblin
    """

    key = "mark"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Mark whom?")
            return

        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return

        if hasattr(caller, "is_profession") and caller.is_profession("ranger"):
            ok, message = caller.apply_ranger_mark(target) if hasattr(caller, "apply_ranger_mark") else (False, "You cannot mark that target.")
            caller.msg(message)
            return

        if target == caller:
            caller.msg("You already know your own weaknesses.")
            return

        if target.location != caller.location:
            caller.msg("They are not here.")
            return

        difficulty = random.randint(1, 100)
        memory = dict(getattr(target.db, "theft_memory", None) or {}).get(caller.id)
        attention = str(getattr(target.db, "attention_state", "idle") or "idle")

        caller.db.marked_target = target.id
        caller.db.last_mark_target = target.id
        caller.db.last_mark_time = time.time()
        caller.db.mark_data = {
            "difficulty": difficulty,
            "timestamp": caller.db.last_mark_time,
        }
        record_mark_attempt(caller, target)

        perception_difficulty = 10
        if hasattr(target, "get_skill_rank"):
            try:
                perception_difficulty = max(10, int(target.get_skill_rank("perception") or 0))
            except Exception:
                perception_difficulty = 10
        SkillService.award_xp(caller, "appraisal", perception_difficulty, source={"mode": "difficulty"}, success=True, outcome="success", event_key="mark")
        SkillService.award_xp(caller, "perception", max(10, perception_difficulty - 5), source={"mode": "difficulty"}, success=True, outcome="success", event_key="mark")

        caller.msg(f"You assess {target.key}. Difficulty: {difficulty}")
        caller.msg("They seem wary of you." if memory else "They seem unsuspecting.")
        caller.msg(f"Attention: {attention}")
        caller.msg(f"Risk level: {max(1, difficulty // 20)}")
