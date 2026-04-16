from __future__ import annotations


REQUIRED_SERVICES = [
    "room_service",
    "exit_service",
    "template_service",
    "spawn_service",
    "placement_service",
    "instance_service",
    "audit_service",
    "diff_history_service",
    "session_service",
    "map_importer",
    "map_exporter",
    "map_diff_service",
    "undo_service",
]


def is_builder_available() -> bool:
    try:
        import world.builder  # noqa: F401
    except ImportError:
        return False
    return True


def require_builder() -> None:
    if not is_builder_available():
        raise RuntimeError("Builder system not available")


def builder_services_available() -> bool:
    for service_name in REQUIRED_SERVICES:
        try:
            __import__(f"world.builder.services.{service_name}")
        except ImportError:
            return False
    return True


def builder_ready() -> bool:
    return is_builder_available() and builder_services_available()