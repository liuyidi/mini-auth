from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Verify the database connection is reachable before accepting traffic.
    # This surfaces misconfigured DATABASE_URL immediately at startup rather
    # than on the first request, which also causes Railway's health check to
    # fail fast and retry instead of routing traffic to a broken instance.
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield


app = FastAPI(
    title="DeepSeek Chat API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
