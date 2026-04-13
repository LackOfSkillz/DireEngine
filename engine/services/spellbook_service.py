from collections.abc import Mapping

from domain.spells.spell_definitions import get_spell
from engine.services.result import ActionResult


class SpellbookService:
    @staticmethod
    def _normalize_identifier(value):
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _normalize_profession(value):
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _get_profession(character):
        if character is None:
            return ""
        if hasattr(character, "get_profession"):
            return SpellbookService._normalize_profession(character.get_profession())
        return SpellbookService._normalize_profession(getattr(character, "profession", ""))

    @staticmethod
    def ensure_spellbook_defaults(character):
        if character is None:
            return {"known_spells": {}}

        db = getattr(character, "db", None)
        if db is None:
            return {"known_spells": {}}

        raw = getattr(db, "spellbook", None)
        if not isinstance(raw, Mapping):
            raw = {}

        normalized = dict(raw)
        known_spells = normalized.get("known_spells")
        if not isinstance(known_spells, Mapping):
            normalized["known_spells"] = {}
        else:
            normalized["known_spells"] = dict(known_spells)

        db.spellbook = normalized
        return normalized

    @staticmethod
    def has_spell(character, spell_id):
        normalized = SpellbookService._normalize_identifier(spell_id)
        spellbook = SpellbookService.ensure_spellbook_defaults(character)
        return normalized in spellbook["known_spells"]

    @staticmethod
    def learn_spell(character, spell_id, method):
        normalized = SpellbookService._normalize_identifier(spell_id)
        normalized_method = SpellbookService._normalize_identifier(method)
        spell = get_spell(normalized)
        if spell is None:
            return ActionResult.fail(errors=["That spell definition does not exist."], messages=["That spell definition does not exist."])

        allowed_professions = {SpellbookService._normalize_profession(entry) for entry in (spell.allowed_professions or [])}
        if allowed_professions and SpellbookService._get_profession(character) not in allowed_professions:
            return ActionResult.fail(errors=["You cannot learn that spell."], messages=["You cannot learn that spell."])

        if normalized_method not in set(spell.acquisition_methods or []):
            return ActionResult.fail(errors=["You cannot learn that spell that way."], messages=["You cannot learn that spell that way."])

        spellbook = SpellbookService.ensure_spellbook_defaults(character)
        known_spells = dict(spellbook["known_spells"])
        if normalized in known_spells:
            return ActionResult.fail(errors=["You already know that spell."], messages=["You already know that spell."])

        circle = int(getattr(getattr(character, "db", None), "circle", getattr(character, "circle", 1)) or 1)
        known_spells[normalized] = {
            "learned_via": normalized_method,
            "circle_learned": circle,
        }
        spellbook["known_spells"] = known_spells
        getattr(character, "db").spellbook = spellbook
        return ActionResult.ok(
            data={
                "spell_id": normalized,
                "learned_via": normalized_method,
                "circle_learned": circle,
            }
        )