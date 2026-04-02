# Context pour Jules (Gemini) — Corrections a faire

## Etat reel du repo

**45 tests passent** (12 Rust, 20 Python, 13 Bun). Demo fonctionne end-to-end.
Mais il y a de la dette technique et des omissions.

---

## CORRECTIONS URGENTES

### 1. Cargo.toml: edition invalide
**Fichier**: `/Cargo.toml` ligne 3
**Bug**: `edition = "2024"` n'existe pas en Rust. Doit etre `"2021"`.
Le compilateur ignore silencieusement, mais c'est faux.

### 2. Server Bun: crash sur JSON malformed
**Fichier**: `/packages/api/src/server.ts` lignes 30 et 42
**Bug**: `await req.json()` sans try-catch. Un POST avec du JSON invalide crash le serveur.
**Fix**: wrapper dans try-catch, retourner 400.

### 3. Clarity.ts: zero tests
**Fichier**: `/packages/api/src/clarity.ts`
**Bug**: Le module `decision()` et `WormLog` n'ont aucun test propre.
Ils sont testes indirectement dans `fibra.test.ts` mais meritent des tests dedies.

### 4. Duplication Rust <-> TypeScript
**Probleme**: Fibra et Clarity existent en Rust ET en TypeScript (copie manuelle).
Les deux implementations ne sont pas liees. Si on change l'algo dans un langage,
l'autre est desynchronise.
**Options**:
- Generer le TS depuis le Rust (wasm-bindgen)
- Ou accepter la duplication et documenter que Rust = source of truth

---

## DETTE TECHNIQUE

### 5. Pas de CI/CD
Aucun `.github/workflows/`. Tests doivent etre lances manuellement.
**Besoin**: GitHub Actions avec:
- `cargo test`
- `cd python && uv run python -m pytest tests/ -v`
- `cd packages/api && bun test`

### 6. justfile sans `just` installe
Le fichier `justfile` existe mais `just` n'est pas installe dans l'environnement.
**Option A**: installer just
**Option B**: remplacer par un `Makefile` standard

### 7. .gitignore incomplet
Le `.gitignore` est centre Python. Il manque:
- `target/` (Rust — present mais enfoui ligne 76)
- `node_modules/` (present dans packages/api/.gitignore mais pas a la racine)
- `.venv/` pour Python
- `*.wasm` si on fait du wasm-bindgen plus tard

### 8. Pas de CHANGELOG ni semver
Les crates Rust sont a `0.1.0` sans plan de versioning.

---

## OMISSIONS FONCTIONNELLES

### 9. Pas d'integration test cross-layer
Le Rust compile ses libs, le Python fait son truc, le Bun fait le sien.
Aucun test ne verifie que les 3 layers fonctionnent ensemble.
**Besoin**: un test d'integration qui:
1. Demarre le serveur Bun
2. Envoie des requetes HTTP
3. Verifie les reponses

### 10. Python package: pas installable standalone
`from living import Soul` ne marche que via `uv run`.
Le package n'est pas installable avec `pip install .` classique.
**Fix**: ajouter un `setup.py` ou verifier que le `pyproject.toml` est compatible pip.

### 11. Bun server: routes hardcodees
Les endpoints `/fibra/schedule`, `/clarity/decide`, etc. sont des strings en dur.
Pas de router, pas de middleware, pas de validation d'input.

### 12. Pas de logging structure
Le serveur Bun fait `console.log`. Pas de logger structure (JSON logs, niveaux, etc.).

### 13. Soul persistence: pas testee
`Soul(persist=Path)` ecrit sur disque mais aucun test ne verifie la persistence.

---

## ARCHITECTURE DU REPO

```
CTM-AbsoluteZero/
├── Cargo.toml              # Rust workspace (fibra + clarity)
├── Cargo.lock
├── README.md
├── justfile                # Task runner (needs `just` CLI)
├── crates/
│   ├── fibra/src/lib.rs    # Golden-angle scheduler + Fib cache (5 tests)
│   └── clarity/src/lib.rs  # Decision<T> + WORM log (7 tests)
├── python/
│   ├── pyproject.toml      # uv package config
│   ├── src/living/
│   │   ├── soul.py         # Self-introspecting execution trace
│   │   ├── skill.py        # Versioned self-modifying functions
│   │   ├── network.py      # Multi-agent shared memory
│   │   ├── growth.py       # Compression-based intelligence metric
│   │   └── demo.py         # End-to-end demo
│   └── tests/              # 20 pytest tests
│       ├── test_soul.py
│       ├── test_skill.py
│       ├── test_network.py
│       └── test_growth.py
└── packages/api/
    ├── package.json        # Bun project
    └── src/
        ├── types.ts        # Shared TypeScript interfaces
        ├── fibra.ts        # Scheduler + FibCache (TS port)
        ├── clarity.ts      # Decision + WormLog (TS port)
        ├── server.ts       # HTTP API (Bun.serve)
        └── fibra.test.ts   # 13 bun:test tests
```

## COMMANDES POUR TESTER

```sh
# Rust
cargo test

# Python
cd python && uv run python -m pytest tests/ -v

# Bun
cd packages/api && bun test

# Demo
cd python && uv run living-demo

# Serveur API
cd packages/api && bun run src/server.ts
```

## PRIORITE DES FIXES

| # | Quoi | Priorite | Effort |
|---|------|----------|--------|
| 1 | Fix edition Cargo.toml | P0 | 1 min |
| 2 | try-catch JSON server.ts | P0 | 5 min |
| 3 | Tests clarity.ts | P1 | 15 min |
| 5 | CI/CD GitHub Actions | P1 | 30 min |
| 9 | Integration tests | P1 | 1h |
| 4 | Documenter duplication Rust/TS | P2 | 15 min |
| 7 | Consolider .gitignore | P2 | 5 min |
| 10 | pip install compatible | P2 | 15 min |
| 11 | Router + validation Bun | P3 | 1h |
| 13 | Test persistence Soul | P3 | 15 min |
