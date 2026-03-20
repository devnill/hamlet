# Claude Code Hooks Research

**Note: Web search was unavailable. These findings are based on training knowledge (cutoff: January 2025). Verify current status of APIs, versions, and deprecation timelines independently.**

## Summary

Claude Code provides a hook system that allows external scripts to intercept and respond to events during execution. The primary hook types are `PreToolUse` and `PostToolUse`, which fire before and after tool invocations. Additional hooks include `Notification` for general notifications and `Stop` for session termination. Hooks are configured via JSON settings files and receive structured JSON input through stdin. Agent spawning and task lifecycle events are NOT directly exposed as dedicated hooks as of early 2025.

## Key Facts

### Hook Configuration Location

Hooks are configured in:
- `~/.claude/settings.json` (global/user level)
- `.claude/settings.json` (project level)
- `CLAUDE_SETTINGS` environment variable (path to settings file)

Settings files can specify hooks under a `hooks` key with arrays of hook configurations.

### Hook Types

**1. PreToolUse**
- Fires **before** a tool is invoked
- Can approve, deny, or modify tool execution
- Input includes: tool name, tool input parameters, conversation context
- Exit code 0 = allow tool execution
- Exit code non-zero = block tool execution
- Can output JSON to modify tool inputs

**2. PostToolUse**
- Fires **after** a tool completes execution
- Receives tool output/result
- Cannot block execution (already happened)
- Can process or log tool results
- Exit code is ignored (no effect on flow)

**3. Notification**
- Fires for general notifications (non-tool events)
- Used for logging, monitoring, alerting
- Input includes: notification type, message content, level (info/warn/error)
- Often used for session lifecycle events

**4. Stop**
- Fires when Claude Code session is terminating
- Cleanup hook for final actions
- Fires on: natural session end, user interrupt (Ctrl+C), error termination
- Best effort execution - may not fire on abrupt process kill

### Hook Input Format

Hooks receive JSON through stdin with this general structure:

```json
{
  "hook_name": "PreToolUse",
  "session_id": "uuid-string",
  "timestamp": "ISO-8601-timestamp",
  "data": {
    // Hook-specific payload
  }
}
```

### PreToolUse Detailed Payload

```json
{
  "hook_name": "PreToolUse",
  "session_id": "...",
  "timestamp": "...",
  "data": {
    "tool_name": "Read|Write|Bash|Grep|...",
    "tool_input": {
      // Tool-specific parameters
    },
    "conversation_id": "...",
    "message_id": "..."
  }
}
```

### PostToolUse Detailed Payload

```json
{
  "hook_name": "PostToolUse",
  "session_id": "...",
  "timestamp": "...",
  "data": {
    "tool_name": "...",
    "tool_input": { ... },
    "tool_output": {
      // Tool result data
    },
    "success": true|false,
    "error": "error message if failed",
    "duration_ms": 123
  }
}
```

### Notification Payload

```json
{
  "hook_name": "Notification",
  "session_id": "...",
  "timestamp": "...",
  "data": {
    "type": "info|warn|error",
    "message": "...",
    "details": { ... }
  }
}
```

### Stop Payload

```json
{
  "hook_name": "Stop",
  "session_id": "...",
  "timestamp": "...",
  "data": {
    "reason": "normal|interrupt|error",
    "message_count": 42
  }
}
```

### Hook Timing Context

| Hook | Timing | Context Available | Can Block |
|------|--------|-------------------|-----------|
| PreToolUse | Before tool execution | Tool name, inputs, session | Yes |
| PostToolUse | After tool completion | Tool name, inputs, outputs, duration | No |
| Notification | On notification event | Notification type, message | No |
| Stop | Session termination | Session stats, termination reason | No |

### Configuration Example

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": {
          "toolName": "Bash"
        },
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/script.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/log-tool.sh"
          }
        ]
      }
    ]
  }
}
```

### Matcher Configuration

Hooks can be filtered using matchers:

```json
{
  "matcher": {
    "toolName": "Bash",           // Match specific tool
    "toolName": { "not": "Read" } // Match all except
  }
}
```

### Hook Script Requirements

1. Must be executable
2. Reads JSON input from stdin
3. Writes output to stdout
4. Exit codes:
   - 0: Success/allow (PreToolUse: permit execution)
   - Non-zero: Failure/block (PreToolUse: deny execution)
5. Environment variables:
   - `CLAUDE_SESSION_ID`: Current session ID
   - `CLAUDE_WORKING_DIR`: Working directory

## Agent Spawning Hooks

### Current Status (as of January 2025)

**No dedicated agent spawning hooks exist.** Agent spawning is handled internally by Claude Code and does not fire separate hook events.

### Observable Events

When an agent is spawned:
1. The main instance sends a `PreToolUse` with `tool_name` matching the agent invocation
2. The spawned agent's actions generate their own `PreToolUse`/`PostToolUse` events
3. When the agent completes, a `PostToolUse` is fired for the original invocation

**Implication:** You can infer agent spawning by tracking `PreToolUse` events for agent-related tools, but there is no explicit "AgentSpawned" or "AgentCompleted" hook.

### Potential Workaround

For observability of agent activity:

1. Track session/task IDs across `PreToolUse`/`PostToolUse` pairs
2. Correlate nested tool calls with parent invocations
3. Use the `session_id` field to group events
4. Monitor for concurrent tool executions (may indicate agent activity)

## Task Lifecycle Hooks

### Current Status (as of January 2025)

**No dedicated task lifecycle hooks exist.** Tasks in Claude Code are an internal concept and do not expose explicit lifecycle events.

### Observable Events

Task-related activity manifests as:
1. **Task start**: No explicit event; infer from first `PreToolUse` for task tools
2. **Task progress**: `PreToolUse`/`PostToolUse` events for tools used within task
3. **Task completion**: `PostToolUse` for task tool with result containing task output
4. **Task status changes**: No direct exposure; must infer from tool call patterns

### Task Tool Events

If Claude Code uses a task-related internal tool:
- `PreToolUse` fires before task execution
- Task execution may involve multiple nested tool calls
- `PostToolUse` fires after all nested operations complete

## Recommendations

Not applicable -- this was a factual inquiry about available hooks.

## Risks

### Documentation Gaps
- Hook system documentation is less complete than core tool documentation
- Payload structures may vary or evolve
- Agent/task hook behavior is inferred, not explicitly documented

### Implementation Risks
- Hooks that block (PreToolUse non-zero exit) can disrupt user workflows
- Hook scripts must be fast; slow hooks degrade overall performance
- Environment may differ between hook invocations
- Stop hooks may not fire on abrupt termination (kill -9, crash)

### Version Compatibility
- Hook payloads are internal API; subject to change
- New hook types may be added without notice
- Matcher syntax may evolve

### Security Considerations
- Hook scripts run with user's permissions
- Malicious hooks could intercept/modify tool inputs
- Hook commands specified in settings files can be modified by code
- Sensitive data (file contents, commands) passes through hook stdin

## Sources

Training knowledge only -- no live web sources consulted.

Key concepts referenced:
- Claude Code settings.json configuration
- JSON-RPC notification structures for hooks
- Hook stdin/stdout protocol conventions