# Experimental FC24 Lua tooling — recovery hold, 2026-10-29

Read [the crash investigation](../../docs/crash-investigation-2026-10-29.md)
and [Windows recovery task](../../WINDOWS_CODEX_CRASH_RECOVERY.md) first.

The user reports reproducible career-load crashes. All 12 supplied dumps record
the same FC24 instruction. Neither OCR causality nor a specific Lua operation
has been established. A previous single successful reload does not establish
collector safety.

- `diagnostic.lua`, `event_probe.lua`, and `collector.experimental.lua` are disabled.
  The first two ignore old local acknowledgements, load no LE modules, and call no
  game API. No handler is registered. Do not re-enable them for recovery.
- Updating files does not remove callbacks already installed in a running Lua VM.
  Close the game and Live Editor normally before testing a copy of a save.
  Do not clear other scripts' handlers.
- `common.lua` remains an offline-testable serialization/transport implementation.
  Its snapshot function is not a qualified production capture path. Unused optional
  table traversal code has been removed.
- `GetSaveUID` is never called, even with a stale `save_uid_verified=true` config.
  Upstream documents that it can create an entry in `sponsors`; it is not a pure
  getter. Use explicit `instance_key`. Existing snapshot/save identifiers remain intact.
- `config.lua` stays local/ignored. None of its verification flags establishes
  runtime compatibility, save integrity, or successful automation.

The automatic JSON watcher and dashboard remain usable on archived snapshots.
Screenshot OCR is an optional offline evidence tool, not a replacement for the
requested unattended game collection. P2 remains blocked. Further development
requires a confirmed game/LE combination, a verified execution mechanism and
repeatable save/load checks on a disposable career.
