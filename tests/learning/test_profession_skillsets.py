import unittest

from world.professions.professions import (
    get_profession_skillset_placement,
    get_profession_skillset_tier,
    get_skillset_tier_for_skill,
)


class ProfessionSkillsetTests(unittest.TestCase):
    def test_cleric_and_empath_match_canonical_skillset_layouts(self):
        cleric = get_profession_skillset_placement("cleric")
        empath = get_profession_skillset_placement("empath")
        self.assertEqual(cleric["primary"], ("magic",))
        self.assertEqual(cleric["secondary"], ("lore", "weapons"))
        self.assertEqual(cleric["tertiary"], ("survival", "armor"))
        self.assertEqual(empath["primary"], ("lore",))
        self.assertEqual(empath["secondary"], ("magic", "survival"))
        self.assertEqual(empath["tertiary"], ("weapons", "armor"))

    def test_profession_skillset_tier_normalizes_combat_to_weapons(self):
        self.assertEqual(get_profession_skillset_tier("ranger", "combat"), "secondary")
        self.assertEqual(get_profession_skillset_tier("paladin", "armor"), "primary")
        self.assertEqual(get_profession_skillset_tier("necromancer", "magic"), "secondary")

    def test_skill_name_lookup_supports_repo_specific_names(self):
        self.assertEqual(get_skillset_tier_for_skill("warrior_mage", skill_name="light_edge"), "secondary")
        self.assertEqual(get_skillset_tier_for_skill("paladin", skill_name="conviction"), "primary")
        self.assertEqual(get_skillset_tier_for_skill("thief", skill_name="thievery"), "primary")


if __name__ == "__main__":
    unittest.main()