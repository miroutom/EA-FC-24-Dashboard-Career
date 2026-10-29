# Verification report — 2026-10-28

## Implemented

- Read-only Phase 0 diagnostic, actual-symbol event probe, JSON transport helpers, diff CLI, closed experimental collector gates and Windows test protocol.
- SQLite/Alembic concrete DDL, career/save isolation, immutable snapshots/raw archive, conflict branches, explicit identity/source reconciliation, NULL semantics and cumulative/as_of analytics.
- XLSX/CSV preview/validation/commit with exact-file idempotency, stale preview detection and explicit conflict replacement. Only the real workbook's `Все сезоны` is imported.
- FastAPI, typed analytics response DTOs, local-only API guard, Russian React dashboard/table/overview/updates, player drawer/history, comparison, sync/errors/bindings and optional notes.
- Automatic local stable-file watcher, atomic DB ingestion, quarantine/retry and 5-second UI refresh. No screenshot collection, OCR, cloud service or production fixtures.
- Typed manual match-evidence API and Matches page for explicit screenshot-backed score, xG/team metrics, timeline, player ratings and a local-only evidence gallery. It never treats cumulative snapshot intervals as full match records.
- Python and npm dependency locks, Windows/macOS startup instructions and GitHub Actions tests for backend on Windows/Linux and frontend on Linux.

## Actually checked locally

Development host: macOS, Python 3.12, Node 22. Browser: installed Chromium via Playwright.

- `pytest -q`: **42 passed**, including actual workbook reconciliation, synthetic snapshot regressions, Lua runtime harness and Alembic upgrade/downgrade/model comparison.
- `ruff check app tests`: passed. Python bytecode compilation: passed.
- `npm test`: **5 passed** (Vitest/Testing Library); explicit import-conflict confirmation and pagination covered.
- `npm run build`: passed (TypeScript + Vite). Vite reports a non-blocking large JS bundle warning.
- `npm run test:e2e`: browser smoke checks real seeded overview, player search/drawer/filter retention, comparison, sync empty state and width 768px. **1 passed** from the final project directory, including actual season-filter totals (146 → 601), after a fresh dependency install and real Excel seed.
- No fake profiles or live fixtures seeded in normal startup. Raw ingestion tests use temporary databases only.

Real Excel (`Все сезоны`): **123 rows**, **82 distinct exact-name player identities**, **5 seasons**, **601 player goals**, **437 assists**, **3093 player appearances**, **364 clean-sheet observations**. Every career total reconciles with its season rows. These are PARTIAL_SCREENSHOT observations, not full club match statistics.

## Windows live P0 follow-up — 2026-10-28

- EA FC 24 runtime `1.0.120.18322` and Live Editor `v24.1.1.9` were exercised in an offline disposable manager career. Team context `191`, ISO game dates and 33 player-season rows were read through the installed v2 API fallbacks.
- A played 10:0 produced the screenshot-matching delta: 16 appearances, 10 goals, 10 assists, 11 clean-sheet rows and one red card. Counters were unchanged on the post-match report and finalized after `USER_MATCH_COMPLETED` followed by return to the hub.
- A quick-sim 1:0 produced 13 appearances, one Roko Šimić goal, one Lucas Gourna-Douath assist and 10 clean-sheet rows. Those counters were already finalized on the result screen after `ABOUT_TO_ENTER_QUICK_SIM` and `USER_MATCH_COMPLETED`; the hub snapshot was idempotent.
- Lua file transport, watcher ingestion, immutable raw archiving and no-change deduplication worked without quarantine or watcher errors. The actual raw hashes, totals and event sequences are recorded in [the Windows evidence report](windows-live-validation-2026-10-28.md).
- This preserved the requested P0 values, but later reload failures mean the in-game Lua collection path is not safe for continued use. It does not verify the automatic collector or P2.

## Not performed / gates still closed

- No verified automatic `season_reader`, save UID stability, reload/rollback behavior, season rollover or script auto-start.
- Callback state was captured: quick-sim counters were final at `USER_MATCH_COMPLETED`. Callback-enabled saves then crashed on reload. A later save also crashed after a second extended manual `0.3.0` diagnostic session, so `diagnostic.lua` is now default-disabled and optional DB scans were removed from the active snapshot path. All in-game collection gates remain closed pending an out-of-process design.
- Interactive simulation was not tested. Advanced match metrics remain UNAVAILABLE. Raw `avg` behavior was observed but is not exposed as a verified average rating.
- `design_references/` was absent from the cloned initial repository and known supplied-file locations. UI follows the written brief; screenshot parity was not checked.
- GitHub Actions execution is separate from the local tests; publishing a workflow does not mean its remote jobs passed.

## Windows game validation

Follow [manual-game-validation.md](manual-game-validation.md), then add evidence to [capability-matrix.md](capability-matrix.md). Do not enable unverified source/trigger/context flags or claim unattended in-game collection before this test.

## Follow-up: explicit Mac demo (2026-10-28)

The user authorized synthetic demo data. A separate data-demo sandbox now seeds fictional players and example snapshots. Normal game/production verification remains unchanged. Regression suite: 48 backend tests; 6 frontend tests, plus a dedicated browser demo/watcher scenario. Mac launcher uses port 8001 and does not replace the real data/ database or mark synthetic saves verified.

## Follow-up: richer demo charts and local-only runtime

Added three synthetic historical seasons idempotently (8 seasons total) and three overview plots: stacked goals/assists leaders, observed-goal distribution by role, and appearances vs goal contributions. Charts share career/season/competition filters and exclude unknown counters without filling them with zeros. Regression checks: 49 backend tests, 10 frontend tests, production build and the extended demo browser scenario passed. The browser scenario checks chart geometry, watcher-driven UI updates, layout at 768px, and zero HTTP(S) requests to external hosts. Local inspection found no cloudflared process; the demo listener was bound to 127.0.0.1:8001. The application starts no external tunnel.
