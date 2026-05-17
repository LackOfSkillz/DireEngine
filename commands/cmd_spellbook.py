from commands.command import Command
from engine.services.spell_access_service import SpellAccessService


def _format_spell_type(spell):
    return str(getattr(spell, "spell_type", "") or "utility").replace("_", " ").title()


def _format_spell_name(spell):
    name = str(getattr(spell, "name", "") or getattr(spell, "id", "") or "Unknown Spell")
    if str(getattr(spell, "provenance", "") or "").strip().lower() == "hybrid_design":
        return f"{name} [Hybrid]"
    return name


def _group_spells_by_spellbook(spells):
    grouped = {}
    for spell in spells:
        spellbook = str(getattr(spell, "spellbook", "") or "Miscellaneous").strip() or "Miscellaneous"
        grouped.setdefault(spellbook, []).append(spell)
    return {key: grouped[key] for key in sorted(grouped)}


def _append_grouped_spell_lines(lines, spells, formatter):
    for spellbook, grouped_spells in _group_spells_by_spellbook(spells).items():
        lines.append(f"{spellbook}:")
        for spell in grouped_spells:
            lines.append(formatter(spell))


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


class CmdSpells(Command):
    """Show your permanently memorized and apprentice-access spells."""

    key = "spells"
    aliases = ["spell"]
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()

        known_spells = SpellAccessService.list_known_spells(caller)
        apprentice_spells = SpellAccessService.get_apprentice_spells(caller)

        if not known_spells and not apprentice_spells:
            caller.msg("You do not currently have any accessible spells.")
            return

        lines = ["Your Spells:"]
        if known_spells:
            lines.append("Permanently Memorized:")
            _append_grouped_spell_lines(
                lines,
                known_spells,
                lambda spell: (
                    f"  {_format_spell_name(spell)} ({_format_spell_type(spell)}) "
                    f"[{int(getattr(spell, 'slot_cost', 0) or 0)} {'slot' if int(getattr(spell, 'slot_cost', 0) or 0) == 1 else 'slots'}]"
                ),
            )

        if apprentice_spells:
            if known_spells:
                lines.append("")
            expire_circle = max(int(spell.apprentice_until_circle or 0) + 1 for spell in apprentice_spells)
            lines.append(f"Apprentice Access (expires at circle {expire_circle}):")
            _append_grouped_spell_lines(
                lines,
                apprentice_spells,
                lambda spell: f"  {_format_spell_name(spell)} ({_format_spell_type(spell)})",
            )

        caller.msg("\n".join(lines))