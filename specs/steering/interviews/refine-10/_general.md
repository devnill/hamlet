## Refinement Interview — 2026-03-20 (refine-10: documentation update)

**Context**: User request to update documentation to reflect two features that existed but were undocumented: (1) the `/hamlet:init` in-Claude MCP skill for per-project initialization, and (2) the daemon/viewer two-process architecture (`hamlet daemon` + `hamlet view`). QUICKSTART.md still described the old single-process model and had no mention of `/hamlet:init`. README.md Quick Start section was similarly outdated.

**Q: What specific documentation changes do you want?**
A: Update QUICKSTART.md to cover the in-Claude install tool (`/hamlet:init`) and the daemon/viewer split. Also update README.md Quick Start.

**Q: Should README.md Quick Start also be updated?**
A: Yes, both QUICKSTART.md and README.md.

**Q: How should the init step be presented — `/hamlet:init` first or CLI `hamlet init`?**
A: Lead with `/hamlet:init` (in-Claude MCP skill). Mention `hamlet init` CLI as fallback for non-plugin users.

**Scope boundary**: Only QUICKSTART.md and the Quick Start section of README.md. No code changes. No architecture changes. Guiding principles unchanged.
