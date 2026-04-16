from django.urls import include, path

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
]

if builder_ready and builder_ready():
    urlpatterns += [
        path("builder/", include("web.api.builder.urls")),
    ]