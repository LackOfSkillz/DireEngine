from commands.command import Command
from engine.services.spell_access_service import SpellAccessService


class CmdSpellbook(Command):
    """
    Inspect the current learned spell state.

    Examples:
        spellbook
    """

    key = "spellbook"
    locks = "cmd:perm(Developer) or perm(Admin)"
    help_category = "Magic"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()

        known_spells = SpellAccessService.list_known_spells(caller)
        spellbook = getattr(getattr(caller, "db", None), "spellbook", {}) or {}
        known_map = spellbook.get("known_spells", {}) or {}

        if not known_spells:
            caller.msg("You do not know any tracked spells.")
            return

        lines = ["Known spells:"]
        for spell in known_spells:
            entry = dict(known_map.get(spell.id, {}) or {})
            learned_via = str(entry.get("learned_via", "unknown") or "unknown")
            circle_learned = entry.get("circle_learned", "?")
            lines.append(f"{spell.name} ({spell.id}) - via {learned_via}, circle {circle_learned}")
        caller.msg("\n".join(lines))