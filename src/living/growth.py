"""
LIVING CODE - Growth: Compression-Based Intelligence Measurement

Intelligence = ability to compress information about a domain.
Code that compresses well understands patterns.
Code that compresses poorly misses structure.

Growth = increased compression ratio = deeper understanding.
"""

from __future__ import annotations

import zlib
import time
import math
from dataclasses import dataclass, field
from typing import Any

from .soul import Soul


@dataclass
class GrowthSnapshot:
    """A measurement of an agent's intelligence at a point in time."""
    timestamp: float
    raw_size: int          # Size of raw execution data
    compressed_size: int   # Size after compression
    ratio: float           # Compression ratio (higher = better understanding)
    unique_patterns: int   # Number of distinct patterns detected
    error_rate: float      # Current error rate
    skills_evolved: int    # Number of skill evolutions so far

    @property
    def intelligence_score(self) -> float:
        """
        Composite intelligence score.
        Combines compression (understanding) with reliability (low errors)
        and adaptability (skill evolution).
        """
        compression_factor = min(self.ratio / 10.0, 1.0)  # Cap at 10x
        reliability = 1.0 - min(self.error_rate, 1.0)
        adaptability = min(self.skills_evolved / 10.0, 1.0)  # Cap at 10

        return (compression_factor * 0.5 +
                reliability * 0.3 +
                adaptability * 0.2)


class GrowthTracker:
    """
    Tracks how much an agent/collective understands over time.

    Method: collect execution data, compress it, measure ratio.
    Better compression = the system has more regular patterns = it understands more.
    """

    def __init__(self, soul: Soul):
        self.soul = soul
        self.snapshots: list[GrowthSnapshot] = []
        self._pattern_cache: dict[str, int] = {}

    def measure(self, extra_data: bytes = b"",
                error_rate: float = 0.0,
                skills_evolved: int = 0) -> GrowthSnapshot:
        """
        Take a growth measurement based on current soul state.
        """
        # Collect all execution data
        raw_data = self._collect_data(extra_data)
        raw_size = len(raw_data)

        if raw_size == 0:
            snapshot = GrowthSnapshot(
                timestamp=time.time(),
                raw_size=0,
                compressed_size=0,
                ratio=1.0,
                unique_patterns=0,
                error_rate=error_rate,
                skills_evolved=skills_evolved,
            )
            self.snapshots.append(snapshot)
            return snapshot

        # Compress
        compressed = zlib.compress(raw_data, level=9)
        compressed_size = len(compressed)
        ratio = raw_size / compressed_size if compressed_size > 0 else 1.0

        # Count unique patterns (n-grams in execution trace)
        patterns = self._extract_patterns(raw_data)

        snapshot = GrowthSnapshot(
            timestamp=time.time(),
            raw_size=raw_size,
            compressed_size=compressed_size,
            ratio=ratio,
            unique_patterns=len(patterns),
            error_rate=error_rate,
            skills_evolved=skills_evolved,
        )

        self.snapshots.append(snapshot)

        self.soul.think(
            "growth", "checkpoint",
            f"Growth measurement: ratio={ratio:.2f}x, "
            f"patterns={len(patterns)}, score={snapshot.intelligence_score:.3f}",
            data={
                "ratio": round(ratio, 3),
                "patterns": len(patterns),
                "score": round(snapshot.intelligence_score, 3),
            },
        )

        return snapshot

    def trend(self) -> str:
        """Is intelligence growing, stable, or declining?"""
        if len(self.snapshots) < 2:
            return "insufficient_data"

        recent = self.snapshots[-5:]
        scores = [s.intelligence_score for s in recent]

        if len(scores) < 2:
            return "insufficient_data"

        # Simple linear trend
        avg_first_half = sum(scores[:len(scores)//2]) / max(len(scores)//2, 1)
        avg_second_half = sum(scores[len(scores)//2:]) / max(len(scores) - len(scores)//2, 1)

        delta = avg_second_half - avg_first_half

        if delta > 0.05:
            return "growing"
        elif delta < -0.05:
            return "declining"
        else:
            return "stable"

    def growth_rate(self) -> float:
        """Growth rate as percentage change between first and last measurement."""
        if len(self.snapshots) < 2:
            return 0.0
        first = self.snapshots[0].intelligence_score
        last = self.snapshots[-1].intelligence_score
        if first == 0:
            return 0.0
        return (last - first) / first

    def _collect_data(self, extra: bytes) -> bytes:
        """Collect all execution trace data."""
        parts = []
        for thought in self.soul.thoughts:
            parts.append(f"{thought.function}:{thought.event}:{thought.message}".encode())
        parts.append(extra)
        return b"|".join(parts)

    def _extract_patterns(self, data: bytes, n: int = 4) -> set[bytes]:
        """Extract unique n-grams as a proxy for pattern richness."""
        patterns = set()
        for i in range(len(data) - n + 1):
            patterns.add(data[i:i+n])
        # Update cache
        for p in patterns:
            key = p.hex()
            self._pattern_cache[key] = self._pattern_cache.get(key, 0) + 1
        return patterns

    def most_common_patterns(self, top_n: int = 10) -> list[tuple[str, int]]:
        """Most frequently occurring patterns across all measurements."""
        sorted_patterns = sorted(self._pattern_cache.items(),
                                  key=lambda x: x[1], reverse=True)
        return sorted_patterns[:top_n]

    def summary(self) -> dict:
        if not self.snapshots:
            return {"measurements": 0, "trend": "no_data"}

        latest = self.snapshots[-1]
        return {
            "measurements": len(self.snapshots),
            "latest_score": round(latest.intelligence_score, 3),
            "latest_ratio": round(latest.ratio, 2),
            "trend": self.trend(),
            "growth_rate": f"{self.growth_rate():.1%}",
            "total_patterns": len(self._pattern_cache),
        }
