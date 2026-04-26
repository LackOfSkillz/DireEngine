import json
import os
import hashlib
import unittest
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django

django.setup()

from django.test import RequestFactory, SimpleTestCase

from web.api.llm_api import llm_generate_room_description, llm_health, room_generate_description
from world.builder.prompting.room_description_generation import RoomDescriptionGenerationResult
from world.builder.services.llm_client import BuilderLLMConfig, LLMError


class BuilderLLMApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("web.api.llm_api.async_to_sync")
    @patch("web.api.llm_api.load_llm_config")
    def test_llm_health_returns_success_payload(self, mock_load_config, mock_async_to_sync):
        mock_load_config.return_value = BuilderLLMConfig(
            llm_enabled=True,
            llm_base_url="http://health.example",
            llm_model="health-model",
            llm_temperature=0.75,
        )
        mock_async_to_sync.return_value = lambda: {
            "model": "health-model",
            "base_url": "http://health.example",
            "reachable": True,
            "latency_ms": 12.5,
        }

        response = llm_health(self.factory.get("/api/llm/health"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "model": "health-model",
                "base_url": "http://health.example",
                "reachable": True,
                "latency_ms": 12.5,
            },
        )

    @patch("web.api.llm_api.load_llm_config")
    def test_llm_health_returns_service_unavailable_when_disabled(self, mock_load_config):
        mock_load_config.return_value = BuilderLLMConfig(
            llm_enabled=False,
            llm_base_url="http://disabled.example",
            llm_model="disabled-model",
            llm_temperature=0.75,
        )

        response = llm_health(self.factory.get("/api/llm/health"))

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(
            response.content,
            {
                "model": "disabled-model",
                "base_url": "http://disabled.example",
                "reachable": False,
                "error": "LLM generation is disabled.",
            },
        )

    @patch("web.api.llm_api.async_to_sync")
    @patch("web.api.llm_api.load_llm_config")
    def test_llm_health_returns_service_unavailable_when_probe_fails(self, mock_load_config, mock_async_to_sync):
        mock_load_config.return_value = BuilderLLMConfig(
            llm_enabled=True,
            llm_base_url="http://offline.example",
            llm_model="offline-model",
            llm_temperature=0.75,
        )

        def raise_health_error():
            raise LLMError("LLM health check connection failed [abc123def456]: offline")

        mock_async_to_sync.return_value = raise_health_error

        response = llm_health(self.factory.get("/api/llm/health"))

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(
            response.content,
            {
                "model": "offline-model",
                "base_url": "http://offline.example",
                "reachable": False,
                "error": "LLM health check connection failed [abc123def456]: offline",
            },
        )

    @patch("web.api.llm_api.async_to_sync")
    @patch("web.api.llm_api.load_llm_config")
    def test_llm_generate_room_description_returns_success_payload(self, mock_load_config, mock_async_to_sync):
        mock_load_config.return_value = BuilderLLMConfig(
            llm_enabled=True,
            llm_base_url="http://llm.example",
            llm_model="builder-model",
            llm_temperature=0.65,
        )
        mock_async_to_sync.return_value = lambda room, zone, client, llm_config: RoomDescriptionGenerationResult(
            ok=True,
            text="Lantern light glows across the wet cobbles.",
            error=None,
            provenance={"source": "llm", "model": "builder-model", "temperature": 0.65, "prompt_trimmed": False},
        )

        response = llm_generate_room_description(
            self.factory.post(
                "/api/llm/generate-room-description",
                data='{"room": {"name": "Lantern Market"}, "zone": {"name": "Harbor Ward"}}',
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "ok": True,
                "text": "Lantern light glows across the wet cobbles.",
                "error": None,
                "provenance": {"source": "llm", "model": "builder-model", "temperature": 0.65, "prompt_trimmed": False},
            },
        )

    @patch("web.api.llm_api.async_to_sync")
    @patch("web.api.llm_api.load_llm_config")
    def test_llm_generate_room_description_returns_service_unavailable_payload(self, mock_load_config, mock_async_to_sync):
        mock_load_config.return_value = BuilderLLMConfig(
            llm_enabled=False,
            llm_base_url="http://llm.example",
            llm_model="builder-model",
            llm_temperature=0.65,
        )
        mock_async_to_sync.return_value = lambda room, zone, client, llm_config: RoomDescriptionGenerationResult(
            ok=False,
            text=None,
            error="Local LLM generation is unavailable.",
            provenance={"source": "disabled", "model": "builder-model", "temperature": 0.65, "prompt_trimmed": False},
        )

        response = llm_generate_room_description(
            self.factory.post(
                "/api/llm/generate-room-description",
                data='{"room": {"name": "Lantern Market"}, "zone": {"name": "Harbor Ward"}}',
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(
            response.content,
            {
                "ok": False,
                "text": None,
                "error": "Local LLM generation is unavailable.",
                "provenance": {"source": "disabled", "model": "builder-model", "temperature": 0.65, "prompt_trimmed": False},
            },
        )

    @patch("web.api.llm_api.load_llm_config")
    def test_llm_generate_room_description_rejects_invalid_payload(self, mock_load_config):
        mock_load_config.return_value = BuilderLLMConfig(
            llm_enabled=True,
            llm_base_url="http://llm.example",
            llm_model="builder-model",
            llm_temperature=0.65,
        )

        response = llm_generate_room_description(
            self.factory.post(
                "/api/llm/generate-room-description",
                data='{"room": {"name": "Lantern Market"}}',
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            {
                "ok": False,
                "error": "Request must include room and zone objects.",
            },
        )

    @patch("web.api.llm_api.resolve_builder_zone_room")
    def test_room_generate_description_debug_returns_prompt_preview(self, mock_resolve_builder_zone_room):
        mock_resolve_builder_zone_room.return_value = (
            {
                "zone_id": "crossingv2",
                "name": "crossingV2",
                "generation_context": {
                    "setting_type": "city",
                    "era_feel": "late-medieval",
                    "culture": ["multicultural"],
                    "mood": ["bustling"],
                    "climate": "river-valley",
                    "voice": "Gritty, pragmatic. Present tense.",
                },
            },
            {
                "id": "crossingV2_628_178",
                "name": "crossingV2_628_178",
                "exits": {
                    "east": {"target": "crossingV2_628_184"},
                    "south": {"target": "crossingV2_628_208"},
                },
            },
        )

        response = room_generate_description(
            self.factory.post(
                "/api/rooms/crossingV2_628_178/generate-description?debug=true",
                data="{}",
                content_type="application/json",
            ),
            "crossingV2_628_178",
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["prompt_version"], "v3_grounded_rich")
        self.assertIn("=== ZONE CONTEXT ===", payload["prompt"])
        self.assertIn("You are in crossingV2.", payload["prompt"])
        self.assertIn("Setting type: city.", payload["prompt"])
        self.assertIn("=== VOICE ===", payload["prompt"])
        self.assertIn("Gritty, pragmatic. Present tense.", payload["prompt"])
        self.assertEqual(payload["hash"], hashlib.sha256(payload["prompt"].encode("utf-8")).hexdigest())

    @patch("web.api.llm_api.resolve_builder_zone_room")
    def test_room_generate_description_debug_returns_not_found_for_unknown_room(self, mock_resolve_builder_zone_room):
        mock_resolve_builder_zone_room.side_effect = ValueError("room not found: missing_room")

        response = room_generate_description(
            self.factory.post(
                "/api/rooms/missing_room/generate-description?debug=true",
                data="{}",
                content_type="application/json",
            ),
            "missing_room",
        )

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content,
            {
                "ok": False,
                "error": "room not found: missing_room",
            },
        )


if __name__ == "__main__":
    unittest.main()