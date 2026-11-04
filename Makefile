# ==============================================================================
# PrimeEdge (Market-OS) Development & Operations Makefile
# ==============================================================================

PYTHON ?= python
PORT ?= 8000

.PHONY: help run test test-v4 health deploy deploy-full sync lint clean

help:
	@echo "PrimeEdge Management Commands:"
	@echo "  make run         - Start local FastAPI development server (port $(PORT))"
	@echo "  make test        - Run backend test suite"
	@echo "  make test-v4     - Run V4 status & quant engine test suite"
	@echo "  make health      - Check live production health endpoint"
	@echo "  make deploy      - Deploy backend changes to Linode VPS"
	@echo "  make deploy-full - Sync full repo to Linode VPS"
	@echo "  make sync        - Sync files to Linode VPS without restarting service"
	@echo "  make clean       - Remove cached pyc and pytest cache files"

run:
	cd backend && $(PYTHON) -m uvicorn app.main:app --reload --port $(PORT)

test:
	$(PYTHON) -m pytest backend/tests/ -v

test-v4:
	cd backend && $(PYTHON) -m pytest tests/test_v4_status.py -v

health:
	@curl -s https://primeedge.app/api/v1/health || echo "Failed to reach primeedge.app"

deploy:
	bash deploy.sh

deploy-full:
	bash deploy.sh --full

sync:
	bash deploy.sh --no-restart

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
