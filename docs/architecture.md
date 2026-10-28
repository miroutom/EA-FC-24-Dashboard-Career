# Architecture

The supplied v0.2 specification is the requirements source. The starter prompt is implementation context. No screenshot/OCR/manual match-entry workflow is substituted for automatic collection.

SQLite stores careers and exact-name historical aliases, seasons/metadata, import previews/batches, explicit save bindings and branches, immutable cumulative snapshots/rows, derived intervals, optional notes and sync diagnostics. `matches` is reserved for a future verified source and is never populated from intervals. DDL is versioned in Alembic concrete revision 0001; foreign keys, WAL, busy timeout, partial unique historical indexes are enabled.

Historical import is a two-stage transaction workflow. Preview validates types, sheet, Unicode, seasons, limits and duplicate keys and records a database fingerprint. Commit checks the career, file digest, expiry, current fingerprint and explicit replacement strategy. No partial commit on failures.

One background watcher runs in the single API process, at 1s scan intervals. It reads only ordinary .json files in the configured local spool, ignores symlinks/.tmp, waits two equal size/mtime/checksum scans, validates strict Pydantic input and then atomically stores all normalized rows/deltas/events. Bytes are archived before DB mutation, so a crash may leave a harmless orphan raw object, never partial stats. Restart/re-delivery hashes suppress duplicate effects. Pending/unbound files remain in raw and can be retried without arbitrary paths from API clients. Oversized files are preserved in quarantine.

Analytics selects one source per season: historical totals by default, explicitly reconciled Live otherwise. Live selects per-key last observations in the active branch, optionally as_of. Missing player rows preserve previous counters. Unknown tournament completeness never becomes an all-competition total. Ratings and unsupported metrics remain NULL. Two or more saves require explicit selection. Season counts include zero-appearance records.

Counter decrease, earlier season, in-game date reversal or out-of-order captured time opens a pending branch. While unresolved, incoming observations are held; active analytics remains unchanged. Accepting a branch switches its Live view, rejecting keeps the prior branch. Both raw histories remain. This favors visible reconciliation over automatic history rewriting; late file delivery can be a conflict requiring review.

React fetches real API data via TanStack Query (5s polling). Career/season/tournament/save/as_of scope is shared by overview, squad, profile and compare. Drawer preserves table filters. Sync shows experimental status, snapshots, events, bindings, source/identity reconciliation and optional notes. Local CSS and Radix primitives follow shadcn composition with keyboard focus/escape handling; no external fonts/images/analytics. Referenced RespectTheJeff screenshots were unavailable in the repository at implementation time; no screenshot-parity claim.

API runs only on loopback with a Host/Origin guard. Input contains data only, never executable Lua/Python commands. No public ingest route or credentials are required. The raw and local config directories are ignored by Git. LAN is outside the default deployment.
