from django.urls import include, path

from web.api.item_api import delete_item, get_all_items, save_item
from web.api.npc_api import delete_npc, get_all_npcs, save_npc
from web.api.views import (
    AccountMeApiView,
    AccountLogoutApiView,
    CharacterCreateApiView,
    CharacterDeleteApiView,
    CharacterListApiView,
    CharacterNameValidationApiView,
    CharacterSelectApiView,
    DebugSessionApiView,
)

try:
    from world.builder.capabilities import builder_ready
except ImportError:  # pragma: no cover - builder is optional
    builder_ready = None


urlpatterns = [
    path("account/me", AccountMeApiView.as_view(), name="api-account-me"),
    path("account/logout", AccountLogoutApiView.as_view(), name="api-account-logout"),
    path("characters/", CharacterListApiView.as_view(), name="api-characters"),
    path("characters/validate-name", CharacterNameValidationApiView.as_view(), name="api-character-validate-name"),
    path("characters/create", CharacterCreateApiView.as_view(), name="api-character-create"),
    path("characters/delete", CharacterDeleteApiView.as_view(), name="api-character-delete"),
    path("characters/select", CharacterSelectApiView.as_view(), name="api-character-select"),
    path("debug/session", DebugSessionApiView.as_view(), name="api-debug-session"),
    path("npcs/", get_all_npcs, name="api-npcs"),
    path("npcs/save/", save_npc, name="api-npcs-save"),
    path("npcs/delete/", delete_npc, name="api-npcs-delete"),
    path("items/", get_all_items, name="api-items"),
    path("items/save/", save_item, name="api-items-save"),
    path("items/delete/", delete_item, name="api-items-delete"),
]

if builder_ready and builder_ready():
    urlpatterns += [
        path("builder/", include("web.api.builder.urls")),
    ]