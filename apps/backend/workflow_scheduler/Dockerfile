# Use full python:3.11 image - no apt-get needed
FROM python:3.11 AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# All build tools already available in python:3.11

# Create working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY ./workflow_scheduler/pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir .

# Production stage - use full python:3.11 to avoid apt-get issues
FROM python:3.11 AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/app/.local/bin:$PATH"

# No runtime dependencies needed - python:3.11 has curl built-in

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (forced rebuild v7 - URL-level pgbouncer fix)
COPY ./workflow_scheduler/ ./workflow_scheduler/
COPY ./shared/ ./shared/

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
