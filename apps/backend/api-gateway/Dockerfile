# Production Dockerfile for Three-Layer API Gateway with uv
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy workspace files from parent directory (context should be apps/backend)
COPY pyproject.toml ./
COPY uv.lock ./
COPY api-gateway/pyproject.toml ./api-gateway/
COPY api-gateway/.python-version* ./api-gateway/

# Install Python dependencies with uv
RUN uv sync --frozen --package api-gateway-mvp

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies including Redis client tools
RUN apt-get update && apt-get install -y \
    curl \
    redis-tools \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy uv and dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY api-gateway/ ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app
USER app

# Set environment variables for three-layer architecture
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# API Gateway specific environment
ENV APP_NAME="API Gateway"
ENV VERSION="1.0.0"
ENV ENVIRONMENT="production"
ENV HOST="0.0.0.0"
ENV PORT="8000"
ENV DEBUG="false"
ENV LOG_LEVEL="INFO"
ENV LOG_FORMAT="json"

# Authentication settings
ENV SUPABASE_AUTH_ENABLED="true"
ENV MCP_API_KEY_REQUIRED="true"

# Rate limiting settings
ENV PUBLIC_RATE_LIMIT_ENABLED="true"

ENV UV_HTTP_TIMEOUT=120

# Expose port
EXPOSE 8000

# Enhanced health check for three-layer architecture
# Uses versioned health endpoint and includes Redis connectivity check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/public/health || curl -f http://localhost:8000/health || exit 1

# Run application with production settings
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--access-log"]
