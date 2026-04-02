# LUX : Transparent AI Language

## Philosophie

LUX (du latin "lumiere") est un langage de programmation concu pour que le code IA soit aussi lisible que la prose. Si un humain ne peut pas comprendre ce que fait le code, le code ne devrait pas exister.

---

## Principes de Design

### 1. Lisibilite Absolue
Le code LUX se lit comme une intention, pas comme une instruction machine.

### 2. Transparence Forcee
Chaque decision, chaque calcul, chaque transformation doit etre tracable et explicable.

### 3. Securite par Construction
Les operations dangereuses sont impossibles par design syntaxique.

---

## Syntaxe

### Declaration d'Agent

```lux
agent CodeReviewer:
    purpose: "Analyser le code source et suggerer des ameliorations"
    can: [read_files, suggest_changes]
    cannot: [modify_files, access_network, read_secrets]

    when confidence < 70%:
        escalate to human with explanation
```

### Decision Transparente

```lux
decide risk_level from data:
    extract features from data
    compute score using model("risk-classifier")

    if score > 0.8:
        return High because "score {score} exceeds critical threshold 0.8"
    elif score > 0.4:
        return Medium because "score {score} in warning range 0.4-0.8"
    else:
        return Low because "score {score} below warning threshold 0.4"

    -- This is REQUIRED. LUX refuses to compile decisions without 'because'.
```

### Pipeline

```lux
pipeline ReviewAndFix:
    step 1: Analyzer reads repository
        produces: list of issues
        explains: "Found {count} issues in {files} files"

    step 2: Fixer generates patches for each issue
        produces: list of patches
        explains: "Generated {count} fixes, confidence avg {avg_conf}%"
        runs: in parallel

    step 3: Tester validates each patch
        produces: test results
        explains: "Passed {pass}/{total} tests"

    step 4: Reviewer approves final changes
        produces: approval decision
        requires: human confirmation
        explains: "Recommending {action} because {reasons}"
```

### Swarm Coordination

```lux
swarm ArchitectureTeam:
    members: [CodeReviewer, SecurityAuditor, PerformanceAnalyst]
    coordinate by: consensus
    if disagreement: ask human

    collective goal: "Produce architecture review"
    each member contributes: their expertise area
    final output merges: all contributions weighted by confidence
```

### Evolution

```lux
evolve weekly:
    evaluate all agents on benchmark_suite
    select top 20% as parents
    merge parents into next generation
    validate safety constraints still hold

    if any metric drops > 5%:
        rollback immediately
        alert human: "Evolution regression detected"

    if all metrics improve:
        deploy canary 10%
        wait 24 hours
        if stable: deploy 100%
        requires: human approval for production
```

---

## Guarantees

### What LUX Guarantees
1. Every decision has a `because` clause (compiler enforced)
2. Every action is logged immutably (WORM integration)
3. Every agent has declared capabilities (cannot exceed them)
4. Every pipeline has bounded execution (timeouts)
5. Every escalation reaches a human (guaranteed delivery)

### What LUX Prevents
1. Opaque decisions (no `because` = no compile)
2. Privilege escalation (capabilities are declarative and immutable)
3. Infinite loops (Fibonacci-bounded timeouts)
4. Secret access (vault proxy, never direct)
5. Trace deletion (WORM partition, physically immutable)

---

## Compilation

LUX compiles to Clarity intermediate representation, which compiles to native code via LLVM.

```
LUX source (.lux)
    |
    v
LUX compiler (checks: because, capabilities, bounds)
    |
    v
Clarity IR (.clar)
    |
    v
Clarity compiler (checks: explain, audit, types)
    |
    v
LLVM IR
    |
    v
Native code (runs on NKV kernel)
```

---

## Example: Complete Application

```lux
-- AI Code Assistant in LUX

agent Analyzer:
    purpose: "Find issues in source code"
    can: [read_files("src/**/*")]
    cannot: [modify_files, access_network]

agent Fixer:
    purpose: "Generate fixes for code issues"
    can: [read_files("src/**/*"), suggest_changes]
    cannot: [apply_changes, access_network]

agent Tester:
    purpose: "Validate fixes with tests"
    can: [read_files, run_tests]
    cannot: [modify_source, access_network]

pipeline AssistDeveloper:
    step 1: Analyzer scans repository
        produces: issues
        explains: "Scanned {file_count} files, found {issue_count} issues"

    step 2: Fixer creates patches for issues
        produces: patches
        explains: "Created {patch_count} patches, avg confidence {conf}%"
        runs: in parallel

    step 3: Tester validates patches
        produces: results
        explains: "Validated: {pass} passed, {fail} failed"

    step 4: human reviews and approves
        explains: "Summary: {pass} fixes ready, {fail} need revision"

safety:
    max_runtime: 5 minutes
    max_memory: 4 GB
    audit: every decision to WORM
    escalate: if confidence < 70% or action is destructive

evolve weekly:
    metric: code_quality_improvement
    rollback_if: metric drops > 5%
    requires: human approval
```

---

## Relation to Other Layers

| Layer | LUX Role |
|-------|----------|
| NKV Kernel | LUX capabilities map to LSM permissions |
| Clarity | LUX compiles to Clarity IR |
| AIML | LUX is the human-readable form of AIML |
| Fibra | LUX pipelines are scheduled by Fibra |
| Collective | LUX swarms produce emergent intelligence |

LUX est le point d'entree pour les developpeurs. C'est le langage qu'ils ecrivent. Tout le reste est infrastructure.
