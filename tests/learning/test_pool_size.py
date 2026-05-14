import unittest

from domain.learning.pool_size import (
    base_pool_size,
    discipline_pool_bonus,
    intelligence_pool_bonus,
    total_pool_size,
    wisdom_pulse_multiplier,
)


class PoolSizeTests(unittest.TestCase):
    def test_base_pool_size_uses_canonical_skillset_formulas(self):
        self.assertAlmostEqual(base_pool_size(0, "primary"), 1000.0)
        self.assertAlmostEqual(base_pool_size(0, "secondary"), 850.0)
        self.assertAlmostEqual(base_pool_size(0, "tertiary"), 700.0)
        self.assertAlmostEqual(base_pool_size(100, "primary"), 2500.0)

    def test_intelligence_bonus_uses_piecewise_breakpoints(self):
        self.assertAlmostEqual(intelligence_pool_bonus(10), 0.0)
        self.assertAlmostEqual(intelligence_pool_bonus(30), 120.0)
        self.assertAlmostEqual(intelligence_pool_bonus(60), 210.0)
        self.assertAlmostEqual(intelligence_pool_bonus(90), 255.0)

    def test_discipline_bonus_uses_piecewise_breakpoints(self):
        self.assertAlmostEqual(discipline_pool_bonus(10), 0.0)
        self.assertAlmostEqual(discipline_pool_bonus(30), 40.0)
        self.assertAlmostEqual(discipline_pool_bonus(60), 70.0)
        self.assertAlmostEqual(discipline_pool_bonus(90), 85.0)

    def test_total_pool_size_applies_stat_modifier(self):
        total = total_pool_size(100, "primary", intelligence=30, discipline=30)
        self.assertAlmostEqual(total, 2900.0)

    def test_wisdom_pulse_multiplier_matches_documented_breakpoints(self):
        self.assertAlmostEqual(wisdom_pulse_multiplier(10), 1.0)
        self.assertAlmostEqual(wisdom_pulse_multiplier(30), 1.12)
        self.assertAlmostEqual(wisdom_pulse_multiplier(60), 1.21)
        self.assertAlmostEqual(wisdom_pulse_multiplier(120), 1.3)


if __name__ == "__main__":
    unittest.main()