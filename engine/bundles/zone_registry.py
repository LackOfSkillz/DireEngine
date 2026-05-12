from engine.bundles.registry import Registry


class ZoneRegistry(Registry):
    required_fields = ("id", "display_name", "bundle_id", "tier")


zone_registry = ZoneRegistry("zone_registry")