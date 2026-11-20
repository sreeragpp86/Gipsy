from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_websocket_telemetry_and_command():
    with client.websocket_connect("/ws") as ws:
        ack = ws.receive_json()
        assert ack["type"] == "connection_ack"
        assert ack["state"] == "IDLE"
        assert "telemetry" in ack
        assert "cpu_usage" in ack["telemetry"]
        assert "memory_used" in ack["telemetry"]

        ws.send_json({
            "type": "text_command",
            "content": "Launch Safari and adjust brightness",
        })

        processing_state = ws.receive_json()
        assert processing_state["type"] == "state_change"
        assert processing_state["state"] == "PROCESSING"

        log_event = ws.receive_json()
        assert log_event["type"] == "log"
        assert "Launch Safari" in log_event["message"]

        tool_state = ws.receive_json()
        assert tool_state["type"] == "state_change"
        assert tool_state["state"] == "EXECUTING_TOOL"

        tool_start = ws.receive_json()
        assert tool_start["type"] == "tool_call"
        assert tool_start["status"] == "running"
