#!/usr/bin/env bash
set -Eeuo pipefail

echo "Verifying Railway PostgreSQL connection..."

if [ ! -f .env.railway ]; then
  echo "ERROR: .env.railway file not found."
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env.railway
set +a

POSTGRES_CONTAINER="$(docker ps -q -f name=postgres | head -n 1)"

if [ -z "${POSTGRES_CONTAINER}" ]; then
  echo "ERROR: No running postgres container found."
  echo "Start local Docker services first, then retry."
  exit 1
fi

echo "Testing connection to Railway PostgreSQL..."

docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD}" "${POSTGRES_CONTAINER}" psql \
  -h "${DBT_DB_HOST}" \
  -p "${DBT_DB_PORT}" \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -c "SELECT version();" \
  -c "SELECT current_database(), current_schema();" \
  -c "SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'public';"

echo "Connection successful."
echo
echo "Checking for analytics schema..."

docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD}" "${POSTGRES_CONTAINER}" psql \
  -h "${DBT_DB_HOST}" \
  -p "${DBT_DB_PORT}" \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'analytics';"

echo
echo "Checking raw_job_postings table..."

docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD}" "${POSTGRES_CONTAINER}" psql \
  -h "${DBT_DB_HOST}" \
  -p "${DBT_DB_PORT}" \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -c "SELECT COUNT(*) AS job_count FROM raw_job_postings;"
