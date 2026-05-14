import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_slots import CmdSlots
from commands.cmd_spellbook import CmdSpells
from engine.services.spellbook_service import SpellbookService


class _MagicCaller:
    def __init__(self, profession="cleric", circle=5, skills=None):
        self.db = SimpleNamespace(
            profession=profession,
            circle=circle,
            spellbook={"known_spells": {}},
            magic_slot_pool=None,
        )
        self.skills = dict(skills or {"primary_magic": 100})
        self.messages = []

    def ensure_core_defaults(self):
        return None

    def get_profession(self):
        return self.db.profession

    def get_circle(self):
        return self.db.circle

    def get_skill(self, skill_name):
        return self.skills.get(skill_name, 0)

    def msg(self, text):
        self.messages.append(str(text))


class SpellCommandTests(unittest.TestCase):
    def test_slots_command_shows_magic_pool(self):
        caller = _MagicCaller(profession="cleric", circle=10)
        SpellbookService.learn_spell(caller, "burden", "book")
        command = SimpleNamespace(caller=caller)

        CmdSlots.func(command)

        output = caller.messages[-1]
        self.assertIn("Magic Slot Pool", output)
        self.assertIn("Total: 10 | Used: 1 | Available: 9", output)
        self.assertIn("Burden: 1 slot", output)

    def test_slots_command_rejects_non_magic_profession(self):
        caller = _MagicCaller(profession="barbarian", circle=10)
        command = SimpleNamespace(caller=caller)

        CmdSlots.func(command)

        self.assertEqual(caller.messages[-1], "You are not a magic-using profession; you have no slot pool.")

    def test_spells_command_distinguishes_permanent_and_apprentice(self):
        caller = _MagicCaller(profession="cleric", circle=5)
        SpellbookService.learn_spell(caller, "manifest_force", "scroll")
        command = SimpleNamespace(caller=caller)

        CmdSpells.func(command)

        output = caller.messages[-1]
        self.assertIn("Permanently Memorized:", output)
        self.assertIn("Manifest Force (Warding) [1 slot]", output)
        self.assertIn("Apprentice Access (expires at circle 11):", output)
        self.assertIn("Burden (Debilitation)", output)
        self.assertIn("Strange Arrow (Targeted Magic)", output)
        self.assertNotIn("Manifest Force (Warding)\n", output)

    def test_spells_command_hides_apprentice_section_for_non_magic_profession(self):
        caller = _MagicCaller(profession="barbarian", circle=5)
        command = SimpleNamespace(caller=caller)

        CmdSpells.func(command)

        self.assertEqual(caller.messages[-1], "You do not currently have any accessible spells.")

    def test_spells_command_has_no_apprentice_section_after_expiration(self):
        caller = _MagicCaller(profession="cleric", circle=11)
        SpellbookService.learn_spell(caller, "manifest_force", "scroll")
        command = SimpleNamespace(caller=caller)

        CmdSpells.func(command)

        output = caller.messages[-1]
        self.assertIn("Permanently Memorized:", output)
        self.assertNotIn("Apprentice Access", output)


if __name__ == "__main__":
    unittest.main()