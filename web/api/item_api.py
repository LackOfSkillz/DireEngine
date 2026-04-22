from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from server.systems.item_loader import delete_item_payload, load_all_items, save_item_payload
from web.character_helpers import parse_request_data


@csrf_exempt
def get_all_items(request):
    if request.method != "GET":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
    return JsonResponse(load_all_items())


@csrf_exempt
def save_item(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
    payload = parse_request_data(request)
    try:
        item = save_item_payload(payload)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "item": item}, status=200)


@csrf_exempt
def delete_item(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
    payload = parse_request_data(request)
    item_id = str(payload.get("id") or "").strip()
    if not item_id:
        return JsonResponse({"ok": False, "error": "id is required"}, status=400)
    try:
        deleted_id = delete_item_payload(item_id)
    except ValueError as exc:
        status = 404 if str(exc) == "not_found" else 400
        return JsonResponse({"ok": False, "error": str(exc)}, status=status)
    return JsonResponse({"ok": True, "deleted_id": deleted_id}, status=200)