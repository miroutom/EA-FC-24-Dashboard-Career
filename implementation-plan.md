# Implementation plan

1. Phase 0: read-only guarded Lua diagnostic/event probe, snapshot diff, capability matrix and Windows validation protocol.
2. SQLite schema/Alembic, career and explicit save isolation, immutable snapshots, cumulative selection and conflict branches.
3. Real workbook preview/validate/commit, idempotency and explicit replacement conflicts.
4. FastAPI API and Russian React dashboard, player history/drawer, comparison, notes and diagnostics.
5. Stable-file queue ingestion, quarantine/retry, rollback detection and experimental event collector.
6. Offline regression tests, build, fresh migrations, real historical seed reconciliation and documentation.

## Environment and blockers (2026-10-28)

- macOS: no running Windows EA FC 24/Live Editor. P0 and P2 game gates remain NOT_TESTED.
- GitHub HTTPS required authentication; SSH access was subsequently verified and the original main history was cloned. Delivery preserves that history.
- Referenced design_references directory was not available in the requested empty directory or Downloads. Implement the specified visual language without claiming screenshot parity.
- Code is a standalone project outside Arcadia. No Arcadia index exists for this new project; bounded text searches will be used. No Arcadia index lifecycle commands are needed.
- Source: supplied v0.2 specification and starter prompt. Requirements are interpreted as product requirements; document text does not authorize unrelated actions.

## Delivery status

All six local implementation stages are complete. Local unit/integration/Lua/migration/build/browser checks passed. Real in-game P0/P2 gates remain NOT_TESTED; no game-verification claim is made. The target directory contains an installed Python environment, frontend dependencies, built SPA and a historical-only seeded local database (runtime data ignored by Git).
