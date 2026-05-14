import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from domain.learning.skill_aliases import list_aliases_for_skill, resolve_skill_alias


class SkillAliasTests(unittest.TestCase):
    def test_le_resolves_to_light_edge(self):
        self.assertEqual(resolve_skill_alias("le"), "light_edge")

    def test_light_edge_phrase_resolves(self):
        self.assertEqual(resolve_skill_alias("light edge"), "light_edge")

    def test_case_insensitive_resolution(self):
        self.assertEqual(resolve_skill_alias("LiGhT EdGe"), "light_edge")

    def test_parry_resolves_to_parry_ability(self):
        self.assertEqual(resolve_skill_alias("parry"), "parry_ability")

    def test_shield_resolves_to_shield_usage(self):
        self.assertEqual(resolve_skill_alias("shield usage"), "shield_usage")

    def test_moe_resolves_to_multiple_engaged_opponent(self):
        self.assertEqual(resolve_skill_alias("moe"), "multiple_engaged_opponent")

    def test_tm_resolves_to_targeted_magic(self):
        self.assertEqual(resolve_skill_alias("tm"), "targeted_magic")

    def test_unknown_alias_returns_none(self):
        self.assertIsNone(resolve_skill_alias("nonsense"))

    def test_blank_alias_returns_none(self):
        self.assertIsNone(resolve_skill_alias(""))

    def test_reverse_alias_listing_for_light_edge(self):
        aliases = list_aliases_for_skill("light_edge")
        self.assertIn("le", aliases)
        self.assertIn("light edge", aliases)
        self.assertIn("light edged", aliases)

    def test_reverse_alias_listing_for_parry_ability(self):
        aliases = list_aliases_for_skill("parry_ability")
        self.assertIn("parry", aliases)

    def test_reverse_alias_listing_for_shield_usage(self):
        aliases = list_aliases_for_skill("shield_usage")
        self.assertIn("shield", aliases)
