import base64
import os
import platform
import subprocess
import httpx
from app.telemetry import get_system_telemetry as sample_telemetry

SCREENSHOT_PATH = "/tmp/gipsy_screen.png"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
VISION_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

APP_ALIASES = {
    "terminal": "Terminal",
    "finder": "Finder",
    "safari": "Safari",
    "notes": "Notes",
    "calculator": "Calculator",
    "calendar": "Calendar",
    "music": "Music",
    "settings": "System Settings",
    "preferences": "System Settings",
    "textedit": "TextEdit",
    "preview": "Preview",
    "messages": "Messages",
    "mail": "Mail",
}


def open_application(app_name: str) -> dict:
    clean_name = app_name.strip()
    if not clean_name or clean_name.startswith("-") or "/" in clean_name or "\\" in clean_name or ".." in clean_name:
        return {"success": False, "error": "Invalid application name or prohibited flag injection detected."}

    resolved_name = APP_ALIASES.get(clean_name.lower(), clean_name)
    current_os = platform.system()

    if current_os == "Darwin":
        try:
            res = subprocess.run(
                ["open", "-a", resolved_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return {
                    "success": True,
                    "message": f"Application '{resolved_name}' opened successfully.",
                    "app": resolved_name,
                }
            return {
                "success": False,
                "error": res.stderr.strip() or f"Could not launch application '{resolved_name}'.",
                "app": resolved_name,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "app": resolved_name}

    return {"success": False, "error": f"OS '{current_os}' not supported for app launching."}


def get_system_telemetry() -> dict:
    telemetry = sample_telemetry()
    return {
        "success": True,
        "telemetry": telemetry,
    }


def set_volume(level: int) -> dict:
    current_os = platform.system()
    clamped_level = max(0, min(100, int(level)))

    if current_os == "Darwin":
        try:
            script = f"set volume output volume {clamped_level}"
            res = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return {
                    "success": True,
                    "level": clamped_level,
                    "message": f"Audio volume adjusted to {clamped_level}%.",
                }
            return {"success": False, "error": res.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": f"OS '{current_os}' not supported for volume control."}


def run_quick_action(action: str, target: str = "") -> dict:
    current_os = platform.system()
    act = action.strip().lower()

    if current_os == "Darwin":
        try:
            if act in ("lock_screen", "lock"):
                subprocess.run(["open", "-a", "ScreenSaverEngine"], check=True)
                return {"success": True, "action": act, "message": "Screen lock initiated."}

            if act in ("open_url", "browse", "url") and target:
                clean_url = target if target.startswith(("http://", "https://")) else f"https://{target}"
                from app.security import is_safe_external_url
                if not is_safe_external_url(clean_url):
                    return {"success": False, "error": f"Target '{target}' is restricted. Navigation to internal or private IP hosts is blocked."}
                subprocess.run(["open", clean_url], check=True)
                return {"success": True, "action": act, "message": f"Navigating to {clean_url}."}

            if act == "mute":
                subprocess.run(["osascript", "-e", "set volume output muted true"], check=True)
                return {"success": True, "action": act, "message": "Master audio muted."}

            if act == "unmute":
                subprocess.run(["osascript", "-e", "set volume output muted false"], check=True)
                return {"success": True, "action": act, "message": "Master audio unmuted."}

            return {"success": False, "error": f"Unknown quick action '{action}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": f"OS '{current_os}' not supported."}


def capture_screen(question: str = "Describe what is currently visible on the screen.") -> dict:
    if platform.system() != "Darwin":
        return {"success": False, "error": "Screen capture is only supported on macOS."}

    clean_question = (question or "Describe what is currently visible on the screen.").strip()

    try:
        if os.path.exists(SCREENSHOT_PATH):
            os.remove(SCREENSHOT_PATH)

        subprocess.run(
            ["screencapture", "-x", SCREENSHOT_PATH],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if not os.path.isfile(SCREENSHOT_PATH) or os.path.getsize(SCREENSHOT_PATH) == 0:
            return {
                "success": False,
                "error": (
                    "Screen capture failed because macOS Screen Recording permission is missing. "
                    "Please enable it in System Settings -> Privacy & Security -> Screen Recording."
                ),
            }

        with open(SCREENSHOT_PATH, "rb") as img_file:
            encoded_image = base64.b64encode(img_file.read()).decode("utf-8")

        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Answer concisely in 1 to 2 plain sentences with no markdown or emojis, "
                            f"based strictly on this screenshot: {clean_question}"
                        ),
                        "images": [encoded_image],
                    }
                ],
                "stream": False,
                "think": False,
                "options": {"num_ctx": 8192, "temperature": 0.2},
            },
            timeout=45.0,
        )

        if resp.status_code != 200:
            return {
                "success": False,
                "error": f"Vision model returned HTTP {resp.status_code}.",
            }

        analysis = resp.json().get("message", {}).get("content", "").strip().replace("*", "")
        if not analysis:
            return {"success": False, "error": "Vision model returned an empty description."}

        return {
            "success": True,
            "question": clean_question,
            "analysis": analysis,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if os.path.exists(SCREENSHOT_PATH):
            try:
                os.remove(SCREENSHOT_PATH)
            except OSError:
                pass
