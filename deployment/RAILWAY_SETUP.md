# Railway Backend Deployment Guide

## Prerequisites
- Railway account created
- GitHub repo connected to Railway
- Production secrets available outside Git

## Step 1: Create New Railway Project
1. Go to railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose: `Sam-Razavi/applyluma`
5. Select the `main` branch
6. Set root directory to `/backend`

## Step 2: Add PostgreSQL Database
1. In the Railway project, click "New Service"
2. Select "Database" -> "PostgreSQL"
3. Railway auto-creates the database
4. Copy the connection string from the "Connect" tab
5. Format: `postgresql://user:pass@host:port/railway`

## Step 3: Add Redis
1. Click "New Service" again
2. Select "Database" -> "Redis"
3. Railway auto-creates the Redis instance
4. Copy the connection string: `redis://host:port`

## Step 4: Configure Environment Variables
In Railway backend service -> Variables tab, add:

```bash
DATABASE_URL=<from Step 2>
REDIS_URL=<from Step 3>
ADZUNA_APP_ID=<your_adzuna_app_id>
ADZUNA_APP_KEY=<your_adzuna_app_key>
OPENAI_API_KEY=<your_openai_api_key>
SECRET_KEY=<generate_a_secure_random_value>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=production
RATE_LIMIT_PER_MINUTE=60
BACKEND_CORS_ORIGINS=["https://applyluma.com","https://www.applyluma.com"]
```

Do not commit real API keys or secrets. Keep them only in Railway's encrypted variables.

## Step 5: Deploy
1. Railway auto-deploys on git push to `main`
2. Check deployment logs in the Railway dashboard
3. Wait for "Build successful"
4. Copy your backend URL, for example `https://applyluma-production.up.railway.app`

## Step 6: Run Database Migrations
In Railway backend service -> Terminal:

```bash
alembic upgrade head
```

If Railway runs the `release` process from `Procfile`, this may already run automatically.

## Step 7: Test Backend
Visit:

```text
https://your-backend-url.up.railway.app/health
```

Expected response:

```json
{"status":"healthy","version":"0.1.0"}
```

API docs:

```text
https://your-backend-url.up.railway.app/docs
```

## Troubleshooting
- If build fails: check logs in Railway dashboard
- If migrations fail: verify `DATABASE_URL` is correct
- If health check fails: check app logs and Railway service status
- If frontend requests fail: verify `BACKEND_CORS_ORIGINS` includes the Vercel/custom frontend domains

