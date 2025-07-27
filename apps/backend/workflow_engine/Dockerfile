# Production Dockerfile for Workflow Engine
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy workflow engine and shared files
COPY workflow_engine/ ./workflow_engine/
COPY shared/ ./shared/
COPY workflow_engine/pyproject.toml ./
COPY workflow_engine/requirements.txt* ./

# Install dependencies
RUN pip install --upgrade pip && \
    (pip install --prefix=/install -r requirements.txt || \
    pip install --prefix=/install \
        fastapi>=0.104.0 \
        uvicorn[standard]>=0.24.0 \
        pydantic>=2.5.0 \
        pydantic-settings>=2.0.0 \
        sqlalchemy>=2.0.0 \
        alembic>=1.12.0 \
        psycopg2-binary>=2.9.0 \
        redis>=5.0.0 \
        grpcio>=1.68.0 \
        grpcio-tools>=1.68.0 \
        protobuf>=5.26.1,<6.0.0 \
        grpcio-health-checking \
        croniter)

# Production stage
FROM python:3.10-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code from builder
COPY --from=builder /app/workflow_engine/workflow_engine ./workflow_engine
COPY --from=builder /app/shared ./shared

# Generate protobuf files using the existing script
RUN python -c "import sys, os; sys.path.insert(0, '.'); from workflow_engine.generate_proto import generate_proto_files; generate_proto_files()" || echo "Proto generation failed, continuing anyway"

# Create top-level proto symlink for imports to work
RUN ln -sf /app/workflow_engine/proto /app/proto

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app
USER app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SHARED_PROTO_DIR=/app/shared/proto/engine

# Expose port
EXPOSE 50050

# Health check - use TCP connection test for gRPC
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD nc -z localhost 50050 || exit 1

# Run application directly
CMD ["python", "-m", "workflow_engine"]
