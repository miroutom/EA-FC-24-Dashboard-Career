assert(type(LCA_ROOT) == 'string', 'Set LCA_ROOT to this collector directory')
local core = dofile(LCA_ROOT .. '/common.lua')
local config = dofile(LCA_ROOT .. '/config.lua')
if config.manual_capture_ack ~= true then
    core.log('manual diagnostic disabled after save/reload safety failure')
    return
end
for _, name in ipairs({'IsInCM','GetPlayersStats','GetPlayerStats','GetUserTeamID','GetSaveUID','GetCurrentDate','AddEventHandler'}) do
    core.log(name .. ': ' .. type(_G[name]))
end
local team, team_source = core.user_team_id()
local current_date, date_source = core.current_date()
core.log('user team context: ' .. tostring(team) .. ' via ' .. team_source)
core.log('current date context: ' .. tostring(current_date) .. ' via ' .. date_source)
local snapshot, reason = core.snapshot(config, 'diagnostic')
if not snapshot then core.log(reason); return end
core.log('rows=' .. #snapshot.rows .. '; diagnostic capture only')
for i=1, math.min(#snapshot.rows, 3) do core.log(core.json(snapshot.rows[i])) end
local ok = pcall(core.write, config, snapshot, 'diagnostic')
core.log(ok and 'diagnostic file written' or 'file transport failed; inspect config/capabilities')
