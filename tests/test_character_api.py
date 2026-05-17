import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.dbserialize import _SaverDict

from world.area_forge.character_api import _get_cooldowns, get_character_payload


def _build_saverdict(data):
    wrapped = _SaverDict()
    wrapped._data.update(data)
    return wrapped


class DummyCharacter:
    def __init__(self, *, states=None, ndb_cooldowns=None):
        self.key = "SmokeClericLive"
        self.account = None
        self.permissions = None
        self.contents = []
        self.db = SimpleNamespace(
            states=states if states is not None else {},
            target=None,
            stance=None,
            equipment={},
            max_hp=100,
            hp=100,
            max_fatigue=100,
            fatigue=0,
            max_balance=100,
            balance=100,
            max_attunement=100,
            attunement=100,
            profession_rank=1,
            life_state="ALIVE",
        )
        self.ndb = SimpleNamespace(cooldowns=ndb_cooldowns)


class CharacterApiCooldownTests(unittest.TestCase):
    def test_get_cooldowns_empty_returns_empty(self):
        character = DummyCharacter(states={})

        self.assertEqual(_get_cooldowns(character), {})

    def test_get_cooldowns_ignores_non_cooldown_state_keys(self):
        character = DummyCharacter(states={"prepared_spell": {"name": "gauge_flow"}})

        self.assertEqual(_get_cooldowns(character), {})

    def test_get_cooldowns_reads_scalar_state_for_backward_compatibility(self):
        character = DummyCharacter(states={"cooldown_gauge_flow": 3})

        self.assertEqual(_get_cooldowns(character), {"gauge_flow": 3})

    def test_get_cooldowns_reads_builtin_dict_duration(self):
        character = DummyCharacter(states={"cooldown_gauge_flow": {"duration": 4}})

        self.assertEqual(_get_cooldowns(character), {"gauge_flow": 4})

    def test_get_cooldowns_reads_evennia_saverdict_duration(self):
        character = DummyCharacter(states={"cooldown_gauge_flow": _build_saverdict({"duration": 2})})

        self.assertEqual(_get_cooldowns(character), {"gauge_flow": 2})

    def test_get_cooldowns_returns_zero_for_malformed_mapping_duration(self):
        character = DummyCharacter(states={"cooldown_gauge_flow": _build_saverdict({"duration": "bad"})})

        self.assertEqual(_get_cooldowns(character), {"gauge_flow": 0})

    def test_get_cooldowns_returns_zero_for_malformed_scalar_value(self):
        character = DummyCharacter(states={"cooldown_gauge_flow": "bad"})

        self.assertEqual(_get_cooldowns(character), {"gauge_flow": 0})

    def test_get_cooldowns_merges_runtime_cooldowns(self):
        character = DummyCharacter(states={}, ndb_cooldowns={"focus": 105.0})

        with patch("world.area_forge.character_api.time.time", return_value=100.0):
            self.assertEqual(_get_cooldowns(character), {"focus": 5})

    def test_get_cooldowns_prefers_longer_runtime_duration(self):
        character = DummyCharacter(
            states={"cooldown_gauge_flow": _build_saverdict({"duration": 2})},
            ndb_cooldowns={"gauge_flow": 110.0},
        )

        with patch("world.area_forge.character_api.time.time", return_value=100.0):
            self.assertEqual(_get_cooldowns(character), {"gauge_flow": 10})

    def test_get_character_payload_serializes_saverdict_cooldowns(self):
        character = DummyCharacter(states={"cooldown_gauge_flow": _build_saverdict({"duration": 2})})

        payload = get_character_payload(character)

        self.assertEqual(payload["cooldowns"], {"gauge_flow": 2})
        self.assertEqual(payload["abilities"], [])


if __name__ == "__main__":
    unittest.main()