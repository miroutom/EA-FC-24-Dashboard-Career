-- P0 gate is CLOSED by default. No event ID or season inference is invented here.
assert(type(LCA_ROOT) == 'string', 'Set LCA_ROOT')
local core = dofile(LCA_ROOT .. '/common.lua')
local config = dofile(LCA_ROOT .. '/config.lua')
if not (config.enabled and config.transport_verified and config.triggers_verified and config.context_reader_verified) then
    core.log('collector disabled: P0 evidence/configuration required'); return
end
assert(type(config.season_reader)=='function', 'verified automatic season_reader required')
assert(config.instance_key or config.save_uid_verified, 'explicit save binding required')
assert(type(AddEventHandler)=='function', 'event API unavailable')
if _G.LCA_COLLECTOR_REGISTERED then core.log('collector already registered'); return end
local ids = {}
for _, name in ipairs(config.verified_event_names) do
    assert(type(name)=='string' and name:match('^ENUM_CM_EVENT_MSG_'), 'invalid symbolic event')
    assert(type(_G[name])=='number', 'event constant absent from installed enums.lua')
    ids[_G[name]] = name
end
assert(next(ids), 'no verified event triggers')
local function collect(_, event_id, _event)
    if not ids[event_id] then return end
    local ok = pcall(function()
        local snapshot = core.snapshot(config, ids[event_id])
        if not snapshot then return end
        local year = config.season_reader()
        assert(type(year)=='number' and year%1==0 and year>=2000 and year<=2200, 'unknown season')
        snapshot.season_start_year = year
        core.write(config, snapshot)
    end)
    if not ok then core.log('collector capture failed; check verified context and file transport') end
end
AddEventHandler('post__CareerModeEvent', collect)
_G.LCA_COLLECTOR_REGISTERED = true
