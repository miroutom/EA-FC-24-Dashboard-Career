assert(type(LCA_ROOT) == 'string', 'Set LCA_ROOT')
local core = dofile(LCA_ROOT .. '/common.lua')
assert(type(AddEventHandler) == 'function', 'event API unavailable')
if _G.LCA_PROBE_REGISTERED then core.log('probe already registered'); return end
local sequence = 0
local function probe(_, event_id, _event)
    sequence = sequence + 1
    local names = {}
    for name, value in pairs(_G) do
        if type(name)=='string' and name:match('^ENUM_CM_EVENT_MSG_') and value==event_id then names[#names+1]=name end
    end
    table.sort(names)
    core.log('probe sequence='..sequence..' event_id='..tostring(event_id)..' symbols='..table.concat(names, ',')..' utc='..os.date('!%Y-%m-%dT%H:%M:%SZ'))
end
AddEventHandler('post__CareerModeEvent', probe)
_G.LCA_PROBE_REGISTERED = true
