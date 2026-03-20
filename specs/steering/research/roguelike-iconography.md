# Roguelike ASCII Iconography Research

**Note: This research is based on training knowledge (cutoff: January 2025). No live web sources were consulted.**

---

## Summary

Roguelike games use a consistent visual language built on ASCII characters, with conventions that have evolved across decades. The primary patterns include: using initial letters for entity types (`d` for dog, `g` for goblin), symbol characters for terrain and objects (`#` for walls, `.` for floors), and color coding to convey state and faction. Most roguelikes follow similar conventions for player representation (`@`), but differ in how they handle activity visualization and UI layout. Classic roguelikes like NetHack, ADOM, Dwarf Fortress, and Caves of Qud share common patterns but each has unique approaches to representing world state, combat, and player feedback.

---

## 1. Character Representations

### Player Character

| Game | Symbol | Notes |
|------|--------|-------|
| NetHack | `@` | The universal "at sign" convention, resembles human figure |
| ADOM | `@` | Same convention |
| Dwarf Fortress | Varies by creature type | In fortress mode, dwarves use species symbol |
| Caves of Qud | `@` | Standard convention |
| CDDA (Cataclysm) | `@` | Standard convention |
| Rogue (original) | `@` | Origin of the convention |

The `@` symbol is the near-universal representation for the player character in roguelikes. The shape vaguely resembles a human figure seen from above.

### NPCs and Creatures

**NetHack Letter-Based System:**

NetHack uses a systematic letter scheme where the first letter indicates creature category:

| Letter | Category | Examples |
|--------|----------|----------|
| `a` | Ants, insects | giant ant, killer bee |
| `b` | Bats, birds | bat, raven, giant bat |
| `c` | Canines | dog, wolf, jackal, coyote |
| `d` | Dragons | red dragon, blue dragon |
| `e` | Elementals, eyes | floating eye, fire elemental |
| `f` | Felines | cat, tiger, lion, panther |
| `g` | Goblins, gremlins | goblin, gremlin, hobgoblin |
| `h` | Humanoids | dwarf, elf, human, gnome |
| `i` | Imps, insects | imp, quasit |
| `j` | Jellies | jelly, gelatinous cube |
| `k` | Kobolds | kobold, large kobold |
| `l` | Leprechauns, lich | leprechaun, lich |
| `m` | Mimics, molds | mimic, brown mold |
| `n` | Nymphs | water nymph, wood nymph |
| `o` | Orcs, ogres | orc, ogre, hill orc |
| `p` | Puddings | brown pudding, black pudding |
| `q` | Quadrupeds | horse, pony, warhorse |
| `r` | Rodents | rat, sewer rat, giant rat |
| `s` | Spiders, snakes | spider, cave spider, snake |
| `t` | Trolls | troll, ice troll |
| `u` | Underworld creatures | umber hulk |
| `v` | Vampires | vampire bat, vampire |
| `w` | Worms, wargs | warg, purple worm |
| `x` | Xorn | xorn |
| `y` | Lights | yellow light, gas spore |
| `z` | Zombified | zombie, ghoul, mummy |

**Uppercase for Significant Creatures (NetHack):**

| Letter | Category | Examples |
|--------|----------|----------|
| `A` | Angels | angel, Archon |
| `B` | Bats (large) | giant bat |
| `C` | Centaurs | centaur, forest centaur |
| `D` | Dragons | dragon (large form) |
| `E` | Elementals | air elemental, fire elemental |
| `F` | Fungi | fungus, mold |
| `G` | Gnomes | gnome, gnome lord |
| `H` | Giants | giant, hill giant, fire giant |
| `I` | Invisible | invisible stalker |
| `J` | Jellyfish | killer bee queen |
| `K` | Kestrels | kestral |
| `L` | Lichs | lich, demilich |
| `M` | Mummies | mummy, mummy lord |
| `N` | Nagas | naga, guardian naga |
| `O` | Ogres | ogre, ogre lord |
| `P` | Purple worms | purple worm |
| `Q` | Quantum | quantum mechanic |
| `R` | Rust monsters | rust monster |
| `S` | Snakes | snake, python |
| `T` | Trolls | troll, rock troll |
| `U` | Unicorns | unicorn, gray unicorn |
| `V` | Vampires | vampire lord |
| `W` | Wraiths | wraith, barrow wight |
| `X` | Xorns | xorn |
| `Y` | Apes | ape, carnivorous ape |
| `Z` | Zruty | zruty |

**Special symbols (NetHack):**

| Symbol | Category | Examples |
|--------|----------|----------|
| `@` | Humans | player, human NPCs, @-monsters |
| `&` | Demons | all demons and devils use ampersand |
| `'` | Nymphs | alternate nymph representation |
| `8` | Golems | all golem types |

**Dwarf Fortress Creature Symbols:**

Dwarf Fortress uses the creature's species initial for most beings, with color variations for status:

| Symbol | Creature | Color |
|--------|----------|-------|
| `d` | Dwarf | Cyan/gray (citizens), red (hostile) |
| `e` | Elf | Green |
| `g` | Goblin | Dark green |
| `k` | Kobold | Gray/dark |
| `H` | Human | Brown (capitalized for civilized) |
| `u` | Underground creature | Various |
| `o` | Ogre | Dark |
| `b` | Bird | Various |
| `c` | Cat/dog | Brown/gray/white |

**Caves of Qud:**

| Convention | Usage |
|------------|-------|
| `@` | Player character |
| Lowercase letters | Common creatures |
| Uppercase letters | Named/uniques/bosses |
| Colors | Indicate faction and status |

**ADOM (Ancient Domains of Mystery):**

| Symbol | Entity | Notes |
|--------|--------|-------|
| `@` | Player | Standard |
| `h` | Humanoid | Various types |
| `g` | Goblin | Hostile |
| `D` | Dragon | Boss-type, uppercase |
| `w` | Worm | Enemy |
| `T` | Giant | Large enemy, uppercase |
| `M` | Monster | Generic boss |
| `_` | Neutral NPC | Shopkeeper, trainer |

### Color Differentiation for Creatures

**Standard faction colors (most roguelikes):**

| Color | Primary Meaning | Secondary Meanings |
|-------|-----------------|-------------------|
| White | Neutral, default | Peaceful creatures, clouds |
| Gray | Object/feature | Statues, constructs, inactive |
| Cyan | Friendly/ally | Player allies, water creatures |
| Green | Nature/benign | Plants, friendly NPCs |
| Yellow | Alert/valuable | Active threats, gold |
| Red | Hostile/danger | Enemies, fire, lava |
| Magenta | Special/magical | Unique creatures, artifacts |
| Blue | Cold/magic | Ice, magical effects |

**Dwarf Fortress color system:**

| Color | Status |
|-------|--------|
| Cyan | Citizen, friendly |
| Red | Hostile, enemy |
| Yellow | Neutral |
| Gray | Dead, inactive |
| Green | On-duty military |
| Blue | On break, idle |

---

## 2. Action/State Visualization

### Status Indicators via Symbol Modification

**NetHack status effects:**

| State | Symbol/Indicator | Visual Effect |
|-------|-------------------|---------------|
| Sleeping | `Z` overlay or creature doesn't move | Sleep animation in some variants |
| Paralyzed | `!` overlay or immobile | Exclamation indicates stunned state |
| Stoned | Creature turns gray | Gradual petrification visual |
| Poisoned | Green coloring | Health bar affected |
| Blind | `I` symbol or darkened | Invisible creatures show as `I` |
| Invisible | `I` | Visible only with detection |
| Confused | `?` or erratic movement | Movement pattern indicates confusion |
| Stunned | `*` or erratic movement | Stars or random movement |
| Hallucinating | Random symbols | All creatures appear randomly |
| Polymorphed | Different symbol | Transformed into new form |

**Dwarf Fortress activity states:**

| State | Visual Indicator |
|-------|------------------|
| Sleeping | `Z` character, cyan color |
| Eating | Food symbol + creature |
| Drinking | Beverage symbol + creature |
| Working | Flashing, task icons |
| On Break | Blue color, idle symbols |
| Military training | `T` task indicator |
| Wounded | Red cross or health indicator |
| Unconscious | `u` or creature on ground |
| Dead | Corpse symbol `X` or `%` |

**Common roguelike state symbols:**

| State | Symbol | Notes |
|-------|--------|-------|
| Sleeping | `Z` or `z` | Resembles "zzz" |
| Paralyzed | `!` | Exclamation for alert |
| Confused | `?` | Question for uncertainty |
| Stunned | `*` | Stars for disorientation |
| Invisible | `I` or not shown | Detection reveals |
| Blinded | Darkened or `;` | Semi-visible indication |

### Combat Visualization

| Action | Typical Symbol | Animation |
|--------|----------------|-----------|
| Attack | Flash, particle burst | `*`, `#` burst |
| Hit | Direction indicator, target flash | Brief highlight |
| Miss | `-` or no visual | No effect |
| Death | `X` (corpse) or `%` (remains) | Remains appear |
| Projectile | Arrow traveling | `>`, `-`, `|` path |
| Magic | `+`, `*`, colored particles | Spell effect |
| Explosion | Expanding `*` symbols | Area effect |

### Activity Animation

**Basic movement feedback:**
- **Discrete jumps** - Character instantly moves from tile to tile (classic approach)
- **Trail effect** - Brief afterimage (`@` leaves faint `.` behind)
- **Arrow/projectile paths** - Symbols travel visibly
- **Movement direction indicators** - Some games show facing with `^v<>`

**Idle animation:**
- Most roguelikes use static symbols when idle
- Dwarf Fortress shows dwarves with activity icons
- Caves of Qud uses subtle color shifts

**Activity cycling patterns:**

| Activity | Animation Pattern |
|----------|-------------------|
| Working | Spin cycle: `-` `\` `|` `/` |
| Progress | Fill: `.` `:` `o` `O` `@` |
| Waiting | Blink at 1-2 Hz |
| Processing | Pulsing brightness |
| Charging | Progress bar fill |

---

## 3. World/Building Representation

### Terrain Symbols

**Universal/Standard terrain:**

| Symbol | Meaning | Notes |
|--------|---------|-------|
| `.` | Floor/ground | Open walkable space |
| `#` | Wall/corridor | Solid barrier |
| `"` | Grass/vegetation | Outdoor terrain |
| `~` | Water | Rivers, lakes, seas |
| `_` | Altar, throne | Special locations |
| `>` | Stairs down | Level transition |
| `<` | Stairs up | Level transition |
| `|` | Door (closed, vertical) | Vertical orientation |
| `-` | Door (horizontal) | Horizontal orientation |
| `+` | Door (closed, alternate) | Some games use this |
| `'` | Open door | Passable |
| `=` | Bridge/platform | Over water |
| `{` | Fountain | Water source |
| `}` | Pool/moat | Water hazard |
| `^` | Trap | Hidden or visible trap |
| `*` | Gold/treasure | Valuables |
| `$` | Money | Currency |

**Dwarf Fortress terrain (extensive):**

| Symbol | Meaning |
|--------|---------|
| `.` | Open space, floor |
| `#` | Ramp (up/down) |
| `>` | Stairs down |
| `<` | Stairs up |
| `"` | Rough floor |
| `~` | Water |
| `≈` | Flowing water |
| Box drawing | Walls (`╔═╗║╚╝`) |
| `O` | Tree (overground) |
| `T` | Tower-Cap (underground tree) |

**ADOM terrain:**

| Symbol | Meaning |
|--------|---------|
| `.` | Floor |
| `#` | Wall |
| `>` | Stairs down |
| `<` | Stairs up |
| `~` | Water |
| `"` | Grass |
| `*` | Gold/gems |
| `+` | Closed door |
| `-` | Open door |
| `^` | Trap |

### Built Structures

**Buildings and constructed objects:**

| Symbol | Meaning | Usage |
|--------|---------|-------|
| `□` | Building outline | Workshop/furnace area |
| `○` | Barrel/pot | Storage container |
| `≡` | Anvil/forge | Smithing equipment |
| `∞` | Workshop | DF specific |
| `╬` | Well | Water access |
| `¶` | Altar/shrine | Religious site |
| `┼` | Table/workstation | Crafting |
| `╔══╗` | Room outline | Structure walls |

**Dwarf Fortress workshops (3x3 structures):**

| Symbol | Workshop |
|--------|----------|
| `≡` | Mason |
| `∞` | Craftsdwarf |
| `Θ` | Kitchen |
| `¥` | Trade depot (5x5) |
| `±` | Butcher shop |

### Items and Objects

| Symbol | Typical Use | Notes |
|--------|-------------|-------|
| `/` | Weapon | Sword, axe |
| `|` | Polearm/staff | Long weapons |
| `!` | Potion | Drinkable |
| `?` | Scroll | Readable |
| `=` | Ring | Jewelry |
| `"` | Amulet | Neck item |
| `(` | Tool | Utility |
| `)` | Weapon (alternate) | Some variants |
| `+` | Spellbook | Magic |
| `0` | Armor (suit) | Full armor |
| `[` | Armor (piece) | Armor parts |
| `%` | Food/corpse | Consumable |
| `*` | Gem/gold | Valuables |
| `$` | Money | Currency |

---

## 4. Animation Patterns

### Movement Animation

**Basic movement feedback:**
- **Discrete jumps** - Character instantly moves from tile to tile (classic approach)
- **Trail effect** - Brief afterimage (`@` leaves faint `.` behind)
- **Arrow/projectile paths** - Symbols travel visibly (`-`, `|`, `/`, `\`, `>`)
- **Movement direction indicators** - Some games show facing

**Idle animation:**
- Most roguelikes use static symbols when idle
- Dwarf Fortress shows dwarves with activity icons (pick, bucket, etc.)
- Caves of Qud uses subtle color shifts

### Spinning/Working Animation

The classic roguelike working indicator cycles through 4 characters:

| Frame | Symbol | Rotation |
|-------|--------|----------|
| 1 | `-` | Horizontal |
| 2 | `\` | Diagonal down |
| 3 | `|` | Vertical |
| 4 | `/` | Diagonal up |

Animation rate: 2-4 Hz typical

### Progress Fill Characters

**Block progression (most common):**
```
░  Light shade (25%)
▒  Medium shade (50%)
▓  Dark shade (75%)
█  Full block (100%)
```

**Bar fill progression:**
```
[        ]  0%
[░       ]  12.5%
[░░      ]  25%
[░░░     ]  37.5%
[░░░░    ]  50%
[░░░░░   ]  62.5%
[░░░░░░  ]  75%
[░░░░░░░ ]  87.5%
[░░░░░░░░]  100%
```

**Braille patterns (smooth progress):**
```
⡀ ⣀ ⣄ ⣤ ⣦ ⣶ ⣷ ⣾ ⣽ ⣻
```

### Environmental Animation

| Element | Animation |
|---------|-----------|
| Flowing water | `≈` characters shift/flow |
| Fire | `^` or `*` flickers, colors cycle red/yellow/orange |
| Smoke | `░` or `▒` drifts upward |
| Magic effects | `+` or `*` particles |
| Weather | `*` rain, `"` snow, `~` wind |
| Light sources | Glow effect (color gradient in tilesets) |

---

## 5. UI Layout Patterns

### Classic NetHack Layout

```
┌────────────────────────────────────────┐
│                                        │
│           MAIN MAP VIEW                │
│         (majority of screen)           │
│                                        │
│                                        │
│                                        │
│                                        │
│                                        │
├────────────────────────────────────────┤
│ HP:50/50 AC:5 Xp:1 T:12345 │ Status line │
├────────────────────────────────────────┤
│ Message: "You see here a potion."     │
│ Message history (scrolling)            │
└────────────────────────────────────────┘
```

**Components:**
1. **Main map** - 80%+ of screen, centered on player
2. **Status line(s)** - Bottom, one or two lines showing stats
3. **Message log** - Bottom, last 1-3 messages visible, scrollable history
4. **Menu overlays** - Inventory, stats, etc. appear as overlays

### Dwarf Fortress Layout

```
┌────────────────────────────────────────┐
│ ┌──────────────┐ ┌───────────────────┐ │
│ │              │ │                   │ │
│ │   MAIN MAP   │ │   SIDE PANEL     │ │
│ │              │ │   (unit list,    │ │
│ │   (centered  │ │   announcements)  │ │
│ │    view)     │ │                   │ │
│ │              │ │                   │ │
│ └──────────────┘ └───────────────────┘ │
├────────────────────────────────────────┤
│ Status: Urists  •  Food: 123  •  ...  │
├────────────────────────────────────────┤
│ ┌────────────────────────────────────┐ │
│ │ Announcement/Event Log              │ │
│ │ (scrolling, filterable)             │ │
│ └────────────────────────────────────┘ │
└────────────────────────────────────────┘
```

**DF Layout components:**
1. **Main map** - Left/center, shows fortress or adventurer location
2. **Side panel** - Right side, shows unit list, menu options, or details
3. **Status bar** - Shows key metrics (wealth, population, alerts)
4. **Announcement log** - Bottom, scrolling log of events
5. **Context menus** - Overlay menus for specific actions

**DF Screen zones:**
- **Map area** - Primary gameplay view
- **Sidebar** - Dynamic context (z-level, units, build menu)
- **Status line** - Quick metrics
- **Announcement area** - Event log

### ADOM Layout

```
┌────────────────────────────────────────┐
│ ┌────────────────────────────────────┐ │
│ │                                    │ │
│ │         MAIN MAP VIEW              │ │
│ │         (full width)               │ │
│ │                                    │ │
│ └────────────────────────────────────┘ │
├────────────────────────────────────────┤
│ HP: 100/100 | PV: 12 | St: 18 | ...  │
├────────────────────────────────────────┤
│ ┌────────────────────────────────────┐│
│ │ Message line                       ││
│ │ (last action result)               ││
│ └────────────────────────────────────┘│
└────────────────────────────────────────┘
```

### Caves of Qud Layout

```
┌────────────────────────────────────────┐
│ ┌────────────────────────────────────┐ │
│ │                                    │ │
│ │         MAIN MAP VIEW              │ │
│ │                                    │ │
│ └────────────────────────────────────┘ │
├────────────────────────────────────────┤
│ HP: XX | Status effects shown here     │
├────────────────────────────────────────┤
│ ┌──────────┐ ┌───────────────────────┐│
│ │ Mini     │ │ Message log           ││
│ │ Map/     │ │ (scrollable)          ││
│ │ Side     │ │                       ││
│ │ Panel    │ │                       ││
│ └──────────┘ └───────────────────────┘│
└────────────────────────────────────────┘
```

### Common Layout Patterns Summary

**Three-zone layout (most common):**
1. Map (top, ~70% of screen)
2. Status (middle, ~10%)
3. Messages (bottom, ~20%)

**Four-zone layout (DF style):**
1. Map (left, ~60%)
2. Side panel (right, ~20%)
3. Status (bottom middle, ~5%)
4. Log (bottom, ~15%)

**Key UI elements across games:**
- Player always centered or near-center on map
- Status always visible at glance
- Messages scroll but remain accessible
- Menus overlay rather than replace main view
- Keybindings shown inline when relevant

---

## 6. Color Conventions

### Universal Color Meanings

| Color | Primary Meaning | Secondary Meanings |
|-------|-----------------|-------------------|
| **White** | Neutral, basic | Player, default items, clouds |
| **Gray** | Object, feature | Statues, inactive, stone |
| **Black** | Empty, void | Holes, darkness (inverse rendering) |
| **Red** | Hostile, danger | Enemies, fire, lava, blood |
| **Green** | Nature, helpful | Plants, poison (some games), friendly NPCs |
| **Blue** | Water, cold | Rivers, ice, magical items |
| **Cyan** | Water (alt), ally | Water creatures, friendly units |
| **Yellow** | Warning, valuable | Gold, light sources, alert states |
| **Magenta** | Magical, special | Artifacts, unique creatures |
| **Brown** | Earth, wood | Terrain, organic materials |

### NetHack Color Meanings

| Color | Creatures | Items | Terrain |
|-------|-----------|-------|---------|
| White | Neutral | Scrolls, bones | Floor, clouds |
| Gray | Constructs | Basic items | Walls |
| Black | N/A | N/A | Dark areas |
| Red | Hostile demons | Potions, fire | Lava, fire |
| Green | Plants, poison | Potions (poison) | Acid, plants |
| Blue | Water creatures | Potions, rings | Water, ice |
| Cyan | Friendly/ally | Potions | Water |
| Yellow | Light creatures | Gold, light | Light sources |
| Magenta | N/A | Potions | N/A |
| Brown | N/A | Potions | Floor (dirt) |

### Dwarf Fortress Color System

**Material-based coloring:**
- Objects show the color of their material
- Creatures show species default colors
- Status colors overlay or modify

**Unit colors:**

| Color | Status |
|-------|--------|
| Cyan | Citizen, friendly |
| Red | Hostile, enemy |
| Yellow | Neutral |
| Gray | Dead, inactive |
| Green | On-duty military |
| Blue | On break, idle |

**Profession indicators (DF):**
Dwarves sometimes show profession through color:
- Miner = brown
- Mason = gray
- Carpenter = brown
- Metalsmith = dark gray
- Gem setter = cyan

### Caves of Qud Color Meanings

| Color | Meaning |
|-------|---------|
| Red | Hostile creature |
| Green | Friendly creature |
| Yellow | Neutral/NPC |
| Cyan | Water/liquid |
| Blue | Special/unique |
| White | Basic/neutral |
| Magenta | Artifact/rare |
| Gray | Object |

### State Color Modifiers

Across most roguelikes, color modifiers indicate status:

| State | Color Effect |
|-------|--------------|
| Poisoned | Green tint |
| Burning | Red/orange flicker |
| Frozen | Blue/white |
| Invisible | Dimmed or not shown |
| Paralyzed | Yellow highlight |
| Asleep | Cyan or steady |
| Confused | Flickering colors |
| Blessed | White glow |
| Cursed | Darkened/black |

---

## 7. Recommendations for Idle Village Game

### Entity Symbol Recommendations

**Option 1: Classic Letter-Based System**

Use initial letters for entity types with color coding for state.

| Entity Type | Symbol | Rationale |
|-------------|--------|-----------|
| Villager | `v` | First letter, lowercase for common |
| Builder | `b` | First letter |
| Farmer | `f` | First letter |
| Miner | `m` | First letter |
| Leader | `L` | Uppercase for important |
| Building | `#` or `π` | Standard terrain/structure |
| Resource | `*` | Standard valuable |

**Pros:**
- Intuitive for roguelike fans
- Easy to remember
- Extensible

**Cons:**
- Requires learning for new players
- Letter conflicts possible

**Option 2: Pictographic Symbol System**

Use shape-suggestive symbols rather than letters.

| Entity Type | Symbol | Rationale |
|-------------|--------|-----------|
| Villager | `☺` or `☻` | Classic smiley, human-like |
| House | `π` or `Ω` | Roof shape suggestion |
| Tree | `♠` or `T` | Tree shape |
| Resource | `♦` or `*` | Diamond = valuable |
| Storage | `○` | Barrel shape |
| Worksite | `Δ` | Triangle = construction |

**Pros:**
- More visually intuitive
- Less memorization
- Distinctive appearance

**Cons:**
- Limited symbol vocabulary
- May require Unicode font support
- Less traditional roguelike feel

**Option 3: Hybrid System**

Letters for creatures, special symbols for terrain/structures.

**Pros:**
- Best of both approaches
- Follows established conventions
- Clear distinction between entity types

**Cons:**
- May feel inconsistent
- Two systems to learn

### State/Activity Visualization Recommendations

**Idle state:**
- Static symbol, dimmed or white color
- No animation

**Working state:**
- Spin animation: `-` `\` `|` `/` at 2-4 Hz
- Color: Yellow or cyan (active)

**Sleeping state:**
- Symbol: `Z` overlay or cyan coloring
- Static, no animation

**Error state:**
- Color: Red
- Symbol: `!` modifier or flash
- Animation: 1 Hz pulse

**Blocked state:**
- Color: Yellow (caution)
- Symbol: `?` modifier or static

### UI Layout Recommendation

**Recommended three-zone layout:**

```
┌─────────────────────────────────────────┐
│ ┌─────────────────────────────────────┐ │
│ │                                     │ │
│ │         VILLAGE MAP                 │ │
│ │         (70-80% of screen)          │ │
│ │                                     │ │
│ │                                     │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ Population: 12 │ Food: 45 │ Day: 15   │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ Event log (3-5 lines)               │ │
│ │ "Builder finished the well."        │ │
│ │ "Farmer started planting."          │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Color Scheme Recommendation

| Status | Primary Color | Alternative |
|--------|---------------|-------------|
| Active/working | Yellow | Cyan |
| Idle | White | Gray |
| Sleeping | Blue | Cyan |
| Blocked | Yellow | Orange |
| Error | Red | Bright red |
| Success | Green | Bright green |

---

## 8. Risks

### Font Compatibility
**Issue:** Many symbols require Unicode support or specific fonts (CP437, extended ASCII).
**Mitigation:** Test with common terminal fonts (DejaVu, Liberation); provide ASCII-only fallback mode.

### Colorblind Accessibility
**Issue:** Color-only differentiation excludes ~8% of male users with color vision deficiency.
**Mitigation:** Use symbol variation in addition to color; offer high-contrast mode; use patterns not just colors.

### Screen Reader Support
**Issue:** Pure ASCII is more screen-reader friendly than Unicode symbols.
**Mitigation:** Provide ASCII-only mode; ensure text descriptions for all symbols; test with screen readers.

### Platform Differences
**Issue:** Symbols render differently across terminals and platforms.
**Mitigation:** Test on target platforms; use widely-supported characters from common fonts.

### Cognitive Overload
**Issue:** Too many symbols overwhelm new players.
**Mitigation:** Introduce symbols gradually through gameplay; provide look/examine commands; include in-game reference.

### Animation Sensitivity
**Issue:** Flashing/blinking can trigger photosensitivity issues.
**Mitigation:** Provide option to disable or reduce animations; respect prefers-reduced-motion settings.

---

## 9. Quick Reference Tables

### Entity Symbols Summary

| Category | Recommended Symbol | Alternatives |
|----------|-------------------|--------------|
| Player/avatar | `@` | `☺`, `☻` |
| Villager/citizen | `v` | First letter of type |
| Building | `#` (walls), `π` (house) | Box drawing `╔═╗` |
| Tree | `T` or `♠` | `*` or `¥` |
| Water | `~` | `≈` for flowing |
| Resource item | `*` for valuable | `$` for currency |
| Storage | `○` barrel | `[]` chest |
| Worksite | `Δ` | `+` |

### State Colors Summary

| State | Primary Color | Alternative |
|-------|---------------|-------------|
| Active/working | Yellow | Bright white |
| Idle | White | Gray |
| Sleeping | Cyan | Blue |
| Hostile | Red | Bright red |
| Friendly | Green | Cyan |
| Neutral | White | Gray |
| Critical/dying | Bright red | Blinking |
| Blocked | Yellow | Orange |

### UI Zone Summary

| Zone | Location | Size |
|------|----------|------|
| Main map | Center/center-left | 70-80% width |
| Status | Bottom edge | 1-2 lines |
| Message log | Bottom below status | 3-5 lines |
| Side panel | Right edge | 15-25% width |
| Minimap | Top-right or panel | Small square |

---

## Sources

Training knowledge only — no live web sources consulted. Information compiled from knowledge of:

- NetHack (various versions, extensive documentation)
- Dwarf Fortress (Bay 12 Games)
- ADOM (Ancient Domains of Darkness, Thomas Biskup)
- Caves of Qud (Freehold Games)
- Cataclysm: Dark Days Ahead
- Original Rogue (1980)
- Standard roguelike conventions from RogueBasin wiki and r/roguelikedev community

For current documentation, verify with:
- NetHack Wiki (nethackwiki.com)
- Dwarf Fortress Wiki (dwarffortresswiki.org)
- ADOM Wiki (ancardia.domination)
- Caves of Qud Wiki (wiki.cavesofqud.com)
- RogueBasin (roguebasin.com)