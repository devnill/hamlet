## Verdict: Fail

The despawn path introduced in WI-210 and WI-211 has a correctness defect (session back-reference not cleared on despawn) and two protocol-contract gaps that leave the type system unable to verify the despawn path end-to-end.

## Critical Findings

None.

## Significant Findings

### S1: `despawn_agent` does not remove the agent from `Session.agent_ids`
- **File**: `src/hamlet/world_state/manager.py:542`
- **Issue**: `despawn_agent` removes the agent from `self._state.agents` and from `village.agent_ids`, but never removes it from the `Session` object's `agent_ids` list in `self._state.sessions`. After despawn the dead agent id remains in `session.agent_ids`.
- **Impact**: Two failure modes. First, `get_or_create_agent` checks `session.agent_ids[0]` to return the existing primary agent — after despawn it looks up a now-deleted id in `self._state.agents`, finds nothing, then creates a brand-new agent instead of recognising this as a new spawn, producing phantom duplicate agents in a restarted session. Second, if `_handle_stop` iterates `session.agent_ids` after the zombie TTL path already ran `despawn_agent`, the second call is a no-op in memory but still reaches `_persistence.delete_agent`, firing a redundant DB DELETE.
- **Suggested fix**: Inside the `async with self._lock` block in `despawn_agent`, after removing from `village.agent_ids`, also clean up the session:
  ```python
  session = self._state.sessions.get(agent.session_id)
  if session and agent_id in session.agent_ids:
      session.agent_ids.remove(agent_id)
  ```

### S2: `delete_agent` missing from `PersistenceProtocol`
- **File**: `src/hamlet/protocols.py:53`
- **Issue**: `WorldStateManager.despawn_agent` calls `self._persistence.delete_agent(agent_id)` where `self._persistence` is typed as `PersistenceProtocol`. `PersistenceProtocol` does not declare `delete_agent`. Any stub or alternative implementation that satisfies only the protocol will fail at runtime when the first despawn fires.
- **Impact**: Runtime `AttributeError` on first despawn in any test or deployment that uses a protocol-conforming stub instead of the concrete `PersistenceFacade`.
- **Suggested fix**: Add to `PersistenceProtocol`:
  ```python
  async def delete_agent(self, agent_id: str) -> None: ...
  ```

### S3: `startup()` not declared on `InferenceEngineProtocol`
- **File**: `src/hamlet/protocols.py:46`
- **Issue**: `AgentInferenceEngine.startup()` is called in `app_factory.py:78` on the concrete type. `InferenceEngineProtocol` only declares `process_event` and `tick`. Any consumer that depends on the protocol cannot call `startup()`, and any stub substituted in tests will silently skip the seeding step, leaving startup zombies that never despawn.
- **Suggested fix**: Add `async def startup(self) -> None: ...` to `InferenceEngineProtocol`.

## Minor Findings

### M1: `ZOMBIE_THRESHOLD_SECONDS` is a hardcoded class constant, not driven by settings
- **File**: `src/hamlet/inference/engine.py:37`
- **Issue**: The despawn threshold is correctly wired from `settings.zombie_despawn_seconds`, but the zombification threshold is a hardcoded class constant of 300 s. A user who lowers `zombie_despawn_seconds` expecting faster cleanup will be surprised that zombification itself still takes 300 s.
- **Suggested fix**: Accept a `zombie_threshold_seconds` constructor parameter alongside `despawn_threshold_seconds`, defaulting to 300.

### M2: `HelpOverlay` `width` CSS does not match content width
- **File**: `src/hamlet/tui/help_overlay.py:13`
- **Issue**: `HelpOverlay` declares `width: 51` but its border string is 40 characters wide. The unused 11 columns show as blank terminal space.
- **Suggested fix**: Set `HelpOverlay` CSS `width: 40` to match its actual content.

### M3: Redundant ZOMBIE upsert immediately before despawn DELETE
- **File**: `src/hamlet/inference/engine.py:462`
- **Issue**: TTL despawn path calls `update_agent(state=AgentState.ZOMBIE)` (queues a write) then immediately calls `despawn_agent` (queues a DELETE). The DELETE supersedes the upsert, making the intermediate write wasted. Not a correctness defect.
- **Suggested fix**: No immediate change required. Skip the ZOMBIE upsert when TTL has already elapsed.

## Unmet Acceptance Criteria

- `PersistenceProtocol` does not declare `delete_agent` — see S2.
- `InferenceEngineProtocol` does not declare `startup` — see S3.
