# ---- 构建阶段 ----
FROM python:3.10-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y build-essential

# 拷贝依赖文件
COPY pyproject.toml ./
COPY requirements.txt ./

# 安装依赖到临时目录
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.10-slim

WORKDIR /app

# 拷贝依赖
COPY --from=builder /install /usr/local

# 拷贝代码
COPY . .

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 端口（如有需要可调整）
EXPOSE 8000

# 启动命令（如有 start_server.sh 可替换）
CMD ["python", "main.py"]
