## Summary
<!-- 1-3 bullets: what changed and why -->

## Test plan
- [ ] Backend: `pytest`
- [ ] Backend: `ruff check app/`
- [ ] Backend: `mypy app/`
- [ ] Frontend: `npm run lint`
- [ ] Frontend: `npm run type-check`
- [ ] Frontend: `npm test`
- [ ] Frontend: `npm run build`
- [ ] Verified manually in the browser (UI changes only)

## Checklist
- [ ] Branched from `dev`; this PR does not target `main` directly (unless
      this *is* the dev → main release PR)
- [ ] Includes an Alembic migration, and `alembic upgrade head` was run
      locally — or N/A
- [ ] No secrets, credentials, or `.env` files included
