# snapshot_v1 and source semantics

The exact input schema is `backend/app/schemas.py:SnapshotInput`; it is an APPLICATION envelope, not a claim that LE supplies its context.

Required: schema_version=1, producer=fc24-live-editor-lua, collector_version, game_version=EA FC 24, UTC captured_at_utc and rows. Optional context: explicit instance_key, verified save_uid, ISO in_game_date, user_team_id, season_start_year. Without an unambiguous binding, team and season, a snapshot stays NEEDS_BINDING. Rows require nonnegative strict integer playerid/teamid/compobjid, unique within a snapshot. Counters app/goals/assists/yellow/red/clean_sheets may be NULL; bool/string/negative counters are rejected. avg is raw nonnegative finite numeric data, not a per-match rating. display_name is optional Unicode display text, never identity evidence. Unknown keys are rejected. Maximum 5MiB / 20,000 rows.

Completeness defaults UNKNOWN. COMPLETE requires real source evidence before claiming all tournaments. Diagnostic always emits UNKNOWN. The experimental collector does not assume completeness; retain tournament-level display until an actual full-set verification exists. Source verification is configured on binding with evidence and never inferred from a payload's own claim.

API outputs validated JSON DTOs, source_scope/data_quality/last_synced_at on analytics. Unknown values are null, never substituted with zero. All-time totals require known values for every included observation; there is no silent sum of partially missing fields. `historical_partial`, `verified_live`, `unknown` indicate source quality; intervals carry confidence and are always displayed as inferred periods.

Snapshot SHA-256 suppresses exact redelivery. Separate state digest recognizes unchanged counters with a different captured time. Such observations remain auditable but do not add deltas. Deltas compare same player+team+competition+season+branch; app_delta > 1 remains a period, app_delta=1 does not prove a match, and app_delta=0 with increased activity is INVALID. Negative counters create branch conflicts, not negative goal events.

Historical SHA idempotency is per career, because importing the same workbook into a different career is allowed. Exact normalized full display names establish import aliases; Unicode display retains original diacritics. Different abbreviations require explicit identity linking. Historical and Live are never added for the same season. Season policy changes and playerid linking require explicit acknowledgements.
