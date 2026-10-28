# Phase 0: Windows + actual game protocol

Use a disposable COPY of an offline manager career. Record exact game build, Live Editor release and Windows version. Follow upstream compatibility instructions; do not bypass anti-cheat or use online modes. The legacy Lua API is deprecated upstream: verify function presence first.

1. Start API/watcher on the Windows machine. Create career and explicit save binding in Sync. Keep its instance_key unique to this save. Create the spool directory.
2. Copy config.example.lua to config.lua beside common.lua. Set absolute spool_dir, instance_key and the known season for diagnostic ONLY. Leave all verification flags false.
3. Open Live Editor Lua engine and set `LCA_ROOT = 'C:/FootballCareerDashboard/collectors/fc24-live-editor'`. Run `dofile(LCA_ROOT .. '/diagnostic.lua')` inside the manager career. Verify emitted JSON contains actual user-team rows. Record GetSaveUID/GetCurrentDate availability separately; no stability claim yet.
4. Run event_probe.lua ONCE. Run it again to check duplicate protection. Record the event sequence and symbolic names resolved from the INSTALLED enums.lua. No hardcoded event numbers.
5. Capture diagnostic before a PLAYED match. Play it. Capture after final whistle, reports, return to hub, and day advance. Compare pairs with `python scripts/diagnose_snapshots.py before.json after.json`. Find the first consistently finalized counters. No xG or match-rating assertion.
6. Repeat for a QUICK simulation, then interactive simulation if used. Confirm same/different reliable triggers. Repeat events and diagnostic; inspect absence of duplicated totals.
7. Reload the same save, then an older copy. Record UID stability, instance key handling and date behavior. Older counters must create conflict branch, preserving previous totals until explicit resolution.
8. Advance the test copy to next season. Establish an actual automatic season reader from a verified installed API. Do not derive season from an assumed July boundary. If unavailable, automation gate remains closed.
9. Only after before/after logs, file transport, context and trigger timing are proved: set config verification flags and implement the documented verified season_reader. List symbolic verified_event_names. Run collector.experimental.lua once. Confirm an unassisted match/simulation produces a file, watcher import and browser update. Diagnostic is not the regular gameplay workflow.
10. Restart game/LE; test the installed release's script auto-start mechanism. Restart watcher; replay same files three times. Validate no duplicated records, and repeat season transition.

P0 passes only with actual player before/after evidence and working file delivery. P2 additionally requires unattended collection after normal game startup. Offline tests alone pass neither gate. If any prerequisite is unavailable, keep collector disabled and document it as NOT_TESTED/UNAVAILABLE.
