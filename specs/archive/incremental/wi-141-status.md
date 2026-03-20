# WI-141 Status: Fix hook registration end-to-end

## Reference Plugin Research

### cyberbrain (`/Users/dan/code/cyberbrain/.claude-plugin/plugin.json`)
- No `hooks` field in plugin.json
- Has `hooks/hooks.json` using `${CLAUDE_PLUGIN_ROOT}` variable for path resolution
- Nested array format: `{ "HookName": [{"hooks": [{"type": "command", "command": "...", "timeout": N}]}] }`

### ideate (`/Users/dan/code/ideate/.claude-plugin/plugin.json`)
- No `hooks` field in plugin.json
- No hooks/hooks.json found

### Actual Claude Code settings.json (`/Users/dan/.claude/settings.json`)
- Confirms the nested array format is required:
  ```json
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "...",
            "async": true
          }
        ]
      }
    ]
  }
  ```
- The real settings use inline `jq | curl` shell commands rather than script paths

## Changes Made

### 1. `src/hamlet/cli/commands/install.py` — `install_hooks_to_settings` function
**Problem**: Was writing flat string format: `settings["hooks"][hook_name] = hook_path`

**Fix**: Changed to nested array format that Claude Code actually parses:
```python
settings["hooks"][hook_name] = [
    {
        "hooks": [
            {
                "type": "command",
                "command": hook_path,
            }
        ]
    }
]
```

### 2. `.claude-plugin/plugin.json` — Added `hooks` field
**Problem**: No `hooks` field, so hooks/hooks.json was never referenced at plugin install time.

**Fix**: Added `"hooks": "./hooks/hooks.json"` field.

Note: Neither cyberbrain nor ideate use this field in their plugin.json, so whether the Claude Code plugin system actually reads this field is uncertain. It may be that the hooks.json file is discovered by convention (path: `hooks/hooks.json`) rather than via plugin.json declaration.

### 3. `hooks/hooks.json` — Fixed file extensions
**Problem**: Referenced `.sh` script files (`pre_tool_use.sh`, etc.) but the actual hook scripts are `.py` files.

**Fix**: Updated all four command paths to use `.py` extension:
- `${CLAUDE_PLUGIN_ROOT}/hooks/pre_tool_use.py`
- `${CLAUDE_PLUGIN_ROOT}/hooks/post_tool_use.py`
- `${CLAUDE_PLUGIN_ROOT}/hooks/notification.py`
- `${CLAUDE_PLUGIN_ROOT}/hooks/stop.py`

The `${CLAUDE_PLUGIN_ROOT}` variable is used by cyberbrain's hooks.json, confirming it is supported by the Claude Code plugin system.

## Remaining Uncertainties

1. **`hooks` field in plugin.json**: No reference plugin uses this field. It's unclear if Claude Code plugin installer reads `plugin.json["hooks"]` to load hooks.json, or if it discovers `hooks/hooks.json` by convention. Adding the field is safe but may have no effect if the field isn't in the plugin schema.

2. **`${CLAUDE_PLUGIN_ROOT}` expansion**: Confirmed used by cyberbrain, so presumably expanded. However, hamlet is not installed as a plugin via the Claude Code marketplace — it uses a manual `hamlet install` CLI command that writes to settings.json directly. The hooks.json with `${CLAUDE_PLUGIN_ROOT}` paths is only relevant for the plugin-install path, not the CLI install path.

3. **Plugin vs CLI install paths**: The project has two distinct installation mechanisms:
   - Plugin install (via Claude Code plugin system): uses `hooks/hooks.json` + `${CLAUDE_PLUGIN_ROOT}`
   - CLI install (`hamlet install`): uses `install_hooks_to_settings` writing absolute paths to settings.json
   Both paths are now fixed, but only one will be used depending on how hamlet is actually installed.

4. **`async` vs `timeout` field**: The real settings.json uses `"async": true` while hooks.json uses `"timeout": 5`. These are different hook behaviors. The CLI install path does not set either — the fix adds only `type` and `command` fields, matching the minimal structure from the WI spec. This may be worth revisiting.
