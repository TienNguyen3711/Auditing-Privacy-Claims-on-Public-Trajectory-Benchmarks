"""Synthetic trajectories shared by the offline tests (no data files)."""
import datetime as dt

from data_io.geolife import Point

HOME, WORK = (39.98, 116.31), (39.91, 116.40)


def synthetic_user(days=5):
    """Logger on in the evening at home, off overnight, on in the morning; a work stay at noon."""
    pts = []
    for d in range(days):
        day = dt.datetime(2008, 10, 20 + d)
        for m in range(0, 40, 2):
            pts.append(Point(day + dt.timedelta(hours=21, minutes=m), HOME[0] + 1e-5 * m, HOME[1]))
        pts.append(Point(day + dt.timedelta(days=1, hours=7), HOME[0], HOME[1] + 2e-5))
        for m in range(0, 60, 5):
            pts.append(Point(day + dt.timedelta(days=1, hours=12, minutes=m), WORK[0], WORK[1]))
    return sorted(pts, key=lambda p: p.t)
