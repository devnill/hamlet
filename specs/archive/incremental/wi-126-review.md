## WI-126 Incremental Review

### Verdict: FAIL

### Findings

- [SIGNIFICANT] `animation_manager` created but not passed to `MCPServer`
  File: `src/hamlet/cli/commands/daemon.py:102-106`
  An `AnimationManager()` instance is created at line 102 and stored in `animation_manager`, but
  `MCPServer` is instantiated at line 106 as `MCPServer(world_state=world_state, port=port)` — the
  `animation_manager` keyword argument is omitted. `MCPServer.__init__` (server.py:31) accepts and
  stores `animation_manager`, and `_handle_state` (server.py:110) calls
  `serialize_state(self._world_state, self._animation_manager)` where `self._animation_manager` will
  be `None`. The `/hamlet/state` HTTP endpoint will always receive a `None` animation manager,
  producing incomplete or incorrect state serialization. WI-125 confirmed the parameter exists in the
  real constructor. Fix: change line 106 to
  `MCPServer(world_state=world_state, port=port, animation_manager=animation_manager)`.

- [SIGNIFICANT] No tests for the daemon command
  Files: `tests/` (no `test_daemon*.py` found)
  There are no tests for `daemon_command`, `_run_daemon`, or the `daemon` subparser registration in
  `__init__.py`. The existing test suite covers all other CLI commands and backend components. At
  minimum, tests should cover: the `--port` override resolving correctly, subparser registration
  (i.e., `hamlet daemon --help` exits 0 and `hamlet daemon` invokes the right function), SIGINT/SIGTERM
  setting `_shutdown_requested`, and the shutdown sequence running even when a component raises.

- [MINOR] `Settings.load()` called twice — once in `daemon_command` and once in `_run_daemon`
  Files: `src/hamlet/cli/commands/daemon.py:214` and `src/hamlet/cli/commands/daemon.py:70`
  `daemon_command` calls `Settings.load()` to resolve the port fallback, then passes `port` into
  `_run_daemon`, which calls `Settings.load()` a second time for the remaining settings. Two separate
  reads of the config file mean the two `Settings` instances could differ if the file is modified
  between calls. The simpler fix is to load settings once in `daemon_command`, pass the full
  `Settings` object (or all needed fields) into `_run_daemon`, and drop the second `Settings.load()`
  inside the coroutine.

- [MINOR] Module-level `_shutdown_requested` flag is never reset before a new run
  File: `src/hamlet/cli/commands/daemon.py:14`
  `_shutdown_requested` is a module-level global initialized to `False` at import time. If
  `asyncio.run(_run_daemon(...))` is called a second time in the same process (as happens in
  integration tests that invoke the function directly), the flag will already be `True` from the
  previous run and `_run_daemon` will exit immediately in the `while not _shutdown_requested` loop.
  Fix: set `_shutdown_requested = False` at the start of `_run_daemon` (before the loop), or pass
  shutdown state as a local `asyncio.Event` instead of a global flag.

- [MINOR] CLI help epilog omits `daemon` example
  File: `src/hamlet/cli/__init__.py:19-23`
  The epilog shown by `hamlet --help` lists only `hamlet install` and `hamlet uninstall`. Adding a
  `hamlet daemon` example line is consistent with the existing style and helps discoverability.
