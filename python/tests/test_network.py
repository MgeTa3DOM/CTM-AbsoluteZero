from living.network import Collective


def test_collective_spawn():
    c = Collective()
    a = c.spawn("alice")
    b = c.spawn("bob")
    assert len(c.agents) == 2
    assert c.net.count() == 2  # two join broadcasts


def test_agents_share_results():
    c = Collective()
    a = c.spawn("alice")
    b = c.spawn("bob")

    a.add_skill("upper", str.upper)
    b.add_skill("upper", str.upper)

    results = c.run_all("upper", "hello")
    assert results["alice"]["result"] == "HELLO"
    assert results["bob"]["result"] == "HELLO"


def test_evolution_notifies_peers():
    c = Collective()
    a = c.spawn("alice")
    b = c.spawn("bob")

    sk_a = a.add_skill("f", lambda x: x)
    sk_a.add_test(1, 1)
    sk_b = b.add_skill("f", lambda x: x)
    sk_b.add_test(1, 1)

    a.evolve("f", lambda x: x, "improve")

    # Bob should have received a message about Alice's evolution
    evo_msgs = c.net.query(topic="skill_evolved")
    assert len(evo_msgs) == 1
    assert evo_msgs[0].sender == "alice"


def test_collective_handles_errors():
    c = Collective()
    a = c.spawn("alice")
    a.add_skill("boom", lambda: (_ for _ in ()).throw(RuntimeError("fail")))

    results = c.run_all("boom")
    assert results["alice"]["ok"] is False


def test_shared_memory_query():
    c = Collective()
    a = c.spawn("alice")
    a.add_skill("f", lambda x: x * 2)

    a.run("f", 5)
    a.run("f", 10)

    msgs = c.net.query(topic="execution", sender="alice")
    assert len(msgs) == 2
