import asyncio
import getpass
import hmac
import ipaddress
import os
import platform
import subprocess
import uuid
from urllib.parse import urlparse

DISALLOWED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

ADMIN_APPS = {
    "terminal",
    "iterm",
    "iterm2",
    "alacritty",
    "kitty",
    "warp",
    "activity monitor",
    "disk utility",
    "console",
}


def is_safe_external_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname or ""
        if not host or host.lower() in DISALLOWED_HOSTS:
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


def is_admin_operation(tool_name: str, arguments: dict) -> bool:
    if tool_name == "open_application":
        app = str(arguments.get("app_name", "")).strip().lower()
        return app in ADMIN_APPS

    if tool_name == "run_quick_action":
        action = str(arguments.get("action", "")).strip().lower()
        if action in ("lock_screen", "lock"):
            return True
        if action in ("open_url", "browse", "url"):
            target = str(arguments.get("target", "")).strip()
            return not is_safe_external_url(target)

    return False


def verify_admin_password(password: str) -> bool:
    clean_pass = password.strip()
    if not clean_pass:
        return False

    env_pass = os.getenv("GIPSY_ADMIN_PASSWORD")
    if env_pass and hmac.compare_digest(clean_pass, env_pass):
        return True

    if platform.system() == "Darwin":
        try:
            user = getpass.getuser()
            res = subprocess.run(
                ["dscl", ".", "-authonly", user, clean_pass],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return res.returncode == 0
        except Exception:
            return False

    return False


class AdminAuthManager:
    def __init__(self):
        self._pending: dict[str, asyncio.Future] = {}

    def create_challenge(self, tool_name: str, arguments: dict) -> tuple[str, asyncio.Future]:
        challenge_id = uuid.uuid4().hex[:12]
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        future = loop.create_future()
        self._pending[challenge_id] = future
        return challenge_id, future

    def resolve_challenge(self, challenge_id: str, password: str) -> bool:
        future = self._pending.get(challenge_id)
        if not future or future.done():
            return False

        is_valid = verify_admin_password(password)
        if is_valid:
            future.set_result(True)
        else:
            future.set_result(False)

        self._pending.pop(challenge_id, None)
        return is_valid

    def cancel_challenge(self, challenge_id: str):
        future = self._pending.pop(challenge_id, None)
        if future and not future.done():
            future.set_result(False)


admin_auth_manager = AdminAuthManager()
