from engine.bundles.registry import Registry


class ProfessionRegistry(Registry):
    required_fields = ("id", "display_name", "bundle_id", "tier")


profession_registry = ProfessionRegistry("profession_registry")