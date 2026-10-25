"""Close this installation's detached local actors before removing its guards."""
from pathlib import Path
import os

import psutil

from usr.plugins.durable_execution.helpers.provenance import ROOT, framework_root

_ACTORS = {
    "usr.plugins.durable_execution.helpers.durable.background",
    "usr.plugins.durable_execution.helpers.durable.execution",
    "usr.plugins.durable_execution.helpers.durable.interactive",
    "usr.plugins.durable_execution.helpers.durable.mcp_broker",
    "usr.plugins.durable_execution.adapters.browser.session_broker",
}


def _owned(args, cwd):
    if Path(cwd).resolve() != framework_root() or len(args) < 3:
        return False
    return (args[1] == "-m" and args[2] in _ACTORS or
            Path(args[1]).resolve() == ROOT / "adapters/code_execution/durable_pty.py")


def stop_local_actors():
    processes = {}
    for process in psutil.process_iter(["pid", "cmdline", "cwd", "status"]):
        try:
            info = process.info
            if (info["pid"] != os.getpid() and info["status"] != psutil.STATUS_ZOMBIE
                    and info["cwd"] and _owned(info["cmdline"] or [], info["cwd"])):
                for child in [process, *process.children(recursive=True)]:
                    processes[child.pid] = child
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    for process in processes.values():
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, remaining = psutil.wait_procs(list(processes.values()), timeout=3)
    for process in remaining:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    _, remaining = psutil.wait_procs(remaining, timeout=3)
    if any(process.status() != psutil.STATUS_ZOMBIE for process in remaining if process.is_running()):
        raise RuntimeError("A local durable actor could not be stopped; plugin remains enabled")
