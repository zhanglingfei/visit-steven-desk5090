"""System health monitoring router"""
from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.services.health_service import get_system_health, SystemHealthStatus

router = APIRouter()


@router.get("/status", response_model=SystemHealthStatus)
async def health_status(user: dict = Depends(get_current_user)):
    """Get comprehensive system health status including GPU and power monitoring diagnostics"""
    return get_system_health()
