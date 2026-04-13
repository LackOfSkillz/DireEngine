import unittest

from domain.mana.backlash import (
    calculate_backlash_chance as calculate_margin_backlash_chance,
    calculate_backlash_severity,
    calculate_cast_margin,
    calculate_control_score,
    calculate_spell_difficulty,
    calculate_strain_penalty,
    resolve_backlash_payload,
    resolve_success_band,
)
from domain.mana.rules import (
    calculate_ambient_floor_required,
    calculate_attunement_max,
    calculate_attunement_regen,
    calculate_backlash_chance,
    calculate_cyclic_drain,
    calculate_effective_env_mana,
    calculate_final_spell_power,
    calculate_harness_cost,
    calculate_harness_efficiency,
    calculate_prep_cost,
    clamp,
    clamp_backlash,
    clamp_mana,
)


class ManaRulesTests(unittest.TestCase):
    def test_clamp_helpers_respect_bounds(self):
        self.assertEqual(clamp(-1, 0, 5), 0)
        self.assertEqual(clamp(7, 0, 5), 5)
        self.assertEqual(clamp(3, 0, 5), 3)
        self.assertEqual(clamp_mana(-0.1), 0.0)
        self.assertEqual(clamp_mana(3.0), 2.0)
        self.assertEqual(clamp_backlash(99.0), 75.0)

    def test_attunement_max_is_monotonic(self):
        low = calculate_attunement_max(10, 10, 10, 1)
        high = calculate_attunement_max(20, 15, 15, 2)
        self.assertGreaterEqual(low, 40.0)
        self.assertGreater(high, low)

    def test_effective_env_mana_and_floor_are_deterministic(self):
        self.assertEqual(calculate_effective_env_mana(1.0, 1.0, 1.0), 1.0)
        self.assertEqual(calculate_effective_env_mana(3.0, 1.0, 1.0), 2.0)
        self.assertEqual(calculate_ambient_floor_required(5), 1)
        self.assertEqual(calculate_ambient_floor_required(20), 2)

    def test_prep_cost_decreases_in_richer_environment(self):
        poor_cost = calculate_prep_cost(20, 0.5)
        rich_cost = calculate_prep_cost(20, 1.5)
        self.assertGreater(poor_cost, rich_cost)

    def test_regen_increases_when_more_attunement_is_missing(self):
        near_empty = calculate_attunement_regen(10, 100, 50, 30)
        near_full = calculate_attunement_regen(90, 100, 50, 30)
        self.assertGreater(near_empty, near_full)

    def test_regen_handles_zero_maximum(self):
        regen = calculate_attunement_regen(0, 0, 50, 30)
        self.assertGreaterEqual(regen, 0.0)

    def test_harness_efficiency_and_cost_clamp(self):
        low = calculate_harness_efficiency(0, 0)
        high = calculate_harness_efficiency(500, 500)
        self.assertEqual(low, 0.60)
        self.assertEqual(high, 0.95)
        self.assertEqual(calculate_harness_cost(10, 0.95), 11)

    def test_final_power_clamps_to_multiplier_ceiling(self):
        power = calculate_final_spell_power(100, 5000, 2.0, 100, 100, profession_cast_modifier=2.0)
        self.assertEqual(power, 250.0)

    def test_backlash_rises_under_strain(self):
        low = calculate_backlash_chance(10, 100, 10, 10, 100)
        high = calculate_backlash_chance(50, 20, 40, 10, 100)
        self.assertGreater(high, low)
        self.assertLessEqual(high, 75.0)

    def test_spell_difficulty_rises_when_overpushing_mana(self):
        spell = {"base_difficulty": 12, "safe_mana": 10, "tier": 2}
        safe = calculate_spell_difficulty(spell, 10, 1.0)
        overpush = calculate_spell_difficulty(spell, 25, 1.0)
        poor_env = calculate_spell_difficulty(spell, 10, 0.4)
        self.assertGreater(overpush, safe)
        self.assertGreater(poor_env, safe)

    def test_control_and_margin_resolve_bands(self):
        control = calculate_control_score(
            {
                "primary_magic_skill": 300,
                "attunement_skill": 250,
                "arcana_skill": 200,
                "intelligence": 30,
                "discipline": 30,
                "profession": "moon mage",
            },
            {},
        )
        margin = calculate_cast_margin(control, 80, calculate_strain_penalty(80, 100), 5)
        self.assertGreater(control, 0.0)
        self.assertIn(resolve_success_band(margin), {"excellent", "solid", "partial"})

    def test_margin_backlash_and_severity_rise_under_pressure(self):
        spell = {"safe_mana": 10, "mana_input": 30}
        mild = calculate_margin_backlash_chance(spell, 12, -2, 1.0)
        severe = calculate_margin_backlash_chance(spell, 30, -20, 0.4)
        self.assertGreater(severe, mild)
        self.assertGreaterEqual(calculate_backlash_severity(spell, 30, -20), 1)

    def test_backlash_payload_preserves_zero_safe_edges(self):
        payload = resolve_backlash_payload({"profession": "cleric"}, 2, {"mana_input": 0, "safe_mana": 0})
        self.assertEqual(payload["shock_gain"], 0)
        self.assertGreater(payload["devotion_loss_ratio"], 0.0)

    def test_cyclic_drain_has_minimum_of_one(self):
        self.assertEqual(calculate_cyclic_drain(0), 1)
        self.assertEqual(calculate_cyclic_drain(10), 1)
        self.assertEqual(calculate_cyclic_drain(20), 2)


if __name__ == "__main__":
    unittest.main()