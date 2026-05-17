import unittest
from types import SimpleNamespace

from engine.services.vocal_damage_service import VocalDamageService


class _Actor:
    def __init__(self, *, charisma=20, discipline=20, skills=None):
        self.db = SimpleNamespace(stats={"charisma": charisma, "discipline": discipline}, states={})
        self.skills = dict(skills or {})

    def get_stat(self, name):
        return int(self.db.stats.get(str(name or "").strip().lower(), 0) or 0)

    def get_skill(self, name):
        return int(self.skills.get(str(name or "").strip().lower(), 0) or 0)

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states

    def clear_state(self, key):
        states = dict(self.db.states or {})
        states.pop(key, None)
        self.db.states = states


class VocalDamageServiceTests(unittest.TestCase):
    def test_duration_matches_canonical_floor(self):
        actor = _Actor(charisma=40, discipline=40)

        duration = VocalDamageService.get_vocal_damage_duration(actor, randomizer=lambda _low, _high: -5)

        self.assertEqual(duration, 100)

    def test_intimidation_damage_tracks_total_and_modifier(self):
        actor = _Actor()
        for bit in range(3):
            VocalDamageService.add_vocal_damage(actor, VocalDamageService.INTIMIDATION_CODE, bit, randomizer=lambda _low, _high: 0)

        summary = VocalDamageService.get_total_vocal_damage(actor)

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["modifier"], 95)
        self.assertEqual(summary["message"], "You feel ready to defeat all challengers.")
        self.assertIsNotNone(actor.get_state("effect_3089001"))

    def test_inspiration_damage_contributes_to_total(self):
        actor = _Actor()
        VocalDamageService.add_vocal_damage(actor, VocalDamageService.INSPIRATION_CODE, 18, randomizer=lambda _low, _high: 0)
        VocalDamageService.add_vocal_damage(actor, VocalDamageService.INTIMIDATION_CODE, 0, randomizer=lambda _low, _high: 0)

        summary = VocalDamageService.get_total_vocal_damage(actor)

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["codes"]["3089001"], 1)
        self.assertEqual(summary["codes"]["3089002"], 1)

    def test_tier_boundaries_match_canonical_messages(self):
        actor = _Actor()
        cases = {
            0: "You feel ready to defeat an army!",
            1: "You feel ready to defeat all challengers.",
            8: "You feel worn but still ready to meet a challenge.",
            14: "You feel depleted and less than inspired.",
            18: "You feel weary of proclaiming your lust for battle.",
            21: "Your voice was nearly stolen by the weakness of your will to press on.",
        }
        for amount, expected in cases.items():
            VocalDamageService.clear_all_vocal_damage(actor)
            for index in range(amount):
                VocalDamageService.add_vocal_damage(actor, VocalDamageService.INTIMIDATION_CODE, index % 3, randomizer=lambda _low, _high: 0)
            self.assertEqual(VocalDamageService.get_exhaustion_tier(actor)["message"], expected)

    def test_expired_entries_are_pruned(self):
        actor = _Actor()
        actor.set_state(VocalDamageService.STATE_KEY, {"3089001": {"0": [1.0]}})

        summary = VocalDamageService.get_total_vocal_damage(actor)

        self.assertEqual(summary["total"], 0)
        self.assertIsNone(actor.get_state("effect_3089001"))

    def test_clear_all_vocal_damage_resets_effect_state(self):
        actor = _Actor()
        VocalDamageService.add_vocal_damage(actor, VocalDamageService.INTIMIDATION_CODE, 0, randomizer=lambda _low, _high: 0)

        summary = VocalDamageService.clear_all_vocal_damage(actor)

        self.assertEqual(summary["total"], 0)
        self.assertIsNone(actor.get_state("effect_3089001"))


if __name__ == "__main__":
    unittest.main()