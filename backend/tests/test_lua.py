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
    assert payload["rows"][0]["two_yellow"] is None
    assert payload["rows"][0]["saves"] is None
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["display_name"] == 'João "Test"'
    assert payload["save_uid"] is None
    core.write(config, doc)
    core.write(config, doc)
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert not list(tmp_path.glob("*.tmp"))


def test_lua_v2_context_fallback_when_legacy_globals_are_absent(tmp_path):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
      function IsInCM() return true end
      function GetPlayersStats() return {
        {playerid=1,teamid=191,compobjid=2,app=1,goals=0,assists=0}
      } end
      function GetCurrentDate() return {year=2024,month=7,day=1} end
      LE = {db={}}
      function LE.db:GetTable(name)
        assert(name == 'career_users')
        return {
          GetFirstRecord=function() return 123 end,
          GetRecordFieldValue=function(_, record, field)
            assert(record == 123 and field == 'clubteamid')
            return 191
          end
        }
      end
    """)
    core = lua.execute((COLLECTOR / "common.lua").read_text())
    config = lua.table_from(
        {"spool_dir": str(tmp_path), "instance_key": "v2-context", "season_start_year": 2024}
    )
    doc = core.snapshot(config, "diagnostic")
    payload = json.loads(core.json(doc))
    assert payload["user_team_id"] == 191
    assert payload["in_game_date"] == "2024-07-01"
    assert len(payload["rows"]) == 1


def test_lua_does_not_scan_optional_db_tables():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
      function IsInCM() return true end
      function GetUserTeamID() return 95 end
      function GetCurrentDate() return {year=2024,month=7,day=8} end
      function GetPlayerName(id) return 'State Player' end
      function GetPlayersStats() return {
        {playerid=7,teamid=95,compobjid=2,app=2,goals=1,assists=0,
         two_yellow=1,saves=3,goals_conceded=2,motm=1}
      } end
      LE = {db={}}
      function LE.db:GetTable(name) error('optional DB scan attempted: ' .. name) end
    """)
    core = lua.execute((COLLECTOR / "common.lua").read_text())
    config = lua.table_from({"instance_key": "state-test", "season_start_year": 2024})
    payload = json.loads(core.json(core.snapshot(config, "diagnostic")))
    assert payload["collector_version"] == "0.3.1-safe"
    assert payload["in_game_date"] == "2024-07-08"
    assert payload["rows"][0]["motm"] == 1
    assert payload["team_states"] == []
    assert payload["player_states"] == []


def test_diagnostic_refuses_capture_without_manual_ack(tmp_path):
    for file in ("common.lua", "diagnostic.lua"):
        (tmp_path / file).write_text((COLLECTOR / file).read_text())
    (tmp_path / "config.lua").write_text("return {manual_capture_ack=false}")
    lua = LuaRuntime()
    lua.globals().LCA_ROOT = str(tmp_path)
    lua.execute("stats_calls=0; function GetPlayersStats() stats_calls=stats_calls+1; return {} end")
    lua.execute((tmp_path / "diagnostic.lua").read_text())
    assert lua.globals().stats_calls == 0


def test_probe_does_not_duplicate_callbacks():
    lua = LuaRuntime()
    lua.globals().LCA_ROOT = str(COLLECTOR)
    lua.globals().LCA_UNSAFE_EVENT_PROBE_ACK = True
    lua.execute("""
      registered=0
      enum_loads=0
      function require(name)
        assert(name == 'imports/career_mode/enums')
        enum_loads=enum_loads+1
        ENUM_CM_EVENT_MSG_USER_MATCH_COMPLETED=6
        return true
      end
      function AddEventHandler(name, fn) registered=registered+1 end
    """)
    lua.execute((COLLECTOR / "event_probe.lua").read_text())
    lua.execute((COLLECTOR / "event_probe.lua").read_text())
    assert lua.globals().registered == 1
    assert lua.globals().enum_loads == 2


def test_probe_refuses_registration_without_unsafe_ack():
    lua = LuaRuntime()
    lua.globals().LCA_ROOT = str(COLLECTOR)
    lua.execute("registered=0; function AddEventHandler() registered=registered+1 end")
    lua.execute((COLLECTOR / "event_probe.lua").read_text())
    assert lua.globals().registered == 0


def test_collector_stays_hard_disabled_after_live_callback_failure(tmp_path):
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
