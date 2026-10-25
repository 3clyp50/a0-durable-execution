"""Plugin boundaries use real framework function dispatch, not patched bodies."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent import Agent, AgentConfig, AgentContext, UserMessage
from helpers import extension, modules, persist_chat, responses_history
from helpers.defer import DeferredTask
from helpers.tool import Tool
from helpers.llm_result import LLMResult
from usr.plugins.durable_execution.helpers import bridge, provenance


@pytest.fixture
def active():
    bridge.activate()
    yield bridge.state()
    bridge.deactivate()


def test_activation_and_disable_preserve_host_files_and_function_identity():
    sources = {name: hashlib.sha256((provenance.framework_root() / name).read_bytes()).hexdigest()
               for name in provenance.manifest()["modules"]}
    original = Agent.monologue
    original_body = Agent.monologue.__wrapped__.__code__
    bridge.activate()
    assert Agent.monologue is original
    assert Agent.monologue.__wrapped__.__code__ is original_body
    assert hasattr(DeferredTask, "result_async") and hasattr(Tool, "documents")
    bridge.deactivate()
    assert Agent.monologue is original and not hasattr(Tool, "documents")
    assert not hasattr(DeferredTask, "result_async")
    assert not hasattr(Agent, "_call_model_with_stream")
    assert sources == {name: hashlib.sha256((provenance.framework_root() / name).read_bytes()).hexdigest()
                       for name in sources}


def test_unreviewed_source_refuses_activation_before_any_change(monkeypatch, tmp_path):
    (tmp_path / "agent.py").write_text("changed = True\n")
    monkeypatch.setattr(bridge, "framework_root", lambda: tmp_path)
    with pytest.raises(RuntimeError, match="compatibility review"):
        bridge.activate()
    assert bridge.state() is None and not hasattr(Tool, "documents")


def test_partial_adapter_failure_rolls_back(monkeypatch):
    original = bridge._apply
    count = 0

    def fail(module, relative, entry, state):
        nonlocal count
        original(module, relative, entry, state)
        count += 1
        if count == 3:
            raise RuntimeError("synthetic activation failure")

    monkeypatch.setattr(bridge, "_apply", fail)
    with pytest.raises(RuntimeError, match="synthetic activation"):
        bridge.activate()
    assert bridge.state() is None and not hasattr(DeferredTask, "result_async")


def test_scheduler_receipts_survive_container_serialization(active):
    from helpers.task_scheduler import AdHocTask, SchedulerTaskList
    task = AdHocTask(name="Example", system_prompt="", prompt="", durable_run_id="retained")
    value = SchedulerTaskList(tasks=[task]).model_dump(mode="json")
    restored = SchedulerTaskList.model_validate(value)
    assert restored.tasks[0].durable_run_id == "retained"


def test_dynamic_tool_loader_uses_the_audited_plugin_source(active):
    from usr.plugins.durable_execution.helpers.durable.codec import identity
    from usr.plugins.durable_execution.helpers.durable.replay import AUDITED_TOOLS
    from tools.response import ResponseTool
    loaded = modules.load_classes_from_file("tools/response.py", Tool)[0]
    assert loaded is not ResponseTool and loaded.replay == "safe"
    assert (loaded.__name__, identity(loaded)["source"]) in AUDITED_TOOLS


def test_recovery_allowlists_match_reviewed_relocated_tool_sources(active):
    from usr.plugins.durable_execution.helpers.durable.codec import identity
    from usr.plugins.durable_execution.helpers.durable.replay import AUDITED_TOOLS, AUDITED_WORKFLOWS
    from usr.plugins.durable_execution.tools.durable_plan import DurablePlan
    from tools.call_subordinate import Delegation
    from tools.parallel import ParallelTool
    assert (DurablePlan.__name__, identity(DurablePlan)["source"]) in AUDITED_TOOLS
    for cls in (Delegation, ParallelTool):
        assert (cls.__name__, identity(cls)["source"]) in AUDITED_WORKFLOWS


@pytest.mark.asyncio
async def test_local_history_compression_finishes_before_checkpoint(active, monkeypatch):
    from extensions.python.message_loop_end import _10_organize_history as history
    from usr.plugins.durable_execution.helpers.durable import runtime
    data = {}
    agent = SimpleNamespace(get_data=data.get, set_data=lambda key, value: data.update({key: value}))
    monkeypatch.setattr(runtime, "current", lambda _: SimpleNamespace(owner=SimpleNamespace(distributed=False)))
    compress = AsyncMock(return_value=False)
    monkeypatch.setattr(history, "compress_history", compress)
    await history.OrganizeHistory(agent).execute()
    compress.assert_awaited_once_with(agent)
    assert data[history.DATA_NAME_TASK] is None


def test_digest_cache_detects_same_size_replacement(tmp_path):
    source = tmp_path / "module.py"
    source.write_text("first")
    before = provenance.path_digest(source)
    source.write_text("other")
    assert before != provenance.path_digest(source)


def test_active_legacy_chat_prevents_switching_execution_paths(monkeypatch):
    task = SimpleNamespace(is_alive=lambda: True)
    monkeypatch.setattr(AgentContext, "all", lambda: [SimpleNamespace(task=task)])
    with pytest.raises(RuntimeError, match="Stop running chats"):
        bridge.activate()
    assert bridge.state() is None


def test_actor_cleanup_matches_only_this_installation():
    from usr.plugins.durable_execution.helpers.lifecycle import _owned
    args = ["python", "-m", "usr.plugins.durable_execution.helpers.durable.background", "job.json"]
    assert _owned(args, str(provenance.framework_root()))
    assert not _owned(args, "/another/framework")
    assert not _owned(["python", "unrelated.py", args[2]], str(provenance.framework_root()))


def test_sqlite_install_does_not_install_packages(monkeypatch):
    from usr.plugins.durable_execution import hooks
    from usr.plugins.durable_execution.helpers import config
    monkeypatch.setattr(config, "values", lambda: {"backend": "local"})
    monkeypatch.setattr(hooks.subprocess, "run", lambda *a, **kw: pytest.fail("SQLite needs no installation"))
    hooks.prepare_backend()


@pytest.mark.parametrize("enabled", [False, True])
def test_install_resumes_only_a_previously_enabled_plugin(monkeypatch, enabled):
    from helpers import plugins
    from usr.plugins.durable_execution import hooks
    calls = []
    for name in ("preflight", "start", "recover"):
        monkeypatch.setattr(hooks.bridge, name, lambda name=name: calls.append(name))
    monkeypatch.setattr(hooks, "prepare_backend", lambda: calls.append("backend"))
    monkeypatch.setattr(plugins, "get_enabled_plugins", lambda agent: ["durable_execution"] if enabled else [])
    hooks.install()
    assert calls == ["preflight", "backend"] + (["start", "recover"] if enabled else [])


def test_update_releases_cached_plugin_code_after_cleanup(monkeypatch):
    from helpers import cache, plugins
    from usr.plugins.durable_execution import hooks
    calls = []
    monkeypatch.setattr(hooks.bridge, "deactivate", lambda: calls.append("stop"))
    monkeypatch.setattr(modules, "purge_namespace", lambda name: calls.append(name))
    monkeypatch.setattr(cache, "remove", lambda area, key: calls.append((area, key)))
    hooks.pre_update()
    assert calls == ["stop", "usr.plugins.durable_execution", (plugins.HOOKS_CACHE_AREA, "durable_execution")]


def test_postgres_installs_missing_driver_only(monkeypatch):
    from usr.plugins.durable_execution import hooks
    from usr.plugins.durable_execution.helpers import config
    monkeypatch.setattr(config, "values", lambda: {"backend": "postgres"})
    monkeypatch.setattr(hooks.importlib.util, "find_spec", lambda name: None)
    calls = []
    monkeypatch.setattr(hooks.subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)))
    hooks.prepare_backend()
    assert calls == [([hooks.sys.executable, "-m", "pip", "install", "psycopg[binary]==3.3.6"], {"check": True})]


@pytest.mark.parametrize("invalid", [{"interactive_shells": "yes"}, {"ssh_known_hosts": True}])
def test_execution_settings_validate_types(monkeypatch, invalid):
    from usr.plugins.durable_execution.helpers import config
    monkeypatch.setattr(config, "get_plugin_config", lambda *a, **kw: invalid)
    with pytest.raises(ValueError):
        config.values()


def test_execution_options_come_from_this_plugin(active, monkeypatch):
    from usr.plugins.durable_execution.helpers import config
    from plugins._code_execution.tools import code_execution_tool as tool
    monkeypatch.setattr(config, "values", lambda: {"interactive_shells": False, "ssh_known_hosts": "/verified/known_hosts"})
    monkeypatch.setattr(tool.plugins, "get_plugin_config", lambda *a, **kw: {"ssh_enabled": "no", "ssh_pass": "unchanged-fixture"})
    values = tool._get_config(None)
    assert values["durability_ssh_known_hosts"] == "/verified/known_hosts"
    assert values["durability_interactive"] is False
    assert values["ssh_pass"] == "unchanged-fixture"


@pytest.fixture
def native(active, tmp_path, monkeypatch):
    # Isolate unrelated provider hooks, retaining actual plugin extension files
    # and the framework's unmodified @extensible wrappers.
    def hooks(point, *args, **kwargs):
        folder = provenance.ROOT / "extensions/python" / point
        return modules.load_classes_from_folder(str(folder), "*.py", extension.Extension) if folder.is_dir() else []

    monkeypatch.setattr(extension, "_get_extension_classes", hooks)
    monkeypatch.setattr(AgentContext, "_contexts", {})
    monkeypatch.setattr(persist_chat, "CHATS_FOLDER", str(tmp_path / "chats"))
    monkeypatch.setattr(responses_history, "prepare_call", lambda *args: {})
    monkeypatch.setattr("helpers.state_monitor_integration.mark_dirty_all", lambda **kwargs: None)
    monkeypatch.setattr("helpers.state_monitor_integration.mark_dirty_for_context", lambda *args, **kwargs: None)
    mask = SimpleNamespace(mask_values=lambda value: value)
    monkeypatch.setattr("helpers.secrets.get_secrets_manager", lambda context: mask)
    monkeypatch.setattr("helpers.log.get_secrets_manager", lambda context: mask)
    monkeypatch.setattr("helpers.mcp_handler.MCPConfig.get_instance", lambda: SimpleNamespace(get_tool=lambda *args: None))
    monkeypatch.setattr(Agent, "prepare_prompt", AsyncMock(return_value=[]))
    monkeypatch.setattr(Agent, "parse_prompt", lambda self, name, **kwargs: kwargs.get("message", ""))
    monkeypatch.setattr(Agent, "read_prompt", lambda *args, **kwargs: "Synthetic prompt")
    from tools.response import ResponseTool
    monkeypatch.setattr(Agent, "get_tool", lambda self, name, method, args, message, loop_data:
                        ResponseTool(self, name, method, args, message, loop_data))
    requests = []

    class SyntheticModel:
        model_name = "synthetic"
        kwargs = {"a0_api_mode": "chat_completions"}

        async def unified_turn(self, **kwargs):
            requests.append(kwargs)
            return LLMResult.from_chat(response=json.dumps({"tool_name": "response", "tool_args": {"text": "Done"}}))

    monkeypatch.setattr(Agent, "get_chat_model", lambda self: SyntheticModel())
    from usr.plugins.durable_execution.helpers.durable import runtime
    owner = runtime.RecoveryService((tmp_path / "journal").resolve())
    monkeypatch.setattr(runtime, "_service", owner)
    context = AgentContext(AgentConfig(mcp_servers=""), id="plugin-native-test")
    yield SimpleNamespace(context=context, owner=owner, requests=requests)
    for ctx in AgentContext.all():
        if ctx.task:
            ctx.task.kill()
    owner.close()


def test_real_native_admission_model_and_tool_hooks(native):
    task = native.context.communicate(UserMessage("Hello", id="stable-input"))
    assert task.result_sync(timeout=10) == "Done"
    run, = native.owner.sync("list_runs")
    assert run["status"] == "completed"
    assert run["checkpoint"]["environment"]["plugin_integration"]["helpers/bridge.py"] == provenance.path_digest(provenance.ROOT / "helpers/bridge.py")
    assert native.owner.sync("get_call", run["run_id"], "model:0")["status"] == "completed"
    assert native.context.communicate(UserMessage("Hello", id="stable-input")).result_sync(timeout=5) == "Done"
    assert len(native.requests) == 1


def test_next_input_retires_completed_previous_loop_markers(native):
    context = native.context
    assert context.communicate(UserMessage("First", id="first-loop")).result_sync(timeout=10) == "Done"
    previous = context.agent0.loop_data
    context.agent0.set_data("_recall_memories_loop", previous)
    context.agent0.set_data("_plugin._infection_check.mono", id(previous))
    assert context.communicate(UserMessage("Next", id="next-loop")).result_sync(timeout=10) == "Done"
    assert context.agent0.loop_data is not previous
    assert context.agent0.get_data("_recall_memories_loop") is None
    assert len(native.requests) == 2


def test_other_plugin_refresh_preserves_the_existing_recovery_service(native, monkeypatch):
    import importlib
    from helpers import plugins
    from usr.plugins.durable_execution.helpers.durable import runtime
    monkeypatch.setattr(plugins, "clear_plugin_cache", lambda *args: None)
    before = bridge.state()
    plugins.after_plugin_change(["another_community_plugin"], python_change=True, frontend_reload=False)
    assert bridge.state() is before
    assert importlib.import_module(runtime.__name__) is runtime
    assert runtime.service() is native.owner


def test_native_unknown_provider_outcome_is_held_without_replay(native, monkeypatch):
    from usr.plugins.durable_execution.helpers.durable import runtime

    async def interrupted(**kwargs):
        native.requests.append(kwargs)
        raise runtime.RecoveryHeld("synthetic lost acknowledgment")

    native.context.agent0.get_chat_model = lambda: SimpleNamespace(model_name="synthetic", kwargs={}, unified_turn=interrupted)
    result = native.context.communicate(UserMessage("Hello", id="uncertain-input")).result_sync(timeout=10)
    assert "attention" in result
    run, = native.owner.sync("list_runs")
    assert run["status"] == "attention"
    native.context.communicate(UserMessage("Hello", id="uncertain-input")).result_sync(timeout=5)
    assert len(native.requests) == 1
