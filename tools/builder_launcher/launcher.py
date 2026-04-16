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