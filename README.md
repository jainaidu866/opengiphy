# OpenGIPHY

A Giphy-style GIF sharing platform — upload, discover, search, like, and share animated GIFs. Built as an incremental full-stack project with a FastAPI backend and a Vue 3 frontend.

## Features

- 🔐 **Auth** — register / login with JWT, protected routes
- ⬆️ **Upload** — drag-and-drop `.gif` upload with live preview, title, description, and tags
- 🔍 **Discover** — responsive masonry grid, full-text search (title / description / tags), **New** and **Trending** sorting
- ❤️ **Likes** — toggle likes with optimistic UI; real like counts everywhere
- 👤 **Profiles** — public user pages listing a user's uploads
- 🔗 **Embed** — copy-ready HTML / Markdown / direct-URL snippets per GIF
- ⚐ **Reporting** — report inappropriate GIFs (one report per user per GIF)

## Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — REST API
- [SQLModel](https://sqlmodel.tiangolo.com/) ORM on **PostgreSQL** (dev uses `create_all()`, no migrations)
- JWT auth — `python-jose` (tokens) + `passlib`/`bcrypt` (password hashing)
- Local filesystem storage for GIF files, served as static at `/uploads`
- Tests: `pytest` + FastAPI `TestClient` (in-memory SQLite override — no live DB needed)

**Frontend**
- [Vue 3](https://vuejs.org/) + [Vite](https://vitejs.dev/) + TypeScript
- [Tailwind CSS](https://tailwindcss.com/) (dark, Giphy-inspired theme)
- [TanStack Query](https://tanstack.com/query) for data fetching/caching
- [Vue Router](https://router.vuejs.org/) + Axios

## Project Structure

```
opengiphy/
├── backend/
│   ├── main.py            # app entry, router registration, static mount
│   ├── database.py        # engine + session + create_all (dev)
│   ├── models.py          # SQLModel tables: User, Gif, Like, Report
│   ├── auth.py            # hashing, JWT, get_current_user(+_optional)
│   ├── routers/
│   │   ├── auth.py        # register / login / me
│   │   ├── gifs.py        # upload / list / detail / delete (+ search & sort)
│   │   ├── likes.py       # like toggle / like status
│   │   ├── profiles.py    # public user profiles
│   │   └── reports.py     # report a GIF
│   ├── requirements.txt
│   ├── uploads/           # stored GIF files (git-ignored)
│   └── tests/             # pytest suite
└── frontend/
    └── src/
        ├── api/client.ts  # axios instance + typed API functions
        ├── stores/auth.ts # auth composable (token + user)
        ├── router/        # routes + auth guard
        └── views/         # Home, Login, Register, Upload, GifDetail, Profile, NotFound
```

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (running locally)

### Backend

```bash
cd backend

# 1. Create & activate a virtual environment
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database
psql -U postgres -c "CREATE DATABASE opengiphy;"

# 4. (Optional) configure environment — copy and edit
cp .env.example .env
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/opengiphy
# SECRET_KEY=replace-with-a-real-secret
# ACCESS_TOKEN_EXPIRE_MINUTES=60

# 5. Run the server (tables auto-create on startup)
uvicorn main:app --reload
```

Backend runs at **http://localhost:8000** — interactive docs at **http://localhost:8000/docs**.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**. The Vite dev server proxies `/api` and `/uploads` to the backend, so run both servers together.

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Register (email, username, password) |
| POST | `/auth/login` | — | Log in, returns JWT access token |
| GET | `/auth/me` | ✅ | Current user info |
| POST | `/gifs/upload` | ✅ | Upload a `.gif` (multipart) |
| GET | `/gifs/` | — | List GIFs. Params: `page`, `limit`, `search`, `sort` (`new`\|`trending`) |
| GET | `/gifs/{id}` | — | GIF detail (increments view count) |
| DELETE | `/gifs/{id}` | ✅ | Delete own GIF (owner only) |
| POST | `/gifs/{id}/like` | ✅ | Toggle like → `{liked, like_count}` |
| GET | `/gifs/{id}/likes` | optional | `{like_count, liked_by_me}` |
| POST | `/gifs/{id}/report` | ✅ | Report a GIF `{reason}` (min 10 chars) |
| GET | `/profiles/{username}` | — | User profile + their paginated GIFs |
| GET | `/health` | — | Health check |
| GET | `/uploads/{filename}` | — | Static GIF files |

## Running Tests

**Backend** (no PostgreSQL required — tests use an in-memory SQLite override):

```bash
cd backend
pytest          # run all tests
pytest -v       # verbose
```

**Frontend** (type-check + production build):

```bash
cd frontend
npm run build   # runs vue-tsc --noEmit && vite build
```

## Notes

- Dev mode uses SQLModel's `create_all()` — for production you'd add Alembic migrations.
- GIF files are stored on the local filesystem under `backend/uploads/`. A production deploy would use object storage (S3/GCS) and a CDN.
- Set a strong `SECRET_KEY` via environment variables in any real deployment.
