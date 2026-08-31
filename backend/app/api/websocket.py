from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/ws")
async def market_socket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected"})
