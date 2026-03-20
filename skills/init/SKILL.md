---
description: "Initialize hamlet for this project. Creates .hamlet/config.json with a unique project ID so the daemon can track this codebase as its own village."
user-invocable: true
argument-hint: "[server_url]"
---

Initialize hamlet for the current project by calling the `hamlet_init` MCP tool.

## Steps

1. Check whether `.hamlet/config.json` already exists in the current working directory.
   - If it exists, read it and report the existing configuration to the user. Ask if they want to re-initialize (which will overwrite it) or stop.
   - If it does not exist, proceed.

2. Call the `hamlet_init` tool (available as `mcp__plugin_hamlet_hamlet-config__hamlet_init`).
   - If the user provided a `server_url` argument, pass it as the `server_url` parameter.
   - Otherwise call with no arguments (defaults apply).

3. Report the result clearly:

```
hamlet initialized for this project.

Project ID:   {project_id from config}
Project name: {project_name from config}
Server URL:   {server_url from config}
Config file:  .hamlet/config.json

Next steps:
  1. Start the hamlet daemon:  hamlet daemon
  2. Open the viewer:          hamlet
  3. Start coding — your activity will appear in the village.
```

4. If the config already existed and the user chose not to re-initialize, show the existing values in the same format with a note: "Already initialized — no changes made."

5. If `hamlet_init` returns an error, surface it clearly and suggest running `hamlet daemon` is running on the expected port.
