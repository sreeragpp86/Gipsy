import platform
import subprocess
from app.telemetry import get_system_telemetry as sample_telemetry

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
