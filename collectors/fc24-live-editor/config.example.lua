-- Copy to config.lua. Use absolute Windows paths with forward slashes.
return {
    spool_dir = 'C:/FootballCareerDashboard/data/spool',
    instance_key = nil, -- Explicit save binding key from Sync UI (one save only).
    season_start_year = nil, -- Diagnostic only. Collector requires verified automatic season_reader.
    enabled = false,
    manual_capture_ack = false, -- Legacy flag; ignored during the recovery hold.
    transport_verified = false,
    triggers_verified = false,
    save_uid_verified = false, -- Legacy flag; GetSaveUID is never called (may write game DB).
    verified_event_names = {}, -- Symbolic globals from your installed enums.lua, after P0.
    season_reader = nil, -- function returning actual season start year; prove rollover first.
    context_reader_verified = false,
}
