## Verdict: Fail

The parent count is correct and the name assertion fires correctly in dev, but the assertion crashes in any installed-package deployment, and the `settings` variable is silently shadowed mid-function causing the MCP port to always fall back to 8080 after the first assignment is overwritten.

## Critical Findings

### C1: `settings` variable silently shadowed — MCP port always falls back to 8080 after line 371
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/install.py:329-371`
- **Issue**: `settings` is first assigned the result of `Settings.load()` (line 329-331) and its `.mcp_port` is used on line 363. Then on line 371 `settings = load_settings(settings_path)` overwrites it with a plain `dict`. This is fine for the dict use below, but if any code after line 371 ever tries to access `settings.mcp_port` it will raise `AttributeError`. More immediately: the `settings` value used on line 363 is the `Settings` object, but if the `try` block on lines 327-331 silently swallows an exception and sets `settings = None`, `mcp_port` falls back to 8080 with no warning. The two `settings` uses (ORM object vs raw dict) sharing one name make this fragile and error-prone. Use distinct names, e.g. `hamlet_settings` for the `Settings` object and `claude_settings` for the Claude Code dict.

### C2: Bare `assert` in `get_hooks_dir()` crashes the process in installed-package layout
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/install.py:62-64`
- **Issue**: When hamlet is installed as a package (e.g., via `pip install hamlet`), `Path(__file__)` resolves to something like `/usr/local/lib/python3.12/site-packages/hamlet/cli/commands/install.py`. Five `.parent` traversals land at `site-packages/`, whose `.name` is `"site-packages"`, not `"hamlet"`. The `assert` then raises `AssertionError` and terminates the process with a traceback instead of falling through to the `try` block at line 71 that is designed to handle exactly this case.
- **Impact**: `hamlet install` is completely broken for any pip-installed deployment. The fallback path (lines 71-78) is never reached.
- **Suggested fix**: Replace the assert with a conditional check so the fallback is allowed to run:
  ```python
  project_root = Path(__file__).parent.parent.parent.parent.parent
  if project_root.name == "hamlet":
      hooks_dir = project_root / "hooks"
      if hooks_dir.exists():
          return hooks_dir.resolve()
  ```
  If you still want an assertion for dev, guard it: `assert "HAMLET_DEV" not in os.environ or project_root.name == "hamlet"`, but a conditional is cleaner.

## Significant Findings

### S1: No tests for `get_hooks_dir()` or any function in `install.py`
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/install.py` (no corresponding test file)
- **Issue**: The acceptance criterion "Path resolution verified with assertion or test" is only partially satisfied — the assertion exists but fails in installed-package mode (see C2). There is no test file exercising `get_hooks_dir()`, `install_hooks_to_settings()`, `remove_hooks_from_settings()`, or `install_command()`. The entire module is untested.
- **Impact**: Regressions in path resolution will not be caught automatically.
- **Suggested fix**: Add `tests/test_cli_install.py` with at minimum:
  - A test that monkeypatches `Path(__file__)` to a dev-tree layout and asserts `get_hooks_dir()` returns the correct path.
  - A test that monkeypatches to an installed-package layout and asserts the fallback is reached (not an AssertionError).
  - A test for `install_hooks_to_settings()` and `remove_hooks_from_settings()` with round-trip correctness.

## Minor Findings

### M1: `validate_mcp_server_running` broad `except Exception` swallows unexpected errors silently
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/install.py:106-107`
- **Issue**: The final `except Exception` catch returns a user-facing string but discards the exception type, making it hard to distinguish a connection timeout from a programming error (e.g., a `TypeError` in the health-URL construction).
- **Suggested fix**: Log the exception type in the returned message or re-raise unexpected non-network exceptions.

### M2: `create_backup` silently drops errors from both copy attempts
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/install.py:200-209`
- **Issue**: Both `except Exception` blocks pass silently, so if backup fails for a non-obvious reason (e.g., disk full) the caller only sees `None` and emits a single-line warning. The underlying `OSError` is discarded.
- **Suggested fix**: At minimum log `str(e)` in both inner except blocks before returning `None`.

## Unmet Acceptance Criteria

- [ ] Path resolution verified with assertion or test — The assertion satisfies this only for a source-tree checkout. It raises `AssertionError` (crashing the process) for any pip-installed layout, and no automated test covers either case.
