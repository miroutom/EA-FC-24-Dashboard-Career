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
function M.log(message)
    message = tostring(message):gsub('[A-Za-z]:[\\/][^%s"]+', '<path>'):gsub('/Users/[^%s"]+', '<path>')
    if type(Log) == 'function' then Log('[LCA] ' .. message) else print('[LCA] ' .. message) end
end
function M.snapshot(config, event)
    if M.call('IsInCM') ~= true then return nil, 'career mode not confirmed' end
    local stats = M.call('GetPlayersStats')
    if type(stats) ~= 'table' then return nil, 'GetPlayersStats unavailable' end
    local team = M.call('GetUserTeamID')
    if type(team) ~= 'number' then return nil, 'user team unavailable' end
    local rows = M.array()
    local keys = {'playerid','teamid','compobjid','app','goals','assists','yellow','red','avg','clean_sheets'}
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
        schema_version=1, producer='fc24-live-editor-lua', collector_version='0.2.0',
        game_version='EA FC 24', captured_at_utc=os.date('!%Y-%m-%dT%H:%M:%SZ'),
        event=event or 'diagnostic', save_uid=uid or M.null,
        instance_key=config.instance_key or M.null, in_game_date=M.null,
        season_start_year=config.season_start_year or M.null,
        user_team_id=team, rows=rows, completeness='UNKNOWN',
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
