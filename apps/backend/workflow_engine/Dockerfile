# Multi-stage Dockerfile for Workflow Engine FastAPI service
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY workflow_engine/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM base as production

# Copy application code
COPY workflow_engine/ ./workflow_engine/
COPY shared/ ./shared/

# Create necessary directories with proper permissions
RUN mkdir -p logs

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 workflow_engine && \
    chown -R workflow_engine:workflow_engine /app
USER workflow_engine

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check using HTTP endpoint instead of gRPC
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["python", "-m", "uvicorn", "workflow_engine.workflow_engine.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# Development stage (with hot reload)
FROM base as development

# Don't create non-root user in dev for easier file access
COPY workflow_engine/ ./workflow_engine/
COPY shared/ ./shared/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV DEBUG=true

EXPOSE 8000

# Health check for development
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with hot reload in development
CMD ["python", "-m", "uvicorn", "workflow_engine.workflow_engine.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
