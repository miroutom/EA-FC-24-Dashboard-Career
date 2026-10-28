# Verification report — 2026-10-28

## Implemented

- Read-only Phase 0 diagnostic, actual-symbol event probe, JSON transport helpers, diff CLI, closed experimental collector gates and Windows test protocol.
- SQLite/Alembic concrete DDL, career/save isolation, immutable snapshots/raw archive, conflict branches, explicit identity/source reconciliation, NULL semantics and cumulative/as_of analytics.
- XLSX/CSV preview/validation/commit with exact-file idempotency, stale preview detection and explicit conflict replacement. Only the real workbook's `Все сезоны` is imported.
- FastAPI, typed analytics response DTOs, local-only API guard, Russian React dashboard/table/overview/updates, player drawer/history, comparison, sync/errors/bindings and optional notes.
- Automatic local stable-file watcher, atomic DB ingestion, quarantine/retry and 5-second UI refresh. No screenshot collection, OCR, cloud service or production fixtures.
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

## Not performed / gates still closed

- No Windows EA FC 24/Live Editor execution: no actual played-match or quick-simulation before/after logs.
- No real validation of game API availability, final-counter timing, season reader, save UID stability, file transport in the embedded Lua sandbox or script auto-start.
- No actual P0 or P2 gate pass. `Collector: not verified` is intentional. Lua harness and synthetic files are not game evidence.
- Live Editor compatibility with the user's game build is unknown. Advanced metrics are UNAVAILABLE and avg units NOT_TESTED.
- `design_references/` was absent from the cloned initial repository and known supplied-file locations. UI follows the written brief; screenshot parity was not checked.
- GitHub Actions execution is separate from the local tests; publishing a workflow does not mean its remote jobs passed.

## Windows game validation

Follow [manual-game-validation.md](manual-game-validation.md), then add evidence to [capability-matrix.md](capability-matrix.md). Do not enable unverified source/trigger/context flags or claim unattended in-game collection before this test.
