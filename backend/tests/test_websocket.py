import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app

client = TestClient(app)


def test_websocket_telemetry_and_ping():
    with client.websocket_connect("/ws") as ws:
        ack = ws.receive_json()
        assert ack["type"] == "connection_ack"
        assert ack["state"] == "IDLE"
        assert "telemetry" in ack
        assert "cpu_usage" in ack["telemetry"]
        assert "memory_used" in ack["telemetry"]

        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_websocket_cswsh_untrusted_origin_rejected():
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws", headers={"origin": "https://malicious-site.com"}):
            pass
    assert exc_info.value.code == 4003


@pytest.mark.parametrize(
    "origin",
    ["tauri://localhost", "http://tauri.localhost", "http://localhost:5173"],
)
def test_websocket_trusted_origins_accepted(origin):
    with client.websocket_connect("/ws", headers={"origin": origin}) as ws:
        ack = ws.receive_json()
        assert ack["type"] == "connection_ack"


def test_websocket_auth_token_enforcement(monkeypatch):
    monkeypatch.setenv("GIPSY_AUTH_TOKEN", "test_ephemeral_token_42")

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws"):
            pass
    assert exc_info.value.code == 4001

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws?token=wrong_token"):
            pass
    assert exc_info.value.code == 4001

    with client.websocket_connect("/ws?token=test_ephemeral_token_42") as ws:
        ack = ws.receive_json()
        assert ack["type"] == "connection_ack"
