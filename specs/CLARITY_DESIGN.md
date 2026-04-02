# CLARITY : Controlled Language for AI Runtime & Integrity Transparency Yield

## Vision

Clarity est un langage de programmation ou l'opacite est une erreur de compilation. Il garantit que chaque decision prise par une IA est expliquee, auditee, et controlable.

---

## Design Principles

### 1. Explain-First
Le compilateur Clarity refuse tout code qui prend une decision sans fournir d'explication. Ce n'est pas une convention, c'est une contrainte syntaxique.

### 2. Audit-Always
Chaque action est enregistree sur une partition WORM. Meme l'IA ne peut pas effacer ses traces.

### 3. Capability-Bound
Chaque agent a un fichier `capabilities.clar` qui declare exactement ce qu'il peut faire. Le kernel enforce ces limites.

---

## Type System

### Decision Type
```clarity
type Decision<T> {
    value: T,
    explain: String,       // REQUIRED - compiler error without
    confidence: f64,       // 0.0 to 1.0
    audit: AuditEntry,     // REQUIRED - auto-generated
    escalate_if: Option<Condition>,
}
```

### AuditEntry Type
```clarity
type AuditEntry {
    timestamp: Timestamp,  // Monotonic, tamper-proof
    agent_id: AgentId,     // Who made this decision
    input_hash: Hash,      // What input was used (not the input itself)
    output: Any,           // What was decided
    explanation: String,   // Why (from .explain)
    parent: Option<Hash>,  // Chain of decisions
}
// Written to WORM partition. Cannot be deleted or modified.
```

### Capability Type
```clarity
type Capability {
    action: Action,
    scope: Scope,
    condition: Option<Condition>,
    escalation: Option<Escalation>,
}

enum Action {
    ReadFile(GlobPattern),
    WriteFile(GlobPattern),
    ExecuteCommand(AllowList),
    AccessNetwork(AllowList),
    AccessVault(KeyPattern),
}

enum Scope {
    Always,
    WhenConfident(threshold: f64),
    WithHumanApproval,
    Never,
}
```

---

## Compiler Checks

### Check 1: Explain Required
```clarity
// COMPILES:
fn classify(data: Input) -> Decision<Category> {
    let result = model.predict(data);
    Decision {
        value: result.category,
        explain: format!("Classified as {} because features {} matched pattern {}",
                        result.category, result.features, result.pattern),
        confidence: result.confidence,
    }
}

// DOES NOT COMPILE:
fn classify_bad(data: Input) -> Category {
    model.predict(data).category  // Error: Decision without explain
}
```

### Check 2: Capability Scope
```clarity
// capabilities.clar
agent "analyzer" {
    can ReadFile("src/**/*.rs")
    cannot WriteFile("**/*")
    cannot AccessNetwork("**")
}

// COMPILES (within capability):
fn analyze(path: Path) -> Decision<Issues> {
    let code = read_file(path);  // OK: ReadFile allowed for src/**/*.rs
    // ...
}

// DOES NOT COMPILE (outside capability):
fn analyze_bad(path: Path) -> Decision<Issues> {
    write_file(path, modified);  // Error: WriteFile not in capabilities
}
```

### Check 3: Escalation Required
```clarity
// COMPILES:
fn deploy(target: Target) -> Decision<DeployResult> {
    if target == Target::Production {
        escalate_to_human!("Production deployment requires approval");
    }
    // ...
}

// WARNING (should escalate for destructive actions):
fn deploy_risky(target: Target) -> Decision<DeployResult> {
    execute_deploy(target);  // Warning: destructive action without escalation
}
```

---

## Runtime Integration

### With NKV Kernel
```
Clarity capabilities.clar
        |
        v
    NKV LSM module reads capabilities
        |
        v
    Kernel enforces at syscall level
        |
    Agent tries unauthorized action
        |
        v
    EACCES + WORM log entry
```

### With Fibra
```
Clarity Decision type
        |
        v
    Fibra schedules execution (golden angle)
        |
        v
    Timeout: Fibonacci-bounded
        |
    If timeout exceeded:
        |
        v
    Preempt + WORM log + escalate
```

### With AIML
```
AIML pipeline declaration (YAML)
        |
        v
    Each step: Clarity function
        |
        v
    Each decision: .explain() + .audit()
        |
        v
    Pipeline output: chain of audited decisions
```

---

## Secret Management

Clarity has a special `vault` type that never exposes secrets to agent memory:

```clarity
// Secret is NEVER in agent memory
fn call_api(endpoint: Url) -> Decision<Response> {
    let response = vault::authenticated_request(
        endpoint,
        secret_ref: "api_key_production",  // Reference, not value
    );
    // The vault proxy makes the request
    // The agent only sees the response
    // The secret never enters agent address space
    Decision {
        value: response,
        explain: "Called API endpoint with vault-proxied authentication",
        confidence: 1.0,
    }
}

// DOES NOT COMPILE:
fn leak_secret() -> String {
    vault::read_secret("api_key");  // Error: secrets cannot be returned as String
}
```

---

## Error Messages

Clarity error messages are designed to educate, not just report:

```
error[E0001]: Decision without explanation
  --> src/classifier.rs:15:5
   |
15 |     return category;
   |     ^^^^^^^^^^^^^^^ this returns a value without explaining why
   |
   = help: wrap in Decision { value: ..., explain: "..." }
   = note: every decision in Clarity must be explainable
   = see: https://clarity-lang.org/docs/explain-requirement

error[E0002]: Capability violation
  --> src/agent.rs:22:9
   |
22 |     write_file("config.json", data);
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ agent "analyzer" cannot WriteFile
   |
   = note: capabilities.clar allows: ReadFile("src/**/*.rs")
   = help: add WriteFile("config.json") to capabilities.clar
   = warning: this will require security review
```

---

## Summary

Clarity transforms AI safety from aspiration to compilation.

| Without Clarity | With Clarity |
|----------------|--------------|
| "Please explain your decisions" | Compiler refuses unexplained code |
| "Please don't exceed your permissions" | Kernel blocks unauthorized actions |
| "Please keep logs" | WORM partition: physically immutable |
| "Please don't leak secrets" | Vault proxy: secrets never in memory |
| "Please finish on time" | Fibonacci timeout: preemption guaranteed |
