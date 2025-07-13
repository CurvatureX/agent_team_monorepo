.PHONY: help install install-dev test lint format clean proto

help:
	@echo "Available commands:"
	@echo "  install     - Install production dependencies"
	@echo "  install-dev - Install development dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo "  proto       - Generate Python code from protobuf files"
	@echo "  clean       - Clean build artifacts"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

lint:
	flake8 workflow_engine/
	mypy workflow_engine/

format:
	black workflow_engine/
	isort workflow_engine/

proto:
	cd protobuf && python generate_python.py

# Database commands
db-init:
	alembic upgrade head

db-migrate:
	alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-schema:
	psql $(DATABASE_URL) < database/schema.sql

db-seed:
	psql $(DATABASE_URL) < database/seed_data.sql

db-reset:
	dropdb --if-exists workflow_engine && createdb workflow_engine
	$(MAKE) db-schema
	$(MAKE) db-seed

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf workflow_engine/proto/ 