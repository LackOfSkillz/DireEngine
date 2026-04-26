import unittest

from world.area_forge.build.review_normalization import _cluster_axis_with_lane_limit


class ReviewNormalizationTests(unittest.TestCase):
    def test_cluster_axis_with_lane_limit_relaxes_threshold_until_under_cap(self):
        values = [index * 13 for index in range(45)]

        lanes, threshold = _cluster_axis_with_lane_limit(values, threshold=12, max_lanes=40)

        self.assertLessEqual(len(lanes), 40)
        self.assertGreaterEqual(threshold, 16)


if __name__ == "__main__":
    unittest.main()