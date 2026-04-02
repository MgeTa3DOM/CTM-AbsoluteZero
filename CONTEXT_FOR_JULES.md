# Contexte complet du projet — Pour Jules (Gemini)

Tu reprends un projet issu de 3h44 de conversations iteratives.
Ce fichier te donne tout le contexte : la vision, l'architecture, le code existant,
ce qui manque, et ce qu'on attend de toi.

---

## LA VISION

### Le probleme initial
"Comment creer une IA qui ne perd pas le controle ?"

### La reponse
Pas par l'alignement comportemental (fragile).
Par l'architecture (inviolable).

Un systeme ou :
- L'IA **ne peut pas** cacher ses intentions → `.explain()` obligatoire, le compilateur refuse sinon
- L'IA **ne peut pas** effacer ses traces → WORM (Write-Once Read-Many), immutable
- L'IA **ne peut pas** escalader ses privileges → capabilities declaratives, kernel-enforced
- L'IA **ne peut pas** boucler a l'infini → timeouts Fibonacci, preemption garantie
- L'IA **ne peut pas** prendre le controle → Human-In-The-Loop pour decisions critiques

Le controle humain est une **propriete de l'architecture**, pas un espoir.

---

## LE STANDARD : LIVING CODE

Le projet implemente un nouveau standard appele **LIVING CODE** :

**L** = Logging Self-Introspection → Le code s'observe lui-meme pendant l'execution
**I** = Information-Native Execution → Code et donnees sont unifies
**V** = Versioned Self-Modification → Le code se reecrit, chaque version est tracee
**I** = Integrally Transparent → Chaque decision porte son explication dans le code
**N** = Network Cooperative → Les agents partagent leurs pensees en temps reel
**G** = Growth-Optimized → L'intelligence se mesure par compression (plus tu compresses, plus tu comprends)

Ce n'est pas une spec theorique. C'est implemente et ca tourne.

---

## L'ARCHITECTURE : 5 COUCHES

```
Couche 5: Intelligence Collective
  Swarms multi-agents, World Models, EvoLLM (evolution hebdomadaire)
  → python/src/living/network.py + growth.py
       |
Couche 4: Fibra Runtime
  Scheduling par angle d'or (137.5°), zero-deadlock, timeouts Fibonacci
  → crates/fibra/ (Rust) + packages/api/src/fibra.ts (Bun)
       |
Couche 3: Orchestration AIML
  Pipelines declaratifs d'agents, coordination, consensus
  → python/src/living/network.py (Collective, Agent)
       |
Couche 2: Langage Clarity
  Decision<T> avec .explain() obligatoire, audit WORM immutable
  → crates/clarity/ (Rust) + packages/api/src/clarity.ts (Bun)
       |
Couche 1: NKV Kernel
  Linux minimal, LSM capabilities, WORM partition, cgroup limits
  → pas encore implemente (prevu Phase 1 du plan)
```

### Pourquoi Fibra (angle d'or) ?
La nature distribue les graines de tournesol a 137.5° pour eviter
les chevauchements. Fibra utilise le meme principe pour distribuer
les taches sans conflit. C'est 3.8 milliards d'annees de R&D.
Zero deadlock par propriete mathematique (angle irrationnel).

### Pourquoi Clarity (explain obligatoire) ?
Une IA que tu ne comprends pas, tu ne peux pas la controler.
Clarity force la transparence au niveau du type system.
`Decision<T>` sans `explain` = erreur de compilation / panic runtime.

### Pourquoi WORM (audit immutable) ?
Meme l'IA ne peut pas effacer ses traces. Le log est append-only.
Pas de delete. Pas de modify. Par design (pas de methode exposee).

---

## CE QUI EXISTE DANS LE CODE

### Stack: Rust + uv (Python) + Bun (TypeScript)

**45 tests passent, 0 failures.**

### Rust (`crates/`)

**fibra** (5 tests) :
- `Scheduler` : distribue les taches par angle d'or, capacity-limited
- `FibCache` : cache multi-niveau Fibonacci (1,1,2,3,5,8,13,21 = 55 entries)
- `Task` : timeout Fibonacci avec escalation automatique
- Preemption des taches expirees (`reap()`)

**clarity** (7 tests) :
- `Decision<T>` : panic si explain vide ou confidence hors [0,1]
- `AuditEntry` : serialisation JSON pour WORM
- `AgentCaps` : capabilities declaratives (can/denied)
- `WormLog` : append-only, aucune methode delete/modify

### Python (`python/src/living/`)

**soul.py** (7 tests) :
- `Soul` : trace d'execution en temps reel
- `@soul.aware` : decorateur qui log entry/exit/error automatiquement
- `Thought` : une pensee (timestamp, fonction, event, message, confidence)
- Watchers : callbacks qui peuvent declencher des corrections mid-flight
- Persistence optionnelle sur disque (append JSON)

**skill.py** (5 tests) :
- `Skill` : wraps une callable, track versions, mesure performance
- `evolve()` : teste le candidat vs l'actuel, accepte seulement si meilleur
- `evaluate()` : score 0-1 sur test cases ponderes
- Historique complet avec reason, author, parent_version, metrics

**network.py** (5 tests) :
- `SharedMemory` : bus de messages append-only, pub/sub par topic
- `Agent` : soul + skills + acces reseau, publie ses resultats
- `Collective` : groupe d'agents, execution collective, notifications d'evolution
- Quand un agent evolue un skill, les autres sont notifies via le bus

**growth.py** (3 tests) :
- `GrowthTracker` : mesure l'intelligence par ratio de compression
- `Snapshot` : score composite (compression 50% + fiabilite 30% + adaptabilite 20%)
- Trend detection (growing/stable/declining)

**demo.py** :
- 3 agents avec un classifieur naif (57% accuracy)
- Alice evolue son skill → 100% accuracy (+75% improvement)
- Verification des 6 proprietes LIVING CODE

### Bun/TypeScript (`packages/api/`)

**types.ts** : interfaces partagees (Decision, FibraTask, Thought, Msg, etc.)

**fibra.ts** (port TS du Rust) :
- `Scheduler` : meme algo que le Rust, golden angle
- `FibCache` : meme structure Fibonacci

**clarity.ts** (port TS du Rust) :
- `decision()` : factory function, throw si explain vide
- `WormLog` : append-only, Object.freeze sur chaque entry

**server.ts** :
- API HTTP Bun avec endpoints : `/fibra/schedule`, `/fibra/complete`, `/fibra/status`,
  `/clarity/decide`, `/clarity/audit`, `/health`

**fibra.test.ts** (13 tests) :
- Tests scheduler, cache, clarity, WORM

---

## CE QUI MANQUE / A CORRIGER

### Bugs

1. **Cargo.toml** : `edition = "2024"` → doit etre `"2021"` (edition 2024 n'existe pas encore)
2. **server.ts** : `await req.json()` sans try-catch → crash sur JSON malformed

### Omissions code

3. **clarity.ts** : 0 tests dedies (teste indirectement via fibra.test.ts)
4. **Soul persistence** : `Soul(persist=Path)` ecrit sur disque mais aucun test de persistence
5. **Integration cross-layer** : aucun test qui lance le serveur Bun et envoie des requetes
6. **Pas de CI/CD** : aucun GitHub Actions, tout est manuel

### Architecture

7. **Duplication Rust <-> TypeScript** : Fibra et Clarity sont reimplementes en TS.
   Si un algo change dans le Rust, le TS est desynchronise.
   Solution envisagee : wasm-bindgen ou documenter que Rust = source of truth

8. **Layer 1 (NKV Kernel)** : pas implemente. Le WORM est simule en memoire,
   pas un vrai filesystem. Les capabilities sont declaratives mais pas enforced par un vrai LSM.

9. **EvoLLM** : le concept d'evolution hebdomadaire des modeles est decrit mais pas code.
   `growth.py` mesure l'intelligence mais ne trigger pas d'evolution automatique.

10. **World Models** : la couche "intelligence 3D spatiale/causale" n'existe pas dans le code.

### Infra

11. **justfile** present mais `just` pas installe
12. **.gitignore** incomplet (manque node_modules/ racine, .venv/)
13. **Package Python** pas installable via pip standard

---

## LES 7 GARANTIES DE SECURITE

Le projet vise ces 7 garanties. Etat actuel :

| Garantie | Mecanisme | Etat |
|----------|-----------|------|
| IA ne cache pas ses intentions | `.explain()` obligatoire | IMPLEMENTE (Clarity) |
| IA ne escalade pas ses privileges | Capabilities declaratives | PARTIEL (types existent, enforcement non) |
| IA ne efface pas ses traces | WORM append-only | IMPLEMENTE (in-memory, pas filesystem) |
| IA ne vole pas les secrets | Vault isolation | NON IMPLEMENTE |
| IA ne depasse pas ses ressources | cgroup limits | NON IMPLEMENTE |
| IA ne boucle pas a l'infini | Fibonacci timeouts | IMPLEMENTE (Fibra) |
| IA ne prend pas le controle | Human-In-The-Loop | PARTIEL (escalation_threshold existe) |

---

## COMMANDES

```sh
# Tests Rust (12 tests)
cargo test

# Tests Python (20 tests)
cd python && uv run python -m pytest tests/ -v

# Tests Bun (13 tests)
cd packages/api && bun test

# Demo end-to-end
cd python && uv run living-demo

# Serveur API
cd packages/api && bun run src/server.ts
```

---

## CE QU'ON ATTEND

L'objectif n'est pas juste de fixer des bugs.
C'est de faire en sorte que le code **incarne** la vision LIVING CODE :

- Du code qui s'observe lui-meme (soul) → deja la
- Du code qui se reecrit (skill) → deja la
- Du code qui collabore (network) → deja la
- Du code qui grandit (growth) → deja la
- Du code qui est transparent par construction (clarity) → deja la
- Du code qui ne peut pas tricher (worm) → deja la, mais seulement en memoire

Le prochain pas : que ces proprietes tiennent **en production**, pas juste en demo.
