"""FastAPI entrypoint — thin orchestrator only."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, clips, health, search, upload, videos
from app.config import (
    CORS_ORIGINS,
    IS_PRODUCTION,
    WARM_MODELS,
    ensure_storage_dirs,
    validate_production_config,
)
from app.database.connection import apply_schema
from app.services.indexing_service import warm_models
from app.utils.logging import RequestIdMiddleware, configure_logging
from app.workers.recovery import recover_unfinished_jobs

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_production_config()
    ensure_storage_dirs()
    apply_schema()
    recover_unfinished_jobs()
    if WARM_MODELS:
        threading.Thread(target=warm_models, daemon=True, name="model-warmup").start()
    yield


app = FastAPI(
    title="Clipseek",
    description="Upload videos, index with YOLO/ByteTrack/CLIP, search by text.",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(videos.router)
app.include_router(search.router)
app.include_router(clips.router)
