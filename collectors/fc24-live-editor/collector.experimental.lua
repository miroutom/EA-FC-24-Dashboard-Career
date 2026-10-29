-- Disabled after real Windows evidence showed that reading/writing snapshots
-- directly inside CareerModeEvent callbacks can leave a save unable to reload.
-- A future collector must defer work out of the callback and pass a disposable
-- save/reload test before this file may register any handler.
assert(type(LCA_ROOT) == 'string', 'Set LCA_ROOT')
local core = dofile(LCA_ROOT .. '/common.lua')
core.log('collector disabled: in-callback capture is unsafe on the validated FC24/Live Editor build')
