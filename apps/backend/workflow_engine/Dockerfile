# Dockerfile for workflow_engine using FastAPI

# Use an official Python runtime as a parent image
FROM python:3.11-slim AS base

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY ./workflow_engine/requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./workflow_engine/workflow_engine /app/workflow_engine
COPY ./shared /app/shared

# Production stage
FROM base AS production

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port 8002 to the outside world
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8002/health || exit 1

# Command to run the application using uvicorn
CMD ["uvicorn", "workflow_engine.main:app", "--host", "0.0.0.0", "--port", "8002"]
