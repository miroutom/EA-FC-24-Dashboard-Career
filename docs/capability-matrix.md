# Capability matrix — 2026-10-28

Collector: **not verified**. Real EA FC 24 build: unknown. Live Editor build: unknown.
P0 and P2 gates: **NOT_TESTED** (macOS development environment, no game).

| Capability | Status | Evidence / scenario |
| --- | --- | --- |
| GetPlayersStats season counters and GetPlayerStats | NOT_TESTED | Documented upstream; actual installation and update timing require game test |
| CareerModeEvent callback signature | NOT_TESTED | Documented upstream, offline harness only |
| Played / quick / interactive simulation final-stat trigger | NOT_TESTED | Run manual-game-validation.md |
| Lua io write and atomic rename | NOT_TESTED | Lua runtime tests are not Live Editor tests |
| Save UID stability / manager-mode detection | NOT_TESTED | Explicit instance binding fallback; IsInCM proves career mode, not manager mode |
| Automatic season context / rollover | NOT_TESTED | No unverified date-to-season heuristic; verified season_reader required |
| Auto-start scripts | NOT_TESTED | Must be verified for installed build |
| avg units / per-game ratings | NOT_TESTED | Raw preserved; rating deliberately unavailable |
| match ID, opponents, score, minutes, xG, possession | UNAVAILABLE | No implemented verified source |
| motm, saves, goals_conceded | UNAVAILABLE | Not consumed; upstream uncertainty |
| Local queue ingestion and historical workbook | PARTIAL | Offline application tests; game delivery untested |

Statuses describe real-source evidence, not whether code compiles. Promote to VERIFIED only with game/LE versions, event sequence, raw before/after files and observed scenario. Keep local paths/save identifiers out of published evidence.

Primary sources consulted:
- https://github.com/xAranaktu/FC-24-Live-Editor/wiki/LUA-API (legacy, explicitly deprecated upstream)
- https://github.com/xAranaktu/FC-24-Live-Editor/wiki/LUA-API-v2-Events
- https://github.com/xAranaktu/FC-24-Live-Editor (compatibility and anti-cheat cautions)
- https://github.com/VeejaLiu/FC-Career-Top (development-tracking example, not proof of per-match statistics)
