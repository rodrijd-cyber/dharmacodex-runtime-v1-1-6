from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .asset_manager import AssetManager, AssetVerificationError
from .master_adapter import generate_complete_internal_reading
from .master_loader import MASTER_SHA256, canonical_source
from .schemas import ReadingInput


logging.basicConfig(level=os.getenv("LOG_LEVEL", "WARNING"))
logger = logging.getLogger("dharmacodex.runtime")
manager = AssetManager()
runtime_assets = None
startup_error: str | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global runtime_assets, startup_error
    try:
        canonical_source()
        runtime_assets = manager.prepare()
    except Exception as exc:
        startup_error = type(exc).__name__
        logger.error("runtime startup failed closed: %s", startup_error)
    yield


app = FastAPI(title="DharmaCodex Private Runtime", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.middleware("http")
async def no_store(request: Request, call_next):
    response = await call_next(request)
    response.headers["cache-control"] = "no-store"
    response.headers["x-content-type-options"] = "nosniff"
    return response


@app.get("/health")
def health():
    if runtime_assets is None:
        return JSONResponse({"status": "NOT_READY"}, status_code=503)
    return {"status": "READY", "runtime_version": "1.1.6", "master_sha256": MASTER_SHA256}


@app.post("/internal/reading")
def reading(input_data: ReadingInput):
    if runtime_assets is None:
        raise HTTPException(status_code=503, detail="RUNTIME_NOT_READY")
    try:
        return generate_complete_internal_reading(input_data, runtime_assets)
    except AssetVerificationError:
        raise HTTPException(status_code=503, detail="RUNTIME_ASSETS_UNAVAILABLE")
    except Exception as exc:
        logger.exception("reading calculation failed: %s", type(exc).__name__)
        raise HTTPException(status_code=422, detail="READING_CALCULATION_FAILED") from None

