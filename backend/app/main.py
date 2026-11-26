import asyncio
import hmac
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.llm import confirmation_manager, run_gipsy_pipeline, tts_engine
from app.security import admin_auth_manager
from app.telemetry import get_system_telemetry
from app.voice.audio_loop import AudioInputPipeline
from app.websocket_manager import manager

ALLOWED_ORIGINS = [
    "tauri://localhost",
    "http://tauri.localhost",
    "http://localhost:5173",
]
ALLOWED_WS_ORIGINS = set(ALLOWED_ORIGINS)

# 0.4s at 16 kHz filters brief clicks/pops before invoking Whisper
MIN_SPEECH_SAMPLES = 6400

audio_pipeline = AudioInputPipeline()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _broadcast_state(state: str):
    await manager.broadcast({"type": "state_change", "state": state})


async def _broadcast_log(level: str, message: str, detail: str | None = None):
    payload = {
        "type": "log",
        "level": level,
        "message": message,
        "timestamp": _utc_now(),
    }
    if detail is not None:
        payload["detail"] = detail
    await manager.broadcast(payload)


def on_audio_amplitude(amp: float):
    if manager.active_connections:
        asyncio.create_task(manager.broadcast({"type": "audio_amplitude", "amplitude": amp}))


async def on_speech_captured(audio_data):
    if len(audio_data) < MIN_SPEECH_SAMPLES:
        return

    is_active = audio_pipeline.is_active_mode()

    try:
        text = await asyncio.to_thread(audio_pipeline.stt.transcribe, audio_data)
    except Exception as e:
        await _broadcast_log("system", f"Whisper transcription error: {e}")
        return

    clean_text = (text or "").strip()
    if not clean_text:
        return

    has_wake, command = audio_pipeline.wake_detector.extract_wake_command(clean_text)
    if not is_active and not has_wake:
        return

    final_command = command if has_wake else clean_text
    audio_pipeline.pause_listening()

    await _broadcast_state("PROCESSING")
    await manager.broadcast({
        "type": "user_speech",
        "text": clean_text,
        "timestamp": _utc_now(),
    })
    await _broadcast_log("info", f"Voice detected: '{clean_text}'")

    if not final_command:
        await _broadcast_log("info", "Wake word recognized. Listening for command...")
        tts_engine.start_worker(manager)
        await tts_engine.enqueue_sentence("I'm listening.")
        await tts_engine.finish_stream()
        await tts_engine.queue.join()
        while tts_engine.is_playing:
            await asyncio.sleep(0.05)

        audio_pipeline.set_active_mode(8.0)
        audio_pipeline.resume_listening()
        await _broadcast_state("LISTENING")
        return

    try:
        await run_gipsy_pipeline(final_command, manager)
    except Exception as e:
        await _broadcast_log("system", f"Pipeline execution error: {e}")
    finally:
        audio_pipeline.resume_listening()
        await _broadcast_state("IDLE")


async def telemetry_loop():
    while True:
        try:
            if manager.active_connections:
                await manager.broadcast({
                    "type": "telemetry",
                    "data": get_system_telemetry(),
                    "timestamp": _utc_now(),
                })
        except Exception:
            pass
        await asyncio.sleep(1.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_system_telemetry()
    task = asyncio.create_task(telemetry_loop())
    audio_pipeline.set_tts_guard(lambda: tts_engine.is_playing)

    try:
        audio_pipeline.start_listening(
            on_speech_completed=on_speech_captured,
            on_amplitude=on_audio_amplitude,
        )
    except Exception as e:
        print(f"[Gipsy Voice] Audio capture initialization note: {e}")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    audio_pipeline.stop_listening()


app = FastAPI(title="Project Gipsy API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": _utc_now(),
    }


async def _handle_ws_message(websocket: WebSocket, data: dict):
    msg_type = data.get("type")

    if msg_type == "text_command":
        asyncio.create_task(run_gipsy_pipeline(data.get("content", ""), manager))
    elif msg_type == "toggle_mic":
        active = bool(data.get("active", False))
        audio_pipeline.mute(not active)
        if active:
            audio_pipeline.set_active_mode(10.0)
            await _broadcast_state("LISTENING")
            await _broadcast_log("action", "Microphone active. Listening for direct speech...")
        else:
            audio_pipeline.reset_active_mode()
            await _broadcast_state("IDLE")
            await _broadcast_log("info", "Microphone muted for privacy.")
    elif msg_type == "confirm_response":
        request_id = data.get("request_id", "")
        approved = bool(data.get("approved", False))
        confirmation_manager.resolve_confirmation(request_id, approved)
    elif msg_type == "admin_auth_submit":
        challenge_id = data.get("challenge_id", "")
        is_valid = admin_auth_manager.resolve_challenge(challenge_id, data.get("password", ""))
        await websocket.send_json({
            "type": "admin_auth_result",
            "challenge_id": challenge_id,
            "success": is_valid,
            "message": "Authorization approved." if is_valid else "Incorrect password. Authorization rejected.",
        })
    elif msg_type == "admin_auth_cancel":
        challenge_id = data.get("challenge_id", "")
        admin_auth_manager.cancel_challenge(challenge_id)
        await websocket.send_json({
            "type": "admin_auth_result",
            "challenge_id": challenge_id,
            "success": False,
            "message": "Authorization cancelled by user.",
        })
    elif msg_type == "ping":
        await websocket.send_json({"type": "pong"})


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
        await websocket.send_json({
            "type": "connection_ack",
            "state": "IDLE",
            "telemetry": get_system_telemetry(),
            "timestamp": _utc_now(),
        })

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            await _handle_ws_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
