# 后端镜像：python:3.12-slim 官方镜像 + 我们的代码
# 企业要点：用 slim 基础镜像减小体积；非 root 用户运行（容器被攻破也拿不到 root）
FROM python:3.12-slim

WORKDIR /app

# 先复制依赖清单：这一层被缓存后，代码改动不会触发重装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 数据库(/app/data，挂载卷) 和日志(/app/logs) 目录：提前建好并赋权给运行用户
RUN useradd -m appuser && mkdir -p /app/data /app/logs && chown -R appuser /app/data /app/logs
COPY --chown=appuser app ./app

USER appuser

# 容器里日志必须不缓冲：否则 docker logs 看不到实时输出
ENV PYTHONUNBUFFERED=1

EXPOSE 8010
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
