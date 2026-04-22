from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, request
from django.db import close_old_connections, connections


HOST = "127.0.0.1"
PORT = 7777
ALLOWED_REMOTE_ADDRESSES = {"127.0.0.1", "::1", "localhost"}
ALLOWED_ORIGINS = {
    "http://127.0.0.1:4001",
    "http://localhost:4001",
}

GODOT_EXE = Path(
    r"C:\Users\gary\AppData\Local\Microsoft\WinGet\Packages\GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe\Godot_v4.6.2-stable_win64.exe"
)
GODOT_PROJECT = Path(r"C:\Users\gary\dragonsire\godot\DireMudClient\project.godot")
GODOT_LAUNCH_LOG = Path(r"C:\Users\gary\dragonsire\tools\builder_launcher\godot_launch.log")
REPO_ROOT = GODOT_PROJECT.parent.parent.parent


logging.basicConfig(level=logging.INFO, format="[builder-launcher] %(message)s")
logger = logging.getLogger("builder_launcher")

app = Flask(__name__)
_DJANGO_READY = False


def _remote_address() -> str:
    return str(request.remote_addr or "").strip()


def _is_local_request() -> bool:
    return _remote_address() in ALLOWED_REMOTE_ADDRESSES


def _apply_cors_headers(response):
    origin = str(request.headers.get("Origin") or "").strip()
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.before_request
def _reject_non_local_requests():
    if request.method == "OPTIONS":
        return _apply_cors_headers(jsonify({"ok": True}))
    if not _is_local_request():
        logger.warning("Rejected non-local request from %s", _remote_address())
        return _apply_cors_headers(jsonify({"ok": False, "error": "localhost_only"})), 403


@app.after_request
def _after_request(response):
    return _apply_cors_headers(response)


def _configured_paths_error() -> str | None:
    if not GODOT_EXE.exists():
        return f"Configured Godot executable not found: {GODOT_EXE}"
    if not GODOT_PROJECT.exists():
        return f"Configured Godot project not found: {GODOT_PROJECT}"
    return None


def _launcher_base_url() -> str:
    return f"http://{HOST}:{PORT}"


def _is_port_bound(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex((host, port)) == 0


def _existing_launcher_is_healthy() -> bool:
    request_url = f"{_launcher_base_url()}/health"
    try:
        with urllib.request.urlopen(request_url, timeout=0.5) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
    return '"service":"builder_launcher"' in payload.replace(" ", "") and '"ok":true' in payload.replace(" ", "")


def _build_launch_command(context: dict) -> list[str]:
    command = [str(GODOT_EXE), "--path", str(GODOT_PROJECT.parent)]
    launch_args = []
    for key in ("area_id", "room_id", "character_name"):
        value = str(context.get(key) or "").strip()
        if value:
            launch_args.append(f"--{key}={value}")
    if launch_args:
        command.append("--")
        command.extend(launch_args)
    return command


def _open_godot_launch_log():
    GODOT_LAUNCH_LOG.parent.mkdir(parents=True, exist_ok=True)
    return GODOT_LAUNCH_LOG.open("a", encoding="utf-8")


def _ensure_django_runtime() -> None:
    global _DJANGO_READY
    if _DJANGO_READY:
        return
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

    import django

    django.setup()

    import evennia

    if not bool(getattr(evennia, "_LOADED", False)):
        evennia._init()
    _DJANGO_READY = True


def _refresh_builder_runtime() -> None:
    _ensure_django_runtime()
    close_old_connections()
    connections.close_all()


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "builder_launcher"})


@app.get("/builder-api/map/export/<area_id>/")
def builder_export_map(area_id: str):
    normalized_area_id = str(area_id or "").strip()
    if not normalized_area_id:
        return jsonify({"ok": False, "error": "area_id_required"}), 400

    try:
        _refresh_builder_runtime()
        from world.builder.services import map_exporter

        exported = map_exporter.export_map(normalized_area_id)
    except ValueError as exc:
        logger.warning("Local builder export rejected for area_id=%s: %s", normalized_area_id, exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local builder export failed for area_id=%s", normalized_area_id)
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "data": {"map": exported}})


def _diff_error_payload(exc) -> tuple[dict, int]:
    payload = {
        "ok": False,
        "error": str(exc),
        "failed_operation_index": getattr(exc, "failed_operation_index", None),
        "failed_operation_id": getattr(exc, "failed_operation_id", None),
        "failed_operation": getattr(exc, "failed_operation", None),
    }
    conflicts = getattr(exc, "conflicts", None)
    if conflicts:
        payload["conflicts"] = list(conflicts)
    return payload, 400


@app.post("/builder-api/map/diff/")
def builder_apply_diff():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    diff = payload.get("diff")
    if diff is None:
        return jsonify({"ok": False, "error": "diff is required."}), 400

    preview = bool(payload.get("preview", False))
    session_id = str(payload.get("session_id") or "").strip() or None
    group_id = str(payload.get("group_id") or "").strip() or None

    try:
        _refresh_builder_runtime()
        from world.builder.services import map_diff_service

        result = map_diff_service.apply_diff(
            diff,
            preview=preview,
            session_id=session_id,
            group_id=group_id,
            username="builder_launcher",
        )
    except ValueError as exc:
        logger.warning("Local diff apply rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        try:
            from world.builder.services import map_diff_service

            if isinstance(exc, map_diff_service.DiffApplyError):
                error_payload, status = _diff_error_payload(exc)
                return jsonify(error_payload), status
        except Exception:
            pass
        logger.exception("Local diff apply failed")
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "data": {"result": result}})


@app.post("/builder-api/map/save-all/")
def builder_save_all():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    diff = payload.get("diff")
    if diff is None:
        return jsonify({"ok": False, "error": "diff is required."}), 400

    session_id = str(payload.get("session_id") or "").strip() or None

    try:
        _refresh_builder_runtime()
        from world.builder.services import map_diff_service

        result = map_diff_service.apply_diff(
            diff,
            preview=False,
            session_id=session_id,
            username="builder_launcher",
        )
    except ValueError as exc:
        logger.warning("Local save-all rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        try:
            from world.builder.services import map_diff_service

            if isinstance(exc, map_diff_service.DiffApplyError):
                error_payload, status = _diff_error_payload(exc)
                return jsonify(error_payload), status
        except Exception:
            pass
        logger.exception("Local save-all failed")
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "data": {"result": result}})


@app.post("/builder-api/map/undo/")
def builder_apply_undo():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    undo_diff = payload.get("undo_diff")
    if undo_diff is None:
        return jsonify({"ok": False, "error": "undo_diff is required."}), 400

    try:
        _refresh_builder_runtime()
        from world.builder.services import map_diff_service, undo_service

        result = undo_service.apply_undo(undo_diff)
    except ValueError as exc:
        logger.warning("Local undo rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        if 'map_diff_service' in locals() and isinstance(exc, map_diff_service.DiffApplyError):
            error_payload, status = _diff_error_payload(exc)
            return jsonify(error_payload), status
        logger.exception("Local undo failed")
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "data": {"result": result}})


@app.post("/builder-api/map/redo/")
def builder_apply_redo():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    diff = payload.get("diff")
    if diff is None:
        return jsonify({"ok": False, "error": "diff is required."}), 400

    try:
        _refresh_builder_runtime()
        from world.builder.services import map_diff_service, undo_service

        result = undo_service.apply_redo(diff)
    except ValueError as exc:
        logger.warning("Local redo rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        if 'map_diff_service' in locals() and isinstance(exc, map_diff_service.DiffApplyError):
            error_payload, status = _diff_error_payload(exc)
            return jsonify(error_payload), status
        logger.exception("Local redo failed")
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "data": {"result": result}})


@app.get("/builder-api/zones/")
def builder_list_zones():
    try:
        _refresh_builder_runtime()
        from world.builder.services import zone_service

        zones = zone_service.list_zones()
    except ValueError as exc:
        logger.warning("Local zone list rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local zone list failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"zones": zones}})


@app.post("/builder-api/zones/create/")
def builder_create_zone():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    try:
        _refresh_builder_runtime()
        from world.builder.services import zone_service

        zone = zone_service.create_zone(payload.get("zone_id"), payload.get("name"))
    except ValueError as exc:
        logger.warning("Local zone create rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local zone create failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"zone": zone}}), 201


@app.get("/builder-api/npcs/")
def builder_list_npcs():
    try:
        _refresh_builder_runtime()
        from world.builder.services import template_service

        templates = template_service.list_templates(template_type="npc")
    except ValueError as exc:
        logger.warning("Local NPC template list rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local NPC template list failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"templates": templates}})


@app.get("/builder-api/items/")
def builder_list_items():
    try:
        _refresh_builder_runtime()
        from world.builder.services import template_service

        templates = template_service.list_templates(template_type="item")
    except ValueError as exc:
        logger.warning("Local item template list rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local item template list failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"templates": templates}})


@app.get("/builder-api/npcs/yaml/")
def builder_list_yaml_npcs():
    try:
        _refresh_builder_runtime()
        from server.systems.npc_loader import load_all_npcs

        return jsonify(load_all_npcs())
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local YAML NPC list failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/builder-api/npcs/yaml/save/")
def builder_save_yaml_npc():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems.npc_loader import save_npc_payload

        npc = save_npc_payload(payload)
    except ValueError as exc:
        logger.warning("Local YAML NPC save rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local YAML NPC save failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "npc": npc})


@app.post("/builder-api/npcs/yaml/delete/")
def builder_delete_yaml_npc():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    npc_id = str(payload.get("id") or "").strip()
    if not npc_id:
        return jsonify({"ok": False, "error": "id is required"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems.npc_loader import delete_npc_payload

        deleted_id = delete_npc_payload(npc_id)
    except ValueError as exc:
        status = 404 if str(exc) == "not_found" else 400
        logger.warning("Local YAML NPC delete rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), status
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local YAML NPC delete failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "deleted_id": deleted_id})


@app.get("/builder-api/items/yaml/")
def builder_list_yaml_items():
    try:
        _refresh_builder_runtime()
        from server.systems.item_loader import load_all_items

        return jsonify(load_all_items())
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local YAML item list failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/builder-api/items/yaml/save/")
def builder_save_yaml_item():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems.item_loader import save_item_payload

        item = save_item_payload(payload)
    except ValueError as exc:
        logger.warning("Local YAML item save rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local YAML item save failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "item": item})


@app.post("/builder-api/items/yaml/delete/")
def builder_delete_yaml_item():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    item_id = str(payload.get("id") or "").strip()
    if not item_id:
        return jsonify({"ok": False, "error": "id is required"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems.item_loader import delete_item_payload

        deleted_id = delete_item_payload(item_id)
    except ValueError as exc:
        status = 404 if str(exc) == "not_found" else 400
        logger.warning("Local YAML item delete rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), status
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local YAML item delete failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "deleted_id": deleted_id})


def _load_builder_room_context(payload: dict):
    room_id = str(payload.get("room_id") or "").strip()
    zone_id = str(payload.get("zone_id") or "").strip()
    if not room_id:
        raise ValueError("room_id is required")
    return room_id, zone_id


@app.post("/builder-api/room/assign-npc/")
def builder_assign_room_npc():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    npc_id = str(payload.get("npc_id") or "").strip()
    if not npc_id:
        return jsonify({"ok": False, "error": "npc_id is required"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems import npc_loader, zone_room_npc_assignments

        room_id, zone_id = _load_builder_room_context(payload)
        npc_records = npc_loader.load_all_npcs()
        if npc_id not in npc_records:
            return jsonify({"ok": False, "error": "invalid npc_id"}), 404
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
        logger.warning("Local room NPC assign rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local room NPC assign failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"zone": updated_zone, "room": updated_room, "npc": npc_records.get(npc_id)}})


@app.post("/builder-api/room/remove-npc/")
def builder_remove_room_npc():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    npc_id = str(payload.get("npc_id") or "").strip()
    if not npc_id:
        return jsonify({"ok": False, "error": "npc_id is required"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems import zone_room_npc_assignments

        room_id, zone_id = _load_builder_room_context(payload)
        zone_payload, room_payload = zone_room_npc_assignments.resolve_builder_zone_room(room_id, zone_id=zone_id)
        next_npc_ids = [candidate for candidate in list(room_payload.get("npcs") or []) if candidate != npc_id]
        updated_zone, updated_room = zone_room_npc_assignments.update_room_npcs(
            room_id,
            next_npc_ids,
            zone_id=zone_payload.get("zone_id") or zone_id,
        )
    except ValueError as exc:
        logger.warning("Local room NPC remove rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local room NPC remove failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"zone": updated_zone, "room": updated_room, "removed_npc_id": npc_id}})


@app.post("/builder-api/room/assign-item/")
def builder_assign_room_item():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    item_id = str(payload.get("item_id") or "").strip()
    count = int(payload.get("count") or 0)
    if not item_id:
        return jsonify({"ok": False, "error": "item_id is required"}), 400
    if count <= 0:
        return jsonify({"ok": False, "error": "count must be greater than 0"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems import item_loader, zone_room_item_assignments

        room_id, zone_id = _load_builder_room_context(payload)
        item_records = item_loader.load_all_items()
        item_record = item_records.get(item_id)
        if item_record is None:
            return jsonify({"ok": False, "error": "invalid item_id"}), 404
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
        logger.warning("Local room item assign rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local room item assign failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"zone": updated_zone, "room": updated_room, "item": item_record}})


@app.post("/builder-api/room/remove-item/")
def builder_remove_room_item():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    item_id = str(payload.get("item_id") or "").strip()
    count = int(payload.get("count") or 1)
    if not item_id:
        return jsonify({"ok": False, "error": "item_id is required"}), 400
    if count <= 0:
        return jsonify({"ok": False, "error": "count must be greater than 0"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems import zone_room_item_assignments

        room_id, zone_id = _load_builder_room_context(payload)
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
            return jsonify({"ok": False, "error": "item not assigned to room"}), 404
        updated_zone, updated_room = zone_room_item_assignments.update_room_items(
            room_id,
            next_items,
            zone_id=zone_payload.get("zone_id") or zone_id,
        )
    except ValueError as exc:
        logger.warning("Local room item remove rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local room item remove failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"zone": updated_zone, "room": updated_room, "removed_item_id": item_id, "count": count}})


@app.post("/builder-api/room/update-item-count/")
def builder_update_room_item_count():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    item_id = str(payload.get("item_id") or "").strip()
    count = int(payload.get("count") or 0)
    if not item_id:
        return jsonify({"ok": False, "error": "item_id is required"}), 400
    if count < 0:
        return jsonify({"ok": False, "error": "count cannot be negative"}), 400

    try:
        _refresh_builder_runtime()
        from server.systems import item_loader, zone_room_item_assignments

        room_id, zone_id = _load_builder_room_context(payload)
        item_records = item_loader.load_all_items()
        item_record = item_records.get(item_id)
        if item_record is None:
            return jsonify({"ok": False, "error": "invalid item_id"}), 404
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
        logger.warning("Local room item count update rejected: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:  # pragma: no cover - local runtime guard
        logger.exception("Local room item count update failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "data": {"zone": updated_zone, "room": updated_room, "item": item_record, "count": count}})


@app.post("/launch-builder")
def launch_builder():
    logger.info("Launch request received from %s", _remote_address())
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    target = str(payload.get("target") or "builder").strip() or "builder"
    if target != "builder":
        logger.warning("Rejected launch request with unsupported target=%s", target)
        return jsonify({"ok": False, "error": "unsupported_target"}), 400

    path_error = _configured_paths_error()
    if path_error is not None:
        logger.error("Launch failed: %s", path_error)
        return jsonify({"ok": False, "error": path_error}), 500

    context = {
        "area_id": str(payload.get("area_id") or "").strip(),
        "room_id": str(payload.get("room_id") or "").strip(),
        "character_name": str(payload.get("character_name") or "").strip(),
    }
    logger.info("Launch context: %s", context)

    command = _build_launch_command(context)
    logger.info("Launch command: %s", command)
    try:
        log_handle = _open_godot_launch_log()
        log_handle.write("\n=== launch ===\n")
        log_handle.write(f"command={command}\n")
        log_handle.write(f"context={context}\n")
        log_handle.flush()
        subprocess.Popen(
            command,
            cwd=str(GODOT_PROJECT.parent),
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            close_fds=os.name != "nt",
        )
    except OSError as exc:
        logger.exception("Launch failed")
        return jsonify({"ok": False, "error": str(exc)}), 500

    logger.info("Launch succeeded")
    return jsonify({"ok": True, "status": "launched"})


if __name__ == "__main__":
    if _existing_launcher_is_healthy():
        logger.info("Builder Launcher already running at %s", _launcher_base_url())
        raise SystemExit(0)
    if _is_port_bound(HOST, PORT):
        logger.error("Port %s is already in use and no healthy Builder Launcher responded at %s", PORT, _launcher_base_url())
        raise SystemExit(1)
    logger.info("Starting Builder Launcher on http://%s:%s", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=False, threaded=True)