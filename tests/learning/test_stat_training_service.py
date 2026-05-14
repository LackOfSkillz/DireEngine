import os
import time
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from engine.services.stat_training_service import CONSULT_WINDOW_SECONDS, StatTrainingService
from typeclasses.npcs import StatTrainerNPC
from typeclasses.rooms import Room


class _DummyCharacter:
    def __init__(self, room=None, *, race="human", tdp=600, stats=None):
        self.location = room
        self.db = SimpleNamespace(race=race, tdp=tdp, stats=dict(stats or {}))
        self.ndb = SimpleNamespace(train_consult_state=None)
        self.sync_calls = 0

    def spend_tdp(self, amount, reason=""):
        current = int(self.db.tdp or 0)
        if current < int(amount or 0):
            return False
        self.db.tdp = current - int(amount or 0)
        return True

    def sync_client_state(self):
        self.sync_calls += 1


class StatTrainingServiceTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.room = self._create(Room, "Trainer Test Room")
        self.trainer = self._create(StatTrainerNPC, "Trainer Test", location=self.room, home=self.room)
        self.trainer.db.trains_stat = "strength"

    def tearDown(self):
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass

    def _create(self, typeclass, key, **kwargs):
        obj = create_object(typeclass, key=key, nohome=True, **kwargs)
        self.created.append(obj)
        return obj

    def test_find_trainer_in_room_returns_stat_trainer(self):
        caller = _DummyCharacter(self.room)
        self.assertEqual(StatTrainingService.find_trainer_in_room(caller), self.trainer)

    def test_consult_outside_trainer_room_errors(self):
        caller = _DummyCharacter(None, stats={"strength": 21})
        result = StatTrainingService.consult(caller)
        self.assertFalse(result.ok)
        self.assertIn("not at a stat trainer", result.message)

    def test_consult_sets_ndb_state(self):
        caller = _DummyCharacter(self.room, stats={"strength": 21})
        result = StatTrainingService.consult(caller)
        self.assertTrue(result.ok)
        self.assertEqual(caller.ndb.train_consult_state["stat"], "strength")
        self.assertEqual(caller.ndb.train_consult_state["cost"], 63)
        self.assertIn("evaluates their Strength training", result.room_message)

    def test_consult_insufficient_tdps_reports_shortfall(self):
        caller = _DummyCharacter(self.room, tdp=10, stats={"strength": 21})
        result = StatTrainingService.consult(caller)
        self.assertFalse(result.ok)
        self.assertIn("You have only 10", result.message)
        self.assertIsNone(result.room_message)

    def test_consult_uses_racial_modifier(self):
        caller = _DummyCharacter(self.room, race="volgrin", stats={"strength": 21})
        result = StatTrainingService.consult(caller)
        self.assertTrue(result.ok)
        self.assertEqual(result.cost, 33)

    def test_commit_without_consult_errors(self):
        caller = _DummyCharacter(self.room, stats={"strength": 21})
        result = StatTrainingService.commit(caller)
        self.assertFalse(result.ok)
        self.assertIn("consulted", result.message)

    def test_commit_after_expired_window_requires_reconsult(self):
        caller = _DummyCharacter(self.room, stats={"strength": 21})
        StatTrainingService.consult(caller)
        caller.ndb.train_consult_state["timestamp"] = time.time() - (CONSULT_WINDOW_SECONDS + 1)
        result = StatTrainingService.commit(caller)
        self.assertFalse(result.ok)
        self.assertIn("Too much time has passed", result.message)

    def test_commit_with_different_trainer_requires_reconsult(self):
        caller = _DummyCharacter(self.room, stats={"strength": 21})
        StatTrainingService.consult(caller)
        other_room = self._create(Room, "Other Room")
        other_trainer = self._create(StatTrainerNPC, "Other Trainer", location=other_room, home=other_room)
        other_trainer.db.trains_stat = "strength"
        caller.location = other_room
        result = StatTrainingService.commit(caller)
        self.assertFalse(result.ok)
        self.assertIn("same trainer", result.message)

    def test_commit_spends_tdp_and_raises_stat(self):
        caller = _DummyCharacter(self.room, tdp=600, stats={"strength": 21})
        consult = StatTrainingService.consult(caller)
        result = StatTrainingService.commit(caller)
        self.assertTrue(consult.ok)
        self.assertTrue(result.ok)
        self.assertEqual(caller.db.tdp, 537)
        self.assertEqual(caller.db.stats["strength"], 22)
        self.assertEqual(result.new_value, 22)
        self.assertIn("trains with Trainer Test", result.room_message)

    def test_commit_without_consult_has_no_room_message(self):
        caller = _DummyCharacter(self.room, stats={"strength": 21})

        result = StatTrainingService.commit(caller)

        self.assertIsNone(result.room_message)

    def test_commit_after_expired_window_has_no_room_message(self):
        caller = _DummyCharacter(self.room, stats={"strength": 21})
        StatTrainingService.consult(caller)
        caller.ndb.train_consult_state["timestamp"] = time.time() - (CONSULT_WINDOW_SECONDS + 1)

        result = StatTrainingService.commit(caller)

        self.assertIsNone(result.room_message)
