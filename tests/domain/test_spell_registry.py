import unittest

from domain.spells.spell_definitions import SPELL_REGISTRY, Spell, get_spell


class SpellRegistryTests(unittest.TestCase):
    def test_registry_contains_seed_spells(self):
        self.assertIn("empath_heal", SPELL_REGISTRY)
        self.assertIn("cleric_minor_heal", SPELL_REGISTRY)
        self.assertIn("daze", SPELL_REGISTRY)
        self.assertIn("slow", SPELL_REGISTRY)

    def test_registry_contains_migrated_legacy_room_and_utility_spells(self):
        for spell_id in ["hinder", "shielding", "glimmer", "radiant_burst", "shared_guard", "cleanse"]:
            with self.subTest(spell_id=spell_id):
                self.assertIn(spell_id, SPELL_REGISTRY)

    def test_get_spell_returns_dataclass(self):
        spell = get_spell("empath_heal")

        self.assertIsInstance(spell, Spell)
        self.assertEqual(spell.name, "Heal")
        self.assertEqual(spell.allowed_professions, ["empath"])

    def test_analogous_patterns_seed_metadata_matches_canon(self):
        burden = get_spell("burden")
        gauge_flow = get_spell("gauge_flow")
        strange_arrow = get_spell("strange_arrow")
        manifest_force = get_spell("manifest_force")

        self.assertEqual(burden.slot_cost, 1)
        self.assertEqual(burden.apprentice_until_circle, 10)
        self.assertNotIn("apprentice", burden.acquisition_methods)
        self.assertEqual(gauge_flow.slot_cost, 2)
        self.assertIsNone(gauge_flow.apprentice_until_circle)
        self.assertNotIn("apprentice", gauge_flow.acquisition_methods)
        self.assertEqual(strange_arrow.slot_cost, 1)
        self.assertEqual(strange_arrow.apprentice_until_circle, 10)
        self.assertNotIn("apprentice", strange_arrow.acquisition_methods)
        self.assertEqual(manifest_force.slot_cost, 1)
        self.assertEqual(manifest_force.apprentice_until_circle, 10)
        self.assertEqual(manifest_force.acquisition_methods, ["scroll"])
        self.assertIn("trader", burden.allowed_professions)

    def test_cleric_accessible_spell_provenance_matches_policy(self):
        directengine_cleric_rows = [
            "arc_burst",
            "bolster",
            "cleanse",
            "cleric_minor_heal",
            "flare",
            "glimmer",
            "hinder",
            "minor_barrier",
            "radiant_burst",
            "shared_guard",
            "shielding",
            "slow",
        ]
        magic_three_rows = ["burden", "gauge_flow", "manifest_force", "strange_arrow"]

        for spell_id in directengine_cleric_rows:
            with self.subTest(spell_id=spell_id):
                self.assertEqual(get_spell(spell_id).provenance, "directengine_canon")

        for spell_id in magic_three_rows:
            with self.subTest(spell_id=spell_id):
                self.assertEqual(get_spell(spell_id).provenance, "magic_3_0_design")

    def test_empath_accessible_spell_provenance_matches_drg_empath_02_audit(self):
        directengine_empath_rows = [
            "arc_burst",
            "bolster",
            "cleanse",
            "flare",
            "glimmer",
            "hinder",
            "radiant_burst",
            "shared_guard",
            "shielding",
        ]
        magic_three_rows = ["burden", "gauge_flow", "manifest_force", "strange_arrow"]
        canonical_healing_rows = [
            "external_wound_healing",
            "internal_wound_healing",
            "vitality_healing",
            "heal_wounds",
            "heal_scars",
            "heal",
            "flush_poisons",
            "cure_disease",
            "regenerate",
        ]

        self.assertEqual(get_spell("empath_heal").provenance, "hybrid_design")

        for spell_id in directengine_empath_rows:
            with self.subTest(spell_id=spell_id):
                self.assertEqual(get_spell(spell_id).provenance, "directengine_canon")

        for spell_id in canonical_healing_rows:
            with self.subTest(spell_id=spell_id):
                self.assertEqual(get_spell(spell_id).provenance, "gsl_2004")

        for spell_id in magic_three_rows:
            with self.subTest(spell_id=spell_id):
                self.assertEqual(get_spell(spell_id).provenance, "magic_3_0_design")

    def test_empath_04_healing_book_metadata(self):
        external = get_spell("external_wound_healing")
        internal = get_spell("internal_wound_healing")
        vitality = get_spell("vitality_healing")
        heal_wounds = get_spell("heal_wounds")
        heal_scars = get_spell("heal_scars")
        heal = get_spell("heal")

        self.assertEqual(external.target_type, "self")
        self.assertEqual(external.apprentice_until_circle, 10)
        self.assertEqual(external.effect_profile.get("gsl_spell_id"), 401001)
        self.assertEqual(internal.target_type, "self")
        self.assertEqual(internal.apprentice_until_circle, 10)
        self.assertEqual(internal.effect_profile.get("gsl_spell_id"), 401002)
        self.assertEqual(vitality.target_type, "self")
        self.assertEqual(vitality.apprentice_until_circle, 10)
        self.assertEqual(vitality.effect_profile.get("gsl_spell_id"), 401005)
        self.assertEqual(heal_wounds.target_type, "self")
        self.assertIsNone(heal_wounds.apprentice_until_circle)
        self.assertEqual(heal_wounds.effect_profile.get("gsl_spell_id"), 401006)
        self.assertEqual(heal_scars.target_type, "self")
        self.assertIsNone(heal_scars.apprentice_until_circle)
        self.assertEqual(heal_scars.effect_profile.get("gsl_spell_id"), 401007)
        self.assertEqual(heal.target_type, "self")
        self.assertIsNone(heal.apprentice_until_circle)
        self.assertEqual(heal.effect_profile.get("gsl_spell_id"), 401008)

    def test_empath_05_cleansing_book_metadata(self):
        flush_poisons = get_spell("flush_poisons")
        cure_disease = get_spell("cure_disease")

        self.assertEqual(flush_poisons.target_type, "self")
        self.assertIsNone(flush_poisons.apprentice_until_circle)
        self.assertEqual(flush_poisons.spellbook, "Cleansing")
        self.assertEqual(flush_poisons.effect_profile.get("gsl_spell_id"), 402002)
        self.assertEqual(flush_poisons.effect_profile.get("castmod_a0"), 10)
        self.assertEqual(flush_poisons.effect_profile.get("castmod_a1"), 35)
        self.assertEqual(flush_poisons.effect_profile.get("castmod_a3"), "100110004")

        self.assertEqual(cure_disease.target_type, "self")
        self.assertIsNone(cure_disease.apprentice_until_circle)
        self.assertEqual(cure_disease.spellbook, "Cleansing")
        self.assertEqual(cure_disease.effect_profile.get("gsl_spell_id"), 402003)
        self.assertEqual(cure_disease.effect_profile.get("castmod_a0"), 12)
        self.assertEqual(cure_disease.effect_profile.get("castmod_a1"), 20)
        self.assertEqual(cure_disease.effect_profile.get("castmod_a3"), "100112004")

    def test_empath_06_vitality_book_metadata(self):
        refresh = get_spell("refresh")
        raise_power = get_spell("raise_power")
        gift_of_life = get_spell("gift_of_life")

        self.assertEqual(refresh.target_type, "self_or_other")
        self.assertEqual(refresh.apprentice_until_circle, 10)
        self.assertEqual(refresh.spellbook, "Vitality")
        self.assertEqual(refresh.effect_profile.get("gsl_spell_id"), 403001)
        self.assertEqual(refresh.effect_profile.get("castmod_a0"), 1)
        self.assertEqual(refresh.effect_profile.get("castmod_a1"), 15)
        self.assertEqual(refresh.effect_profile.get("castmod_a3"), "075133007")

        self.assertEqual(raise_power.target_type, "self")
        self.assertIsNone(raise_power.apprentice_until_circle)
        self.assertEqual(raise_power.spellbook, "Vitality")
        self.assertEqual(raise_power.effect_profile.get("gsl_spell_id"), 403002)
        self.assertEqual(raise_power.effect_profile.get("castmod_a0"), 6)
        self.assertEqual(raise_power.effect_profile.get("castmod_a1"), 18)
        self.assertEqual(raise_power.effect_profile.get("castmod_a3"), "036330004")

        self.assertEqual(gift_of_life.target_type, "self")
        self.assertIsNone(gift_of_life.apprentice_until_circle)
        self.assertEqual(gift_of_life.spellbook, "Vitality")
        self.assertEqual(gift_of_life.effect_profile.get("gsl_spell_id"), 403003)
        self.assertEqual(gift_of_life.effect_profile.get("castmod_a0"), 6)
        self.assertEqual(gift_of_life.effect_profile.get("castmod_a1"), 60)
        self.assertEqual(gift_of_life.effect_profile.get("castmod_a3"), "080123007")

    def test_empath_07_protection_book_metadata(self):
        innocence = get_spell("innocence")
        zone = get_spell("zone_of_protection")

        self.assertEqual(innocence.target_type, "self")
        self.assertIsNone(innocence.apprentice_until_circle)
        self.assertEqual(innocence.spellbook, "Protection")
        self.assertEqual(innocence.effect_profile.get("gsl_spell_id"), 404002)
        self.assertEqual(innocence.effect_profile.get("castmod_a0"), 5)
        self.assertEqual(innocence.effect_profile.get("castmod_a1"), 25)
        self.assertEqual(innocence.effect_profile.get("castmod_a3"), "057190008")

        self.assertEqual(zone.target_type, "self")
        self.assertIsNone(zone.apprentice_until_circle)
        self.assertEqual(zone.spellbook, "Protection")
        self.assertEqual(zone.effect_profile.get("gsl_spell_id"), 404003)
        self.assertEqual(zone.effect_profile.get("castmod_a0"), 15)
        self.assertEqual(zone.effect_profile.get("castmod_a1"), 40)
        self.assertEqual(zone.effect_profile.get("castmod_a3"), "050015010")

    def test_ranger_02_animal_abilities_book_metadata(self):
        wolf_scent = get_spell("wolf_scent")
        see_the_wind = get_spell("see_the_wind")
        spider_climb = get_spell("spider_climb")
        eagle_vision = get_spell("eagle_vision")
        cheetah_swiftness = get_spell("cheetah_swiftness")
        bear_strength = get_spell("bear_strength")
        caiman_swim = get_spell("caiman_swim")
        grizzly_claw = get_spell("grizzly_claw")
        senses_of_the_tiger = get_spell("senses_of_the_tiger")
        wisdom_of_the_pack = get_spell("wisdom_of_the_pack")

        self.assertEqual(wolf_scent.target_type, "self_or_other")
        self.assertEqual(wolf_scent.spellbook, "Animal Abilities")
        self.assertEqual(wolf_scent.effect_profile.get("castmod_a0"), 5)
        self.assertEqual(wolf_scent.effect_profile.get("castmod_a1"), 6)
        self.assertEqual(wolf_scent.effect_profile.get("castmod_a3"), "060182006")

        self.assertEqual(see_the_wind.target_type, "self_or_other")
        self.assertEqual(see_the_wind.effect_profile.get("gsl_spell_id"), 405002)
        self.assertEqual(see_the_wind.effect_profile.get("castmod_a3"), "060182003")

        self.assertEqual(spider_climb.target_type, "self_or_other")
        self.assertEqual(spider_climb.effect_profile.get("gsl_spell_id"), 405003)
        self.assertEqual(spider_climb.effect_profile.get("castmod_a3"), "063182005")

        self.assertEqual(eagle_vision.target_type, "self")
        self.assertEqual(eagle_vision.effect_profile.get("gsl_spell_id"), 405004)
        self.assertEqual(eagle_vision.effect_profile.get("castmod_a3"), "500001001")

        self.assertEqual(cheetah_swiftness.target_type, "self")
        self.assertEqual(cheetah_swiftness.effect_profile.get("gsl_spell_id"), 405005)
        self.assertEqual(cheetah_swiftness.effect_profile.get("castmod_a3"), "200020035")

        self.assertEqual(bear_strength.target_type, "self")
        self.assertEqual(bear_strength.effect_profile.get("gsl_spell_id"), 405006)
        self.assertEqual(bear_strength.effect_profile.get("castmod_a3"), "200020050")

        self.assertEqual(caiman_swim.target_type, "self_or_other")
        self.assertEqual(caiman_swim.effect_profile.get("gsl_spell_id"), 405007)
        self.assertEqual(caiman_swim.effect_profile.get("castmod_a3"), "063182005")

        self.assertEqual(grizzly_claw.target_type, "single")
        self.assertTrue(grizzly_claw.effect_profile.get("disallow_self_target"))
        self.assertEqual(grizzly_claw.effect_profile.get("gsl_spell_id"), 405008)
        self.assertEqual(grizzly_claw.effect_profile.get("castmod_a3"), "060180010")

        self.assertEqual(senses_of_the_tiger.target_type, "self")
        self.assertEqual(senses_of_the_tiger.effect_profile.get("gsl_spell_id"), 405009)
        self.assertEqual(senses_of_the_tiger.effect_profile.get("castmod_a3"), "060180007")

        self.assertEqual(wisdom_of_the_pack.target_type, "self")
        self.assertEqual(wisdom_of_the_pack.effect_profile.get("gsl_spell_id"), 405010)
        self.assertEqual(wisdom_of_the_pack.effect_profile.get("castmod_a3"), "050200016")

        hands_of_lirisa = get_spell("hands_of_lirisa")
        earth_meld = get_spell("earth_meld")
        mesmerize = get_spell("mesmerize")
        blend = get_spell("blend")
        breathe_water = get_spell("breathe_water")
        water_purification = get_spell("water_purification")
        compost = get_spell("compost")
        swarm = get_spell("swarm")
        haraweps_bonds = get_spell("haraweps_bonds")
        awaken_forest = get_spell("awaken_forest")
        hobble = get_spell("hobble")
        branch_break = get_spell("branch_break")
        plague_of_scavengers = get_spell("plague_of_scavengers")

        self.assertEqual(hands_of_lirisa.target_type, "self_or_other")
        self.assertEqual(hands_of_lirisa.effect_profile.get("gsl_spell_id"), 406001)
        self.assertEqual(hands_of_lirisa.effect_profile.get("castmod_a3"), "064167002")

        self.assertEqual(earth_meld.target_type, "self_or_other")
        self.assertEqual(earth_meld.effect_profile.get("gsl_spell_id"), 406002)
        self.assertEqual(earth_meld.effect_profile.get("castmod_a3"), "063182005")

        self.assertEqual(mesmerize.target_type, "single")
        self.assertEqual(mesmerize.effect_profile.get("gsl_spell_id"), 406003)
        self.assertEqual(mesmerize.effect_profile.get("castmod_a3"), "500012018")

        self.assertEqual(blend.target_type, "self")
        self.assertEqual(blend.effect_profile.get("gsl_spell_id"), 406004)
        self.assertEqual(blend.effect_profile.get("castmod_a3"), "013999017")

        self.assertEqual(breathe_water.target_type, "self")
        self.assertEqual(breathe_water.effect_profile.get("gsl_spell_id"), 406005)
        self.assertEqual(breathe_water.effect_profile.get("castmod_a3"), "200001014")

        self.assertEqual(water_purification.target_type, "self")
        self.assertEqual(water_purification.effect_profile.get("gsl_spell_id"), 406006)
        self.assertEqual(water_purification.effect_profile.get("castmod_a3"), "150015018")

        self.assertEqual(compost.target_type, "self")
        self.assertEqual(compost.effect_profile.get("gsl_spell_id"), 407001)
        self.assertEqual(compost.effect_profile.get("castmod_a3"), "050247003")

        self.assertEqual(swarm.target_type, "single")
        self.assertTrue(bool(swarm.effect_profile.get("disallow_self_target")))
        self.assertEqual(swarm.effect_profile.get("gsl_spell_id"), 407002)
        self.assertEqual(swarm.effect_profile.get("castmod_a3"), "061185011")

        self.assertEqual(haraweps_bonds.target_type, "single")
        self.assertTrue(bool(haraweps_bonds.effect_profile.get("disallow_self_target")))
        self.assertEqual(haraweps_bonds.effect_profile.get("gsl_spell_id"), 407003)
        self.assertEqual(haraweps_bonds.effect_profile.get("castmod_a3"), "060190015")

        self.assertEqual(awaken_forest.target_type, "self")
        self.assertEqual(awaken_forest.effect_profile.get("gsl_spell_id"), 407004)
        self.assertEqual(awaken_forest.effect_profile.get("castmod_a3"), "500010020")

        self.assertEqual(hobble.target_type, "single")
        self.assertTrue(bool(hobble.effect_profile.get("disallow_self_target")))
        self.assertEqual(hobble.effect_profile.get("gsl_spell_id"), 407005)
        self.assertEqual(hobble.effect_profile.get("castmod_a3"), "500015015")

        self.assertEqual(branch_break.target_type, "single")
        self.assertTrue(bool(branch_break.effect_profile.get("disallow_self_target")))
        self.assertEqual(branch_break.effect_profile.get("gsl_spell_id"), 407006)
        self.assertEqual(branch_break.effect_profile.get("castmod_a3"), "60183008")

        self.assertEqual(plague_of_scavengers.target_type, "single")
        self.assertTrue(bool(plague_of_scavengers.effect_profile.get("disallow_self_target")))
        self.assertEqual(plague_of_scavengers.effect_profile.get("gsl_spell_id"), 407010)
        self.assertEqual(plague_of_scavengers.effect_profile.get("castmod_a3"), "062190016")

    def test_all_structured_spells_define_required_fields(self):
        for spell_id, spell in SPELL_REGISTRY.items():
            with self.subTest(spell_id=spell_id):
                self.assertTrue(str(spell.spell_type or "").strip())
                self.assertTrue(str(spell.mana_type or "").strip())
                self.assertTrue(list(spell.allowed_professions or []))
                self.assertGreater(int(spell.safe_mana or 0), 0)
                self.assertGreater(int(spell.base_difficulty or 0), 0)


if __name__ == "__main__":
    unittest.main()