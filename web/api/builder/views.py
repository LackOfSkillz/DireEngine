from __future__ import annotations

import logging

from django.http import JsonResponse
from evennia.utils.search import search_object

from server.systems import item_loader
from server.systems import npc_loader
from server.systems import zone_room_item_assignments
from server.systems import zone_room_npc_assignments
from web.character_helpers import parse_request_data
from world.builder.capabilities import builder_ready
from world.builder.permissions import require_builder


logger = logging.getLogger(__name__)
BUILDER_API_AVAILABLE = builder_ready()
LOCAL_BUILDER_REMOTE_ADDRS = {"127.0.0.1", "::1", "localhost"}

if BUILDER_API_AVAILABLE:
    import world.builder.services.audit_service as audit_service
    import world.builder.services.diff_history_service as diff_history_service
    import world.builder.services.exit_service as exit_service
    import world.builder.services.instance_service as instance_service
    import world.builder.services.map_diff_service as map_diff_service
    import world.builder.services.map_exporter as map_exporter
    import world.builder.services.map_importer as map_importer
    import world.builder.services.placement_service as placement_service
    import world.builder.services.room_service as room_service
    import world.builder.services.session_service as session_service
    import world.builder.services.spawn_service as spawn_service
    import world.builder.services.template_service as template_service
    import world.builder.services.undo_service as undo_service
    import world.builder.services.zone_service as zone_service


def builder_not_available_response():
    return {"ok": False, "error": "Builder system not available"}


def _success(data: dict, status: int = 200):
    return JsonResponse({"ok": True, "data": data}, status=status)


def _failure(error: str, status: int = 400):
    return JsonResponse({"ok": False, "error": str(error)}, status=status)


def _parse_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _get_request_username(request) -> str | None:
    user = getattr(request, "user", None)
    username = str(getattr(user, "username", "") or "").strip()
    return username or None


def _get_optional_session(payload: dict | None):
    if not isinstance(payload, dict):
        return None
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        return None
    session = session_service.get_session(session_id)
    if session is None:
        raise ValueError("invalid session_id")
    return session


def _get_optional_group_id(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    group_id = str(payload.get("group_id") or "").strip()
    return group_id or None


def _require_builder_api():
    if not BUILDER_API_AVAILABLE:
        return JsonResponse(builder_not_available_response(), status=503)
    return None


def _is_local_builder_request(request) -> bool:
    remote_addr = str(request.META.get("REMOTE_ADDR") or "").strip()
    local_header = str(request.headers.get("X-Builder-Local") or "").strip().lower()
    return remote_addr in LOCAL_BUILDER_REMOTE_ADDRS and local_header == "1"


def _require_builder_permission(request):
    if _is_local_builder_request(request):
        return None
    try:
        require_builder(getattr(request, "user", None))
    except PermissionError:
        return JsonResponse({"ok": False, "error": "permission_denied"}, status=403)
    return None


def list_templates(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    try:
        templates = template_service.list_templates()
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"templates": templates})


def get_template(request, template_id):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    try:
        template = template_service.get_template(template_id)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    if template is None:
        return _failure("not_found", status=404)
    return _success({"template": template})


def create_template(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    try:
        template = template_service.register_template(payload)
    except ValueError as exc:
        return _failure(str(exc), status=400)

    logger.info("Builder template created: template_id=%s type=%s", template.get("template_id"), template.get("type"))
    return _success({"template": template}, status=201)


def update_template(request, template_id):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    updates = parse_request_data(request)
    try:
        template = template_service.update_template(template_id, updates)
    except ValueError as exc:
        return _failure(str(exc), status=400)

    logger.info("Builder template updated: template_id=%s", template_id)
    return _success({"template": template})


def search_templates(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    query = request.GET.get("q", "")
    template_type = request.GET.get("type") or None
    try:
        templates = template_service.search_templates(query, template_type=template_type)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"templates": templates})


def list_zones(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    try:
        zones = zone_service.list_zones()
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"zones": zones})


def create_zone(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    try:
        zone = zone_service.create_zone(payload.get("zone_id"), payload.get("name"))
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"zone": zone}, status=201)


def list_npc_templates(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied
    try:
        templates = template_service.list_templates(template_type="npc")
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"templates": templates})


def list_item_templates(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied
    try:
        templates = template_service.list_templates(template_type="item")
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"templates": templates})


def spawn_from_template(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    template_id = str(payload.get("template_id") or "").strip()
    location_id = payload.get("location_id")

    if not template_id:
        return _failure("template_id is required.", status=400)
    if location_id in (None, ""):
        return _failure("location_id is required.", status=400)

    lookup_value = f"#{int(location_id)}" if str(location_id).strip().isdigit() else str(location_id).strip()
    matches = search_object(lookup_value)
    location = matches[0] if matches else None
    if location is None:
        return _failure("invalid location", status=404)

    try:
        result = spawn_service.spawn_from_template_result(template_id, location)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"spawn": result}, status=201)


def move_instance(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    object_id = payload.get("object_id")
    destination_id = payload.get("destination_id")
    relation = str(payload.get("relation") or "in").strip().lower() or "in"

    if object_id in (None, ""):
        return _failure("object_id is required.", status=400)
    if destination_id in (None, ""):
        return _failure("destination_id is required.", status=400)

    object_lookup = f"#{int(object_id)}" if str(object_id).strip().isdigit() else str(object_id).strip()
    destination_lookup = f"#{int(destination_id)}" if str(destination_id).strip().isdigit() else str(destination_id).strip()
    object_matches = search_object(object_lookup)
    destination_matches = search_object(destination_lookup)
    obj = object_matches[0] if object_matches else None
    destination = destination_matches[0] if destination_matches else None

    if obj is None:
        return _failure("invalid object", status=404)
    if destination is None:
        return _failure("invalid destination", status=404)

    try:
        result = placement_service.move_with_relation(obj, destination, relation=relation)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"move": result})


def delete_instance(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    object_id = payload.get("object_id")
    if object_id in (None, ""):
        return _failure("object_id is required.", status=400)

    try:
        result = instance_service.delete_instance_by_id(object_id)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return JsonResponse({"ok": True, "deleted_id": result.get("deleted_id")}, status=200)


def import_map(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    map_data = payload.get("map") if isinstance(payload, dict) else None
    mode = str((payload.get("mode") if isinstance(payload, dict) else "safe") or "safe").strip().lower() or "safe"
    if map_data is None:
        return _failure("map is required.", status=400)

    try:
        result = map_importer.import_map(map_data, mode=mode)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"result": result})


def apply_diff(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    diff = payload.get("diff") if isinstance(payload, dict) else None
    preview_value = payload.get("preview", False) if isinstance(payload, dict) else False
    if diff is None:
        return _failure("diff is required.", status=400)

    preview = _parse_bool(preview_value)
    try:
        session = _get_optional_session(payload if isinstance(payload, dict) else None)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    group_id = _get_optional_group_id(payload if isinstance(payload, dict) else None)
    username = _get_request_username(request)

    try:
        result = map_diff_service.apply_diff(
            diff,
            preview=preview,
            session_id=session.get("session_id") if isinstance(session, dict) else None,
            group_id=group_id,
            username=username,
        )
    except map_diff_service.DiffApplyError as exc:
        error_payload = {
            "ok": False,
            "error": str(exc),
            "failed_operation_index": exc.failed_operation_index,
            "failed_operation_id": exc.failed_operation_id,
            "failed_operation": exc.failed_operation,
        }
        if exc.conflicts:
            error_payload["conflicts"] = list(exc.conflicts)
        return JsonResponse(error_payload, status=400)
    except ValueError as exc:
        return _failure(str(exc), status=400)

    if result.get("preview"):
        logger.info("Diff preview validated: %s operations", result.get("validated_operations", 0))
    else:
        logger.info("Diff applied: %s operations", result.get("applied", 0))
    return _success({"result": result})


def save_all(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    diff = payload.get("diff") if isinstance(payload, dict) else None
    if diff is None:
        return _failure("diff is required.", status=400)

    try:
        session = _get_optional_session(payload if isinstance(payload, dict) else None)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    username = _get_request_username(request)

    try:
        result = map_diff_service.apply_diff(
            diff,
            preview=False,
            session_id=session.get("session_id") if isinstance(session, dict) else None,
            username=username,
        )
    except map_diff_service.DiffApplyError as exc:
        error_payload = {
            "ok": False,
            "error": str(exc),
            "failed_operation_index": exc.failed_operation_index,
            "failed_operation_id": exc.failed_operation_id,
            "failed_operation": exc.failed_operation,
        }
        if exc.conflicts:
            error_payload["conflicts"] = list(exc.conflicts)
        return JsonResponse(error_payload, status=400)
    except ValueError as exc:
        return _failure(str(exc), status=400)

    logger.info("Batch save applied: %s operations", result.get("applied", 0))
    return _success({"result": result})


def apply_undo(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    undo_diff = payload.get("undo_diff") if isinstance(payload, dict) else None
    if undo_diff is None:
        return _failure("undo_diff is required.", status=400)
    if _parse_bool(payload.get("preview", False) if isinstance(payload, dict) else False):
        return _failure("Undo does not support preview mode.", status=400)

    try:
        result = undo_service.apply_undo(undo_diff)
    except map_diff_service.DiffApplyError as exc:
        error_payload = {
            "ok": False,
            "error": str(exc),
            "failed_operation_index": exc.failed_operation_index,
            "failed_operation_id": exc.failed_operation_id,
            "failed_operation": exc.failed_operation,
        }
        if exc.conflicts:
            error_payload["conflicts"] = list(exc.conflicts)
        return JsonResponse(error_payload, status=400)
    except ValueError as exc:
        return _failure(str(exc), status=400)

    audit_service.log_audit_event(
        "undo_apply",
        0,
        {
            "area_id": str((undo_diff or {}).get("area_id") or ""),
            "applied": int(result.get("applied", 0) or 0),
            "operation_ids": [str(op.get("id") or f"auto-{index}") for index, op in enumerate((undo_diff or {}).get("operations") or []) if isinstance(op, dict)],
        },
    )
    return JsonResponse({"ok": True, "result": result}, status=200)


def apply_redo(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    diff = payload.get("diff") if isinstance(payload, dict) else None
    if diff is None:
        return _failure("diff is required.", status=400)

    try:
        result = undo_service.apply_redo(diff)
    except map_diff_service.DiffApplyError as exc:
        error_payload = {
            "ok": False,
            "error": str(exc),
            "failed_operation_index": exc.failed_operation_index,
            "failed_operation_id": exc.failed_operation_id,
            "failed_operation": exc.failed_operation,
        }
        if exc.conflicts:
            error_payload["conflicts"] = list(exc.conflicts)
        return JsonResponse(error_payload, status=400)
    except ValueError as exc:
        return _failure(str(exc), status=400)

    audit_service.log_audit_event(
        "redo_apply",
        0,
        {
            "area_id": str((diff or {}).get("area_id") or ""),
            "applied": int(result.get("applied", 0) or 0),
            "operation_ids": [str(op.get("id") or f"auto-{index}") for index, op in enumerate((diff or {}).get("operations") or []) if isinstance(op, dict)],
        },
    )
    return JsonResponse({"ok": True, "result": result}, status=200)


def get_diff_history(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    area_id = str(request.GET.get("area_id") or "").strip()
    limit_value = request.GET.get("limit")

    try:
        entries = diff_history_service.load_history()
        if area_id:
            entries = [entry for entry in entries if str(entry.get("area_id") or "") == area_id]
        entries = sorted(entries, key=lambda entry: float(entry.get("timestamp", 0.0) or 0.0), reverse=True)
        if limit_value not in (None, ""):
            limit = int(limit_value)
            if limit < 0:
                raise ValueError("limit must be >= 0")
            entries = entries[:limit]
    except ValueError as exc:
        return _failure(str(exc), status=400)

    return JsonResponse({"ok": True, "history": entries}, status=200)


def get_audit_log(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    object_id = request.GET.get("object_id")
    action = request.GET.get("action")
    limit_value = request.GET.get("limit")
    start_ts = request.GET.get("start_ts")
    end_ts = request.GET.get("end_ts")

    try:
        limit = int(limit_value) if limit_value not in (None, "") else None
        if object_id not in (None, ""):
            entries = audit_service.get_audit_for_object(object_id, limit=limit)
        elif action not in (None, ""):
            entries = audit_service.get_audit_by_action(action, limit=limit)
        elif start_ts not in (None, "") and end_ts not in (None, ""):
            entries = audit_service.get_audit_in_range(start_ts, end_ts, limit=limit)
        else:
            entries = audit_service.load_audit_log(limit=limit)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"entries": entries})


def export_map(request, area_id):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    try:
        exported = map_exporter.export_map(area_id)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"map": exported})


def update_room(request, room_id):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    room = room_service.get_room(room_id)
    if room is None:
        return _failure("invalid room_id", status=404)

    try:
        updated = room_service.update_room(room, payload)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"room": room_service.normalize_room(updated)})


def assign_room_npc(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    room_id = str(payload.get("room_id") or "").strip()
    zone_id = str(payload.get("zone_id") or "").strip()
    npc_id = str(payload.get("npc_id") or "").strip()
    if not room_id:
        return _failure("room_id is required", status=400)
    if not npc_id:
        return _failure("npc_id is required", status=400)

    npc_records = npc_loader.load_all_npcs()
    if npc_id not in npc_records:
        return _failure("invalid npc_id", status=404)

    try:
        zone_payload, room_payload = zone_room_npc_assignments.resolve_builder_zone_room(room_id, zone_id=zone_id)
        next_npc_ids = list(room_payload.get("npcs") or [])
        if npc_id not in next_npc_ids:
            next_npc_ids.append(npc_id)
        updated_zone, updated_room = zone_room_npc_assignments.update_room_npcs(
            room_id,
            next_npc_ids,
            zone_id=zone_payload.get("zone_id") or zone_id,
        )
    except ValueError as exc:
        return _failure(str(exc), status=404)

    return _success({"zone": updated_zone, "room": updated_room, "npc": npc_records.get(npc_id)})


def remove_room_npc(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    room_id = str(payload.get("room_id") or "").strip()
    zone_id = str(payload.get("zone_id") or "").strip()
    npc_id = str(payload.get("npc_id") or "").strip()
    if not room_id:
        return _failure("room_id is required", status=400)
    if not npc_id:
        return _failure("npc_id is required", status=400)

    try:
        zone_payload, room_payload = zone_room_npc_assignments.resolve_builder_zone_room(room_id, zone_id=zone_id)
        next_npc_ids = [candidate for candidate in list(room_payload.get("npcs") or []) if candidate != npc_id]
        updated_zone, updated_room = zone_room_npc_assignments.update_room_npcs(
            room_id,
            next_npc_ids,
            zone_id=zone_payload.get("zone_id") or zone_id,
        )
    except ValueError as exc:
        return _failure(str(exc), status=404)

    return _success({"zone": updated_zone, "room": updated_room, "removed_npc_id": npc_id})


def assign_item_to_room(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    room_id = str(payload.get("room_id") or "").strip()
    zone_id = str(payload.get("zone_id") or "").strip()
    item_id = str(payload.get("item_id") or "").strip()
    count = int(payload.get("count") or 0)
    if not room_id:
        return _failure("room_id is required", status=400)
    if not item_id:
        return _failure("item_id is required", status=400)
    if count <= 0:
        return _failure("count must be greater than 0", status=400)

    item_records = item_loader.load_all_items()
    item_record = item_records.get(item_id)
    if item_record is None:
        return _failure("invalid item_id", status=404)

    try:
        zone_payload, room_payload = zone_room_item_assignments.resolve_builder_zone_room(room_id, zone_id=zone_id)
        next_items = list(room_payload.get("items") or [])
        merged = False
        for entry in next_items:
            if str((entry or {}).get("id") or "").strip() != item_id:
                continue
            entry["count"] = max(0, int(entry.get("count") or 0)) + count
            merged = True
            break
        if not merged:
            next_entry = {"id": item_id, "count": count}
            if str(item_record.get("category") or "").strip().lower() == "container":
                next_entry["items"] = []
            next_items.append(next_entry)
        updated_zone, updated_room = zone_room_item_assignments.update_room_items(
            room_id,
            next_items,
            zone_id=zone_payload.get("zone_id") or zone_id,
        )
    except ValueError as exc:
        return _failure(str(exc), status=404)

    return _success({"zone": updated_zone, "room": updated_room, "item": item_record})


def remove_item_from_room(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    room_id = str(payload.get("room_id") or "").strip()
    zone_id = str(payload.get("zone_id") or "").strip()
    item_id = str(payload.get("item_id") or "").strip()
    count = int(payload.get("count") or 1)
    if not room_id:
        return _failure("room_id is required", status=400)
    if not item_id:
        return _failure("item_id is required", status=400)
    if count <= 0:
        return _failure("count must be greater than 0", status=400)

    try:
        zone_payload, room_payload = zone_room_item_assignments.resolve_builder_zone_room(room_id, zone_id=zone_id)
        next_items = []
        found_item = False
        for entry in list(room_payload.get("items") or []):
            normalized_entry = dict(entry or {})
            if str(normalized_entry.get("id") or "").strip() != item_id:
                next_items.append(normalized_entry)
                continue
            found_item = True
            next_count = max(0, int(normalized_entry.get("count") or 0) - count)
            if next_count > 0:
                normalized_entry["count"] = next_count
                next_items.append(normalized_entry)
        if not found_item:
            return _failure("item not assigned to room", status=404)
        updated_zone, updated_room = zone_room_item_assignments.update_room_items(
            room_id,
            next_items,
            zone_id=zone_payload.get("zone_id") or zone_id,
        )
    except ValueError as exc:
        return _failure(str(exc), status=404)

    return _success({"zone": updated_zone, "room": updated_room, "removed_item_id": item_id, "count": count})


def update_room_item_count(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    room_id = str(payload.get("room_id") or "").strip()
    zone_id = str(payload.get("zone_id") or "").strip()
    item_id = str(payload.get("item_id") or "").strip()
    count = int(payload.get("count") or 0)
    if not room_id:
        return _failure("room_id is required", status=400)
    if not item_id:
        return _failure("item_id is required", status=400)
    if count < 0:
        return _failure("count cannot be negative", status=400)

    item_records = item_loader.load_all_items()
    item_record = item_records.get(item_id)
    if item_record is None:
        return _failure("invalid item_id", status=404)

    try:
        zone_payload, room_payload = zone_room_item_assignments.resolve_builder_zone_room(room_id, zone_id=zone_id)
        next_items = []
        found_item = False
        for entry in list(room_payload.get("items") or []):
            normalized_entry = dict(entry or {})
            if str(normalized_entry.get("id") or "").strip() != item_id:
                next_items.append(normalized_entry)
                continue
            found_item = True
            if count > 0:
                normalized_entry["count"] = count
                next_items.append(normalized_entry)
        if not found_item and count > 0:
            next_entry = {"id": item_id, "count": count}
            if str(item_record.get("category") or "").strip().lower() == "container":
                next_entry["items"] = []
            next_items.append(next_entry)
        updated_zone, updated_room = zone_room_item_assignments.update_room_items(
            room_id,
            next_items,
            zone_id=zone_payload.get("zone_id") or zone_id,
        )
    except ValueError as exc:
        return _failure(str(exc), status=404)

    return _success({"zone": updated_zone, "room": updated_room, "item": item_record, "count": count})


def create_exit(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    source_id = payload.get("source_id")
    target_id = payload.get("target_id")
    direction = str(payload.get("direction") or "").strip()

    if not direction:
        return _failure("direction is required.", status=400)

    source = room_service.get_room(source_id)
    target = room_service.get_room(target_id)
    if source is None:
        return _failure("invalid source_id", status=404)
    if target is None:
        return _failure("invalid target_id", status=404)
    if getattr(source, "id", None) == getattr(target, "id", None):
        return _failure("self-referencing exits are not allowed.", status=400)

    try:
        exit_obj, action = exit_service.ensure_exit(source, direction, target)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success(
        {
            "exit": {
                "id": getattr(exit_obj, "id", None),
                "direction": str(getattr(exit_obj, "key", "") or ""),
                "source_id": source_id,
                "target_id": target_id,
                "action": action,
            }
        }
    )


def delete_exit(request):
    unavailable = _require_builder_api()
    if unavailable is not None:
        return unavailable
    denied = _require_builder_permission(request)
    if denied is not None:
        return denied

    payload = parse_request_data(request)
    source_id = payload.get("source_id")
    direction = str(payload.get("direction") or "").strip()

    if not direction:
        return _failure("direction is required.", status=400)

    source = room_service.get_room(source_id)
    if source is None:
        return _failure("invalid source_id", status=404)

    try:
        result = exit_service.delete_exit(source, direction)
    except ValueError as exc:
        return _failure(str(exc), status=400)
    return _success({"exit": result})