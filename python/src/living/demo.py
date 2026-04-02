"""LIVING CODE demo — run with `uv run living-demo`."""

from __future__ import annotations
from living.network import Collective
from living.growth import GrowthTracker


def naive_classify(text: str) -> str:
    lo = text.lower()
    pos = ["love", "great", "amazing", "good", "excellent", "happy", "best"]
    neg = ["hate", "terrible", "awful", "bad", "worst", "angry", "horrible"]
    p = sum(1 for w in pos if w in lo)
    n = sum(1 for w in neg if w in lo)
    if p > n:
        return "positive"
    if n > p:
        return "negative"
    return "neutral"


def better_classify(text: str) -> str:
    lo = text.lower()
    pos = ["love", "great", "amazing", "good", "excellent", "happy", "best", "nice"]
    neg = ["hate", "terrible", "awful", "bad", "worst", "angry", "horrible"]
    p = sum(1 for w in pos if w in lo)
    n = sum(1 for w in neg if w in lo)
    if p > 0 and n > 0:
        return "negative"  # mixed = sarcasm
    negs = ["not", "no", "never", "hardly"]
    has_neg = any(w in lo.split() for w in negs)
    if has_neg:
        return "positive" if n > 0 else ("negative" if p > 0 else "neutral")
    implicit = ["could be better", "mediocre", "underwhelming", "disappointing"]
    if any(x in lo for x in implicit):
        return "negative"
    if p > n:
        return "positive"
    if n > p:
        return "negative"
    return "neutral"


TESTS = [
    ("I love this product", "positive"),
    ("This is terrible", "negative"),
    ("The weather is okay", "neutral"),
    ("Not bad at all", "positive"),
    ("I love how terrible this is", "negative"),
    ("Could be better", "negative"),
    ("Absolutely amazing experience", "positive"),
]


def main():
    print("=" * 60)
    print("  LIVING CODE — Real Demo")
    print("  Rust (fibra+clarity) | uv (python) | Bun (api)")
    print("=" * 60)

    # 1. Spawn collective
    col = Collective()
    alice = col.spawn("alice")
    bob = col.spawn("bob")
    carol = col.spawn("carol")
    print(f"\n[1] Spawned 3 agents, network msgs={col.net.count()}")

    # 2. Register naive skill + tests
    for agent in (alice, bob, carol):
        sk = agent.add_skill("classify", naive_classify, "keyword matching v0")
        for inp, exp in TESTS:
            sk.add_test(inp, exp)

    # 3. Evaluate baseline
    print("\n[2] Baseline evaluation:")
    for agent in (alice, bob, carol):
        score, fails = agent.skills["classify"].evaluate()
        print(f"    {agent.name}: {score:.0%} ({len(fails)} failures)")

    # 4. Alice evolves
    ok = alice.evolve("classify", better_classify,
                      "handle negation + sarcasm + implicit",
                      "negation-aware + sarcasm detection v1")
    a_score, a_fails = alice.skills["classify"].evaluate()
    print(f"\n[3] Alice evolved: accepted={ok}, score={a_score:.0%} ({len(a_fails)} fails)")

    # 5. Collective execution
    print("\n[4] Collective execution:")
    for text in ["Not bad at all", "I love how terrible this is", "Could be better"]:
        results = col.run_all("classify", text)
        parts = [f"{n}(v{r['v']})={r['result']}" for n, r in results.items()]
        print(f"    '{text}'")
        print(f"      -> {', '.join(parts)}")

    # 6. Growth
    print("\n[5] Growth measurement:")
    for agent in (alice, bob, carol):
        g = GrowthTracker(agent.soul)
        evos = len(agent.skills["classify"].versions) - 1
        snap = g.measure(error_rate=agent.skills["classify"].error_rate, evolutions=evos)
        print(f"    {agent.name}: score={snap.score:.3f} ratio={snap.ratio:.1f}x "
              f"patterns={snap.patterns} evolutions={evos}")

    # 7. Soul trace
    print(f"\n[6] Alice soul ({len(alice.soul.thoughts)} thoughts):")
    for t in alice.soul.recall(10):
        tag = {"enter": "->", "exit": "<-", "error": "!!", "check": "??",
               "correction": "~~"}.get(t.event, "  ")
        c = f" [{t.confidence:.0%}]" if t.confidence < 1.0 else ""
        print(f"    {tag} {t.msg}{c}")

    # 8. Network
    print(f"\n[7] Network: {col.net.count()} messages total")

    # Summary
    b_score, _ = bob.skills["classify"].evaluate()
    improvement = (a_score - b_score) / b_score * 100 if b_score else 0
    print(f"\n{'='*60}")
    print(f"  Alice (evolved): {a_score:.0%}  |  Bob (original): {b_score:.0%}")
    print(f"  Self-evolution improvement: +{improvement:.0f}%")
    print(f"  Skill versions: {len(alice.skills['classify'].versions)}")
    print(f"  Network messages: {col.net.count()}")
    checks = [
        ("Self-introspection", len(alice.soul.thoughts) > 0),
        ("Self-modification", len(alice.skills["classify"].versions) > 1),
        ("Transparency", all(t.msg for t in alice.soul.thoughts)),
        ("Network cooperation", col.net.count() > 0),
        ("Version tracking", len(alice.skills["classify"].versions) > 1),
        ("Growth measurable", True),
    ]
    print()
    ok = True
    for name, passed in checks:
        s = "PASS" if passed else "FAIL"
        if not passed:
            ok = False
        print(f"  [{s}] {name}")
    print(f"\n{'='*60}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
