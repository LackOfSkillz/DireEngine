import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from domain.abilities.roars.registry import ROAR_REGISTRY
from typeclasses.npcs import BarbarianGuildleader


class _Actor:
    def __init__(self, *, profession="barbarian", circle=300):
        self.profession = profession
        self.db = SimpleNamespace(circle=circle, spellbook1=0)

    def is_profession(self, profession):
        return self.profession == str(profession)

    def get_circle(self):
        return int(self.db.circle or 0)

    def get_spellbook1(self):
        return int(self.db.spellbook1 or 0)

    def set_spellbook1(self, value, emit_messages=True):
        self.db.spellbook1 = int(value or 0)
        return self.db.spellbook1


class TkielTeachingTests(unittest.TestCase):
    def _guide(self):
        return SimpleNamespace(db=SimpleNamespace(trains_profession="barbarian"))

    def test_tkiel_teaches_all_roars_with_sufficient_slots(self):
        caller = _Actor(circle=300)
        guide = self._guide()

        for definition in sorted(ROAR_REGISTRY.values(), key=lambda item: int(item.bit_index)):
            with self.subTest(roar=definition.name):
                result = BarbarianGuildleader.teach_roar(guide, caller, definition.canonical_display_name)
                self.assertTrue(result.success)
                self.assertTrue(caller.get_spellbook1() & (1 << int(definition.bit_index)))

    def test_tkiel_rejects_non_barbarian(self):
        caller = _Actor(profession="cleric", circle=300)

        result = BarbarianGuildleader.teach_roar(self._guide(), caller, "kuniyo")

        self.assertFalse(result.success)
        self.assertIn("for Barbarians", result.errors[0])

    def test_tkiel_rejects_when_slots_are_full(self):
        caller = _Actor(circle=5)
        guide = self._guide()

        self.assertTrue(BarbarianGuildleader.teach_roar(guide, caller, "kuniyo").success)
        result = BarbarianGuildleader.teach_roar(guide, caller, "everild")

        self.assertFalse(result.success)
        self.assertIn("no room", result.errors[0])

    def test_tkiel_rejects_deaths_shriek_without_prerequisite(self):
        caller = _Actor(circle=300)

        result = BarbarianGuildleader.teach_roar(self._guide(), caller, "death's shriek")

        self.assertFalse(result.success)
        self.assertIn("Death's Embrace", result.errors[0])

    def test_handle_inquiry_uses_alias_normalization_for_roars(self):
        caller = _Actor(circle=300)

        message = BarbarianGuildleader.handle_inquiry(self._guide(), caller, "deaths shriek")

        self.assertIn("Death's Embrace", message)
        self.assertEqual(caller.get_spellbook1(), 0)
        self.assertTrue(BarbarianGuildleader.teach_roar(self._guide(), caller, "death's embrace").success)
        message = BarbarianGuildleader.handle_inquiry(self._guide(), caller, "deaths shriek")
        self.assertIn("Death's Shriek", message)


if __name__ == "__main__":
    unittest.main()