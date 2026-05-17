import unittest
from types import SimpleNamespace

from domain.abilities.roars.deaths_embrace import DeathsEmbraceRoar
from domain.abilities.roars.deaths_lullaby import DeathsLullabyRoar
from domain.abilities.roars.deaths_shriek import DeathsShriekRoar
from domain.abilities.roars.magics_bane import MagicsBaneRoar
from domain.abilities.roars.tempestuous_fury import TempestuousFuryRoar
from domain.abilities.roars.trothfang_butchery import TrothfangButcheryRoar
from engine.services.roar_service import RoarService


class _Target:
    def __init__(self):
        self.id = 2
        self.key = "Goblin"
        self.roundtime = 0
        self.db = SimpleNamespace(states={}, stats={"discipline": 5, "reflex": 5, "agility": 5, "strength": 5, "stamina": 5}, mm=1, position="standing")

    def get_stat(self, name):
        return int(self.db.stats.get(str(name or "").strip().lower(), 0) or 0)

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states

    def set_roundtime(self, value):
        self.roundtime = float(value)

    def set_position_state(self, state):
        self.db.position_state = state


class _Actor:
    def __init__(self):
        self.id = 1
        self.key = "Barbarian"
        self.db = SimpleNamespace(stats={"discipline": 30, "charisma": 30, "strength": 20, "reflex": 20, "agility": 20, "stamina": 20}, circle=75)

    def get_stat(self, name):
        return int(self.db.stats.get(str(name or "").strip().lower(), 0) or 0)

    def get_circle(self):
        return self.db.circle


class BarbarianIntimidationRoarTests(unittest.TestCase):
    def test_trothfang_applies_reflex_agility_and_strength_penalties(self):
        actor = _Actor()
        target = _Target()

        result = TrothfangButcheryRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        payload = target.get_state("barbarian_roar_trothfang")
        self.assertIn("reflex", payload["stat_modifiers"])
        self.assertIn("agility", payload["stat_modifiers"])
        self.assertIn("strength", payload["stat_modifiers"])

    def test_tempestuous_applies_missile_penalties(self):
        actor = _Actor()
        target = _Target()

        result = TempestuousFuryRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        payload = target.get_state("barbarian_roar_tempestuous")
        self.assertIn("missile_accuracy", payload["penalties"])

    def test_deaths_embrace_applies_melee_penalties(self):
        actor = _Actor()
        target = _Target()

        result = DeathsEmbraceRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        payload = target.get_state("barbarian_roar_deaths_embrace")
        self.assertIn("melee_accuracy", payload["penalties"])

    def test_deaths_lullaby_applies_roundtime(self):
        actor = _Actor()
        target = _Target()

        result = DeathsLullabyRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda low, _high: low)

        self.assertTrue(result.success)
        self.assertGreaterEqual(target.roundtime, 1)

    def test_deaths_shriek_forces_kneeling(self):
        actor = _Actor()
        target = _Target()

        result = DeathsShriekRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertEqual(target.db.position, "kneeling")

    def test_magics_bane_applies_primary_magic_and_devices_penalties(self):
        actor = _Actor()
        target = _Target()

        result = MagicsBaneRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        payload = target.get_state("barbarian_roar_magics_bane")
        self.assertIn("primary_magic", payload["skill_modifiers"])
        self.assertIn("magical_devices", payload["skill_modifiers"])