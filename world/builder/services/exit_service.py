from __future__ import annotations


BUILDER_EXIT_SERVICE_AVAILABLE = False

try:
    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object
    from typeclasses.exits import Exit
except Exception:  # pragma: no cover - optional builder dependency guard
    ObjectDB = None
    create_object = None
    Exit = None
else:
    BUILDER_EXIT_SERVICE_AVAILABLE = True


def _require_builder_runtime() -> None:
    if not BUILDER_EXIT_SERVICE_AVAILABLE:
        raise RuntimeError("Builder exit service is unavailable because the Evennia runtime could not be imported.")


def _require_room(room, label: str):
    if room is None:
        raise ValueError(f"{label} is required.")
    return room


def _require_direction(direction: object) -> str:
    if not isinstance(direction, str) or not direction.strip():
        raise ValueError("direction must be a non-empty string.")
    return direction.strip()


def _normalize_aliases(aliases: object) -> list[str]:
    if aliases is None:
        return []
    if not isinstance(aliases, (list, tuple)):
        raise ValueError("aliases must be a list of strings.")
    normalized: list[str] = []
    for raw_alias in aliases:
        alias = str(raw_alias or "").strip()
        if alias and alias not in normalized:
            normalized.append(alias)
    return normalized


def find_exit(source, direction):
    _require_builder_runtime()
    source_room = _require_room(source, "source")
    normalized_direction = _require_direction(direction).lower()

    for candidate in list(getattr(source_room, "contents", []) or []):
        if getattr(candidate, "destination", None) is None:
            continue
        if str(getattr(candidate, "key", "") or "").strip().lower() == normalized_direction:
            return candidate
    return None


def get_exit_by_id(exit_id):
    _require_builder_runtime()
    normalized_exit_id = str(exit_id or "").strip().lstrip("#")
    if not normalized_exit_id:
        raise ValueError("exit_id is required.")
    if not normalized_exit_id.isdigit():
        raise ValueError("exit_id must be a numeric object id.")
    return ObjectDB.objects.filter(id=int(normalized_exit_id), db_typeclass_path="typeclasses.exits.Exit").first()


def create_exit(source, direction, target):
    _require_builder_runtime()
    source_room = _require_room(source, "source")
    target_room = _require_room(target, "target")
    normalized_direction = _require_direction(direction)

    return create_object(
        Exit,
        key=normalized_direction,
        location=source_room,
        destination=target_room,
        home=source_room,
    )


def ensure_exit(source, direction, target):
    _require_builder_runtime()
    source_room = _require_room(source, "source")
    target_room = _require_room(target, "target")
    normalized_direction = _require_direction(direction)

    existing = find_exit(source_room, normalized_direction)
    if existing is None:
        return create_exit(source_room, normalized_direction, target_room), "created"

    existing_destination_id = getattr(getattr(existing, "destination", None), "id", None)
    target_id = getattr(target_room, "id", None)
    if existing_destination_id == target_id:
        return existing, "unchanged"

    existing.delete()
    return create_exit(source_room, normalized_direction, target_room), "replaced"


def delete_exit(source, direction):
    _require_builder_runtime()
    source_room = _require_room(source, "source")
    normalized_direction = _require_direction(direction)

    existing = find_exit(source_room, normalized_direction)
    if existing is None:
        raise ValueError("Exit not found.")

    existing.delete()
    return {"deleted_direction": normalized_direction, "source_id": getattr(source_room, "id", None)}


def update_exit(exit_id, *, direction=None, target=None, label=None, aliases=None):
    _require_builder_runtime()
    existing = get_exit_by_id(exit_id)
    if existing is None:
        raise ValueError("Exit not found.")

    if direction is not None:
        existing.key = _require_direction(direction)
    if target is not None:
        existing.destination = _require_room(target, "target")
    if label is not None:
        normalized_label = str(label or "").strip()
        existing.db.exit_display_name = normalized_label or None
    if aliases is not None:
        normalized_aliases = _normalize_aliases(aliases)
        existing.aliases.clear()
        for alias in normalized_aliases:
            existing.aliases.add(alias)
    existing.save()
    return existing