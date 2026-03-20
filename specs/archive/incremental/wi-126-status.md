# WI-126 Status — Create daemon mode entry point

## What was implemented

- **New file** `src/hamlet/cli/commands/daemon.py`
  - `_run_daemon(port)` async coroutine that starts PersistenceFacade, WorldStateManager,
    AgentInferenceEngine, all simulation subsystems (AgentUpdater, StructureUpdater,
    ExpansionManager, AnimationManager), MCPServer, EventProcessor, and SimulationEngine in
    the same order as `_run_app()` in `__main__.py`.
  - No TUI imports (no HamletApp, no ViewportManager).
  - File logging added to `~/.hamlet/hamlet.log` via a `FileHandler` attached to the root
    logger before any components are started.
  - SIGINT and SIGTERM are handled by setting a module-level `_shutdown_requested` flag; the
    main loop polls the flag with `asyncio.sleep(0.5)` and breaks when set.
  - Shutdown in reverse startup order (GP-7), mirroring `__main__.py` `finally` block.
  - `daemon_command(args)` synchronous entry point wraps `asyncio.run(_run_daemon(port))`.

- **Modified file** `src/hamlet/cli/__init__.py`
  - Added `daemon` subparser with `--port` (optional int, overrides `settings.mcp_port`).
  - Registered `_daemon_command` shim (deferred import) via `set_defaults(func=...)`,
    consistent with how `install` and `uninstall` are registered.

## Deviations from spec

- **Dispatch style**: The spec showed adding a `command == "daemon"` branch in `main()`.
  The existing CLI dispatches via `parsed_args.func(parsed_args)` (argparse `set_defaults`
  pattern), not via an `if/elif` chain.  The daemon subcommand was registered the same way
  (using a `_daemon_command` shim for deferred import) so the dispatch path is consistent
  with the rest of the CLI without modifying `main()`.

- **`animation_manager` not passed to MCPServer**: The spec mentioned "Pass `animation_manager`
  to MCPServer", but `MCPServer.__init__` does not accept an `animation_manager` parameter
  (WI-125 changes were not present in the actual source).  The daemon was written to match the
  real constructor signature (`world_state`, `port`) — no deviation from running code.

## Files modified/created

| Action   | Path |
|----------|------|
| Created  | `src/hamlet/cli/commands/daemon.py` |
| Modified | `src/hamlet/cli/__init__.py` |
