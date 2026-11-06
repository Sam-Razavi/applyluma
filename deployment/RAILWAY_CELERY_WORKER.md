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

## Embedded beat (optional, saves a service)

Set `CELERY_EMBED_BEAT=1` on the worker service and `start-worker.sh` runs
`celery worker -B`, scheduling beat tasks from inside the worker. Then delete
the separate `applyluma-celery-beat` service **at the same time**: while both
run, every scheduled task fires twice. Only valid with exactly one worker
replica, since each replica would start its own scheduler.
