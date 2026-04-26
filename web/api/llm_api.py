from __future__ import annotations

import json

from asgiref.sync import async_to_sync
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from server.systems.zone_room_npc_assignments import resolve_builder_zone_room
from world.builder.prompting.room_description_prompt import PROMPT_VERSION, assemble_room_description_prompt
from world.builder.prompting.room_description_generation import generate_room_description
from world.builder.services.llm_client import LLMError, LocalLLMClient, _hash_prompt, load_llm_config


def _parse_json_payload(request) -> tuple[dict, bool]:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}, False
    return (payload if isinstance(payload, dict) else {}), isinstance(payload, dict)


def _is_debug_prompt_request(request) -> bool:
    return str(request.GET.get("debug") or "").strip().lower() in {"1", "true", "yes", "on"}


@require_http_methods(["GET"])
def llm_health(request):
    config = load_llm_config()
    if not config.llm_enabled:
        return JsonResponse(
            {
                "model": config.llm_model,
                "base_url": config.llm_base_url,
                "reachable": False,
                "error": "LLM generation is disabled.",
            },
            status=503,
        )

    client = LocalLLMClient(base_url=config.llm_base_url, model=config.llm_model)
    try:
        payload = async_to_sync(client.health)()
    except LLMError as error:
        return JsonResponse(
            {
                "model": config.llm_model,
                "base_url": config.llm_base_url,
                "reachable": False,
                "error": str(error),
            },
            status=503,
        )
    return JsonResponse(payload, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def llm_generate_room_description(request):
    payload, payload_is_valid = _parse_json_payload(request)
    if request.body and not payload_is_valid:
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    room = payload.get("room")
    zone = payload.get("zone")
    if not isinstance(room, dict) or not isinstance(zone, dict):
        return JsonResponse({"ok": False, "error": "Request must include room and zone objects."}, status=400)

    config = load_llm_config()
    client = LocalLLMClient(base_url=config.llm_base_url, model=config.llm_model) if config.llm_enabled else None
    result = async_to_sync(generate_room_description)(room, zone, client=client, llm_config=config)
    response_payload = {
        "ok": result.ok,
        "text": result.text,
        "error": result.error,
        "provenance": result.provenance,
    }
    status_code = 200 if result.ok else 503 if result.provenance.get("source") in {"disabled", "unavailable"} else 400
    return JsonResponse(response_payload, status=status_code)


@csrf_exempt
@require_http_methods(["POST"])
def room_generate_description(request, room_id: str):
    payload, payload_is_valid = _parse_json_payload(request)
    if request.body and not payload_is_valid:
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    zone_id = str(payload.get("zone_id") or "").strip()
    try:
        zone, room = resolve_builder_zone_room(room_id, zone_id=zone_id)
    except ValueError as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=404)

    if _is_debug_prompt_request(request):
        prompt = assemble_room_description_prompt(room, zone)
        return JsonResponse(
            {
                "prompt": prompt.prompt,
                "prompt_version": PROMPT_VERSION,
                "hash": _hash_prompt(prompt.prompt),
            },
            status=200,
        )

    config = load_llm_config()
    client = LocalLLMClient(base_url=config.llm_base_url, model=config.llm_model) if config.llm_enabled else None
    result = async_to_sync(generate_room_description)(room, zone, client=client, llm_config=config)
    response_payload = {
        "ok": result.ok,
        "text": result.text,
        "error": result.error,
        "provenance": result.provenance,
    }
    status_code = 200 if result.ok else 503 if result.provenance.get("source") in {"disabled", "unavailable"} else 400
    return JsonResponse(response_payload, status=status_code)