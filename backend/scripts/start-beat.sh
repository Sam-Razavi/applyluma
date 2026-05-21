#!/bin/sh
set -e

celery -A app.tasks.celery_app beat --loglevel=info --scheduler celery.beat.PersistentScheduler
