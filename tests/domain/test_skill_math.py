import unittest

from world.systems.skills import MINDSTATE_MAX, calculate_mindstate


class SkillMathTests(unittest.TestCase):
    def test_mindstate_clamps_to_bounds(self):
        self.assertEqual(calculate_mindstate(0, 100), 0)
        self.assertEqual(calculate_mindstate(500, 100), MINDSTATE_MAX)

    def test_mindstate_increases_with_pool(self):
        low = calculate_mindstate(10, 100)
        high = calculate_mindstate(60, 100)
        self.assertLess(low, high)


if __name__ == "__main__":
    unittest.main()