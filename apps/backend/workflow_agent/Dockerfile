FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy pyproject.toml first for better Docker layer caching
COPY pyproject.toml .

# Install Python dependencies using uv
RUN uv pip install --system -e .

# Copy the application code
COPY . .

# Create proto directory and copy generated files
RUN mkdir -p proto

# Expose the gRPC port
EXPOSE 50051

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "-m", "main"]
