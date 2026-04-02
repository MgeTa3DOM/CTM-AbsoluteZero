import pytest
from living.soul import Soul


def test_think_records():
    s = Soul()
    s.think("fn1", "enter", "hello")
    assert len(s.thoughts) == 1
    assert s.thoughts[0].fn == "fn1"


def test_recall():
    s = Soul()
    for i in range(20):
        s.think("f", "enter", str(i))
    assert len(s.recall(5)) == 5
    assert s.recall(5)[-1].msg == "19"


def test_errors_tracked():
    s = Soul()
    s.think("f", "enter", "ok")
    s.think("f", "error", "boom", confidence=0.0)
    assert len(s.errors()) == 1


def test_watcher_triggers_correction():
    s = Soul()

    def watch(t):
        if "danger" in t.msg:
            return "abort"
        return None

    s.watch(watch)
    t = s.think("f", "check", "danger ahead")
    assert t.event == "correction"
    assert "CORRECTED" in t.msg


def test_aware_decorator():
    s = Soul()

    @s.aware
    def add(a, b):
        return a + b

    assert add(1, 2) == 3
    events = [t.event for t in s.thoughts]
    assert "enter" in events
    assert "exit" in events


def test_aware_captures_error():
    s = Soul()

    @s.aware
    def fail():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        fail()

    assert len(s.errors()) == 1


def test_low_confidence():
    s = Soul()
    s.think("f", "check", "unsure", confidence=0.3)
    s.think("f", "check", "sure", confidence=0.9)
    assert len(s.low_confidence(0.5)) == 1
