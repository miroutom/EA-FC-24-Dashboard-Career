> Later review — 2026-10-29: [all 12 minidumps](crash-investigation-2026-10-29.md)
> show the same FC24 instruction, including sessions without LCA output. The
> observations below do not establish which operation causes the load failure.
> Earlier wording claiming that one successful reload proves manual capture safe,
> or that callback capture is the proven cause, is superseded by this review.

# Windows live validation evidence — 2026-10-28

## Scope and versions

- Offline disposable manager career, season 2024/25, RB Salzburg (`user_team_id=191`).
- EA FC 24 runtime log version `1.0.120.18322`; installed file product version `24.0.5929398.0`; Steam build ID `25351902`.
- FC 24 Live Editor `v24.1.1.9`.
- Diagnostic payloads used `completeness=UNKNOWN`. Save UID was unavailable/null, so the explicit local instance binding remained the identity fallback.
- Screenshots were used only to validate the diagnostic output. They are not an ingestion source.

## Transport and context

The embedded Lua runtime wrote real JSON payloads atomically. The local watcher archived and imported them without quarantine or watcher errors. Installed v2 fallbacks read the user team from `career_users` and the ISO date through the installed helpers module. The event probe loaded the installed `imports/career_mode/enums` symbols and its duplicate-registration guard held.

## Played match

Observed result: RB Salzburg 10:0 LASK.

| Point | Raw SHA-256 | In-game date | Apps | Goals | Assists | Red | Clean-sheet rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Before | `195e32ade4e78c61e46f83ebb4b6ca6c20a7082e074c4f38c359a1b188df5934` | 2024-07-28 | 16 | 10 | 10 | 0 | 11 |
| Post-match report | `891d88a5b726a833192f0c64d01c53c6b755ffb841d20d9af942014cf12e5cdc` | 2024-07-28 | 16 | 10 | 10 | 0 | 11 |
| Hub | `491a5131d911c6beee6a7a94eaa3023685df52842c633fce3310c54ea17ab670` | 2024-08-05 | 32 | 20 | 20 | 1 | 22 |

The report snapshot was unchanged. The hub delta matched the screenshots:

- Karim Konaté: +1 app, +5 goals, +2 assists.
- Roko Šimić: +1 app, +2 goals, +5 assists.
- Strahinja Pavlović: +1 app, +1 goal, +1 red.
- Maurits Kjærgaard: +1 app, +1 goal, +1 assist.
- Oscar Gloukh: +1 app, +1 goal, +1 assist.
- Mads Bidstrup: +1 app, +1 assist.

The match screen showed Pavlović receiving two yellows and the resulting red. `GetPlayersStats` exposed the red increment but no yellow increment; therefore these season counters cannot be claimed as a complete match-card feed.

Relevant event order:

1. `ENUM_CM_EVENT_MSG_ABOUT_TO_ENTER_PREMATCH`
2. `ENUM_CM_EVENT_MSG_ABOUT_TO_ENTER_A_MATCH`
3. `ENUM_CM_EVENT_MSG_HIGHLIGHTS_READY`
4. `ENUM_CM_EVENT_MSG_USER_MATCH_COMPLETED`
5. `ENUM_CM_EVENT_MSG_DAY_PASSED`
6. `ENUM_CM_EVENT_MSG_PREPARE_FOR_SAVE`
7. `ENUM_CM_EVENT_MSG_ENTERED_HUB_FIRST_TIME`

## Quick simulation

Observed result: Austria Wien 0:1 RB Salzburg; Roko Šimić scored at 46 minutes.

| Point | Raw SHA-256 | In-game date | Apps | Goals | Assists | Red | Clean-sheet rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Before | `e401c69b30b4e6411c5c414b302d8892e7dc85e5299c417cc5b74c2a4955418b` | 2024-08-05 | 32 | 20 | 20 | 1 | 22 |
| Result screen | `b430ea6b57d7eb9128cad8208eb87aea5103d5984b7b3cc9d2060bee1aec902c` | 2024-08-05 | 45 | 21 | 21 | 1 | 32 |
| Hub | `3c03c1b89d6df40cbc8dc31cabef780f822c0ed591a0dcc9340f50061610b83a` | 2024-08-11 | 45 | 21 | 21 | 1 | 32 |

The result-screen delta contained 13 appearances, Šimić +1 goal, Lucas Gourna-Douath +1 assist and 10 clean-sheet rows. The hub state was identical. Raw `avg` deltas tracked the displayed simulation ratings ×10, subject to the game's internal rounding; the application continues to preserve this as raw cumulative data rather than presenting it as a verified average.

Relevant event order:

1. `ENUM_CM_EVENT_MSG_ABOUT_TO_ENTER_PREMATCH`
2. `ENUM_CM_EVENT_MSG_ABOUT_TO_ENTER_QUICK_SIM`
3. `ENUM_CM_EVENT_MSG_CPU_MATCH_COMPLETED` (multiple competition updates)
4. `ENUM_CM_EVENT_MSG_USER_MATCH_COMPLETED`
5. result screen with finalized counters
6. `ENUM_CM_EVENT_MSG_DAY_PASSED`
7. `ENUM_CM_EVENT_MSG_WEEK_PASSED`
8. `ENUM_CM_EVENT_MSG_PREPARE_FOR_SAVE`
9. `ENUM_CM_EVENT_MSG_ENTERED_HUB_FIRST_TIME`

## Gate result and remaining work

Gate P0 passes: real player counters changed across a real match and the embedded Lua-to-Python file path worked. The automatic collector remains disabled because the following are not yet verified:

- a safe deferred execution mechanism outside CareerModeEvent callbacks;
- automatic season context and rollover;
- save UID stability, reload and older-save conflict behavior;
- interactive simulation, if it will be used;
- script auto-start and unassisted capture after a full restart.

Consequently `verified_live`, `completeness=COMPLETE`, config verification flags and P2 remain unset.

## Reload observation

The first attempt to reload the freshly saved career ended in an FC 24 crash while Live Editor reported `ENUM_CM_EVENT_MSG_INITIAL_USER_ADDED` followed by `ENUM_CM_EVENT_MSG_SET_NUM_USERS`. No diagnostic script was executing and no Lua error preceded the crash. FC 24 produced two minidumps. The current and preceding career files were both present with the same nonzero size, and all previously imported dashboard data remained intact.

A controlled retry after a full game/Live Editor restart crashed on the same career. Live Editor logged an empty autorun pass, no new LCA script output, and then two new minidumps. A newly created career and the user's separate Leicester career both reloaded successfully under the same downgraded game/Live Editor environment. This isolates the failure to the `Live P0 Test` save state, but does not establish what corrupted it. The LCA diagnostic uses only getters plus filesystem output outside the game save, the event probe only logs callbacks, and the gated experimental collector never ran; no LCA code path mutates the game database or save.

Both affected career files were copied to the ignored local preflight backup before further testing. The event probe was also optimized to cache installed symbol names instead of rescanning Lua globals for every event. It must not be used during recovery or on a valued career. Reload stability for a fresh disposable test save remains to be established after any future diagnostic step.

A fresh disposable RB Salzburg career was then created with a new explicit instance binding. It reloaded before any LCA code, produced a diagnostic snapshot at `2024-07-01`, was saved to a separate slot, and reloaded successfully afterward. The payload was imported only into the new dashboard career; the corrupted save's snapshots were unchanged. This single controlled check observed a successful reload; it does not establish that repeated diagnostics are safe. The original save corruption remains unexplained; the old high-volume event-probe session is not proof of causality and will not be repeated on the replacement save.

## Callback safety failure

A replacement disposable career was saved and reloaded successfully after manual diagnostics. A narrow one-shot timing probe was then registered for quick-sim entry, `USER_MATCH_COMPLETED`, `PREPARE_FOR_SAVE` and hub entry. It captured only those four events:

- pre-sim at `2024-08-04`: 27 apps, 7 goals, 5 assists;
- `USER_MATCH_COMPLETED`: 39 apps, 10 goals, 6 assists, proving quick-sim counters were already final;
- `PREPARE_FOR_SAVE` and hub at `2024-08-11`: the same finalized counters.

The match result was WSG Tirol 0:3 RB Salzburg (Roko Šimić 2, Lucas Gourna-Douath 1). After saving, that slot crashed on reload and produced two new minidumps. This reproduces the unsafe boundary: manual diagnostics followed by save/reload passed, while sessions with CareerModeEvent callback activity produced non-reloadable saves. The probe did not mutate the game database, but doing `GetPlayersStats` and filesystem work synchronously inside the callback is not save-safe on this installed build. The timing probe was removed, the broad event probe now requires an explicit unsafe acknowledgement, and `collector.experimental.lua` was hard-disabled. P2 is BLOCKED until capture work can be deferred outside the callback and a fresh disposable save passes reload testing.

## Manual collector 0.3 observation — 2026-10-29

A single manual hub diagnostic from the reload-safe test line produced collector `0.3.0` at in-game date `2024-08-17`. The existing watcher imported the same quarantined file successfully after widening the validated rating-date field to the observed `YYYYMMDD` representation. No second game capture was required.

Observed payload coverage:

- 32 season-stat rows and 32 player-state rows;
- tournament `compobjid=364`, with 42 summed player appearances, 20 goals and 14 assists across three recorded matches;
- one goalkeeper save and two raw goals-conceded for Alexander Schlager;
- yellow counters for Karim Konaté, Oumar Solet and Aleksa Terzić, plus one red for Lucas Gourna-Douath;
- 11 players with a last-match-history row and 16 with a coarse integer rating-history row dated `20240810`;
- no nonzero injury ID in this observation.

The sole `leagueteamlinks` row was inconsistent as a live standings source: `nummatchesplayed=10` while all six W/D/L counters and all GF/GA counters were zero. The backend now requires `matches = wins + draws + losses` before exposing a league record or deriving W/D/L. This raw row remains stored for audit but is hidden from dashboard records. Exact season form therefore remains unavailable from the installed Live Editor database tables.

## Repeated manual 0.3 safety failure — 2026-10-29

The user captured a pre-match `0.3.0` diagnostic at `00:11:25`, played SK Sturm Graz 0:13 RB Salzburg, and captured a post-match diagnostic at `00:22:54–00:22:55`. The watcher imported the post-match JSON successfully at in-game date `2024-08-18`; there was no Lua or ingestion error. Career files were written at `00:22:34`, `00:22:41` and `00:23:30`. Loading the new `Safe After Match 1` slot then crashed FC 24, producing minidumps at `00:23:40.328` and `00:23:41.728`.

This invalidates the earlier assumption that manual diagnostics were a safe continuing collection path. It does not prove which Live Editor operation damages the save, but the strongest new difference from the earlier basic diagnostic is traversal of `leagueteamlinks`, `teamplayerlinks`, `career_playerlastgrowth`, `career_playerlastmatchhistory` and `career_playermatchratinghistory`. All three career files, both minidumps, the Live Editor log and raw JSON were copied unchanged to the ignored local preflight backup.

Collector `0.3.1-safe` no longer invokes any of those optional table scans, and `diagnostic.lua` now refuses capture unless a local manual acknowledgement is explicitly set. No further Lua test is authorized on the user's good `Safe` slot. Future match ingestion must use already archived evidence, screenshots, or a parser operating on a copied save outside the game process.

The archived evidence was imported as explicit match record `SK Sturm Graz 0:13 RB Salzburg` dated `2024-08-17`. It contains 26 local screenshots, 18 timeline events, 16 player-performance rows and the displayed team metrics (including 9.6 xG, 59% possession, 22 shots, 16 on target, 49 passes, 21 tackles and 0 saves for Salzburg). Goals, assists and ratings were cross-checked against the exact snapshot delta. The gold MOTM marker identifies Roko Šimić; the raw season `motm` counter changed for Oumar Solet and remains semantically unvalidated rather than silently overriding the screen.
