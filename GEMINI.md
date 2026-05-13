# ApplyLuma - Project Instructions

This file serves as the foundational guidance for Gemini CLI when working in the ApplyLuma codebase. It complements the existing `CLAUDE.md` and provides additional context for AI-driven development.

## Project Vision
ApplyLuma is an AI-powered job search and resume optimization platform. It helps users manage their resumes, analyze them against market data, and tailor them for specific job descriptions using LLMs.

## Core Tech Stack

### Backend (`/backend`)
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL with SQLAlchemy 2.0 (Async/Sync)
- **Migrations:** Alembic
- **Task Queue:** Celery with Redis for asynchronous CV tailoring.
- **AI Integration:** OpenAI API for resume analysis and tailoring.
- **External API:** Adzuna for job search data.
- **PDF Generation:** ReportLab.
- **Validation:** Pydantic v2.

### Frontend (`/frontend`)
- **Framework:** React 18 with Vite and TypeScript.
- **Styling:** Tailwind CSS.
- **State Management:** Zustand.
- **Data Fetching:** Axios.
- **Charts:** Recharts for the analytics dashboard.
- **Forms:** React Hook Form + Zod.

### Data Engineering (`/airflow`, `/dbt`)
- **Orchestration:** Apache Airflow.
- **Transformation:** dbt (data build tool) for PostgreSQL.
- **Pipeline:** Daily ETL from job sources to analytics models.

## Infrastructure & Deployment
- **Backend/Worker/DB/Cache:** Railway.
- **Frontend:** Vercel.
- **CI/CD:** GitHub Actions (implied) / Auto-deploy from `main`.
- **Local Dev:** `docker-compose` orchestrates Postgres, Redis, Backend, Worker, Frontend, and Airflow.

## Project Structure & Conventions

### Backend
- `app/api/v1/`: Versioned API endpoints.
- `app/crud/`: Database abstraction layer.
- `app/models/`: SQLAlchemy models.
- `app/schemas/`: Pydantic models for validation and serialization.
- `app/services/`: Business logic (AI, PDF, parsing).
- `app/tasks/`: Celery task definitions.

### Frontend
- `src/components/`: Reusable UI components.
- `src/pages/`: Page-level components.
- `src/stores/` or `src/store/`: Zustand state definitions.
- `src/api/`: API client and hooks.
- `src/types/`: TypeScript interfaces and types.

## Development Workflow

1.  **Branching:** Always work in `dev` or a feature branch branched from `dev`. Never push directly to `main`.
2.  **Environment:** Use `.env` files for local configuration (see `.env.example`).
3.  **Local Services:** Run `docker-compose up` to start the full stack.
4.  **Testing:**
    - Backend: `pytest` in `backend/tests`.
    - Frontend: `npm run lint` and `npm run type-check`.
5.  **Database:** Use `alembic revision --autogenerate` for new migrations and `alembic upgrade head` to apply.

## Specialized Guidance

### AI CV Tailoring
The tailoring process is asynchronous. 
1.  User submits a tailoring request.
2.  FastAPI creates a `tailor_job` record and triggers a Celery task.
3.  Celery task calls OpenAI to rewrite sections.
4.  User reviews diffs via the frontend and confirms changes.
5.  ReportLab generates the final PDF.

### Analytics Pipeline
Airflow scrapes jobs and triggers dbt. dbt transforms raw data into analytics-ready tables. The FastAPI `analytics` endpoints read from these transformed tables.

### Knowledge Graph
The project uses `graphify` for codebase mapping.
- Location: `graphify-out/`
- Recommendation: Consult `graphify-out/GRAPH_REPORT.md` for architectural insights.

## Rules for Gemini CLI
- **Prioritize Idiomatic Code:** Follow the existing patterns in the `crud`, `services`, and `schemas` folders.
- **Type Safety:** Maintain strict TypeScript typing in the frontend and Pydantic validation in the backend.
- **Surgical Updates:** Use `replace` for targeted edits.
- **Validation:** Always verify changes by running relevant tests or checking for lint/type errors.
- **Documentation:** Keep this `GEMINI.md` and `CLAUDE.md` updated with significant architectural changes.
