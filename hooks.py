"""Normal plugin lifecycle; SQLite requires no dependency installation."""
import importlib.util
import subprocess
import sys

from usr.plugins.durable_execution.helpers import bridge


def prepare_backend():
    from usr.plugins.durable_execution.helpers.config import values
    if values()["backend"] == "postgres" and importlib.util.find_spec("psycopg") is None:
        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg[binary]==3.3.6"], check=True)
        importlib.invalidate_caches()


def install():
    bridge.preflight()
    prepare_backend()


def pre_update():
    bridge.deactivate()


def uninstall():
    bridge.deactivate()
