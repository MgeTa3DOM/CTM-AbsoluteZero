"""
Auto-Refinement Pipeline — Self-improving AI agents.

The loop:
1. Agents execute tasks, soul records everything
2. Evaluator scores each execution against test cases
3. Low-scoring skills trigger evolution attempts
4. Successful evolutions get recorded in the dataset
5. Dataset gets recycled: old executions feed new training
6. Growth tracker measures intelligence over time

Dataset storage: local filesystem + configurable remote
(Google Drive, S3, GCS) via adapters.
"""

from __future__ import annotations

import json
import time
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from living.soul import Soul
from living.skill import Skill
from living.network import Agent, Collective
from living.growth import GrowthTracker


# --- Dataset Storage ---

class StorageBackend(Protocol):
    """Interface for dataset storage (local, Google Drive, S3, etc.)"""
    def write(self, path: str, data: bytes) -> None: ...
    def read(self, path: str) -> bytes: ...
    def list(self, prefix: str) -> list[str]: ...
    def size_bytes(self) -> int: ...


class LocalStorage:
    """Local filesystem storage for datasets."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, path: str, data: bytes) -> None:
        full = self.root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)

    def read(self, path: str) -> bytes:
        return (self.root / path).read_bytes()

    def list(self, prefix: str = "") -> list[str]:
        results = []
        search = self.root / prefix if prefix else self.root
        if search.exists():
            for f in search.rglob("*"):
                if f.is_file():
                    results.append(str(f.relative_to(self.root)))
        return sorted(results)

    def size_bytes(self) -> int:
        total = 0
        for f in self.root.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total


class GoogleDriveStorage:
    """
    Google Drive storage adapter.

    Requires: google-api-python-client + oauth credentials.
    Can be configured via environment variables:
      GDRIVE_FOLDER_ID  — target folder in Drive
      GDRIVE_CREDS_PATH — path to service account JSON

    For now: writes config file that n8n/external tool can pick up.
    """

    def __init__(self, folder_id: str | None = None, max_gb: float = 144):
        self.folder_id = folder_id or os.environ.get("GDRIVE_FOLDER_ID", "")
        self.max_bytes = int(max_gb * 1024 * 1024 * 1024)
        self._local_cache = LocalStorage(Path("/tmp/gdrive-cache"))

    def write(self, path: str, data: bytes) -> None:
        # Cache locally + queue for upload
        self._local_cache.write(path, data)
        # Write upload manifest for n8n/external sync
        manifest = {
            "action": "upload",
            "path": path,
            "size": len(data),
            "folder_id": self.folder_id,
            "ts": time.time(),
            "hash": hashlib.sha256(data).hexdigest(),
        }
        manifest_path = f".queue/{int(time.time()*1000)}_{path.replace('/', '_')}.json"
        self._local_cache.write(manifest_path, json.dumps(manifest).encode())

    def read(self, path: str) -> bytes:
        return self._local_cache.read(path)

    def list(self, prefix: str = "") -> list[str]:
        return [f for f in self._local_cache.list(prefix) if not f.startswith(".queue/")]

    def size_bytes(self) -> int:
        return self._local_cache.size_bytes()


# --- Dataset ---

@dataclass
class ExecutionRecord:
    """One recorded execution for the dataset."""
    ts: float
    agent: str
    skill: str
    skill_version: int
    input_data: Any
    output: Any
    expected: Any
    correct: bool
    confidence: float
    latency_ms: float
    soul_trace: list[dict]  # Thoughts during execution
    evolution_triggered: bool = False


class Dataset:
    """
    Self-growing dataset for auto-refinement.

    Every execution is recorded. The dataset feeds back into
    skill evolution: patterns of failure become training signal.
    """

    def __init__(self, storage: StorageBackend, max_gb: float = 144):
        self.storage = storage
        self.max_bytes = int(max_gb * 1024 * 1024 * 1024)
        self._records: list[ExecutionRecord] = []
        self._session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]

    def record(self, rec: ExecutionRecord) -> str:
        """Record an execution. Returns the storage path."""
        self._records.append(rec)
        path = f"executions/{rec.agent}/{rec.skill}/v{rec.skill_version}/{self._session_id}_{len(self._records):06d}.json"
        data = json.dumps({
            "ts": rec.ts,
            "agent": rec.agent,
            "skill": rec.skill,
            "version": rec.skill_version,
            "input": repr(rec.input_data)[:500],
            "output": repr(rec.output)[:500],
            "expected": repr(rec.expected)[:500],
            "correct": rec.correct,
            "confidence": rec.confidence,
            "latency_ms": rec.latency_ms,
            "soul_trace": rec.soul_trace[:20],  # Limit trace size
            "evolution_triggered": rec.evolution_triggered,
        }, indent=2).encode()
        self.storage.write(path, data)
        return path

    def failures(self, skill: str | None = None) -> list[ExecutionRecord]:
        """Get all failed executions, optionally filtered by skill."""
        recs = [r for r in self._records if not r.correct]
        if skill:
            recs = [r for r in recs if r.skill == skill]
        return recs

    def success_rate(self, skill: str | None = None) -> float:
        recs = self._records if not skill else [r for r in self._records if r.skill == skill]
        if not recs:
            return 0.0
        return sum(1 for r in recs if r.correct) / len(recs)

    def recycle(self) -> dict:
        """
        Recycle the dataset: analyze patterns in failures,
        generate evolution signals.

        Returns a summary of what was found.
        """
        if not self._records:
            return {"status": "empty", "signals": []}

        # Group failures by skill
        skill_failures: dict[str, list[ExecutionRecord]] = {}
        for r in self._records:
            if not r.correct:
                skill_failures.setdefault(r.skill, []).append(r)

        signals = []
        for skill_name, failures in skill_failures.items():
            failure_rate = len(failures) / max(
                len([r for r in self._records if r.skill == skill_name]), 1
            )
            if failure_rate > 0.2:  # >20% failure = needs evolution
                # Extract common patterns in failed inputs
                failed_inputs = [repr(f.input_data) for f in failures[-10:]]
                signals.append({
                    "skill": skill_name,
                    "failure_rate": round(failure_rate, 3),
                    "failure_count": len(failures),
                    "sample_inputs": failed_inputs[:5],
                    "action": "evolve",
                })

        # Save recycle report
        report = {
            "ts": time.time(),
            "total_records": len(self._records),
            "total_failures": sum(1 for r in self._records if not r.correct),
            "success_rate": self.success_rate(),
            "signals": signals,
            "storage_bytes": self.storage.size_bytes(),
            "storage_max_bytes": self.max_bytes,
        }
        self.storage.write(
            f"recycle/{int(time.time())}_report.json",
            json.dumps(report, indent=2).encode(),
        )
        return report

    def stats(self) -> dict:
        return {
            "total_records": len(self._records),
            "success_rate": round(self.success_rate(), 3),
            "storage_bytes": self.storage.size_bytes(),
            "storage_max_gb": self.max_bytes / (1024**3),
            "storage_used_pct": round(
                self.storage.size_bytes() / self.max_bytes * 100, 2
            ) if self.max_bytes else 0,
        }


# --- Auto-Refinement Loop ---

class RefinementLoop:
    """
    The self-improvement loop.

    1. Run agents on tasks
    2. Record everything in dataset
    3. Recycle dataset to find failure patterns
    4. Trigger skill evolution for failing skills
    5. Measure growth
    6. Repeat
    """

    def __init__(self, collective: Collective, dataset: Dataset):
        self.collective = collective
        self.dataset = dataset
        self.cycle = 0
        self._growth_trackers: dict[str, GrowthTracker] = {}

    def run_cycle(self, skill: str, test_cases: list[tuple[Any, Any]],
                  evolution_fn: Callable[[str, list[ExecutionRecord]], Callable | None] | None = None) -> dict:
        """
        Run one refinement cycle:
        1. Execute all test cases across all agents
        2. Record results
        3. Recycle dataset
        4. Evolve if needed
        5. Measure growth
        """
        self.cycle += 1
        cycle_results = {
            "cycle": self.cycle,
            "agents": {},
            "evolutions": [],
        }

        # Execute
        for agent_name, agent in self.collective.agents.items():
            if skill not in agent.skills:
                continue

            agent_results = []
            for inp, expected in test_cases:
                t0 = time.perf_counter()
                try:
                    output = agent.run(skill, inp)
                    correct = output == expected
                except Exception as e:
                    output = str(e)
                    correct = False
                dt = (time.perf_counter() - t0) * 1000

                rec = ExecutionRecord(
                    ts=time.time(),
                    agent=agent_name,
                    skill=skill,
                    skill_version=agent.skills[skill].version.v,
                    input_data=inp,
                    output=output,
                    expected=expected,
                    correct=correct,
                    confidence=agent.skills[skill].version.metrics.get("score", 0),
                    latency_ms=dt,
                    soul_trace=[{"fn": t.fn, "e": t.event, "msg": t.msg[:100]}
                                for t in agent.soul.recall(5)],
                )
                self.dataset.record(rec)
                agent_results.append(rec)

            success = sum(1 for r in agent_results if r.correct)
            total = len(agent_results)
            cycle_results["agents"][agent_name] = {
                "success": success,
                "total": total,
                "rate": round(success / total, 3) if total else 0,
                "version": agent.skills[skill].version.v,
            }

        # Recycle
        report = self.dataset.recycle()
        cycle_results["recycle"] = report

        # Evolve if needed
        if evolution_fn:
            for signal in report.get("signals", []):
                if signal["action"] == "evolve":
                    failures = self.dataset.failures(signal["skill"])
                    new_fn = evolution_fn(signal["skill"], failures)
                    if new_fn:
                        for agent in self.collective.agents.values():
                            if signal["skill"] in agent.skills:
                                accepted = agent.evolve(
                                    signal["skill"], new_fn,
                                    f"auto-refinement cycle {self.cycle}: "
                                    f"failure_rate={signal['failure_rate']}"
                                )
                                if accepted:
                                    cycle_results["evolutions"].append({
                                        "agent": agent.name,
                                        "skill": signal["skill"],
                                        "cycle": self.cycle,
                                    })

        # Growth
        for agent_name, agent in self.collective.agents.items():
            if agent_name not in self._growth_trackers:
                self._growth_trackers[agent_name] = GrowthTracker(agent.soul)
            tracker = self._growth_trackers[agent_name]
            evos = len(agent.skills.get(skill, Skill("", lambda: None, Soul())).versions) - 1
            snap = tracker.measure(
                error_rate=1 - cycle_results["agents"].get(agent_name, {}).get("rate", 0),
                evolutions=evos,
            )
            cycle_results["agents"][agent_name]["growth_score"] = round(snap.score, 3)

        cycle_results["dataset"] = self.dataset.stats()
        return cycle_results
