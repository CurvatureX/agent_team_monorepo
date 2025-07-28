FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy pyproject.toml first for better Docker layer caching
COPY workflow_agent/pyproject.toml .

# Install Python dependencies using uv
RUN uv pip install --system -e .

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application code
COPY workflow_agent/ .
COPY shared/ ./shared/

# Create the prompts directory where the prompt engine expects it
RUN mkdir -p /shared/prompts && cp -r ./shared/prompts/* /shared/prompts/

# Create proto directory and generate protobuf files
RUN mkdir -p proto && \
    python -m grpc_tools.protoc \
    --python_out=proto \
    --grpc_python_out=proto \
    --proto_path=shared/proto \
    shared/proto/workflow_agent.proto || echo "Proto generation failed, continuing anyway"

# Fix protobuf imports
RUN find proto -name "*_pb2_grpc.py" -exec sed -i 's/^import \([a-zA-Z_][a-zA-Z0-9_]*_pb2\) as /from . import \1 as /g' {} \; || true

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose the gRPC port
EXPOSE 50051

# Run the application
CMD ["python", "main.py"]
