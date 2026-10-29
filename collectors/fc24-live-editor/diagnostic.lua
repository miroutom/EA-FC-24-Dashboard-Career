-- Recovery hold: legacy local acknowledgements cannot re-enable game reads.
-- Native crashes are outside pcall's protection. See the crash investigation.
print('[LCA] diagnostic disabled: save/reload investigation pending; no game API called')
