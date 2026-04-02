# CTM-AbsoluteZero

**LIVING CODE** — Self-introspecting, self-modifying, cooperative AI agents.

## Stack

| Layer | Tool | What |
|-------|------|------|
| **Fibra** | Rust | Golden-angle task scheduler, zero-deadlock, Fibonacci cache |
| **Clarity** | Rust | Decision types with mandatory `.explain()`, WORM audit log |
| **Living Code** | Python (uv) | Soul, Skill, Network, Growth — self-modifying agents |
| **API** | Bun (TypeScript) | HTTP server exposing Fibra + Clarity + agent collective |

## Quick start

```sh
# Run all tests (Rust + Python + Bun)
cargo test && cd python && uv run python -m pytest tests/ -v && cd ../packages/api && bun test

# Run the demo
cd python && uv run living-demo

# Start the API
cd packages/api && bun run src/server.ts
```

## What it does

3 agents start with a naive text classifier (57% accuracy).
One agent evolves its skill autonomously → 100% accuracy.
Every decision is traced (soul), versioned (skill), shared (network), and measured (growth).

```
[2] Baseline: alice=57%, bob=57%, carol=57%
[3] Alice evolved: score=100% (+75% improvement)
[4] 'Not bad at all' → alice=positive, bob=negative, carol=negative
```

## Structure

```
crates/fibra/        Rust — golden-angle scheduler
crates/clarity/      Rust — transparent decision types
python/src/living/   Python — soul, skill, network, growth, demo
packages/api/src/    Bun — TypeScript API + tests
```
