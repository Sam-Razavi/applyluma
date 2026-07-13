#!/bin/sh
set -e

# Optional dedicated worker for the AI generation queue (CV tailoring, cover
# letters). Deploying this as a second Railway service, alongside the
# default worker (start-worker.sh), gives user-facing generation requests
# their own --pool=solo slot instead of queueing behind batch matching jobs
# or beat-scheduled notification runs. Not required: start-worker.sh alone
# still processes the ai_pipeline queue if this service isn't deployed.
celery -A app.tasks.celery_app worker --pool=solo --loglevel=info -Q ai_pipeline --hostname=ai-worker@%h
