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
local function db_table(name)
    local ok, value = pcall(function()
        if type(LE) ~= 'table' or type(LE.db) ~= 'table' then return nil end
        return LE.db:GetTable(name)
    end)
    if ok and type(value) == 'table' then return value end
    return nil
end
local function db_number(tbl, record, field)
    local ok, value = pcall(function() return tbl:GetRecordFieldValue(record, field) end)
    if ok and type(value) == 'number' then return value end
    return nil
end
local function db_first(tbl)
    local ok, value = pcall(function() return tbl:GetFirstRecord() end)
    if ok and type(value) == 'number' then return value end
    return 0
end
local function db_next(tbl)
    local ok, value = pcall(function() return tbl:GetNextValidRecord() end)
    if ok and type(value) == 'number' then return value end
    return 0
end
local function nullable_number(value)
    return type(value) == 'number' and value or M.null
end
local function collect_team_states(team)
    local result = M.array()
    local tbl = db_table('leagueteamlinks')
    if not tbl then return result end
    local fields = {
        'teamid','leagueid','nummatchesplayed','homewins','homedraws','homelosses',
        'awaywins','awaydraws','awaylosses','homegf','homega','awaygf','awayga',
        'points','currenttableposition','lastgameresult','teamform','teamshortform','teamlongform',
    }
    local record = db_first(tbl)
    while type(record) == 'number' and record > 0 do
        local teamid = db_number(tbl, record, 'teamid')
        local leagueid = db_number(tbl, record, 'leagueid')
        if teamid == team and type(leagueid) == 'number' then
            local row = {}
            for _, field in ipairs(fields) do row[field] = nullable_number(db_number(tbl, record, field)) end
            result[#result+1] = row
        end
        record = db_next(tbl)
    end
    table.sort(result, function(a,b) return a.leagueid < b.leagueid end)
    return result
end
local function collect_player_states(team, stats)
    local by_player, roster = {}, {}
    local function ensure(playerid)
        if type(playerid) ~= 'number' then return nil end
        if not by_player[playerid] then
            by_player[playerid] = {
                playerid=playerid, teamid=team, injury_id=M.null,
                injury_date_raw=M.null, injury_duration_days=M.null,
                last_match_minutes=M.null, last_match_overall=M.null,
                last_match_fact=M.null, last_match_position=M.null,
                latest_match_rating_raw=M.null, latest_match_rating_minutes=M.null,
                latest_match_rating_date_raw=M.null,
            }
        end
        roster[playerid] = true
        return by_player[playerid]
    end
    for _, source in pairs(stats) do
        if type(source) == 'table' and source.teamid == team then ensure(source.playerid) end
    end
    local links = db_table('teamplayerlinks')
    if links then
        local record = db_first(links)
        while type(record) == 'number' and record > 0 do
            if db_number(links, record, 'teamid') == team then
                local row = ensure(db_number(links, record, 'playerid'))
                if row then row.injury_id = nullable_number(db_number(links, record, 'injury')) end
            end
            record = db_next(links)
        end
    end
    local growth = db_table('career_playerlastgrowth')
    if growth then
        local record = db_first(growth)
        while type(record) == 'number' and record > 0 do
            local playerid = db_number(growth, record, 'playerid')
            local row = roster[playerid] and by_player[playerid] or nil
            if row then
                row.injury_date_raw = nullable_number(db_number(growth, record, 'injurydate'))
                row.injury_duration_days = nullable_number(db_number(growth, record, 'injuryduration'))
            end
            record = db_next(growth)
        end
    end
    local last_match = db_table('career_playerlastmatchhistory')
    if last_match then
        local record = db_first(last_match)
        while type(record) == 'number' and record > 0 do
            if db_number(last_match, record, 'teamid') == team then
                local row = ensure(db_number(last_match, record, 'playerid'))
                if row then
                    row.last_match_minutes = nullable_number(db_number(last_match, record, 'minsplayed'))
                    row.last_match_overall = nullable_number(db_number(last_match, record, 'playeroverall'))
                    row.last_match_fact = nullable_number(db_number(last_match, record, 'playerfact'))
                    row.last_match_position = nullable_number(db_number(last_match, record, 'position'))
                end
            end
            record = db_next(last_match)
        end
    end
    local ratings, rating_key = db_table('career_playermatchratinghistory'), {}
    if ratings then
        local record = db_first(ratings)
        while type(record) == 'number' and record > 0 do
            local playerid = db_number(ratings, record, 'playerid')
            local date = db_number(ratings, record, 'date')
            if roster[playerid] and type(date) == 'number' then
                local artificial = db_number(ratings, record, 'artificialkey') or 0
                local key = date * 1000000 + artificial
                if not rating_key[playerid] or key > rating_key[playerid] then
                    rating_key[playerid] = key
                    local row = by_player[playerid]
                    row.latest_match_rating_raw = nullable_number(db_number(ratings, record, 'rating'))
                    row.latest_match_rating_minutes = nullable_number(db_number(ratings, record, 'minsplayed'))
                    row.latest_match_rating_date_raw = date
                end
            end
            record = db_next(ratings)
        end
    end
    local result = M.array()
    for playerid, row in pairs(by_player) do
        local name = M.call('GetPlayerName', playerid)
        if type(name) == 'string' then row.display_name = name end
        result[#result+1] = row
    end
    table.sort(result, function(a,b) return a.playerid < b.playerid end)
    return result
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
    local uid = config.save_uid_verified and M.call('GetSaveUID') or nil
    if uid ~= nil then uid = tostring(uid) end
    return {
        schema_version=1, producer='fc24-live-editor-lua', collector_version='0.3.1-safe',
        game_version='EA FC 24', captured_at_utc=os.date('!%Y-%m-%dT%H:%M:%SZ'),
        event=event or 'diagnostic', save_uid=uid or M.null,
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
