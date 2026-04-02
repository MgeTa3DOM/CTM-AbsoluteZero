"""Soul — Real-time self-introspecting execution trace.

The soul is not a log you read after.  It's a live trace
the code reads and writes DURING execution.  Functions decorated
with `@soul.aware` record every entry, exit, and error.
Watchers can trigger corrections mid-flight.
"""

from __future__ import annotations

import functools
import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(slots=True)
class Thought:
    ts: float
    fn: str
    event: str          # enter | exit | error | check | correction
    msg: str
    data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    correction: str | None = None


class Soul:
    __slots__ = ("thoughts", "_watchers", "_depth", "_persist")

    def __init__(self, persist: Path | None = None):
        self.thoughts: list[Thought] = []
        self._watchers: list[Callable[[Thought], str | None]] = []
        self._depth = 0
        self._persist = persist

    # -- core --

    def think(self, fn: str, event: str, msg: str, *,
              data: dict | None = None, confidence: float = 1.0) -> Thought:
        t = Thought(time.time(), fn, event, msg, data or {}, confidence)
        for w in self._watchers:
            fix = w(t)
            if fix:
                t.correction = fix
                t.event = "correction"
                t.msg = f"CORRECTED: {fix} (was: {msg})"
        self.thoughts.append(t)
        if self._persist:
            with open(self._persist, "a") as f:
                f.write(json.dumps({"ts": t.ts, "fn": t.fn, "e": t.event,
                                     "msg": t.msg, "c": t.confidence}) + "\n")
        return t

    # -- queries --

    def recall(self, n: int = 10) -> list[Thought]:
        return self.thoughts[-n:]

    def errors(self) -> list[Thought]:
        return [t for t in self.thoughts if t.event == "error"]

    def corrections(self) -> list[Thought]:
        return [t for t in self.thoughts if t.event == "correction"]

    def low_confidence(self, below: float = 0.7) -> list[Thought]:
        return [t for t in self.thoughts if t.confidence < below]

    # -- watchers --

    def watch(self, fn: Callable[[Thought], str | None]):
        self._watchers.append(fn)

    # -- decorator --

    def aware(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = func.__name__
            self._depth += 1
            self.think(name, "enter", f"{'  ' * self._depth}-> {name}")
            try:
                result = func(*args, **kwargs)
                self.think(name, "exit", f"{'  ' * self._depth}<- {name}")
                return result
            except Exception as exc:
                self.think(name, "error", f"{'  ' * self._depth}!! {name}: {exc}",
                           confidence=0.0,
                           data={"tb": traceback.format_exc()})
                raise
            finally:
                self._depth -= 1
        return wrapper

    def summary(self) -> dict[str, Any]:
        return {
            "thoughts": len(self.thoughts),
            "errors": len(self.errors()),
            "corrections": len(self.corrections()),
            "fns": list({t.fn for t in self.thoughts}),
        }
