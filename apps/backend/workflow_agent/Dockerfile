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

# FastAPI 不需要 protobuf 生成

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FASTAPI_PORT=8001

# Expose the FastAPI port (替换 gRPC 端口)
EXPOSE 8001

# Health check for FastAPI service
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the FastAPI application (替换 gRPC 服务器)
CMD ["python", "main.py"]
