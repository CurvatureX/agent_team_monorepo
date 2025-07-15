# Workflow Engine Makefile

.PHONY: help install proto clean test run dev

# Default target
help:
	@echo "Available targets:"
	@echo "  install    - Install dependencies"
	@echo "  proto      - Generate Python code from protobuf files"
	@echo "  clean      - Clean generated files"
	@echo "  test       - Run tests"
	@echo "  run        - Run the application"
	@echo "  dev        - Run in development mode"
	@echo "  db-init    - Initialize database"
	@echo "  db-migrate - Create database migration"
	@echo "  db-upgrade - Apply database migrations"
	@echo "  db-reset   - Reset database"

# Install dependencies
install:
	pip install -e .

# Generate protobuf Python code
proto:
	python scripts/generate_proto.py

# Clean generated files
clean:
	rm -rf workflow_engine/proto/*.py
	rm -rf workflow_engine/proto/__pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Run tests
test:
	pytest tests/ -v

# Run application
run:
	uvicorn workflow_engine.main:app --host 0.0.0.0 --port 8000

# Run in development mode
dev:
	uvicorn workflow_engine.main:app --host 0.0.0.0 --port 8000 --reload

# Database commands
db-init:
	alembic init alembic

db-migrate:
	alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	alembic upgrade head

db-reset:
	alembic downgrade base
	alembic upgrade head 