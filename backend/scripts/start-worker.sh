#!/bin/sh
set -e

# CELERY_EMBED_BEAT=1 runs the beat scheduler inside this worker (-B), so the
# separate applyluma-celery-beat service can be deleted (~110 MB RAM saved).
# Only ever with ONE worker replica: each replica would start its own
# scheduler and every scheduled task would fire once per replica. Set this
# variable and delete the beat service at the same time, or tasks double up.
if [ "${CELERY_EMBED_BEAT:-0}" = "1" ]; then
  exec celery -A app.tasks.celery_app worker -B \
    --schedule /tmp/celerybeat-schedule \
    --pool=solo --loglevel=info -Q celery,ai_pipeline
fi

exec celery -A app.tasks.celery_app worker --pool=solo --loglevel=info -Q celery,ai_pipeline
