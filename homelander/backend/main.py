from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import chat, models
from backend.core.config import settings
from backend.database.db import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("homelander")

app = FastAPI(title="HOMELANDER API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(models.router)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    logger.info("HOMELANDER backend started. Local-only mode: %s", settings.LOCAL_ONLY_MODE)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak raw stack traces to the client (spec rule #22).
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong inside HOMELANDER. Please try again."},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
