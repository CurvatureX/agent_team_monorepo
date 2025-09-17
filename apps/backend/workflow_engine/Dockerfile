# Simple, clean Dockerfile for Workflow Engine
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY workflow_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY workflow_engine/ .

# Copy shared models (for compatibility)
COPY shared/ ./shared

# Expose port 8002 to the outside world
EXPOSE 8002

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8002/health || exit 1

# Command to run the application using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
