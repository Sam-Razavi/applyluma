# Stage 1 — install runtime deps only
FROM python:3.11-slim AS builder
WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN pip install --upgrade pip
COPY pyproject.toml .
COPY app/ ./app/
RUN pip install --no-cache-dir .

# Stage 2 — lean runtime image
FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/ scripts/
RUN adduser --disabled-password --gecos "" appuser \
 && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c \
    "import urllib.request,os; urllib.request.urlopen( \
     f'http://localhost:{os.getenv(\"PORT\",\"8080\")}/api/v1/health')"
CMD ["sh", "scripts/start-web.sh"]
