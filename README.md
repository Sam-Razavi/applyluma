# ApplyLuma 🌟

AI-powered job search platform with intelligent CV tailoring and data-driven insights.

## Overview

ApplyLuma helps job seekers optimize their applications through:
- AI-powered CV tailoring matched to job descriptions
- Automated cover letter generation
- Application tracking and analytics
- Market insights and skills gap analysis

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database + data warehouse
- **Redis** - Caching and task queue
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **Celery** - Async task processing

### Frontend
- **React 18** with TypeScript
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **React Router** - Navigation
- **React Query** - Server state

### Data Engineering
- **Apache Airflow** - Workflow orchestration
- **dbt** - Data transformations
- **Pandas** - Data processing

### AI/ML
- **Claude API** (Anthropic) - CV tailoring and analysis
- **spaCy** - NLP and keyword extraction

## Local Development

### Prerequisites
- Docker Desktop
- Node.js 18+
- Python 3.11+
- Git

### Quick Start

```bash
# Clone repository
git clone <your-repo>
cd applyluma

# Start all services with Docker
docker-compose up

# Services will be available at:
# - Backend API: http://localhost:8000
# - Frontend: http://localhost:5173
# - API Docs: http://localhost:8000/docs
# - Airflow: http://localhost:8080
```

### Manual Setup (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

applyluma/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── core/           # Config, security
│   │   └── db/             # Database connection
│   ├── tests/
│   └── alembic/            # Migrations
├── frontend/               # React application
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       ├── services/       # API calls
│       └── store/          # Zustand stores
├── airflow/                # Data engineering
│   └── dags/
├── dbt/                    # Data transformations
│   └── models/
└── docker/                 # Docker configs

## Features

### MVP (Phase 1)
- [x] User authentication (JWT)
- [x] CV upload and parsing
- [x] Job description input (URL or text)
- [x] AI-powered CV tailoring
- [x] Cover letter generation
- [x] Application tracking
- [x] Basic dashboard

### Phase 2 (Data Engineering)
- [ ] Automated job scraping (Airflow)
- [ ] Data warehouse (star schema)
- [ ] dbt transformations
- [ ] Advanced analytics dashboard
- [ ] Skills gap analysis
- [ ] Market trends

## Contributing

This is a portfolio project by Sam Razavi. Feedback welcome!

## License

MIT