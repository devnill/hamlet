#!/usr/bin/env python3
"""Generate sprite PNG assets for the Kitty renderer from mockup source tiles.

Reads 96×96 mockup tiles (6× upscale from 16×16), downsamples with
NEAREST resampling to recover the original pixel art, applies background
transparency for non-terrain sprites, and creates colour variants of
the base agent sprite for each agent type.

Library, Tower, and Well are generated programmatically.

Run from the project root:
    python3 scripts/generate_sprites.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

MOCKUP_DIR = Path("specs/steering/research/mockups")
ASSETS_DIR = Path("src/hamlet/gui/kitty/assets")

# Agent type → tunic colour (RGB)
AGENT_COLOURS: dict[str, tuple[int, int, int]] = {
    "general": (220, 220, 220),   # white / silver
    "researcher": (50, 100, 210),  # blue  (matches base mockup)
    "coder": (210, 200, 30),       # yellow
    "architect": (200, 30, 200),   # magenta
    "tester": (30, 180, 180),      # teal
    "planner": (20, 110, 40),      # dark green
    "executor": (210, 40, 40),     # red
}

# Base tunic colour in the mockup agent (researcher / blue)
_BASE_TUNIC = (50, 100, 210)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bg_colors(path: Path) -> list[tuple[int, int, int]]:
    """Return the four corner pixel colours of the image as background reference.

    Corner-only sampling avoids accidentally including sprite content that
    reaches a tile edge (e.g. road surfaces exiting the left/right edge).
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    corners = [
        img.getpixel((0, 0)),
        img.getpixel((w - 1, 0)),
        img.getpixel((0, h - 1)),
        img.getpixel((w - 1, h - 1)),
    ]
    # Deduplicate while preserving order
    seen: set[tuple[int, int, int]] = set()
    result = []
    for c in corners:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _remove_bg(
    img: Image.Image,
    bg_colors: list[tuple[int, int, int]],
    tolerance: int = 28,
) -> Image.Image:
    """Replace background-coloured pixels with transparency (flood fill from corners)."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size

    def _is_bg(r: int, g: int, b: int) -> bool:
        return any(
            abs(r - br) < tolerance
            and abs(g - bg) < tolerance
            and abs(b - bb) < tolerance
            for br, bg, bb in bg_colors
        )

    # BFS flood fill from all four corners
    from collections import deque
    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        cx, cy = corner
        r, g, b, a = px[cx, cy]
        if _is_bg(r, g, b):
            queue.append(corner)
            visited.add(corner)

    while queue:
        x, y = queue.popleft()
        r, g, b, a = px[x, y]
        if _is_bg(r, g, b):
            px[x, y] = (r, g, b, 0)
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    return img


def _swap_colour(
    img: Image.Image,
    source: tuple[int, int, int],
    target: tuple[int, int, int],
    tolerance: int = 45,
) -> Image.Image:
    """Replace pixels close to *source* colour with *target* colour."""
    img = img.convert("RGBA")
    px = img.load()
    sr, sg, sb = source
    tr, tg, tb = target
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            dist = ((r - sr) ** 2 + (g - sg) ** 2 + (b - sb) ** 2) ** 0.5
            if dist < tolerance:
                px[x, y] = (tr, tg, tb, a)
    return img


def _save(img: Image.Image, name: str) -> None:
    path = ASSETS_DIR / name
    img.save(path)
    print(f"  {name}")


def _downsample(path: Path, target: int, transparent: bool, bg_colors: list) -> Image.Image:
    """Load 96×96 mockup, downsample to *target*×*target*, optionally remove bg."""
    img = Image.open(path)
    if transparent:
        # Remove background at full resolution for cleaner edges
        img = _remove_bg(img.convert("RGBA"), bg_colors)
    else:
        img = img.convert("RGBA")
    return img.resize((target, target), Image.NEAREST)


# ---------------------------------------------------------------------------
# Programmatic sprites — Library, Tower, Well
# ---------------------------------------------------------------------------

def _make_library_16() -> Image.Image:
    """2-tile Library rendered into 16×16 (single-tile footprint for the renderer)."""
    # Colours
    ROOF   = (80, 100, 140)   # blue-grey slate
    DROOF  = (50,  70, 110)   # dark roof / ridge
    WALL   = (130,  80,  40)  # warm brown wall
    DWALL  = ( 90,  50,  20)  # dark outline / shadow
    WIN    = (255, 220,  80)  # lit window
    DOOR   = ( 30,  15,   5)  # dark doorway
    BASE   = (110,  60,  20)  # foundation

    T = (0, 0, 0, 0)  # transparent
    def c(r, g, b): return (r, g, b, 255)

    rows = [
        # x: 0123456789012345
        [T,T,c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),T,T],
        [T,c(*DROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*DROOF),T],
        [T,c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),T],
        [T,c(*ROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*DROOF),c(*ROOF),T],
        [T,T,c(*DWALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*WIN),c(*WIN),c(*DWALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*DWALL),c(*WIN),c(*WIN),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*WIN),c(*WIN),c(*DWALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*DWALL),c(*WIN),c(*WIN),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*DWALL),c(*DWALL),c(*DWALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*DWALL),c(*DWALL),c(*DWALL),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*WIN),c(*WIN),c(*DWALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*DWALL),c(*WIN),c(*WIN),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*WIN),c(*WIN),c(*DWALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*DWALL),c(*WIN),c(*WIN),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*DWALL),c(*DWALL),c(*DWALL),c(*WALL),c(*WALL),c(*WALL),c(*WALL),c(*DWALL),c(*DWALL),c(*DWALL),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*WALL),c(*WALL),c(*DWALL),c(*WALL),c(*DOOR),c(*DOOR),c(*WALL),c(*DWALL),c(*WALL),c(*WALL),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*WALL),c(*WALL),c(*DWALL),c(*WALL),c(*DOOR),c(*DOOR),c(*WALL),c(*DWALL),c(*WALL),c(*WALL),c(*DWALL),T,T],
        [T,T,c(*DWALL),c(*WALL),c(*WALL),c(*DWALL),c(*WALL),c(*DOOR),c(*DOOR),c(*WALL),c(*DWALL),c(*WALL),c(*WALL),c(*DWALL),T,T],
        [T,T,c(*BASE),c(*BASE),c(*BASE),c(*BASE),c(*BASE),c(*BASE),c(*BASE),c(*BASE),c(*BASE),c(*BASE),c(*BASE),c(*BASE),T,T],
        [T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T],
    ]
    img = Image.new("RGBA", (16, 16))
    for y, row in enumerate(rows):
        for x, pixel in enumerate(row):
            img.putpixel((x, y), pixel)
    return img


def _make_tower_16() -> Image.Image:
    """Tall stone tower in 16×16."""
    ROOF  = ( 90,  90,  90)  # dark grey pointed roof
    STONE = (150, 150, 150)  # light stone
    DSTON = (100, 100, 100)  # dark stone / mortar
    WIN   = (255, 220,  80)  # window
    DOOR  = ( 30,  15,   5)  # doorway

    T = (0, 0, 0, 0)
    def c(r, g, b): return (r, g, b, 255)

    rows = [
        [T,T,T,T,T,T,T,c(*ROOF),c(*ROOF),T,T,T,T,T,T,T],
        [T,T,T,T,T,T,c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),T,T,T,T,T,T],
        [T,T,T,T,T,c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),c(*ROOF),T,T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*WIN), c(*WIN), c(*WIN), c(*WIN), c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*WIN), c(*WIN), c(*WIN), c(*WIN), c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*WIN), c(*WIN), c(*WIN), c(*WIN), c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*WIN), c(*WIN), c(*WIN), c(*WIN), c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*STONE),c(*DOOR), c(*DOOR), c(*STONE),c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*STONE),c(*STONE),c(*DOOR), c(*DOOR), c(*STONE),c(*STONE),c(*DSTON),T,T,T,T],
        [T,T,T,T,c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),T,T,T,T],
    ]
    img = Image.new("RGBA", (16, 16))
    for y, row in enumerate(rows):
        for x, pixel in enumerate(row):
            img.putpixel((x, y), pixel)
    return img


def _make_well_16() -> Image.Image:
    """Stone well with water visible inside, 16×16."""
    STONE = (150, 150, 150)
    DSTON = (100, 100, 100)
    WATER = ( 60, 130, 220)
    DWATR = ( 30,  70, 150)
    WOOD  = (140,  90,  40)
    DWOOD = ( 90,  55,  20)

    T = (0, 0, 0, 0)
    def c(r, g, b): return (r, g, b, 255)

    rows = [
        [T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T],
        [T,T,T,T,c(*WOOD),c(*WOOD),c(*WOOD),c(*WOOD),c(*WOOD),c(*WOOD),c(*WOOD),c(*WOOD),T,T,T,T],
        [T,T,T,T,c(*DWOOD),c(*DWOOD),c(*DWOOD),c(*DWOOD),c(*DWOOD),c(*DWOOD),c(*DWOOD),c(*DWOOD),T,T,T,T],
        [T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T],
        [T,T,c(*STONE),c(*DSTON),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*DSTON),c(*STONE),T,T],
        [T,T,c(*STONE),c(*WATER),c(*DWATR),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*DWATR),c(*WATER),c(*STONE),T,T],
        [T,T,c(*STONE),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*STONE),T,T],
        [T,T,c(*STONE),c(*WATER),c(*WATER),c(*WATER),c(*DWATR),c(*DWATR),c(*DWATR),c(*DWATR),c(*WATER),c(*WATER),c(*WATER),c(*STONE),T,T],
        [T,T,c(*STONE),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*STONE),T,T],
        [T,T,c(*STONE),c(*DSTON),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*WATER),c(*DSTON),c(*STONE),T,T],
        [T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T],
        [T,T,c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),T,T],
        [T,T,c(*DSTON),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*STONE),c(*DSTON),T,T],
        [T,T,T,c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),c(*DSTON),T,T,T],
        [T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T],
        [T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T],
    ]
    img = Image.new("RGBA", (16, 16))
    for y, row in enumerate(rows):
        for x, pixel in enumerate(row):
            img.putpixel((x, y), pixel)
    return img


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Detect grass background colours (shared by most mockup tiles)
    grass_path = MOCKUP_DIR / "hamlet_v4_grass.png"
    bg_colors = _bg_colors(grass_path)

    print("=== Terrain tiles ===")
    terrain_map = {
        "plain":    "hamlet_v4_grass.png",
        "water":    "hamlet_v4_water.png",
        "mountain": "hamlet_v4_mountain.png",
        "forest":   "hamlet_v4_forest.png",
        "meadow":   "hamlet_v4_meadow.png",
    }
    for ttype, fname in terrain_map.items():
        for size in (16, 8):
            img = Image.open(MOCKUP_DIR / fname).convert("RGB")
            tile = img.resize((size, size), Image.NEAREST)
            _save(tile, f"terrain_{ttype}_{size}.png")

    print("\n=== Structure tiles (from mockups) ===")
    structure_mockups = {
        "house":    "hamlet_v4_house.png",
        "workshop": "hamlet_v4_workshop.png",
        "forge":    "hamlet_v4_forge.png",
    }
    for stype, fname in structure_mockups.items():
        for size in (16, 8):
            img16 = _downsample(MOCKUP_DIR / fname, 16, transparent=True, bg_colors=bg_colors)
            if size == 16:
                tile = img16
            else:
                tile = img16.resize((size, size), Image.NEAREST)
            _save(tile, f"structure_{stype}_0_{size}.png")

    print("\n=== Structure tiles (road from strip) ===")
    # Road strip is 294×96 — three tiles each ~98px wide.
    # Use the center tile (vertical road).
    road_strip = Image.open(MOCKUP_DIR / "hamlet_v4_road_tiles.png")
    tile_w = road_strip.width // 3  # 98px
    road_crop = road_strip.crop((tile_w, 0, tile_w * 2, road_strip.height))
    # Downsample to 16×16 first, then detect bg from the downsampled corners
    road16_raw = road_crop.convert("RGBA").resize((16, 16), Image.NEAREST)
    # Sample corner pixels of the 16×16 tile for background detection
    road_bg_colors = [road16_raw.getpixel((x, y)) for x, y in [(0,0),(15,0),(0,15),(15,15)]]
    road_bg_rgb = [(r, g, b) for r, g, b, *_ in road_bg_colors]
    for size in (16, 8):
        tile = _remove_bg(road16_raw.copy(), road_bg_rgb)
        if size == 8:
            tile = tile.resize((8, 8), Image.NEAREST)
        _save(tile, f"structure_road_0_{size}.png")

    print("\n=== Structure tiles (programmatic: library, tower, well) ===")
    for stype, maker in [("library", _make_library_16), ("tower", _make_tower_16), ("well", _make_well_16)]:
        img16 = maker()
        img8 = img16.resize((8, 8), Image.NEAREST)
        _save(img16, f"structure_{stype}_0_16.png")
        _save(img8, f"structure_{stype}_0_8.png")

    print("\n=== Agent tiles (colour variants) ===")
    agent_path = MOCKUP_DIR / "hamlet_v4_agent.png"
    agent_bg = _bg_colors(agent_path)

    # Build base agent at 16×16 with background removed (this is researcher / blue)
    base16 = _downsample(agent_path, 16, transparent=True, bg_colors=agent_bg)

    for atype, target_rgb in AGENT_COLOURS.items():
        # Swap the blue tunic to the target colour (skip for researcher — it's already correct)
        if atype == "researcher":
            img16 = base16.copy()
        else:
            img16 = _swap_colour(base16.copy(), _BASE_TUNIC, target_rgb)
        img8 = img16.resize((8, 8), Image.NEAREST)
        for frame in range(4):  # same sprite for all 4 frames (animation deferred)
            _save(img16, f"agent_{atype}_{frame}_16.png")
            _save(img8, f"agent_{atype}_{frame}_8.png")

    total = len(list(ASSETS_DIR.glob("*.png")))
    print(f"\nDone — {total} sprite files written to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
