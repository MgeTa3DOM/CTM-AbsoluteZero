"""
LIVING CODE - Network: Cooperative Intelligence

Agents that share their soul (execution trace) and skills (versioned code)
in real-time. No central controller. Intelligence emerges from information flow.

Each agent publishes thoughts to shared memory.
Other agents read, cross-reference, and contribute back.
Consensus is emergent, not voted.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from collections import defaultdict

from .soul import Soul, Thought
from .skill import Skill


@dataclass
class Message:
    """A message in the shared memory bus."""
    sender: str
    topic: str
    content: Any
    timestamp: float = field(default_factory=time.time)
    in_reply_to: Optional[str] = None  # message id
    msg_id: str = ""

    def __post_init__(self):
        if not self.msg_id:
            self.msg_id = f"{self.sender}:{self.timestamp:.6f}"


class SharedMemory:
    """
    Shared memory bus for agent cooperation.
    Append-only (WORM principle). Agents publish and subscribe.
    No deletion, no modification.
    """

    def __init__(self):
        self._messages: list[Message] = []
        self._subscribers: dict[str, list[Callable[[Message], None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def publish(self, msg: Message):
        """Publish a message. All subscribers on that topic get notified."""
        with self._lock:
            self._messages.append(msg)
        # Notify subscribers
        for callback in self._subscribers.get(msg.topic, []):
            callback(msg)
        for callback in self._subscribers.get("*", []):  # Wildcard subscribers
            callback(msg)

    def subscribe(self, topic: str, callback: Callable[[Message], None]):
        """Subscribe to a topic. Use "*" for all messages."""
        self._subscribers[topic].append(callback)

    def query(self, topic: str | None = None, sender: str | None = None,
              last_n: int = 50) -> list[Message]:
        """Query shared memory. Filters are optional."""
        with self._lock:
            msgs = list(self._messages)

        if topic:
            msgs = [m for m in msgs if m.topic == topic]
        if sender:
            msgs = [m for m in msgs if m.sender == sender]

        return msgs[-last_n:]

    def count(self) -> int:
        return len(self._messages)


class Agent:
    """
    A LIVING CODE agent with a soul, skills, and network access.

    It can:
    - Execute skills with self-introspection
    - Publish its thoughts to the network
    - Read other agents' thoughts
    - Learn from peers (adopt their skill improvements)
    """

    def __init__(self, name: str, network: SharedMemory, soul: Soul | None = None):
        self.name = name
        self.network = network
        self.soul = soul or Soul()
        self.skills: dict[str, Skill] = {}
        self._inbox: list[Message] = []

        # Subscribe to messages directed at us or broadcast
        network.subscribe("broadcast", self._on_message)
        network.subscribe(f"agent:{name}", self._on_message)
        network.subscribe("skill_evolution", self._on_skill_evolution)

    def _on_message(self, msg: Message):
        """Handle incoming messages."""
        if msg.sender == self.name:
            return  # Ignore own messages
        self._inbox.append(msg)
        self.soul.think(
            f"agent:{self.name}", "checkpoint",
            f"Received from {msg.sender}: {msg.topic}",
            data={"sender": msg.sender, "topic": msg.topic},
        )

    def _on_skill_evolution(self, msg: Message):
        """When a peer evolves a skill, consider adopting it."""
        if msg.sender == self.name:
            return

        skill_name = msg.content.get("skill_name")
        new_score = msg.content.get("new_score", 0)

        if skill_name in self.skills:
            my_score, _ = self.skills[skill_name].evaluate()
            self.soul.think(
                f"agent:{self.name}", "self_check",
                f"Peer {msg.sender} evolved '{skill_name}' to score {new_score:.2f}. "
                f"My score: {my_score:.2f}",
                data={"peer": msg.sender, "peer_score": new_score, "my_score": my_score},
                confidence=my_score,
            )

    def register_skill(self, name: str, fn: Callable, source: str = "") -> Skill:
        """Register a skill this agent can execute."""
        skill = Skill(name, fn, self.soul, source)
        self.skills[name] = skill
        return skill

    def execute(self, skill_name: str, *args, **kwargs) -> Any:
        """Execute a skill and publish the result to the network."""
        if skill_name not in self.skills:
            raise KeyError(f"Agent '{self.name}' has no skill '{skill_name}'")

        skill = self.skills[skill_name]

        self.soul.think(
            f"agent:{self.name}", "enter",
            f"Executing skill '{skill_name}' v{skill.current_version.version}",
        )

        result = skill(*args, **kwargs)

        # Share result with network
        self.network.publish(Message(
            sender=self.name,
            topic="execution",
            content={
                "skill": skill_name,
                "version": skill.current_version.version,
                "result_preview": repr(result)[:100],
                "latency_ms": skill.avg_latency_ms,
            },
        ))

        return result

    def evolve_skill(self, skill_name: str, new_fn: Callable,
                     reason: str, source: str = "") -> bool:
        """Attempt to evolve a skill. If accepted, notify the network."""
        if skill_name not in self.skills:
            return False

        accepted = self.skills[skill_name].evolve(new_fn, reason, source, author="self")

        if accepted:
            skill = self.skills[skill_name]
            score, _ = skill.evaluate()
            self.network.publish(Message(
                sender=self.name,
                topic="skill_evolution",
                content={
                    "skill_name": skill_name,
                    "new_version": skill.current_version.version,
                    "new_score": score,
                    "reason": reason,
                },
            ))

        return accepted

    def think_about(self, topic: str) -> list[Message]:
        """
        Read what the network thinks about a topic.
        This is how agents learn from each other.
        """
        messages = self.network.query(topic=topic)
        self.soul.think(
            f"agent:{self.name}", "self_check",
            f"Consulting network on '{topic}': {len(messages)} messages found",
            data={"topic": topic, "message_count": len(messages)},
        )
        return messages

    def status(self) -> dict:
        return {
            "name": self.name,
            "skills": {name: skill.stats() for name, skill in self.skills.items()},
            "soul_summary": self.soul.summary(),
            "inbox_size": len(self._inbox),
        }


class Collective:
    """
    A group of agents sharing the same network.
    Emergence happens here: agents contribute individually,
    collective intelligence emerges from the information flow.
    """

    def __init__(self):
        self.network = SharedMemory()
        self.agents: dict[str, Agent] = {}

    def add_agent(self, name: str) -> Agent:
        agent = Agent(name, self.network)
        self.agents[name] = agent
        self.network.publish(Message(
            sender="system",
            topic="broadcast",
            content={"event": "agent_joined", "agent": name},
        ))
        return agent

    def collective_execute(self, skill_name: str, input_data: Any) -> dict[str, Any]:
        """
        All agents with this skill execute it.
        Returns all results. Consensus is for the caller to determine.
        """
        results = {}
        for name, agent in self.agents.items():
            if skill_name in agent.skills:
                try:
                    results[name] = {
                        "result": agent.execute(skill_name, input_data),
                        "version": agent.skills[skill_name].current_version.version,
                        "error": None,
                    }
                except Exception as e:
                    results[name] = {
                        "result": None,
                        "version": agent.skills[skill_name].current_version.version,
                        "error": str(e),
                    }

        # Publish collective result
        self.network.publish(Message(
            sender="collective",
            topic="collective_result",
            content={
                "skill": skill_name,
                "agents_participated": len(results),
                "agents_succeeded": sum(1 for r in results.values() if r["error"] is None),
            },
        ))

        return results

    def status(self) -> dict:
        return {
            "agents": len(self.agents),
            "network_messages": self.network.count(),
            "agent_status": {name: agent.status() for name, agent in self.agents.items()},
        }
