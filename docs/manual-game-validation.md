# Phase 0: Windows + actual game protocol

> **BLOCKED on the validated installation (2026-10-29).** Do not execute this
> protocol again. It is retained only as historical evidence. Callback sessions
> and a repeated manual `0.3.0` diagnostic session were both followed by save
> reload crashes. Future validation requires a disposable environment and an
> out-of-process design that does not traverse game DB tables from Lua.

Use a disposable COPY of an offline manager career. Record exact game build, Live Editor release and Windows version. Follow upstream compatibility instructions; do not bypass anti-cheat or use online modes. The legacy Lua API is deprecated upstream: verify function presence first.

1. Start API/watcher on the Windows machine. Create career and explicit save binding in Sync. Keep its instance_key unique to this save. Create the spool directory.
2. Copy config.example.lua to config.lua beside common.lua. Set absolute spool_dir, instance_key and the known season for diagnostic ONLY. Leave all verification flags false.
3. Historical step only: the manual diagnostic was run from the career hub. The script now refuses capture unless a local acknowledgement is set; do not set it on the validated installation.
4. Do **not** run `event_probe.lua` or `collector.experimental.lua` in normal testing. Callback-enabled sessions on the validated build were followed by repeatable save reload crashes. Existing event evidence is historical only.
5. Historical step only: before/after manual diagnostics were compared. Repeating this with the extended `0.3.0` table scans failed reload safety, so this is no longer an authorized collection path.
6. Repeat manually for a QUICK simulation, then interactive simulation if used. Inspect absence of duplicated totals. Validate new optional fields against screenshots: league W/D/L/GF/GA/points, cards, goalkeeper counters, injury state and last-match/rating raw values. Missing fields stay null and do not fail P0.
7. Reload the same save, then an older copy. Record UID stability, instance key handling and date behavior. Older counters must create conflict branch, preserving previous totals until explicit resolution.
8. Advance the test copy to next season. Establish an actual automatic season reader from a verified installed API. Do not derive season from an assumed July boundary. If unavailable, automation gate remains closed.
9. Only after before/after logs, file transport, context and trigger timing are proved, test callback safety on a disposable save. Never read statistics or write files directly inside a CareerModeEvent callback if save/reload safety has not passed. The validated Windows build failed this test, so its experimental collector must remain disabled until work is deferred outside the callback and a fresh save/reload test passes.
10. Restart game/LE; test the installed release's script auto-start mechanism. Restart watcher; replay same files three times. Validate no duplicated records, and repeat season transition.

P0 passes only with actual player before/after evidence and working file delivery. P2 additionally requires unattended collection after normal game startup. Offline tests alone pass neither gate. If any prerequisite is unavailable, keep collector disabled and document it as NOT_TESTED/UNAVAILABLE.
