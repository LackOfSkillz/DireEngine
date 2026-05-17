import unittest
from types import SimpleNamespace

from engine.services.ranger_saf_service import HowlState, RangerSafService


class _Room:
    def __init__(self, terrain="urban"):
        self._terrain = terrain

    def get_terrain_type(self):
        return self._terrain


class _Actor:
    def __init__(self, *, profession="ranger", saf=0, terrain="urban", companion=None, stealthed=False):
        self.profession = profession
        self.db = SimpleNamespace(
            profession=profession,
            canonical_saf=saf,
            ranger_companion=dict(companion or {}),
            stealthed=stealthed,
        )
        self.location = _Room(terrain=terrain)

    def get_ranger_terrain_type(self):
        return self.location.get_terrain_type()

    def get_ranger_companion(self):
        return dict(self.db.ranger_companion)


class RangerSafServiceTests(unittest.TestCase):
    def test_get_and_set_saf_clamp_to_canonical_range(self):
        actor = _Actor(saf=0)
        self.assertEqual(RangerSafService.get_saf(actor), 0)
        RangerSafService.set_saf(actor, 999)
        self.assertEqual(RangerSafService.get_saf(actor), 150)
        RangerSafService.set_saf(actor, -999)
        self.assertEqual(RangerSafService.get_saf(actor), -100)

    def test_get_spellcasting_modifier_uses_canonical_boundaries(self):
        ranger = _Actor(profession="ranger", saf=-100)
        non_ranger = _Actor(profession="cleric", saf=0)
        ranger_spell = SimpleNamespace(allowed_professions=["ranger"])
        self.assertEqual(RangerSafService.get_spellcasting_modifier(ranger, ranger_spell), -2)
        RangerSafService.set_saf(ranger, 0)
        self.assertEqual(RangerSafService.get_spellcasting_modifier(ranger, ranger_spell), 0)
        self.assertEqual(RangerSafService.get_spellcasting_modifier(non_ranger, ranger_spell), 2)

    def test_get_bow_load_modifier_uses_canonical_thresholds(self):
        actor = _Actor(saf=-51)
        self.assertEqual(RangerSafService.get_bow_load_modifier(actor), 1.1)
        RangerSafService.set_saf(actor, -50)
        self.assertEqual(RangerSafService.get_bow_load_modifier(actor), 1.0)
        RangerSafService.set_saf(actor, 76)
        self.assertEqual(RangerSafService.get_bow_load_modifier(actor), 0.9)
        RangerSafService.set_saf(actor, 75)
        self.assertEqual(RangerSafService.get_bow_load_modifier(actor), 1.0)

    def test_apply_forage_harm_cost_decrements_saf(self):
        """Gate 3 remains tested as directengine_canon after the negative forage canon audit."""
        actor = _Actor(saf=0)
        RangerSafService.apply_forage_harm_cost(actor)
        self.assertEqual(RangerSafService.get_saf(actor), -1)

    def test_clear_on_guild_commitment_resets_saf(self):
        actor = _Actor(saf=-50)
        RangerSafService.clear_on_guild_commitment(actor)
        self.assertEqual(RangerSafService.get_saf(actor), 0)

    def test_is_companion_tease_enabled_requires_wilderness_and_threshold(self):
        actor = _Actor(saf=-26, terrain="forest")
        self.assertTrue(RangerSafService.is_companion_tease_enabled(actor))
        RangerSafService.set_saf(actor, -25)
        self.assertFalse(RangerSafService.is_companion_tease_enabled(actor))
        RangerSafService.set_saf(actor, -30)
        actor.location = _Room("urban")
        self.assertFalse(RangerSafService.is_companion_tease_enabled(actor))

    def test_get_howl_state_returns_enhanced_for_wilderness_wolf_combo(self):
        actor = _Actor(saf=-26, terrain="forest", companion={"name": "wolf"})
        self.assertEqual(RangerSafService.get_howl_state(actor), HowlState.ENHANCED)

    def test_get_howl_state_returns_trapped_for_stealth_howl_without_affinity(self):
        actor = _Actor(saf=0, terrain="forest", stealthed=True)
        self.assertEqual(RangerSafService.get_howl_state(actor), HowlState.TRAPPED)

    def test_get_howl_state_returns_normal_otherwise(self):
        actor = _Actor(saf=-10, terrain="forest", companion={"name": "raccoon"})
        self.assertEqual(RangerSafService.get_howl_state(actor), HowlState.NORMAL)

    def test_get_multi_tier_threshold_uses_verified_boundary(self):
        actor = _Actor(saf=-33)
        self.assertEqual(RangerSafService.get_multi_tier_threshold(actor), 1)
        RangerSafService.set_saf(actor, -34)
        self.assertEqual(RangerSafService.get_multi_tier_threshold(actor), 0)

    def test_get_display_percent_returns_zero_minus_saf(self):
        actor = _Actor(saf=-50)
        self.assertEqual(RangerSafService.get_display_percent(actor), 50)
        RangerSafService.set_saf(actor, 100)
        self.assertEqual(RangerSafService.get_display_percent(actor), -100)

    def test_get_skin_yield_bonus_uses_canonical_formula(self):
        actor = _Actor(saf=-100)
        self.assertEqual(RangerSafService.get_skin_yield_bonus(actor, 20), 20)
        RangerSafService.set_saf(actor, 0)
        self.assertEqual(RangerSafService.get_skin_yield_bonus(actor, 20), 15)

    def test_tick_drift_applies_urban_and_wilderness_clamped_steps(self):
        actor = _Actor(saf=149)
        RangerSafService.tick_drift(actor, urbanclass=8)
        self.assertEqual(RangerSafService.get_saf(actor), 150)
        RangerSafService.set_saf(actor, -99)
        RangerSafService.tick_drift(actor, urbanclass=7)
        self.assertEqual(RangerSafService.get_saf(actor), -100)


if __name__ == "__main__":
    unittest.main()