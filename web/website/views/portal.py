from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from evennia.utils import logger

from web.character_helpers import (
    get_character_slot_summary,
    get_owned_characters,
    get_selected_character_id,
    get_slot_limit_message,
    serialize_character,
    set_selected_character,
)
from web.character_builder import get_character_builder_config


class PlayNowRedirectView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/auth/login/?next={reverse('play-now')}")

        characters = get_owned_characters(request.user)
        if not characters:
            return redirect("/characters/create")

        selected_id = get_selected_character_id(request)
        selected_character = next(
            (character for character in characters if int(character.id) == int(selected_id or 0)),
            None,
        )

        if selected_character:
            set_selected_character(request, selected_character)
            logger.log_info(
                f"Play Now used selected character: account={request.user.username} character={selected_character.key} id={selected_character.id}"
            )
            return redirect(reverse("webclient:index"))

        if len(characters) == 1:
            character = characters[0]
            set_selected_character(request, character)
            logger.log_info(
                f"Play Now auto-selected: account={request.user.username} character={character.key} id={character.id}"
            )
            return redirect(reverse("webclient:index"))

        messages.info(request, "Select a character first, or use Play on a specific character.")
        return redirect("/characters/")


class CharacterDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "website/character_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_id = get_selected_character_id(self.request)
        characters = get_owned_characters(self.request.user)
        slot_summary = get_character_slot_summary(self.request.user)
        context["selected_character_id"] = selected_id
        context["selected_character_name"] = next(
            (character.key for character in characters if int(character.id) == int(selected_id or 0)),
            None,
        )
        context["character_slots"] = slot_summary
        context["slot_limit_message"] = get_slot_limit_message(self.request.user)
        context["characters"] = [
            serialize_character(character, selected_id=selected_id)
            for character in characters
        ]
        return context


class CharacterCreatePageView(LoginRequiredMixin, TemplateView):
    template_name = "website/character_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["character_slots"] = get_character_slot_summary(self.request.user)
        context["slot_limit_message"] = get_slot_limit_message(self.request.user)
        context["builder_config"] = get_character_builder_config()
        return context
