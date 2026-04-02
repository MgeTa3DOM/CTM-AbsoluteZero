"""Skill — Versioned self-modifying functions.

A Skill wraps a callable.  It tracks every version, why it changed,
and measures performance.  When `evolve()` is called, the candidate
is tested against the current implementation.  Only accepted if
score improves (or stays equal).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from living.soul import Soul


@dataclass(slots=True)
class Version:
    v: int
    source: str
    reason: str
    author: str           # human | self | peer
    ts: float
    metrics: dict[str, float] = field(default_factory=dict)
    parent: int | None = None


@dataclass(slots=True)
class TestCase:
    input: Any
    expected: Any
    weight: float = 1.0


class Skill:
    __slots__ = ("name", "soul", "_fn", "_tests", "_versions",
                 "_calls", "_errors", "_latency")

    def __init__(self, name: str, fn: Callable, soul: Soul, source: str = ""):
        self.name = name
        self.soul = soul
        self._fn = fn
        self._tests: list[TestCase] = []
        self._versions: list[Version] = [
            Version(0, source or f"<init:{name}>", "initial", "human", time.time())
        ]
        self._calls = 0
        self._errors = 0
        self._latency = 0.0

    @property
    def version(self) -> Version:
        return self._versions[-1]

    @property
    def versions(self) -> list[Version]:
        return list(self._versions)

    def __call__(self, *args: Any, **kw: Any) -> Any:
        self._calls += 1
        t0 = time.perf_counter()
        try:
            r = self._fn(*args, **kw)
            dt = time.perf_counter() - t0
            self._latency += dt
            self.soul.think(f"skill:{self.name}", "exit",
                            f"{self.name} v{self.version.v} ok ({dt*1e3:.1f}ms)")
            return r
        except Exception as e:
            self._errors += 1
            self.soul.think(f"skill:{self.name}", "error",
                            f"{self.name} v{self.version.v} FAIL: {e}",
                            confidence=0.0)
            raise

    def add_test(self, inp: Any, expected: Any, weight: float = 1.0):
        self._tests.append(TestCase(inp, expected, weight))

    def evaluate(self, fn: Callable | None = None) -> tuple[float, list[str]]:
        fn = fn or self._fn
        if not self._tests:
            return 1.0, []
        total = sum(t.weight for t in self._tests)
        passed = 0.0
        fails: list[str] = []
        for tc in self._tests:
            try:
                got = fn(tc.input)
                if got == tc.expected:
                    passed += tc.weight
                else:
                    fails.append(f"{tc.input!r}: got {got!r}, want {tc.expected!r}")
            except Exception as e:
                fails.append(f"{tc.input!r}: {e}")
        return passed / total if total else 0.0, fails

    def evolve(self, new_fn: Callable, reason: str,
               source: str = "", author: str = "self") -> bool:
        old_score, _ = self.evaluate()
        new_score, _ = self.evaluate(new_fn)

        self.soul.think(f"skill:{self.name}", "check",
                        f"evolve? v{self.version.v} {old_score:.2f} -> candidate {new_score:.2f}",
                        confidence=new_score)

        if new_score >= old_score:
            v = Version(
                self.version.v + 1, source, reason, author, time.time(),
                {"score": new_score, "delta": new_score - old_score},
                self.version.v,
            )
            self._versions.append(v)
            self._fn = new_fn
            self._calls = self._errors = 0
            self._latency = 0.0
            self.soul.think(f"skill:{self.name}", "correction",
                            f"EVOLVED v{v.parent} -> v{v.v}: {reason}")
            return True

        self.soul.think(f"skill:{self.name}", "check",
                        f"REJECTED: {new_score:.2f} < {old_score:.2f}")
        return False

    @property
    def error_rate(self) -> float:
        return self._errors / self._calls if self._calls else 0.0

    def stats(self) -> dict[str, Any]:
        return {
            "name": self.name, "version": self.version.v,
            "total_versions": len(self._versions),
            "calls": self._calls, "error_rate": round(self.error_rate, 3),
            "tests": len(self._tests),
        }
