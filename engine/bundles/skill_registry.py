from engine.bundles.registry import Registry


class SkillRegistry(Registry):
    required_fields = ("id", "canon_id", "display_name", "group", "description")


skill_registry = SkillRegistry("skill_registry")