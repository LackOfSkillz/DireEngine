from engine.bundles.registry import Registry


class TradeRegistry(Registry):
    required_fields = ("id", "display_name", "bundle_id", "tier")


trade_registry = TradeRegistry("trade_registry")