# Refinement Interview — 2026-03-20 (refine-10: documentation update)

**Context**: User request to update documentation to reflect two features that existed but were undocumented in the quickstart: (1) the `/hamlet:init` in-Claude MCP skill for per-project initialization, and (2) the daemon/viewer two-process architecture.

**Q: What specific documentation changes do you want?**
A: Update QUICKSTART.md to cover the in-Claude install tool (`/hamlet:init`) and installing/using the hamlet daemon and client app.

**Q: Should README.md Quick Start also be updated?**
A: Yes, both QUICKSTART.md and README.md.

**Q: How should the init step be presented?**
A: Lead with `/hamlet:init` (in-Claude MCP skill) as primary. Mention `hamlet init` CLI as the fallback for non-plugin users.

**Scope**: QUICKSTART.md and README.md Quick Start section only. No code changes. No architecture changes. Guiding principles unchanged.
