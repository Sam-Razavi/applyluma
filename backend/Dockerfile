FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --upgrade pip

COPY pyproject.toml .
RUN pip install -e ".[dev]"

COPY . .

EXPOSE 8080

CMD ["sh", "scripts/start-web.sh"]
