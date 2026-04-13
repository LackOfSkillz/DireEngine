from collections.abc import Mapping

from domain.spells.spell_definitions import SPELL_REGISTRY, Spell
from engine.services.result import ActionResult
from engine.services.spellbook_service import SpellbookService


class SpellAccessService:
    @staticmethod
    def _fail(message, data=None):
        return ActionResult.fail(errors=[str(message)], messages=[str(message)], data=data)

    @staticmethod
    def _normalize_profession(value):
        return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _normalize_spell_id(value):
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _get_profession(character):
        if character is None:
            return ""
        if hasattr(character, "get_profession"):
            return SpellAccessService._normalize_profession(character.get_profession())
        return SpellAccessService._normalize_profession(getattr(character, "profession", ""))

    @staticmethod
    def _get_circle(character):
        if character is None:
            return 0
        db = getattr(character, "db", None)
        if db is None:
            return max(0, int(getattr(character, "circle", 0) or 0))
        return max(0, int(getattr(db, "circle", getattr(character, "circle", 0)) or 0))

    @staticmethod
    def _get_skill(character, skill_name):
        if character is None:
            return 0
        getter = getattr(character, "get_skill", None)
        if callable(getter):
            return max(0, int(getter(skill_name) or 0))
        return 0

    @staticmethod
    def _normalize_spellbook(character):
        return SpellbookService.ensure_spellbook_defaults(character)

    @staticmethod
    def has_spell(character, spell_id):
        return SpellbookService.has_spell(character, spell_id)

    @staticmethod
    def can_use_spell(character, spell):
        if character is None:
            return SpellAccessService._fail("Missing character.")
        if spell is None:
            return SpellAccessService._fail("You do not know how to prepare that spell.")

        profession = SpellAccessService._get_profession(character)
        allowed_professions = {
            SpellAccessService._normalize_profession(entry) for entry in (spell.allowed_professions or [])
        }
        if allowed_professions and profession not in allowed_professions:
            return SpellAccessService._fail(
                "You cannot comprehend that spell.",
                data={"spell_id": spell.id, "profession": profession},
            )

        if not SpellAccessService.has_spell(character, spell.id):
            return SpellAccessService._fail(
                "You have not learned that spell.",
                data={"spell_id": spell.id},
            )

        circle = SpellAccessService._get_circle(character)
        if circle < int(spell.min_circle or 0):
            return SpellAccessService._fail(
                "You are not experienced enough.",
                data={"spell_id": spell.id, "required_circle": int(spell.min_circle or 0), "circle": circle},
            )

        for skill_name, requirement in dict(spell.min_skill or {}).items():
            if SpellAccessService._get_skill(character, skill_name) < int(requirement or 0):
                return SpellAccessService._fail(
                    "You lack the skill.",
                    data={"spell_id": spell.id, "skill": skill_name, "required": int(requirement or 0)},
                )

        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "circle": circle,
            }
        )

    @staticmethod
    def list_known_spells(character):
        spellbook = SpellAccessService._normalize_spellbook(character)
        known = []
        for spell_id in spellbook["known_spells"]:
            spell = SPELL_REGISTRY.get(spell_id)
            if spell is not None:
                known.append(spell)
        return sorted(known, key=lambda spell: (int(spell.min_circle or 0), spell.name.lower(), spell.id))

    @staticmethod
    def list_available_spells(character, include_locked=False):
        available = []
        for spell in SpellAccessService.list_known_spells(character):
            result = SpellAccessService.can_use_spell(character, spell)
            if result.success or include_locked:
                available.append(spell)
        return available