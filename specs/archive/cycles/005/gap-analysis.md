## Summary

WI-208 through WI-212 are implemented and pass their acceptance criteria. Prior critical/significant gaps from Cycle 4 are fixed. However, five significant functional and correctness gaps remain in code that was not touched by this cycle's work items: wrong daemon error message, missing Settings field for zombie detection threshold, no request timeout on HTTP fetch methods, hardcoded daemon URL in CLI, and village expansion never founding new settlements despite Guiding Principle 5 requiring it. Two minor gaps are noted (protocol completeness, missing docs) but do not block convergence.

## Critical Gaps

None.

## Significant Gaps

### SG1: Wrong daemon error message in viewer path

- **File**: `src/hamlet/__main__.py:115`
- **Expected**: When the daemon is unreachable, the viewer prints a message telling the user how to start the daemon. The no-args entry point (`hamlet`) now launches the viewer (see `main()` line 145–150), so the daemon must be started with `hamlet daemon`.
- **Actual**: The error message at line 115 says `"Start the daemon first with: hamlet"`. Running `hamlet` launches the viewer, not the daemon. The message is wrong.
- **Impact**: Users following the error message will open another viewer, not start the daemon. Misleads every user who hits the health check failure path.
- **Suggested fix**: Change line 115 from `"hamlet"` to `"hamlet daemon"`.

### SG2: `zombie_threshold_seconds` not wired from Settings to AgentInferenceEngine

- **File**: `src/hamlet/app_factory.py:76`, `src/hamlet/config/settings.py`
- **Expected**: Both the despawn threshold and the zombie detection threshold should be configurable via `~/.hamlet/config.json`.
- **Actual**: `app_factory.py:76` passes `despawn_threshold_seconds=settings.zombie_despawn_seconds` to `AgentInferenceEngine` but does not pass `zombie_threshold_seconds`. `Settings` has no `zombie_threshold_seconds` field. The engine defaults to 300s for zombie detection, which cannot be changed without modifying source code.
- **Impact**: Users cannot tune zombie detection sensitivity. Silent misconfiguration — editing `config.json` for zombie behavior only affects despawn timing, not detection.
- **Suggested fix**: Add `zombie_threshold_seconds: int = 300` to `Settings`. Pass `zombie_threshold_seconds=settings.zombie_threshold_seconds` in `build_components`.

### SG3: No request timeout on `RemoteStateProvider.fetch_state` and `fetch_events`

- **File**: `src/hamlet/tui/remote_state.py:41-54`
- **Expected**: All HTTP calls from the viewer should have a bounded timeout to prevent the viewer from hanging if the daemon dies mid-response.
- **Actual**: `check_health` has `timeout=aiohttp.ClientTimeout(total=2)` (line 31). `fetch_state` (lines 41–44) and `fetch_events` (lines 50–54) have no timeout. If the daemon is killed mid-response or hangs, the viewer hangs indefinitely on the next poll.
- **Impact**: Viewer process hangs, requiring manual kill. Only affects the failure mode when the daemon crashes mid-response, but that is a common crash scenario.
- **Suggested fix**: Add `timeout=aiohttp.ClientTimeout(total=5)` to both `fetch_state` and `fetch_events`.

### SG4: CLI `hamlet view` and `main()` fallback hardcode `localhost:8080`, ignoring `Settings.mcp_port`

- **File**: `src/hamlet/cli/__init__.py:102, 145, 170`
- **Expected**: All code paths that construct the daemon URL should use `Settings.mcp_port`.
- **Actual**: Three locations hardcode `http://localhost:8080`:
  - Line 102: `view` parser `--url` default
  - Line 145: `_view_command` fallback `getattr(args, "url", "http://localhost:8080")`
  - Line 170: `main()` no-subcommand fallback
  `__main__.py:149` correctly reads `settings.mcp_port`; the CLI wrappers do not.
- **Impact**: Users who change `mcp_port` in `~/.hamlet/config.json` will find `hamlet view` still connects to port 8080 instead of the configured port.
- **Suggested fix**: Load `Settings` in `_view_command` and in `main()` fallback path; construct URL as `f"http://localhost:{settings.mcp_port}"`.

### SG5: Village expansion builds roads to new sites but never founds new settlements

- **File**: `src/hamlet/simulation/expansion.py:66-86`
- **Expected**: Guiding Principle 5 states: "Villages can expand, connect via roads, and found new settlements." When `check_village_expansion` finds a suitable site, a new village should be created at that site.
- **Actual**: `process_expansion` calls `create_road_between` to draw a road toward the expansion site but never calls any world-state method to create a new village at the destination. The expansion site is selected and a road is drawn, but no settlement is founded.
- **Impact**: Principle 5 violation. The world never grows beyond the initial per-project villages. The road leads nowhere. Multi-project scenarios produce disconnected villages instead of an interconnected settlement network.
- **Suggested fix**: After `create_road_between`, call `world_state.get_or_create_village` (or a new `found_village` method) to create a new village at `site`. If founding logic is not yet implemented on `WorldStateManager`, add a `found_village(center: Position, name: str)` method.

## Minor Gaps

### M1: `WorldStateProtocol` missing four method declarations

- **File**: `src/hamlet/protocols.py`
- **Issue**: `WorldStateProtocol` does not declare `get_agents_in_view`, `get_structures_in_view`, `update_structure`, or `create_structure`. These methods are called at runtime (`app.py:164,169`, `structure_updater.py:42`, `expansion.py:106`).
- **Impact**: No runtime failure in current paths (StructureUpdater runs only in daemon mode; expansion uses `hasattr` guard). Static type checkers will miss protocol violations.
- **Suggested fix**: Add the four method stubs to `WorldStateProtocol`. Add no-op stubs for `update_structure` and `create_structure` to `RemoteWorldState`.

### M2: `hamlet service install` absent from QUICKSTART.md and README.md

- **File**: `QUICKSTART.md`, `README.md`
- **Issue**: The `hamlet service install` command (macOS launchd integration) exists in the CLI but is not documented in either user-facing document.
- **Impact**: Users must discover this feature by running `hamlet service --help`.
- **Suggested fix**: Add a brief section on `hamlet service install/uninstall` in QUICKSTART.md.

## No Gaps Found In

- **WI-208 (zombie reset on load)**: `load_from_persistence` correctly forces `AgentState.ZOMBIE`. `startup()` seeds `zombie_since` from loaded ZOMBIE agents. Both paths tested.
- **WI-209 (WorldView initial paint)**: `on_mount` omits premature `resize()`. `on_resize` is the sole resize handler.
- **WI-210 (despawn infrastructure)**: `despawn_agent` removes agent from all data structures and queues a DB DELETE. Five tests cover the primary paths.
- **WI-211 (inference engine despawn)**: Session-end and zombie TTL despawn paths are both implemented and tested.
- **WI-212 (legend overlay)**: Overlay uses correct CSS layer, position, and display. Toggle via `/` works.
- **AgentUpdater ZOMBIE guard**: `if agent.state == AgentState.ZOMBIE: continue` is present. ZOMBIE lifecycle owned exclusively by `AgentInferenceEngine._update_zombie_states()`.
- **Protocol completeness (write-side stubs)**: `RemoteWorldState` implements `handle_event`, `get_or_create_project`, `get_or_create_session`, `get_or_create_agent`, `update_agent`, `add_work_units`, `get_agents_by_session`, `get_village_by_project`, `despawn_agent`. The gap in M1 is limited to four additional methods.
