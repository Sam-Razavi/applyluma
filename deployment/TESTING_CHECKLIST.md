# ApplyLuma Production Testing Checklist

Test these features end-to-end on `https://applyluma.com`.

## Backend Health Checks
- [ ] Backend health endpoint responds: `https://your-backend-url/health`
- [ ] API docs accessible: `https://your-backend-url/docs`
- [ ] CORS allows frontend domain
- [ ] Database connection successful
- [ ] Redis connection successful

## Frontend Loads
- [ ] Site loads at `https://applyluma.com`
- [ ] No console errors in browser DevTools
- [ ] CSS/images load correctly
- [ ] Mobile responsive on phone or DevTools
- [ ] SSL certificate valid

## Authentication
- [ ] Register new user account
- [ ] Receive JWT tokens
- [ ] Login with credentials
- [ ] Logout clears session
- [ ] Protected routes redirect to login

## Resume Management
- [ ] Upload `.pdf` resume
- [ ] Upload `.docx` resume
- [ ] View uploaded resume
- [ ] Set primary resume
- [ ] Delete resume
- [ ] Error handling for invalid files

## AI Resume Analysis
- [ ] Trigger AI analysis on uploaded resume
- [ ] Receive ATS score
- [ ] Get skill extraction
- [ ] Get keyword suggestions
- [ ] Analysis completes in less than 10 seconds
- [ ] OpenAI API key working

## Analytics Dashboard
- [ ] Navigate to `/analytics`
- [ ] All 12 charts load
- [ ] KPI cards show real data, not empty state
- [ ] Charts render correctly
- [ ] Tooltips work on hover
- [ ] Responsive on mobile
- [ ] No `undefined` or `NaN` values

## Job Search
- [ ] Search for jobs by keyword
- [ ] Filter by location
- [ ] Filter by salary
- [ ] Adzuna API returns results
- [ ] Save job to database

## Performance
- [ ] Page load time under 3 seconds
- [ ] API responses under 1 second for common routes
- [ ] No obvious memory leaks during long sessions
- [ ] Images optimized

## Security
- [ ] HTTPS enforced
- [ ] No mixed content warnings
- [ ] Environment variables not exposed in frontend
- [ ] SQL injection protection checked with test input `' OR 1=1--`
- [ ] XSS protection checked with harmless test input `<script>alert('xss')</script>`

## Data Pipeline
- [ ] Airflow scraper ran successfully
- [ ] `raw_job_postings` table populated
- [ ] `transform_jobs` DAG completed
- [ ] `analytics.fct_job_postings` has data
- [ ] Analytics dashboard reflects scraped data

## Cross-Browser Testing
- [ ] Chrome desktop
- [ ] Chrome mobile
- [ ] Firefox
- [ ] Safari if Mac available
- [ ] Edge

## Error Handling
- [ ] 404 page for invalid routes
- [ ] Friendly server error handling
- [ ] Friendly error messages, not stack traces
- [ ] Toast notifications for user actions

## Final Checks
- [ ] All environment variables set correctly
- [ ] No hardcoded secrets in code
- [ ] GitHub repo updated with deployment docs
- [ ] README.md has live demo link
- [ ] CONTRIBUTING.md explains dev workflow

## Bugs Found
Document any issues here for fixing.

---

When all items are checked, ApplyLuma is production-ready.

