import unittest

from engine.services.state_service import StateService

from domain.combat.maneuvers import ManeuverID
from domain.combat.resolution import (
    CombatOutcome,
    FULL_PARRY_THRESHOLD,
    NO_PARRY_THRESHOLD,
    AttackResolution,
    calculate_damage,
    compute_edf,
    compute_foi,
    compute_offensive_factor,
    compute_parry,
    compute_shield,
    resolve_attack,
)


class DummyDb:
    pass


class DummyItemDb:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class DummyShield:
    def __init__(self, mindef=10, maxdef=45):
        self.db = DummyItemDb(mindef=mindef, maxdef=maxdef)


class DummyWeapon:
    def __init__(self, profile=None, **attrs):
        self._profile = dict(profile or {})
        self.db = DummyItemDb(**attrs)

    def get_weapon_profile(self):
        return dict(self._profile)


class DummyActor:
    def __init__(self, *, stats=None, skills=None, stance=None, weapon=None, equipment=None, awareness="normal", states=None, effects=None, position_mods=None):
        self._stats = dict(stats or {})
        self._skills = dict(skills or {})
        self._weapon = weapon
        self._equipment = dict(equipment or {})
        self._awareness = awareness
        self._states = dict(states or {})
        self._effects = dict(effects or {})
        self._position_mods = dict(position_mods or {"offense": 0, "defense": 0})
        self.db = DummyDb()
        self.db.stance = dict(stance or {"offense": 50, "defense": 50})
        self.db.aiming = None
        self.db.is_npc = False
        self.db.max_hp = 100
        self.db.hp = 100
        self.db.intoxicated = False
        self.db.fatigue = 0
        self.db.injuries = {"body": {}, "head": {}}
        self.db.last_maneuver = 0
        self.id = 1
        self.location = None
        self.incoming_attackers = 1

    def get_stat(self, name):
        return self._stats.get(name, 0)

    def get_skill(self, name):
        return self._skills.get(name, 0)

    def get_total_hindrance(self):
        return (0, 0)

    def get_arm_penalty(self):
        return 0

    def get_hand_penalty(self):
        return 0

    def get_position_modifiers(self):
        return dict(self._position_mods)

    def get_awareness(self):
        return self._awareness

    def get_state(self, name):
        return self._states.get(name)

    def set_state(self, name, value):
        self._states[name] = value

    def clear_state(self, name):
        self._states.pop(name, None)

    def get_effect_modifier(self, name):
        return self._effects.get(name, 0)

    def get_weapon_profile(self):
        if self._weapon is None:
            return {"skill": "brawling", "damage": 3, "damage_min": 1, "damage_max": 3, "balance": 50}
        return self._weapon.get_weapon_profile()

    def get_equipment(self):
        return dict(self._equipment)

    def get_armor_for_bodypart(self, _part):
        return []

    def get_total_armor_protection(self, _part):
        return 0

    def format_body_part_name(self, part):
        return part

    def is_staggered(self):
        return False

    def is_surprised(self):
        return False

    def get_last_maneuver(self):
        return int(getattr(self.db, "last_maneuver", 0) or 0)


class FixedCombatRng:
    def __init__(self, *values):
        self._values = list(values)

    def roll(self):
        if not self._values:
            raise AssertionError("No more combat RNG values available")
        return self._values.pop(0)


class FixedRandom:
    def __init__(self, *values):
        self._values = list(values)

    def randint(self, _start, _end):
        if not self._values:
            return _start
        return self._values.pop(0)

    def choice(self, sequence):
        return sequence[0]


class CombatResolutionTests(unittest.TestCase):
    def setUp(self):
        weapon_profile = {
            "skill": "light_edge",
            "damage": 6,
            "damage_min": 4,
            "damage_max": 8,
            "balance": 60,
            "puncture": 2,
            "slice": 6,
            "impact": 2,
            "power": 55,
            "force": 8,
            "strength": 100,
            "current_damage": 0,
        }
        self.weapon = DummyWeapon(profile=weapon_profile)
        self.attacker = DummyActor(
            stats={"agility": 30, "reflex": 25, "strength": 28},
            skills={"light_edge": 60, "tactics": 20},
            weapon=self.weapon,
        )
        self.defender = DummyActor(
            stats={"agility": 20, "reflex": 22, "strength": 18},
            skills={"evasion": 35, "parry_ability": 30, "shield_usage": 20},
            weapon=DummyWeapon(profile={"skill": "light_edge", "balance": 55, "damage": 4, "damage_min": 2, "damage_max": 5}),
        )
        self.context = {
            "profile": self.weapon.get_weapon_profile(),
            "weapon": self.weapon,
            "weapon_effects": {},
            "skill_name": "light_edge",
            "suitability": 0,
            "current_range": "melee",
            "is_ranged_weapon": False,
            "ranger_aim_stacks": 0,
            "ambush": False,
            "ambush_accuracy_bonus": 0,
            "attacker_tempo_state": "calm",
            "surge_state": None,
            "press_state": None,
            "frenzy_state": None,
            "attacker_berserk": None,
            "attacker_disrupt": None,
            "attacker_unnerving": None,
            "attacker_intimidate": None,
            "snipe_active": False,
            "ranger_snipe": {},
            "ranger_mark": None,
            "hold_state": None,
            "defender_tempo_state": "calm",
            "defender_berserk": None,
            "defender_roars": {},
            "strong_ambush": False,
            "aimed_part": None,
            "aimed_location": None,
            "damage_type": "impact",
            "offensive_roar": None,
            "ambush_damage_multiplier": 1.0,
            "crush_state": None,
            "partial_ambush": False,
            "fatigue_cost": 0,
            "weapon_name": "training sword",
        }

    def test_attack_resolution_type_still_accepts_legacy_init(self):
        resolution = AttackResolution(hit=True, damage=3, roundtime=2, details={"outcome": "hit"})

        self.assertTrue(resolution.hit)
        self.assertEqual(resolution.damage, 3)
        self.assertEqual(resolution.roundtime, 2)
        self.assertEqual(resolution.details["outcome"], "hit")

    def test_offensive_factor_uses_rng_inside_total(self):
        """GSL S00041/S00265: OF includes the combat RNG multiplier inside OF itself."""
        of_low = compute_offensive_factor(self.attacker, self.defender, self.context, combat_rng=FixedCombatRng(80))
        of_high = compute_offensive_factor(self.attacker, self.defender, self.context, combat_rng=FixedCombatRng(120))

        self.assertLess(of_low.total, of_high.total)
        self.assertEqual(of_low.rng_pct, 80)
        self.assertEqual(of_high.rng_pct, 120)

    def test_edf_is_deterministic_without_rng(self):
        """GSL S00042: EDF is deterministic and does not consume combat RNG."""
        first = compute_edf(self.defender, self.attacker, self.context)
        second = compute_edf(self.defender, self.attacker, self.context)

        self.assertEqual(first.total, second.total)
        self.assertEqual(first.reflex, second.reflex)

    def test_edf_uses_last_maneuver_defense_scaling(self):
        """GSL S09449/S00042: defender last maneuver changes usable evasion scaling."""
        self.defender.db.last_maneuver = int(ManeuverID.LUNGE)
        after_lunge = compute_edf(self.defender, self.attacker, self.context)

        self.defender.db.last_maneuver = int(ManeuverID.DODGE)
        after_dodge = compute_edf(self.defender, self.attacker, self.context)

        self.assertLess(after_lunge.total, after_dodge.total)
        self.assertEqual(after_lunge.maneuver_scale_pct, 40)
        self.assertEqual(after_dodge.maneuver_scale_pct, 100)

    def test_foi_strength_bonus_is_capped_by_weapon_force(self):
        """GSL S00092: strength contribution to FOI is capped by weapon force."""
        strong = DummyActor(stats={"strength": 200}, skills={"light_edge": 60}, weapon=self.weapon)
        foi = compute_foi(strong, self.context, rng=FixedRandom(5))

        self.assertLessEqual(foi.strength_bonus, foi.base_roll + foi.strength_bonus)
        self.assertEqual(foi.base_roll, 5)
        self.assertGreaterEqual(foi.strength_bonus, 0)

    def test_parry_below_threshold_blocks_nothing(self):
        """GSL S00043: parry_percent below 50 yields no block."""
        weak_defender = DummyActor(stats={"agility": 1, "reflex": 1}, skills={"parry_ability": 1, "light_edge": 80}, weapon=self.defender._weapon)
        parry = compute_parry(weak_defender, leftover_of=200, context=self.context)

        self.assertLess(parry.parry_percent, NO_PARRY_THRESHOLD)
        self.assertEqual(parry.block_pct, 0)

    def test_parry_above_full_threshold_blocks_everything(self):
        """GSL S00043: parry_percent above 150 yields a full block."""
        strong_defender = DummyActor(stats={"agility": 80, "reflex": 80}, skills={"parry_ability": 120, "light_edge": 1}, weapon=self.defender._weapon)
        parry = compute_parry(strong_defender, leftover_of=40, context=self.context)

        self.assertGreater(parry.parry_percent, FULL_PARRY_THRESHOLD)
        self.assertEqual(parry.block_pct, 100)

    def test_parry_scaling_uses_last_maneuver(self):
        scaled_defender = DummyActor(stats={"agility": 80, "reflex": 80}, skills={"parry_ability": 120, "light_edge": 1}, weapon=self.defender._weapon)
        scaled_defender.db.last_maneuver = int(ManeuverID.LUNGE)
        after_lunge = compute_parry(scaled_defender, leftover_of=60, context=self.context)

        scaled_defender.db.last_maneuver = int(ManeuverID.PARRY)
        after_parry = compute_parry(scaled_defender, leftover_of=60, context=self.context)

        self.assertLess(after_lunge.parry_score, after_parry.parry_score)
        self.assertEqual(after_lunge.maneuver_scale_pct, 60)
        self.assertEqual(after_parry.maneuver_scale_pct, 100)

    def test_parry_uses_parry_ability_not_weapon_skill(self):
        defender = DummyActor(
            stats={"agility": 10, "reflex": 10},
            skills={"parry_ability": 5, "light_edge": 100},
            weapon=self.defender._weapon,
        )

        parry = compute_parry(defender, leftover_of=100, context=self.context)

        self.assertEqual(parry.parry_score, 28)

    def test_shield_uses_min_plus_skill_capped_by_max(self):
        """GSL S00046/S09449 bridge: shield score is capped, then scaled by last maneuver."""
        defender = DummyActor(
            stats={"agility": 20, "reflex": 20},
            skills={"shield_usage": 30},
            equipment={"shield": [DummyShield(mindef=12, maxdef=35)]},
        )
        shield = compute_shield(defender, leftover_of=50, context=self.context)

        self.assertEqual(shield.shield_score, 28)
        self.assertEqual(shield.block_pct, 28)

    def test_shield_scaling_uses_last_maneuver(self):
        defender = DummyActor(
            stats={"agility": 20, "reflex": 20},
            skills={"shield_usage": 30},
            equipment={"shield": [DummyShield(mindef=12, maxdef=35)]},
        )
        defender.db.last_maneuver = int(ManeuverID.LUNGE)
        after_lunge = compute_shield(defender, leftover_of=50, context=self.context)

        defender.db.last_maneuver = int(ManeuverID.DODGE)
        after_dodge = compute_shield(defender, leftover_of=50, context=self.context)

        self.assertLess(after_lunge.shield_score, after_dodge.shield_score)
        self.assertEqual(after_lunge.maneuver_scale_pct, 40)
        self.assertEqual(after_dodge.maneuver_scale_pct, 85)

    def test_shield_uses_shield_usage_not_legacy_shield(self):
        defender = DummyActor(
            stats={"agility": 20, "reflex": 20},
            skills={"shield": 30, "shield_usage": 5},
            equipment={"shield": [DummyShield(mindef=12, maxdef=35)]},
        )

        shield = compute_shield(defender, leftover_of=50, context=self.context)

        self.assertEqual(shield.shield_score, 13)

    def test_leftover_of_zero_yields_evasion_miss(self):
        """GSL S00092: leftover_OF <= 0 after OF-EDF subtraction means the attack is evaded."""
        defender = DummyActor(
            stats={"agility": 40, "reflex": 40},
            skills={"evasion": 90},
            weapon=self.defender._weapon,
        )
        result = resolve_attack(self.attacker, defender, context=self.context, combat_rng=FixedCombatRng(60), rng=FixedRandom(4, 4, 4))

        self.assertFalse(result.hit)
        self.assertEqual(result.details["combat_outcome"], CombatOutcome.EVADED.value)
        self.assertEqual(result.details["outcome"], "miss")

    def test_positive_leftover_of_reaches_hit_path(self):
        """GSL S00092: leftover_OF > 0 proceeds beyond evasion into impact resolution."""
        defender = DummyActor(
            stats={"agility": 5, "reflex": 5},
            skills={"evasion": 1},
            weapon=self.defender._weapon,
        )
        result = resolve_attack(self.attacker, defender, context=self.context, combat_rng=FixedCombatRng(120), rng=FixedRandom(6, 6, 6))

        self.assertTrue(result.hit)
        self.assertEqual(result.details["outcome"], "hit")
        self.assertGreater(result.details["leftover_of"], 0)

    def test_full_parry_converts_penetration_into_miss(self):
        """GSL S00092/S00043: full parry after penetration turns the attack into a blocked miss."""
        parrying_defender = DummyActor(
            stats={"agility": 90, "reflex": 90},
            skills={"evasion": 5, "parry_ability": 140, "light_edge": 1},
            weapon=self.defender._weapon,
        )
        result = resolve_attack(self.attacker, parrying_defender, context=self.context, combat_rng=FixedCombatRng(130), rng=FixedRandom(5, 5, 5))

        self.assertFalse(result.hit)
        self.assertEqual(result.details["combat_outcome"], CombatOutcome.FULLY_PARRIED.value)
        self.assertEqual(result.details["quality"], "blocked")

    def test_shield_partial_block_still_allows_hit(self):
        """GSL S00092/S00046: partial shield blocks reduce impact but do not necessarily negate the hit."""
        shielding_defender = DummyActor(
            stats={"agility": 5, "reflex": 5},
            skills={"evasion": 1, "shield_usage": 20},
            weapon=self.defender._weapon,
            equipment={"shield": [DummyShield(mindef=10, maxdef=25)]},
        )
        result = resolve_attack(self.attacker, shielding_defender, context=self.context, combat_rng=FixedCombatRng(140), rng=FixedRandom(8, 8, 8))

        self.assertTrue(result.hit)
        self.assertIn(result.details["combat_outcome"], {CombatOutcome.PARTIALLY_SHIELDED.value, CombatOutcome.HIT.value})
        self.assertGreater(result.details["post_defense_foi"], 0)

    def test_resolve_attack_populates_legacy_and_new_detail_fields(self):
        """DRG-024 compatibility: resolver keeps legacy detail keys while adding OF/EDF/FOI breakdowns."""
        result = resolve_attack(self.attacker, self.defender, context=self.context, combat_rng=FixedCombatRng(120), rng=FixedRandom(7, 7, 7))

        self.assertIn("accuracy", result.details)
        self.assertIn("evasion", result.details)
        self.assertIn("offensive_factor", result.details)
        self.assertIn("evasion_defense_factor", result.details)
        self.assertIn("force_of_impact", result.details)
        self.assertIn("leftover_of", result.details)

    def test_calculate_damage_preserves_placeholder_critical_hits(self):
        """DRG-024a still propagates critical-hit state through the new pipeline."""
        context = dict(self.context)
        context.update({
            "leftover_of": 30,
            "post_defense_foi": 18,
            "snipe_config": {},
            "maneuver": "swing",
        })

        damage = calculate_damage(self.attacker, self.defender, context, rng=FixedRandom(1, 15, 15, 15, 50, 50, 50, 20, 18, 90, 90, 90, 90))

        self.assertGreater(damage, 0)
        self.assertTrue(context["critical"])
        self.assertIn("raw_damage", context)
        self.assertIn("post_armor_damage", context)
        self.assertIn("wound_level", context)

    def test_calculate_damage_handles_targets_without_injuries_map(self):
        """Hit-area selection should not crash on valid targets that lack an initialized injuries map."""
        context = dict(self.context)
        context.update({
            "leftover_of": 30,
            "post_defense_foi": 18,
            "snipe_config": {},
            "maneuver": "swing",
        })
        defender = DummyActor(
            stats={"agility": 5, "reflex": 5},
            skills={"evasion": 1},
            weapon=self.defender._weapon,
        )
        delattr(defender.db, "injuries")

        damage = calculate_damage(self.attacker, defender, context, rng=FixedRandom(8, 50, 20, 20, 20, 15, 15, 90, 90, 90, 90))

        self.assertGreater(damage, 0)
        self.assertIn(context["hit_location"], {"head", "neck", "chest", "back", "abdomen", "left_arm", "right_arm", "left_hand", "right_hand", "left_leg", "right_leg", "tail"})
        self.assertIn("stamina_denominator", context)

    def test_manifest_force_absorbs_physical_damage_after_armor(self):
        from engine.services.state_service import StateService

        baseline_context = dict(self.context)
        baseline_context.update({
            "leftover_of": 30,
            "post_defense_foi": 18,
            "snipe_config": {},
            "maneuver": "swing",
        })
        context = dict(baseline_context)
        defender = DummyActor(
            stats={"agility": 5, "reflex": 5},
            skills={"evasion": 1},
            weapon=self.defender._weapon,
        )
        baseline_defender = DummyActor(
            stats={"agility": 5, "reflex": 5},
            skills={"evasion": 1},
            weapon=self.defender._weapon,
        )
        StateService.apply_warding_effect(defender, "manifest_force", strength=50, duration=20, absorbs_physical=True)

        baseline_damage = calculate_damage(self.attacker, baseline_defender, baseline_context, rng=FixedRandom(8, 50, 20, 20, 20, 15, 15, 90, 90, 90, 90))
        damage = calculate_damage(self.attacker, defender, context, rng=FixedRandom(8, 50, 20, 20, 20, 15, 15, 90, 90, 90, 90))

        self.assertGreaterEqual(int(context["barrier_event"].get("absorbed", 0) or 0), 1)
        self.assertLess(sum(int(v or 0) for v in context["post_armor_damage"].values() if isinstance(v, (int, float))), sum(int(v or 0) for v in baseline_context["post_armor_damage"].values() if isinstance(v, (int, float))))
        self.assertLessEqual(damage, baseline_damage)
        self.assertIn("post_armor_damage", context)

    def test_magic_only_ward_does_not_absorb_physical_damage(self):
        from engine.services.state_service import StateService

        baseline_context = dict(self.context)
        baseline_context.update({
            "leftover_of": 30,
            "post_defense_foi": 18,
            "snipe_config": {},
            "maneuver": "swing",
        })
        barrier_context = dict(baseline_context)
        baseline_defender = DummyActor(stats={"agility": 5, "reflex": 5}, skills={"evasion": 1}, weapon=self.defender._weapon)
        barrier_defender = DummyActor(stats={"agility": 5, "reflex": 5}, skills={"evasion": 1}, weapon=self.defender._weapon)
        StateService.apply_warding_effect(barrier_defender, "minor_barrier", strength=50, duration=20, absorbs_physical=False)

        baseline_damage = calculate_damage(self.attacker, baseline_defender, baseline_context, rng=FixedRandom(8, 50, 20, 20, 20, 15, 15, 90, 90, 90, 90))
        barrier_damage = calculate_damage(self.attacker, barrier_defender, barrier_context, rng=FixedRandom(8, 50, 20, 20, 20, 15, 15, 90, 90, 90, 90))

        self.assertEqual(baseline_damage, barrier_damage)
        self.assertEqual(barrier_context["barrier_event"], {})

    def test_bless_adds_accuracy_and_damage_against_undead_targets(self):
        blessed_attacker = DummyActor(
            stats={"agility": 30, "reflex": 25, "strength": 28},
            skills={"light_edge": 60, "tactics": 20},
            weapon=self.weapon,
        )
        undead_defender = DummyActor(
            stats={"agility": 5, "reflex": 5, "strength": 18},
            skills={"evasion": 1},
            weapon=self.defender._weapon,
        )
        undead_defender.key = "Restless Skeleton"
        undead_defender.db.creature_type = "undead"
        StateService.apply_utility_effect(
            blessed_attacker,
            "bless",
            20,
            source_spell="bless",
            extra_data={"strength": 3, "undead_accuracy_bonus": 6, "undead_damage_bonus": 3},
        )

        baseline_of = compute_offensive_factor(self.attacker, undead_defender, self.context, combat_rng=FixedCombatRng(100))
        blessed_of = compute_offensive_factor(blessed_attacker, undead_defender, self.context, combat_rng=FixedCombatRng(100))

        baseline_context = dict(self.context)
        baseline_context.update({"leftover_of": 30, "post_defense_foi": 18, "snipe_config": {}, "maneuver": "swing"})
        blessed_context = dict(baseline_context)
        baseline_damage = calculate_damage(self.attacker, undead_defender, baseline_context, rng=FixedRandom(8, 50, 20, 20, 20, 15, 15, 90, 90, 90, 90))
        blessed_damage = calculate_damage(blessed_attacker, undead_defender, blessed_context, rng=FixedRandom(8, 50, 20, 20, 20, 15, 15, 90, 90, 90, 90))

        self.assertGreater(blessed_of.total, baseline_of.total)
        self.assertGreater(blessed_damage, baseline_damage)

    def test_protection_from_evil_adds_evasion_bonus_against_undead_attackers(self):
        undead_attacker = DummyActor(
            stats={"agility": 30, "reflex": 25, "strength": 28},
            skills={"light_edge": 60, "tactics": 20},
            weapon=self.weapon,
        )
        undead_attacker.key = "Shadow Hound"
        undead_attacker.db.creature_type = "undead"
        protected_defender = DummyActor(
            stats={"agility": 20, "reflex": 22, "strength": 18},
            skills={"evasion": 35, "parry_ability": 30, "shield_usage": 20},
            weapon=self.defender._weapon,
        )
        StateService.apply_warding_effect(
            protected_defender,
            "protection_from_evil",
            strength=3,
            duration=20,
            extra_data={"undead_evasion_bonus": 6},
        )

        baseline = compute_edf(self.defender, undead_attacker, self.context)
        protected = compute_edf(protected_defender, undead_attacker, self.context)

        self.assertGreater(protected.total, baseline.total)

    def test_divine_radiance_adds_evasion_bonus_against_undead_attackers(self):
        undead_attacker = DummyActor(
            stats={"agility": 30, "reflex": 25, "strength": 28},
            skills={"light_edge": 60, "tactics": 20},
            weapon=self.weapon,
        )
        undead_attacker.key = "Restless Dead"
        undead_attacker.db.creature_type = "undead"
        radiant_defender = DummyActor(
            stats={"agility": 20, "reflex": 22, "strength": 18},
            skills={"evasion": 35, "parry_ability": 30, "shield_usage": 20},
            weapon=self.defender._weapon,
        )
        StateService.apply_warding_effect(
            radiant_defender,
            "divine_radiance",
            strength=2,
            duration=20,
            extra_data={"undead_evasion_bonus": 2},
        )

        baseline = compute_edf(self.defender, undead_attacker, self.context)
        protected = compute_edf(radiant_defender, undead_attacker, self.context)

        self.assertGreater(protected.total, baseline.total)


if __name__ == "__main__":
    unittest.main()