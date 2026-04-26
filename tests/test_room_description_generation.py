import unittest
from types import SimpleNamespace

from world.builder.prompting.room_description_generation import _input_hash, generate_room_description


class _StubClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def generate(self, prompt, max_tokens=250, temperature=0.75):
        self.calls.append({"prompt": prompt, "max_tokens": max_tokens, "temperature": temperature})
        if self.error is not None:
            raise self.error
        return self.response


class RoomDescriptionGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_room_description_returns_text_and_provenance(self):
        client = _StubClient(response="A wet market lane glitters under hanging lanterns.")
        config = SimpleNamespace(llm_enabled=True, llm_model="mistral-nemo", llm_temperature=0.55)

        result = await generate_room_description(
            {"name": "Lantern Market", "environment": "city", "exits": {"west": {"target": "canal_walk"}}},
            {"name": "Harbor Ward", "generation_context": {"setting_type": "city", "mood": ["bustling"]}},
            client=client,
            llm_config=config,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "A wet market lane glitters under hanging lanterns.")
        self.assertIsNone(result.error)
        self.assertEqual(result.provenance["source"], "llm")
        self.assertEqual(result.provenance["model"], "mistral-nemo")
        self.assertIn("input_hash", result.provenance)
        self.assertEqual(client.calls[0]["temperature"], 0.55)
        self.assertIn("Lantern Market", client.calls[0]["prompt"])

    def test_input_hash_changes_when_room_tags_change(self):
        zone = {"name": "Harbor Ward", "generation_context": {"setting_type": "city"}}
        base_room = {
            "id": "lantern_market",
            "name": "Lantern Market",
            "exits": {"west": {"target": "canal_walk"}},
            "tags": {"structure": "street", "specific_function": None, "named_feature": None, "condition": None, "custom": []},
        }
        changed_room = {
            **base_room,
            "tags": {"structure": "bridge", "specific_function": None, "named_feature": None, "condition": None, "custom": []},
        }

        self.assertNotEqual(_input_hash(base_room, zone), _input_hash(changed_room, zone))

    async def test_generate_room_description_degrades_gracefully_when_llm_fails(self):
        client = _StubClient(error=RuntimeError("connection refused"))
        config = SimpleNamespace(llm_enabled=True, llm_model="mistral-nemo", llm_temperature=0.75)

        result = await generate_room_description(
            {"name": "Lantern Market", "environment": "city"},
            {"name": "Harbor Ward", "generation_context": {"setting_type": "city"}},
            client=client,
            llm_config=config,
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.text)
        self.assertEqual(result.error, "connection refused")
        self.assertEqual(result.provenance["source"], "unavailable")

    async def test_generate_room_description_returns_disabled_result_when_llm_is_off(self):
        config = SimpleNamespace(llm_enabled=False, llm_model="mistral-nemo", llm_temperature=0.75)

        result = await generate_room_description(
            {"name": "Lantern Market", "environment": "city"},
            {"name": "Harbor Ward"},
            client=None,
            llm_config=config,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Local LLM generation is unavailable.")
        self.assertEqual(result.provenance["source"], "disabled")


if __name__ == "__main__":
    unittest.main()