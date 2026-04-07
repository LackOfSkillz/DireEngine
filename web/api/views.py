from django.contrib.auth import logout
from django.http import JsonResponse
from django.views import View

from evennia.utils import logger

from web.character_helpers import (
    create_web_character_from_payload,
    delete_owned_character,
    get_character_slot_summary,
    get_owned_character_or_404,
    get_owned_characters,
    get_selected_character_id,
    parse_request_data,
    serialize_character,
    set_selected_character,
)
from web.character_builder import validate_character_name


class JsonLoginRequiredView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"authenticated": False, "error": "Authentication required."}, status=401)
        return super().dispatch(request, *args, **kwargs)


class AccountMeApiView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"authenticated": False, "username": None})
        return JsonResponse({"authenticated": True, "username": request.user.username})


class AccountLogoutApiView(View):
    def post(self, request, *args, **kwargs):
        username = request.user.username if request.user.is_authenticated else None
        logout(request)
        if username:
            logger.log_info(f"Web logout: {username}")
        return JsonResponse({"authenticated": False, "username": None})


class CharacterListApiView(JsonLoginRequiredView):
    def get(self, request, *args, **kwargs):
        selected_id = get_selected_character_id(request)
        slot_summary = get_character_slot_summary(request.user)
        characters = [
            serialize_character(character, selected_id=selected_id)
            for character in get_owned_characters(request.user)
        ]
        return JsonResponse(
            {
                "authenticated": True,
                "selected_character_id": selected_id,
                "character_slots": slot_summary,
                "characters": characters,
            }
        )


class CharacterCreateApiView(JsonLoginRequiredView):
    def post(self, request, *args, **kwargs):
        payload = parse_request_data(request)
        try:
            character, normalized = create_web_character_from_payload(request.user, payload)
        except ValueError as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)

        set_selected_character(request, character)
        logger.log_info(
            f"Web character created: account={request.user.username} character={character.key} race={getattr(character.db, 'race', '')}"
        )
        return JsonResponse(
            {
                "ok": True,
                "submitted": {
                    "name": normalized["name"],
                    "race": normalized["race"],
                    "gender": normalized["gender"],
                },
                "character": serialize_character(character, selected_id=character.id),
            },
            status=201,
        )


class CharacterNameValidationApiView(JsonLoginRequiredView):
    def get(self, request, *args, **kwargs):
        result = validate_character_name(request.GET.get("name"))
        status_code = 200 if result["ok"] else 400
        return JsonResponse(result, status=status_code)


class CharacterDeleteApiView(JsonLoginRequiredView):
    def post(self, request, *args, **kwargs):
        payload = parse_request_data(request)
        character_id = payload.get("character_id") or payload.get("id")
        if not character_id:
            return JsonResponse({"ok": False, "error": "character_id is required."}, status=400)

        try:
            character = delete_owned_character(request, request.user, character_id)
        except Exception as exc:
            status_code = 404 if exc.__class__.__name__ == "Http404" else 400
            return JsonResponse({"ok": False, "error": str(exc)}, status=status_code)

        logger.log_info(f"Web character deleted: account={request.user.username} character={character.key}")
        return JsonResponse({"ok": True, "deleted_character_id": int(character_id)})


class CharacterSelectApiView(JsonLoginRequiredView):
    def post(self, request, *args, **kwargs):
        payload = parse_request_data(request)
        character_id = payload.get("character_id") or payload.get("id")
        if not character_id:
            return JsonResponse({"ok": False, "error": "character_id is required."}, status=400)

        try:
            character = get_owned_character_or_404(request.user, character_id)
        except Exception as exc:
            status_code = 404 if exc.__class__.__name__ == "Http404" else 400
            return JsonResponse({"ok": False, "error": str(exc)}, status=status_code)

        set_selected_character(request, character)
        logger.log_info(
            f"Web character selected: account={request.user.username} character={character.key} id={character.id}"
        )
        return JsonResponse(
            {
                "ok": True,
                "selected_character_id": int(character.id),
                "character": serialize_character(character, selected_id=character.id),
            }
        )


class DebugSessionApiView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                "user": request.user.username if request.user.is_authenticated else None,
                "puppet": get_selected_character_id(request),
                "authenticated": bool(request.user.is_authenticated),
            }
        )