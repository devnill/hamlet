---
## Refinement Interview — 2026-03-20 (refine-9: quality cycle)

**Context**: Cycle 008 review passed with 2 significant findings fixed (WI-180 os.chdir omission, HOOK_SCRIPTS incomplete). Primary open gap: test coverage for all v0.4.0 additions. User invoked /ideate:refine to plan the next cycle.

**Q: What's driving this refinement — addressing the test coverage gap from the cycle 008 review, adding new functionality, or something else?**
A: This cycle should focus solely on quality — test coverage, documentation, and any items to address sustainable development.

**Q: For test coverage — should hook script unit tests be included in scope, or only package test gaps?**
A: Yes to all.

**Q: For documentation and sustainable development — which sub-areas are in scope? Options: code health fixes (enum identity, saver.py, startup deduplication); pre-existing functional gaps (Q-10 Bash schema, Q-6 health endpoint, Q-16 notification_type); documentation (README, QUICKSTART, CLAUDE.md, docstrings); architecture items (Any typing / Protocols, Q-13 stop_reason differentiation).**
A: All of the above.

**Q: For stop_reason differentiation — should "tool" (interrupt) produce different state transitions than "stop" (clean exit)? Proposed: immediately mark agents IDLE and flush pending_tools when stop_reason="tool", rather than waiting for zombie TTL.**
A: The zombie concept is just a thematic element when we can't infer the status of an agent. We should strive to match the intent in cases like this, as long as the telemetry is accurate.

**Q: For Any typing at module boundaries — Protocols or guarded imports?**
A: Protocols are better.
