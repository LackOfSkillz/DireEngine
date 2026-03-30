import random
import time

from evennia import Command


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
        caller.db.mark_data = {
            "difficulty": difficulty,
            "timestamp": time.time(),
        }

        caller.msg(f"You assess {target.key}. Difficulty: {difficulty}")
        caller.msg("They seem wary of you." if memory else "They seem unsuspecting.")
        caller.msg(f"Attention: {attention}")
        caller.msg(f"Risk level: {max(1, difficulty // 20)}")
