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


def test_websocket_cswsh_untrusted_origin_rejected():
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws", headers={"origin": "https://malicious-site.com"}):
            pass
    assert exc_info.value.code == 4003


def test_websocket_trusted_origin_accepted():
    with client.websocket_connect("/ws", headers={"origin": "http://localhost:5173"}) as ws:
        ack = ws.receive_json()
        assert ack["type"] == "connection_ack"


def test_websocket_auth_token_enforcement(monkeypatch):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    monkeypatch.setenv("GIPSY_AUTH_TOKEN", "test_ephemeral_token_42")

    # Reject without token
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws"):
            pass
    assert exc_info.value.code == 4001

    # Reject with invalid token
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws?token=wrong_token"):
            pass
    assert exc_info.value.code == 4001

    # Accept with valid token
    with client.websocket_connect("/ws?token=test_ephemeral_token_42") as ws:
        ack = ws.receive_json()
        assert ack["type"] == "connection_ack"

