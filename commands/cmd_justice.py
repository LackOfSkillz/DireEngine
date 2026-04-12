from commands.command import Command
from world.systems.justice import decay_wanted, get_justice_status


class CmdJustice(Command):
    """
    Review your justice standing and local legal state.

    Examples:
        justice
    """

    key = "justice"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        decay_wanted(caller)
        status = get_justice_status(caller)
        caller.msg(f"Justice in this area: {status.get('law', 'standard')}")
        caller.msg(f"Wanted tier: {status.get('wanted_tier', 'clear')} ({int(status.get('wanted_level', 0) or 0)})")
        caller.msg(f"Warning level: {int(status.get('warning_level', 0) or 0)}")
        active_guard_name = status.get("active_guard_name")
        if active_guard_name:
            caller.msg(f"Active guard: {active_guard_name}")
        if bool(status.get("pending_arrest")):
            caller.msg("Pending arrest: yes")
        else:
            caller.msg("Pending arrest: no")
        if bool(status.get("guard_attention")):
            caller.msg("The authorities are actively trying to detain you.")
        if bool(status.get("detained")):
            caller.msg(f"Detained until: {float(status.get('detained_until', 0) or 0):.2f}")
        custody = str(status.get("custody", "free") or "free")
        if custody != "free":
            caller.msg(f"Custody: {custody}")
        fine_due = int(status.get("outstanding_fine", 0) or 0)
        if fine_due > 0:
            caller.msg(f"Outstanding fine: {fine_due}")
        debt = int(status.get("justice_debt", 0) or 0)
        caller.msg(f"Debt: {debt} silver")
        confiscated = int(status.get("confiscated_items", 0) or 0)
        caller.msg(f"Confiscated items: {'Yes' if confiscated > 0 else 'No'}")
        crime_count = int(status.get("crime_count", 0) or 0)
        caller.msg(f"Crime Count: {crime_count}")
        caller.msg(f"Law Reputation: {int(status.get('law_reputation', 0) or 0)}")
        if confiscated > 0:
            caller.msg("You recall your belongings are held at the guardhouse.")

        warrants = status.get("warrants") or {}
        if not warrants:
            caller.msg("You have no active warrants.")
            return

        for region, data in warrants.items():
            severity = int((data or {}).get("severity", 0) or 0)
            caller.msg(f"{region}: severity {severity}")
