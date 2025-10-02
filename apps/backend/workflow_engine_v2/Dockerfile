# Use python image for build/install
FROM python:3.11 AS builder

WORKDIR /app
COPY workflow_engine_v2/requirements.txt ./
RUN pip install -r requirements.txt

# Production image
FROM python:3.11 AS production
WORKDIR /app

# Copy site-packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code maintaining package structure
COPY workflow_engine_v2/ ./workflow_engine_v2/
# Copy shared models/specs used by v2
COPY shared/ ./shared

# Startup
RUN chmod +x workflow_engine_v2/startup.sh || true

# Non-root
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8002/health || exit 1

CMD ["./workflow_engine_v2/startup.sh"]
