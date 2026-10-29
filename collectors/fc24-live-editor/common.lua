-- Application contract, not a claim that every FC24 installation exposes this API.
local M = {}
M.null = {}
local function quote(s)
    return '"' .. tostring(s):gsub('[%z\1-\31\\"]', function(c)
        if c == '"' then return '\\"' end
        if c == '\\' then return '\\\\' end
        return string.format('\\u%04x', c:byte())
    end) .. '"'
end
function M.json(v)
    if v == nil or v == M.null then return 'null' end
    if type(v) == 'string' then return quote(v) end
    if type(v) == 'boolean' then return tostring(v) end
    if type(v) == 'number' then
        assert(v == v and v ~= math.huge and v ~= -math.huge, 'non-finite number')
        return tostring(v)
    end
    assert(type(v) == 'table', 'unsupported JSON type')
    local items = {}
    if getmetatable(v) and getmetatable(v).__array then
        for _, value in ipairs(v) do items[#items+1] = M.json(value) end
        return '[' .. table.concat(items, ',') .. ']'
    end
    for key, value in pairs(v) do items[#items+1] = quote(key) .. ':' .. M.json(value) end
    table.sort(items)
    return '{' .. table.concat(items, ',') .. '}'
end
function M.array(t) return setmetatable(t or {}, {__array=true}) end
function M.call(name, ...)
    if type(_G[name]) ~= 'function' then return nil end
    local ok, value = pcall(_G[name], ...)
    if ok then return value end
    return nil -- Do not log exceptions which can contain private paths.
end
function M.user_team_id()
    local team = M.call('GetUserTeamID')
    if type(team) == 'number' then return team, 'GetUserTeamID' end
    local ok, value = pcall(function()
        if type(LE) ~= 'table' or type(LE.db) ~= 'table' then return nil end
        local users = LE.db:GetTable('career_users')
        if type(users) ~= 'table' then return nil end
        local record = users:GetFirstRecord()
        if type(record) ~= 'number' or record <= 0 then return nil end
        return users:GetRecordFieldValue(record, 'clubteamid')
    end)
    if ok and type(value) == 'number' then
        return value, 'LE.db career_users.clubteamid'
    end
    return nil, 'unavailable'
end
local function date_iso(value)
    if type(value) ~= 'table' then return nil end
    local year, month, day = value.year, value.month, value.day
    if type(year) ~= 'number' or type(month) ~= 'number' or type(day) ~= 'number' then return nil end
    if year < 2000 or year > 2200 or month < 1 or month > 12 or day < 1 or day > 31 then return nil end
    return string.format('%04d-%02d-%02d', year, month, day)
end
function M.current_date()
    local value = date_iso(M.call('GetCurrentDate'))
    if value then return value, 'GetCurrentDate' end
    if type(require) == 'function' then
        local loaded = pcall(require, 'imports/other/helpers')
        if loaded then
            value = date_iso(M.call('GetCurrentDate'))
            if value then return value, 'imports/other/helpers GetCurrentDate' end
        end
    end
    return nil, 'unavailable'
end
function M.log(message)
    message = tostring(message):gsub('[A-Za-z]:[\\/][^%s"]+', '<path>'):gsub('/Users/[^%s"]+', '<path>')
    if type(Log) == 'function' then Log('[LCA] ' .. message) else print('[LCA] ' .. message) end
end
function M.snapshot(config, event)
    if M.call('IsInCM') ~= true then return nil, 'career mode not confirmed' end
    local stats = M.call('GetPlayersStats')
    if type(stats) ~= 'table' then return nil, 'GetPlayersStats unavailable' end
    local team = M.user_team_id()
    if type(team) ~= 'number' then return nil, 'user team unavailable' end
    local in_game_date = M.current_date()
    local rows = M.array()
    local keys = {
        'playerid','teamid','compobjid','app','goals','assists','yellow','two_yellow',
        'red','avg','clean_sheets','saves','goals_conceded','motm',
    }
    for _, row in pairs(stats) do
        if type(row) == 'table' and row.teamid == team then
            local out = {}
            for _, key in ipairs(keys) do
                out[key] = type(row[key]) == 'number' and row[key] or M.null
            end
            local name = M.call('GetPlayerName', row.playerid)
            if type(name) == 'string' then out.display_name = name end
            rows[#rows+1] = out
        end
    end
    table.sort(rows, function(a,b)
        return tostring(a.playerid)..':'..tostring(a.compobjid) < tostring(b.playerid)..':'..tostring(b.compobjid)
    end)
    -- GetSaveUID can INSERT a sponsors record. Never call it from this collector,
    -- even when an old local config sets save_uid_verified=true. Use instance_key.
    return {
        schema_version=1, producer='fc24-live-editor-lua', collector_version='0.3.1-safe',
        game_version='EA FC 24', captured_at_utc=os.date('!%Y-%m-%dT%H:%M:%SZ'),
        event=event or 'diagnostic', save_uid=M.null,
        instance_key=config.instance_key or M.null, in_game_date=in_game_date or M.null,
        season_start_year=config.season_start_year or M.null,
        user_team_id=team, rows=rows, completeness='UNKNOWN',
        -- Direct LE.db table scans are intentionally disabled. Repeated 0.3.0
        -- diagnostics that traversed the optional tables were followed by a
        -- reproducible save reload crash on the validated Windows build.
        team_states=M.array(), player_states=M.array(),
    }
end
function M.write(config, snapshot, prefix)
    assert(type(config.spool_dir) == 'string', 'configure spool_dir')
    assert(io and io.open and os and os.rename, 'file transport unavailable')
    _G.LCA_FILE_SEQ = (_G.LCA_FILE_SEQ or 0) + 1
    local filename = (prefix or 'snapshot') .. '-' .. os.date('!%Y%m%dT%H%M%S') .. '-' .. _G.LCA_FILE_SEQ .. '.json'
    local destination = config.spool_dir .. '/' .. filename
    local temp = destination .. '.tmp'
    for _, path in ipairs({temp, destination}) do
        local prior = io.open(path, 'rb')
        if prior then prior:close(); error('snapshot name collision; retry later') end
    end
    local f = assert(io.open(temp, 'wb'))
    assert(f:write(M.json(snapshot)))
    assert(f:close())
    local existing = io.open(destination, 'r')
    if existing then existing:close(); error('snapshot name collision; retry later') end
    assert(os.rename(temp, destination))
    return filename
end
return M
