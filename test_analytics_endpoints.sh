#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://applyluma-production.up.railway.app/api/v1/analytics"

endpoints=(
  "job-market-health"
  "trending-skills"
  "salary-insights"
  "hiring-patterns"
  "company-insights"
  "skill-demand"
  "location-trends"
  "industry-breakdown"
  "experience-levels"
  "job-type-mix"
  "salary-by-skill"
)

failed=0

for endpoint in "${endpoints[@]}"; do
  echo "Testing /${endpoint}..."
  status=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/${endpoint}")
  if [ "${status}" = "200" ]; then
    echo "  OK ${status}"
  else
    echo "  FAILED ${status}"
    failed=1
  fi
done

exit "${failed}"
