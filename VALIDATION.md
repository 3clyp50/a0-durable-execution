# Validation

Verified on 2026-10-25 against Agent Zero
`84b502f6f30e4f4363b609bed3b9887f17abe8fc` using the Python 3.12 framework runtime.
The live target was the Dockerized Agent Zero at `localhost:32081`.

| Check | Result |
| --- | --- |
| Native plugin boundaries | 22 passed |
| Retained upstream engine suite | 332 passed, 34 subtests passed; no skips |
| Browser UI state and retry identities | 30 passed |
| Undefined Python names (`ruff check --select F821`) | Passed |
| Host source integrity | No tracked Agent Zero source changes |

The engine suite used disposable PostgreSQL 17.11, psycopg 3.3.6, installed
Chromium, and isolated companion sources from PR #29 at
`030dd05cf1eed0691f21a1f45a6d5979678b4a61`. It exercised SQLite and PostgreSQL,
real SIGKILL recovery, independent worker chat projections, shell/SSH/PTYs,
Chromium profile state and an acknowledged browser POST, MCP delivery and
credential isolation, host-browser/computer receipts, memory, scheduler,
documents, retention, backups, and API access checks. Synthetic effects and
loopback provider endpoints were used for the destructive recovery scenarios.

A complete packaged-runner pass was followed by targeted reruns for the final
integration-source metadata and plugin-owned execution settings. The native
tests use actual function-hook files and unchanged framework wrappers. The
upstream fixtures intentionally suppress hook discovery, so their separate
bootstrap binds the same dispatcher bodies. Process requesters explicitly
activate the plugin as a real enabled framework worker would.

Live checks completed:

- Normal ZIP install, enable, disable, uninstall, and reinstall; journal data
  survived uninstall outside the plugin checkout.
- A configured model and the response tool completed a journaled turn.
- Two successive turns completed in the same chat. The agent read the plan
  through `durable_plan` and returned its saved title and item count.
- Repeating the same input ID returned the recorded response.
- A server restart preserved the completed response and saved plan.
- The UI saved a revisioned plan and rendered on desktop and at 390px width.
- POST without a CSRF token returned 403.
- Ordinary chat completed after disabling, with no journal entry for that input.
- SQLite installed no PostgreSQL driver in the live environment.

The installed plugin is left **disabled**. Installation does not opt the user in.

## Limits

This is experimental and pinned to reviewed framework sources. It uses native
hooks plus reversible in-memory adapters for 35 existing modules. Disable it
before updating the framework or bundled plugins. Source, integration settings,
or unknown hook/state changes can require a recovery hold.

The shared-worker tests ran on one Linux machine with independent processes and
state directories. Separate physical hosts, production PostgreSQL infrastructure,
and real Windows/macOS desktop actions were not tested. Companion protocol tests
do not establish compatibility with an older installed companion.

Unknown external effects remain unknown. Disabling removes the recovery guards;
it does not undo remote actions or cancel remote services. See README cleanup
and custody notes before repeating interrupted work.
