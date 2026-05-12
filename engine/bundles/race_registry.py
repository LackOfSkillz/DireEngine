from engine.bundles.registry import Registry


class RaceRegistry(Registry):
    required_fields = ("id", "display_name", "bundle_id", "tier")


race_registry = RaceRegistry("race_registry")