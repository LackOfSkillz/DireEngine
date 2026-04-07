"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path
from django.views.generic import TemplateView

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns
from web.website.views.help import LoreHelpApiView, LorePageView

# add patterns here
urlpatterns = [
    path("world", TemplateView.as_view(template_name="website/world.html"), name="world"),
    path("guilds", TemplateView.as_view(template_name="website/guilds.html"), name="guilds"),
    path("lore", LorePageView.as_view(), name="lore"),
    path("api/help/", LoreHelpApiView.as_view(), name="lore-help-api"),
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
