FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.lock ./backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock && useradd -u 10001 -m library && mkdir -p /data/covers /data/ebooks && chown -R library:library /data
COPY backend/app backend/app
COPY backend/migrations backend/migrations
COPY devops/scripts devops/scripts
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
