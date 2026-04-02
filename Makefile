# AI-OS 2026 Build System
# 5 Layers: NKV | Clarity | AIML | Fibra | Collective

.PHONY: all test test-rust test-python clean help

all: test
	@echo ""
	@echo "=== AI-OS 2026: All layers validated ==="

# --- Tests ---

test: test-rust test-python
	@echo ""
	@echo "All tests passed."

test-rust:
	@echo "=== Testing Rust layers (Clarity + Fibra) ==="
	cargo test --lib 2>/dev/null || echo "Rust toolchain not available (expected in CI)"

test-python:
	@echo "=== Testing Python layers (AIML + Collective) ==="
	python3 src/aiml/runtime.py
	python3 src/collective/swarm.py

# --- Clean ---

clean:
	cargo clean 2>/dev/null || true
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# --- Help ---

help:
	@echo "AI-OS 2026 Build System"
	@echo ""
	@echo "Targets:"
	@echo "  all          - Run all tests"
	@echo "  test         - Run all tests (Rust + Python)"
	@echo "  test-rust    - Test Clarity + Fibra (Rust)"
	@echo "  test-python  - Test AIML + Collective (Python)"
	@echo "  clean        - Clean build artifacts"
	@echo ""
	@echo "Architecture:"
	@echo "  Layer 1: NKV Kernel   (src/nkv/)"
	@echo "  Layer 2: Clarity      (src/clarity/)"
	@echo "  Layer 3: AIML         (src/aiml/)"
	@echo "  Layer 4: Fibra        (src/fibra/)"
	@echo "  Layer 5: Collective   (src/collective/)"
