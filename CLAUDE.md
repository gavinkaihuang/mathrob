# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MathRob — an AI-driven high-school math learning system (Shanghai curriculum). OCR image scan → Gemini AI analysis (LaTeX / difficulty / knowledge points) → SM-2 spaced-repetition reviews → full-paper grading + diagnostic assessments + weighted knowledge-mastery scoring.

Monorepo: **Python FastAPI backend** + **Next.js 16 (App Router) frontend**. External Postgres (NAS) and MinIO/S3 (image storage). AI via Google Gemini.

## Commands

### Run the backend (run from repo root — the module path is `backend.app.main`)

```bash
source backend/venv/bin/activate && uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend: http://localhost:8000 · Swagger at `/docs`. The server must be started from the repo root, not from `backend/`.

### Run the frontend

```bash
cd frontend && npm run dev      # http://localhost:3006 (port is fixed via package.json)
cd frontend && npm run build    # production build
cd frontend && npm run lint     # eslint (flat config, eslint-config-next)
```

### Install deps / first-time setup

```bash
pip install -r backend/requirements.txt     # with backend venv active
cd frontend && npm install
```

### Database migrations (must run from `backend/`)

`alembic/env.py` imports `from app.database import Base` and prepends `os.getcwd()` to `sys.path`, so Alembic **must be invoked from the `backend/` directory**, not the repo root:

```bash
cd backend
source venv/bin/activate
alembic upgrade head                                  # apply migrations
alembic revision --autogenerate -m "describe change"  # create a new revision
```

`create_db.py` is a legacy bootstrap helper; prefer Alembic for schema changes.

### Tests

**There is no test suite.** `pytest` is not in `requirements.txt`. The many `backend/test_*.py`, `check_*.py`, `debug_*.py`, `dump_*.py`, and `show_*.py` files are **ad-hoc inspection/migration scripts**, not a test framework — do not treat `pytest` as runnable. `backend/scripts/rerun_exam.py` re-grades an existing exam.

## Architecture

### Backend layout

```
backend/app/
├── main.py            # FastAPI app, CORS, lifespan (file watcher thread), router registration
├── database.py        # engine (pool_size=20, statement_timeout=10min), get_db + tenacity retry
├── models.py          # all ORM models (single file)
├── auth_deps.py       # get_current_user / get_current_active_admin (JWT, OAuth2 at /api/token)
├── config.py          # frozen S3 settings dataclass
├── routers/
│   ├── api.py         # SHIM — aggregates the 5 domain routers below into one /api router
│   ├── _common.py     # shared Pydantic schemas + singleton ai_service instance
│   ├── problems.py    # problem CRUD, wrong-book, mastery, AI analysis, similar, solution submit
│   ├── reviews.py     # daily review, review history, daily-practice generation
│   ├── exams.py       # full-paper upload+grade pipeline, history, status polling, detail
│   ├── assessment.py  # diagnostic assessment: generate paper, submit, grade, finalize
│   ├── misc.py        # weekly report, progress, logs, solution attempts
│   ├── auth.py users.py settings.py logs.py upload.py
├── services/          # business logic (see "Service layer" below)
└── api/v1/endpoints/taxonomy.py   # EXTERNAL API for MathQBank: /api/v1/taxonomy/{tags,tree}
```

**`routers/api.py` is a thin aggregator**, not the old 3100-line monolith some root docs still describe. When adding endpoints, put them in the matching domain router (`problems` / `reviews` / `exams` / `assessment` / `misc`) and reuse schemas + `ai_service` from `routers/_common.py`. `main.py` includes `api.router` under `/api`, so URL paths stay unchanged.

### Service layer (`backend/app/services/`)

- **`ai_service.py`** (~1000 lines) — the core. `call_gemini_with_fallback()` handles token rotation + retries; entry points `analyze_image`, `analyze_solution`, `generate_similar_problem`, `grade_full_paper`. Picks model by category (vision / routine_teaching / advanced_assessment / utility).
- **`token_manager.py`** — round-robin over the DB-backed Gemini key pool; 429/quota errors trigger a 60-min cooldown persisted to `gemini_tokens`.
- **`model_manager.py`** — resolves the Gemini model name from the `model_configs` table by role, or by `ExamType` (custom → routine_teaching/Flash; diagnostic/midterm/final → advanced_assessment/Pro).
- **`srs_logic.py`** — SM-2 spaced repetition (0/1/2 score → interval & ease updates).
- **`knowledge_mastery_service.py`** — weighted moving-average mastery: `custom=1.0, diagnostic=2.0, midterm=3.0, final=3.0`.
- **`upload_service.py`** — S3/MinIO upload + presigned URLs; `get_accessible_image_url()` hydrates image paths before they leave the API.
- **`taxonomy_service.py`** — builds the knowledge-point tree from `knowledge_nodes` (ltree path format, e.g. `101.10101.1010101`).
- **`report_service.py`** — weekly-report PDF via ReportLab.
- **`file_watcher.py`** — Watchdog thread on `backend/uploads/`; the `on_new_scan` callback in `main.py` is currently a no-op `print` (auto-scan is wired but not implemented end-to-end).

### Frontend layout

Next.js App Router; `@/*` path alias maps to the `frontend/` root. `next.config.ts` whitelists all http/https image hosts (presigned S3 URLs).

- **`context/AuthContext.tsx`** — JWT stored in `localStorage`, exposes `authHeader()`. Wrap at root layout.
- **`utils/api.ts`** — `fetchWithAuth()` injects the bearer header and, on `429/401/503`, dispatches a window `ai-system-error` CustomEvent → rendered by `components/SystemErrorBanner.tsx`. `resolveImageUrl()` normalizes stored image paths against `NEXT_PUBLIC_API_URL`. All API calls go through this helper.
- **`components/MarkdownRenderer.tsx`** — canonical renderer for any Markdown + LaTeX content (react-markdown + remark-gfm + remark-math + rehype-katex). KaTeX CSS is imported once in `app/layout.tsx`. Reuse this rather than `LatexRenderer` for mixed content.
- **`hooks/useExamPolling.ts`** — exam grading is async: `POST /api/exams/upload_and_grade` returns `exam_id` + `task_id`; the hook polls `/api/exams/task_status/{task_id}` then routes to `/exams/{exam_id}`.

## Cross-cutting conventions (read before changing these)

- **Images are in S3, not on disk.** Storage was migrated from `backend/uploads/` to MinIO. The `/static` mount still exists for legacy paths, but new code should use `upload_service` + presigned URLs on the backend and `resolveImageUrl` on the frontend. `_common._hydrate_problem_images` is the pattern for hydrating `Problem.image_path` before returning.
- **AI config is DB-driven, not env-driven.** Model names come from `model_configs`; Gemini keys come from the `gemini_tokens` pool. Do **not** wire up `GEMINI_API_KEY` from `.env` (it's a stale entry in `.env.example`).
- **DB engine is intentionally oversized.** `pool_size=20`, `max_overflow=20`, `statement_timeout=600000ms` (10 min) are sized for concurrent multi-batch exam grading — don't shrink without reason.
- **Transient DB errors return 503, not 500.** `get_db` + the `db_retry` tenacity decorator retry `OperationalError` and dispose the pool on failure; `get_current_user` returns 503 so polling endpoints degrade gracefully.
- **Exam-type weights drive mastery.** Changing `ExamType` semantics ripples into `knowledge_mastery_service` and `model_manager`.

## Environment

`.env` lives at the **repo root** and is loaded via `dotenv` by both `database.py` and `config.py`. Required vars:

- `DATABASE_URL` — Postgres connection string
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME` — MinIO/S3
- `NEXT_PUBLIC_API_URL` — backend origin for the frontend (defaults to empty → same-origin)

## Known tech debt (dev-only; do not "fix" silently without checking intent)

- CORS is `allow_origins=["*"]` with `allow_credentials=False`.
- JWT secret has a hardcoded default in `auth_service.py` — rotate for any non-local deployment.

## Repo docs are often stale

The root contains many `*.md` files (`PROJECT_CONTEXT.md`, `CODE_STRUCTURE_GUIDE.md`, `IMPLEMENTATION_*.md`, etc.). They are historical implementation notes and frequently lag the code — e.g. `PROJECT_CONTEXT.md` still describes `api.py` as a 3100-line monolith even after the router split. Use them for background, but verify against the actual source before relying on specifics.
