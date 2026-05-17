import unittest

from domain.spells.spell_definitions import get_spell
from engine.services.spell_access_service import SpellAccessService
from engine.services.spellbook_service import SpellbookService


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, profession="commoner", circle=1, skills=None):
        self.db = DummyHolder()
        self.profession = profession
        self.db.circle = circle
        self.db.magic_slot_pool = None
        self.skills = dict(skills or {"primary_magic": 100})

    def get_profession(self):
        return self.profession

    def get_skill(self, skill_name):
        return self.skills.get(skill_name, 0)

    def get_circle(self):
        return self.db.circle

    def ensure_core_defaults(self):
        SpellbookService.ensure_spellbook_defaults(self)


class SpellAccessServiceTests(unittest.TestCase):
    def test_wrong_profession_fails(self):
        character = DummyCharacter(profession="cleric")
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "cleric_minor_heal", "npc")
        spell = get_spell("empath_heal")

        result = SpellAccessService.can_use_spell(character, spell)

        self.assertFalse(result.success)
        self.assertIn("You cannot comprehend that spell.", result.errors)

    def test_not_learned_fails(self):
        character = DummyCharacter(profession="empath")
        character.ensure_core_defaults()
        spell = get_spell("empath_heal")

        result = SpellAccessService.can_use_spell(character, spell)

        self.assertFalse(result.success)
        self.assertIn("You have not learned that spell.", result.errors)

    def test_low_circle_fails(self):
        character = DummyCharacter(profession="empath", circle=0)
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "empath_heal", "npc")
        spell = get_spell("empath_heal")

        result = SpellAccessService.can_use_spell(character, spell)

        self.assertFalse(result.success)
        self.assertIn("You are not experienced enough.", result.errors)

    def test_valid_spell_succeeds(self):
        character = DummyCharacter(profession="empath", circle=1, skills={"primary_magic": 20})
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "empath_heal", "npc")
        spell = get_spell("empath_heal")

        result = SpellAccessService.can_use_spell(character, spell)

        self.assertTrue(result.success)
        self.assertEqual(result.data["spell_id"], "empath_heal")
        self.assertEqual(result.data["via"], "permanent")

    def test_learn_spell_validates_acquisition_method(self):
        character = DummyCharacter(profession="cleric", circle=1)
        character.ensure_core_defaults()

        invalid = SpellbookService.learn_spell(character, "cleric_minor_heal", "ritual")
        npc = SpellbookService.learn_spell(character, "cleric_minor_heal", "npc")
        duplicate = SpellbookService.learn_spell(character, "cleric_minor_heal", "npc")

        self.assertFalse(invalid.success)
        self.assertIn("You cannot learn that spell that way.", invalid.errors)
        self.assertTrue(npc.success)
        self.assertFalse(duplicate.success)
        self.assertIn("You already know that spell.", duplicate.errors)

    def test_known_spell_tracks_method_and_circle(self):
        character = DummyCharacter(profession="cleric", circle=3)
        character.ensure_core_defaults()

        result = SpellbookService.learn_spell(character, "cleric_minor_heal", "book")

        self.assertTrue(result.success)
        self.assertTrue(SpellbookService.has_spell(character, "cleric_minor_heal"))
        self.assertEqual(character.db.spellbook["known_spells"]["cleric_minor_heal"]["learned_via"], "book")
        self.assertEqual(character.db.spellbook["known_spells"]["cleric_minor_heal"]["circle_learned"], 3)

    def test_list_helpers_filter_unknown_spells(self):
        character = DummyCharacter(profession="empath", circle=1)
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "empath_heal", "player")

        known = SpellAccessService.list_known_spells(character)
        available = SpellAccessService.list_available_spells(character)

        self.assertEqual([spell.id for spell in known], ["empath_heal"])
        self.assertEqual([spell.id for spell in available], ["empath_heal"])

    def test_integration_requires_learning_then_allows_use(self):
        empath = DummyCharacter(profession="empath", circle=1, skills={"primary_magic": 20})
        empath.ensure_core_defaults()
        spell = get_spell("empath_heal")

        before = SpellAccessService.can_use_spell(empath, spell)
        learned = SpellbookService.learn_spell(empath, "empath_heal", "npc")
        after = SpellAccessService.can_use_spell(empath, spell)
        wrong_profession = DummyCharacter(profession="cleric", circle=1, skills={"primary_magic": 20})
        wrong_profession.ensure_core_defaults()
        SpellbookService.learn_spell(wrong_profession, "cleric_minor_heal", "npc")
        wrong_after = SpellAccessService.can_use_spell(wrong_profession, spell)

        self.assertFalse(before.success)
        self.assertTrue(learned.success)
        self.assertTrue(after.success)
        self.assertFalse(wrong_after.success)
        self.assertIn("You cannot comprehend that spell.", wrong_after.errors)

    def test_apprentice_spell_is_available_without_memorization(self):
        character = DummyCharacter(profession="cleric", circle=5, skills={"primary_magic": 20})
        character.ensure_core_defaults()

        result = SpellAccessService.can_use_spell(character, get_spell("burden"))

        self.assertTrue(result.success)
        self.assertEqual(result.data["via"], "apprentice")

    def test_gauge_flow_is_not_apprentice_accessible(self):
        character = DummyCharacter(profession="cleric", circle=5, skills={"primary_magic": 20})
        character.ensure_core_defaults()

        result = SpellAccessService.can_use_spell(character, get_spell("gauge_flow"))

        self.assertFalse(result.success)
        self.assertIn("You have not learned that spell.", result.errors)

    def test_cleric_04_low_circle_spells_are_apprentice_accessible(self):
        character = DummyCharacter(profession="cleric", circle=5, skills={"primary_magic": 20})
        character.ensure_core_defaults()

        apprentice_ids = [spell.id for spell in SpellAccessService.get_apprentice_spells(character)]

        self.assertIn("bless", apprentice_ids)
        self.assertIn("protection_from_evil", apprentice_ids)
        self.assertIn("holy_light", apprentice_ids)

    def test_manifest_force_is_apprentice_accessible(self):
        character = DummyCharacter(profession="cleric", circle=5, skills={"primary_magic": 20})
        character.ensure_core_defaults()

        result = SpellAccessService.can_use_spell(character, get_spell("manifest_force"))

        self.assertTrue(result.success)
        self.assertEqual(result.data["via"], "apprentice")

    def test_apprentice_access_expires_at_circle_eleven(self):
        character = DummyCharacter(profession="cleric", circle=11, skills={"primary_magic": 20})
        character.ensure_core_defaults()

        result = SpellAccessService.can_use_spell(character, get_spell("burden"))

        self.assertFalse(result.success)
        self.assertIn("You have not learned that spell.", result.errors)

    def test_permanently_memorized_apprentice_spell_survives_expiration(self):
        character = DummyCharacter(profession="cleric", circle=10, skills={"primary_magic": 20})
        character.ensure_core_defaults()
        learned = SpellbookService.learn_spell(character, "burden", "book")
        character.db.circle = 11

        result = SpellAccessService.can_use_spell(character, get_spell("burden"))

        self.assertTrue(learned.success)
        self.assertTrue(result.success)
        self.assertEqual(result.data["via"], "permanent")

    def test_get_apprentice_spells_returns_only_current_nonmemorized_access(self):
        character = DummyCharacter(profession="cleric", circle=5, skills={"primary_magic": 20})
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "manifest_force", "scroll")

        apprentice_ids = [spell.id for spell in SpellAccessService.get_apprentice_spells(character)]

        self.assertEqual(
            apprentice_ids,
            ["bless", "burden", "strange_arrow", "holy_light", "protection_from_evil"],
        )

    def test_non_magic_profession_has_no_apprentice_access(self):
        character = DummyCharacter(profession="barbarian", circle=5, skills={"primary_magic": 20})
        character.ensure_core_defaults()

        self.assertEqual(SpellAccessService.get_apprentice_spells(character), [])

    def test_cleric_05_ward_spells_are_not_apprentice_accessible(self):
        character = DummyCharacter(profession="cleric", circle=20, skills={"primary_magic": 300})
        character.ensure_core_defaults()

        apprentice_ids = [spell.id for spell in SpellAccessService.get_apprentice_spells(character)]

        self.assertNotIn("major_physical_protection", apprentice_ids)
        self.assertNotIn("halo", apprentice_ids)
        self.assertNotIn("divine_radiance", apprentice_ids)

    def test_cleric_06_resurrection_spells_are_not_apprentice_accessible(self):
        character = DummyCharacter(profession="cleric", circle=20, skills={"primary_magic": 300})
        character.ensure_core_defaults()

        apprentice_ids = [spell.id for spell in SpellAccessService.get_apprentice_spells(character)]

        self.assertNotIn("rejuvenation", apprentice_ids)
        self.assertNotIn("mass_rejuvenation", apprentice_ids)

    def test_cleric_07_divine_intervention_spells_are_not_apprentice_accessible(self):
        character = DummyCharacter(profession="cleric", circle=20, skills={"primary_magic": 300})
        character.ensure_core_defaults()

        apprentice_ids = [spell.id for spell in SpellAccessService.get_apprentice_spells(character)]

        self.assertNotIn("aesrela_everild", apprentice_ids)
        self.assertNotIn("revelation", apprentice_ids)
        self.assertNotIn("hand_of_tenemlor", apprentice_ids)

    def test_cleric_08_utility_spells_are_not_apprentice_accessible(self):
        character = DummyCharacter(profession="cleric", circle=20, skills={"primary_magic": 300})
        character.ensure_core_defaults()

        apprentice_ids = [spell.id for spell in SpellAccessService.get_apprentice_spells(character)]

        self.assertNotIn("spirit_beacon", apprentice_ids)
        self.assertNotIn("uncurse", apprentice_ids)


if __name__ == "__main__":
    unittest.main()