import psutil


def get_system_telemetry() -> dict:
    vm = psutil.virtual_memory()
    batt = psutil.sensors_battery()

    battery_data = None
    if batt is not None:
        battery_data = {
            "percent": batt.percent,
            "power_plugged": batt.power_plugged,
        }

    return {
        "cpu_usage": round(psutil.cpu_percent(interval=None), 1),
        "memory_used": round(vm.used / (1024**3), 1),
        "memory_total": round(vm.total / (1024**3), 1),
        "battery": battery_data,
    }
