# Dockerfile for Workflow Engine
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml ./

# 安装 Python 依赖，包括新增的 psycopg2-binary
RUN pip install --no-cache-dir -e .

# 复制源代码
COPY workflow_engine/ ./workflow_engine/
COPY scripts/ ./scripts/
COPY database/ ./database/

# 复制共享的 proto 文件
COPY ../shared/proto/ ./shared/proto/

# 生成 protobuf 文件
RUN python scripts/generate_proto.py

# 设置环境变量
ENV PYTHONPATH=/app
ENV CREDENTIAL_ENCRYPTION_KEY=${CREDENTIAL_ENCRYPTION_KEY}
ENV DATABASE_URL=${DATABASE_URL}
ENV REDIS_URL=${REDIS_URL}
ENV GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
ENV GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
ENV GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID}
ENV GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET}
ENV SLACK_CLIENT_ID=${SLACK_CLIENT_ID}
ENV SLACK_CLIENT_SECRET=${SLACK_CLIENT_SECRET}

# 暴露端口（如果需要作为独立服务运行）
EXPOSE 50052

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import workflow_engine; print('OK')" || exit 1

# 启动命令（可以根据实际需要调整）
CMD ["python", "-m", "workflow_engine.main"] 