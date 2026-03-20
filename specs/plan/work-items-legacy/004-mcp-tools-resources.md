# 004: MCP Tools and Resources

## Objective
Implement the MCP tools (`hamlet_status`) and resources (`hamlet://world`) that expose server state.

## Acceptance Criteria
- [ ] `hamlet_status` tool registered with MCP server
- [ ] Tool returns server status with event queue size and uptime
- [ ] `hamlet://world` resource registered with MCP server
- [ ] Resource returns world state summary (projects, agents, structures)
- [ ] Both handlers catch exceptions and return error responses

## File Scope
- `src/hamlet/mcp_server/handlers.py` (modify)

## Dependencies
- Depends on: 003
- Blocks: 005

## Implementation Notes
Tools and resources need access to World State for status. Use dependency injection pattern.

## Complexity
Low