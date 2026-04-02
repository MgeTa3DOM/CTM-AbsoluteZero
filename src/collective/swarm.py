"""
Collective Intelligence: Multi-Agent Swarm Coordination

Implements Layer 5 of the AI-OS architecture:
- Swarm coordination using Fibra golden angle scheduling
- World Model integration for spatial/causal reasoning
- EvoLLM weekly model improvement cycle
- Collective IQ metrics (target: 1.5x individual)
"""

from __future__ import annotations

import math
import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum


# --- Constants ---

GOLDEN_ANGLE = 137.50776405003785
PHI = 1.618033988749895
MAX_SWARM_SIZE = 64
COLLECTIVE_IQ_TARGET = 1.5  # 1.5x individual performance


# --- Swarm Agent ---

@dataclass
class SwarmAgent:
    """Individual agent in a swarm."""
    agent_id: str
    expertise: str
    confidence: float = 0.0
    angle: float = 0.0  # Fibra scheduling angle

    def contribute(self, task: Any) -> SwarmContribution:
        """Agent produces a contribution for the collective task."""
        # In production: call actual AI model
        return SwarmContribution(
            agent_id=self.agent_id,
            result=f"contribution_from_{self.agent_id}",
            confidence=self.confidence,
            explanation=f"Agent {self.agent_id} ({self.expertise}) analyzed the task",
        )


@dataclass
class SwarmContribution:
    """Single agent's contribution to collective output."""
    agent_id: str
    result: Any
    confidence: float
    explanation: str


# --- Coordination Strategies ---

class CoordinationStrategy(Enum):
    CONSENSUS = "consensus"
    TOURNAMENT = "tournament"
    WEIGHTED_MERGE = "weighted_merge"
    VOTING = "voting"


@dataclass
class ConsensusResult:
    """Result of collective coordination."""
    agreed: bool
    result: Any
    confidence: float
    explanation: str
    contributions: list[SwarmContribution]
    escalated_to_human: bool = False


# --- World Model ---

@dataclass
class WorldState:
    """Shared world model for spatial and causal reasoning."""
    timestamp: float
    spatial_data: dict[str, Any] = field(default_factory=dict)
    causal_graph: dict[str, list[str]] = field(default_factory=dict)
    predictions: list[dict[str, Any]] = field(default_factory=list)

    def query_spatial(self, entity: str) -> Optional[dict]:
        return self.spatial_data.get(entity)

    def query_causal(self, cause: str) -> list[str]:
        return self.causal_graph.get(cause, [])

    def predict(self, scenario: dict) -> dict:
        """Predict outcome of a scenario using world model."""
        # In production: neural physics model inference
        return {
            "scenario": scenario,
            "predicted_outcome": "stable",
            "confidence": 0.85,
            "timestamp": time.time(),
        }

    def update(self, observation: dict) -> None:
        """Update world model with new observation."""
        self.timestamp = time.time()
        if "spatial" in observation:
            self.spatial_data.update(observation["spatial"])
        if "causal" in observation:
            for cause, effects in observation["causal"].items():
                existing = self.causal_graph.get(cause, [])
                self.causal_graph[cause] = list(set(existing + effects))


# --- EvoLLM ---

@dataclass
class ModelSnapshot:
    """Snapshot of a model for evolution tracking."""
    model_id: str
    version: int
    metrics: dict[str, float]
    timestamp: float
    parent_id: Optional[str] = None


class EvoLLM:
    """
    Weekly model improvement cycle.
    Evaluate -> Select -> Merge -> Validate -> Deploy
    """

    def __init__(self, rollback_threshold: float = 0.95):
        self.rollback_threshold = rollback_threshold
        self.generations: list[list[ModelSnapshot]] = []
        self.current_generation: list[ModelSnapshot] = []
        self.baseline_metrics: dict[str, float] = {}

    def evaluate(self, models: list[ModelSnapshot],
                 benchmark: Callable[[str], dict[str, float]]) -> list[ModelSnapshot]:
        """Evaluate all models on benchmark suite."""
        for model in models:
            model.metrics = benchmark(model.model_id)
        return sorted(models, key=lambda m: sum(m.metrics.values()), reverse=True)

    def select(self, models: list[ModelSnapshot],
               top_percent: float = 0.2) -> list[ModelSnapshot]:
        """Select top performers for merging."""
        n = max(1, int(len(models) * top_percent))
        return models[:n]

    def merge(self, parents: list[ModelSnapshot]) -> ModelSnapshot:
        """Merge selected models via weighted averaging."""
        if not parents:
            raise ValueError("Cannot merge empty parent list")

        # Weighted average of metrics based on performance
        total_score = sum(sum(p.metrics.values()) for p in parents)
        merged_metrics = {}

        for parent in parents:
            weight = sum(parent.metrics.values()) / total_score if total_score > 0 else 1.0 / len(parents)
            for key, value in parent.metrics.items():
                merged_metrics[key] = merged_metrics.get(key, 0) + value * weight

        return ModelSnapshot(
            model_id=f"merged_gen{len(self.generations)}",
            version=len(self.generations),
            metrics=merged_metrics,
            timestamp=time.time(),
            parent_id=",".join(p.model_id for p in parents),
        )

    def validate(self, model: ModelSnapshot) -> tuple[bool, list[str]]:
        """Validate merged model against baseline. Returns (pass, issues)."""
        issues = []

        if not self.baseline_metrics:
            # First generation: set baseline
            self.baseline_metrics = dict(model.metrics)
            return True, []

        for key, baseline_value in self.baseline_metrics.items():
            if key in model.metrics:
                ratio = model.metrics[key] / baseline_value if baseline_value > 0 else 0
                if ratio < self.rollback_threshold:
                    issues.append(
                        f"Metric '{key}' regressed: {model.metrics[key]:.3f} "
                        f"vs baseline {baseline_value:.3f} "
                        f"(ratio {ratio:.3f} < threshold {self.rollback_threshold})"
                    )

        return len(issues) == 0, issues

    def evolve_cycle(self, models: list[ModelSnapshot],
                     benchmark: Callable[[str], dict[str, float]],
                     human_approval: Callable[[ModelSnapshot], bool]) -> Optional[ModelSnapshot]:
        """
        Complete evolution cycle:
        1. Evaluate on benchmarks
        2. Select top 20%
        3. Merge into next generation
        4. Validate safety + capability
        5. Deploy with human approval
        """
        # Step 1: Evaluate
        evaluated = self.evaluate(models, benchmark)

        # Step 2: Select
        selected = self.select(evaluated)

        # Step 3: Merge
        merged = self.merge(selected)

        # Step 4: Validate
        valid, issues = self.validate(merged)
        if not valid:
            return None  # Rollback: don't deploy

        # Step 5: Human approval (HILT)
        if not human_approval(merged):
            return None  # Human rejected

        # Success: update baseline and archive generation
        self.baseline_metrics = dict(merged.metrics)
        self.generations.append(self.current_generation)
        self.current_generation = [merged]

        return merged


# --- Swarm Coordinator ---

class SwarmCoordinator:
    """
    Coordinates multi-agent swarms using Fibra golden angle scheduling.
    Target: collective output 1.5x better than any individual agent.
    """

    def __init__(self, strategy: CoordinationStrategy = CoordinationStrategy.CONSENSUS):
        self.agents: list[SwarmAgent] = []
        self.strategy = strategy
        self.world_model = WorldState(timestamp=time.time())
        self.current_angle = 0.0
        self._audit: list[dict] = []

    def add_agent(self, agent: SwarmAgent) -> None:
        if len(self.agents) >= MAX_SWARM_SIZE:
            raise ValueError(f"Swarm cannot exceed {MAX_SWARM_SIZE} agents")
        # Assign Fibra angle
        self.current_angle = (self.current_angle + GOLDEN_ANGLE) % 360.0
        agent.angle = self.current_angle
        self.agents.append(agent)

    def coordinate(self, task: Any,
                   human_fallback: Callable[[], Any] | None = None) -> ConsensusResult:
        """
        Coordinate all agents on a task.
        Returns collective result.
        """
        if not self.agents:
            raise ValueError("Swarm has no agents")

        # Collect contributions from all agents (sorted by Fibra angle)
        sorted_agents = sorted(self.agents, key=lambda a: a.angle)
        contributions = [agent.contribute(task) for agent in sorted_agents]

        # Apply coordination strategy
        if self.strategy == CoordinationStrategy.CONSENSUS:
            result = self._consensus(contributions, human_fallback)
        elif self.strategy == CoordinationStrategy.TOURNAMENT:
            result = self._tournament(contributions)
        elif self.strategy == CoordinationStrategy.WEIGHTED_MERGE:
            result = self._weighted_merge(contributions)
        elif self.strategy == CoordinationStrategy.VOTING:
            result = self._voting(contributions, human_fallback)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        # Audit
        self._audit.append({
            "timestamp": time.time(),
            "task": str(task)[:200],
            "strategy": self.strategy.value,
            "agents": len(contributions),
            "result_confidence": result.confidence,
            "escalated": result.escalated_to_human,
        })

        return result

    def _consensus(self, contributions: list[SwarmContribution],
                   human_fallback: Callable | None) -> ConsensusResult:
        """All agents must agree. If not, escalate to human."""
        if not contributions:
            return ConsensusResult(False, None, 0.0, "No contributions", [], True)

        # Check if all results agree (simplified: check if confidence > 0.7)
        high_confidence = [c for c in contributions if c.confidence > 0.7]

        if len(high_confidence) == len(contributions):
            # Consensus reached
            avg_conf = sum(c.confidence for c in contributions) / len(contributions)
            return ConsensusResult(
                agreed=True,
                result=contributions[0].result,
                confidence=avg_conf,
                explanation=f"Consensus: all {len(contributions)} agents agree (avg confidence {avg_conf:.2f})",
                contributions=contributions,
            )
        else:
            # No consensus - escalate to human
            if human_fallback:
                human_result = human_fallback()
                return ConsensusResult(
                    agreed=True,
                    result=human_result,
                    confidence=1.0,
                    explanation="Human resolved disagreement",
                    contributions=contributions,
                    escalated_to_human=True,
                )
            return ConsensusResult(
                agreed=False,
                result=None,
                confidence=0.0,
                explanation=f"No consensus: {len(high_confidence)}/{len(contributions)} confident",
                contributions=contributions,
                escalated_to_human=True,
            )

    def _tournament(self, contributions: list[SwarmContribution]) -> ConsensusResult:
        """Best result (by confidence) wins."""
        best = max(contributions, key=lambda c: c.confidence)
        return ConsensusResult(
            agreed=True,
            result=best.result,
            confidence=best.confidence,
            explanation=f"Tournament winner: {best.agent_id} (confidence {best.confidence:.2f})",
            contributions=contributions,
        )

    def _weighted_merge(self, contributions: list[SwarmContribution]) -> ConsensusResult:
        """Merge results weighted by confidence."""
        total_conf = sum(c.confidence for c in contributions)
        avg_conf = total_conf / len(contributions) if contributions else 0

        return ConsensusResult(
            agreed=True,
            result=[c.result for c in contributions],
            confidence=avg_conf,
            explanation=f"Weighted merge of {len(contributions)} contributions (avg confidence {avg_conf:.2f})",
            contributions=contributions,
        )

    def _voting(self, contributions: list[SwarmContribution],
                human_fallback: Callable | None) -> ConsensusResult:
        """Majority vote, human tiebreak."""
        # Simplified: group by result, pick majority
        votes: dict[str, list[SwarmContribution]] = {}
        for c in contributions:
            key = str(c.result)
            votes.setdefault(key, []).append(c)

        majority = max(votes.values(), key=len)
        majority_pct = len(majority) / len(contributions)

        if majority_pct > 0.5:
            avg_conf = sum(c.confidence for c in majority) / len(majority)
            return ConsensusResult(
                agreed=True,
                result=majority[0].result,
                confidence=avg_conf,
                explanation=f"Majority vote: {len(majority)}/{len(contributions)} ({majority_pct:.0%})",
                contributions=contributions,
            )
        else:
            if human_fallback:
                return ConsensusResult(
                    agreed=True,
                    result=human_fallback(),
                    confidence=1.0,
                    explanation="Human resolved voting tie",
                    contributions=contributions,
                    escalated_to_human=True,
                )
            return ConsensusResult(
                agreed=False,
                result=None,
                confidence=0.0,
                explanation="No majority, human required",
                contributions=contributions,
                escalated_to_human=True,
            )

    def collective_iq_ratio(self, individual_score: float,
                            collective_score: float) -> float:
        """Measure collective IQ as ratio of individual performance."""
        if individual_score <= 0:
            return 0.0
        return collective_score / individual_score

    def audit_trail(self) -> list[dict]:
        return list(self._audit)


# --- Tests ---

def test_swarm_golden_angle_assignment():
    swarm = SwarmCoordinator()
    angles = []
    for i in range(8):
        agent = SwarmAgent(f"agent_{i}", f"expertise_{i}", confidence=0.8)
        swarm.add_agent(agent)
        angles.append(agent.angle)

    # All angles should be unique
    assert len(set(round(a, 3) for a in angles)) == 8


def test_consensus_coordination():
    swarm = SwarmCoordinator(CoordinationStrategy.CONSENSUS)
    for i in range(4):
        swarm.add_agent(SwarmAgent(f"a{i}", "test", confidence=0.85))

    result = swarm.coordinate("test task")
    assert result.agreed
    assert result.confidence > 0.7
    assert not result.escalated_to_human


def test_consensus_escalation():
    swarm = SwarmCoordinator(CoordinationStrategy.CONSENSUS)
    swarm.add_agent(SwarmAgent("a1", "test", confidence=0.9))
    swarm.add_agent(SwarmAgent("a2", "test", confidence=0.3))  # Low confidence

    result = swarm.coordinate("test task")
    assert not result.agreed
    assert result.escalated_to_human


def test_tournament_coordination():
    swarm = SwarmCoordinator(CoordinationStrategy.TOURNAMENT)
    swarm.add_agent(SwarmAgent("a1", "test", confidence=0.6))
    swarm.add_agent(SwarmAgent("a2", "test", confidence=0.9))
    swarm.add_agent(SwarmAgent("a3", "test", confidence=0.7))

    result = swarm.coordinate("test task")
    assert result.confidence == 0.9  # Best wins


def test_evolllm_cycle():
    evo = EvoLLM(rollback_threshold=0.9)

    models = [
        ModelSnapshot("m1", 0, {"quality": 0.8, "speed": 0.7}, time.time()),
        ModelSnapshot("m2", 0, {"quality": 0.9, "speed": 0.6}, time.time()),
        ModelSnapshot("m3", 0, {"quality": 0.7, "speed": 0.9}, time.time()),
    ]

    def benchmark(model_id):
        for m in models:
            if m.model_id == model_id:
                return m.metrics
        return {}

    def approve(model):
        return True  # Auto-approve for test

    result = evo.evolve_cycle(models, benchmark, approve)
    assert result is not None
    assert result.model_id.startswith("merged")


def test_evolllm_rollback():
    evo = EvoLLM(rollback_threshold=0.95)

    # Set high baseline
    evo.baseline_metrics = {"quality": 1.0, "speed": 1.0}

    models = [
        ModelSnapshot("m1", 1, {"quality": 0.5, "speed": 0.5}, time.time()),  # Poor
    ]

    def benchmark(model_id):
        return {"quality": 0.5, "speed": 0.5}

    def approve(model):
        return True

    result = evo.evolve_cycle(models, benchmark, approve)
    assert result is None  # Rolled back due to regression


def test_world_model():
    world = WorldState(timestamp=time.time())
    world.update({
        "spatial": {"robot_arm": {"x": 1.0, "y": 2.0, "z": 0.5}},
        "causal": {"heat": ["expansion", "deformation"]},
    })

    assert world.query_spatial("robot_arm") is not None
    assert "expansion" in world.query_causal("heat")
    assert world.query_causal("unknown") == []


def test_swarm_max_size():
    swarm = SwarmCoordinator()
    for i in range(MAX_SWARM_SIZE):
        swarm.add_agent(SwarmAgent(f"a{i}", "test"))

    try:
        swarm.add_agent(SwarmAgent("overflow", "test"))
        assert False, "Should have raised"
    except ValueError:
        pass  # Expected


if __name__ == "__main__":
    test_swarm_golden_angle_assignment()
    test_consensus_coordination()
    test_consensus_escalation()
    test_tournament_coordination()
    test_evolllm_cycle()
    test_evolllm_rollback()
    test_world_model()
    test_swarm_max_size()
    print("All collective intelligence tests passed!")
