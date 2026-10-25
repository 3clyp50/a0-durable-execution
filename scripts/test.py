#!/usr/bin/env python3
"""Verify the plugin against a disposable archive of a framework checkout."""
import argparse
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", type=Path, required=True)
    parser.add_argument("--python", default="python")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    assert (source / "plugin.yaml").is_file()
    with tempfile.TemporaryDirectory(prefix="a0-durable-test-") as directory:
        checkout = Path(directory)
        archive = subprocess.check_output(["git", "-C", str(args.framework), "archive", "HEAD"])
        with tarfile.open(fileobj=io.BytesIO(archive)) as content:
            content.extractall(checkout, filter="data")
        plugin = checkout / "usr/plugins/durable_execution"
        shutil.copytree(source, plugin, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".pytest_cache", "*.pyc", "config.json", ".toggle-1", "state", ".env*"))
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(filter(None, [str(checkout), environment.get("PYTHONPATH")]))
        for suite in ("tests/test_plugin.py", "tests/upstream"):
            subprocess.run([args.python, "-m", "pytest", str(plugin / suite), "-q", "--tb=short"],
                           cwd=checkout, env=environment, check=True)
        node = shutil.which("node")
        if node:
            subprocess.run([node, "--test", str(plugin / "tests/upstream/test_durability_ui.mjs")], check=True)
        else:
            print("Node.js unavailable: UI state tests were not run.")


if __name__ == "__main__":
    main()
