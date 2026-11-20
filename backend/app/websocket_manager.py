import asyncio
import re
from datetime import datetime, timezone
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

    async def send_personal(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)


manager = ConnectionManager()


async def process_text_command(content: str):
    await manager.broadcast({
        "type": "state_change",
        "state": "PROCESSING",
    })
    await manager.broadcast({
        "type": "log",
        "level": "info",
        "message": f"Processing command: \"{content}\"",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    is_os_action = bool(re.search(r"open|launch|volume|brightness|screen|app|finder|terminal|mute", content, re.IGNORECASE))

    if is_os_action:
        tool_name = f"os.dispatch_action(\"{content}\")"
        await manager.broadcast({
            "type": "state_change",
            "state": "EXECUTING_TOOL",
        })
        await manager.broadcast({
            "type": "tool_call",
            "name": tool_name,
            "status": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await manager.broadcast({
            "type": "log",
            "level": "action",
            "message": "Dispatching OS tool",
            "detail": tool_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(0.8)

        await manager.broadcast({
            "type": "tool_call",
            "name": tool_name,
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await manager.broadcast({
            "type": "state_change",
            "state": "SPEAKING",
        })
        await manager.broadcast({
            "type": "assistant_message",
            "content": f"Executed system instruction: \"{content}\"",
            "tool": {
                "name": tool_name,
                "status": "completed",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(1.2)

        await manager.broadcast({
            "type": "state_change",
            "state": "IDLE",
        })
        await manager.broadcast({
            "type": "log",
            "level": "system",
            "message": "Lifecycle returned to IDLE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    else:
        await manager.broadcast({
            "type": "state_change",
            "state": "SPEAKING",
        })
        await manager.broadcast({
            "type": "assistant_message",
            "content": f"Echo: \"{content}\". Standing by for OS directives.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(1.2)

        await manager.broadcast({
            "type": "state_change",
            "state": "IDLE",
        })
