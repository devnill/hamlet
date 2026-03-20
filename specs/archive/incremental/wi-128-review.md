## WI-128 Incremental Review
### Verdict: PASS_WITH_NOTES
### Findings

- [SIGNIFICANT] `/Users/dan/code/hamlet/.claude-plugin/plugin.json:9` — The `mcpServers` field is set to the string `"./.claude-plugin/mcp.json"` rather than an object containing server definitions. The acceptance criterion requires only that the field exist, which it does, so the criterion is technically met. However, the type is inconsistent with how `mcpServers` is defined everywhere else in the plugin spec (always an object). If any plugin loader or tool validates that `mcpServers` is an object (matching the shape in `mcp.json`), this string value will cause a parse or validation failure at runtime. The field should either embed the server map inline — `"mcpServers": { "hamlet-config": { "command": "sh", "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/start.sh"] } }` — or the loader must explicitly support a path-reference string, which is not documented anywhere in the spec.

- [MINOR] `/Users/dan/code/hamlet/.claude-plugin/plugin.json:5-7` — The `author` field is `{ "name": "hamlet" }`, which mirrors the project name rather than identifying an actual author (person or organisation). This is not a correctness problem but will appear incorrect to any tooling or registry that expects a real author identity.
