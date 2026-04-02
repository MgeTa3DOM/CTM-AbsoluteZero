from living.soul import Soul
from living.growth import GrowthTracker


def test_measure():
    s = Soul()
    for i in range(50):
        s.think("f", "enter", f"step {i}")
    g = GrowthTracker(s)
    snap = g.measure()
    assert snap.ratio > 1.0
    assert snap.patterns > 0
    assert 0 <= snap.score <= 1.0


def test_trend_insufficient():
    s = Soul()
    g = GrowthTracker(s)
    assert g.trend() == "insufficient"


def test_score_components():
    s = Soul()
    for i in range(100):
        s.think("f", "enter", f"data point {i}")
    g = GrowthTracker(s)
    snap = g.measure(error_rate=0.0, evolutions=5)
    assert snap.score > 0  # good compression + no errors + some evolution
