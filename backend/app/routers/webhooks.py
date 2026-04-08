import asyncio
import hashlib
import hmac

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import async_session_factory
from app.services.webhook_service import process_pco_webhook

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/pco")
async def receive_pco_webhook(request: Request) -> JSONResponse:
    """Receive and validate a PCO webhook payload."""
    body = await request.body()
    signature = request.headers.get("X-PCO-Webhooks-Authenticity", "")

    # Log every incoming webhook (valid or invalid)
    logger.info("pco_webhook_received", has_signature=bool(signature))

    # Validate HMAC-SHA256 signature
    if not signature or not settings.PCO_WEBHOOK_SECRET:
        logger.warning("pco_webhook_invalid_signature", reason="missing_signature_or_secret")
        return JSONResponse(status_code=403, content={"error": "invalid_signature"})

    expected = hmac.new(
        settings.PCO_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        logger.warning("pco_webhook_invalid_signature", reason="mismatch")
        return JSONResponse(status_code=403, content={"error": "invalid_signature"})

    # Parse payload and dispatch async processing
    # Use the app-level session_factory if available (for testability),
    # fall back to the module-level factory.
    session_factory = getattr(request.app.state, "session_factory", async_session_factory)
    task = asyncio.create_task(process_pco_webhook(body, session_factory))
    # Store reference to prevent garbage collection before task completes
    request.state.webhook_task = task

    return JSONResponse(status_code=200, content={"received": True})
