from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from server.systems.npc_loader import delete_npc_payload, load_all_npcs, save_npc_payload
from web.character_helpers import parse_request_data


@csrf_exempt
def get_all_npcs(request):
    if request.method != "GET":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
    return JsonResponse(load_all_npcs())


@csrf_exempt
def save_npc(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    payload = parse_request_data(request)
    try:
        npc = save_npc_payload(payload)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "npc": npc}, status=200)


@csrf_exempt
def delete_npc(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    payload = parse_request_data(request)
    npc_id = str(payload.get("id") or "").strip()
    if not npc_id:
        return JsonResponse({"ok": False, "error": "id is required"}, status=400)

    try:
        deleted_id = delete_npc_payload(npc_id)
    except ValueError as exc:
        status = 404 if str(exc) == "not_found" else 400
        return JsonResponse({"ok": False, "error": str(exc)}, status=status)
    return JsonResponse({"ok": True, "deleted_id": deleted_id}, status=200)