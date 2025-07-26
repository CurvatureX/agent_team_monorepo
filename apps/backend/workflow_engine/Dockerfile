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
    pip install --prefix=/install -r requirements.txt

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

# Copy application code from builder
COPY --from=builder /app/workflow_engine ./
COPY --from=builder /app/shared ./shared

# Generate protobuf files
RUN python -m grpc_tools.protoc \
    --python_out=proto \
    --grpc_python_out=proto \
    --proto_path=shared/proto/engine \
    shared/proto/engine/*.proto || echo "Proto generation failed, continuing anyway"

# Fix protobuf imports
RUN find proto -name "*_pb2_grpc.py" -exec sed -i 's/^import \([a-zA-Z_][a-zA-Z0-9_]*_pb2\) as /from . import \1 as /g' {} \; || true
RUN find proto -name "*_pb2.py" -exec sed -i 's/^import \([a-zA-Z_][a-zA-Z0-9_]*_pb2\) as /from . import \1 as /g' {} \; || true

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
