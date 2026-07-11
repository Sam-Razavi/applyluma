# Monitoring & Alerting

ApplyLuma has three independent layers of monitoring. They catch different
failure modes and none of them substitutes for the others.

| Layer | Catches | Where it runs |
|---|---|---|
| External uptime pinger (UptimeRobot) | The whole app being down/unreachable | Outside the app — the only layer that works when the app itself is dead |
| Internal health watchdog | Degraded dependencies (Redis, Celery, stalled scraping, AI job failure spikes) while the app is still up | Celery beat, every 15 minutes |
| Sentry | Unhandled exceptions in the running backend and frontend | In-process, on both `backend/` and `frontend/` |

A process that has crashed entirely can't email you about itself — that's
why the external pinger is the one layer that isn't pure code in this repo.

## 1. External uptime pinger (UptimeRobot)

Set this up once, outside of any deploy:

1. Create a free account at uptimerobot.com.
2. Add an HTTP(s) monitor:
   - URL: `https://applyluma-production.up.railway.app/health?deep=1`
   - Interval: 5 minutes
   - Alert condition: non-2xx response (the endpoint returns `503` when the
     database check fails; a total outage times out or connection-refuses,
     which also alerts)
3. Enable email and/or push notifications on the monitor.

`/health` (no query param) stays a fast, dependency-free liveness check —
that's what Railway's own health check probe should keep using, so a
transient DB blip doesn't cause Railway to restart the container. Only
`/health?deep=1` runs a real `SELECT 1` and can return `503`.

## 2. Internal health watchdog

`app/tasks/watchdog.py` (Celery task `run_health_watchdog`, scheduled via
`app/tasks/celery_app.py` beat entry `health-watchdog-every-15-min`) checks,
every 15 minutes:

- `db`, `redis`, `celery` — the same probes as `/api/v1/health/detailed`.
- `pipeline` — whether `raw_job_postings` scraping is fresh
  (`crud_admin.get_pipeline_health`).
- `ai_job_failures` — whether failed tailor/cover-letter jobs in the last
  hour meet or exceed `WATCHDOG_FAILURE_SPIKE_THRESHOLD` (default `5`,
  overridable via env var).

State is persisted in the `app_settings` table under the key
`health_watchdog_state` (`"ok"` or `"degraded:<comma-joined checks>"`), the
same throttling pattern used by the AI budget alert. An email to
`CONTACT_RECIPIENT_EMAIL` only fires on a *transition*:

- healthy → degraded: one alert email.
- degraded with an additional check now failing: one more alert email (the
  check list is part of the state, so this is detected as a new state).
- degraded → healthy: one recovery email.
- otherwise: silent, so a persistent known issue doesn't spam your inbox.

This layer requires Celery beat to be running (`backend/scripts/start-beat.sh`
/ `backend/railway.beat.json`) — if beat itself is down, this layer goes
silent too, which is exactly the gap the external pinger fills.

## 3. Sentry

- Backend: initialized in `backend/app/main.py`, gated on the `SENTRY_DSN`
  env var (`backend/app/core/config.py`). **Verify `SENTRY_DSN` is set in
  Railway** — if it's unset, backend exceptions are only visible in Railway
  logs.
- Frontend: initialized in `frontend/src/main.tsx`, gated on the
  `VITE_SENTRY_DSN` build-time env var. `ErrorBoundary.tsx` reports caught
  render errors via `Sentry.captureException`. **Verify `VITE_SENTRY_DSN` is
  set in Vercel.**

## Admin status banner

Every `/admin/*` page shows a red (unhealthy) or amber (degraded) banner
when `GET /api/v1/admin/system/health` reports anything other than `ok`,
polled every 60 seconds (`frontend/src/components/layout/AdminStatusBanner.tsx`,
mounted in `frontend/src/components/AdminRoute.tsx`). This is a convenience
for whoever has the admin panel open — it is not a substitute for the
external pinger or the email alerts above, since nobody has to be looking at
the page for those to fire.
