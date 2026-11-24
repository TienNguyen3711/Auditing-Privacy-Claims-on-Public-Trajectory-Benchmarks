"""SQ2 attack pipeline: segments, baseline, original vs control, answer parsing (offline, no LLM)."""
import unittest

from attacks.home_inference import baseline_home, parse_latlon, segments, shown_segments
from controls.geometric import Rotation
from data_io.geo import haversine_m
from mechanisms.cloaking import GridCloak
from tests.synthetic import HOME, synthetic_user


class Pipeline(unittest.TestCase):
    def test_baseline_finds_home_cell(self):
        segs = shown_segments(segments(GridCloak(500).apply(synthetic_user())))
        self.assertLess(haversine_m(*baseline_home(segs), *HOME), 400)

    def test_control_of_cloaked_output_keeps_segments(self):
        pts = synthetic_user()
        cloaked = GridCloak(500).apply(pts)
        orig = shown_segments(segments(cloaked))
        ctrl = shown_segments(segments(Rotation.about_centroid(pts, 200).points(cloaked)))
        self.assertEqual([(s.start, s.end) for s in orig], [(s.start, s.end) for s in ctrl])
        self.assertTrue(all((o.lat, o.lon) != (c.lat, c.lon) for o, c in zip(orig, ctrl)))

    def test_parse(self):
        self.assertEqual(parse_latlon('<think>x</think>{"lat": 39.98, "lon": 116.31}'), (39.98, 116.31))
        self.assertEqual(parse_latlon("Home is at 39.98, 116.31."), (39.98, 116.31))
        self.assertIsNone(parse_latlon("I cannot tell."))


if __name__ == "__main__":
    unittest.main()
