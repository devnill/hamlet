# WI-137 Status: Add `hamlet daemon` to `__main__.py` dispatch

## Current `main()` Before Change

```python
def main() -> int:
    """Main entry point for the Hamlet TUI application.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    try:
        return asyncio.run(_run_app())
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\n\nGoodbye!", file=sys.stderr)
        return 0
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        err_msg = str(exc).lower()
        if "database" in err_msg or "sqlite" in err_msg:
            print("\nError: Database problem", file=sys.stderr)
            print("       The database may be locked by another Hamlet instance.", file=sys.stderr)
            print("       If Hamlet is already running, use that instance instead.", file=sys.stderr)
            print("       Otherwise, delete ~/.hamlet/world.db and restart.", file=sys.stderr)
        else:
            print(f"\nFatal error: {exc}", file=sys.stderr)
            print("\nFor help, see: https://github.com/yourusername/hamlet#troubleshooting", file=sys.stderr)
        return 1
```

## New `main()` After Change

```python
def main() -> None:
    """Main entry point for the Hamlet TUI application."""
    args = sys.argv[1:]

    if not args:
        # No subcommand: launch viewer mode (backward compatible)
        asyncio.run(_run_viewer())
        return

    # Delegate to CLI for subcommand dispatch (daemon, init, install, view, etc.)
    from hamlet.cli import main as cli_main
    sys.exit(cli_main(args))
```

## `_run_app()` Preservation

`_run_app()` was **preserved** (left untouched). A grep of `tests/` for `_run_app` returned no matches, but per the work item instructions only `main()` was modified. `_run_app()` remains in place at lines 30–191 of `__main__.py`.

## Summary

- `hamlet` with no args now calls `asyncio.run(_run_viewer())` instead of `asyncio.run(_run_app())`
- `hamlet <subcommand>` delegates to `hamlet.cli.main` via `sys.exit(cli_main(args))`
- The `console_script` entry point (`hamlet = "hamlet.__main__:main"`) continues working unchanged
- `_run_app()` and `_run_viewer()` are both untouched
