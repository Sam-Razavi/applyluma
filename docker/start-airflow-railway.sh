#!/usr/bin/env bash
set -Eeuo pipefail

echo "Starting Airflow with Railway PostgreSQL connection..."

if [ ! -f .env.railway ]; then
  echo "ERROR: .env.railway file not found."
  echo "Create it in the project root with Railway PostgreSQL credentials."
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env.railway
set +a

required_vars=(
  "AIRFLOW_POSTGRES_CONN_HOST"
  "AIRFLOW_POSTGRES_CONN_PORT"
  "AIRFLOW_POSTGRES_CONN_LOGIN"
  "AIRFLOW_POSTGRES_CONN_PASSWORD"
  "AIRFLOW_POSTGRES_CONN_SCHEMA"
  "DBT_DB_HOST"
  "DBT_DB_PORT"
  "POSTGRES_USER"
  "POSTGRES_PASSWORD"
  "POSTGRES_DB"
)

for var in "${required_vars[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "ERROR: ${var} is not set in .env.railway"
    exit 1
  fi
done

echo "All required environment variables are set."
echo
echo "Database connections:"
echo "  Airflow metadata DB: ${AIRFLOW_METADATA_USER:-applyluma}@postgres:5432/${AIRFLOW_METADATA_DB:-airflow_db} (local)"
echo "  postgres_default:    ${AIRFLOW_POSTGRES_CONN_LOGIN}@${AIRFLOW_POSTGRES_CONN_HOST}:${AIRFLOW_POSTGRES_CONN_PORT}/${AIRFLOW_POSTGRES_CONN_SCHEMA} (Railway)"
echo "  dbt prod target:     ${POSTGRES_USER}@${DBT_DB_HOST}:${DBT_DB_PORT}/${POSTGRES_DB} (Railway)"
echo
echo "Connection details:"
echo "  Airflow postgres_default -> ${AIRFLOW_POSTGRES_CONN_HOST}:${AIRFLOW_POSTGRES_CONN_PORT}/${AIRFLOW_POSTGRES_CONN_SCHEMA}"
echo "  dbt prod target          -> ${DBT_DB_HOST}:${DBT_DB_PORT}/${POSTGRES_DB}"
echo

docker-compose --env-file .env.railway up -d

echo
echo "Airflow started with Railway connection."
echo "  Airflow UI: http://localhost:8080"
echo "  Username: admin"
echo "  Password: admin"
