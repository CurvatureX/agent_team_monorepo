# Use python image with build tools already installed
FROM python:3.11 AS builder

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies (no need for gcc, it's already in python:3.11)
COPY workflow_engine/requirements.txt .
RUN pip install -r requirements.txt

# Production stage - use full python:3.11 to avoid apt-get
FROM python:3.11 AS production

# Set working directory
WORKDIR /app

# No runtime dependencies needed - python:3.11 has everything

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY workflow_engine/ .

# Copy shared models (for compatibility)
COPY shared/ ./shared

# Make startup script executable
RUN chmod +x startup.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port 8002 to the outside world
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD curl -f http://localhost:8002/health || exit 1

# Command to run the startup script which validates imports and then starts the application
CMD ["./startup.sh"]
