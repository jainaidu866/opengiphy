import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import create_db_and_tables
from routers import auth, gifs, likes, profiles, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="OpenGIPHY API", version="0.1.0", lifespan=lifespan)

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
