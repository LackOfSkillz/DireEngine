import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

from engine.services.wound_transfer_service import WoundTransferService


class _Patient:
    def __init__(self, wounds=None, location=None, profession="commoner"):
        self.key = "Patient"
        self.id = 22
        self.location = location
        self.messages = []
        self.db = SimpleNamespace(empath_saf_duration=0, empath_saf_burden=0, empath_permashock=False)
        self._profession = profession
        self._wounds = dict(wounds or {"bleeding": 35, "vitality": 0})

    def msg(self, text):
        self.messages.append(str(text))

    def get_empath_wounds(self):
        return dict(self._wounds)

    def get_profession(self):
        return self._profession

    def is_empath(self):
        return self._profession == "empath"


class _Empath:
    def __init__(self, patient=None, *, is_empath=True, empathy=10, fatigue=0, max_fatigue=100, position="standing", circle=5):
        self.key = "Empath"
        self.id = 11
        self.location = object()
        if patient is not None:
            patient.location = self.location
        self.patient = patient
        self.messages = []
        self.db = SimpleNamespace(fatigue=fatigue, max_fatigue=max_fatigue, position=position, circle=circle)
        self._is_empath = is_empath
        self._empathy = empathy
        self.take_calls = []

    def is_empath(self):
        return self._is_empath

    def get_fatigue(self):
        return self.db.fatigue, self.db.max_fatigue

    def set_fatigue(self, value):
        self.db.fatigue = max(0, min(int(value), int(self.db.max_fatigue)))

    def get_skill(self, skill_name):
        if skill_name == "empathy":
            return self._empathy
        return 0

    def get_circle(self):
        return self.db.circle

    def _sync_exp_skill_state(self, _skill_name):
        return None

    def get_empath_link_state(self, require_local=True, emit_break_messages=True):
        if self.patient is None:
            return None
        return {"target": self.patient}

    def take_empath_wound(self, wound_type, amount_spec="", **kwargs):
        self.take_calls.append({"wound_type": wound_type, "amount_spec": amount_spec, **kwargs})
        target = kwargs.get("target")
        normalized_wound = str(wound_type or "").strip().lower()
        if target is not None and hasattr(target, "_wounds") and normalized_wound in target._wounds:
            raw_amount = str(amount_spec or "").strip().lower()
            if raw_amount.isdigit():
                applied = min(int(raw_amount), int(target._wounds.get(normalized_wound, 0) or 0))
            else:
                applied = min(10, int(target._wounds.get(normalized_wound, 0) or 0))
            target._wounds[normalized_wound] = max(0, int(target._wounds.get(normalized_wound, 0) or 0) - applied)
        return True, "You draw the injury into yourself."

    def touch_empath_target(self, target):
        return True, [f"touch {target.key}"]

    def link_empath_target(self, target, persistent=False):
        if persistent:
            return True, [f"persistent {target.key}"]
        return True, [f"link {target.key}"]

    def mend_empath_self(self):
        return True, "You focus inward, stabilizing your condition."


class WoundTransferServiceTests(unittest.TestCase):
    def test_transfer_blocks_non_empaths(self):
        patient = _Patient()
        empath = _Empath(patient, is_empath=False)

        result = WoundTransferService.transfer(empath, patient, wound_type="bleeding", amount="10")

        self.assertFalse(result.success)
        self.assertIn("You cannot draw another's wounds into yourself.", result.errors)

    def test_transfer_blocks_prone_empath(self):
        patient = _Patient()
        empath = _Empath(patient, position="prone")

        result = WoundTransferService.transfer(empath, patient, wound_type="bleeding", amount="10")

        self.assertFalse(result.success)
        self.assertIn("You can't heal while lying down on the job!", result.errors)

    def test_transfer_blocks_exhausted_empath(self):
        patient = _Patient()
        empath = _Empath(patient, fatigue=90, max_fatigue=100)

        result = WoundTransferService.transfer(empath, patient, wound_type="bleeding", amount="10")

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "fatigue")

    def test_transfer_blocks_when_saf_is_active(self):
        patient = _Patient()
        empath = _Empath(patient)
        empath.db.empath_saf_duration = 10800

        result = WoundTransferService.transfer(empath, patient, wound_type="bleeding", amount="10")

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "saf")
        self.assertIn("spiritual shock", result.errors[0].lower())

    def test_transfer_uses_empathy_as_transference_substitute_for_advanced_wounds(self):
        patient = _Patient()
        empath = _Empath(patient, empathy=0)

        result = WoundTransferService.transfer(empath, patient, wound_type="poison", amount="10")

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "empathy_too_low")

    def test_transfer_caps_requested_amount_at_twenty(self):
        patient = _Patient(wounds={"bleeding": 55})
        empath = _Empath(patient)

        with patch("engine.services.wound_transfer_service.SkillService.award_xp"):
            result = WoundTransferService.transfer(empath, patient, wound_type="bleeding", amount="35")

        self.assertTrue(result.success)
        self.assertEqual(empath.take_calls[-1]["amount_spec"], "20")
        self.assertTrue(result.data["capped"])

    def test_transfer_requires_linked_patient_match(self):
        patient = _Patient()
        other = _Patient()
        empath = _Empath(patient)
        other.location = empath.location

        result = WoundTransferService.transfer(empath, other, wound_type="bleeding", amount="10")

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "wrong_patient")

    def test_transfer_emits_patient_relief_message(self):
        patient = _Patient()
        empath = _Empath(patient)

        with patch("engine.services.wound_transfer_service.SkillService.award_xp"):
            result = WoundTransferService.transfer(empath, patient, wound_type="bleeding", amount="10")

        self.assertTrue(result.success)
        self.assertEqual(patient.messages[-1], "You feel your pain lessen.")

    def test_transfer_awards_canonical_progression_xp_and_fatigue_cost(self):
        patient = _Patient(wounds={"bleeding": 35})
        empath = _Empath(patient, empathy=24, fatigue=18, circle=6)

        with patch("engine.services.wound_transfer_service.SkillService.award_xp") as award_xp:
            result = WoundTransferService.transfer(empath, patient, wound_type="bleeding", amount="10")

        self.assertTrue(result.success)
        self.assertEqual(result.data["transferred_amount"], 10)
        self.assertEqual(result.data["transferred_wound_type"], "bleeding")
        self.assertEqual(empath.db.fatigue, 15)
        self.assertEqual(empath.take_calls[-1]["learning_action"], "canonical_progression")
        award_xp.assert_has_calls(
            [
                call(empath, "primary_magic", 9),
                call(empath, "perception", 3),
                call(empath, "empathy", 40),
            ]
        )

    def test_transfer_skips_xp_for_empath_patient_but_keeps_fatigue_cost(self):
        patient = _Patient(wounds={"bleeding": 35}, profession="empath")
        empath = _Empath(patient, fatigue=18)

        with patch("engine.services.wound_transfer_service.SkillService.award_xp") as award_xp:
            result = WoundTransferService.transfer(empath, patient, wound_type="bleeding", amount="9")

        self.assertTrue(result.success)
        self.assertEqual(empath.db.fatigue, 15)
        award_xp.assert_not_called()

    def test_take_shock_rescues_permashocked_empath_patient(self):
        patient = _Patient(profession="empath")
        patient.db.empath_saf_duration = 999999
        patient.db.empath_saf_burden = 999
        patient.db.empath_permashock = True
        empath = _Empath(patient, circle=10)

        result = WoundTransferService.transfer(empath, patient, wound_type="shock")

        self.assertTrue(result.success)
        self.assertEqual(patient.db.empath_saf_duration, 0)
        self.assertFalse(bool(patient.db.empath_permashock))
        self.assertGreater(int(empath.db.empath_saf_duration or 0), 0)

    def test_take_shock_requires_circle_ten(self):
        patient = _Patient(profession="empath")
        patient.db.empath_saf_duration = 999999
        patient.db.empath_saf_burden = 999
        patient.db.empath_permashock = True
        empath = _Empath(patient, circle=9)

        result = WoundTransferService.transfer(empath, patient, wound_type="shock")

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "circle_too_low")

    def test_transfer_applies_poison_bonus_after_clamped_scaling(self):
        patient = _Patient(wounds={"poison": 25})
        empath = _Empath(patient, empathy=96, circle=12)

        with patch("engine.services.wound_transfer_service.SkillService.award_xp") as award_xp:
            result = WoundTransferService.transfer(empath, patient, wound_type="poison", amount="10")

        self.assertTrue(result.success)
        self.assertEqual(result.data["transferred_wound_type"], "poison")
        award_xp.assert_has_calls(
            [
                call(empath, "primary_magic", 9),
                call(empath, "perception", 3),
                call(empath, "empathy", 120),
            ]
        )

    def test_transfer_applies_disease_bonus_after_flooring_scale(self):
        patient = _Patient(wounds={"disease": 22})
        empath = _Empath(patient, empathy=3, circle=10)

        with patch("engine.services.wound_transfer_service.SkillService.award_xp") as award_xp:
            result = WoundTransferService.transfer(empath, patient, wound_type="disease", amount="10")

        self.assertTrue(result.success)
        award_xp.assert_has_calls(
            [
                call(empath, "primary_magic", 9),
                call(empath, "perception", 3),
                call(empath, "empathy", 70),
            ]
        )

    def test_touch_link_and_mend_wrap_existing_character_hooks(self):
        patient = _Patient()
        empath = _Empath(patient)

        touch = WoundTransferService.touch(empath, patient)
        link = WoundTransferService.link(empath, patient, persistent=True)
        mend = WoundTransferService.mend_self(empath)

        self.assertEqual(touch.messages, ["touch Patient"])
        self.assertEqual(link.messages, ["persistent Patient"])
        self.assertEqual(mend.messages, ["You focus inward, stabilizing your condition."])


if __name__ == "__main__":
    unittest.main()