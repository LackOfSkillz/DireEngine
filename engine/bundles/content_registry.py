from engine.bundles.registry import Registry


class ContentRegistry(Registry):
    required_fields = ("id", "content_type")


content_registry = ContentRegistry("content_registry")