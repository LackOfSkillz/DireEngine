import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_awake import CmdAwake
from commands.cmd_sleep import CmdSleep
from engine.services.pulse_service import PulseService
from engine.services.rexp_service import (
    REXP_CAP_SECONDS,
    REXP_CONSUMPTION_PER_GROUP_PULSE,
    apply_offline_drain,
    consume_rexp_for_group_pulse,
    get_rexp_display,
    update_rexp_banking,
)
from engine.services.skill_service import SkillService


class _DummySkill:
    def __init__(self, name, *, pool=0.0, max_pool=100.0, rank=1, last_trained=None):
        self.name = name
        self.pool = pool
        self.max_pool = max_pool
        self.rank = rank
        self.rank_progress = 0.0
        self.mindstate = 0
        self.skillset = "primary"
        self.last_trained = time.time() - 9999 if last_trained is None else last_trained

    def recalc_pool(self):
        return None


class _DummyHandler:
    def __init__(self, skills):
        self.skills = dict(skills)


class _DummyCharacter:
    def __init__(self):
        now = time.time()
        self.key = "Tester"
        self.db = SimpleNamespace(
            sleep_state="awake",
            rexp_banked_seconds=0,
            rexp_cycle_start=now,
            rexp_used_this_cycle_seconds=0,
            rexp_last_active_check=now,
            rexp_last_offline=None,
            exp_skill_state={
                "light_edge": {"pool": 40.0, "rank": 10, "rank_progress": 0.0},
            },
            stats={"intelligence": 30, "discipline": 30, "wisdom": 30},
        )
        self.ndb = SimpleNamespace(sleep_xp_block_notifications={})
        self.messages = []
        self.exp_skills = _DummyHandler({"light_edge": _DummySkill("light_edge", pool=40.0, last_trained=now - 9999)})

    def ensure_core_defaults(self):
        return None

    def ensure_sleep_defaults(self):
        return None

    def is_awake(self):
        return self.db.sleep_state == "awake"

    def is_in_light_sleep(self):
        return self.db.sleep_state == "light_sleep"

    def is_in_deep_sleep(self):
        return self.db.sleep_state == "deep_sleep"

    def is_asleep(self):
        return self.db.sleep_state in {"light_sleep", "deep_sleep"}

    def sync_client_state(self, *args, **kwargs):
        return None

    def msg(self, text):
        self.messages.append(str(text))

    def get_exp_skillset_tier(self, skill_name):
        return "primary"

    def _sync_exp_skill_state(self, skill_name, legacy_entry=None):
        return self.exp_skills.skills[skill_name]

    def _persist_exp_skill_state(self, skill):
        return None

    def auto_wake_if_sleeping(self, reason="activity"):
        if not self.is_asleep():
            return False
        self.db.sleep_state = "awake"
        self.messages.append(f"awake:{reason}")
        return True


class SleepRestedExpRuntimeTests(unittest.TestCase):
    def test_sleep_command_advances_sleep_state_and_awake_resets(self):
        caller = _DummyCharacter()

        with patch("commands.cmd_sleep.send_untargeted_action"):
            CmdSleep.func(SimpleNamespace(caller=caller))
            self.assertEqual(caller.db.sleep_state, "light_sleep")
            CmdSleep.func(SimpleNamespace(caller=caller))
            self.assertEqual(caller.db.sleep_state, "deep_sleep")

        with patch("commands.cmd_awake.send_untargeted_action"):
            CmdAwake.func(SimpleNamespace(caller=caller))

        self.assertEqual(caller.db.sleep_state, "awake")

    def test_award_xp_is_blocked_while_asleep(self):
        caller = _DummyCharacter()
        caller.db.sleep_state = "light_sleep"

        with patch("engine.services.messaging.send_untargeted_action"):
            result = SkillService.award_xp(caller, "light_edge", 25)

        self.assertTrue(result.success)
        self.assertEqual(result.amount, 0.0)

    def test_update_rexp_banking_banks_after_idle_threshold(self):
        caller = _DummyCharacter()
        caller.db.exp_skill_state = {}
        caller.db.rexp_last_active_check = 0

        banked = update_rexp_banking(caller, now=600)

        self.assertEqual(banked, 150)
        self.assertEqual(caller.db.rexp_banked_seconds, 150)

    def test_group_pulse_consumes_rexp_once_and_triples_drain(self):
        caller = _DummyCharacter()
        caller.db.rexp_banked_seconds = 120
        caller.db.rexp_used_this_cycle_seconds = 0
        skill = caller.exp_skills.skills["light_edge"]
        skill.last_trained = time.time() - 9999
        caller.db.sleep_state = "light_sleep"

        with patch("engine.services.pulse_service.pulse") as pulse_mock:
            processed = PulseService.process_skill_pulse(caller, global_tick=0, skill_group_offsets={0: 0})

        self.assertEqual(processed, 1)
        pulse_mock.assert_called_once()
        self.assertEqual(pulse_mock.call_args.kwargs["drain_multiplier"], 3.0)
        self.assertEqual(caller.db.rexp_banked_seconds, 120 - REXP_CONSUMPTION_PER_GROUP_PULSE)

    def test_deep_sleep_skips_group_pulse(self):
        caller = _DummyCharacter()
        caller.db.sleep_state = "deep_sleep"

        with patch("engine.services.pulse_service.pulse") as pulse_mock:
            processed = PulseService.process_skill_pulse(caller, global_tick=0, skill_group_offsets={0: 0})

        self.assertEqual(processed, 0)
        pulse_mock.assert_not_called()

    def test_offline_drain_reduces_pools_and_banks_rexp(self):
        caller = _DummyCharacter()
        caller.db.rexp_last_offline = 0

        drained = apply_offline_drain(caller, now=340)

        self.assertEqual(drained, 40)
        self.assertEqual(caller.exp_skills.skills["light_edge"].pool, 0.0)
        self.assertGreater(caller.db.rexp_banked_seconds, 0)

    def test_rexp_display_includes_sleep_state_and_cycle_values(self):
        caller = _DummyCharacter()
        caller.db.sleep_state = "deep_sleep"
        caller.db.rexp_banked_seconds = REXP_CAP_SECONDS
        caller.db.rexp_used_this_cycle_seconds = 1200

        display = get_rexp_display(caller, now=caller.db.rexp_cycle_start + 60)

        self.assertEqual(display["sleep_state"], "Deep Sleep")
        self.assertEqual(display["banked"], "4:00 hours")
        self.assertEqual(display["usable_this_cycle"], "3:40 hours")

    def test_consume_rexp_for_group_pulse_requires_actual_drain(self):
        caller = _DummyCharacter()
        caller.db.rexp_banked_seconds = 120

        consumed = consume_rexp_for_group_pulse(caller, group_drained=False)

        self.assertFalse(consumed)
        self.assertEqual(caller.db.rexp_banked_seconds, 120)
