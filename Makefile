# Makefile to simplify project commands

.PHONY: setup dev test coverage clean infra-up infra-down
.PHONY: lint format typecheck security shell logs sonar

setup:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

dev:
	./venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

test:
	./venv/bin/pytest

coverage:
	./venv/bin/pytest --cov=src --cov-report=xml --cov-report=term-missing tests/

lint:
	./venv/bin/ruff check src/ tests/

format:
	./venv/bin/ruff format src/ tests/

typecheck:
	./venv/bin/mypy src/ --no-error-summary

security:
	./venv/bin/bandit -r src/ -x venv,tests,migrations

infra-up:
	docker compose up -d db redis

infra-down:
	docker compose down

shell:
	./venv/bin/python3

logs:
	docker compose logs -f

clean:
	rm -rf venv
	rm -f test.db
	find . -type d -name "__pycache__" -exec rm -rf {} +

sonar:
	./scripts/sonar_scan.sh "auth-service-python" "Auth Service Python"
