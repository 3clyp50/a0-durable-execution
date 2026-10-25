"""Source-checked, reversible adapters for framework seams without hooks.

Decorated functions use native start extensions. Other existing callables keep
their identity: only their implementation is exchanged while the plugin runs.
The framework checkout is never written, and every exchange has an undo record.
"""
from __future__ import annotations

import ast
import copy
import functools
import hashlib
import importlib
import inspect
import threading
from pathlib import Path
from types import FunctionType

from usr.plugins.durable_execution.helpers.provenance import ROOT, framework_root, manifest

_MISSING = inspect.Signature.empty
_LOCK = threading.RLock()
_ANCHOR = "_durable_execution_plugin"


def state():
    from helpers import plugins
    return getattr(plugins, _ANCHOR, None)


def _set_state(value):
    from helpers import plugins
    if value is None:
        if hasattr(plugins, _ANCHOR):
            delattr(plugins, _ANCHOR)
    else:
        setattr(plugins, _ANCHOR, value)


def _assign(owner, name, value, undo):
    previous = (owner.get(name, _MISSING) if isinstance(owner, dict) else
                getattr(owner, name, _MISSING) if isinstance(owner, FunctionType) else vars(owner).get(name, _MISSING))
    undo.append((owner, name, previous))
    if isinstance(owner, dict):
        owner[name] = value
    else:
        setattr(owner, name, value)


def _restore(undo):
    for owner, name, previous in reversed(undo):
        if isinstance(owner, dict):
            if previous is _MISSING:
                owner.pop(name, None)
            else:
                owner[name] = previous
        elif previous is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, previous)


def _exec(nodes, namespace, filename):
    local = {}
    source = _source_tree(filename)
    futures = [node for node in source.body if isinstance(node, ast.ImportFrom) and node.module == "__future__"]
    tree = ast.Module(body=[*futures, *copy.deepcopy(nodes)], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), filename, "exec", dont_inherit=True), namespace, local)
    return local


@functools.lru_cache(maxsize=64)
def _parse(filename, mtime, ctime, size):
    return ast.parse(Path(filename).read_text())


def _source_tree(filename):
    info = Path(filename).stat()
    return _parse(filename, info.st_mtime_ns, info.st_ctime_ns, info.st_size)


def _function(descriptor):
    if isinstance(descriptor, (classmethod, staticmethod)):
        descriptor = descriptor.__func__
    return inspect.unwrap(descriptor) if inspect.isfunction(descriptor) else descriptor


def _exchange(old, new, undo):
    old, new = _function(old), _function(new)
    if not isinstance(old, FunctionType) or not isinstance(new, FunctionType):
        return False
    if old.__code__.co_freevars != new.__code__.co_freevars:
        raise RuntimeError(f"Unsupported closure change: {old.__qualname__}")
    for name in ("__code__", "__defaults__", "__kwdefaults__", "__annotations__", "__doc__"):
        _assign(old, name, getattr(new, name), undo)
    return True


def _attribute_nodes(tree, wanted):
    selected = []
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(target, ast.Name) and target.id in wanted for target in targets):
            selected.append(node)
    return selected


def _apply(module, relative, entry, current):
    filename = str(ROOT / entry["path"])
    tree = _source_tree(filename)
    namespace = vars(module)
    definitions = {node.name: node for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    # Imports use the host namespace so existing function globals keep working.
    imported = _exec([node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
                      and not (isinstance(node, ast.ImportFrom) and node.module == "__future__")], namespace, filename)
    for name, value in imported.items():
        _assign(namespace, name, value, current["undo"])
    for op in entry["operations"]:
        name, node = op["name"], definitions[op["name"]]
        if op["kind"] == "definition":
            value = _exec([node], namespace, filename)[name]
            original = namespace.get(name, _MISSING)
            if op.get("native"):
                current["replacements"][relative + ":" + name] = _function(value)
            elif original is _MISSING or not _exchange(original, value, current["undo"]):
                _assign(namespace, name, value, current["undo"])
            continue
        cls = namespace[name]
        children = [child for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name in op["methods"]]
        skeleton = ast.ClassDef(name=name, bases=[], keywords=[], decorator_list=[],
                                body=children or [ast.Pass()])
        replacement = _exec([skeleton], namespace, filename)[name]
        for method in op["methods"]:
            value = vars(replacement)[method]
            original = vars(cls).get(method, _MISSING)
            if method in op.get("native_methods", []):
                current["replacements"][relative + ":" + name + "." + method] = _function(value)
            elif original is _MISSING or not _exchange(original, value, current["undo"]):
                _assign(cls, method, value, current["undo"])
        values = _exec(_attribute_nodes(node, op["attributes"]), namespace, filename)
        annotations = values.pop("__annotations__", {})
        for attr, value in values.items():
            _assign(cls, attr, value, current["undo"])
        if annotations:
            # Pydantic copies inherited fields; rebuild each existing subclass.
            from pydantic import BaseModel
            if issubclass(cls, BaseModel):
                from pydantic.fields import FieldInfo
                pending = [cls]
                while pending:
                    target = pending.pop()
                    pending.extend(target.__subclasses__())
                    updated = dict(target.model_fields)
                    for attr, annotation in annotations.items():
                        updated[attr] = FieldInfo(annotation=eval(annotation, namespace) if isinstance(annotation, str) else annotation,
                                                  default=values.get(attr))
                    _assign(target, "__pydantic_fields__", updated, current["undo"])
                    # Preserve compiled validators/serializers for exact rollback.
                    for compiled in ("__pydantic_core_schema__", "__pydantic_validator__", "__pydantic_serializer__"):
                        _assign(target, compiled, getattr(target, compiled), current["undo"])
                    target.model_rebuild(force=True)
            _assign(cls, "__annotations__", {**getattr(cls, "__annotations__", {}), **annotations}, current["undo"])
    globals_ = _exec(_attribute_nodes(tree, entry["globals"]), namespace, filename)
    for name, value in globals_.items():
        if name != "__annotations__":
            _assign(namespace, name, value, current["undo"])
    if relative == "helpers/task_scheduler.py":
        from pydantic import BaseModel
        for target in list(namespace.values()):
            if isinstance(target, type) and issubclass(target, BaseModel) and target.__module__ == module.__name__:
                for compiled in ("__pydantic_core_schema__", "__pydantic_validator__", "__pydantic_serializer__"):
                    _assign(target, compiled, getattr(target, compiled), current["undo"])
                target.model_rebuild(force=True)


def preflight():
    failures = []
    for relative, entry in manifest()["modules"].items():
        source = framework_root() / relative
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() not in entry["accepted_sources"]:
            failures.append(relative)
    if failures:
        raise RuntimeError("Durable Execution needs a compatibility review for: " + ", ".join(failures))


def _quiescent():
    from agent import AgentContext
    if any(context.task and context.task.is_alive() for context in AgentContext.all()):
        raise RuntimeError("Stop running chats before enabling, disabling, or updating Durable Execution")


def activate():
    """Install all adapters atomically; a failure restores the original process."""
    with _LOCK:
        if state():
            return state()
        preflight()
        _quiescent()
        current = {"undo": [], "replacements": {}, "active": False}
        _set_state(current)
        try:
            from helpers import modules
            original_import = modules.import_module

            @functools.wraps(original_import)
            def import_module(path):
                absolute = Path(modules.get_abs_path(path)).resolve()
                try:
                    relative = absolute.relative_to(framework_root()).as_posix()
                except ValueError:
                    return original_import(path)
                entry = manifest()["modules"].get(relative)
                if entry and entry["dynamic"]:
                    module = original_import(path)
                    _apply(module, relative, entry, {"undo": [], "replacements": {}})
                    return module
                return original_import(path)

            _assign(modules, "import_module", import_module, current["undo"])
            entries = list(manifest()["modules"].items())
            entries.sort(key=lambda item: (0 if item[0].startswith("helpers/") else
                                           1 if "/helpers/" in item[0] else
                                           2 if item[0] == "agent.py" else 3, item[0]))
            for relative, entry in entries:
                module = importlib.import_module(relative[:-3].replace("/", "."))
                _apply(module, relative, entry, current)
            current["active"] = True
            return current
        except BaseException:
            _restore(current["undo"])
            _set_state(None)
            raise


def dispatch(key, data):
    current = state()
    if not current or not current["active"]:
        raise RuntimeError("Durable Execution is enabled but its adapters are unavailable")
    data["result"] = current["replacements"][key](*data["args"], **data["kwargs"])


async def dispatch_async(key, data):
    current = state()
    if not current or not current["active"]:
        raise RuntimeError("Durable Execution is enabled but its adapters are unavailable")
    data["result"] = await current["replacements"][key](*data["args"], **data["kwargs"])


def start():
    from usr.plugins.durable_execution.hooks import prepare_backend
    prepare_backend()
    current = activate()
    from usr.plugins.durable_execution.helpers.durable import runtime
    if current.get("owner") is not None:
        runtime._service = current["owner"]
        return current["owner"]
    owner = runtime.initialize()
    if owner is None or owner.failed:
        raise RuntimeError("Durable Execution storage is unavailable; execution remains held")
    current["owner"] = owner
    return owner


def recover():
    from usr.plugins.durable_execution.helpers.durable.runtime import service
    owner = service()
    if owner:
        owner.recover()


def deactivate():
    """Require quiescence before removing execution guards; preserve the journal."""
    with _LOCK:
        current = state()
        if not current:
            return
        from usr.plugins.durable_execution.helpers.durable import runtime
        owner = current.get("owner") or runtime.service()
        if owner and owner.driving:
            raise RuntimeError("Stop active durable runs before disabling or updating Durable Execution")
        _quiescent()
        from usr.plugins.durable_execution.helpers.lifecycle import stop_local_actors
        stop_local_actors()
        if owner:
            owner.close()
            runtime._service = None
        current["active"] = False
        _restore(current["undo"])
        _set_state(None)


def preserve_modules():
    import sys
    current = state()
    if current:
        current["modules"] = {key: value for key, value in sys.modules.items()
                              if key == "usr.plugins.durable_execution" or key.startswith("usr.plugins.durable_execution.")}


def restore_modules():
    import sys
    current = state()
    if current:
        for key, value in current.get("modules", {}).items():
            sys.modules[key] = value
            parent, _, name = key.rpartition(".")
            if parent in sys.modules:
                setattr(sys.modules[parent], name, value)
