# ProductAgents — developer task runner.
#
# One entrypoint over the Python (uv), frontend (npm), and desktop (Tauri)
# workflows. Run `make` or `make help` to list targets. Recipes are thin
# wrappers around the canonical commands documented in CLAUDE.md.

DESKTOP := desktop

.DEFAULT_GOAL := help

# ---- meta ---------------------------------------------------------------

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: doctor
doctor: ## Check required tools (uv, node, cargo) are installed
	@command -v uv    >/dev/null 2>&1 && echo "  ok      uv    $$(uv --version)"        || echo "  MISSING uv    -> https://docs.astral.sh/uv/"
	@command -v node  >/dev/null 2>&1 && echo "  ok      node  $$(node --version)"      || echo "  MISSING node  -> https://nodejs.org  (>= 18)"
	@command -v cargo >/dev/null 2>&1 && echo "  ok      cargo $$(cargo --version)"     || echo "  MISSING cargo -> curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   (only needed for 'make gui')"

# ---- setup --------------------------------------------------------------

.PHONY: setup
setup: ## Full setup: Python deps + frontend deps + Playwright browser
	uv sync
	cd $(DESKTOP) && npm install
	cd $(DESKTOP) && npx playwright install chromium
	@echo "Setup complete. 'make gui' also needs a Rust toolchain (run 'make doctor')."

.PHONY: sync
sync: ## Install/refresh Python deps only (uv sync)
	uv sync

# ---- run ----------------------------------------------------------------

.PHONY: gui
gui: ## Launch the desktop GUI (Tauri dev window; needs Rust)
	cd $(DESKTOP) && npm run tauri dev

.PHONY: dev-web
dev-web: ## Serve only the React frontend in a browser (http://localhost:1420)
	cd $(DESKTOP) && npm run dev

.PHONY: bridge
bridge: ## Run the dev WebSocket bridge (browser/Playwright UI testing)
	uv run productagents serve-ws

# ---- quality & tests ----------------------------------------------------

.PHONY: test
test: test-py test-web ## Run all unit tests (Python + frontend)

.PHONY: test-py
test-py: ## Run the Python test suite (pytest + coverage)
	uv run pytest

.PHONY: test-web
test-web: ## Run the frontend unit tests (Vitest)
	cd $(DESKTOP) && npm test

.PHONY: e2e
e2e: ## Run the Playwright browser e2e suite (boots Vite + the WS bridge)
	cd $(DESKTOP) && npm run e2e

.PHONY: lint
lint: ## Lint + format-check (ruff), import-layer contracts, bandit — mirrors CI
	uv run ruff check .
	uv run ruff format --check .
	uv run lint-imports
	uv run bandit -c pyproject.toml -r packages -q

.PHONY: typecheck
typecheck: ## Type-check Python (ty)
	uv run ty check

.PHONY: contrast
contrast: ## Verify WCAG contrast of the design tokens (design/contrast.py; exits 1 on failures)
	python3 design/contrast.py

.PHONY: build-web
build-web: ## Type-check + production-build the frontend
	cd $(DESKTOP) && npm run build

.PHONY: build-sidecar
build-sidecar: ## Freeze the IPC sidecar binary into desktop/src-tauri/binaries/
	bash desktop/packaging/build-sidecar.sh

.PHONY: package
package: build-sidecar ## Build the installable desktop app (bundles the sidecar)
	cd desktop && npm run tauri build

.PHONY: check
check: lint typecheck test-py test-web build-web contrast ## Full gate: lint + types + unit tests + frontend build + contrast

# ---- clean --------------------------------------------------------------

.PHONY: clean
clean: ## Remove build & test artifacts (keeps installed deps)
	rm -rf htmlcov .coverage .pytest_cache .ruff_cache .ty_cache
	find . -type d -name __pycache__ -not -path './.venv/*' -not -path '*/node_modules/*' -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(DESKTOP)/dist $(DESKTOP)/playwright-report $(DESKTOP)/test-results $(DESKTOP)/src-tauri/gen/schemas
	@echo "Cleaned build & test artifacts."

.PHONY: clean-all
clean-all: clean ## Deep clean: also remove .venv, node_modules, and Rust target
	rm -rf .venv $(DESKTOP)/node_modules $(DESKTOP)/src-tauri/target
	@echo "Removed .venv, node_modules, and Rust target. Run 'make setup' to rebuild."
