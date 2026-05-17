import unittest
from types import SimpleNamespace

from domain.abilities.roars.kuniyo_spirit import KuniyoSpiritRoar
from engine.services.roar_service import RoarService


class _Target:
    def __init__(self):
        self.id = 2
        self.key = "Goblin"
        self.db = SimpleNamespace(states={}, stats={"discipline": 5, "reflex": 5, "agility": 5, "strength": 5}, mm=1)

    def get_stat(self, name):
        return int(self.db.stats.get(str(name or "").strip().lower(), 0) or 0)

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states


class _Actor:
    def __init__(self):
        self.id = 1
        self.key = "Barbarian"
        self.db = SimpleNamespace(stats={"discipline": 30, "charisma": 25, "strength": 20, "reflex": 20, "agility": 20}, circle=5)

    def get_stat(self, name):
        return int(self.db.stats.get(str(name or "").strip().lower(), 0) or 0)

    def get_circle(self):
        return self.db.circle


class KuniyoSpiritTests(unittest.TestCase):
    def test_begin_roar_applies_stun_vulnerability_on_success(self):
        actor = _Actor()
        target = _Target()

        result = KuniyoSpiritRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertIsNotNone(target.get_state("effect_2077001"))
        self.assertGreaterEqual(target.get_state("effect_2077001")["stun_vulnerability_pct"], 100)


if __name__ == "__main__":
    unittest.main()