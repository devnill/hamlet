## WI-131 Incremental Review

### Verdict: PASS_WITH_NOTES

### Findings

- [SIGNIFICANT] `src/hamlet/cli/commands/init.py:27-32` — The bare `except Exception` swallows all errors from `Settings.load()` silently, including validation errors that would indicate a corrupt user config. If `Settings.load()` raises because the user's `~/.hamlet/config.json` has an invalid `mcp_port` value, the command silently falls back to port 8080 and writes a `server_url` that does not reflect the user's actual configuration. The fallback should log a warning so the user knows the generated `server_url` may be wrong: `except Exception as e: print(f"Warning: could not load settings ({e}), using default port 8080", file=sys.stderr)`.

- [SIGNIFICANT] No tests exist for `init_command`. The happy path (creates `.hamlet/config.json` with expected keys), the overwrite-prompt cancellation path, and the EOFError path are all untested. The existing test suite covers every other command module. Add `tests/test_cli_init.py` with at minimum: (1) fresh init creates a valid JSON file with `project_id`, `project_name`, and `server_url` keys; (2) running init a second time with input `"n"` does not overwrite the file; (3) EOFError during prompt cancels without modifying the file.

- [MINOR] `src/hamlet/cli/__init__.py:17-24` — The `epilog` examples block lists `hamlet install` and `hamlet uninstall` but omits `hamlet init`. A user reading `hamlet --help` gets no indication that `hamlet init` exists from the examples section (it does appear in the subcommand list, but the examples are inconsistent).

- [MINOR] `src/hamlet/cli/__init__.py:78` — The `init_parser` description says "Initialize a per-project Hamlet configuration file in the current working directory." but the `help` string is the shorter "Create .hamlet/config.json in the current directory". The help string is more precise and concrete; the description could match it for consistency.
