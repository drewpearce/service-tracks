"""PCO (Planning Center Online) API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.pco_client import PcoApiError, PcoAuthError, PcoClient, PcoRateLimitError, PcoServerError
from app.database import get_db
from app.dependencies import require_verified_email
from app.models.church import Church
from app.models.pco_connection import PcoConnection
from app.rate_limit import limiter
from app.schemas.pco import (
    PcoConnectRequest,
    PcoConnectResponse,
    PcoStatusResponse,
    SelectServiceTypeRequest,
    SelectServiceTypeResponse,
)
from app.utils.encryption import decrypt, encrypt

router = APIRouter(prefix="/api/pco", tags=["pco"])


# ---------------------------------------------------------------------------
# POST /connect
# ---------------------------------------------------------------------------


@router.post("/connect")
@limiter.limit("10/minute")
async def connect(
    body: PcoConnectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> PcoConnectResponse:
    """Validate PCO credentials, encrypt and store them, return service types."""
    church_id = request.state.church_id

    client = PcoClient(body.application_id, body.secret)

    try:
        valid = await client.validate_credentials()
        if not valid:
            raise HTTPException(status_code=400, detail="invalid_credentials")

        service_types = await client.get_service_types()
    except PcoRateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"PCO rate limit exceeded. Retry after {exc.retry_after} seconds.",
        ) from exc
    except PcoServerError as exc:
        raise HTTPException(status_code=502, detail="PCO is currently unavailable.") from exc
    except PcoApiError as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected PCO error: {exc.message}") from exc

    # Encrypt credentials
    app_id_encrypted = encrypt(body.application_id)
    secret_encrypted = encrypt(body.secret)

    # Upsert pco_connection
    result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    conn = result.scalar_one_or_none()

    if conn is not None:
        conn.auth_method = "api_key"
        conn.app_id_encrypted = app_id_encrypted
        conn.secret_encrypted = secret_encrypted
        conn.status = "active"
        conn.last_successful_call_at = datetime.now(timezone.utc)
    else:
        conn = PcoConnection(
            church_id=church_id,
            auth_method="api_key",
            app_id_encrypted=app_id_encrypted,
            secret_encrypted=secret_encrypted,
            status="active",
            last_successful_call_at=datetime.now(timezone.utc),
        )
        db.add(conn)

    await db.flush()

    return PcoConnectResponse(status="active", service_types=service_types)


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


@router.get("/status")
async def status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> PcoStatusResponse:
    """Return the PCO connection status for the authenticated church."""
    church_id = request.state.church_id

    result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    conn = result.scalar_one_or_none()

    if conn is None:
        return PcoStatusResponse(
            connected=False,
            auth_method=None,
            status=None,
            last_successful_call_at=None,
        )

    # Look up service type info if configured
    service_type_id: str | None = None
    service_type_name: str | None = None
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one_or_none()
    if church is not None and church.pco_service_type_id is not None:
        service_type_id = church.pco_service_type_id
        # Attempt to resolve name via PCO API (graceful degradation on failure)
        if conn.status == "active":
            try:
                app_id = decrypt(conn.app_id_encrypted)
                secret = decrypt(conn.secret_encrypted)
                client = PcoClient(app_id, secret)
                service_type = await client.get_service_type(church.pco_service_type_id)
                if service_type is not None:
                    service_type_name = service_type.name
            except (PcoApiError, Exception):
                # Graceful degradation: return service_type_id without name
                pass

    return PcoStatusResponse(
        connected=True,
        auth_method=conn.auth_method,
        status=conn.status,
        last_successful_call_at=(conn.last_successful_call_at.isoformat() if conn.last_successful_call_at else None),
        service_type_id=service_type_id,
        service_type_name=service_type_name,
    )


# ---------------------------------------------------------------------------
# POST /select-service-type
# ---------------------------------------------------------------------------


@router.post("/select-service-type")
@limiter.limit("10/minute")
async def select_service_type(
    body: SelectServiceTypeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> SelectServiceTypeResponse:
    """Validate a service type via PCO and save it to the church record."""
    church_id = request.state.church_id

    # Fetch the PCO connection
    result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    conn = result.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=400, detail="pco_not_connected")

    # Decrypt credentials
    app_id = decrypt(conn.app_id_encrypted)
    secret = decrypt(conn.secret_encrypted)

    client = PcoClient(app_id, secret)

    try:
        service_type = await client.get_service_type(body.service_type_id)
        if service_type is None:
            raise HTTPException(status_code=400, detail="invalid_service_type")
    except PcoAuthError as exc:
        raise HTTPException(status_code=400, detail="pco_credentials_invalid") from exc
    except PcoRateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"PCO rate limit exceeded. Retry after {exc.retry_after} seconds.",
        ) from exc
    except PcoServerError as exc:
        raise HTTPException(status_code=502, detail="PCO is currently unavailable.") from exc
    except PcoApiError as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected PCO error: {exc.message}") from exc

    # Update the church record
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one()
    church.pco_service_type_id = body.service_type_id
    church.sync_enabled = True
    await db.flush()

    return SelectServiceTypeResponse(
        service_type_id=service_type.id,
        service_type_name=service_type.name,
    )
