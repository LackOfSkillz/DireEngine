import unittest
from types import SimpleNamespace

from engine.services.barbarian_saf_service import BarbarianSafService


class _Actor:
    def __init__(self, *, profession="barbarian", saf=0, stats=None):
        self.profession = profession
        self.db = SimpleNamespace(profession=profession, canonical_saf=saf)
        self.stats = dict(stats or {"discipline": 20, "stamina": 10, "charisma": 10})

    def get_stat(self, name):
        return int(self.stats.get(str(name or "").strip().lower(), 0) or 0)


class BarbarianSafServiceTests(unittest.TestCase):
    def test_non_barbarians_do_not_expose_inner_fire(self):
        actor = _Actor(profession="cleric", saf=75)

        self.assertEqual(BarbarianSafService.get_inner_fire(actor), 0)
        self.assertFalse(BarbarianSafService.is_berserk_available(actor))

    def test_inner_fire_stays_non_negative(self):
        actor = _Actor(saf=-5)

        self.assertEqual(BarbarianSafService.get_inner_fire(actor), 0)
        BarbarianSafService.set_inner_fire(actor, -25)
        self.assertEqual(BarbarianSafService.get_inner_fire(actor), 0)

    def test_s00264_magic_costs_match_canonical_formulas(self):
        actor = _Actor(saf=10)

        self.assertEqual(BarbarianSafService.apply_magic_hit_cost(actor, 7), 17)
        self.assertEqual(BarbarianSafService.apply_magic_cast_cost(actor, 3), 32)

    def test_berserk_cost_uses_canonical_stat_formula(self):
        actor = _Actor(saf=10, stats={"discipline": 20, "stamina": 10, "charisma": 5})

        self.assertEqual(BarbarianSafService.calculate_berserk_delta(actor), 120)
        self.assertEqual(BarbarianSafService.apply_berserk_cost(actor), 130)

    def test_berserk_cost_accepts_override_formula(self):
        actor = _Actor(saf=10)

        self.assertEqual(BarbarianSafService.apply_berserk_cost(actor, override_formula=7), 17)

    def test_recovery_and_admin_paths_move_toward_verified_baseline(self):
        actor = _Actor(saf=25)

        self.assertEqual(BarbarianSafService.tick_inner_fire_recovery(actor), 24)
        self.assertEqual(BarbarianSafService.curse(actor), 124)
        self.assertEqual(BarbarianSafService.praise(actor), 0)
        self.assertEqual(BarbarianSafService.clear_on_guild_commitment(actor), 0)

    def test_berserk_gate_stays_available_at_zero_or_higher(self):
        actor = _Actor(saf=0)
        self.assertTrue(BarbarianSafService.is_berserk_available(actor))


if __name__ == "__main__":
    unittest.main()