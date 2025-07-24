# Production Dockerfile for Workflow Engine
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./
COPY requirements.txt* ./

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r pyproject.toml || \
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
        protobuf>=5.26.1,\<6.0.0

# Production stage
FROM python:3.10-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY workflow_engine/ ./
COPY shared/ ./shared/

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app && \
    chmod +x start_server.sh
USER app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SHARED_PROTO_DIR=/app/shared/proto/engine

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "server.py"]
