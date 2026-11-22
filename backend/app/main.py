import asyncio
import hmac
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.llm import run_gipsy_pipeline
from app.telemetry import get_system_telemetry
from app.websocket_manager import manager
from app.voice.audio_loop import AudioInputPipeline

ALLOWED_WS_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
}

audio_pipeline = AudioInputPipeline()


async def on_speech_captured(audio_data):
    await manager.broadcast({
        "type": "state_change",
        "state": "PROCESSING",
    })
    await manager.broadcast({
        "type": "log",
        "level": "info",
        "message": "Voice input detected, transcribing with Whisper...",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        text = await asyncio.to_thread(audio_pipeline.stt.transcribe, audio_data)
    except Exception as e:
        text = ""
        await manager.broadcast({
            "type": "log",
            "level": "system",
            "message": f"Whisper transcription error: {str(e)}",
        })

    if text.strip():
        await manager.broadcast({
            "type": "user_speech",
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await run_gipsy_pipeline(text, manager)
    else:
        await manager.broadcast({
            "type": "state_change",
            "state": "IDLE",
        })


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
    origin = websocket.headers.get("origin")
    if origin and origin not in ALLOWED_WS_ORIGINS:
        await websocket.close(code=4003, reason="Forbidden: untrusted origin")
        return

    expected_token = os.getenv("GIPSY_AUTH_TOKEN")
    if expected_token:
        client_token = websocket.query_params.get("token") or websocket.headers.get("x-auth-token")
        if not client_token or not hmac.compare_digest(client_token, expected_token):
            await websocket.close(code=4001, reason="Unauthorized: invalid or missing auth token")
            return

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
                asyncio.create_task(run_gipsy_pipeline(content, manager))
            elif msg_type == "toggle_mic":
                active = bool(data.get("active", False))
                if active:
                    await manager.broadcast({
                        "type": "state_change",
                        "state": "LISTENING",
                    })
                    await manager.broadcast({
                        "type": "log",
                        "level": "action",
                        "message": "Microphone capture active, listening for speech...",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    try:
                        audio_pipeline.start_capture(on_speech_captured)
                    except Exception as e:
                        await manager.broadcast({
                            "type": "log",
                            "level": "system",
                            "message": f"Microphone init note: {str(e)}",
                        })
                else:
                    audio = audio_pipeline.stop_capture()
                    if audio is not None and len(audio) > 0:
                        asyncio.create_task(on_speech_captured(audio))
                    else:
                        await manager.broadcast({
                            "type": "state_change",
                            "state": "IDLE",
                        })
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
