## WI-135 Incremental Review

### Verdict: PASS_WITH_NOTES

### Findings

**State inconsistency between `display` and `visible` in `action_toggle_help`**

`app.py:227` toggles `overlay.display` directly:

```python
overlay.display = not overlay.display
```

`HelpOverlay` (context file, `help_overlay.py:23-27`) declares `visible: reactive[bool] = reactive(False)` and uses a `watch_visible` watcher that syncs `self.display = value`. By bypassing the `visible` reactive and writing `display` directly, the reactive property is left permanently `False` even when the overlay is shown. Any code that reads `overlay.visible` — including `HelpOverlay.on_key` (line 38) and `action_hide_help` (line 52) — will see stale state. The toggle should write `overlay.visible = not overlay.visible` instead, letting the watcher drive `display`.

**Dead key handlers in `HelpOverlay` when overlay is hidden**

`help_overlay.py:33-40`: `on_key` and the `BINDINGS` declared on `HelpOverlay` (lines 18-21) can only fire when the widget has keyboard focus. A `Static` widget with `display: none` is never focused, so these handlers are permanently unreachable. This is not a bug introduced by WI-135 (it is in the context file), but `app.py` is the correct place to have already wired the `?` binding to `action_toggle_help`, which it does correctly.

All four acceptance criteria are structurally satisfied. The `display`/`visible` desync is a correctness defect but does not prevent the overlay from toggling visually; it does break any logic that later reads `overlay.visible`.

---

## WI-136 Incremental Review

### Verdict: PASS

### Findings

**Redundant `getattr` fallback in `_view_command`**

`cli/__init__.py:126`:

```python
url = getattr(args, "url", "http://localhost:8080")
```

The `--url` argument at line 101 declares `default="http://localhost:8080"`, so `args.url` is always present after `parse_args`. The `getattr` fallback is unreachable dead code. Use `args.url` directly.

All four acceptance criteria are met. The `view` subcommand is registered with `--url`, the no-args path calls `_run_viewer` at the default URL, and custom URLs are forwarded correctly.

---

## WI-137 Incremental Review

### Verdict: FAIL

### Findings

**Exit code from `_run_viewer()` is silently discarded on the no-args path**

`__main__.py:248-249`:

```python
asyncio.run(_run_viewer())
return
```

`_run_viewer` returns `int` (0 or 1). The return value of `asyncio.run(...)` is discarded; `main()` returns `None`. The caller at line 257 is:

```python
sys.exit(main())
```

`sys.exit(None)` always exits with code 0. If the daemon is not running and `_run_viewer` returns `1`, the process still exits 0. Monitoring tools and shell scripts that check the exit code of `hamlet` will receive a false success signal.

Fix: return the result.

```python
if not args:
    sys.exit(asyncio.run(_run_viewer()))
    return
```

Or equivalently keep the current structure but propagate:

```python
result = asyncio.run(_run_viewer())
sys.exit(result)
```

**`main()` return type inconsistency with `sys.exit` call site**

`__main__.py:242` declares `main()` with no return type annotation and `sys.exit(main())` on line 257 expects an integer-compatible value. The CLI `main()` in `cli/__init__.py:130` is declared `-> int`. The `__main__.main()` should be declared `-> None` and `sys.exit` should be removed from line 257 (since control for the args path already calls `sys.exit` internally at line 253), or `main()` should return `int` consistently. As written, `sys.exit(main())` on line 257 is always `sys.exit(None)` because neither code path inside `main()` returns an integer to the caller.

All three acceptance criteria are structurally present (`_run_app` is preserved, no-args dispatches to `_run_viewer`, args dispatch to `cli.main`), but the exit code propagation defect means criterion 1 is not correctly implemented — a failed `_run_viewer` invocation will not report failure to the calling shell.
