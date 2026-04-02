"""
LIVING CODE - Skill: Versioned Self-Modification

Code that rewrites itself. Every version is tracked with:
- WHAT changed
- WHY it changed (detected by the soul)
- Performance delta before/after

Not a deploy pipeline. The code itself decides when to evolve.
"""

from __future__ import annotations

import time
import hashlib
import textwrap
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .soul import Soul, Thought


@dataclass
class SkillVersion:
    """One version of a skill (a function that can evolve)."""
    version: int
    source: str  # The actual source code / logic description
    created_at: float
    reason: str  # WHY this version exists
    metrics: dict[str, float] = field(default_factory=dict)
    parent_version: Optional[int] = None
    author: str = "system"  # "human", "self", "peer"

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.source.encode()).hexdigest()[:12]


@dataclass
class SkillTest:
    """A test case for evaluating skill performance."""
    input: Any
    expected: Any
    weight: float = 1.0  # Importance of this test case


class Skill:
    """
    A function that knows its own history and can rewrite itself.

    Each Skill wraps a callable. When performance drops or errors accumulate,
    the skill can accept a new implementation, test it, and swap if better.
    """

    def __init__(self, name: str, initial_fn: Callable, soul: Soul,
                 source: str = ""):
        self.name = name
        self.soul = soul
        self._fn = initial_fn
        self._tests: list[SkillTest] = []
        self._call_count = 0
        self._error_count = 0
        self._total_latency = 0.0

        self.versions: list[SkillVersion] = [
            SkillVersion(
                version=0,
                source=source or f"<initial: {name}>",
                created_at=time.time(),
                reason="initial implementation",
                author="human",
            )
        ]

    @property
    def current_version(self) -> SkillVersion:
        return self.versions[-1]

    def __call__(self, *args, **kwargs) -> Any:
        """Execute the skill, tracking performance."""
        self._call_count += 1
        start = time.time()

        try:
            result = self._fn(*args, **kwargs)
            latency = time.time() - start
            self._total_latency += latency

            self.soul.think(
                f"skill:{self.name}", "exit",
                f"Skill '{self.name}' v{self.current_version.version} "
                f"executed in {latency*1000:.1f}ms",
                data={"latency_ms": round(latency * 1000, 1),
                      "version": self.current_version.version},
            )
            return result

        except Exception as e:
            self._error_count += 1
            self.soul.think(
                f"skill:{self.name}", "error",
                f"Skill '{self.name}' v{self.current_version.version} "
                f"FAILED: {e} (errors: {self._error_count}/{self._call_count})",
                confidence=0.0,
                data={"error": str(e), "error_rate": self.error_rate},
            )
            raise

    @property
    def error_rate(self) -> float:
        if self._call_count == 0:
            return 0.0
        return self._error_count / self._call_count

    @property
    def avg_latency_ms(self) -> float:
        if self._call_count == 0:
            return 0.0
        return (self._total_latency / self._call_count) * 1000

    def add_test(self, input: Any, expected: Any, weight: float = 1.0):
        """Add a test case for evaluating skill versions."""
        self._tests.append(SkillTest(input=input, expected=expected, weight=weight))

    def evaluate(self, fn: Callable | None = None) -> tuple[float, list[str]]:
        """
        Run all tests against a function (default: current implementation).
        Returns (score 0-1, list of failure descriptions).
        """
        fn = fn or self._fn
        if not self._tests:
            return 1.0, []

        total_weight = sum(t.weight for t in self._tests)
        passed_weight = 0.0
        failures = []

        for test in self._tests:
            try:
                result = fn(test.input)
                if result == test.expected:
                    passed_weight += test.weight
                else:
                    failures.append(
                        f"input={test.input!r}: got {result!r}, expected {test.expected!r}"
                    )
            except Exception as e:
                failures.append(f"input={test.input!r}: raised {e}")

        score = passed_weight / total_weight if total_weight > 0 else 0.0
        return score, failures

    def evolve(self, new_fn: Callable, reason: str, source: str = "",
               author: str = "self") -> bool:
        """
        Attempt to evolve the skill to a new implementation.
        Only accepts if new version scores >= current version on tests.
        Returns True if evolution was accepted.
        """
        # Evaluate current
        current_score, _ = self.evaluate(self._fn)

        # Evaluate candidate
        new_score, new_failures = self.evaluate(new_fn)

        self.soul.think(
            f"skill:{self.name}", "self_check",
            f"Evolution attempt: v{self.current_version.version} "
            f"(score={current_score:.2f}) -> candidate (score={new_score:.2f})",
            data={
                "current_score": current_score,
                "new_score": new_score,
                "new_failures": new_failures,
                "reason": reason,
            },
            confidence=new_score,
        )

        if new_score >= current_score:
            # Accept evolution
            old_version = self.current_version.version
            new_version = SkillVersion(
                version=old_version + 1,
                source=source or f"<evolved from v{old_version}>",
                created_at=time.time(),
                reason=reason,
                metrics={
                    "score": new_score,
                    "improvement": new_score - current_score,
                    "prev_error_rate": self.error_rate,
                },
                parent_version=old_version,
                author=author,
            )
            self.versions.append(new_version)
            self._fn = new_fn
            self._error_count = 0
            self._call_count = 0

            self.soul.think(
                f"skill:{self.name}", "correction",
                f"EVOLVED: v{old_version} -> v{new_version.version} "
                f"({reason}), score {current_score:.2f} -> {new_score:.2f}",
                data={"from": old_version, "to": new_version.version},
            )
            return True
        else:
            self.soul.think(
                f"skill:{self.name}", "self_check",
                f"Evolution REJECTED: candidate score {new_score:.2f} "
                f"< current {current_score:.2f}",
                confidence=new_score,
            )
            return False

    def history(self) -> list[dict]:
        """Full version history."""
        return [
            {
                "version": v.version,
                "hash": v.hash,
                "reason": v.reason,
                "author": v.author,
                "metrics": v.metrics,
                "created_at": v.created_at,
            }
            for v in self.versions
        ]

    def stats(self) -> dict:
        return {
            "name": self.name,
            "current_version": self.current_version.version,
            "total_versions": len(self.versions),
            "call_count": self._call_count,
            "error_rate": round(self.error_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "test_count": len(self._tests),
        }
