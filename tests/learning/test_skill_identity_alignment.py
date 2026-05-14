import os
import re
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from domain.learning.skill_aliases import SKILL_ALIASES, resolve_skill_alias
from domain.learning.skill_groups import CANONICAL_PULSE_GROUPS
from typeclasses.characters import SKILL_REGISTRY


class SkillIdentityAlignmentTests(unittest.TestCase):
    def test_skill_aliases_target_real_skills(self):
        registry_keys = set(SKILL_REGISTRY.keys())
        drift = set(SKILL_ALIASES.values()) - registry_keys
        self.assertFalse(drift, f"Aliases reference non-existent skills: {sorted(drift)}")

    def test_pulse_groups_reference_real_skills(self):
        registry_keys = set(SKILL_REGISTRY.keys())
        for group in CANONICAL_PULSE_GROUPS:
            drift = set(group.skill_ids) - registry_keys
            self.assertFalse(drift, f"Group {group.index} ({group.name}) references non-existent skills: {sorted(drift)}")

    def test_every_registry_entry_has_display_name(self):
        missing = [key for key, meta in SKILL_REGISTRY.items() if not str(meta.get("display_name") or "").strip()]
        self.assertFalse(missing, f"Registry entries missing display_name: {sorted(missing)}")

    def test_every_registry_entry_has_canonical_key_format(self):
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        invalid = [key for key in SKILL_REGISTRY if not pattern.match(key)]
        self.assertFalse(invalid, f"Invalid key format: {sorted(invalid)}")

    def test_group_9_is_reserved_empty(self):
        group_9 = next(group for group in CANONICAL_PULSE_GROUPS if group.index == 9)
        self.assertEqual(group_9.name, "Guild-Specific")
        self.assertEqual(group_9.skill_ids, ())

    def test_non_guild_locked_registry_entries_are_grouped(self):
        all_grouped = set()
        for group in CANONICAL_PULSE_GROUPS:
            all_grouped.update(group.skill_ids)

        orphaned = []
        for key, meta in SKILL_REGISTRY.items():
            if meta.get("visibility") == "guild_locked":
                continue
            if key not in all_grouped:
                orphaned.append(key)

        self.assertFalse(orphaned, f"Non-guild-locked skills not in any pulse group: {sorted(orphaned)}")

    def test_defense_skills_exist_with_defense_category(self):
        for key in ("shield_usage", "parry_ability", "multiple_engaged_opponent"):
            self.assertIn(key, SKILL_REGISTRY)
            self.assertEqual(SKILL_REGISTRY[key]["category"], "defense")

    def test_defense_aliases_resolve_to_dedicated_skills(self):
        self.assertEqual(resolve_skill_alias("parry"), "parry_ability")
        self.assertEqual(resolve_skill_alias("shield"), "shield_usage")
        self.assertEqual(resolve_skill_alias("moe"), "multiple_engaged_opponent")

    def test_defense_skills_live_in_group_zero(self):
        defense_group = next(group for group in CANONICAL_PULSE_GROUPS if group.index == 0)
        self.assertIn("shield_usage", defense_group.skill_ids)
        self.assertIn("multiple_engaged_opponent", defense_group.skill_ids)
        edged_group = next(group for group in CANONICAL_PULSE_GROUPS if group.index == 1)
        self.assertIn("parry_ability", edged_group.skill_ids)


if __name__ == "__main__":
    unittest.main()