#!/usr/bin/env bash
set -Eeuo pipefail

CONN_ID="${AIRFLOW_POSTGRES_CONN_ID:-postgres_default}"
CONN_TYPE="${AIRFLOW_POSTGRES_CONN_TYPE:-postgres}"
CONN_HOST="${AIRFLOW_POSTGRES_CONN_HOST:-postgres}"
CONN_PORT="${AIRFLOW_POSTGRES_CONN_PORT:-5432}"
CONN_SCHEMA="${AIRFLOW_POSTGRES_CONN_SCHEMA:-applyluma}"
CONN_LOGIN="${AIRFLOW_POSTGRES_CONN_LOGIN:-applyluma}"
CONN_PASSWORD="${AIRFLOW_POSTGRES_CONN_PASSWORD:-applyluma}"

echo "Checking Airflow connection '${CONN_ID}'..."

if airflow connections get "${CONN_ID}" >/dev/null 2>&1; then
  echo "Airflow connection '${CONN_ID}' already exists. Skipping creation."
  exit 0
fi

echo "Creating Airflow connection '${CONN_ID}'..."

if airflow connections add "${CONN_ID}" \
  --conn-type "${CONN_TYPE}" \
  --conn-host "${CONN_HOST}" \
  --conn-port "${CONN_PORT}" \
  --conn-schema "${CONN_SCHEMA}" \
  --conn-login "${CONN_LOGIN}" \
  --conn-password "${CONN_PASSWORD}"; then
  echo "Airflow connection '${CONN_ID}' created successfully."
  exit 0
fi

# If another init process created it between the get and add commands, treat that
# as success. Any other failure should still fail the init service.
if airflow connections get "${CONN_ID}" >/dev/null 2>&1; then
  echo "Airflow connection '${CONN_ID}' now exists. Continuing."
  exit 0
fi

echo "Failed to create Airflow connection '${CONN_ID}'." >&2
exit 1
