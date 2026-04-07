from django.urls import path

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