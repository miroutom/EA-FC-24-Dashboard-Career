# Read-only FC24 Lua tooling

Start with [Windows validation](../../docs/manual-game-validation.md) and [capabilities](../../docs/capability-matrix.md).

Files:
- common.lua: guarded getters, JSON escaping/null preservation, own-team filtering, temporary file and rename.
- diagnostic.lua: capability/type checks and a real snapshot when available. Never mutates game DB, player attributes, save, or budget.
- event_probe.lua: logs actual event IDs and installed symbolic names. Registers once per Lua VM, never clears other scripts' handlers.
- collector.experimental.lua: disabled until P0 flags, existing symbolic event constants and verified automatic season context. No guessed API/IDs; exactly one handler per VM.
- config.example.lua: local configuration template. config.lua is ignored by Git to protect paths and identifiers.

Run in the Live Editor Lua engine after setting:

```lua
LCA_ROOT = 'C:/FootballCareerDashboard/collectors/fc24-live-editor'
dofile(LCA_ROOT .. '/diagnostic.lua')
dofile(LCA_ROOT .. '/event_probe.lua')
-- Only after real P0 evidence:
-- dofile(LCA_ROOT .. '/collector.experimental.lua')
```

P0/P2 not passed by offline tests. Registration guards last for the Lua VM lifetime. To change a registered callback/configuration, restart the engine/game according to the installed LE behavior; do not clear all event handlers. File delivery failures are logged without local path contents. Game versions are recorded in the manual evidence report, not guessed via undocumented calls.
