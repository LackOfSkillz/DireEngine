import unittest
from types import SimpleNamespace

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import Character
from world.professions.professions import (
    get_profession_profile,
    get_profession_skillset_placement,
    get_profession_skillset_tier,
    get_skillset_tier_for_skill,
)


class ProfessionSkillsetTests(unittest.TestCase):
    def test_empath_profile_preserves_audited_identity_surface(self):
        profile = get_profession_profile("empath")

        self.assertEqual(profile["display"], "Empath")
        self.assertEqual(profile["guild_tag"], "empath_guildhall")
        self.assertEqual(profile["primary_skillsets"], ("lore",))
        self.assertEqual(profile["secondary_skillsets"], ("magic", "survival"))

    def test_cleric_and_empath_match_canonical_skillset_layouts(self):
        cleric = get_profession_skillset_placement("cleric")
        empath = get_profession_skillset_placement("empath")
        self.assertEqual(cleric["primary"], ("magic",))
        self.assertEqual(cleric["secondary"], ("lore", "weapons"))
        self.assertEqual(cleric["tertiary"], ("survival", "armor"))
        self.assertEqual(empath["primary"], ("lore",))
        self.assertEqual(empath["secondary"], ("magic", "survival"))
        self.assertEqual(empath["tertiary"], ("weapons", "armor"))

    def test_ranger_profile_uses_canonical_primary_magic_axis(self):
        ranger = get_profession_skillset_placement("ranger")

        self.assertEqual(ranger["primary"], ("magic",))
        self.assertEqual(ranger["secondary"], ("weapons", "armor"))
        self.assertEqual(ranger["tertiary"], ("survival", "lore"))

    def test_profession_skillset_tier_normalizes_combat_to_weapons(self):
        self.assertEqual(get_profession_skillset_tier("ranger", "combat"), "secondary")
        self.assertEqual(get_profession_skillset_tier("paladin", "armor"), "primary")
        self.assertEqual(get_profession_skillset_tier("necromancer", "magic"), "secondary")

    def test_skill_name_lookup_supports_repo_specific_names(self):
        self.assertEqual(get_skillset_tier_for_skill("warrior_mage", skill_name="light_edge"), "secondary")
        self.assertEqual(get_skillset_tier_for_skill("paladin", skill_name="conviction"), "primary")
        self.assertEqual(get_skillset_tier_for_skill("thief", skill_name="thievery"), "primary")

    def test_empath_exp_skill_tier_uses_skill_specific_identity_overrides(self):
        caller = SimpleNamespace(db=SimpleNamespace(profession="empath"))
        caller.get_skill_metadata = lambda skill_name: Character.get_skill_metadata(caller, skill_name)

        self.assertEqual(Character.get_exp_skillset_tier(caller, "empathy"), "primary")
        self.assertEqual(Character.get_exp_skillset_tier(caller, "first_aid"), "secondary")
        self.assertEqual(Character.get_exp_skillset_tier(caller, "scholarship"), "secondary")

    def test_ranger_exp_skill_tier_and_weights_follow_magic_primary_axis(self):
        caller = SimpleNamespace(db=SimpleNamespace(profession="ranger"))
        caller.get_skill_metadata = lambda skill_name: Character.get_skill_metadata(caller, skill_name)
        caller.get_profession = lambda: "ranger"

        self.assertEqual(Character.get_exp_skillset_tier(caller, "attunement"), "primary")
        self.assertEqual(Character.get_exp_skillset_tier(caller, "outdoorsmanship"), "tertiary")
        self.assertGreater(Character.get_skill_weight(caller, "magic"), Character.get_skill_weight(caller, "survival"))

    def test_empath_maps_to_life_mana_realm(self):
        caller = SimpleNamespace(get_profession=lambda: "empath")

        self.assertEqual(Character.get_mana_realm(caller), "life")


if __name__ == "__main__":
    unittest.main()