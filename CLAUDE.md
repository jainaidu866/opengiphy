# OpenGIPHY

A Giphy-style GIF sharing platform. Solo intern project, built incrementally day by day.

## Stack

**Backend**
- FastAPI (REST API)
- SQLModel ORM on PostgreSQL (local)
- JWT auth: python-jose (tokens) + passlib/bcrypt (password hashing)
- Local filesystem storage for GIF files
- pytest + FastAPI TestClient

**Frontend**
- Vue 3 + Vite + TypeScript
- Tailwind CSS (dark, Giphy-inspired theme)
- TanStack Query + Vue Router + Axios
- Vitest + Vue Test Utils (jsdom) for component tests

## Layout

```
opengiphy/
├── backend/
│   ├── main.py            # app entry, router registration, lifespan,
│   │                      #   /uploads static mount + serves frontend/dist at "/"
│   ├── database.py        # engine + session + create_all (dev)
│   ├── models.py          # SQLModel tables: User, Gif, Like, Report
│   ├── auth.py            # hashing, JWT, get_current_user(+_optional)
│   ├── routers/
│   │   ├── auth.py        # /auth/register, /auth/login, /auth/me
│   │   ├── gifs.py        # upload / list / detail / delete (+ search & sort)
│   │   ├── likes.py       # like toggle / like status
│   │   ├── profiles.py    # public user profiles
│   │   └── reports.py     # report a GIF
│   ├── requirements.txt
│   └── tests/             # test_auth, test_gifs, test_likes,
│                          #   test_profiles, test_reports (36 tests)
└── frontend/
    └── src/
        ├── api/client.ts  # axios instance (same-origin baseURL) + typed API fns
        ├── stores/auth.ts # auth composable (token + user)
        ├── router/        # routes + auth guard
        ├── views/         # Home, Login, Register, Upload, GifDetail, Profile, NotFound
        └── tests/         # Vitest component tests (12 tests)
```

## Data model

- **User**: id, email (unique), username (unique), hashed_password, created_at
- **Gif**: id, user_id (FK→users), title, description, tags (JSON), file_path, view_count, created_at
- **Like**: user_id + gif_id (composite PK), created_at
- **Report**: id, gif_id (FK→gifs), reporter_id (FK→users), reason, created_at; unique (gif_id, reporter_id)

## Rules / conventions

- All models use SQLModel.
- DB schema is created with `create_all()` — dev mode, no migrations yet.
- Every endpoint returns proper HTTP status codes and raises `HTTPException` on errors.
- JWT bearer tokens protect routes via the `get_current_user` dependency.
- Tests use FastAPI `TestClient` and override the DB session with in-memory SQLite (no live Postgres needed to run tests).
- Never return `hashed_password` in any response.

## Config (env vars)

- `DATABASE_URL` — defaults to `postgresql://postgres:postgres@localhost:5432/opengiphy`
- `SECRET_KEY` — JWT signing key (set a real one in production)
- `ACCESS_TOKEN_EXPIRE_MINUTES` — defaults to 60

## Common commands

Backend (run from `backend/`):

```bash
uvicorn main:app --reload      # dev server at http://127.0.0.1:8000 (docs at /docs)
pytest                         # run tests (36)
```

Frontend (run from `frontend/`):

```bash
npm run dev                    # Vite dev server at http://localhost:5173 (proxies /auth, /gifs, /profiles, /uploads → :8000)
npm run test                   # Vitest component tests (12)
npm run build                  # type-check + production build → frontend/dist/
```

## Serving / deployment

- The axios client uses a **same-origin** `baseURL` (`''`). In dev the Vite proxy
  forwards the API path prefixes to the backend; in production the backend serves
  the built frontend directly.
- If `frontend/dist/` exists, `main.py` mounts it at `/` (`StaticFiles(html=True)`),
  **after** all API routers — so the whole app runs on one origin (single tunnel,
  no CORS/proxy). Build the frontend first, then run uvicorn.
- A permissive CORS middleware (`allow_origins=["*"]`) and Vite `allowedHosts: true`
  were added for remote demo access — tighten both before any real deployment.
