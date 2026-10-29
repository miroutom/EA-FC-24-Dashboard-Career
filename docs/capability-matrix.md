# Capability matrix — 2026-10-28

Historical diagnostic values: **P0 OBSERVED** on 2026-10-28. All in-game Lua collection: **blocked on save safety**.
EA FC 24 runtime build: `1.0.120.18322`; installed file product version: `24.0.5929398.0`; Steam build ID: `25351902`. Live Editor: `v24.1.1.9`.
P0 values matched a played match and quick simulation, but the collection path is **BLOCKED** after reload crashes in callback-enabled sessions and after repeated extended manual diagnostics. P2 is **BLOCKED**.

| Capability | Status | Evidence / scenario |
| --- | --- | --- |
| GetPlayersStats season counters and GetPlayerStats | VERIFIED | Real RB Salzburg rows matched screenshots for a played 10:0 and quick-sim 1:0; raw evidence is listed in `windows-live-validation-2026-10-28.md` |
| CareerModeEvent callback signature | UNSAFE | Installed symbolic names and sequences were captured, but saves from callback-enabled sessions repeatedly crashed on reload; event probes are disabled for normal use |
| Played / quick / interactive simulation final-stat trigger | BLOCKED | Quick-sim counters were finalized at `USER_MATCH_COMPLETED`, but callbacks failed save/reload safety; repeated extended manual diagnostics later failed it too; interactive simulation not tested |
| Lua io write and atomic rename | OBSERVED_UNSAFE_PATH | Payloads reached the queue/archive, but successful transport does not establish career-save safety |
| Save UID stability / manager-mode detection | PARTIAL | Manager career, team `191` and game date were read through installed v2 fallbacks; save UID remained unavailable/null and reload stability is not tested |
| Automatic season context / rollover | PARTIAL | Current date is read by the installed v2 fallback; rollover still needs real-season validation |
| Auto-start scripts | NOT_TESTED | Must be verified for installed build |
| avg units / per-game ratings | PARTIAL | Raw `avg` increments tracked displayed per-match ratings ×10 (with game-internal rounding); it is cumulative raw data and remains unavailable as a claimed average |
| match ID, opponents, score, minutes, xG, possession | SCREENSHOT_VERIFIED_MANUAL | SK Sturm Graz 0:13 RB Salzburg is stored from 26 screenshots plus an exact pre/post snapshot delta; no automatic source is claimed |
| Match timeline and player ratings | SCREENSHOT_VERIFIED_MANUAL | 18 visible events and 16 player performances are exposed by the local Matches API/page; ratings are cross-checked against the cumulative `avg` delta |
| motm, saves, goals_conceded, two-yellow | IMPLEMENTED_NOT_VALIDATED | Optional season counters are preserved and exposed, but need comparison with FC 24 screens |
| League W/D/L, GF/GA, points, table place | SOURCE_REJECTED | Real FC 24 evidence returned 10 matches with zero W/D/L/GF/GA; inconsistent `leagueteamlinks` rows are retained as raw evidence but hidden from analytics |
| Injury and last-match state | DISABLED_UNSAFE_SOURCE | Direct optional DB-table traversal was present in `0.3.0` and is disabled in `0.3.1-safe` after the repeated-diagnostic reload failure |
| Latest rating history row | DISABLED_UNSAFE_SOURCE | Historical raw rows remain auditable; new in-game DB-table reads are disabled |
| Local queue ingestion and historical workbook | VERIFIED | Real game delivery, idempotent no-change handling and existing workbook ingestion observed; completeness remains UNKNOWN |

Statuses describe real-source evidence, not whether code compiles. Promote to VERIFIED only with game/LE versions, event sequence, raw before/after files and observed scenario. Keep local paths/save identifiers out of published evidence.

Primary sources consulted:
- https://github.com/xAranaktu/FC-24-Live-Editor/wiki/LUA-API (legacy, explicitly deprecated upstream)
- https://github.com/xAranaktu/FC-24-Live-Editor/wiki/LUA-API-v2-Events
- https://github.com/xAranaktu/FC-24-Live-Editor (compatibility and anti-cheat cautions)
- https://github.com/VeejaLiu/FC-Career-Top (development-tracking example, not proof of per-match statistics)
