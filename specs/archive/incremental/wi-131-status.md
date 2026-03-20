# WI-131 Status: Add `hamlet init` CLI command

## Files Created

- `src/hamlet/cli/commands/init.py` — new `init_command(args: Namespace) -> int` function that creates `.hamlet/config.json` in the cwd with `project_id` (random UUID), `project_name` (cwd basename), and `server_url` derived from `Settings.mcp_port` (fallback: 8080). Prompts for overwrite confirmation if the config already exists; cancels on 'n' or non-interactive (EOFError).

## Files Modified

- `src/hamlet/cli/__init__.py` — added `init` subparser in `create_parser()` and a `_init_command` deferred-import shim function (same pattern as `_daemon_command`).
- `src/hamlet/cli/commands/__init__.py` — added `"init"` to `__all__`.

## Dispatch Pattern Used

Deferred import shim: the subparser registers `set_defaults(func=_init_command)` where `_init_command` is a module-level shim that imports and calls `hamlet.cli.commands.init.init_command` only when the subcommand is actually invoked. This matches the existing `_daemon_command` pattern and avoids eager imports at parser construction time.
