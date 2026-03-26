import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.middleware.auth import ws_auth
from app.services.metrics_service import collect_metrics_async
from config import settings

router = APIRouter()


@router.websocket("/metrics")
async def metrics_ws(websocket: WebSocket, token: str = Query(...)):
    user = await ws_auth(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    try:
        while True:
            metrics = await collect_metrics_async()
            await websocket.send_json(metrics.model_dump())
            await asyncio.sleep(settings.metrics_interval)
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
