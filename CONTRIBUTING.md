# Contributing to ApplyLuma

## Development Workflow

### Branch Strategy
- `main` - Production code (protected)
- `dev` - Development code where all work happens
- `feature/*` - Feature branches created from `dev`

### Making Changes

1. **Start from dev branch**

```bash
git checkout dev
git pull origin dev
```

2. **Create feature branch**

```bash
git checkout -b feature/your-feature-name
```

3. **Make changes and commit**

```bash
git add .
git commit -m "feat: description of your changes"
```

4. **Push to GitHub**

```bash
git push origin feature/your-feature-name
```

5. **Merge to dev after local testing**

```bash
git checkout dev
git merge feature/your-feature-name
git push origin dev
```

6. **Deploy to production when ready**

```bash
git checkout main
git merge dev
git push origin main
```

Railway and Vercel auto-deploy from `main`.

### Commit Message Convention
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes such as formatting
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

### Local Development

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

**Airflow:**

```bash
docker-compose up airflow-webserver airflow-scheduler
```

### Before Merging to Main
- [ ] All tests pass locally
- [ ] No console errors
- [ ] Code follows project style
- [ ] Environment variables documented
- [ ] README updated if needed

## Questions?
Open an issue on GitHub or contact Sam Razavi.

