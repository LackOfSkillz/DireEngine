from collections.abc import Mapping

from domain.spells.spell_definitions import get_spell
from engine.services.result import ActionResult
from engine.services.slot_service import SlotService


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
    def _get_circle(character):
        if character is None:
            return 0
        if hasattr(character, "get_circle"):
            return max(0, int(character.get_circle() or 0))
        db = getattr(character, "db", None)
        return max(0, int(getattr(db, "circle", getattr(character, "circle", 0)) or 0))

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

        slot_cost = max(0, int(getattr(spell, "slot_cost", 0) or 0))
        if slot_cost > 0 and not SlotService.has_available_slots(character, slot_cost):
            available = SlotService.get_available_slots(character)
            return ActionResult.fail(
                errors=[
                    f"You cannot memorize {spell.name}. It requires {slot_cost} slot(s), but you only have {available} available."
                ],
                messages=[
                    f"You cannot memorize {spell.name}. It requires {slot_cost} slot(s), but you only have {available} available. Use SLOTS to review your allocations."
                ],
                data={
                    "spell_id": normalized,
                    "reason": "insufficient_slots",
                    "needed": slot_cost,
                    "available": available,
                },
            )

        circle = SpellbookService._get_circle(character)
        if slot_cost > 0 and not SlotService.allocate(character, "spells", normalized, slot_cost):
            available = SlotService.get_available_slots(character)
            return ActionResult.fail(
                errors=["You cannot commit that many slots right now."],
                messages=["You cannot commit that many slots right now."],
                data={
                    "spell_id": normalized,
                    "reason": "slot_allocation_failed",
                    "needed": slot_cost,
                    "available": available,
                },
            )

        known_spells[normalized] = {
            "learned_via": normalized_method,
            "circle_learned": circle,
            "slot_cost": slot_cost,
        }
        spellbook["known_spells"] = known_spells
        getattr(character, "db").spellbook = spellbook
        return ActionResult.ok(
            data={
                "spell_id": normalized,
                "learned_via": normalized_method,
                "circle_learned": circle,
                "slot_cost": slot_cost,
                "slots_consumed": slot_cost,
                "slots_available": SlotService.get_available_slots(character),
            }
        )