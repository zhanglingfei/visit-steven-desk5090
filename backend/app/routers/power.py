import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, HTTPException

from app.middleware.auth import ws_auth, get_current_user
from app.models.power import PowerMetrics, PowerHistoryResponse
from app.services.power_service import (
    get_current_power,
    log_power_reading,
    get_total_kwh,
    get_power_history,
    get_recent_readings,
)

router = APIRouter()

# Cache for current power reading
_current_power_cache = {"reading": None, "timestamp": 0}


@router.get("/current", response_model=PowerMetrics)
async def get_current_power_metrics(user: dict = Depends(get_current_user)):
    """Get current power consumption and accumulated kWh"""
    # Ensure cache is loaded from database
    total_kwh = get_total_kwh()
    reading = get_current_power()

    # Calculate uptime since first reading
    from app.services.power_service import _power_cache
    uptime_hours = 0
    if _power_cache["first_reading_time"]:
        uptime_hours = (reading.timestamp - _power_cache["first_reading_time"]) / 3600

    return PowerMetrics(
        timestamp=reading.timestamp,
        watts=reading.watts,
        voltage=reading.voltage,
        current=reading.current,
        source=reading.source,
        total_kwh=round(total_kwh, 6),
        uptime_hours=round(uptime_hours, 2),
    )


@router.get("/total-kwh")
async def get_total_kwh_endpoint(user: dict = Depends(get_current_user)):
    """Get total accumulated kWh since monitoring started"""
    total = get_total_kwh()
    from app.services.power_service import _power_cache

    return {
        "total_kwh": round(total, 6),
        "first_reading_at": _power_cache["first_reading_time"],
    }


@router.get("/history", response_model=PowerHistoryResponse)
async def get_power_history_endpoint(
    start_date: datetime = Query(..., description="Start date (ISO format)"),
    end_date: datetime = Query(..., description="End date (ISO format)"),
    user: dict = Depends(get_current_user),
):
    """Get power consumption statistics for a specific time period"""
    from datetime import datetime as dt, timezone
    import time

    # Get current UTC time for comparison
    current_utc = dt.now(timezone.utc)
    current_ts = current_utc.timestamp()

    # Ensure dates are timezone-aware for accurate comparison
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    start_ts = start_date.timestamp()
    end_ts = end_date.timestamp()

    # Reject future dates - use 60 second buffer to account for clock skew
    if start_ts > current_ts + 60:
        raise HTTPException(status_code=400, detail="Start date cannot be in the future")
    if end_ts > current_ts + 60:
        raise HTTPException(status_code=400, detail="End date cannot be in the future")

    # Cap end timestamp at current time to prevent any future data leakage
    end_ts = min(end_ts, current_ts)

    return get_power_history(start_ts, end_ts)


@router.get("/recent")
async def get_recent_power_readings(
    hours: int = Query(default=24, ge=1, le=168),
    user: dict = Depends(get_current_user),
):
    """Get recent power readings for charting (default: last 24 hours)"""
    readings = get_recent_readings(hours)

    return {
        "readings": [
            {"timestamp": r[0], "watts": r[1]}
            for r in readings
        ],
        "count": len(readings),
    }


@router.websocket("/power")
async def power_ws(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for real-time power updates every 15 seconds"""
    user = await ws_auth(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    try:
        # Ensure cache is loaded from database on first connection
        get_total_kwh()

        # Use precise 15-second intervals aligned to clock
        import time
        next_reading_time = time.time()

        while True:
            # Wait until next 15-second interval
            sleep_duration = next_reading_time - time.time()
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)

            # Record actual timestamp
            reading_time = time.time()

            # Get current power reading
            reading = get_current_power()
            # Override timestamp for consistent intervals
            reading.timestamp = reading_time

            # Log to database and get accumulated kWh
            total_kwh = log_power_reading(reading)

            # Calculate uptime
            from app.services.power_service import _power_cache
            uptime_hours = 0
            if _power_cache["first_reading_time"]:
                uptime_hours = (reading.timestamp - _power_cache["first_reading_time"]) / 3600

            # Send metrics
            metrics = PowerMetrics(
                timestamp=reading.timestamp,
                watts=reading.watts,
                voltage=reading.voltage,
                current=reading.current,
                source=reading.source,
                total_kwh=round(total_kwh, 6),
                uptime_hours=round(uptime_hours, 2),
            )

            await websocket.send_json(metrics.model_dump())

            # Schedule next reading exactly 15 seconds later
            next_reading_time += 15

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
