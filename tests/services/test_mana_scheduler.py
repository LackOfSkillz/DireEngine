import unittest
import os
import time

import django

from engine.services.mana_service import ManaService
from tools.diretest.core.runtime import clear_active_context, set_active_context


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.systems.scheduler import flush_due, get_scheduler_snapshot


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, profession="commoner", identifier=1):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.profession = profession
        self.pk = identifier
        self.id = identifier
        self.key = f"Dummy{identifier}"
        self.devotion = 50
        self.devotion_max = 100

    def ensure_core_defaults(self):
        return None

    def is_profession(self, profession):
        return self.profession == str(profession or "").strip().lower()

    def get_devotion(self):
        return self.devotion

    def get_devotion_max(self):
        return self.devotion_max

    def adjust_devotion(self, amount, sync=False):
        _sync = sync
        self.devotion = max(0, min(self.devotion_max, self.devotion + int(amount)))
        return self.devotion

    def get_skill(self, name):
        _name = name
        return 100

    def get_stat(self, name):
        _name = name
        return 30


class ManaSchedulerTests(unittest.TestCase):
    def setUp(self):
        self._diretest_context = type("DireTestContext", (), {"test_mode": True})()
        set_active_context(self._diretest_context)

    def tearDown(self):
        for identifier in (301, 302, 303):
            ManaService.cancel_scheduled_effects(DummyCharacter(identifier=identifier))
        clear_active_context(self._diretest_context)

    def _jobs_for_owner(self, owner_key):
        snapshot = get_scheduler_snapshot() or {}
        return [job for job in list(snapshot.get("active_jobs", [])) if str(job.get("owner", "") or "") == owner_key]

    def test_schedule_devotion_pulse_registers_one_job(self):
        character = DummyCharacter(profession="cleric", identifier=301)

        ManaService.cancel_scheduled_effects(character)
        ManaService.schedule_devotion_pulse(character, delay=60)

        jobs = self._jobs_for_owner("#301")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].get("system"), "mana.devotion")

    def test_duplicate_devotion_schedule_keeps_single_job(self):
        character = DummyCharacter(profession="cleric", identifier=302)

        ManaService.cancel_scheduled_effects(character)
        ManaService.schedule_devotion_pulse(character, delay=60)
        ManaService.schedule_devotion_pulse(character, delay=60)

        jobs = self._jobs_for_owner("#302")
        self.assertEqual(len(jobs), 1)

    def test_flush_due_runs_devotion_callback_and_reschedules(self):
        character = DummyCharacter(profession="cleric", identifier=303)

        ManaService.cancel_scheduled_effects(character)
        ManaService.schedule_devotion_pulse(character, delay=0)
        executed = flush_due(now=time.time() + 1.0)

        self.assertTrue(executed)
        self.assertEqual(character.devotion, 51)
        jobs = self._jobs_for_owner("#303")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].get("system"), "mana.devotion")


if __name__ == "__main__":
    unittest.main()
