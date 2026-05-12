from engine.bundles.registry import Registry


class SpellCircleRegistry(Registry):
    required_fields = ("id", "display_name")


spell_circle_registry = SpellCircleRegistry("spell_circle_registry")