# OpenGIPHY

A Giphy-style GIF sharing platform. Solo intern project, built incrementally day by day.

## Stack

**Backend**
- FastAPI (REST API)
- SQLModel ORM on PostgreSQL (local)
- JWT auth: python-jose (tokens) + passlib/bcrypt (password hashing)
- Local filesystem storage for GIF files
- pytest + FastAPI TestClient

**Frontend** (not started yet — Day 2+)
- Vue 3 + Vite + TypeScript
- Tailwind CSS
- TanStack Query
- Vitest

## Layout

```
opengiphy/
├── backend/
│   ├── main.py            # app entry, router registration, lifespan
│   ├── database.py        # engine + session + create_all (dev)
│   ├── models.py          # SQLModel tables: User, Gif, Like
│   ├── auth.py            # hashing, JWT, get_current_user dependency
│   ├── routers/
│   │   ├── auth.py        # /auth/register, /auth/login, /auth/me
│   │   └── gifs.py        # (Day 2) upload/list/like
│   ├── requirements.txt
│   └── tests/
│       └── test_auth.py
└── frontend/              # (Day 2+) Vite Vue3 TS scaffold
```

## Data model

- **User**: id, email (unique), username (unique), hashed_password, created_at
- **Gif**: id, user_id (FK→users), title, description, tags (JSON), file_path, view_count, created_at
- **Like**: user_id + gif_id (composite PK), created_at

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

Run from `backend/`:

```bash
uvicorn main:app --reload      # dev server at http://127.0.0.1:8000 (docs at /docs)
pytest                         # run tests
```
