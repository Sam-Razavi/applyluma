# ApplyLuma before the thesis work

This document records what ApplyLuma was before any work for the bachelor thesis
"Designing and Evaluating an AI-Assisted Decision Support System" (Stockholm
University, DSV, IB015N) was added to the repository.

## How the baseline is marked

- The git tag **`pre-thesis-baseline`** points at the last commit before the thesis
  work. Everything in the repository at that tag existed before the thesis.
- Written on 2026-11-12. The tag, not this date, is the exact boundary.
- Thesis work is added after the tag, in its own folders, in pull requests whose
  titles start with `[thesis]`.

To see everything added since the baseline:

```bash
git diff --stat pre-thesis-baseline..HEAD
git log --oneline pre-thesis-baseline..HEAD
```

## What existed at the baseline

A deployed job-search platform (https://applyluma.com): FastAPI and PostgreSQL
backend, React frontend, Celery workers, hosted on Railway and Vercel.

| Area | What it does |
|---|---|
| Accounts | Email and password, Google sign-in, magic-link sign-in, password reset, account deletion |
| CVs | Upload (PDF, DOCX, Markdown), text extraction, version history, completeness score |
| Job data | Nightly pipeline: scrapes Platsbanken, RemoteOK, Remotive and The Muse; removes cross-source duplicates; extracts keywords; archives old ads |
| Discover | Filterable feed of live job ads with a match score per ad, a skill gap list, saved jobs |
| Rule-based matcher | The match score. Described in full below, because it is the baseline the thesis compares against |
| AI CV Tailor | Rewrites a CV for a job with GPT-4o, section by section, with checks against invented content; PDF templates |
| Cover letters | Generated with GPT-4o in three tones |
| Applications | Tracker with status history, timeline, analytics, CSV export |
| Email forwarding | Forwarded recruiter emails are matched to applications and classified by keyword rules |
| Analytics | Market dashboard built from the scraped ads |
| Browser extension | Saves jobs from LinkedIn, Indeed, Glassdoor and Arbetsförmedlingen |
| Admin | Users, AI costs, pipeline health, database, audit log, monitoring |
| Billing | Stripe checkout and customer portal |

Automated tests at the baseline: 904 backend tests (pytest, including tests on a
real PostgreSQL in CI) and 384 frontend tests (Vitest).

## Where AI was used at the baseline

| Feature | Model | Role |
|---|---|---|
| CV tailoring | GPT-4o | Generates text: a rewritten CV |
| Cover letters | GPT-4o | Generates text: a letter |
| Job ad import from a URL | GPT-4o-mini | Extracts title, company and description from a web page |

**No AI model took part in ranking, scoring or recommending jobs.** The match score
shown in Discover is computed by fixed rules, with no model call. Adding an AI
component to that decision is the thesis work.

## The rule-based matcher

Code: `backend/app/services/matching_service.py`, class `MatchingService`. It is not
changed after the baseline tag, so the comparison target stays fixed.

### Formula

```
score = 0.40 × skills + 0.30 × experience + 0.15 × salary + 0.10 × education + 0.05 × location
```

Each part is a number from 0 to 100. The result is rounded to one decimal.

### How each part is computed

**Skills (40%).** The job's skills are the keywords found in the ad text by a fixed
vocabulary (`job_scrapers/keyword_extraction.py`, about 46 terms; only technical
skills, frameworks, tools and certifications count, not soft skills or spoken
languages). The CV's skills are found by the larger vocabulary in
`keyword_extractor.py`. A job skill is matched when the same term is among the CV's
skills.

```
coverage = matched / required
evidence = min(matched / 5, 1)
skills   = coverage × (0.5 + 0.5 × evidence) × 100
```

So 5 of 5 scores 100, 1 of 1 scores 60, and 0 of any number scores 0. An ad in which
no skill from the vocabulary is found scores a fixed 30.

**Experience (30%).** Compares the years of experience found in the CV (the largest
"N years of experience" or "N år erfarenhet" phrase) with the years the job requires.
If the job states no requirement, the part is 100.

**Salary (15%).** A fixed 70 in every case.

**Education (10%).** If the job states a required level (bachelor, master, PhD), 100
when the CV mentions that level and 50 when it does not. If the job states no
requirement, 100.

**Location (5%).** 80 when the job allows remote work, 70 otherwise.

### What reaches the matcher in production

Every caller (`tasks/matching.py`, `MatchingService.batch_compute_scores`,
`endpoints/job_bookmark.py`) passes the ad's title, description, salary, location and
remote flag. None passes a required number of years or a required education level,
because the scraped ads do not carry those as structured fields.

The consequence is that only the skills part varies:

| Part | Value in production |
|---|---|
| Experience | always 100 |
| Salary | always 70 |
| Education | always 100 |
| Location | 70, or 80 for remote jobs |

```
score = 0.40 × skills + 54        (54.5 for remote jobs)
```

- Lowest possible score: **54** (the ad names skills, the CV has none of them).
- Highest possible score: **94** (94.5 for remote jobs).
- An ad with no recognised skills: **66**.

### Known simplifications

- Skills are matched as vocabulary terms. A skill the vocabulary does not contain is
  invisible, in the ad and in the CV.
- The matcher does not tell mandatory requirements from preferred ones.
- Experience, education and salary do not affect the score in production.
- Missing information and a clear mismatch are not distinguished.
- The explanation is one generated line, for example "You have 4/5 required skills
  (Python, SQL, Docker, Git matched; missing: Kubernetes)."

## Removed just before the baseline

An older endpoint, `POST /api/v1/ai/tailor-cv`, sent a CV and a job description to
GPT-4o-mini and returned strengths, gaps and suggested CV edits, with a simple
keyword-overlap percentage. It gave advice on improving a CV; it did not rank or
recommend jobs. No page in the app, and no version of the browser extension, called it,
and it had no tests. It was removed as unused code in the same change that added this
document. The code remains in the git history
(`backend/app/api/v1/endpoints/ai.py`, `backend/app/services/ai_service.py`).
