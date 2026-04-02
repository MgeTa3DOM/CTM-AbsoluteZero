"""
LIVING CODE - Soul: Self-Introspecting Execution Engine

This is NOT a spec. This is code that watches itself run,
logs every decision in real-time, and can interrupt its own execution
when something looks wrong.

The "soul" is a live execution trace that the code reads and writes
to DURING execution, not after.
"""

from __future__ import annotations

import time
import json
import traceback
import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from pathlib import Path
from contextlib import contextmanager


@dataclass
class Thought:
    """A single moment of self-awareness during execution."""
    timestamp: float
    function: str
    event: str  # "enter", "checkpoint", "self_check", "exit", "error", "correction"
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    correction: Optional[str] = None  # What the code decided to do differently

    def to_dict(self) -> dict:
        d = {
            "t": round(self.timestamp, 6),
            "fn": self.function,
            "event": self.event,
            "msg": self.message,
        }
        if self.data:
            d["data"] = self.data
        if self.confidence < 1.0:
            d["confidence"] = round(self.confidence, 3)
        if self.correction:
            d["correction"] = self.correction
        return d


class Soul:
    """
    The execution trace of a living program.

    Every function decorated with @soul.aware writes its thoughts here.
    The soul can be read mid-execution by any function, enabling
    self-correction in real-time.
    """

    def __init__(self, persist_path: Optional[Path] = None):
        self.thoughts: list[Thought] = []
        self.persist_path = persist_path
        self._watchers: list[Callable[[Thought], Optional[str]]] = []
        self._depth = 0

    def think(self, function: str, event: str, message: str,
              data: dict[str, Any] | None = None,
              confidence: float = 1.0) -> Thought:
        """Record a thought. Returns the thought so callers can react."""
        thought = Thought(
            timestamp=time.time(),
            function=function,
            event=event,
            message=message,
            data=data or {},
            confidence=confidence,
        )

        # Let watchers react BEFORE recording (they can trigger corrections)
        for watcher in self._watchers:
            correction = watcher(thought)
            if correction:
                thought.correction = correction
                thought.event = "correction"
                thought.message = f"CORRECTED: {correction} (was: {message})"

        self.thoughts.append(thought)

        if self.persist_path:
            self._persist(thought)

        return thought

    def recall(self, last_n: int = 10) -> list[Thought]:
        """Read recent thoughts. This is how code reads its own execution."""
        return self.thoughts[-last_n:]

    def recall_errors(self) -> list[Thought]:
        """Find all errors in execution history."""
        return [t for t in self.thoughts if t.event == "error"]

    def recall_corrections(self) -> list[Thought]:
        """Find all self-corrections."""
        return [t for t in self.thoughts if t.event == "correction"]

    def recall_low_confidence(self, threshold: float = 0.7) -> list[Thought]:
        """Find moments where confidence was low."""
        return [t for t in self.thoughts if t.confidence < threshold]

    def add_watcher(self, watcher: Callable[[Thought], Optional[str]]):
        """
        Add a watcher that sees every thought in real-time.
        Watcher returns None to accept, or a string to trigger correction.
        """
        self._watchers.append(watcher)

    def aware(self, func: Callable) -> Callable:
        """
        Decorator: makes a function self-aware.
        It logs entry, exit, errors, and enables self-checks mid-execution.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            fname = func.__name__
            self._depth += 1
            indent = "  " * self._depth

            # Log entry with actual arguments
            safe_args = _safe_repr(args[1:] if args else args)  # skip self if method
            safe_kwargs = _safe_repr(kwargs)
            self.think(fname, "enter",
                       f"{indent}-> {fname}({safe_args})",
                       data={"args": safe_args, "kwargs": safe_kwargs})

            try:
                result = func(*args, **kwargs)

                # Log exit with result
                safe_result = _safe_repr(result)
                self.think(fname, "exit",
                           f"{indent}<- {fname} = {safe_result}",
                           data={"result": safe_result})

                self._depth -= 1
                return result

            except Exception as e:
                self.think(fname, "error",
                           f"{indent}!! {fname} FAILED: {e}",
                           data={"error": str(e), "traceback": traceback.format_exc()},
                           confidence=0.0)
                self._depth -= 1
                raise

        return wrapper

    @contextmanager
    def checkpoint(self, function: str, message: str,
                   confidence: float = 1.0, data: dict | None = None):
        """
        Context manager for mid-function self-checks.
        Usage:
            with soul.checkpoint("my_func", "checking input validity", confidence=0.8):
                # do the thing
        """
        thought = self.think(function, "self_check", f"CHECK: {message}",
                             data=data or {}, confidence=confidence)
        if thought.correction:
            yield thought.correction  # Caller gets the correction instruction
        else:
            yield None

    def summary(self) -> dict:
        """Summarize the soul's state."""
        return {
            "total_thoughts": len(self.thoughts),
            "errors": len(self.recall_errors()),
            "corrections": len(self.recall_corrections()),
            "low_confidence": len(self.recall_low_confidence()),
            "functions_called": list(set(t.function for t in self.thoughts)),
        }

    def dump(self) -> str:
        """Dump entire soul as readable text."""
        lines = []
        for t in self.thoughts:
            prefix = {"enter": "->", "exit": "<-", "error": "!!", "self_check": "??",
                       "correction": "~~", "checkpoint": "**"}.get(t.event, "  ")
            conf = f" [{t.confidence:.0%}]" if t.confidence < 1.0 else ""
            lines.append(f"{prefix} {t.message}{conf}")
        return "\n".join(lines)

    def _persist(self, thought: Thought):
        """Append thought to disk (WORM-style: append only)."""
        with open(self.persist_path, "a") as f:
            f.write(json.dumps(thought.to_dict()) + "\n")


def _safe_repr(obj: Any, max_len: int = 200) -> str:
    """Safe string representation, truncated."""
    try:
        s = repr(obj)
        return s[:max_len] + "..." if len(s) > max_len else s
    except Exception:
        return "<unrepresentable>"


# --- Global soul instance ---
_global_soul = Soul()


def get_soul() -> Soul:
    return _global_soul


def set_soul(soul: Soul):
    global _global_soul
    _global_soul = soul
