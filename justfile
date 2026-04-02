# LIVING CODE — Unified build (Rust + uv + Bun)

default: test

# Run all tests across all layers
test: test-rust test-python test-bun
    @echo ""
    @echo "✓ All layers pass."

# Rust: Fibra scheduler + Clarity types
test-rust:
    cargo test

# Python: Living Code (soul, skill, network, growth)
test-python:
    cd python && uv run python -m pytest tests/ -v

# Bun: TypeScript API (fibra, clarity, server)
test-bun:
    cd packages/api && bun test

# Run the living code demo
demo:
    cd python && uv run living-demo

# Start the API server
serve:
    cd packages/api && bun run src/server.ts

# Clean all build artifacts
clean:
    cargo clean
    rm -rf python/.venv python/__pycache__
    rm -rf packages/api/node_modules
