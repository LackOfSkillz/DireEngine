import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_circle import CmdCircle
from commands.cmd_learn_feat import CmdLearnFeat
from engine.services.spellbook_service import SpellbookService
from typeclasses.npcs import ClericGuildmaster, EmpathGuildleader, GuildLeaderNPC, RangerGuildleader


class _Room:
    def __init__(self):
        self.messages = []

    def msg_contents(self, text, exclude=None):
        self.messages.append(str(text))


class _Caller:
    def __init__(self, profession="cleric", circle=10, *, skills=None, coins=5000, exp_skill_state=None):
        self.key = "TestCaller"
        self.location = _Room()
        self.messages = []
        self.search_results = {}
        self.skills = dict(skills or {"primary_magic": 100, "theurgy": 100})
        self.db = SimpleNamespace(
            profession=profession,
            circle=circle,
            spellbook={"known_spells": {}},
            magic_slot_pool=None,
            exp_skill_state=dict(exp_skill_state or {"theurgy": {"rank": 500}}),
            coins=coins,
        )

    def ensure_core_defaults(self):
        SpellbookService.ensure_spellbook_defaults(self)

    def get_profession(self):
        return self.db.profession

    def is_profession(self, key):
        return self.get_profession() == str(key)

    def get_circle(self):
        return self.db.circle

    def get_skill(self, skill_name):
        return self.skills.get(skill_name, 0)

    def get_active_learning_entries(self):
        return []

    def get_mindstate_cap(self):
        return 130

    def msg(self, text):
        self.messages.append(str(text))

    def search(self, name, location=None):
        _location = location
        return self.search_results.get(str(name).strip().lower())

    def grant_tdp(self, amount, reason=""):
        return int(amount or 0)

    def sync_client_state(self):
        return None


class _EmpathCaller(_Caller):
    def __init__(self, circle=2):
        super().__init__(profession="empath", circle=circle, skills={"primary_magic": 100, "empathy": 8})

    def get_circle_progression_status(self):
        return {
            "current_circle": 2,
            "next_circle": 3,
            "requirements": {"empathy": 10},
            "current_ranks": {"empathy": 8},
        }

    def get_empath_progression_rank(self):
        return 8

    def format_skill_name(self, skill_name):
        return str(skill_name).replace("_", " ").title()

    def get_next_empath_unlock_status(self):
        return None

    def get_available_empath_unlocks(self):
        return []

    def get_empath_circle_status_lines(self):
        return []


class _RangerCaller(_Caller):
    def __init__(self, *, profession="ranger", circle=1, perception=0, forage_uses=0):
        super().__init__(profession=profession, circle=circle, skills={"perception": perception})
        self.db.forage_uses = forage_uses

    def can_advance_ranger(self):
        reasons = []
        if int(getattr(self.db, "forage_uses", 0) or 0) < 1:
            reasons.append("You have not yet learned to gather from the wild.")
        if int(self.get_skill("perception") or 0) < 5:
            reasons.append("Your awareness of the wild is still too shallow.")
        return (not reasons), (reasons or None)


class GuildProgressionCommandTests(unittest.TestCase):
    def test_learn_without_args_preserves_mindstate_output(self):
        caller = _Caller()
        command = SimpleNamespace(caller=caller, args="")

        CmdLearnFeat.func(command)

        self.assertEqual(caller.messages[-1], "Active Learning: clear [0/130]")

    def test_learn_spell_from_guildmaster_updates_spellbook(self):
        caller = _Caller(profession="cleric", circle=10)
        guide = SimpleNamespace(key="Guildleader Esuin", db=SimpleNamespace(trains_profession="cleric"))
        guide.teach_spell = lambda actor, spell_name: ClericGuildmaster.teach_spell(guide, actor, spell_name)
        caller.search_results["esuin"] = guide
        command = SimpleNamespace(caller=caller, args="bless from esuin")

        CmdLearnFeat.func(command)

        self.assertIn("bless", caller.db.spellbook["known_spells"])
        self.assertIn("commit the pattern to memory", caller.messages[-1].lower())

    def test_guildmaster_rejects_wrong_profession(self):
        caller = _Caller(profession="cleric", circle=10)
        guide = SimpleNamespace(db=SimpleNamespace(leads_profession="empath"))

        result = GuildLeaderNPC.teach_spell(guide, caller, "empath_heal")

        self.assertFalse(result.success)
        self.assertIn("Only Empaths may train here.", result.errors)

    def test_cleric_guildmaster_refuses_unshipped_directengine_spell(self):
        caller = _Caller(profession="cleric", circle=10)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="cleric"))

        result = ClericGuildmaster.teach_spell(guide, caller, "minor_barrier")

        self.assertFalse(result.success)
        self.assertIn("I do not teach a spell called 'minor_barrier'.", result.errors)

    def test_cleric_guildmaster_requires_circle_for_higher_tier_spell(self):
        caller = _Caller(profession="cleric", circle=2)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="cleric"))

        result = ClericGuildmaster.teach_spell(guide, caller, "halo")

        self.assertFalse(result.success)
        self.assertIn("Circle 20", result.errors[0])

    def test_empath_guildleader_teaches_empath_spell_from_allowlist(self):
        caller = _EmpathCaller(circle=2)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="empath"))

        result = EmpathGuildleader.teach_spell(guide, caller, "empath_heal")

        self.assertTrue(result.success)
        self.assertIn("empath_heal", caller.db.spellbook["known_spells"])

    def test_empath_guildleader_requires_circle_for_regenerate(self):
        caller = _EmpathCaller(circle=2)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="empath"))

        result = EmpathGuildleader.teach_spell(guide, caller, "regenerate")

        self.assertFalse(result.success)
        self.assertIn("Circle 5", result.errors[0])

    def test_empath_guildleader_refuses_off_class_spell(self):
        caller = _EmpathCaller(circle=10)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="empath"))

        result = EmpathGuildleader.teach_spell(guide, caller, "bless")

        self.assertFalse(result.success)
        self.assertIn("I do not teach a spell called 'bless'.", result.errors)

    def test_empath_guildleader_refuses_shared_cross_profession_spell(self):
        caller = _EmpathCaller(circle=10)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="empath"))

        result = EmpathGuildleader.teach_spell(guide, caller, "burden")

        self.assertFalse(result.success)
        self.assertIn("I do not teach a spell called 'burden'.", result.errors)

    def test_ranger_guildleader_refuses_off_class_spell(self):
        caller = _RangerCaller(circle=10, perception=10, forage_uses=1)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="ranger"))

        result = RangerGuildleader.teach_spell(guide, caller, "bless")

        self.assertFalse(result.success)
        self.assertIn("I do not teach a spell called 'bless'.", result.errors)

    def test_ranger_guildleader_teaches_animal_abilities_book_from_registry(self):
        caller = _RangerCaller(circle=10, perception=10, forage_uses=1)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="ranger"))

        for spell_name in [
            "wolf_scent",
            "see_the_wind",
            "spider_climb",
            "eagle_vision",
            "cheetah_swiftness",
            "bear_strength",
            "caiman_swim",
            "grizzly_claw",
            "senses_of_the_tiger",
            "wisdom_of_the_pack",
        ]:
            with self.subTest(spell_name=spell_name):
                result = RangerGuildleader.teach_spell(guide, caller, spell_name)
                self.assertTrue(result.success)
                self.assertIn(spell_name, caller.db.spellbook["known_spells"])

    def test_ranger_guildleader_teaches_wilderness_survival_book_from_registry(self):
        caller = _RangerCaller(circle=10, perception=10, forage_uses=1)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="ranger"))

        for spell_name in [
            "hands_of_lirisa",
            "earth_meld",
            "mesmerize",
            "blend",
            "breathe_water",
            "water_purification",
        ]:
            with self.subTest(spell_name=spell_name):
                result = RangerGuildleader.teach_spell(guide, caller, spell_name)
                self.assertTrue(result.success)
                self.assertIn(spell_name, caller.db.spellbook["known_spells"])

    def test_ranger_guildleader_teaches_wilderness_defense_book_from_registry(self):
        caller = _RangerCaller(circle=10, perception=10, forage_uses=1)
        guide = SimpleNamespace(db=SimpleNamespace(trains_profession="ranger"))

        for spell_name in [
            "compost",
            "swarm",
            "haraweps_bonds",
            "awaken_forest",
            "hobble",
            "branch_break",
            "plague_of_scavengers",
        ]:
            with self.subTest(spell_name=spell_name):
                result = RangerGuildleader.teach_spell(guide, caller, spell_name)
                self.assertTrue(result.success)
                self.assertIn(spell_name, caller.db.spellbook["known_spells"])

    def test_ranger_guildleader_advancement_feedback_mentions_missing_requirements(self):
        caller = _RangerCaller(circle=1, perception=1, forage_uses=0)
        guide = SimpleNamespace(db=SimpleNamespace())

        message = RangerGuildleader.handle_inquiry(guide, caller, "advancement")

        self.assertIn("gather from the wild", message)
        self.assertIn("awareness", message)

    def test_circle_for_cleric_uses_generic_progression_surface(self):
        caller = _Caller(
            profession="cleric",
            circle=9,
            skills={"primary_magic": 220, "theurgy": 180},
            exp_skill_state={"primary_magic": {"rank": 220}, "theurgy": {"rank": 180}},
        )
        command = SimpleNamespace(caller=caller, args="")

        CmdCircle.func(command)

        self.assertIn("Cleric Circle: 9", caller.messages[0])
        self.assertIn("Primary Magic: 220/225", "\n".join(caller.messages))
        self.assertIn("Theurgy: 180/225", "\n".join(caller.messages))
        self.assertNotIn("Only Empaths can circle this way.", "\n".join(caller.messages))

    def test_circle_for_empath_preserves_existing_path(self):
        caller = _EmpathCaller()
        command = SimpleNamespace(caller=caller, args="")

        CmdCircle.func(command)

        self.assertIn("Empath Circle: 2", caller.messages[0])


if __name__ == "__main__":
    unittest.main()