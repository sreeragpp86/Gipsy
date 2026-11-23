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


def on_audio_amplitude(amp: float):
    if manager.active_connections:
        asyncio.create_task(manager.broadcast({
            "type": "audio_amplitude",
            "amplitude": amp,
        }))


async def on_speech_captured(audio_data):
    if len(audio_data) < 6400:
        return

    is_active = audio_pipeline.is_active_mode()

    text = ""
    try:
        text = await asyncio.to_thread(audio_pipeline.stt.transcribe, audio_data)
    except Exception as e:
        await manager.broadcast({
            "type": "log",
            "level": "system",
            "message": f"Whisper transcription error: {str(e)}",
        })
        return

    if not text or not text.strip():
        return

    clean_text = text.strip()
    has_wake, command = audio_pipeline.wake_detector.extract_wake_command(clean_text)

    if not is_active and not has_wake:
        return

    final_command = command if has_wake else clean_text
    audio_pipeline.pause_listening()

    await manager.broadcast({
        "type": "state_change",
        "state": "PROCESSING",
    })
    await manager.broadcast({
        "type": "user_speech",
        "text": clean_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await manager.broadcast({
        "type": "log",
        "level": "info",
        "message": f"Voice detected: '{clean_text}'",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    if not final_command:
        await manager.broadcast({
            "type": "log",
            "level": "info",
            "message": "Wake word recognized. Listening for command...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        from app.llm import tts_engine
        tts_engine.start_worker(manager)
        await tts_engine.enqueue_sentence("I'm listening.")
        await tts_engine.finish_stream()

        audio_pipeline.set_active_mode(8.0)
        audio_pipeline.resume_listening()
        await manager.broadcast({
            "type": "state_change",
            "state": "LISTENING",
        })
        return

    try:
        await run_gipsy_pipeline(final_command, manager)
    except Exception as e:
        await manager.broadcast({
            "type": "log",
            "level": "system",
            "message": f"Pipeline execution error: {str(e)}",
        })
    finally:
        audio_pipeline.resume_listening()
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

    from app.llm import tts_engine
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
                audio_pipeline.mute(not active)
                if active:
                    audio_pipeline.set_active_mode(10.0)
                    await manager.broadcast({
                        "type": "state_change",
                        "state": "LISTENING",
                    })
                    await manager.broadcast({
                        "type": "log",
                        "level": "action",
                        "message": "Microphone active. Listening for direct speech...",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    audio_pipeline.reset_active_mode()
                    await manager.broadcast({
                        "type": "state_change",
                        "state": "IDLE",
                    })
                    await manager.broadcast({
                        "type": "log",
                        "level": "info",
                        "message": "Microphone muted for privacy.",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            elif msg_type == "set_state":
                state = data.get("state", "IDLE")
                await manager.broadcast({
                    "type": "state_change",
                    "state": state,
                })
            elif msg_type == "admin_auth_submit":
                challenge_id = data.get("challenge_id", "")
                password = data.get("password", "")
                from app.security import admin_auth_manager
                is_valid = admin_auth_manager.resolve_challenge(challenge_id, password)
                await websocket.send_json({
                    "type": "admin_auth_result",
                    "challenge_id": challenge_id,
                    "success": is_valid,
                    "message": "Authorization approved." if is_valid else "Incorrect password. Authorization rejected.",
                })
            elif msg_type == "admin_auth_cancel":
                challenge_id = data.get("challenge_id", "")
                from app.security import admin_auth_manager
                admin_auth_manager.cancel_challenge(challenge_id)
                await websocket.send_json({
                    "type": "admin_auth_result",
                    "challenge_id": challenge_id,
                    "success": False,
                    "message": "Authorization cancelled by user.",
                })
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
