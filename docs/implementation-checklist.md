# PlotPlanner implementation checklist

The product described in the README is implemented in `backend/app` and `frontend/src`.
Legacy files (`profile_api.py`, `RAG_KB_api.py`, `mcp_tools.py`, the old frontend panels) are unused and were left in place.

## What is in place

- Auth: Supabase JWT via JWKS. Ownership enforced in the API. RLS on every public table.
- Profile, facts, conversational onboarding, interest graph, courses with verified YouTube videos and checked documentation links, goals and plans, chat with tools and confirmable proposals, documents (PDF/DOCX/TXT), job search (Jobicy, The Muse, optional Adzuna), salary evidence from published listings, earning plans, analytics, account data deletion, per-user rate limits.
- MCP at `/mcp` (`search_learning_resources`, `search_jobs`, `get_course_details`), same token verification, read-only.
- Migration `0002` applied to Supabase (additive). Existing user and profile were kept (1 user, 1 profile, alembic `0002`, 18 public tables, all with RLS).

## Decisions worth knowing

| Decision | Why |
| --- | --- |
| JWKS (ES256/RS256), no JWT secret | The project signs with asymmetric keys |
| Alembic version table in `app_private` | `public` is exposed by the Data API |
| RLS plus ownership checks in code | The backend connects as the table owner, which bypasses RLS |
| Plain CSS, not Tailwind | The app already had a design system; the new pages extend it |
| Documents stored as private `bytea` | Supabase Storage needs a service-role key this server does not hold |
| Postgres full-text search, not pgvector | No vector extension on the project, and reviewable facts don't need embeddings |
| Remotive not used | Its terms forbid showing listings behind an account signup |
| Jobicy tag search is one keyword, then filtered locally | Its tag search does not match multi-word queries well |
| AI changes are proposals until accepted | Chat must not write the profile on its own |
| Course generation is a status job (`generating` → `ready`/`failed`) | It calls the model and YouTube and must not hold the request open |

## Still external

| Item | State |
| --- | --- |
| Google sign-in | Provider is disabled in the Supabase project. Email and password work. |
| Email confirmation | Required by the project (`mailer_autoconfirm` off) |
| Adzuna | Optional. Set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` for extra listings and provider salary estimates |
| Deleting the Supabase Auth account | Needs a service-role key. The app deletes all PlotPlanner data and says so |
| YouTube quota | A daily quota exhaustion is reported on the course; the pathway is still saved |

## Run it

```bash
cd backend && .venv/bin/alembic upgrade head
backend/.venv/bin/uvicorn app.main:app --port 8000
cd frontend && npm run dev

backend/scripts/test_db.sh start
backend/.venv/bin/python -m pytest backend/tests
(cd frontend && npm test)
```
