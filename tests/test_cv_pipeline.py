import unittest

import numpy as np

from world.area_forge.extract.cv_pipeline import corridors_to_edges, extract_corridor_graph


class CvPipelineTests(unittest.TestCase):
    def test_extract_corridor_graph_aborts_when_junction_count_exceeds_threshold(self):
        line_mask = np.zeros((40, 40), dtype=np.uint8)
        for center_x in (10, 30):
            line_mask[15:26, center_x] = 255
            line_mask[20, center_x - 5:center_x + 6] = 255

        with self.assertWarnsRegex(RuntimeWarning, "junction count 2 exceeded threshold 1"):
            graph = extract_corridor_graph(
                line_mask,
                cfg={
                    "max_junction_count": 1,
                    "junction_count_reference_p95": 0,
                    "junction_count_reference_multiplier": 0,
                },
            )

        self.assertEqual(graph["segments"], [])
        self.assertEqual(graph["junctions"], [])
        self.assertEqual(graph["overflow"], {"raw_junction_count": 2, "junction_threshold": 1})

    def test_extract_corridor_graph_uses_higher_reference_threshold(self):
        line_mask = np.zeros((40, 40), dtype=np.uint8)
        for center_x in (10, 30):
            line_mask[15:26, center_x] = 255
            line_mask[20, center_x - 5:center_x + 6] = 255

        graph = extract_corridor_graph(
            line_mask,
            cfg={
                "max_junction_count": 1,
                "junction_count_reference_p95": 1,
                "junction_count_reference_multiplier": 3,
            },
        )

        self.assertEqual(len(graph["junctions"]), 2)
        self.assertNotIn("overflow", graph)

    def test_corridors_to_edges_bridges_dead_end_stub_chain_through_junction(self):
        rooms = [
            {"id": "room_a", "x": 370, "y": 404, "w": 10, "h": 10, "bbox": {"x": 365, "y": 399, "w": 10, "h": 10}},
            {"id": "room_b", "x": 460, "y": 404, "w": 10, "h": 10, "bbox": {"x": 455, "y": 399, "w": 10, "h": 10}},
            {"id": "room_c", "x": 500, "y": 404, "w": 10, "h": 10, "bbox": {"x": 495, "y": 399, "w": 10, "h": 10}},
        ]
        corridors = [
            {
                "id": "stub_a",
                "dead_end": True,
                "endpoints": [{"x": 366, "y": 404}, {"x": 384, "y": 404}],
                "pixels": [{"x": x, "y": 404} for x in range(366, 385)],
            },
            {
                "id": "stub_chain",
                "dead_end": True,
                "endpoints": [{"x": 384, "y": 404}, {"x": 457, "y": 404}],
                "pixels": [{"x": x, "y": 404} for x in range(384, 458)],
            },
            {
                "id": "spine",
                "dead_end": False,
                "endpoints": [{"x": 457, "y": 404}, {"x": 500, "y": 404}],
                "pixels": [{"x": x, "y": 404} for x in range(457, 501)],
            },
        ]
        junctions = [
            {"id": "j_left", "x": 381, "y": 404},
            {"id": "j_right", "x": 460, "y": 404},
        ]
        attachments = {
            "stub_a": ["room_a"],
            "stub_chain": ["room_a"],
            "spine": ["room_b", "room_c"],
        }

        edges = corridors_to_edges(rooms, corridors, attachments, junctions)
        edge_keys = {(edge["source"], edge["direction"], edge["target"]): edge for edge in edges}

        self.assertIn(("room_a", "east", "room_b"), edge_keys)
        self.assertEqual(edge_keys[("room_a", "east", "room_b")]["derivation_method"], "junction_bridge")
        self.assertIn(("room_b", "west", "room_a"), edge_keys)


if __name__ == "__main__":
    unittest.main()