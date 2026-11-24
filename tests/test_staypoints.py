"""Stay points, night hours and home ground-truth quality (offline)."""
import datetime as dt
import unittest

from data_io.geo import haversine_m
from data_io.geolife import Point
from data_io.staypoints import assess_home, detect_stays, home_location, night_hours
from tests.synthetic import HOME, WORK, synthetic_user


class StayPoints(unittest.TestCase):
    def test_night_hours(self):
        self.assertAlmostEqual(night_hours(dt.datetime(2008, 1, 1, 21), dt.datetime(2008, 1, 2, 7)), 8.0)
        self.assertEqual(night_hours(dt.datetime(2008, 1, 1, 9), dt.datetime(2008, 1, 1, 17)), 0.0)

    def test_home_from_overnight_gap(self):
        home = home_location(detect_stays(synthetic_user()))
        self.assertIsNotNone(home)
        self.assertLess(haversine_m(*home, *HOME), 100)

    def test_stay_does_not_span_long_recording_gap(self):
        t0 = dt.datetime(2008, 9, 11, 5)
        pts = [Point(t0 + dt.timedelta(minutes=m), *HOME) for m in range(0, 30, 5)]
        pts += [Point(t0 + dt.timedelta(days=8, minutes=m), *HOME) for m in range(0, 30, 5)]
        stays = detect_stays(pts)
        self.assertEqual(len(stays), 2)
        self.assertTrue(all((s.end - s.start) < dt.timedelta(hours=1) for s in stays))


class HomeQuality(unittest.TestCase):
    def test_assess_home_passes_clear_case(self):
        pts = synthetic_user()
        a = assess_home(pts, detect_stays(pts))
        self.assertTrue(a.passed, a.reasons)
        self.assertLess(haversine_m(*a.home, *HOME), 100)
        self.assertEqual(a.night_share, 1.0)

    def test_assess_home_flags_split_nights_and_far_home(self):
        far = (39.30, 117.10)  # synthetic place about 90 km from HOME

        def nights_at(places, days):
            pts = []
            for d in range(days):  # nights cycle through places; daytime data near WORK
                place = places[d % len(places)]
                day = dt.datetime(2008, 10, 1 + d)
                pts.append(Point(day + dt.timedelta(hours=21), *place))
                pts.append(Point(day + dt.timedelta(days=1, hours=7), *place))
                pts += [Point(day + dt.timedelta(days=1, hours=12, minutes=m), *WORK) for m in range(60)]
            return sorted(pts, key=lambda p: p.t)

        pts = nights_at([HOME, far, (39.95, 116.35)], 9)   # three places, 3 nights each: share about 0.33
        a = assess_home(pts, detect_stays(pts))
        self.assertFalse(a.passed)
        self.assertTrue(any("night share" in r for r in a.reasons), a.reasons)
        pts = nights_at([far], 5)                            # always sleeps about 90 km from where the data is
        b = assess_home(pts, detect_stays(pts))
        self.assertTrue(any("km from data median" in r for r in b.reasons), b.reasons)
        self.assertFalse(any("night share" in r for r in b.reasons), b.reasons)


if __name__ == "__main__":
    unittest.main()
