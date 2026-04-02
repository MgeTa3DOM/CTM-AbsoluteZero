"""Network — Cooperative multi-agent shared memory.

Agents publish thoughts.  Other agents read them.
No central controller.  Intelligence emerges from information flow.
Append-only bus (WORM principle).
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from living.soul import Soul
from living.skill import Skill


@dataclass(slots=True)
class Msg:
    sender: str
    topic: str
    data: Any
    ts: float = field(default_factory=time.time)


class SharedMemory:
    """Append-only message bus."""

    def __init__(self):
        self._msgs: list[Msg] = []
        self._subs: dict[str, list[Callable[[Msg], None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def publish(self, msg: Msg):
        with self._lock:
            self._msgs.append(msg)
        for cb in self._subs.get(msg.topic, []):
            cb(msg)
        for cb in self._subs.get("*", []):
            cb(msg)

    def subscribe(self, topic: str, cb: Callable[[Msg], None]):
        self._subs[topic].append(cb)

    def query(self, topic: str | None = None, sender: str | None = None,
              n: int = 50) -> list[Msg]:
        with self._lock:
            out = list(self._msgs)
        if topic:
            out = [m for m in out if m.topic == topic]
        if sender:
            out = [m for m in out if m.sender == sender]
        return out[-n:]

    def count(self) -> int:
        return len(self._msgs)


class Agent:
    """Agent with soul, skills, network."""

    def __init__(self, name: str, net: SharedMemory, soul: Soul | None = None):
        self.name = name
        self.net = net
        self.soul = soul or Soul()
        self.skills: dict[str, Skill] = {}
        self._inbox: list[Msg] = []
        net.subscribe("broadcast", self._on_msg)
        net.subscribe(f"agent:{name}", self._on_msg)
        net.subscribe("skill_evolved", self._on_peer_evolve)

    def _on_msg(self, msg: Msg):
        if msg.sender != self.name:
            self._inbox.append(msg)

    def _on_peer_evolve(self, msg: Msg):
        if msg.sender == self.name:
            return
        sk = msg.data.get("skill")
        if sk and sk in self.skills:
            peer_score = msg.data.get("score", 0)
            my_score, _ = self.skills[sk].evaluate()
            self.soul.think(f"agent:{self.name}", "check",
                            f"peer {msg.sender} evolved '{sk}' to {peer_score:.2f}, mine={my_score:.2f}")

    def add_skill(self, name: str, fn: Callable, source: str = "") -> Skill:
        sk = Skill(name, fn, self.soul, source)
        self.skills[name] = sk
        return sk

    def run(self, skill: str, *args: Any, **kw: Any) -> Any:
        sk = self.skills[skill]
        result = sk(*args, **kw)
        self.net.publish(Msg(self.name, "execution", {
            "skill": skill, "v": sk.version.v,
            "result": repr(result)[:100],
        }))
        return result

    def evolve(self, skill: str, new_fn: Callable,
               reason: str, source: str = "") -> bool:
        sk = self.skills[skill]
        ok = sk.evolve(new_fn, reason, source)
        if ok:
            score, _ = sk.evaluate()
            self.net.publish(Msg(self.name, "skill_evolved", {
                "skill": skill, "v": sk.version.v, "score": score, "reason": reason,
            }))
        return ok


class Collective:
    """Group of agents on the same network."""

    def __init__(self):
        self.net = SharedMemory()
        self.agents: dict[str, Agent] = {}

    def spawn(self, name: str) -> Agent:
        a = Agent(name, self.net)
        self.agents[name] = a
        self.net.publish(Msg("system", "broadcast", {"event": "joined", "agent": name}))
        return a

    def run_all(self, skill: str, *args: Any, **kw: Any) -> dict[str, Any]:
        results = {}
        for name, agent in self.agents.items():
            if skill in agent.skills:
                try:
                    results[name] = {"ok": True, "result": agent.run(skill, *args, **kw),
                                     "v": agent.skills[skill].version.v}
                except Exception as e:
                    results[name] = {"ok": False, "error": str(e)}
        return results
