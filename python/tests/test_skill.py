from living.soul import Soul
from living.skill import Skill


def test_skill_call():
    s = Soul()
    sk = Skill("upper", str.upper, s, "str.upper")
    assert sk("hello") == "HELLO"
    assert sk.stats()["calls"] == 1


def test_skill_evaluation():
    s = Soul()
    sk = Skill("upper", str.upper, s)
    sk.add_test("hello", "HELLO")
    sk.add_test("world", "WORLD")
    score, fails = sk.evaluate()
    assert score == 1.0
    assert fails == []


def test_skill_evolve_accepted():
    s = Soul()
    sk = Skill("classify", lambda t: "pos" if "good" in t else "neg", s)
    sk.add_test("good stuff", "pos")
    sk.add_test("bad stuff", "neg")
    sk.add_test("not bad", "pos")  # naive fails this

    old_score, _ = sk.evaluate()
    assert old_score < 1.0

    def better(t):
        if "not bad" in t:
            return "pos"
        return "pos" if "good" in t else "neg"

    assert sk.evolve(better, "handle negation")
    assert sk.version.v == 1
    new_score, _ = sk.evaluate()
    assert new_score > old_score


def test_skill_evolve_rejected():
    s = Soul()
    sk = Skill("id", lambda x: x, s)
    sk.add_test(1, 1)
    sk.add_test(2, 2)

    # Worse function
    assert not sk.evolve(lambda x: 0, "break everything")
    assert sk.version.v == 0


def test_version_history():
    s = Soul()
    sk = Skill("f", lambda x: x, s)
    sk.add_test(1, 1)
    sk.evolve(lambda x: x, "no-op", author="peer")
    assert len(sk.versions) == 2
    assert sk.versions[1].author == "peer"
    assert sk.versions[1].parent == 0
