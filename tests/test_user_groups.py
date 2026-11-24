"""User groups (policy (a)) and loading a group as one person."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from data_io import user_groups
from data_io.geolife import load_group

HEADER = "Geolife trajectory\nWGS 84\nAltitude is in Feet\nReserved 3\n0,2,255,My Track,0,0,2,8421376\n0\n"


class Groups(unittest.TestCase):
    def test_connected_components_and_ids(self):
        pairs = [{"user_a": "003", "user_b": "007", "shared_points": 5},
                 {"user_a": "007", "user_b": "001", "shared_points": 1},
                 {"user_a": "002", "user_b": "004", "shared_points": 1}]
        g = user_groups.build(["000", "001", "002", "003", "004", "007"], pairs)
        self.assertEqual(g, {"g000": ["000"], "g001": ["001", "003", "007"], "g002": ["002", "004"]})
        g2 = user_groups.build(["000", "001", "002", "003", "004", "007"], pairs, min_shared_points=2)
        self.assertEqual(g2["g003"], ["003", "007"])
        self.assertEqual(g2["g001"], ["001"])

    def test_committed_group_file_covers_all_users_once(self):
        doc = json.loads(user_groups.DEFAULT_OUT.read_text())
        members = [u for m in doc["groups"].values() for u in m]
        self.assertEqual(len(members), len(set(members)))
        self.assertEqual(len(members), doc["n_users"])
        self.assertEqual(len(doc["groups"]), doc["n_groups"])


class LoadGroup(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        rows = {"000": ["39.98,116.31,0,100,39744.1,2008-10-23,02:53:00", "39.98,116.32,0,100,39744.1,2008-10-23,02:54:00"],
                "003": ["39.98,116.31,0,100,39744.1,2008-10-23,02:53:00", "39.97,116.30,0,100,39744.1,2008-10-23,03:00:00"]}
        for u, lines in rows.items():
            d = self.root / u / "Trajectory"
            d.mkdir(parents=True)
            (d / "a.plt").write_text(HEADER + "\n".join(lines) + "\n")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_union_keeps_shared_point_once(self):
        pts = load_group(["000", "003"], self.root)
        self.assertEqual(len(pts), 3)
        self.assertEqual([p.t for p in pts], sorted(p.t for p in pts))


if __name__ == "__main__":
    unittest.main()
