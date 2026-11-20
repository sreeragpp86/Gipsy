import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.telemetry import get_system_telemetry
from app.websocket_manager import manager, process_text_command


async def telemetry_loop():
    while True:
        try:
            if manager.active_connections:
                data = get_system_telemetry()
                await manager.broadcast({
                    "type": "telemetry",
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        except Exception:
            pass
        await asyncio.sleep(1.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_system_telemetry()
    task = asyncio.create_task(telemetry_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Project Gipsy API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        initial_telemetry = get_system_telemetry()
        await websocket.send_json({
            "type": "connection_ack",
            "state": "IDLE",
            "telemetry": initial_telemetry,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "text_command":
                content = data.get("content", "")
                asyncio.create_task(process_text_command(content))
            elif msg_type == "set_state":
                state = data.get("state", "IDLE")
                await manager.broadcast({
                    "type": "state_change",
                    "state": state,
                })
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
