# Read-only FC24 Lua tooling

Start with [Windows validation](../../docs/manual-game-validation.md) and [capabilities](../../docs/capability-matrix.md).

Files:
- common.lua: guarded getters, JSON escaping/null preservation, own-team filtering, temporary file and rename. Optional direct DB-table scans are disabled.
- diagnostic.lua: capability/type checks and a snapshot harness. It is disabled unless a local manual acknowledgement is deliberately set.
- event_probe.lua: historical P0 event logger. It is now guarded by an explicit unsafe acknowledgement because callback sessions were followed by save reload failures on the validated build. Never run it on a valued save.
- collector.experimental.lua: hard-disabled after real evidence that snapshot work inside CareerModeEvent callbacks can leave a save unable to reload. It registers no handler.
- config.example.lua: local configuration template. config.lua is ignored by Git to protect paths and identifiers.

Do not run this in a valued career. The historical invocation was:

```lua
LCA_ROOT = 'C:/MyProjects/EA-FC-24-Dashboard-Career/collectors/fc24-live-editor'
dofile(LCA_ROOT .. '/diagnostic.lua')
```

Collector `0.3.1-safe` no longer traverses optional league, injury or rating-history DB tables. The optional arrays are always empty. Card and goalkeeper season counters can still be preserved when the single installed `GetPlayersStats` call returns them, but no further in-game validation is authorized on the current save.

Historical P0 values were captured, but both callback sessions and a repeated extended manual diagnostic session failed save/reload safety. Do not run `diagnostic.lua`, `event_probe.lua`, or `collector.experimental.lua` in normal gameplay. File delivery failures are logged without local path contents. The exact game versions and failures are recorded in the manual evidence report.
