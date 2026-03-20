# WI-136 Status: Update default CLI behavior for no-subcommand case

## Changes Made

**File modified:** `src/hamlet/cli/__init__.py`

### 1. Registered `view` subcommand (`create_parser`)

Added a `view` subparser after the existing `daemon` parser with a `--url` argument (default `http://localhost:8080`) and `set_defaults(func=_view_command)`.

### 2. Added `_view_command` shim

Added a new thin shim function `_view_command(args)` that reads `args.url` and calls `asyncio.run(_run_viewer(url))`, consistent with the existing shim pattern used by `_init_command` and `_daemon_command`.

### 3. Changed no-subcommand branch in `main()`

Replaced the `parser.print_help(); return 0` fallback with a direct call to `_run_viewer("http://localhost:8080")` via `asyncio.run`.

## How Each Case Is Handled

- **`hamlet` (no args):** `parsed_args.command` is `None`; the no-subcommand branch in `main()` imports and runs `_run_viewer("http://localhost:8080")` directly.
- **`hamlet view`:** Dispatches to `_view_command` via `parsed_args.func`; calls `_run_viewer("http://localhost:8080")`.
- **`hamlet view --url http://localhost:9090`:** Dispatches to `_view_command`; `args.url` is `"http://localhost:9090"`, so `_run_viewer("http://localhost:9090")` is called.
- **`hamlet --help`:** argparse handles `--help` before subcommand dispatch; unaffected.
- **All other subcommands** (`install`, `uninstall`, `init`, `daemon`): dispatch via `parsed_args.func` as before; unaffected.
