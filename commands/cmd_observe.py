import time

from commands.command import Command
from world.systems import awareness, stealth, theft


class CmdObserve(Command):
    """
    Carefully watch the room for details or movement.

    Examples:
        observe guard
    """

    key = "observe"
    locks = "cmd:all()"
    help_category = "Perception"

    def _get_detection_bonus(self, caller, target, room):
        base = 0
        if hasattr(caller, "get_skill_rank"):
            try:
                base = int(caller.get_skill_rank("perception") or 0)
            except Exception:
                base = 0
        total = awareness.get_awareness_total(caller, actor=target, context={"room": room, "observe_target": target})
        return max(0, int(total - base))

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        args = (self.args or "").strip()
        if not args:
            caller.msg("Observe whom?")
            return
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return
        if not room:
            caller.msg("There is no one here to observe.")
            return

        target = caller.search(args, location=room)
        if not target:
            return

        count = awareness.record_observe_attempt(caller, target, now=time.time())
        awareness_state = dict(getattr(caller.db, "awareness_state", None) or {})
        awareness_state["observe_target"] = getattr(target, "id", None)
        awareness_state["observe_target_name"] = getattr(target, "key", None)
        caller.db.awareness_state = awareness_state

        if hasattr(target, "is_hidden") and target.is_hidden():
            result = stealth.resolve_detection(
                caller,
                target,
                award_xp=True,
                active=True,
                context={"perception_bonus": self._get_detection_bonus(caller, target, room)},
            )
            if result.get("success") and result.get("margin", 0) >= 20:
                target.reveal()
                caller.msg(f"You focus on {target.key} long enough to expose them.")
            elif result.get("hint") == "hint":
                caller.msg(f"You notice enough about {target.key} to narrow down their hiding place.")
            else:
                caller.msg(f"You study {target.key}, but they give away little.")
        else:
            caller.msg(f"You study {target.key}'s habits and posture for any telltale weakness.")

        if count >= 2:
            theft.increase_room_suspicion(room, amount=1)
            target.msg(f"You notice {caller.key} watching you a little too closely.")
        caller.apply_thief_roundtime(1.5)
