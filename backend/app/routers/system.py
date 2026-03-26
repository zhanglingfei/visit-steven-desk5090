from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.models.metrics import SystemInfo
from app.services.metrics_service import MetricsCollector

router = APIRouter()


@router.get("/info", response_model=SystemInfo)
async def system_info(user: dict = Depends(get_current_user)):
    return MetricsCollector.get_system_info()
