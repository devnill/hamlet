# Module: TUI

## Scope

This module owns the terminal user interface built with Textual. It is responsible for:

- Rendering the world view (agents, structures, terrain)
- Displaying the status line (agent count, structure count, project name)
- Showing the event log (scrollable list of recent events)
- Handling user input (scroll, menu navigation, legend)
- Managing overlays (legend, help, menus)
- Refreshing display at configurable frame rate

This module is NOT responsible for:

- Managing world state (World State module)
- Game logic (Simulation module)
- Coordinate translation (Viewport module)

## Provides

- `HamletApp` class — Main Textual application
  - `async run_async()` — Start the TUI
  - `request_refresh()` — Request immediate redraw

- `WorldView` widget — Main world rendering area
  - Renders agents as `@` with type-based colors
  - Renders structures based on type and stage
  - Handles scroll input

- `StatusBar` widget — Status line at top
  - Shows agent count, structure count, active project
  - Shows viewport position

- `EventLog` widget — Scrollable event list at bottom
  - Shows recent events in chronological order
  - Auto-scrolls to show latest

- `LegendOverlay` widget — Legend display (toggleable)
  - Shows agent types and colors
  - Shows structure symbols

## Requires

- `WorldState` (from World State module) — Query entities for rendering
  - `get_agents_in_view(bounds) -> List[Agent]`
  - `get_structures_in_view(bounds) -> List[Structure]`
  - `get_event_log(limit) -> List[EventLogEntry]`
- `ViewportManager` (from Viewport module) — Coordinate translation
  - `get_visible_bounds() -> BoundingBox`
  - `world_to_screen(pos) -> Position`
- `asyncio` — Event loop integration

## Boundary Rules

1. **No game logic.** TUI only renders state; it never modifies World State directly.

2. **Frame-rate limited.** Rendering happens at fixed frame rate (default 30 FPS), not on every state change.

3. **Input delegation.** User input (scroll, etc.) goes through Viewport module; TUI only handles raw input events.

4. **Widget hierarchy.** Textual widget hierarchy must not leak into other modules.

5. **No business logic.** Symbol mappings, colors, and animations are defined here; not in World State.

## Internal Design Notes

### Widget Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                      HamletApp                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    StatusBar                          │   │
│  │  Agents: 12 │ Structures: 8 │ Project: hamlet │ (5,10)│  │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │                    WorldView                         │   │
│  │                 (Main render area)                   │   │
│  │                                                      │   │
│  │      @  @  ░▒▓  .  .  .  @  ░░                       │   │
│  │      │  │  ░░▓▓  .  .  .  │  ░░                       │   │
│  │      @  @  ░░▓▓  #  #  #  @  ░░                       │   │
│  │      .  .  .  .  .  .  .  .  .                        │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    EventLog                           │   │
│  │  [12:34:56] Agent spawned near (5,10)                │   │
│  │  [12:34:55] Structure 'Library' stage 2 complete    │   │
│  │  [12:34:54] Read tool completed (researcher)         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    LegendOverlay (toggleable)        │   │
│  │  @ Agent  # Wall  ░ Structure (wood)  ▒ Stone       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Symbol Mappings

```python
# Agent symbols
AGENT_SYMBOL = "@"

# Agent colors by type
AGENT_COLORS = {
    AgentType.RESEARCHER: "cyan",
    AgentType.CODER: "yellow",
    AgentType.EXECUTOR: "green",
    AgentType.ARCHITECT: "magenta",
    AgentType.TESTER: "blue",
    AgentType.GENERAL: "white",
}

# Agent state modifications
def get_agent_color(agent: Agent) -> str:
    base_color = AGENT_COLORS.get(agent.inferred_type, "white")
    if agent.state == "zombie":
        # Blend with green for zombie effect
        return blend_colors(base_color, "green", ratio=0.5)
    return base_color

# Structure symbols by type
STRUCTURE_SYMBOLS = {
    StructureType.HOUSE: "∩",      # Roof shape
    StructureType.WORKSHOP: "◊",   # Diamond
    StructureType.LIBRARY: "⌂",     # House with chimney
    StructureType.FORGE: "▲",      # Triangle (forge)
    StructureType.TOWER: "⎔",      # Tower shape
    StructureType.ROAD: "#",       # Hash (paved)
    StructureType.WELL: "○",       # Circle (well)
}

# Structure colors by material
MATERIAL_COLORS = {
    "wood": "brown",
    "stone": "gray",
    "brick": "red",
}

# Stage progression symbols
STAGE_SYMBOLS = {
    0: "░",  # Foundation (light shade)
    1: "▒",  # Frame (medium shade)
    2: "▓",  # Complete (dark shade)
    3: "█",  # Enhanced (full block)
}

def get_structure_symbol(structure: Structure) -> str:
    """Get display symbol for a structure."""
    base_symbol = STRUCTURE_SYMBOLS.get(structure.type, "#")
    # Roads use stage symbols; others use type symbols
    if structure.type == StructureType.ROAD:
        return STAGE_SYMBOLS.get(structure.stage, "#")
    return base_symbol

def get_structure_color(structure: Structure) -> str:
    """Get display color for a structure."""
    return MATERIAL_COLORS.get(structure.material, "white")
```

### Animation System

```python
class AnimationManager:
    """Manages animation frames for active agents."""
    
    FRAME_RATE = 4  # Hz, for spin animation
    
    def __init__(self):
        self._frame = 0
        self._last_update = time.time()
    
    def update(self) -> None:
        """Update animation frame based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        if elapsed >= 1.0 / self.FRAME_RATE:
            self._frame = (self._frame + 1) % 4
            self._last_update = now
    
    def get_spin_symbol(self) -> str:
        """Get current spin animation symbol."""
        symbols = ["-", "\\", "|", "/"]
        return symbols[self._frame]

def get_agent_display(agent: Agent, animation: AnimationManager) -> Tuple[str, str]:
    """
    Get the display symbol and color for an agent.
    
    Returns:
        (symbol, color)
    """
    color = get_agent_color(agent)
    
    if agent.state == "active":
        # Show spin animation for active agents
        symbol = animation.get_spin_symbol()
    else:
        # Static @ for idle/zombie
        symbol = "@"
    
    return symbol, color
```

### Textual Implementation

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Container
from textual.reactive import reactive

class WorldView(Static):
    """Widget that renders the world view."""
    
    def __init__(self, world_state: WorldStateManager, viewport: ViewportManager):
        super().__init__()
        self._world_state = world_state
        self._viewport = viewport
        self._animation = AnimationManager()
    
    def on_mount(self) -> None:
        """Set up periodic refresh."""
        self.set_interval(1/30, self.refresh)  # 30 FPS
    
    def render(self) -> str:
        """Render the world view."""
        self._animation.update()
        
        # Get visible bounds
        bounds = self._viewport.get_visible_bounds()
        
        # Get entities in view
        agents = await self._world_state.get_agents_in_view(bounds)
        structures = await self._world_state.get_structures_in_view(bounds)
        
        # Build display buffer
        lines = []
        for y in range(bounds.min_y, bounds.max_y + 1):
            row = []
            for x in range(bounds.min_x, bounds.max_x + 1):
                world_pos = Position(x, y)
                screen_pos = self._viewport.world_to_screen(world_pos)
                
                # Check for entities at this position
                char, color = self._get_cell_content(world_pos, agents, structures)
                row.append((char, color))
            lines.append(row)
        
        # Convert to Rich renderable
        return self._render_lines(lines)
    
    def _get_cell_content(self, pos: Position, agents: List[Agent], 
                           structures: List[Structure]) -> Tuple[str, str]:
        """Get character and color for a cell."""
        # Check agents first (higher priority)
        for agent in agents:
            if agent.position == pos:
                return get_agent_display(agent, self._animation)
        
        # Check structures
        for structure in structures:
            if structure.position == pos:
                symbol = get_structure_symbol(structure)
                color = get_structure_color(structure)
                return symbol, color
        
        # Empty space
        return ".", "white"
    
    def _render_lines(self, lines: List[List[Tuple[str, str]]]) -> str:
        """Convert display buffer to renderable string."""
        # Use Rich Text for colors
        from rich.text import Text
        text = Text()
        for row in lines:
            for char, color in row:
                text.append(char, style=color)
            text.append("\n")
        return text

class StatusBar(Static):
    """Widget that shows status information."""
    
    agent_count = reactive(0)
    structure_count = reactive(0)
    project_name = reactive("")
    viewport_pos = reactive((0, 0))
    
    def render(self) -> str:
        return (
            f"Agents: {self.agent_count} │ "
            f"Structures: {self.structure_count} │ "
            f"Project: {self.project_name} │ "
            f"({self.viewport_pos[0]}, {self.viewport_pos[1]})"
        )

class EventLog(Static):
    """Widget that shows recent events."""
    
    events = reactive([])
    max_lines = reactive(5)
    
    def render(self) -> str:
        lines = []
        for event in self.events[-self.max_lines:]:
            timestamp = event.timestamp.strftime("%H:%M:%S")
            lines.append(f"[{timestamp}] {event.summary}")
        return "\n".join(lines)

class HamletApp(App):
    """Main Textual application."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1fr 20fr 5fr;
    }
    
    StatusBar {
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    
    WorldView {
        background: $background;
        color: $text;
    }
    
    EventLog {
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "scroll_left", "Scroll Left"),
        ("l", "scroll_right", "Scroll Right"),
        ("k", "scroll_up", "Scroll Up"),
        ("j", "scroll_down", "Scroll Down"),
        ("?", "toggle_legend", "Legend"),
        ("f", "toggle_follow", "Follow"),
    ]
    
    def __init__(self, world_state: WorldStateManager, viewport: ViewportManager):
        super().__init__()
        self._world_state = world_state
        self._viewport = viewport
    
    def compose(self) -> ComposeResult:
        yield StatusBar()
        yield WorldView(self._world_state, self._viewport)
        yield EventLog()
    
    def on_mount(self) -> None:
        """Set up state polling."""
        self.set_interval(1/30, self._update_state)  # 30 FPS
    
    async def _update_state(self) -> None:
        """Poll world state and update display."""
        # Update status bar
        villages = await self._world_state.get_all_villages()
        if villages:
            primary = villages[0]
            agents = await self._world_state.get_agents_by_village(primary.id)
            structures = await self._world_state.get_structures_by_village(primary.id)
            
            self.query_one(StatusBar).agent_count = len(agents)
            self.query_one(StatusBar).structure_count = len(structures)
            self.query_one(StatusBar).project_name = primary.name
            self.query_one(StatusBar).viewport_pos = (
                self._viewport.center.x,
                self._viewport.center.y
            )
        
        # Update event log
        events = await self._world_state.get_event_log(limit=100)
        self.query_one(EventLog).events = events
    
    def action_scroll_left(self) -> None:
        self._viewport.scroll(-1, 0)
    
    def action_scroll_right(self) -> None:
        self._viewport.scroll(1, 0)
    
    def action_scroll_up(self) -> None:
        self._viewport.scroll(0, -1)
    
    def action_scroll_down(self) -> None:
        self._viewport.scroll(0, 1)
    
    def action_toggle_legend(self) -> None:
        # Toggle legend overlay
        pass
    
    def action_toggle_follow(self) -> None:
        # Toggle follow mode
        pass
```

### Input Handling

```
┌─────────────────────────────────────────────────────────────┐
│                    KEY BINDINGS                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Arrow keys / hjkl: Scroll viewport                         │
│  f: Toggle follow mode (follow active agent)               │
│  ?: Toggle legend overlay                                   │
│  q: Quit application                                        │
│  /: Focus event log for scrolling                           │
│  Esc: Return to world view from overlays                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Frame Rate Management

The TUI refreshes at a fixed frame rate, independent of event arrival:

```python
class HamletApp(App):
    def on_mount(self) -> None:
        # Main render loop at 30 FPS
        self.set_interval(1/30, self._refresh_world)
        
        # State polling at 10 FPS (for log updates)
        self.set_interval(1/10, self._refresh_state)
    
    async def _refresh_world(self) -> None:
        """Refresh world view."""
        self.query_one(WorldView).refresh()
    
    async def _refresh_state(self) -> None:
        """Poll world state for updates."""
        # Update viewport auto-follow
        await self._viewport.update()
        
        # Update status bar
        # Update event log
```
