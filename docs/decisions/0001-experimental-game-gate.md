# 0001: keep automation gated without game evidence

Status: accepted, 2026-10-28.

The development host is macOS and no actual FC24 session is available. The legacy API is documented but deprecated; post__CareerModeEvent does not prove that final counters or season context are available. Therefore the code includes a read-only experimental collector with explicit gates, not a fabricated working integration. Event IDs resolve from installed symbolic constants. Automatic season_reader is a required verified adapter, not an assumed calendar boundary. Real P0 logs and a Windows test remain required.

The Python queue and dashboard are fully testable offline using isolated synthetic fixtures and the user's actual historical workbook. Neither counts as P0/P2 game verification. No manual screenshots are requested as a gameplay data source.
