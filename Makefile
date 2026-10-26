.PHONY: backend frontend lint test terraform setup clean

# ──────────────────────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────────────────────

backend:
	cd apps/backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd apps/frontend && npm run dev

# ──────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────

setup-backend:
	cd apps/backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

setup-frontend:
	cd apps/frontend && npm install

setup: setup-backend setup-frontend

# ──────────────────────────────────────────────────────────────
# Quality
# ──────────────────────────────────────────────────────────────

lint:
	cd apps/backend && source .venv/bin/activate && ruff check .

format:
	cd apps/backend && source .venv/bin/activate && ruff format .

test:
	cd apps/backend && source .venv/bin/activate && pytest tests/ -v

# ──────────────────────────────────────────────────────────────
# Infrastructure
# ──────────────────────────────────────────────────────────────

terraform-init:
	cd infra/terraform && terraform init

terraform-plan:
	cd infra/terraform && terraform plan

terraform-apply:
	cd infra/terraform && terraform apply

# ──────────────────────────────────────────────────────────────
# Clean
# ──────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
