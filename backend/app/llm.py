import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
import httpx
from app.security import admin_auth_manager, is_admin_operation
from app.voice.tts import SentenceChunker, TextToSpeechEngine
from tools.os_tools import RISKY_TOOLS
from tools.registry import OLLAMA_TOOLS, execute_tool

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "system_prompt.txt"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
OLLAMA_OPTIONS = {"num_ctx": 8192, "temperature": 0.3}

tts_engine = TextToSpeechEngine()


class ConfirmationManager:
    def __init__(self):
        self._pending: dict[str, asyncio.Future] = {}

    def create_confirmation(self) -> tuple[str, asyncio.Future]:
        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending[request_id] = future
        return request_id, future

    def resolve_confirmation(self, request_id: str, approved: bool) -> bool:
        future = self._pending.pop(request_id, None)
        if not future or future.done():
            return False
        future.set_result(bool(approved))
        return True

    def cancel_confirmation(self, request_id: str):
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(False)


confirmation_manager = ConfirmationManager()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return (
        "You are Gipsy, a calm, crisp, and analytical tactical OS assistant. "
        "Keep spoken replies strictly concise: exactly 1 to 2 sentences with zero markdown or emojis. "
        "You have access to capture_screen whenever the user asks about what is on their screen, "
        "an error message, or open windows."
    )


async def get_available_ollama_model() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if OLLAMA_MODEL in models or any(OLLAMA_MODEL in m for m in models):
                    return OLLAMA_MODEL
                for candidate in ("qwen3.5:9b", "qwen2.5:7b", "qwen2.5:0.5b"):
                    if any(candidate in m for m in models):
                        return candidate
                if models:
                    return models[0]
    except Exception:
        pass
    return None


def execute_fallback_intent(content: str) -> tuple[str, dict, str] | None:
    text = content.strip().lower()

    open_match = re.search(r"(?:open|launch)\s+([a-zA-Z0-9\s]+)", text)
    if open_match:
        app_name = open_match.group(1).strip()
        if is_admin_operation("open_application", {"app_name": app_name}):
            return (
                "open_application",
                {"app_name": app_name},
                f"Launching {app_name} is an admin-level action and requires authentication on your HUD.",
            )
        result = execute_tool("open_application", {"app_name": app_name})
        msg = (
            f"Opening {app_name}. Ready on your display."
            if result.get("success")
            else f"Unable to locate application {app_name}."
        )
        return ("open_application", {"app_name": app_name}, msg)

    vol_match = re.search(r"(?:volume|audio)\s*(?:to\s*)?(\d+)", text)
    if vol_match:
        level = int(vol_match.group(1))
        execute_tool("set_volume", {"level": level})
        return ("set_volume", {"level": level}, f"Audio volume adjusted to {level} percent.")

    if "mute" in text:
        execute_tool("run_quick_action", {"action": "mute"})
        return ("run_quick_action", {"action": "mute"}, "Master audio output muted.")

    if "unmute" in text:
        execute_tool("run_quick_action", {"action": "unmute"})
        return ("run_quick_action", {"action": "unmute"}, "Master audio output restored.")

    if any(k in text for k in ("telemetry", "system status", "battery", "cpu", "ram")):
        res = execute_tool("get_system_telemetry", {})
        t = res.get("telemetry", {})
        cpu = t.get("cpu_usage", 0)
        ram = t.get("memory_used", 0)
        return (
            "get_system_telemetry",
            {},
            f"System operating normally. CPU load at {cpu} percent with {ram} gigabytes memory in use.",
        )

    if "lock" in text:
        execute_tool("run_quick_action", {"action": "lock_screen"})
        return ("run_quick_action", {"action": "lock_screen"}, "Workstation locked.")

    if "screen" in text and any(k in text for k in ("look", "see", "what", "analyze", "read", "error", "window")):
        res = execute_tool("capture_screen", {"question": content})
        msg = res.get("analysis") if res.get("success") else res.get("error", "Unable to capture screen.")
        return ("capture_screen", {"question": content}, msg)

    return None


async def _emit_reply(reply_text: str, manager, tool_info: dict | None = None):
    payload = {
        "type": "assistant_message",
        "content": reply_text,
        "timestamp": _utc_now(),
    }
    if tool_info is not None:
        payload["tool"] = tool_info

    await manager.broadcast(payload)
    tts_engine.start_worker(manager)
    await tts_engine.enqueue_sentence(reply_text)
    await tts_engine.finish_stream()


async def _authorize_and_execute_tool(tool_name: str, tool_args: dict, manager) -> dict:
    display_name = f"{tool_name}({json.dumps(tool_args)})"

    await manager.broadcast({"type": "state_change", "state": "EXECUTING_TOOL"})
    await manager.broadcast({
        "type": "tool_call",
        "name": display_name,
        "status": "running",
        "timestamp": _utc_now(),
    })
    await manager.broadcast({
        "type": "log",
        "level": "action",
        "message": f"Executing tool: {tool_name}",
        "detail": display_name,
        "timestamp": _utc_now(),
    })

    if tool_name in RISKY_TOOLS:
        request_id, confirm_future = confirmation_manager.create_confirmation()
        await manager.broadcast({
            "type": "confirm_required",
            "request_id": request_id,
            "tool": tool_name,
            "args": tool_args,
        })
        await manager.broadcast({
            "type": "log",
            "level": "system",
            "message": f"Safety Gate: Operator confirmation required for '{tool_name}'.",
            "timestamp": _utc_now(),
        })

        try:
            approved = await asyncio.wait_for(confirm_future, timeout=30.0)
        except asyncio.TimeoutError:
            approved = False
            confirmation_manager.cancel_confirmation(request_id)

        if not approved:
            await manager.broadcast({
                "type": "tool_call",
                "name": display_name,
                "status": "denied",
                "timestamp": _utc_now(),
            })
            await manager.broadcast({
                "type": "log",
                "level": "system",
                "message": f"Safety Gate: '{tool_name}' cancelled by operator.",
                "timestamp": _utc_now(),
            })
            return {
                "success": False,
                "error": "Action cancelled by operator.",
                "message": "Action cancelled by operator.",
            }

    if is_admin_operation(tool_name, tool_args):
        challenge_id, auth_future = admin_auth_manager.create_challenge(tool_name, tool_args)
        await manager.broadcast({
            "type": "admin_auth_required",
            "challenge_id": challenge_id,
            "tool_name": tool_name,
            "arguments": tool_args,
            "prompt": f"Manual authentication required for '{tool_name}'. Please authorize on HUD.",
            "expires_in": 30,
            "timestamp": _utc_now(),
        })
        await manager.broadcast({
            "type": "log",
            "level": "system",
            "message": f"Security Gate: Operation '{tool_name}' requires manual admin authorization.",
            "timestamp": _utc_now(),
        })

        try:
            is_authorized = await asyncio.wait_for(auth_future, timeout=30.0)
        except asyncio.TimeoutError:
            is_authorized = False
            admin_auth_manager.cancel_challenge(challenge_id)

        if not is_authorized:
            await manager.broadcast({
                "type": "tool_call",
                "name": display_name,
                "status": "denied",
                "timestamp": _utc_now(),
            })
            await manager.broadcast({
                "type": "log",
                "level": "system",
                "message": f"Security Gate: Authorization rejected for '{tool_name}'.",
                "timestamp": _utc_now(),
            })
            return {
                "success": False,
                "error": "Manual admin authorization rejected or timed out. Command aborted.",
            }

    if tool_name == "capture_screen":
        await manager.broadcast({"type": "screen_capture_start"})
        # Allow macOS WindowServer a brief frame to hide the HUD before screencapture runs
        await asyncio.sleep(0.22)

    try:
        tool_output = await asyncio.to_thread(execute_tool, tool_name, tool_args)
    finally:
        if tool_name == "capture_screen":
            await manager.broadcast({"type": "screen_capture_end"})

    await manager.broadcast({
        "type": "tool_call",
        "name": display_name,
        "status": "completed",
        "timestamp": _utc_now(),
    })
    return tool_output


async def _stream_tool_followup(client: httpx.AsyncClient, model_name: str, messages: list[dict], manager):
    tts_engine.start_worker(manager)
    chunker = SentenceChunker()

    stream_req = await client.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": model_name,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": OLLAMA_OPTIONS,
        },
    )

    full_text = ""
    async for line in stream_req.aiter_lines():
        if not line:
            continue
        try:
            chunk = json.loads(line)
            token = chunk.get("message", {}).get("content", "")
            if token:
                full_text += token
                await manager.broadcast({"type": "stream_chunk", "chunk": token})
                for sentence in chunker.add_token(token):
                    await tts_engine.enqueue_sentence(sentence)
        except Exception:
            pass

    remaining = chunker.flush()
    if remaining:
        await tts_engine.enqueue_sentence(remaining)

    await manager.broadcast({
        "type": "assistant_message",
        "content": full_text.strip().replace("*", ""),
        "timestamp": _utc_now(),
    })
    await tts_engine.finish_stream()


async def _execute_pipeline(content: str, manager):
    await manager.broadcast({"type": "state_change", "state": "PROCESSING"})
    await manager.broadcast({
        "type": "log",
        "level": "info",
        "message": f'Instruction received: "{content}"',
        "timestamp": _utc_now(),
    })

    model_name = await get_available_ollama_model()
    if model_name:
        messages = [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": content},
        ]
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                chat_resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": model_name,
                        "messages": messages,
                        "tools": OLLAMA_TOOLS,
                        "stream": False,
                        "think": False,
                        "options": OLLAMA_OPTIONS,
                    },
                )

                if chat_resp.status_code == 200:
                    msg = chat_resp.json().get("message", {})
                    tool_calls = msg.get("tool_calls", [])
                    if tool_calls:
                        for call in tool_calls:
                            func = call.get("function", {})
                            tool_output = await _authorize_and_execute_tool(
                                func.get("name", ""),
                                func.get("arguments", {}),
                                manager,
                            )
                            messages.append(msg)
                            messages.append({"role": "tool", "content": json.dumps(tool_output)})

                        await _stream_tool_followup(client, model_name, messages, manager)
                        return

                    reply_text = msg.get("content", "").strip().replace("*", "")
                    await _emit_reply(reply_text, manager)
                    return
        except Exception as e:
            await manager.broadcast({
                "type": "log",
                "level": "system",
                "message": f"Ollama dispatch failed: {e}",
                "timestamp": _utc_now(),
            })

    fallback = execute_fallback_intent(content)
    if fallback:
        tool_name, tool_args, reply_text = fallback
        display_name = f"{tool_name}({json.dumps(tool_args)})"

        await manager.broadcast({"type": "state_change", "state": "EXECUTING_TOOL"})
        await manager.broadcast({
            "type": "tool_call",
            "name": display_name,
            "status": "running",
            "timestamp": _utc_now(),
        })
        await manager.broadcast({
            "type": "log",
            "level": "action",
            "message": f"Dispatched OS tool: {tool_name}",
            "detail": display_name,
            "timestamp": _utc_now(),
        })
        await asyncio.sleep(0.5)
        await manager.broadcast({
            "type": "tool_call",
            "name": display_name,
            "status": "completed",
            "timestamp": _utc_now(),
        })
        await _emit_reply(reply_text, manager, tool_info={"name": display_name, "status": "completed"})
    else:
        await _emit_reply(f"Instruction recognized: {content}. Standing by for tactical directives.", manager)


async def run_gipsy_pipeline(content: str, manager):
    try:
        await _execute_pipeline(content, manager)
    except Exception as e:
        await manager.broadcast({
            "type": "log",
            "level": "system",
            "message": f"Pipeline execution error: {e}",
            "timestamp": _utc_now(),
        })
        await manager.broadcast({"type": "state_change", "state": "IDLE"})
