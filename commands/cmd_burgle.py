from commands.command import Command
from world.systems.burglary import attempt_entry, can_burgle


class CmdBurgle(Command):
    """
    Attempt a burglary entry against a protected target.

    Examples:
        burgle window
        burgle chest
    """

    key = "burgle"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Burgle what?")
            return
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        room = getattr(caller, "location", None)
        if not room:
            caller.msg("You are in no position to do that.")
            return

        target = caller.search(self.args.strip(), location=room)
        if not target:
            return

        validation = can_burgle(caller, target)
        if not validation.get("allowed"):
            caller.msg(str(validation.get("reason") or "You cannot work that target."))
            return

        starting_room = room
        result = attempt_entry(caller, target)
        if result.get("success"):
            if str(result.get("entry_result") or "") == "container_open":
                caller.msg(f"You quietly work {target.key} open.")
            else:
                caller.msg(f"You work your way through {target.key} and slip inside.")
            if starting_room and starting_room != getattr(caller, "location", None):
                starting_room.msg_contents(f"{caller.key} slips through {target.key}.", exclude=[caller])
            return

        entry_result = str(result.get("entry_result") or "blocked")
        if entry_result == "trap_triggered":
            caller.msg(f"A trap on {target.key} goes off in your hands!")
            if starting_room:
                starting_room.msg_contents(
                    f"A sharp alarm bursts from {target.key} as {caller.key} fumbles the intrusion.",
                    exclude=[caller],
                )
            return
        if entry_result in {"trap_alerted", "lock_alerted", "noisy_failure"}:
            caller.msg(f"You make too much noise working {target.key}, and the intrusion collapses.")
            if starting_room:
                starting_room.msg_contents(f"{caller.key} makes a suspicious mess of {target.key}.", exclude=[caller])
            return
        if str(result.get("lock_result") or "") == "no_progress":
            caller.msg(f"{target.key} resists you before you can gain entry.")
            return
        caller.msg(str(result.get("entry_result") or "You fail to make a way in."))