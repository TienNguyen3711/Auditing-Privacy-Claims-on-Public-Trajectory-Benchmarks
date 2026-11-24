"""Geometric control and grid cloaking (offline)."""
import unittest

from controls.geometric import Rotation
from data_io.geo import haversine_m
from mechanisms.cloaking import GridCloak
from tests.synthetic import HOME, synthetic_user


class ControlsMechanisms(unittest.TestCase):
    def test_rotation_preserves_distances_and_moves_points(self):
        pts = synthetic_user()
        rot = Rotation.about_centroid(pts, 135)
        rp = rot.points(pts)
        for i in range(0, len(pts) - 1, 7):
            d0 = haversine_m(pts[i].lat, pts[i].lon, pts[i + 1].lat, pts[i + 1].lon)
            d1 = haversine_m(rp[i].lat, rp[i].lon, rp[i + 1].lat, rp[i + 1].lon)
            self.assertAlmostEqual(d0, d1, delta=max(1.0, 0.002 * d0))
        self.assertGreater(haversine_m(*rot.latlon(*HOME), *HOME), 1000)
        self.assertEqual([p.t for p in pts], [p.t for p in rp])

    def test_cloak_error_bounded_by_half_diagonal(self):
        cloak = GridCloak(500)
        for p, c in zip(synthetic_user(), cloak.apply(synthetic_user())):
            self.assertLessEqual(haversine_m(p.lat, p.lon, c.lat, c.lon), 500 * 2 ** 0.5 / 2 + 1)


if __name__ == "__main__":
    unittest.main()
