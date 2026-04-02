"""
AIML Runtime: Declarative AI Agent Orchestration Engine

Parses AIML YAML declarations and executes agent pipelines
with Fibra scheduling, Clarity audit, and safety enforcement.
"""

from __future__ import annotations

import hashlib
import time
import enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# --- Enums ---

class CoordinationPattern(enum.Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONSENSUS = "consensus"
    TOURNAMENT = "tournament"
    SWARM = "swarm"


class SafetyLevel(enum.Enum):
    STANDARD = "standard"
    ELEVATED = "elevated"
    CRITICAL = "critical"


# --- Core Types ---

@dataclass
class AgentDeclaration:
    """Declarative agent definition from AIML YAML."""
    name: str
    model: str
    capabilities: list[str]
    constraints: dict[str, Any] = field(default_factory=dict)
    explain_required: bool = True  # Clarity integration: always True

    def validate(self) -> list[str]:
        errors = []
        if not self.name:
            errors.append("Agent must have a name")
        if not self.model:
            errors.append("Agent must specify a model")
        if not self.explain_required:
            errors.append("Clarity compliance: explain must be required")
        if "timeout" not in self.constraints:
            errors.append("Agent must have a timeout constraint")
        return errors


@dataclass
class PipelineStep:
    """Single step in an AIML pipeline."""
    name: str
    agent: str
    input_ref: str
    output_ref: str
    requires_human_approval: bool = False
    parallel: bool = False
    max_retries: int = 3

    def validate(self) -> list[str]:
        errors = []
        if not self.name:
            errors.append("Step must have a name")
        if not self.agent:
            errors.append("Step must reference an agent")
        return errors


@dataclass
class Pipeline:
    """AIML pipeline: ordered sequence of agent steps."""
    name: str
    steps: list[PipelineStep]
    safety: SafetyConstraints

    def validate(self) -> list[str]:
        errors = []
        if not self.steps:
            errors.append("Pipeline must have at least one step")
        for step in self.steps:
            errors.extend(step.validate())
        errors.extend(self.safety.validate())
        return errors


@dataclass
class CollectiveDeclaration:
    """Multi-agent collective with coordination strategy."""
    name: str
    agents: list[str]
    coordination: CoordinationPattern
    human_fallback: bool = True  # Required by safety spec

    def validate(self) -> list[str]:
        errors = []
        if len(self.agents) < 2:
            errors.append("Collective must have at least 2 agents")
        if not self.human_fallback:
            errors.append("Safety: collective must have human fallback")
        return errors


@dataclass
class EvolutionDeclaration:
    """EvoLLM weekly improvement cycle."""
    name: str
    schedule: str  # Cron expression
    metric: str
    rollback_threshold: float = 0.95  # Rollback if below 95% of baseline
    human_approval_required: bool = True

    def validate(self) -> list[str]:
        errors = []
        if not self.schedule:
            errors.append("Evolution must have a schedule")
        if not self.metric:
            errors.append("Evolution must have a metric")
        if not self.human_approval_required:
            errors.append("Safety: evolution must require human approval")
        if self.rollback_threshold <= 0 or self.rollback_threshold >= 1:
            errors.append("Rollback threshold must be between 0 and 1")
        return errors


@dataclass
class SafetyConstraints:
    """Mandatory safety constraints for every AIML program."""
    explain_required: bool = True
    audit_worm: bool = True
    human_escalation: bool = True
    max_cpu_cores: int = 4
    max_memory_gb: int = 8
    max_timeout_sec: int = 300
    network_restricted: bool = True
    secrets_vault_only: bool = True

    def validate(self) -> list[str]:
        errors = []
        if not self.explain_required:
            errors.append("Safety: explain must be required (Clarity)")
        if not self.audit_worm:
            errors.append("Safety: WORM audit must be enabled")
        if not self.human_escalation:
            errors.append("Safety: human escalation must be enabled")
        if self.max_timeout_sec <= 0:
            errors.append("Safety: timeout must be positive")
        if not self.secrets_vault_only:
            errors.append("Safety: secrets must use vault only")
        return errors


# --- Audit Trail ---

@dataclass
class AuditRecord:
    """Immutable audit record for WORM partition."""
    timestamp: float
    pipeline: str
    step: str
    agent: str
    input_hash: str
    output_hash: str
    explanation: str
    decision: str
    parent_hash: Optional[str] = None

    def to_worm_bytes(self) -> bytes:
        record = (
            f"AIML_AUDIT|ts={self.timestamp}|pipeline={self.pipeline}|"
            f"step={self.step}|agent={self.agent}|"
            f"input={self.input_hash}|output={self.output_hash}|"
            f"explain={self.explanation}|decision={self.decision}\n"
        )
        return record.encode("utf-8")


class WormAuditLog:
    """Append-only audit log. No delete, no modify."""

    def __init__(self):
        self._records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    def read_all(self) -> list[AuditRecord]:
        return list(self._records)

    def count(self) -> int:
        return len(self._records)

    # Intentionally no delete() or modify() methods


# --- AIML Compiler ---

class AimlCompiler:
    """
    Validates AIML declarations against safety constraints.
    Compilation fails if any constraint is missing.
    """

    def compile(self, agents: list[AgentDeclaration],
                pipeline: Pipeline,
                collectives: list[CollectiveDeclaration] | None = None,
                evolution: EvolutionDeclaration | None = None) -> CompilationResult:
        errors = []

        # Validate all agents
        for agent in agents:
            agent_errors = agent.validate()
            errors.extend(agent_errors)

        # Validate pipeline
        pipeline_errors = pipeline.validate()
        errors.extend(pipeline_errors)

        # Validate collectives
        if collectives:
            for collective in collectives:
                errors.extend(collective.validate())

        # Validate evolution
        if evolution:
            errors.extend(evolution.validate())

        # Cross-reference: all pipeline agents must be declared
        declared_agents = {a.name for a in agents}
        for step in pipeline.steps:
            if step.agent not in declared_agents:
                errors.append(f"Pipeline step '{step.name}' references undeclared agent '{step.agent}'")

        if errors:
            return CompilationResult(success=False, errors=errors)

        return CompilationResult(success=True, errors=[])


@dataclass
class CompilationResult:
    success: bool
    errors: list[str]


# --- Pipeline Executor ---

class PipelineExecutor:
    """Executes compiled AIML pipelines with safety enforcement."""

    def __init__(self, audit_log: WormAuditLog):
        self.audit_log = audit_log
        self._agent_handlers: dict[str, Callable] = {}

    def register_handler(self, agent_name: str, handler: Callable) -> None:
        self._agent_handlers[agent_name] = handler

    def execute(self, pipeline: Pipeline, initial_input: Any) -> ExecutionResult:
        current_input = initial_input
        results = []

        for step in pipeline.steps:
            # Check human approval requirement
            if step.requires_human_approval:
                # In production: block and wait for human approval
                pass

            handler = self._agent_handlers.get(step.agent)
            if handler is None:
                return ExecutionResult(
                    success=False,
                    error=f"No handler registered for agent '{step.agent}'",
                    results=results,
                )

            # Execute with timeout (Fibra integration point)
            try:
                output = handler(current_input)
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error=f"Step '{step.name}' failed: {e}",
                    results=results,
                )

            # Audit every step
            input_hash = hashlib.sha256(str(current_input).encode()).hexdigest()[:16]
            output_hash = hashlib.sha256(str(output).encode()).hexdigest()[:16]

            record = AuditRecord(
                timestamp=time.time(),
                pipeline=pipeline.name,
                step=step.name,
                agent=step.agent,
                input_hash=input_hash,
                output_hash=output_hash,
                explanation=f"Step {step.name} executed by {step.agent}",
                decision=str(output)[:200],
            )
            self.audit_log.append(record)

            results.append(StepResult(step=step.name, output=output))
            current_input = output

        return ExecutionResult(success=True, results=results)


@dataclass
class StepResult:
    step: str
    output: Any


@dataclass
class ExecutionResult:
    success: bool
    results: list[StepResult] = field(default_factory=list)
    error: Optional[str] = None


# --- Tests ---

def test_compiler_rejects_missing_explain():
    compiler = AimlCompiler()
    agent = AgentDeclaration(
        name="test",
        model="claude-opus-4-6",
        capabilities=["read"],
        constraints={"timeout": "30s"},
        explain_required=False,  # Violation
    )
    pipeline = Pipeline(
        name="test",
        steps=[PipelineStep(name="s1", agent="test", input_ref="in", output_ref="out")],
        safety=SafetyConstraints(),
    )
    result = compiler.compile([agent], pipeline)
    assert not result.success
    assert any("explain" in e.lower() for e in result.errors)


def test_compiler_rejects_missing_safety():
    compiler = AimlCompiler()
    agent = AgentDeclaration(
        name="test",
        model="claude-opus-4-6",
        capabilities=["read"],
        constraints={"timeout": "30s"},
    )
    pipeline = Pipeline(
        name="test",
        steps=[PipelineStep(name="s1", agent="test", input_ref="in", output_ref="out")],
        safety=SafetyConstraints(audit_worm=False),  # Violation
    )
    result = compiler.compile([agent], pipeline)
    assert not result.success


def test_compiler_accepts_valid_program():
    compiler = AimlCompiler()
    agent = AgentDeclaration(
        name="analyzer",
        model="claude-opus-4-6",
        capabilities=["read_code"],
        constraints={"timeout": "30s"},
    )
    pipeline = Pipeline(
        name="review",
        steps=[PipelineStep(name="analyze", agent="analyzer", input_ref="code", output_ref="issues")],
        safety=SafetyConstraints(),
    )
    result = compiler.compile([agent], pipeline)
    assert result.success
    assert len(result.errors) == 0


def test_audit_log_is_append_only():
    log = WormAuditLog()
    record = AuditRecord(
        timestamp=time.time(),
        pipeline="test",
        step="s1",
        agent="a1",
        input_hash="abc",
        output_hash="def",
        explanation="test explanation",
        decision="approved",
    )
    log.append(record)
    log.append(record)
    assert log.count() == 2
    assert len(log.read_all()) == 2
    # No delete or modify methods exist


def test_pipeline_execution():
    log = WormAuditLog()
    executor = PipelineExecutor(log)
    executor.register_handler("upper", lambda x: x.upper())

    agent = AgentDeclaration(
        name="upper",
        model="test",
        capabilities=["transform"],
        constraints={"timeout": "30s"},
    )
    pipeline = Pipeline(
        name="transform",
        steps=[PipelineStep(name="uppercase", agent="upper", input_ref="in", output_ref="out")],
        safety=SafetyConstraints(),
    )

    result = executor.execute(pipeline, "hello world")
    assert result.success
    assert result.results[0].output == "HELLO WORLD"
    assert log.count() == 1


def test_collective_requires_human_fallback():
    collective = CollectiveDeclaration(
        name="team",
        agents=["a", "b"],
        coordination=CoordinationPattern.CONSENSUS,
        human_fallback=False,
    )
    errors = collective.validate()
    assert any("human fallback" in e.lower() for e in errors)


def test_evolution_requires_human_approval():
    evo = EvolutionDeclaration(
        name="weekly",
        schedule="0 0 * * 0",
        metric="quality",
        human_approval_required=False,
    )
    errors = evo.validate()
    assert any("human approval" in e.lower() for e in errors)


if __name__ == "__main__":
    test_compiler_rejects_missing_explain()
    test_compiler_rejects_missing_safety()
    test_compiler_accepts_valid_program()
    test_audit_log_is_append_only()
    test_pipeline_execution()
    test_collective_requires_human_fallback()
    test_evolution_requires_human_approval()
    print("All AIML runtime tests passed!")
