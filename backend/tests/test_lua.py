import json
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "collectors" / "fc24-live-editor"


def test_lua_readonly_snapshot_serialization_and_atomic_write(tmp_path):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
      function IsInCM() return true end
      function GetUserTeamID() return 95 end
      function GetPlayerName(id) return 'João "Test"' end
      function GetPlayersStats() return {
        {playerid=1,teamid=95,compobjid=2,app=10,goals=4,assists=3,avg=72},
        {playerid=2,teamid=10,compobjid=2,app=10,goals=8}
      } end
    """)
    core = lua.execute((COLLECTOR / "common.lua").read_text())
    config = lua.table_from({"spool_dir": str(tmp_path), "instance_key": "synthetic-test"})
    doc = core.snapshot(config, "test")
    payload = json.loads(core.json(doc))
    assert payload["rows"][0]["goals"] == 4
    assert payload["rows"][0]["clean_sheets"] is None
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["display_name"] == 'João "Test"'
    assert payload["save_uid"] is None
    core.write(config, doc)
    core.write(config, doc)
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert not list(tmp_path.glob("*.tmp"))


def test_probe_does_not_duplicate_callbacks():
    lua = LuaRuntime()
    lua.globals().LCA_ROOT = str(COLLECTOR)
    lua.execute("registered=0; function AddEventHandler(name, fn) registered=registered+1 end")
    lua.execute((COLLECTOR / "event_probe.lua").read_text())
    lua.execute((COLLECTOR / "event_probe.lua").read_text())
    assert lua.globals().registered == 1


def test_collector_gate_closed_without_real_game_evidence(tmp_path):
    for file in ("common.lua", "collector.experimental.lua"):
        (tmp_path / file).write_text((COLLECTOR / file).read_text())
    (tmp_path / "config.lua").write_text("return {enabled=false}")
    lua = LuaRuntime()
    lua.globals().LCA_ROOT = str(tmp_path)
    lua.execute("registered=0; function AddEventHandler() registered=registered+1 end")
    lua.execute((tmp_path / "collector.experimental.lua").read_text())
    assert lua.globals().registered == 0


def test_diff_negative_not_reported_as_negative_goal():
    import importlib.util

    spec = importlib.util.spec_from_file_location("diagnose", ROOT / "scripts" / "diagnose_snapshots.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = {"rows": [{"playerid": 1, "teamid": 95, "compobjid": 2, "app": 10, "goals": 8}]}
    after = {"rows": [{"playerid": 1, "teamid": 95, "compobjid": 2, "app": 10, "goals": 3}]}
    assert module.compare(before, after)[0]["delta"] is None
