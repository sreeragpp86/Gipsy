from tools.os_tools import (
    get_system_telemetry,
    open_application,
    run_quick_action,
    set_volume,
)

OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Launch or activate a local application on the OS (e.g., Terminal, Notes, Safari, Finder, Calculator, Music).",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the target application to launch.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_telemetry",
            "description": "Query live system resource metrics including CPU load, RAM usage, and battery/power state.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Adjust the system audio output volume level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume percentage from 0 (silent) to 100 (maximum).",
                    }
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_quick_action",
            "description": "Execute quick OS utility actions such as screen lock, opening a website URL, or muting/unmuting audio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["lock_screen", "open_url", "mute", "unmute"],
                        "description": "The target action to execute.",
                    },
                    "target": {
                        "type": "string",
                        "description": "Target argument if applicable (e.g. URL to navigate when action is open_url).",
                    },
                },
                "required": ["action"],
            },
        },
    },
]

TOOL_MAPPING = {
    "open_application": open_application,
    "get_system_telemetry": get_system_telemetry,
    "set_volume": set_volume,
    "run_quick_action": run_quick_action,
}


def execute_tool(name: str, arguments: dict) -> dict:
    handler = TOOL_MAPPING.get(name)
    if not handler:
        return {"success": False, "error": f"Tool '{name}' is not registered."}
    try:
        return handler(**arguments)
    except Exception as e:
        return {"success": False, "error": str(e)}
