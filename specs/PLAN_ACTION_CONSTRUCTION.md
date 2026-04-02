# PLAN D'ACTION CONSTRUCTION - AI-OS 2026

## Timeline : 8 Mois, 5 Phases

---

## Phase 1 : Foundation (Mois 1-2)

### Objectif
Kernel minimal bootable avec garanties de securite.

### Taches

| Semaine | Tache | Livrable |
|---------|-------|----------|
| S1 | Fork Linux minimal (defconfig strip) | Kernel < 10MB |
| S2 | Implement LSM module NKV | Capability checks |
| S3 | WORM partition driver | Write-once filesystem |
| S4 | cgroup v2 agent profiles | Resource isolation |
| S5 | Secure boot chain | Verified boot |
| S6 | Boot optimization | < 2s cold boot |
| S7 | Integration tests | All Layer 1 tests pass |
| S8 | Documentation + review | Peer-reviewed spec |

### Criteres de Succes
- [ ] Boot time < 2 secondes
- [ ] Image < 50 MB
- [ ] LSM refuse acces non-autorise
- [ ] WORM refuse deletion
- [ ] cgroup kill process hors limites

### Equipe
- 2 kernel developers
- 1 security engineer
- 1 QA engineer

---

## Phase 2 : Language (Mois 2-4)

### Objectif
Compilateur Clarity fonctionnel avec toutes les contraintes de transparence.

### Taches

| Semaine | Tache | Livrable |
|---------|-------|----------|
| S9 | Clarity grammar + parser (LALR) | AST generation |
| S10 | Type system implementation | Type checker |
| S11 | .explain() enforcement | Compiler rejects opaque code |
| S12 | .audit_log() integration | WORM write on every decision |
| S13 | capabilities.clar parser | Permission declarations |
| S14 | Standard library | Core types + functions |
| S15 | Optimization passes | Performant codegen |
| S16 | Tooling (LSP, formatter) | Developer experience |

### Criteres de Succes
- [ ] Compiler refuse code sans .explain()
- [ ] Audit logs ecrits sur WORM
- [ ] capabilities.clar parsed et enforced
- [ ] Performance comparable a Rust
- [ ] LSP fonctionnel dans VSCode

### Equipe
- 2 compiler engineers
- 1 language designer
- 1 tooling engineer

---

## Phase 3 : Orchestration (Mois 4-6)

### Objectif
Runtime AIML + Fibra scheduler operationnels.

### Taches

| Semaine | Tache | Livrable |
|---------|-------|----------|
| S17 | AIML parser + validator | YAML -> IR |
| S18 | Pipeline execution engine | Sequential + parallel |
| S19 | Collective coordination | Consensus, tournament, swarm |
| S20 | Fibra scheduler core | Golden angle distribution |
| S21 | Fibonacci cache | Log-structured cache |
| S22 | Timeout management | Fibonacci-bounded preemption |
| S23 | AIML <-> Clarity bridge | Cross-layer integration |
| S24 | Stress testing | 256 concurrent agents |

### Criteres de Succes
- [ ] AIML programs compile and execute
- [ ] Fibra: zero deadlocks in 10M test runs
- [ ] 256 concurrent agents stable
- [ ] Fibonacci timeouts preempt correctly
- [ ] Cross-layer audit trail complete

### Equipe
- 2 runtime engineers
- 1 distributed systems engineer
- 1 performance engineer

---

## Phase 4 : Intelligence (Mois 6-7)

### Objectif
Intelligence collective emergente avec World Models et EvoLLM.

### Taches

| Semaine | Tache | Livrable |
|---------|-------|----------|
| S25 | World model integration | Neural physics 3D |
| S26 | Swarm coordination | Emergent behavior |
| S27 | Collective IQ metrics | Measurement framework |
| S28 | EvoLLM weekly cycle | Model evolution pipeline |

### Criteres de Succes
- [ ] Collective IQ >= 1.5x individual
- [ ] World model spatial reasoning functional
- [ ] EvoLLM improves metrics weekly
- [ ] Rollback works on regression
- [ ] Human approval gate functional

### Equipe
- 2 ML engineers
- 1 research scientist
- 1 evaluation engineer

---

## Phase 5 : Production (Mois 7-8)

### Objectif
Systeme complet, audite, documente, open-source.

### Taches

| Semaine | Tache | Livrable |
|---------|-------|----------|
| S29 | Security audit (external) | Audit report |
| S30 | Performance benchmarks | Published benchmarks |
| S31 | Documentation complete | User + developer docs |
| S32 | Open-source release | GitHub + Apache 2.0 |

### Criteres de Succes
- [ ] External security audit: no critical findings
- [ ] All 7 security guarantees verified
- [ ] Performance meets all specs
- [ ] Documentation complete
- [ ] Community contribution guide

### Equipe
- 1 security auditor (external)
- 1 technical writer
- 1 community manager
- All previous team members for support

---

## Budget Estime

| Poste | Cout/Mois | Total (8 mois) |
|-------|-----------|-----------------|
| Kernel team (3) | 45K EUR | 360K EUR |
| Compiler team (3) | 45K EUR | 270K EUR (6 mois) |
| Runtime team (3) | 40K EUR | 200K EUR (5 mois) |
| ML team (3) | 50K EUR | 150K EUR (3 mois) |
| Infra (CI/CD, cloud) | 10K EUR | 80K EUR |
| Security audit | - | 50K EUR |
| **Total** | | **~1.1M EUR** |

---

## Risques et Mitigations

| Risque | Probabilite | Impact | Mitigation |
|--------|------------|--------|------------|
| Clarity compiler delays | Medium | High | Start with subset, iterate |
| Fibra scheduling bugs | Low | High | Formal verification of core algorithm |
| EvoLLM regression | Medium | Medium | Automated rollback + canary |
| Talent acquisition | High | High | Open-source community, bounties |
| Performance targets missed | Low | Medium | Profile early, optimize late |

---

## Definition of Done

Le projet est considere DONE quand :

1. Boot < 2 secondes (mesure)
2. Image < 50 MB (mesure)
3. 7 tests de securite passent (automatise)
4. Clarity refuse code sans explain (automatise)
5. Fibra: 0 deadlocks en 10M runs (automatise)
6. Collective IQ >= 1.5x (benchmark)
7. EvoLLM: amelioration mesurable par semaine (metric)
8. Audit externe: 0 critique (rapport)
9. Documentation complete (checklist)
10. Licence Apache 2.0 publiee (GitHub)
