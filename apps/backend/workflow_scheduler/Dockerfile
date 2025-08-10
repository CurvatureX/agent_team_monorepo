# Multi-stage build for workflow_scheduler
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements and install dependencies
<<<<<<< HEAD
COPY workflow_scheduler/pyproject.toml ./
=======
COPY ./workflow_scheduler/pyproject.toml ./
>>>>>>> c9adfde4c8f458194672917215abd65d75986286
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir .

# Production stage
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/app/.local/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
<<<<<<< HEAD
COPY workflow_scheduler/ ./workflow_scheduler/
COPY shared/ ./shared/
=======
COPY ./workflow_scheduler/ ./workflow_scheduler/
COPY ./shared/ ./shared/
>>>>>>> c9adfde4c8f458194672917215abd65d75986286

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose port
EXPOSE 8003

# Set Python path to include shared modules
ENV PYTHONPATH=/app:$PYTHONPATH

# Start application
CMD ["python", "-m", "workflow_scheduler.main"]
