"""Growth — Compression-based intelligence measurement.

Intelligence ≈ ability to compress information about a domain.
Higher compression ratio = deeper pattern understanding.
"""

from __future__ import annotations

import zlib
import time
from dataclasses import dataclass
from typing import Any

from living.soul import Soul


@dataclass(slots=True)
class Snapshot:
    ts: float
    raw: int
    compressed: int
    ratio: float
    patterns: int
    error_rate: float
    evolutions: int

    @property
    def score(self) -> float:
        compress = min(self.ratio / 10.0, 1.0)
        reliability = 1.0 - min(self.error_rate, 1.0)
        adapt = min(self.evolutions / 10.0, 1.0)
        return compress * 0.5 + reliability * 0.3 + adapt * 0.2


class GrowthTracker:
    def __init__(self, soul: Soul):
        self.soul = soul
        self.snaps: list[Snapshot] = []

    def measure(self, error_rate: float = 0.0, evolutions: int = 0) -> Snapshot:
        raw = "|".join(f"{t.fn}:{t.event}:{t.msg}" for t in self.soul.thoughts).encode()
        raw_size = len(raw) or 1
        comp = zlib.compress(raw, 9)
        ratio = raw_size / len(comp) if comp else 1.0

        # count unique 4-grams as pattern proxy
        ngrams = {raw[i:i+4] for i in range(len(raw) - 3)} if len(raw) >= 4 else set()

        snap = Snapshot(time.time(), raw_size, len(comp), ratio,
                        len(ngrams), error_rate, evolutions)
        self.snaps.append(snap)
        self.soul.think("growth", "check",
                        f"ratio={ratio:.1f}x patterns={len(ngrams)} score={snap.score:.3f}")
        return snap

    def trend(self) -> str:
        if len(self.snaps) < 2:
            return "insufficient"
        scores = [s.score for s in self.snaps[-5:]]
        mid = len(scores) // 2
        first = sum(scores[:mid]) / max(mid, 1)
        second = sum(scores[mid:]) / max(len(scores) - mid, 1)
        delta = second - first
        if delta > 0.05:
            return "growing"
        if delta < -0.05:
            return "declining"
        return "stable"
