import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from domain.abilities.dances.registry import DANCE_BY_BIT
from typeclasses.npcs import BarbarianPitMaster


class _Actor:
    def __init__(self, *, profession="barbarian", circle=100):
        self.profession = profession
        self.db = SimpleNamespace(circle=circle, spellbook2=0)

    def is_profession(self, profession):
        return self.profession == str(profession)

    def get_circle(self):
        return int(self.db.circle or 0)

    def get_spellbook2(self):
        return int(self.db.spellbook2 or 0)

    def set_spellbook2(self, value, emit_messages=True):
        self.db.spellbook2 = int(value or 0)
        return self.db.spellbook2


class BarbarianPitMasterTests(unittest.TestCase):
    def _guide(self, definition):
        return SimpleNamespace(
            key=definition.canonical_pit_master,
            db=SimpleNamespace(
                trains_profession="barbarian",
                teaches_dance=definition.name,
                required_level=definition.required_level,
                canonical_room_id=definition.canonical_pit_room,
            ),
        )

    def test_each_pit_master_teaches_configured_dance(self):
        for definition in DANCE_BY_BIT.values():
            with self.subTest(dance=definition.name):
                actor = _Actor(circle=max(100, int(definition.required_level)))
                result = BarbarianPitMaster.teach_dance(self._guide(definition), actor)

                self.assertTrue(result.success)
                self.assertTrue(actor.get_spellbook2() & (1 << int(definition.bit_index)))

    def test_underleveled_barbarian_is_refused(self):
        definition = DANCE_BY_BIT[1]
        actor = _Actor(circle=int(definition.required_level) - 1)

        result = BarbarianPitMaster.teach_dance(self._guide(definition), actor)

        self.assertFalse(result.success)
        self.assertIn("not seasoned enough", result.errors[0])

    def test_non_barbarian_is_refused(self):
        definition = DANCE_BY_BIT[2]
        actor = _Actor(profession="cleric", circle=100)

        result = BarbarianPitMaster.teach_dance(self._guide(definition), actor)

        self.assertFalse(result.success)
        self.assertIn("not for you", result.errors[0])

    def test_already_known_dance_is_refused(self):
        definition = DANCE_BY_BIT[3]
        actor = _Actor(circle=100)
        actor.set_spellbook2(1 << int(definition.bit_index))

        result = BarbarianPitMaster.teach_dance(self._guide(definition), actor)

        self.assertFalse(result.success)
        self.assertIn("already know", result.errors[0])


if __name__ == "__main__":
    unittest.main()