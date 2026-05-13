#!/bin/sh
set -e

celery -A app.tasks.celery_app worker --pool=solo --loglevel=info
