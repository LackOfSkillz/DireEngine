import unittest

from world.area_forge.extract.yaml_graph import _infer_special_target_text


class YamlGraphTests(unittest.TestCase):
    def test_infer_special_target_text_handles_uppercase_to(self):
        self.assertEqual(_infer_special_target_text("Climb Rope To Hvaral"), "Hvaral")


if __name__ == "__main__":
    unittest.main()