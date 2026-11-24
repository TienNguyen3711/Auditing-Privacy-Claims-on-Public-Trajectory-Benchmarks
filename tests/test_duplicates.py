"""Duplicate scan on a tiny synthetic GeoLife tree."""
import shutil
import tempfile
import unittest
from pathlib import Path

from data_io.duplicates import report_md, scan

HEADER = "Geolife trajectory\nWGS 84\nAltitude is in Feet\nReserved 3\n0,2,255,My Track,0,0,2,8421376\n0\n"


def plt(rows):
    return HEADER + "".join(f"{lat},{lon},0,100,39744.1,2008-10-23,{t}\n" for lat, lon, t in rows)


class Duplicates(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        shared = [(39.98, 116.31, f"02:53:{s:02d}") for s in range(10)]
        own = [(39.90, 116.40, f"03:00:{s:02d}") for s in range(10)]
        for user, files in {"000": {"a.plt": shared, "b.plt": own}, "001": {"a.plt": shared},
                            "002": {"c.plt": [(39.98, 116.31, "02:53:00")] + own[:0]}}.items():
            d = self.root / user / "Trajectory"
            d.mkdir(parents=True)
            for name, rows in files.items():
                (d / name).write_text(plt(rows))

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_pairs_and_identical_files(self):
        r = scan(self.root)
        pairs = {(p["user_a"], p["user_b"]): p for p in r["pairs"]}
        self.assertEqual(pairs[("000", "001")]["shared_points"], 10)
        self.assertEqual(pairs[("000", "001")]["share_of_a"], 0.5)
        self.assertEqual(pairs[("000", "001")]["share_of_b"], 1.0)
        self.assertEqual(pairs[("000", "002")]["shared_points"], 1)
        self.assertNotIn(("001", "002"), pairs)  # a point is credited to its first holder only
        self.assertEqual(len(r["identical_files_across_users"]), 1)
        self.assertIn("| 000 | 001 | 10 |", report_md(r))


if __name__ == "__main__":
    unittest.main()
