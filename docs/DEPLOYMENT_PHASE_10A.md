# Deployment Guide: Phase 10A

## Prerequisites

- Railway project with PostgreSQL and Redis services
- Vercel project linked to the repository
- `main` branch triggers automatic deploys on both platforms

## Database Migration

Phase 10A adds three new tables. The migration `0008_phase_10a_tables.py` must run before the new code is live.

**Run locally against Railway (requires public proxy URL):**

```bash
# Set the public Railway DATABASE_URL in .env:
# DATABASE_URL=postgresql://postgres:<password>@viaduct.proxy.rlwy.net:<port>/railway

cd backend
python -m alembic upgrade head
```

**Verify:**

```bash
python -m alembic current
# → 0008 (head)
```

**Tables to confirm:**

```sql
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('saved_jobs', 'extracted_keywords', 'job_matching_scores');
```

## Backend Deployment (Railway)

1. Merge feature branch → `dev` and test
2. `git checkout main && git merge dev`
3. `git push origin main`
4. Railway auto-deploys in ~3 minutes
5. Check Railway logs for startup errors

Railway environment variables required (already set):
- `DATABASE_URL` — internal Railway postgres URL
- `REDIS_URL` — internal Railway redis URL
- `OPENAI_API_KEY`
- `SECRET_KEY`

## Frontend Deployment (Vercel)

Vercel auto-deploys on push to `main`. No manual steps needed.

Verify the new routes are reachable after deploy:
- `/discover` — job discovery feed
- `/saved-jobs` — saved jobs collection

## Post-Deploy Verification

1. Log in as a test user
2. Navigate to `/discover` — jobs should load (empty if no scraping has run yet)
3. Click the bookmark icon on a job — it should save and the icon should fill
4. Navigate to `/saved-jobs` — the saved job should appear
5. Star and delete the saved job — both should work

## Rollback

If something goes wrong:

```bash
cd backend
python -m alembic downgrade 0007
```

This drops `saved_jobs`, `extracted_keywords`, and `job_matching_scores`. Data in those tables will be lost.
