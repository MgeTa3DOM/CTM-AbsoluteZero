# AIML - AI Meta Language Specification

## Version 1.0

AIML est un langage declaratif pour l'orchestration d'agents IA. Il remplace les approches imperatives (scripts, DAGs) par une specification intentionnelle de ce que les agents doivent accomplir.

---

## 1. Primitives du Langage

### 1.1 Agent Declaration

```yaml
agent:
  name: "code-reviewer"
  model: "claude-opus-4-6"
  capabilities:
    - read_code
    - suggest_fixes
    - explain_reasoning
  constraints:
    max_tokens: 8192
    timeout: 30s
    explain: required  # Clarity integration
```

### 1.2 Pipeline Declaration

```yaml
pipeline:
  name: "code-review-pipeline"
  steps:
    - agent: code-reviewer
      input: ${source_code}
      output: review_results

    - agent: fix-applier
      input: ${review_results}
      output: patched_code
      requires: human_approval  # HILT escalation

    - agent: test-runner
      input: ${patched_code}
      output: test_results
```

### 1.3 Collective Declaration

```yaml
collective:
  name: "architecture-team"
  agents:
    - code-reviewer
    - security-auditor
    - performance-analyst
  coordination: consensus  # All must agree
  voting: weighted          # By expertise area
  fallback: human_decision  # If no consensus
```

### 1.4 Evolution Declaration

```yaml
evolution:
  name: "weekly-improvement"
  schedule: "0 0 * * 0"  # Every Sunday
  strategy: evolllm
  steps:
    - evaluate: benchmark_suite
    - select: top_performers
    - merge: weighted_average
    - validate: safety_checks
    - deploy: canary_10_percent
  rollback: automatic  # If metrics drop > 5%
```

---

## 2. Type System

### 2.1 Base Types

| Type | Description | Example |
|------|-------------|---------|
| `Text` | UTF-8 string | `"Hello world"` |
| `Code` | Source code with language tag | `Code<python>("def f(): pass")` |
| `Image` | Image tensor | `Image<rgb>(224, 224)` |
| `Audio` | Audio waveform | `Audio<wav>(16000)` |
| `Embedding` | Vector representation | `Embedding<768>(...)` |
| `Decision` | Typed decision with explanation | `Decision<approve>("Reason...")` |

### 2.2 Composite Types

```yaml
types:
  ReviewResult:
    severity: enum[critical, warning, info]
    location: CodeLocation
    suggestion: Code
    explanation: Text  # Required by Clarity
    confidence: float[0.0, 1.0]

  CodeLocation:
    file: Path
    line: int
    column: int
```

---

## 3. Coordination Patterns

### 3.1 Sequential
Agents execute one after another. Output of one feeds input of next.

### 3.2 Parallel
Agents execute simultaneously. Results merged at synchronization point.

### 3.3 Consensus
All agents must agree. If disagreement, escalate to human.

### 3.4 Tournament
Agents compete. Best result (by metric) wins.

### 3.5 Swarm
Agents self-organize using Fibra scheduling. Emergent behavior.

```yaml
coordination:
  pattern: swarm
  scheduler: fibra
  angle: 137.5  # Golden angle
  max_agents: 64
  emergence_threshold: 0.8  # Collective IQ target
```

---

## 4. World Models Integration

```yaml
world_model:
  name: "physics-3d"
  type: neural_physics
  capabilities:
    - spatial_reasoning
    - temporal_prediction
    - causal_inference
  update_frequency: 100ms
  agents_with_access:
    - spatial-planner
    - robotics-controller
```

---

## 5. Safety Constraints

Every AIML program must declare safety constraints:

```yaml
safety:
  explain: required           # All decisions must be explainable
  audit: worm_partition       # Immutable audit trail
  escalation: human_in_loop   # Human approves critical decisions
  resource_limits:
    cpu: 4_cores
    memory: 8GB
    gpu: 1_device
    network: restricted       # Allowlisted endpoints only
  capabilities:
    file_system: read_only    # Unless escalated
    network: allowlist_only
    secrets: vault_only       # Never in agent memory
```

---

## 6. Runtime: Fibra Integration

AIML programs are scheduled by the Fibra runtime:

```
AIML Declaration
      |
      v
Fibra Scheduler
  - Golden angle (137.5) task distribution
  - Zero-lock concurrent execution
  - Fibonacci-bounded timeouts
  - Logarithmic cache coherence
      |
      v
NKV Kernel
  - cgroup resource enforcement
  - LSM capability checking
  - WORM audit logging
```

---

## 7. Example: Full Application

```yaml
# Complete AIML application: AI Code Assistant

application:
  name: "ai-code-assistant"
  version: "1.0"

agents:
  - name: analyzer
    model: claude-opus-4-6
    role: "Analyze code structure and identify issues"

  - name: fixer
    model: claude-opus-4-6
    role: "Generate fixes for identified issues"

  - name: tester
    model: claude-opus-4-6
    role: "Write and run tests for fixes"

  - name: reviewer
    model: claude-opus-4-6
    role: "Review fixes for quality and security"

pipeline:
  - step: analyze
    agent: analyzer
    input: ${repository}
    output: issues

  - step: fix
    agent: fixer
    input: ${issues}
    output: patches
    parallel: true  # Fix issues in parallel

  - step: test
    agent: tester
    input: ${patches}
    output: test_results

  - step: review
    agent: reviewer
    input:
      patches: ${patches}
      tests: ${test_results}
    output: final_decision
    requires: human_approval

safety:
  explain: required
  audit: worm
  max_iterations: 10
  timeout: 5m
  escalation: human_in_loop

evolution:
  schedule: weekly
  strategy: evolllm
  metric: code_quality_score
  rollback_threshold: 0.95
```

---

## 8. Compiler

The AIML compiler validates:
1. All agents have `explain: required` (Clarity compliance)
2. All pipelines have bounded iterations
3. All collectives have human fallback
4. All resources have cgroup limits
5. All secrets use vault access

Compilation fails if any safety constraint is missing.

```bash
aiml compile app.aiml --target fibra --verify safety
```
