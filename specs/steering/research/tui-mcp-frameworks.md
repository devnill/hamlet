# TUI Frameworks and MCP Server Architecture Research

**Note: Web search was unavailable. These findings are based on training knowledge (cutoff: January 2025). Verify current status of APIs, versions, and deprecation timelines independently.**

## Summary

For a persistent server that renders ASCII art and accepts MCP connections with real-time UI updates, **Python with Textual** offers the best combination of async-native concurrency, rapid iteration, and MCP ecosystem alignment. Go with Bubbletea/tcell is a strong alternative if performance is critical. Rust with Ratatui has the steepest iteration cost despite excellent performance.

## Key Facts

### MCP Server Architecture

- MCP (Model Context Protocol) uses JSON-RPC 2.0 over stdio or SSE (Server-Sent Events) transport
- Claude Code connects to MCP servers configured in `claude_desktop_config.json` or via CLI flags
- MCP servers can expose three capability types: `resources` (read-only data), `tools` (callable functions), and `prompts` (templates)
- Bidirectional communication: Claude Code sends requests, servers respond or emit notifications
- Hook events (like PreToolUse, PostToolUse) are sent via the `notifications` channel
- Official SDKs exist for Python, TypeScript, and Go (community-maintained)

### Framework Comparison Facts

**Go - Bubbletea/tcell:**
- Bubbletea (v0.26+) is built on the Elm Architecture: `Model -> Update(msg) -> View`
- tcell (v2) provides low-level terminal cell manipulation
- Concurrency: Go routines + channels map well to event-driven architecture
- No built-in async I/O; requires explicit goroutine management for MCP server + UI coordination
- Strong Windows terminal support via native console APIs
- Compilation step adds ~2-5 second iteration overhead

**Python - Textual:**
- Textual (v0.47+) is async-native, built on asyncio
- Built-in CSS-like styling and reactive attributes
- `App.run_async()` allows running TUI alongside other async tasks (MCP server)
- Widget system with layout management; ASCII-only mode available via `App(ansi_color=False)`
- Dev tools: `textual run --dev` provides hot reload
- Direct integration with Python MCP SDK (`mcp` package)

**Rust - Ratatui:**
- Ratatui (v0.26+) is the maintained fork of tui-rs
- Immediate mode rendering: each frame rebuilds the entire widget tree
- No built-in event loop; must bring own async runtime (tokio recommended)
- Requires manual coordination between tokio tasks and terminal rendering
- Compilation + type system adds significant iteration overhead (5-15 seconds typical)
- Excellent performance; suitable for complex tile rendering

### MCP Event Flow

```
Claude Code                        MCP Server                    TUI App
    |                                 |                            |
    |--[stdio/SSE]------------------->|                            |
    |   initialize                    |                            |
    |<-------------------------------|                            |
    |   initialize response          |                            |
    |                                 |                            |
    |--[notification]---------------->|                            |
    |   tools/called (hook event)     |                            |
    |                                 |--[async channel]--------->|
    |                                 |   event                   |   update UI
    |                                 |                            |
```

## Recommendations

### Option 1: Python with Textual (Recommended)
- **Pros:**
  - Async-native architecture matches MCP's async nature perfectly
  - Python MCP SDK (`mcp` package) is officially supported
  - Hot reload with `--dev` flag enables fast iteration
  - Reactive attributes (`@on` decorators) simplify state management
  - Large widget library; can render ASCII-only with custom widgets
  - Easy to add MCP server as another async task in same process
- **Cons:**
  - Python performance limits for very complex tile rendering
  - Requires Python 3.8+ environment
  - Textual is newer ecosystem than Go/Rust options
- **When to use:** Primary choice when iteration speed and MCP integration are priorities. Ideal for a project that will evolve.

### Option 2: Go with Bubbletea/tcell
- **Pros:**
  - Goroutines provide clean separation between MCP server and UI loop
  - Compiled binary is easy to deploy
  - Strong cross-platform terminal support
  - Good performance for complex rendering
  - Community MCP SDK available (`github.com/modelcontextprotocol/go-sdk`)
- **Cons:**
  - Must manually coordinate between MCP event channel and Bubbletea message queue
  - Compilation step slows iteration
  - Less ergonomic state management than Textual's reactive model
- **When to use:** When you need a single deployable binary and can accept slower iteration.

### Option 3: Rust with Ratatui
- **Pros:**
  - Best performance; handles complex tile rendering efficiently
  - Strong type safety catches errors early
  - tokio + Ratatui is a common pattern with good community support
  - Memory safe with no GC pauses
- **Cons:**
  - Steepest learning curve and slowest iteration cycle
  - Must bridge tokio async runtime with Ratatui's synchronous render loop
  - No official MCP SDK; would need to implement JSON-RPC layer manually or use community crates
  - More boilerplate for event coordination
- **When to use:** When performance is critical and project scope is well-defined with less need for rapid evolution.

## MCP Integration Details

### Receiving Hook Events from Claude Code

Claude Code can send notifications to MCP servers when configured. The standard mechanism:

1. **Configure MCP server in Claude Code:** Add server configuration to Claude Code settings or use `--mcp-config` flag
2. **Server declares capabilities:** In `initialize` response, specify supported features
3. **Hook notifications:** Claude Code sends `notifications/tools/called` or similar events when hooks fire
4. **Server processes and forwards:** MCP server receives via stdio/SSE and can push to internal event queue

### Typical MCP Server Architecture for Event Reception

```python
# Python MCP server with async event handling
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("my-idle-game")
event_queue = asyncio.Queue()

@app.list_tools()
async def list_tools():
    return [...]

@app.call_tool()
async def call_tool(name, arguments):
    # Put event in queue for TUI to consume
    await event_queue.put({"type": name, "data": arguments})
    return {"status": "received"}

async def run_with_tui():
    # Run MCP server and TUI concurrently
    async with stdio_server() as (read_stream, write_stream):
        mcp_task = asyncio.create_task(
            app.run(read_stream, write_stream, app.create_initialization_options())
        )
        tui_task = asyncio.create_task(run_tui(event_queue))
        await asyncio.gather(mcp_task, tui_task)
```

### Claude Code Hook System

As of early 2025, Claude Code supports:
- **PreToolUse / PostToolUse:** Notifications before/after tool execution
- **Notification events:** Delivered to MCP servers subscribed to notifications
- **Server-sent notifications:** MCP servers can also send notifications to Claude Code

The exact hook event format uses JSON-RPC notification structure:
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {
    "level": "info",
    "data": { /* event details */ }
  }
}
```

## Risks

### Python/Textual Risks
- Textual is still evolving rapidly; API changes possible between versions
- Python GIL could be a bottleneck if MCP events arrive faster than UI can process
- Textual's ASCII-only rendering may require custom widget work for complex tile sets

### Go/Bubbletea Risks
- Coordinating MCP stdio with Bubbletea's message loop requires careful channel management
- No official MCP Go SDK from Anthropic (community-maintained only)
- tcell had a v1 to v2 breaking change; future v3 possible

### Rust/Ratatui Risks
- Ratatui is a community fork; long-term maintenance less certain than Bubbletea/Textual
- No canonical MCP SDK for Rust
- Steepest iteration cost may slow feature development

### General MCP Risks
- MCP is actively evolving; protocol versions may change
- Hook event API is newer and may have less documentation
- Claude Code MCP integration specifics may differ from Claude Desktop

## Sources

Training knowledge only - no live web sources consulted.

Key packages referenced:
- `github.com/charmbracelet/bubbletea` (Go)
- `github.com/gdamore/tcell/v2` (Go)
- `textual` on PyPI (Python)
- `ratatui` on crates.io (Rust)
- `mcp` on PyPI (Python MCP SDK)
- `github.com/modelcontextprotocol/go-sdk` (Go MCP SDK)