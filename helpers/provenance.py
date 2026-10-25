"""Resolve effective plugin sources without installing files into the framework."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def manifest():
    return json.loads((ROOT / "UPSTREAM.json").read_text())


@lru_cache(maxsize=1)
def framework_root():
    from helpers import files
    return Path(files.get_base_dir()).resolve()


@lru_cache(maxsize=512)
def source_path(name):
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Source must be framework relative")
    mapped = manifest()["sources"].get(name)
    return ROOT / mapped if mapped else framework_root() / path


def effective_path(path):
    path = Path(path).resolve()
    try:
        relative = path.relative_to(framework_root()).as_posix()
    except ValueError:
        return path
    return source_path(relative)


def owned_source(path):
    path = Path(path).resolve()
    return path.is_relative_to(ROOT) or path.is_relative_to(framework_root())


def owned_function_hook(identity):
    return any(identity["class"].rsplit(".", 1)[-1] == item["class"]
               and identity["source"] == item["source"]
               for item in manifest().get("function_hooks", []))


def host_sources():
    return {name: path_digest(framework_root() / name)
            for name in manifest()["modules"]}


@lru_cache(maxsize=512)
def _digest(path, mtime, ctime, size, inode):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def path_digest(path):
    path = Path(path)
    info = path.stat()
    return _digest(str(path), info.st_mtime_ns, info.st_ctime_ns, info.st_size, info.st_ino)
