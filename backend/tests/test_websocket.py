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
            "type": "set_state",
            "state": "EXECUTING_TOOL",
        })

        state_msg = ws.receive_json()
        assert state_msg["type"] == "state_change"
        assert state_msg["state"] == "EXECUTING_TOOL"

        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"
