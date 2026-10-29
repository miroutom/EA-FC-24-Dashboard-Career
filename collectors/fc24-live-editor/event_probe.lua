assert(type(LCA_ROOT) == 'string', 'Set LCA_ROOT')
local core = dofile(LCA_ROOT .. '/common.lua')
assert(type(AddEventHandler) == 'function', 'event API unavailable')
-- Live Editor v2 keeps the readable Career Mode event names in this module.
-- Load it even when the callback is already registered: the existing callback
-- resolves names from _G at event time, so rerunning the probe upgrades the
-- current session without registering a second handler.
pcall(require, 'imports/career_mode/enums')
if _G.LCA_UNSAFE_EVENT_PROBE_ACK ~= true then
    core.log('event probe disabled: callback sessions were followed by save reload failures; use disposable saves only')
    return
end
if _G.LCA_PROBE_REGISTERED then core.log('probe already registered'); return end
local sequence = 0
local names_by_id = {}
for name, value in pairs(_G) do
    if type(name)=='string' and name:match('^ENUM_CM_EVENT_MSG_') and type(value)=='number' then
        local names = names_by_id[value]
        if not names then names = {}; names_by_id[value] = names end
        names[#names+1] = name
    end
end
for _, names in pairs(names_by_id) do table.sort(names) end
local function probe(_, event_id, _event)
    sequence = sequence + 1
    local names = names_by_id[event_id] or {}
    core.log('probe sequence='..sequence..' event_id='..tostring(event_id)..' symbols='..table.concat(names, ',')..' utc='..os.date('!%Y-%m-%dT%H:%M:%SZ'))
end
AddEventHandler('post__CareerModeEvent', probe)
_G.LCA_PROBE_REGISTERED = true
