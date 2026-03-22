# Review Manifest — Cycle 001/refine-13 (Full Review)

| ID | Title | File Scope (key files) | Verdict | Findings (C/S/M) | Review Path |
|---|---|---|---|---|---|
| 220 | Verify handle_event enum dispatch | manager.py, test_world_state_manager.py | Pass | 0/0/0 | archive/incremental/220-verify-enum-dispatch.md |
| 221 | Verify EVENT_SCHEMA string tool_output | validation.py, event_processor.py, tests | Pass | 0/0/0 | archive/incremental/221-verify-bash-string-tool-output.md |
| 222 | stop_reason behavioral differentiation | inference/engine.py, test_inference_engine.py | Pass | 0/0/0 | archive/incremental/222-verify-stop-reason-differentiation.md |
| 223 | Event pipeline parametrized coverage | test_event_processor.py, test_world_state_manager.py | Fail→Fixed | 0/1/0 | archive/incremental/223-verify-event-pipeline-coverage.md |
| 224 | TUI/persistence/install test coverage | test_tui_world_view.py, test_cli_install.py, test_persistence_facade.py | Fail→Fixed | 0/1/0 | archive/incremental/224-verify-tui-persistence-coverage.md |
| 225 | get_nearest_village_to method | manager.py, protocols.py, remote_world_state.py | Fail→Fixed | 1/1/1 | archive/incremental/225-verify-nearest-village.md |
| 226 | StatusBar village name | status_bar.py, test_tui_status_bar.py | Pass | 0/0/1 | archive/incremental/226-verify-status-bar-village-name.md |
| 227 | Structure size_tier data model | types.py, migrations.py, loader.py, writer.py, serializers.py | Pass | 0/0/0 | archive/incremental/227-verify-size-tier-data-model.md |
| 228 | Size tier calculation in StructureUpdater | structure_updater.py, config.py, manager.py, protocols.py | Fail→Fixed | 1/2/1 | archive/incremental/228-verify-size-tier-calculation.md |
| 229 | Multi-cell footprint + agent displacement | grid.py, manager.py, remote_world_state.py, tests | Fail→Fixed | 2/3/2 | archive/incremental/229-verify-multi-cell-footprint.md |
| 230 | Multi-cell WorldView rendering | world_view.py, test_tui_world_view.py | Pass | 0/0/0 | archive/incremental/230-verify-multi-cell-rendering.md |
| 231 | RemoteWorldState size_tier deserialization | remote_world_state.py, test_remote_world_state.py | Pass | 0/0/1 | archive/incremental/231-verify-remote-world-state-size-tier.md |

---

# Review Manifest — Cycle 006 (Full Review)

| id | title | file scope | verdict | findings (C/S/M) | review path |
|---|---|---|---|---|---|
| 213 | Fix daemon error message and CLI port hardcoding | __main__.py, cli/__init__.py | Pass | 0/0/2 | archive/incremental/213-fix-daemon-error-message-and-cli-port-hardcoding.md |
| 214 | Wire zombie_threshold_seconds from Settings | settings.py, app_factory.py | Pass | 0/0/2 | archive/incremental/214-wire-zombie-threshold-seconds-from-settings.md |
| 215 | Add request timeout to RemoteStateProvider fetch methods | remote_state.py | Fail→Pass | 0/0/1 | archive/incremental/215-add-request-timeout-to-remote-state-provider-fetch-methods.md |
| 216 | Village expansion founds new settlements | expansion.py, manager.py | Fail→Pass | 0/1/2 | archive/incremental/216-village-expansion-founds-new-settlements.md |

---

# Review Manifest — Cycle 005 (Full Review)

| id | title | file scope | verdict | findings (C/S/M) | review path |
|---|---|---|---|---|---|
| 002 | Event Schema and Validation | validation.py | None | — | — |
| 003 | Event Notification Handler | handlers.py, __init__.py | None | — | — |
| 004 | MCP Tools and Resources | handlers.py | None | — | — |
| 005 | MCPServer Integration | server.py, __init__.py | None | — | — |
| 011 | InternalEvent Data Structure | __init__.py, internal_event.py | None | — | — |
| 012 | Sequence Generator | sequence_generator.py, __init__.py | None | — | — |
| 013 | Event Router Interface | event_router.py, __init__.py | None | — | — |
| 014 | Event Processor | event_processor.py, __init__.py | None | — | — |
| 021 | Core Types and Data Structures | __init__.py, types.py | None | — | — |
| 022 | Agent Inference Engine Skeleton | engine.py, __init__.py | None | — | — |
| 023 | Spawn Detection Algorithm | engine.py, test_spawn_detection.py | None | — | — |
| 024 | Type Inference Rules | engine.py, rules.py, test_type_inference.py | None | — | — |
| 025 | Idle and Zombie Detection | engine.py, colors.py, test_zombie_detection.py | None | — | — |
| 031 | Define Data Model Types | types.py | None | — | — |
| 032 | Create WorldState Container | state.py | None | — | — |
| 033 | Implement Position Grid Index | grid.py | None | — | — |
| 034 | Implement WorldStateManager Foundation | manager.py | None | — | — |
| 035 | Implement Project, Session, and Village CRUD | manager.py | None | — | — |
| 036 | Implement Agent CRUD with Position Assignment | manager.py | None | — | — |
| 037 | Implement Structure and Work Unit Management | manager.py | None | — | — |
| 041 | Implement SimulationEngine Core | __init__.py, engine.py, config.py, state.py | None | — | — |
| 042 | Implement Agent State Management | agent_updater.py | None | — | — |
| 043 | Implement Structure Progression System | structure_updater.py | None | — | — |
| 044 | Implement Animation State Machine | animation.py | None | — | — |
| 045 | Implement Village Expansion and Road Building | expansion.py | None | — | — |
| 046 | Integrate Simulation Components into Tick Loop | engine.py | None | — | — |
| 051 | Coordinate Types and Translation | coordinates.py | None | — | — |
| 052 | Viewport State Dataclass | state.py | None | — | — |
| 053 | Spatial Index for Visibility Queries | spatial_index.py | None | — | — |
| 054 | ViewportManager Core Operations | manager.py | None | — | — |
| 055 | ViewportManager Auto-Follow and Visibility Queries | manager.py | None | — | — |
| 056 | Viewport Package Exports | __init__.py | None | — | — |
| 061 | Textual Application Setup (HamletApp) | app.py | None | — | — |
| 062 | Symbol and Color Mappings | symbols.py | None | — | — |
| 063 | WorldView Widget | world_view.py | None | — | — |
| 064 | StatusBar Widget | status_bar.py | None | — | — |
| 065 | EventLog Widget | event_log.py | None | — | — |
| 066 | LegendOverlay Widget | legend.py | None | — | — |
| 067 | Input Handling and Actions | app.py | None | — | — |
| 068 | Reactive State Updates | app.py | None | — | — |
| 071 | Persistence Data Structures | types.py | None | — | — |
| 072 | Database Connection Management | connection.py | None | — | — |
| 073 | Migration System | migrations.py | None | — | — |
| 074 | Write-Behind Queue Infrastructure | queue.py | None | — | — |
| 075 | Entity Save Operations | saver.py | None | — | — |
| 076 | Write Execution | writer.py | None | — | — |
| 077 | Event Log Operations | event_log.py | None | — | — |
| 078 | State Loading | loader.py | None | — | — |
| 079 | Persistence Facade and Checkpoint | __init__.py, facade.py | None | — | — |
| 080 | Persistence Layer Core Tests - Facade, Connection, Migrations | test_persistence_facade.py, test_persistence_connection.py, test_persistence_migrations.py | None | — | — |
| 081 | Persistence Layer Data Tests - Writer, Loader, Queue, EventLog | test_persistence_writer.py, test_persistence_loader.py, test_persistence_queue.py, test_persistence_event_log.py | None | — | — |
| 082 | Event Processing Tests - Processor, Router, SequenceGenerator | test_event_processor.py, test_event_router.py, test_sequence_generator.py | None | — | — |
| 083 | Simulation Engine Core Tests - Engine, AgentUpdater, StructureUpdater | test_simulation_engine.py, test_agent_updater.py, test_structure_updater.py | None | — | — |
| 084 | Simulation Features Tests - Expansion, Animation | test_expansion.py, test_animation.py | None | — | — |
| 085 | Viewport Tests - Manager, Coordinates, SpatialIndex, State | test_viewport_manager.py, test_viewport_coordinates.py, test_viewport_spatial_index.py, test_viewport_state.py | None | — | — |
| 086 | TUI Widget Tests - StatusBar, EventLog, Legend | test_tui_status_bar.py, test_tui_event_log.py, test_tui_legend.py | None | — | — |
| 087 | TUI Integration Tests - WorldView, HamletApp | test_tui_world_view.py, test_tui_app.py | None | — | — |
| 088 | World State Tests - Grid, Manager CRUD and Queries | test_position_grid.py, test_world_state_manager.py | None | — | — |
| 089 | MCP Server Tests - Validation, Handlers, Server | test_mcp_validation.py, test_mcp_handlers.py, test_mcp_server.py | None | — | — |
| 090 | Hook Scripts - PreToolUse and PostToolUse | pre_tool_use.py, post_tool_use.py | None | — | — |
| 091 | Hook Scripts - Notification and Stop | notification.py, stop.py | None | — | — |
| 092 | Hook Installation Command | install.py, __init__.py | None | — | — |
| 093 | Application Entry Point | __main__.py, pyproject.toml | None | — | — |
| 094 | Configuration Module | __init__.py, settings.py, paths.py | None | — | — |
| 095 | Application Wiring and Orchestration | __main__.py, app.py | None | — | — |
| 096 | README and Documentation | README.md | None | — | — |
| 097 | End-to-End Integration Tests | test_e2e_hook_to_render.py, test_e2e_persistence_roundtrip.py | None | — | — |
| 098 | Final Polish and Error Messages | install.py, __main__.py | None | — | — |
| 099 | AgentType enum consolidation | types.py, symbols.py | None | — | — |
| 100 | HTTP endpoint on MCPServer | server.py, pyproject.toml | None | — | — |
| 101 | Fix PersistenceFacade constructor call in __main__.py | __main__.py | None | — | — |
| 102 | Wire AgentInferenceEngine in __main__.py | __main__.py | None | — | — |
| 103 | Wire simulation subsystems in __main__.py | __main__.py | None | — | — |
| 104 | WorldStateManager.handle_event() and public state accessors | manager.py, engine.py, manager.py, handlers.py, expansion.py | None | — | — |
| 105 | PersistenceFacade.log_event() method | facade.py | None | — | — |
| 106 | Implement work unit accumulation from PostToolUse | engine.py | None | — | — |
| 107 | Fix deterministic agent color assignment | manager.py, engine.py | None | — | — |
| 108 | Consolidate structure rules to single source of truth | config.py, manager.py, structure_updater.py | None | — | — |
| 109 | Persist Agent.project_id to SQLite | migrations.py, writer.py, loader.py | None | — | — |
| 110 | TESTER inference rules | engine.py | None | — | — |
| 111 | LLM activity summarization | summarizer.py, engine.py, settings.py, status_bar.py, pyproject.toml | None | — | — |
| 112 | Config validation in Settings.load() | settings.py | None | — | — |
| 113 | Hook script rewrite — read stdin, find_config, send all required fields | pre_tool_use.py, post_tool_use.py, notification.py, stop.py | None | — | — |
| 114 | Inference engine — fix active_tools counter and project entity creation | engine.py | None | — | — |
| 115 | Village initialization — seed initial structures on village creation | manager.py | None | — | — |
| 116 | Infrastructure — health endpoint and mcp_port wiring | server.py, __main__.py | None | — | — |
| 117 | Move TOOL_TO_STRUCTURE to world_state/rules.py | rules.py, engine.py | None | — | — |
| 118 | Minor display and code fixes | legend.py, engine.py, rules.py, server.py | None | — | — |
| 119 | Visualization fixes — animation colors, legend, dead code cleanup | animation.py, legend.py, colors.py, manager.py | None | — | — |
| 120 | Validation schema fix and InternalEvent notification/stop fields | validation.py, internal_event.py, event_processor.py | None | — | — |
| 121 | Hook server URL — dynamic port from config, no hardcoded 8080 | install.py, pre_tool_use.py, post_tool_use.py, notification.py, stop.py | None | — | — |
| 122 | Consume notification_message and stop_reason downstream | engine.py, manager.py | None | — | — |
| 123 | Consolidate agent color maps — animation.py uses TYPE_COLORS as single source | animation.py | None | — | — |
| 124 | Fix find_config() traversal — skip global config without project_id | pre_tool_use.py, post_tool_use.py, notification.py, stop.py | None | — | — |
| 125 | Add REST state endpoints to MCP server | server.py, serializers.py | None | — | — |
| 126 | Create daemon mode entry point | daemon.py, __init__.py, __init__.py | None | — | — |
| 127 | Create viewer mode and refactor entry point | remote_state.py, remote_world_state.py, __main__.py | None | — | — |
| 128 | Create plugin manifest files | plugin.json, mcp.json | None | — | — |
| 129 | Create hooks.json and shell wrappers | hooks.json, pre_tool_use.sh, post_tool_use.sh, notification.sh, stop.sh | None | — | — |
| 130 | Create plugin MCP server | server.py, start.sh | None | — | — |
| 131 | Add hamlet init CLI command | init.py, __init__.py, __init__.py | None | — | — |
| 132 | Change legend toggle key from ? to / | app.py, legend.py | None | — | — |
| 133 | Verify vim hjkl scroll bindings have no conflicts | app.py | None | — | — |
| 134 | Create HelpOverlay widget | help_overlay.py | None | — | — |
| 135 | Wire HelpOverlay into HamletApp | app.py | None | — | — |
| 136 | Update default CLI behavior for no-subcommand case | __init__.py | None | — | — |
| 137 | Add hamlet daemon to __main__.py dispatch | __main__.py | None | — | — |
| 166 | Add async:true to plugin hooks.json | hooks.json | None | — | — |
| 167 | Remove inline hooks from ~/.claude/settings.json | settings.json | None | — | — |
| 168 | Register hamlet in claude-marketplace | marketplace.json | None | — | — |
| 169 | Fix plugin execution: chmod, BASH_SOURCE, plugin.json path verification | pre_tool_use.py, post_tool_use.py, notification.py, stop.py, start.sh, plugin.json | None | — | — |
| 170 | Fix server_url plumbing and hamlet_init onboarding guidance | pre_tool_use.py, post_tool_use.py, notification.py, stop.py, server.py | None | — | — |
| 171 | Add uv/mcp diagnostic to start.sh python3 fallback | start.sh | None | — | — |
| 172 | Add python3 availability guard to start.sh and fix pip advice | start.sh | None | — | — |
| 173 | hamlet_init: add server_url guidance and path parameter; add hamlet to marketplace CLAUDE.md | server.py, CLAUDE.md | None | — | — |
| 174 | Extract hook utilities to hamlet_hook_utils.py | hamlet_hook_utils.py, pre_tool_use.py, post_tool_use.py, notification.py, stop.py | Pass | 0/0/1 | archive/incremental/174-extract-hook-utils.md |
| 175 | Remove dead .sh wrapper files from hooks/ | pre_tool_use.sh, post_tool_use.sh, notification.sh, stop.sh | Pass | 0/0/0 | archive/incremental/175-remove-dead-sh-files.md |
| 176 | Improve mcp import check in start.sh | start.sh | Pass | 0/0/0 | archive/incremental/176-mcp-import-check.md |
| 177 | Add server_url parameter to hamlet_init | server.py | Pass | 0/0/0 | archive/incremental/177-server-url-param.md |
| 178 | Add error logging in hamlet_hook_utils.py on malformed config JSON | hamlet_hook_utils.py | Pass | 0/0/0 | archive/incremental/178-config-error-logging.md |
| 179 | New hook scripts — agent/session lifecycle | session_start.py, session_end.py, subagent_start.py, subagent_stop.py, teammate_idle.py, task_completed.py | None | — | — |
| 180 | New hook scripts — system/observation events | post_tool_use_failure.py, user_prompt_submit.py, pre_compact.py, post_compact.py, stop_failure.py | None | — | — |
| 181 | Update hooks.json — register all 15 hooks, fix PreToolUse async | hooks.json | None | — | — |
| 182 | Extend event schema for new hook types | internal_event.py, validation.py, event_processor.py | None | — | — |
| 183 | Daemon handling for new event types with visual triggers | manager.py | None | — | — |
| 184 | Adaptive viewport — wire WorldView to terminal size | world_view.py | None | — | — |
| 185 | Plugin update hygiene — hamlet install detects plugin and skips hooks | install.py | None | — | — |
| 186 | Version bump to 0.4.0 | pyproject.toml, plugin.json, __init__.py, __init__.py | None | — | — |
| 187 | Test coverage — event pipeline round-trip for all 15 HookType values | test_event_processor.py, test_world_state_manager.py | Pass | 0/0/0 | archive/incremental/187-event-pipeline-tests.md |
| 188 | Test coverage — on_resize, on_mount, and is_plugin_active | test_tui_world_view.py, test_cli_install.py | Pass | 0/0/2 | archive/incremental/188-on-resize-plugin-tests.md |
| 189 | Test coverage — hook script unit tests | test_hooks.py | Pass | 0/0/0 | archive/incremental/189-hook-script-tests.md |
| 190 | CLAUDE.md for the hamlet project | CLAUDE.md | Pass | 0/0/0 | archive/incremental/190-claude-md.md |
| 191 | README and QUICKSTART accuracy update | README.md, QUICKSTART.md | Pass | 0/0/0 | archive/incremental/191-readme-quickstart.md |
| 192 | Public API docstrings for five core modules | manager.py, engine.py, event_processor.py, server.py, facade.py | Pass | 0/0/0 | archive/incremental/192-docstrings.md |
| 193 | Code health — enum identity dispatch and convention comment in handle_event | manager.py | Pass | 0/0/1 | archive/incremental/193-enum-identity.md |
| 194 | Code health — remove orphaned saver.py and deduplicate startup sequence | saver.py, app_factory.py, __main__.py, daemon.py | Pass | 0/0/0 | archive/incremental/194-saver-appfactory.md |
| 195 | Functional gap — /hamlet/health endpoint test (Q-6) | test_mcp_server.py | Pass | 0/0/0 | archive/incremental/195-health-test.md |
| 196 | Functional gap — Bash tool_output schema widening and notification_type extraction (Q-10, Q-16) | validation.py, internal_event.py, event_processor.py, test_event_processor.py | Pass | 0/0/1 | archive/incremental/196-bash-schema-notification-type.md |
| 197 | stop_reason behavioral differentiation — use telemetry to mark agents IDLE (Q-13) | engine.py, manager.py, test_inference_engine.py | Pass | 0/0/1 | archive/incremental/197-stop-reason-differentiation.md |
| 198 | Protocol interfaces for module boundaries | protocols.py, engine.py, server.py, event_processor.py, engine.py, manager.py | Pass | 0/0/0 | archive/incremental/198-protocol-interfaces.md |
| 199 | Add end_turn to stop_reason IDLE transition guards | engine.py, manager.py, test_inference_engine.py | Pass | 0/0/1 | archive/incremental/199-end-turn-stop-reason.md |
| 200 | notification_type downstream consumption in WorldStateManager | manager.py | Pass | 0/0/0 | archive/incremental/200-notification-type-consumption.md |
| 201 | Test WorldStateManager.handle_event Stop/end_turn IDLE transition | test_world_state_manager.py | Pass | 0/0/2 | archive/incremental/201-end-turn-manager-test.md |
| 202 | Update QUICKSTART.md for daemon/viewer split and hamlet_init skill | QUICKSTART.md | Pass | 0/0/1 | archive/incremental/202-update-quickstart.md |
| 203 | Update README.md Quick Start section | README.md | Pass | 0/0/2 | archive/incremental/203-update-readme-quickstart.md |
| 204 | hamlet service subcommand group with launchd integration | service.py, __init__.py, test_cli_service.py | Pass | 0/0/2 | archive/incremental/204-service-subcommand.md |
| 205 | Daemon port conflict detection and warning | daemon.py, test_cli_daemon.py | Pass | 0/0/0 | archive/incremental/205-daemon-port-conflict.md |
| 206 | Fix service.py correctness issues and test/daemon cleanup | service.py, daemon.py, test_cli_service.py, test_cli_daemon.py | Pass | 0/0/1 | archive/incremental/206-service-correctness-fixes.md |
| 207 | Fix _install idempotency guard and missing edge-case tests | service.py, test_cli_service.py, __init__.py | Pass | 0/1/1 | archive/incremental/207-install-guard-fix.md |
| 208 | Reset agent state to ZOMBIE on daemon startup | manager.py, test_world_state_manager.py | Pass | 0/0/1 | archive/incremental/208-reset-agent-state-zombie.md |
| 209 | Fix WorldView initial paint (remove premature resize in on_mount) | world_view.py, test_tui_world_view.py | Pass | 0/0/1 | archive/incremental/209-fix-worldview-initial-paint.md |
| 210 | Agent despawn infrastructure | manager.py, facade.py, writer.py, test_world_state_manager.py, test_persistence_facade.py | Pass | 0/0/1 | archive/incremental/210-agent-despawn-infrastructure.md |
| 211 | Inference engine despawn logic and zombie TTL config | engine.py, types.py, settings.py, test_inference_engine.py, test_settings.py | Pass | 0/0/1 | archive/incremental/211-inference-engine-despawn-logic.md |
| 212 | Fix legend overlay positioning | legend.py, app.py, test_tui_legend.py | Pass | 0/0/1 | archive/incremental/212-fix-legend-overlay-positioning.md |
