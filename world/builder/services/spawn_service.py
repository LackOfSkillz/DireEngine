from __future__ import annotations


BUILDER_SPAWN_SERVICE_AVAILABLE = False

try:
    from evennia.utils.create import create_object
    from typeclasses.objects import Object

    from .audit_service import log_audit_event
    from .template_service import BUILDER_TEMPLATE_SERVICE_AVAILABLE, require_template
except Exception:  # pragma: no cover - optional builder dependency guard
    create_object = None
    Object = None
    log_audit_event = None
    require_template = None
else:
    BUILDER_SPAWN_SERVICE_AVAILABLE = BUILDER_TEMPLATE_SERVICE_AVAILABLE


def _require_builder_runtime() -> None:
    if not BUILDER_SPAWN_SERVICE_AVAILABLE:
        raise RuntimeError("Builder spawn service is unavailable because the Evennia runtime could not be imported.")


def _require_location(location):
    if location is None:
        raise ValueError("location is required.")
    return location


def _apply_template_fields(obj, template: dict, location) -> None:
    obj.key = str(template["name"])
    obj.db.desc = str(template["description"])
    obj.db.template_id = template["template_id"]
    obj.db.builder_spawned = True
    obj.db.builder_attributes = dict(template.get("attributes", {}) or {})
    obj.db.builder_flags = list(template.get("flags", []) or [])
    obj.db.builder_item_kind = str(template.get("item_kind", "") or "").strip().lower()
    obj.db.weight = float(template.get("weight", 0.0) or 0.0)
    obj.db.value = float(template.get("value", 0.0) or 0.0)
    obj.location = location
    obj.home = obj.home or location


def _is_guard_template(template: dict) -> bool:
    tags = {str(tag or "").strip().lower() for tag in list(template.get("tags") or [])}
    return "guard" in tags or "guard_validated" in tags


def create_item_instance(template: dict, location):
    _require_builder_runtime()
    target_location = _require_location(location)
    obj = create_object(Object, key=str(template["name"]), location=target_location, home=target_location)
    _apply_template_fields(obj, template, target_location)
    obj.db.is_npc = False
    obj.db.is_container = str(template.get("item_kind", "") or "").strip().lower() == "container"
    return obj


def create_npc_instance(template: dict, location):
    _require_builder_runtime()
    target_location = _require_location(location)
    if _is_guard_template(template):
        from world.systems import guards

        obj = create_object("typeclasses.npcs.GuardNPC", key=str(template["name"]), location=target_location, home=target_location)
        guards._assign_template_to_guard(obj, template, target_location)
        obj.db.builder_spawned = True
    else:
        obj = create_object(Object, key=str(template["name"]), location=target_location, home=target_location)
        _apply_template_fields(obj, template, target_location)
        obj.db.is_npc = True
    return obj


def spawn_from_template(template_id: str, location):
    _require_builder_runtime()
    target_location = _require_location(location)
    template = require_template(template_id)
    template_type = str(template.get("type", "")).strip().lower()

    if template_type == "item":
        obj = create_item_instance(template, target_location)
    elif template_type == "npc":
        obj = create_npc_instance(template, target_location)
    else:
        raise ValueError(f"Unsupported template type: {template_type}")

    if getattr(obj, "location", None) != target_location:
        raise ValueError("Spawned object location does not match requested location.")
    if str(getattr(getattr(obj, "db", None), "template_id", "") or "") != template["template_id"]:
        raise ValueError("Spawned object template_id does not match requested template.")

    log_audit_event(
        "spawn",
        getattr(obj, "id", 0),
        {
            "template_id": template["template_id"],
            "location_id": getattr(target_location, "id", None),
            "type": template_type,
        },
    )
    return obj


def spawn_from_template_result(template_id: str, location) -> dict:
    obj = spawn_from_template(template_id, location)
    return {
        "id": getattr(obj, "id", None),
        "key": str(getattr(obj, "key", "") or ""),
        "template_id": str(getattr(getattr(obj, "db", None), "template_id", "") or ""),
        "location_id": getattr(location, "id", None),
        "type": str(require_template(template_id).get("type", "") or ""),
        "zone_id": str(getattr(getattr(obj, "db", None), "zone_id", "") or getattr(getattr(obj, "db", None), "zone", "") or ""),
    }