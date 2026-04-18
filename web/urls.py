"""
This is the starting point when a user enters a url in their web browser.

The urls is matched (by regex) and mapped to a 'view' - a Python function or
callable class that in turn (usually) makes use of a 'template' (a html file
with slots that can be replaced by dynamic content) in order to render a HTML
page to show the user.

This file includes the urls in website, webclient and admin. To override you
should modify urls.py in those sub directories.

Search the Django documentation for "URL dispatcher" for more help.

"""

from django.urls import include, path

from web import views

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

# add patterns
urlpatterns = [
    path("builder/", views.builder_view, name="builder"),
    path("builder/api/zones/", views.builder_zone_list, name="builder-zone-list"),
    path("builder/api/zones/create/", views.builder_zone_create, name="builder-zone-create"),
    path("builder/api/rooms/", views.builder_room_list, name="builder-room-list"),
    path("builder/api/rooms/create/", views.builder_room_create, name="builder-room-create"),
    path("builder/api/zone/<str:zone_id>/", views.builder_zone_detail, name="builder-zone-detail"),
    path("builder/api/room/<int:room_id>/", views.builder_room_detail, name="builder-room-detail"),
    path("builder/api/room/<int:room_id>/delete/", views.builder_room_delete, name="builder-room-delete"),
    path("builder/api/room/<int:room_id>/save/", views.builder_room_save, name="builder-room-save"),
    # website
    path("", include("web.website.urls")),
    # local api wrappers
    path("api/", include("web.api.urls")),
    # webclient
    path("webclient/", include("web.webclient.urls")),
    # web admin
    path("admin/", include("web.admin.urls")),
    # add any extra urls here:
    # path("mypath/", include("path.to.my.urls.file")),
]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
