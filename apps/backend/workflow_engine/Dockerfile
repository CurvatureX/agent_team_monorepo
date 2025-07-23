# ---- 构建阶段 ----
FROM python:3.10-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential

COPY workflow_engine/pyproject.toml ./
COPY workflow_engine/requirements.txt ./

RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY shared /app/shared
COPY workflow_engine /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SHARED_PROTO_DIR=/app/shared/proto/engine

EXPOSE 8000

CMD ["bash", "start_server.sh", "start"] 