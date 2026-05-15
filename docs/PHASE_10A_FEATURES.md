# Phase 10A: Swedish Job Discovery & AI-Powered Job Matching

## Overview

Phase 10A adds a full job discovery pipeline to ApplyLuma, including Swedish job scraping, AI-powered CV-to-job matching, keyword extraction, and a saved-jobs collection.

## Features

### 1. Job Discovery Feed (`/discover`)

- Paginated feed of Swedish job postings from Platsbanken, Jobbsafari, and Indeed.se
- Filter by location, salary range, keywords, source, and minimum match score
- Sort by best match, highest salary, or most recent
- Filters collapse on mobile (tap "Filters" to expand)

### 2. AI Match Scoring

Every job is scored against the authenticated user's CV:

| Score dimension | Weight |
|---|---|
| Skills match | 40% |
| Experience match | 25% |
| Salary match | 15% |
| Education match | 10% |
| Location match | 10% |

Scores are cached in Redis for 24 hours and invalidated automatically when the user updates their CV.

### 3. Keyword Extraction

Job descriptions are parsed for:
- Technical skills (Python, SQL, …)
- Frameworks (React, FastAPI, …)
- Tools (Docker, Kubernetes, …)
- Soft skills
- Languages
- Certifications

Keywords are stored in `extracted_keywords` with confidence scores and cached for 7 days.

### 4. Saved Jobs (`/saved-jobs`)

- Save any discovered job with one click (bookmark icon on job card)
- Organise saved jobs into named collections (list_name field)
- Star important jobs
- Add personal notes
- Collection tabs filter the view
- Delete individual saved jobs

### 5. Job Detail Modal

Click any job card to open a detail modal showing:
- Full job description
- Match score breakdown
- Matched skills (green) and missing skills (red)
- Direct "Apply now" link

## Database Tables

| Table | Purpose |
|---|---|
| `raw_job_postings` | Source job data scraped by Airflow |
| `saved_jobs` | User's saved job collection |
| `extracted_keywords` | Keywords parsed from job descriptions |
| `job_matching_scores` | Cached CV-to-job match scores |

Migration: `backend/alembic/versions/0008_phase_10a_tables.py`

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/jobs` | List jobs with filters |
| GET | `/api/v1/jobs/{id}` | Job detail with full description |
| GET | `/api/v1/jobs/{id}/keywords` | Keywords grouped by type |
| POST | `/api/v1/saved-jobs` | Save a job |
| GET | `/api/v1/saved-jobs` | List saved jobs |
| PATCH | `/api/v1/saved-jobs/{id}` | Update (star, notes, list_name) |
| DELETE | `/api/v1/saved-jobs/{id}` | Remove saved job |

## Data Pipeline

Airflow scrapes Swedish job boards daily at 02:00 UTC. After scraping:
1. Raw postings land in `raw_job_postings`
2. Match scores are computed on demand (cached per user)
3. Keywords are extracted on demand (cached per posting)
