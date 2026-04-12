from commands.command import Command
from world.systems.justice import get_wanted_tier, is_detained, process_surrender


class CmdSurrender(Command):
    """
    Submit to local justice pressure.

    Examples:
        surrender
    """

    key = "surrender"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        if is_detained(caller):
            caller.msg("You are already in custody.")
            return
        if (
            not bool(getattr(caller.db, "guard_attention", False))
            and not bool(getattr(caller.db, "pending_arrest", False))
            and int(getattr(caller.db, "active_guard_id", 0) or 0) <= 0
            and get_wanted_tier(caller) != "arrest_eligible"
        ):
            caller.msg("No authority is pressing you hard enough to demand surrender right now.")
            return
        result = process_surrender(caller)
        if not result.get("ok"):
            caller.msg(str(result.get("reason") or "You cannot surrender right now."))
            return
        penalty = dict(result.get("penalty") or {})
        guard_name = str(result.get("guard_name") or "the authorities")
        caller.msg(
            f"{guard_name} accepts your surrender. Fine assessed: {int(penalty.get('fine', 0) or 0)} coins. "
            f"Detention: {int(penalty.get('detain_seconds', 0) or 0)} seconds."
        )
