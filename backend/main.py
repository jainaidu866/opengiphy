import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import create_db_and_tables
from routers import auth, gifs, likes, profiles, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="OpenGIPHY API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded GIFs at http://localhost:8000/uploads/<filename>.gif
os.makedirs(gifs.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=gifs.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(gifs.router)
app.include_router(likes.router)
app.include_router(profiles.router)
app.include_router(reports.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


# Serve the built Vue frontend (frontend/dist) at the root. This mount MUST be
# registered last so the API routes above take priority; the catch-all "/" only
# handles paths the API doesn't claim. html=True serves index.html for "/".
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
