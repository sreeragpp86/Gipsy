import os
from unittest.mock import MagicMock, patch
from app.llm import load_system_prompt
from tools.os_tools import SCREENSHOT_PATH, capture_screen
from tools.registry import AVAILABLE_TOOLS, OLLAMA_TOOLS, execute_tool


def test_system_prompt_loading():
    prompt = load_system_prompt()
    assert "Gipsy" in prompt
    assert "concise" in prompt.lower()
    assert "capture_screen" in prompt


def test_ollama_tool_schemas():
    tool_names = [t["function"]["name"] for t in OLLAMA_TOOLS]
    assert "open_application" in tool_names
    assert "get_system_telemetry" in tool_names
    assert "set_volume" in tool_names
    assert "run_quick_action" in tool_names
    assert "capture_screen" in tool_names
    assert "capture_screen" in AVAILABLE_TOOLS


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


def test_capture_screen_missing_permission():
    with patch("tools.os_tools.platform.system", return_value="Darwin"), patch(
        "tools.os_tools.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="could not create image from display")
        res = capture_screen("What error is shown?")
        assert res["success"] is False
        assert "Screen Recording" in res["error"]
        assert not os.path.exists(SCREENSHOT_PATH)


def test_capture_screen_success_and_cleanup():
    def fake_screencapture(*args, **kwargs):
        with open(SCREENSHOT_PATH, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nfake_png_bytes")
        return MagicMock(returncode=0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "A terminal displaying a pytest error."}}

    with patch("tools.os_tools.platform.system", return_value="Darwin"), patch(
        "tools.os_tools.subprocess.run", side_effect=fake_screencapture
    ), patch("tools.os_tools.httpx.post", return_value=mock_resp) as mock_post:
        res = capture_screen("What is on my screen?")
        assert res["success"] is True
        assert "terminal" in res["analysis"].lower()
        assert mock_post.called
        assert not os.path.exists(SCREENSHOT_PATH)
