"""Read-only prerequisite checks; never installs or changes host networking."""
import importlib.util
import os
import platform
import shutil
import subprocess

from app.network.models import EnvironmentReport


def check_environment() -> EnvironmentReport:
    if platform.system() != "Linux":
        return EnvironmentReport(available=False, code="LINUX_REQUIRED")
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return EnvironmentReport(available=False, code="ROOT_REQUIRED")
    if importlib.util.find_spec("mininet") is None:
        return EnvironmentReport(available=False, code="MININET_NOT_INSTALLED")
    if any(shutil.which(tool) is None for tool in ("ovs-vsctl", "mnexec", "ip", "ping")):
        return EnvironmentReport(available=False, code="NETWORK_TOOLS_MISSING")
    try:
        result = subprocess.run(["ovs-vsctl", "show"], capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return EnvironmentReport(available=False, code="OVS_UNAVAILABLE")
    if result.returncode != 0:
        return EnvironmentReport(available=False, code="OVS_UNAVAILABLE")
    return EnvironmentReport(available=True, code="READY")
