# Durable Execution for Agent Zero

A community plugin port of the journaled execution and recovery engine in
[Agent Zero PR #1968](https://github.com/agent0ai/agent-zero/pull/1968), based on
[`b77c1ae3`](https://github.com/TerminallyLazy/agent-zero/commit/b77c1ae3f6284b80ffe3054e5c0ad3c514dc3e1e).

Install it, enable it when wanted, and open **Recovery**. Local SQLite needs no
new Python package. No framework source file or framework requirement is written.
The distribution includes `.toggle-0`, so installation starts disabled.

## How it integrates

The plugin uses Agent Zero's existing `@extensible` start hooks for admission,
stop/reset, monologue, model calls, interventions, and JSON tool dispatch.
Before the original function runs, the plugin supplies its journaled result.

Some PR changes concern functions without an extension point. For those seams,
source-checked runtime adapters exchange implementations in memory while the
plugin is active. Existing function and class identities are preserved. Dynamic
API/tool/extension loaders apply the same adapters to their local module objects.
Every process-wide exchange has an undo record; disablement restores it.
The port also waits for local history compression at the checkpoint boundary
and retires completed loop markers before a new input, so repeated SQLite turns
do not try to serialize live tasks or references to a previous loop.

This is a substantial integration with core internals. The plugin packaging does
not make those boundaries disappear. The supported host sources are pinned in
`UPSTREAM.json`; a changed host requires a compatibility review, and activation
refuses it rather than guessing. This version targets the `ready` sources around
`505c0b4d` and `84b502f6`. It is experimental.

## Features

- Input identity and SQLite WAL/FULL journal admission before dispatch.
- Recorded provider/tool intents, known results, checkpoints, and recovery holds
  for outcomes that cannot be established safely.
- Native Responses and JSON tools, interventions, stop/reset, bounded child
  workflows, scheduler occurrence receipts, retention, and private backups.
- Revisioned typed chat plans, document conflicts, explicit recovery decisions,
  restore selection, and bounded inference retries through the recovery panel.
- The upstream PostgreSQL worker coordinator and encrypted portable-resource
  adapters: attachments/workspaces, shell/SSH, browser, MCP, memory, and background
  inference. Shared mode requires the deployment dependencies below.

The local and shared tiers retain the upstream safety limits. Unknown external
effects are held. A provider timeout is never evidence that its action did not
happen. Unreviewed third-party hooks and state may prevent automatic recovery.

## Install and enable

In **Plugins → Install → Git**, use this repository's URL. The plugin folder is
`usr/plugins/durable_execution`, with `plugin.yaml` at its root.

1. Stop running chats before enabling the plugin.
2. Enable **Durable Execution** globally. The default backend is local SQLite.
3. If framework files were updated since the server started, restart Agent Zero.
4. Open **Recovery** in the sidebar, or **Config → Recovery and documents**.
5. Start a new chat. Its subsequent work uses journaled admission.

Existing chat snapshots are retained. Shared PostgreSQL is a separate deployment:
local chat files are not automatically imported into shared history.

Settings live in the plugin's normal `config.json`. They include `backend`
(`local` or `postgres`), `retention_runs`, and `retention_days`. Backend changes
require a restart; changing a backend is not a data migration.
`interactive_shells` selects shared PTY sessions; turning it off uses batch
receipts. `ssh_known_hosts` points to a verified known_hosts file on each worker
for shared SSH recovery. SSH address, credentials, and timeouts stay in the normal
Code Execution settings. These options need no edits to the bundled plugin.

## PostgreSQL and remote resources

All workers need a dedicated PostgreSQL namespace, direct/session-pooled
connections, compatible sources and plugin settings, and these server environment variables:

```bash
A0_DURABILITY_POSTGRES_DSN='postgresql://…'
A0_DURABILITY_POSTGRES_NAMESPACE='agent_zero'
A0_DURABILITY_RESOURCE_KEY='…'
```

Keep credentials and the Fernet resource key outside settings and source. The
PostgreSQL driver is optional: `psycopg[binary]==3.3.6`. This plugin does not add it
to Agent Zero's shared requirements or install it for local SQLite use.

Host-browser and desktop recovery retain the upstream requirement for a matching
[a0-connector implementation](https://github.com/agent0ai/a0-connector/pull/29),
including its persistent private key and journal. An ordinary older companion
does not establish remote-effect recovery.

## Disable, update, uninstall

Stop active durable runs first. Disable before updating Agent Zero or a bundled
plugin, since a changed source pin intentionally prevents startup with the old adapters. If
startup refuses compatibility, stop the server and set this plugin to off:

```bash
rm -f usr/plugins/durable_execution/.toggle-1
touch usr/plugins/durable_execution/.toggle-0
```

Disable the plugin in **Plugins** to restore the
ordinary execution path and remove its adapters. Update and uninstall run the
same quiescence/cleanup boundary through `hooks.py`. Local detached actors are
stopped, including their child processes; an unacknowledged effect remains unknown
in the journal. Remote SSH commands and companion services retain their own
lifecycle: review/cancel them before disabling, and use their host controls if
cleanup cannot be acknowledged. Disabling does not declare an external action undone.
Successful updates reload the plugin and restore its enabled state. If an update
fails, disable it until the error is resolved.

Recovery data is preserved under `usr/plugin_data/durable_execution/` outside the
install checkout. Uninstall does not delete it or shared packages. Independent
backups, PostgreSQL WAL, replicas, host working copies, and external resources
retain their own custody. Disabled or uninstalled code cannot enforce its old
recovery holds; re-enable it to review unresolved work before repeating actions.

## Verification

Run from an Agent Zero framework environment with this repository available:

```bash
python scripts/test.py --framework /path/to/agent-zero --python /path/to/framework/python
```

The runner creates a disposable checkout and plugin installation, runs native
integration tests and the retained upstream engine tests separately, and removes
its fixture. It does not copy your `usr/` data or use a live recovery database.
PostgreSQL tests require an explicitly disposable `A0_TEST_DURABILITY_POSTGRES_DSN`.

`tests/test_plugin.py` exercises actual function-hook files and unchanged core
wrappers. The upstream unit fixtures deliberately suppress extension discovery;
their separate bootstrap binds the same dispatcher bodies for those tests.
Subprocess recovery tests retain real process termination. Two inherited timing
checks use explicit synchronization so slower admission does not cause a false
failure. `VALIDATION.md` records actual results and outstanding limits.

## Attribution

The recovery engine, adapters, UI state machine, and original tests come from the
MIT-licensed Agent Zero contribution by TerminallyLazy at the revision above.
`UPSTREAM.json` records source provenance and integration boundaries. The plugin
adds packaging, native hook dispatch, reversible source-checked integration,
plugin settings, lifecycle handling, and tests for those boundaries.

See [LICENSE](LICENSE). This community port is independent of upstream approval.
