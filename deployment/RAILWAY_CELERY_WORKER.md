# Railway Celery Worker

Phase 9 CV tailoring requires a long-running Celery worker in addition to the FastAPI web service.

## Required Railway Services

- Web service: uses `backend/railway.json` and starts `sh scripts/start-web.sh`
- Worker service: same repo and backend root, uses `backend/railway.worker.json` or start command `sh scripts/start-worker.sh`
- Redis: must be available through `REDIS_URL`
- PostgreSQL: must be available through `DATABASE_URL`

## Worker Start Command

```bash
sh scripts/start-worker.sh
```

Equivalent direct command:

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

The worker must use the same environment variables as the backend web service, especially `DATABASE_URL`, `REDIS_URL`, and `OPENAI_API_KEY`.
