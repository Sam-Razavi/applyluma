#!/bin/bash
set -e

echo "=== Running Airflow Integrity Tests ==="
pytest airflow/tests/test_dag_integrity.py

echo "=== Running Airflow Logic Unit Tests ==="
pytest airflow/tests/test_dag_logic.py

echo "=== Running dbt Parse and Compile (Dry Run) ==="
cd dbt
dbt parse --profiles-dir .
dbt compile --profiles-dir .

echo "=== Data Pipeline Tests Completed Successfully ==="
