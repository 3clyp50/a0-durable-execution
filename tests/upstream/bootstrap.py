"""Bindings for the upstream suites that deliberately suppress function hooks."""
import importlib
from usr.plugins.durable_execution.helpers import bridge


def activate():
    bridge.activate()
    undo = []
    for key, replacement in bridge.state()["replacements"].items():
        module_path, qualname = key.split(":", 1)
        target = importlib.import_module(module_path[:-3].replace("/", "."))
        for segment in qualname.split("."):
            target = getattr(target, segment)
        bridge._exchange(target, replacement, undo)
    return undo
