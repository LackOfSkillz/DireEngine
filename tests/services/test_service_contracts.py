import unittest

from engine.services.result import ActionResult
from engine.services.state_service import StateService


class DummyTarget:
    def __init__(self):
        self.db = type("DB", (), {"hp": 100})()
        self.balance = None
        self.fatigue = None
        self.roundtime = None

    def set_hp(self, value):
        self.db.hp = int(value)

    def set_balance(self, value):
        self.balance = value

    def set_fatigue(self, value):
        self.fatigue = value

    def set_roundtime(self, value):
        self.roundtime = value

    def apply_thief_roundtime(self, value):
        self.roundtime = ("ambush", value)


class ServiceContractTests(unittest.TestCase):
    def test_action_result_properties(self):
        result = ActionResult.ok(data={"amount": 5, "hit": True, "damage": 7, "roundtime": 2.5})
        self.assertTrue(result.success)
        self.assertEqual(result.amount, 5.0)
        self.assertTrue(result.hit)
        self.assertEqual(result.damage, 7)
        self.assertEqual(result.roundtime, 2.5)

    def test_state_service_returns_action_result(self):
        target = DummyTarget()
        damage_result = StateService.apply_damage(target, 12)
        self.assertTrue(damage_result.success)
        self.assertEqual(damage_result.amount, 12.0)
        self.assertEqual(target.db.hp, 88)

        balance_result = StateService.apply_balance(target, 77)
        fatigue_result = StateService.apply_fatigue(target, 11)
        roundtime_result = StateService.apply_roundtime(target, 3)

        self.assertTrue(balance_result.success)
        self.assertTrue(fatigue_result.success)
        self.assertTrue(roundtime_result.success)
        self.assertEqual(target.balance, 77)
        self.assertEqual(target.fatigue, 11)
        self.assertEqual(target.roundtime, 3)


if __name__ == "__main__":
    unittest.main()