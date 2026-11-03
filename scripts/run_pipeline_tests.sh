#!/bin/bash
set -e

echo "=== Running dbt Parse ==="
cd dbt
dbt deps --profiles-dir .
dbt parse --profiles-dir .

echo "=== Data Pipeline Tests Completed Successfully ==="
