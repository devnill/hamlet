---
type: refinement-interview
date: 2026-03-18
cycle: refine-20260318
domain: general
---

## Context

User-initiated refinement triggered by setup friction encountered while running hamlet with hooks installed. Hooks were firing but no changes were visible; investigation surfaced that there was no per-project hamlet config. The user wants to reduce setup friction through a plugin model, a daemon/viewer split, a project init command, and in-app help.

## Q: What changes do you want to make?

**A:** Four things:
1. Make hamlet a plugin so hooks register when installed and de-register when uninstalled.
2. If the server isn't running, hamlet's hooks should fail silently.
3. There should be a command to set up the hamlet config scoped to the current project.
4. There should be in-app help to show a user how to control hamlet.

## Q: What do you mean by "plugin" for item 1?

**A:** Use a Claude Code plugin. See cyberbrain, beepboop, or ideate for examples. The plugin should add the MCP server and register the hooks.

## Q: On item 2 (fail silently): the hooks already catch all exceptions and exit 0 with a 1-second timeout. What failure behavior are you actually seeing?

**A:** This is the correct behavior; I was just being complete.

## Q: Does hamlet auto-start as a background daemon via the plugin, or does the user still manually start hamlet?

**A:** The plugin should only serve to register the MCP, hooks, and configuration tool. Hamlet should still be run manually. We should actually refine this further to have a hamlet daemon as a separate process from the viewer.

## Q: Should `hamlet init` generate a new random UUID or derive it from the directory path (matching the hooks' fallback hash)?

**A:** Random UUID.

## Q: For in-app help — second overlay or expand legend?

**A:** The help menu should be the `?` hotkey, with the legend hotkey being `/` (changing from current `?` for legend). Along with other keybindings — let's say vim-style (`hjkl`).
