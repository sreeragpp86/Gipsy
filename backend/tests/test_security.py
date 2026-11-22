import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.security import (
    is_safe_external_url,
    is_admin_operation,
    verify_admin_password,
    AdminAuthManager,
)
from tools.os_tools import open_application, run_quick_action
from app.voice.audio_loop import AudioInputPipeline


def test_safe_external_url_validation():
    assert is_safe_external_url("https://www.google.com") is True
    assert is_safe_external_url("https://github.com/torvalds") is True
    assert is_safe_external_url("http://localhost:8000") is False
    assert is_safe_external_url("http://127.0.0.1:8000/admin") is False
    assert is_safe_external_url("http://0.0.0.0:8000") is False
    assert is_safe_external_url("http://192.168.1.1/router") is False
    assert is_safe_external_url("http://10.0.0.1/internal") is False
    assert is_safe_external_url("http://172.16.0.5/api") is False
    assert is_safe_external_url("file:///etc/passwd") is False
    assert is_safe_external_url("javascript:alert(1)") is False


def test_is_admin_operation_classification():
    assert is_admin_operation("open_application", {"app_name": "terminal"}) is True
    assert is_admin_operation("open_application", {"app_name": "iTerm2"}) is True
    assert is_admin_operation("open_application", {"app_name": "Activity Monitor"}) is True
    assert is_admin_operation("open_application", {"app_name": "Console"}) is True
    assert is_admin_operation("open_application", {"app_name": "Disk Utility"}) is True

    assert is_admin_operation("open_application", {"app_name": "Calculator"}) is False
    assert is_admin_operation("open_application", {"app_name": "Notes"}) is False
    assert is_admin_operation("open_application", {"app_name": "Calendar"}) is False
    assert is_admin_operation("open_application", {"app_name": "Safari"}) is False

    assert is_admin_operation("run_quick_action", {"action": "lock"}) is True
    assert is_admin_operation("run_quick_action", {"action": "lock_screen"}) is True
    assert is_admin_operation("run_quick_action", {"action": "mute"}) is False
    assert is_admin_operation("run_quick_action", {"action": "unmute"}) is False
    assert is_admin_operation("set_volume", {"level": 50}) is False
    assert is_admin_operation("get_system_telemetry", {}) is False

    assert is_admin_operation("run_quick_action", {"action": "open_url", "target": "http://127.0.0.1:8000"}) is True
    assert is_admin_operation("run_quick_action", {"action": "open_url", "target": "https://apple.com"}) is False


def test_flag_injection_and_path_traversal_guards():
    res1 = open_application("-a Terminal")
    assert res1["success"] is False
    assert "prohibited flag injection" in res1["error"]

    res2 = open_application("../../../bin/sh")
    assert res2["success"] is False
    assert "prohibited flag injection" in res2["error"]

    res3 = open_application("/Applications/Terminal.app")
    assert res3["success"] is False
    assert "prohibited flag injection" in res3["error"]


def test_ssrf_blocked_in_quick_action():
    res = run_quick_action("open_url", "http://127.0.0.1:9000/internal")
    assert res["success"] is False
    assert "restricted" in res["error"]


def test_admin_password_verification(monkeypatch):
    monkeypatch.setenv("GIPSY_ADMIN_PASSWORD", "gipsy-secure-token-2026")
    assert verify_admin_password("gipsy-secure-token-2026") is True
    assert verify_admin_password("wrong-password") is False
    assert verify_admin_password("") is False


@pytest.mark.anyio
async def test_admin_auth_manager_lifecycle(monkeypatch):
    monkeypatch.setenv("GIPSY_ADMIN_PASSWORD", "secret123")
    manager = AdminAuthManager()

    cid, fut = manager.create_challenge("open_application", {"app_name": "terminal"})
    assert cid in manager._pending
    assert not fut.done()

    success = manager.resolve_challenge(cid, "wrong")
    assert success is False
    assert await fut is False
    assert cid not in manager._pending

    cid2, fut2 = manager.create_challenge("open_application", {"app_name": "terminal"})
    success2 = manager.resolve_challenge(cid2, "secret123")
    assert success2 is True
    assert await fut2 is True

    cid3, fut3 = manager.create_challenge("run_quick_action", {"action": "lock"})
    manager.cancel_challenge(cid3)
    assert await fut3 is False


def test_websocket_admin_auth_submission(monkeypatch):
    monkeypatch.setenv("GIPSY_ADMIN_PASSWORD", "secret-test-pass")
    from app.security import admin_auth_manager

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        init_data = ws.receive_json()
        assert init_data["type"] == "connection_ack"

        cid, fut = admin_auth_manager.create_challenge("open_application", {"app_name": "terminal"})

        ws.send_json({
            "type": "admin_auth_submit",
            "challenge_id": cid,
            "password": "wrong-password",
        })
        res = ws.receive_json()
        assert res["type"] == "admin_auth_result"
        assert res["success"] is False
        assert "Incorrect password" in res["message"]

        cid2, fut2 = admin_auth_manager.create_challenge("open_application", {"app_name": "terminal"})
        ws.send_json({
            "type": "admin_auth_submit",
            "challenge_id": cid2,
            "password": "secret-test-pass",
        })
        res2 = ws.receive_json()
        assert res2["type"] == "admin_auth_result"
        assert res2["success"] is True
        assert "approved" in res2["message"]


def test_audio_loop_watchdog_limits():
    with patch("app.voice.audio_loop.SpeechToTextEngine"):
        pipeline = AudioInputPipeline(sample_rate=16000, block_size=1600, max_duration_sec=15.0)
        assert pipeline.max_duration_sec == 15.0
        assert pipeline.max_chunks == 150
