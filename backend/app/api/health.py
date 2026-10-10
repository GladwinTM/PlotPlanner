import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

# The Supabase session pooler can take several seconds to hand out a connection.
READY_TIMEOUT_SECONDS = 15


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request):
    """Dependency check. Reports only pass/fail, never connection details."""
    try:
        async with request.app.state.session_factory() as session:
            await asyncio.wait_for(session.execute(text("select 1")), READY_TIMEOUT_SECONDS)
    except Exception as exc:  # any failure means "not ready"; the cause is logged
        logger.error("readiness check failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"status": "unavailable", "checks": {"database": "failed"}})
    return {"status": "ready", "checks": {"database": "ok"}}
