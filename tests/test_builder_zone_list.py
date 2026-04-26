import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django

django.setup()

from web.views import _serialize_yaml_builder_zones


class BuilderZoneListTests(unittest.TestCase):
    def test_serialize_yaml_builder_zones_ignores_raw_snapshots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zones_dir = Path(temp_dir)

            canonical_zone = zones_dir / "crossingV2.yaml"
            raw_snapshot = zones_dir / "crossingV2.raw.yaml"

            payload = {
                "schema_version": "v1",
                "zone_id": "crossingv2",
                "name": "crossingV2",
                "generation_context": {},
                "rooms": [
                    {
                        "id": "crossingV2_628_178",
                        "name": "crossingV2_628_178",
                        "desc": "",
                        "stateful_descs": {},
                        "details": {},
                        "room_states": [],
                        "ambient": {"rate": 0, "messages": []},
                        "environment": "city",
                        "tags": {
                            "structure": None,
                            "specific_function": None,
                            "named_feature": None,
                            "condition": None,
                            "custom": [],
                        },
                        "items": [],
                        "npcs": [],
                        "zone_id": "crossingv2",
                        "map": {"x": 0, "y": 0, "layer": 0},
                        "exits": {},
                    }
                ],
                "placements": {"npcs": [], "items": []},
            }

            canonical_zone.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            raw_payload = dict(payload)
            raw_payload["zone_id"] = "crossingV2"
            raw_snapshot.write_text(yaml.safe_dump(raw_payload, sort_keys=False), encoding="utf-8")

            with patch("web.views._worlddata_zones_dir", return_value=zones_dir):
                zones = _serialize_yaml_builder_zones()

        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0]["id"], "crossingv2")
        self.assertEqual(zones[0]["name"], "crossingV2")


if __name__ == "__main__":
    unittest.main()