#!/bin/sh
set -e

celery -A app.tasks.celery_app worker --loglevel="${CELERY_LOG_LEVEL:-info}"
