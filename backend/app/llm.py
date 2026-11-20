import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import httpx
from tools.registry import OLLAMA_TOOLS, execute_tool

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "system_prompt.txt"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")


def load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return (
        "You are Gipsy, a calm, crisp, and analytical tactical OS assistant. "
        "Keep spoken replies strictly concise: exactly 1 to 2 sentences with zero markdown or emojis."
    )


async def get_available_ollama_model() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                if OLLAMA_MODEL in models or any(OLLAMA_MODEL in m for m in models):
                    return OLLAMA_MODEL
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
        result = execute_tool("open_application", {"app_name": app_name})
        msg = f"Opening {app_name}. Ready on your display." if result.get("success") else f"Unable to locate application {app_name}."
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
        return ("get_system_telemetry", {}, f"System operating normally. CPU load at {cpu} percent with {ram} gigabytes memory in use.")

    if "lock" in text:
        execute_tool("run_quick_action", {"action": "lock_screen"})
        return ("run_quick_action", {"action": "lock_screen"}, "Workstation locked.")

    return None


async def run_gipsy_pipeline(content: str, manager):
    await manager.broadcast({
        "type": "state_change",
        "state": "PROCESSING",
    })
    await manager.broadcast({
        "type": "log",
        "level": "info",
        "message": f"Instruction received: \"{content}\"",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    model_name = await get_available_ollama_model()

    if model_name:
        system_prompt = load_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
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
                    },
                )

                if chat_resp.status_code == 200:
                    data = chat_resp.json()
                    msg = data.get("message", {})
                    tool_calls = msg.get("tool_calls", [])

                    if tool_calls:
                        for call in tool_calls:
                            func = call.get("function", {})
                            tool_name = func.get("name")
                            tool_args = func.get("arguments", {})
                            display_name = f"{tool_name}({json.dumps(tool_args)})"

                            await manager.broadcast({
                                "type": "state_change",
                                "state": "EXECUTING_TOOL",
                            })
                            await manager.broadcast({
                                "type": "tool_call",
                                "name": display_name,
                                "status": "running",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                            await manager.broadcast({
                                "type": "log",
                                "level": "action",
                                "message": f"Executing tool: {tool_name}",
                                "detail": display_name,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })

                            tool_output = execute_tool(tool_name, tool_args)

                            await manager.broadcast({
                                "type": "tool_call",
                                "name": display_name,
                                "status": "completed",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })

                            messages.append(msg)
                            messages.append({
                                "role": "tool",
                                "content": json.dumps(tool_output),
                            })

                        await manager.broadcast({
                            "type": "state_change",
                            "state": "SPEAKING",
                        })

                        stream_req = await client.post(
                            f"{OLLAMA_BASE_URL}/api/chat",
                            json={
                                "model": model_name,
                                "messages": messages,
                                "stream": True,
                            },
                        )

                        full_text = ""
                        async for line in stream_req.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                token = chunk.get("message", {}).get("content", "")
                                full_text += token
                                await manager.broadcast({
                                    "type": "stream_chunk",
                                    "chunk": token,
                                })
                            except Exception:
                                pass

                        clean_reply = full_text.strip().replace("*", "")
                        await manager.broadcast({
                            "type": "assistant_message",
                            "content": clean_reply,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                        await asyncio.sleep(1.0)
                        await manager.broadcast({
                            "type": "state_change",
                            "state": "IDLE",
                        })
                        return

                    else:
                        reply_text = msg.get("content", "").strip().replace("*", "")
                        await manager.broadcast({
                            "type": "state_change",
                            "state": "SPEAKING",
                        })
                        await manager.broadcast({
                            "type": "assistant_message",
                            "content": reply_text,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        await asyncio.sleep(1.0)
                        await manager.broadcast({
                            "type": "state_change",
                            "state": "IDLE",
                        })
                        return
        except Exception as e:
            await manager.broadcast({
                "type": "log",
                "level": "system",
                "message": f"Ollama dispatch failed: {str(e)}",
            })

    fallback = execute_fallback_intent(content)
    if fallback:
        tool_name, tool_args, reply_text = fallback
        display_name = f"{tool_name}({json.dumps(tool_args)})"

        await manager.broadcast({
            "type": "state_change",
            "state": "EXECUTING_TOOL",
        })
        await manager.broadcast({
            "type": "tool_call",
            "name": display_name,
            "status": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await manager.broadcast({
            "type": "log",
            "level": "action",
            "message": f"Dispatched OS tool: {tool_name}",
            "detail": display_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(0.5)

        await manager.broadcast({
            "type": "tool_call",
            "name": display_name,
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await manager.broadcast({
            "type": "state_change",
            "state": "SPEAKING",
        })
        await manager.broadcast({
            "type": "assistant_message",
            "content": reply_text,
            "tool": {
                "name": display_name,
                "status": "completed",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(1.2)
        await manager.broadcast({
            "type": "state_change",
            "state": "IDLE",
        })
    else:
        await manager.broadcast({
            "type": "state_change",
            "state": "SPEAKING",
        })
        await manager.broadcast({
            "type": "assistant_message",
            "content": f"Instruction recognized: {content}. Standing by for tactical directives.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await asyncio.sleep(1.0)
        await manager.broadcast({
            "type": "state_change",
            "state": "IDLE",
        })
