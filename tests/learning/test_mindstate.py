import unittest

from domain.learning.mindstate import MINDSTATE_BANDS, get_mindstate_band, get_mindstate_name, is_mind_locked


class MindstateBandTests(unittest.TestCase):
    def test_all_35_bands_exist(self):
        self.assertEqual(sorted(MINDSTATE_BANDS.keys()), list(range(35)))

    def test_all_bands_have_names_and_descriptions(self):
        for band in MINDSTATE_BANDS.values():
            self.assertTrue(band.name)
            self.assertTrue(band.short_name)
            self.assertTrue(band.description)

    def test_only_mind_lock_is_locked(self):
        locked_values = [band.value for band in MINDSTATE_BANDS.values() if band.is_locked]
        self.assertEqual(locked_values, [34])

    def test_pulse_modifier_never_decreases(self):
        values = [MINDSTATE_BANDS[index].pulse_modifier for index in range(35)]
        self.assertEqual(values, sorted(values))

    def test_lookup_helpers(self):
        self.assertEqual(get_mindstate_band(0).name, "clear")
        self.assertEqual(get_mindstate_name(34), "mind lock")
        self.assertTrue(is_mind_locked(34))
        self.assertFalse(is_mind_locked(33))

    def test_out_of_range_values_clamp_to_clear(self):
        self.assertEqual(get_mindstate_band(-1).name, "clear")
        self.assertEqual(get_mindstate_band(35).name, "clear")

    def test_verified_ordering_examples(self):
        self.assertEqual(get_mindstate_name(2), "perusing")
        self.assertEqual(get_mindstate_name(3), "learning")
        self.assertEqual(get_mindstate_name(15), "absorbing")
        self.assertEqual(get_mindstate_name(20), "focused")
        self.assertEqual(get_mindstate_name(33), "nearly locked")


if __name__ == "__main__":
    unittest.main()