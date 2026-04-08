from fastapi import APIRouter
from starlette.responses import JSONResponse

from app.scheduler import get_scheduler_status

router = APIRouter()


@router.get("/api/health")
async def health_check():
    sched = get_scheduler_status()

    status_code = 200
    status = "healthy"

    if sched["scheduler"] != "running":
        status_code = 503
        status = "degraded"

    body = {
        "status": status,
        "db": "ok",
        **sched,
    }

    return JSONResponse(content=body, status_code=status_code)
