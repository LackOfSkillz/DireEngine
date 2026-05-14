from commands.command import Command
from domain.spells.spell_definitions import get_spell
from engine.services.slot_service import SlotService


class CmdSlots(Command):
    """
        Show your magic slot pool.

        Examples:
            slots
            spellslots
    """

    key = "slots"
    aliases = ["spellslots"]
    help_category = "Magic"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()

        pool = SlotService.get_pool(caller)
        if pool is None:
            caller.msg("You are not a magic-using profession; you have no slot pool.")
            return

        used = SlotService.get_used_slots(caller)
        available = SlotService.get_available_slots(caller)
        lines = [
            "Magic Slot Pool:",
            f"Total: {int(pool.get('max', 0) or 0)} | Used: {used} | Available: {available}",
        ]

        allocations = dict(pool.get("allocations", {}) or {})
        for category in sorted(allocations):
            entries = dict(allocations.get(category, {}) or {})
            if not entries:
                continue
            lines.append("")
            lines.append(f"{category.title()}:")
            for item_id, cost in sorted(entries.items()):
                spell = get_spell(item_id) if category == "spells" else None
                label = spell.name if spell is not None else str(item_id).replace("_", " ").title()
                suffix = "slot" if int(cost or 0) == 1 else "slots"
                lines.append(f"  {label}: {int(cost or 0)} {suffix}")

        if all(not entries for entries in allocations.values()):
            lines.append("")
            lines.append("No slots are currently allocated.")

        caller.msg("\n".join(lines))