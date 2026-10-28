# 0002: explicit synthetic demo for macOS

Accepted 2026-10-28 after the user explicitly requested stub data and a Mac launch.

The original specification prohibits silently fabricated production/game data. The follow-up authorizes a separate synthetic demo. The normal app.main path keeps real historical data and its game verification gates. app.demo uses data-demo/, a marker-guarded database, fictional player names, DEMO_SYNTHETIC coverage and demo source/quality DTOs. It never marks a save verified_live. Normal ingestion rejects lca-demo-simulator payloads; demo ingestion rejects game-source payloads. The demo controls endpoint exists only in demo mode.

Synthetic snapshots pass through the existing ingestion/watcher pipeline. A manual demo-only control queues another synthetic cumulative observation without pretending to play a real match. The browser prominently labels the sandbox; localhost:8001 coexists with the normal localhost:8000 application. No game checks are promoted by this demo.
