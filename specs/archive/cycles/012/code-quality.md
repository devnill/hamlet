## Verdict: Fail

There are two significant issues: re-install silently breaks with a confusing launchctl error, and all XML values in the plist template are interpolated without escaping, which produces a malformed plist for any path containing `&`, `<`, or `>`.

## Critical Findings

None.

## Significant Findings

### S1: `_install` does not guard against re-installing an already-loaded service
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/service.py:95`
- **Issue**: `_install` calls `launchctl bootstrap` without first checking whether the service is already loaded. On macOS, `launchctl bootstrap` on an already-loaded label returns a non-zero exit code with an opaque I/O error message (e.g., "Bootstrap failed: 5: Input/output error"). The function prints this raw launchctl error and exits 1, giving the user no guidance.
- **Impact**: Running `hamlet service install` a second time (after it was already installed and running) produces a confusing error and leaves the system in an inconsistent state: the new plist has been written to disk but the service is still running the old one.
- **Suggested fix**: At the start of `_install`, after finding the executable, call `_service_is_running()`. If `True`, print a message explaining the service is already installed and running, then either return 0 or call `_uninstall` before proceeding (depending on desired semantics — a "reinstall" that unloads and reloads would be safe). At minimum, the error branch at line 96 should check whether the error string contains "already loaded" and emit a clear message:
  ```python
  if rc != 0:
      if "already" in output.lower() or "5:" in output:
          print("Service is already installed. Run `hamlet service uninstall` first.")
      else:
          print(f"Error: launchctl load failed: {output}")
      sys.exit(1)
  ```

### S2: XML injection in plist template via unescaped path values
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/service.py:86-90`
- **Issue**: `hamlet_exe`, `log_path`, and `err_log_path` are interpolated directly into the XML plist using Python string `.format()`. None of these values are XML-escaped. A path containing `&` (e.g., a home directory under a volume path that happens to include an ampersand, or an unusual username) produces a malformed plist that `launchd` will silently reject or parse incorrectly.
- **Impact**: The plist file is written to disk in a broken state. `launchctl bootstrap` either fails with a parse error or silently loads a service with wrong arguments. The user sees a confusing error with no indication the plist is malformed.
- **Suggested fix**: Use `xml.sax.saxutils.escape()` on each interpolated value before writing the plist:
  ```python
  from xml.sax.saxutils import escape
  plist_content = PLIST_TEMPLATE.format(
      hamlet_executable=escape(hamlet_exe),
      log_path=escape(log_path),
      err_log_path=escape(err_log_path),
  )
  ```
  Alternatively, use `plistlib` to generate the plist programmatically, which handles all encoding automatically.

## Minor Findings

### M1: `Settings` mock target in daemon tests is fragile
- **File**: `/Users/dan/code/hamlet/tests/test_cli_daemon.py:44`
- **Issue**: Three tests patch `"hamlet.config.settings.Settings"` rather than `"hamlet.cli.commands.daemon.Settings"`. This works only because `daemon_command` defers its `from hamlet.config.settings import Settings` import to inside the function body. If that import were ever hoisted to module level, all three tests would silently stop patching the right object and pass vacuously.
- **Suggested fix**: Change the patch target to `"hamlet.cli.commands.daemon.Settings"` in `test_daemon_port_conflict_hamlet_exits`, `test_daemon_port_conflict_other_exits`, and `test_daemon_port_free_proceeds`.

### M2: `sys.exit()` used instead of `return` in service subcommand error paths, inconsistent with other commands
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/service.py:44,78,98,129,138,155,173,209`
- **Issue**: All error paths in service subcommands call `sys.exit(1)` directly instead of returning a non-zero exit code. Every other command in the codebase returns an integer and lets `main()` in `__init__.py` call `sys.exit()`. The `main()` exception wrapper at line 172-178 of `__init__.py` is unreachable for service errors, which also means the service commands cannot be tested by checking their return values — tests must catch `SystemExit`.
- **Suggested fix**: Replace `sys.exit(1)` with `return 1` throughout `service.py` and let `main()` handle the process exit. This aligns with the pattern used by `install`, `uninstall`, and `daemon` commands.

### M3: No test for re-install (already-loaded) scenario
- **File**: `/Users/dan/code/hamlet/tests/test_cli_service.py`
- **Issue**: `TestInstallCommand` has no test case for calling `install` when the service is already running. Given that S1 above is a known failure mode, this gap means the broken behavior is not caught by the test suite.
- **Suggested fix**: Add a test that patches `_service_is_running` to return `True` and verifies that `install` either succeeds gracefully or prints a clear "already installed" message rather than the raw launchctl error.

### M4: `_launchctl` merges stderr and stdout in the wrong order for error reporting
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/service.py:61`
- **Issue**: `output` is built as `result.stderr + result.stdout`. For `launchctl`, error messages go to stderr. Prepending stderr to stdout is correct for display, but naming the variable `output` and printing it as a single blob means that on a failure, any stdout prefix (which is usually empty from launchctl) appears before the actual error. This is harmless in practice but the concatenation order is the reverse of what you would expect (stdout before stderr is the conventional display order).
- **Suggested fix**: Reverse the concatenation to `result.stdout + result.stderr` so that any primary output precedes diagnostic messages, consistent with how terminal output is normally read.

## Suggestions

- Consider using `plistlib.dumps()` (stdlib, available since Python 3.4) to generate the plist content instead of the XML string template. This eliminates both the XML injection risk (S2) and the need to maintain the template string manually.
- The `_check_port_conflict` function in `daemon.py` has an inherent TOCTOU gap: the port could be claimed between the check at line 147 and `asyncio.run` at line 166. The existing `OSError` handler in `_run_daemon` covers this, but the two code paths emit different error messages for the same condition. The conflict-detection error (lines 149-163) prints to stdout without a `file=sys.stderr` argument, while the `OSError` handler correctly writes to stderr. This inconsistency should be unified.
