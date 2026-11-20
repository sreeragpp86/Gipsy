from app.llm import load_system_prompt
from tools.registry import OLLAMA_TOOLS, execute_tool


def test_system_prompt_loading():
    prompt = load_system_prompt()
    assert "Gipsy" in prompt
    assert "concise" in prompt.lower()


def test_ollama_tool_schemas():
    tool_names = [t["function"]["name"] for t in OLLAMA_TOOLS]
    assert "open_application" in tool_names
    assert "get_system_telemetry" in tool_names
    assert "set_volume" in tool_names
    assert "run_quick_action" in tool_names


def test_tool_telemetry():
    result = execute_tool("get_system_telemetry", {})
    assert result["success"] is True
    assert "telemetry" in result
    assert "cpu_usage" in result["telemetry"]
    assert "memory_used" in result["telemetry"]


def test_tool_volume():
    result = execute_tool("set_volume", {"level": 50})
    assert result["success"] is True
    assert result["level"] == 50


def test_tool_quick_action():
    result = execute_tool("run_quick_action", {"action": "unmute"})
    assert result["success"] is True


def test_unknown_tool():
    result = execute_tool("nonexistent_tool", {})
    assert result["success"] is False
    assert "not registered" in result["error"]
