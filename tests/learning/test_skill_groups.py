import unittest

from domain.learning.skill_groups import CANONICAL_PULSE_GROUPS, get_skill_group_for_skill, get_skill_group_map


class SkillGroupTests(unittest.TestCase):
    def test_canonical_group_offsets_match_ten_group_cycle(self):
        self.assertEqual([group.offset_seconds for group in CANONICAL_PULSE_GROUPS], list(range(0, 200, 20)))

    def test_group_map_contains_all_offsets(self):
        group_map = get_skill_group_map()
        self.assertEqual(sorted(group_map.keys()), list(range(0, 200, 20)))

    def test_lookup_supports_runtime_aliases(self):
        self.assertEqual(get_skill_group_for_skill("shield").offset_seconds, 0)
        self.assertEqual(get_skill_group_for_skill("light edge").offset_seconds, 20)
        self.assertEqual(get_skill_group_for_skill("polearm").offset_seconds, 60)

    def test_lookup_finds_defense_group(self):
        group = get_skill_group_for_skill("parry")
        self.assertIsNotNone(group)
        self.assertEqual(group.offset_seconds, 20)

    def test_group_9_is_reserved_empty(self):
        self.assertEqual(CANONICAL_PULSE_GROUPS[-1].index, 9)
        self.assertEqual(CANONICAL_PULSE_GROUPS[-1].skill_ids, ())


if __name__ == "__main__":
    unittest.main()