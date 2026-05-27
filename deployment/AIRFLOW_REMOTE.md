# Connect Airflow to Railway Production Database

## Overview
Your always-on PC will run Airflow locally, but connect to the Railway PostgreSQL database to populate production analytics data.

## Prerequisites
- Railway PostgreSQL deployed
- Airflow running locally on your always-on PC
- Railway backend URL from `RAILWAY_SETUP.md`

## Step 1: Get Railway PostgreSQL Connection String
1. In Railway dashboard -> PostgreSQL service
2. Click the "Connect" tab
3. Copy "Postgres Connection URL"
4. Format: `postgresql://user:password@host.railway.app:5432/railway`

## Step 2: Update Airflow Connection on Your PC
On your always-on PC, edit the Airflow connection.

### Option A: Via Airflow UI
1. Open `http://localhost:8080`
2. Admin -> Connections -> Edit `postgres_default`
3. Update:
   - Host: Railway host from the connection string
   - Database: `railway`
   - User: value from the connection string
   - Password: value from the connection string
   - Port: `5432`
4. Save

### Option B: Via Environment Variable
In your Airflow `docker-compose.yml` or `.env`:

```yaml
AIRFLOW_CONN_POSTGRES_DEFAULT=postgresql://user:password@railway-host:5432/railway
```

## Step 3: Update DAG Configuration
Confirm DAGs use the production database connection, either through `postgres_default` or the `DATABASE_URL` environment variable.

## Step 4: Test Connection
In Airflow UI:
1. Go to Admin -> Connections
2. Click "Test" on `postgres_default`
3. Confirm "Connection successfully tested"

## Step 5: Manual Test Scrape
1. In Airflow UI -> DAGs
2. Find the `scrape_jobs` DAG
3. Click "Trigger DAG"
4. Monitor execution in Graph view
5. Check logs for errors

## Step 6: Verify Data in Production
1. Go to Railway -> PostgreSQL -> Data tab
2. Query:

```sql
SELECT COUNT(*) FROM raw_job_postings;
```

You should see newly scraped jobs.

## Step 7: Enable Daily Schedule
In `airflow/dags/scrape_jobs.py`, confirm schedule is:

```python
schedule_interval = "0 2 * * *"  # 2 AM UTC daily
```

If the DAG uses the newer Airflow `schedule` argument, use the same cron value there.

## Step 8: Test Analytics Pipeline
1. Trigger `transform_jobs` DAG manually
2. Verify dbt models run successfully
3. Check `analytics.fct_job_postings` table is populated
4. Visit `https://applyluma.com/analytics`
5. Dashboard should show real data

## Troubleshooting
- Connection fails: verify Railway PostgreSQL is running and public networking is enabled
- Permission denied: check the Railway database user has write access
- DAG fails: check Airflow logs for the specific task error
- No data in analytics: verify dbt models ran after scraping

