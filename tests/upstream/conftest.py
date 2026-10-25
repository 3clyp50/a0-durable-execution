"""Run the retained upstream engine tests in their original hook-free fixtures.

Those fixtures intentionally replace extension discovery. Bind the same native
hook bodies for this suite; tests/test_plugin.py checks real discovery separately.
"""
import os

from usr.plugins.durable_execution.helpers import bridge
from usr.plugins.durable_execution.helpers.provenance import framework_root
from usr.plugins.durable_execution.tests.upstream.bootstrap import activate

_test_undo = activate()
_old_pythonpath = os.environ.get("PYTHONPATH")
os.environ["PYTHONPATH"] = os.pathsep.join(filter(None, [str(framework_root()), _old_pythonpath]))


def pytest_sessionfinish(session, exitstatus):
    bridge._restore(_test_undo)
    bridge.deactivate()
    if _old_pythonpath is None:
        os.environ.pop("PYTHONPATH", None)
    else:
        os.environ["PYTHONPATH"] = _old_pythonpath
