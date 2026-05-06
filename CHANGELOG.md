# Changelog

## v0.6.0 — Forza focus, post-race modal flow, live race position (2026-05-06)

**Modular refactor** — `listener.py` was a single ~3K-line file; split into focused modules. No behavior change, but every later feature in this release benefited.

- Extracted `config.py`, `db/store.py`, `parsers/{forza,acc,f1}.py`, `reference/loader.py`, `session/{manager,protocol,watchdog}.py`, `net/{router,api,server,pages}/*.py`
- `static/` split too: per-page CSS + JS, shared `tokens.css` + `base.css`

**Forza-only focus** — ACC and F1 are parked. Code stays in tree, not bound at startup, hidden from UI. ([#15](https://github.com/Estetika101/pacefinderapp/issues/15), [#16](https://github.com/Estetika101/pacefinderapp/pull/16))

- Listener no longer binds ACC (9996) or F1 (20777); no more port-conflict warning at startup
- `/sessions` is now the Forza overview directly (multi-game tabs gone, `/sessions/game?name=forza_motorsport` → 301 → `/sessions`)
- README, GitHub repo description, marketing site (`pacefindermarketing#21`) all updated to Forza-only with "ACC and F1 coming soon"

**Post-race modal flow** — capture metadata at the natural moment, no manual Edit click required. ([#7](https://github.com/Estetika101/pacefinderapp/pull/25), [#5](https://github.com/Estetika101/pacefinderapp/pull/26), [#4](https://github.com/Estetika101/pacefinderapp/pull/27), [#2 + #3](https://github.com/Estetika101/pacefinderapp/pull/28), [#6](https://github.com/Estetika101/pacefinderapp/pull/29))

- Race-end auto-detect from `is_race_on` 1→0 transition — modal appears within ~1s of crossing the line, no longer waiting 10s for the silence timeout. New `closed_reason` column distinguishes `race_end` / `timeout` / `idle_timeout`.
- Weather selector (Dry / Damp / Wet / Snow), default Dry; reads telemetry-derived ambient/track temps as read-only context
- Tyre compound selector (Street / Sport / Race / Slick / Rally / Off-Road / Drag), optional, no default
- Track dropdown merged from FM2023_TRACKS + `data/fm8_tracks_extended.csv` + per-user `learned_track_ordinals`. Switched from `<select>` to `<input list>` + `<datalist>` for type-ahead search and free-form entry.
- Car free-text override + "Unknown Car" fallback for unmapped car ordinals (e.g. ordinal 42 from pre-FM8 era)
- Modal opens optimistically (no longer blocks on `/finish` POST), no auto-replay after Save

**Live dashboard race position** — current position, grid start, ± gained vs grid. ([#30](https://github.com/Estetika101/pacefinderapp/pull/33))

- Three-cell mini-grid in the Lap Timing column (Pos / Grid / ±)
- Real grid detected via `current_race_time` reset signal — Forza ticks `current_race_time` UP during the countdown then RESETS to ~0 at lights-drop. The position at that reset is the real grid slot. (Multiple iterations; final fix in [#41](https://github.com/Estetika101/pacefinderapp/pull/41))
- Position widget hidden until race actually starts — no more phantom P1 leaking through ([#42](https://github.com/Estetika101/pacefinderapp/pull/42))

**Position display across all session views** — Grid → Finish → ± everywhere a session is rendered. ([#35](https://github.com/Estetika101/pacefinderapp/pull/35))

- Recent feed: `P5 → P3 +2`
- Per-circuit aggregate: `Pavg.f` plus `±Y.Y` avg gained
- Track detail table: separate Grid / Finish / ± columns
- Session detail header: three new stat blocks
- KPI color fix: avg-gained renders red when negative ([#43](https://github.com/Estetika101/pacefinderapp/pull/43))

**Telemetry tab DELTA fix** — sector deltas + cumulative chart now show real values. ([#1](https://github.com/Estetika101/pacefinderapp/pull/13))

- Per-lap Δ column (was a single ambiguous column showing `+0.000` everywhere)
- Cumulative DELTA chart renders one trace per non-reference lap
- Δ column hidden when only the reference lap is selected

**Data + reference**

- New `data/fm8_tracks_extended.csv` with 9 seed mappings for circuit variants the bluemanos base list doesn't cover (Mugello, Maple Valley, Yas Marina, Spa, Bathurst, Brands Hatch GP, VIR, Grand Oak National, Hakone Reversed) plus user-added Sunset Peninsula + Nürburgring Sprint
- New `data/fm8_cars_extended.csv` (empty, awaiting ordinal 42 research)
- New `data/README.md` documenting source attribution, format, precedence, contribution process
- Loader logs `Loaded N base + M extended FM tracks, X base + Y extended FM cars` at startup

**Spec-first workflow** — established `docs/specs/` as canonical spec home

- 12 specs written for shipped + planned work (sector-delta-fix, cross-chart-cursor-sync, track-map-interactivity, tire-panel, reference-selector-additions, race-end-detection, post-race-{weather,tyre-compound,track-dropdown}, fm8-tracks-extended-csv, car-ordinal-resolution, park-acc-f1, marketing-videos)
- Each spec gets a matching GitHub issue with cross-link

**Cleanups + smaller fixes**

- Removed broken Telemetry tab from track-detail page ([#18](https://github.com/Estetika101/pacefinderapp/pull/19))
- Default Form chart filter switched from `Real` to `All` so `time_trial` sessions populate ([#17](https://github.com/Estetika101/pacefinderapp/pull/20))
- Dashboard "Reset" button removed (was a no-op)
- Finish-modal auto-open delay dropped 5s → 500ms
- Listener `_clear_race_ended` import that was missing after the refactor ([#14](https://github.com/Estetika101/pacefinderapp/pull/14))
- README, GitHub repo description, CLAUDE.md aligned to Forza-only ([#22](https://github.com/Estetika101/pacefinderapp/pull/22))

## v0.5.0 — Sessions hierarchy + game selector (2026-05-02)

- `7f5eba8` Sessions nav is now a 4-level hierarchy: Sessions → Game → Track → Session
- `/sessions` serves a game selector (Forza / ACC / F1 cards with session/track counts)
- `/sessions/game?name=X` serves the tracks grid filtered by game
- `/sessions/track?name=X&game=Y` breadcrumb now shows game level with correct back-link
- `/sessions/session?id=X&game=Y&track=Z` breadcrumb reconstructs full chain
- `game` param threaded through all URL navigation and DB queries
- New `/sessions/games` JSON endpoint (`_db_games_index()`)
- `/sessions/tracks` and `/sessions/track/data` now accept optional `?game=` filter

## v0.4.0 — SQLite + sessions UI refactor (2026-05-02)

- `b88cf98` SQLite layer live: `_db_init()` at startup, DB write on session close, migrate existing JSON sessions
- `a9312d8` `/sessions/data` returns summary-only rows (no lap data embedded); Finish Race overlay uses `/sessions/session/data?id=X`
- Three-level sessions UI: tracks index → track detail → session detail
- Per-track AI coaching tip (one sentence, cached in `track_tips` DB table)
- Track detail page: inline SVG spark graphs for lap time trends, best lap highlight, tip bar
- Session detail page: full lap table with slip metrics (avg slip, peak slip, slip > 0.1%)
- Slip stats computed on-demand from `_laps.json` samples (not stored in DB)
- AI analysis result cached in `sessions.ai_analysis` / `ai_analyzed_at` / `ai_model` columns

## v0.3.0 — Live dashboard redesign (2026-05-02)

- `f70d813` / `16ec1a6` Full-viewport 4-column layout: throttle | brake | rear slip | lap timing
- Vertical fill bars for throttle, brake, slip (height-based, not width)
- Gear / speed / RPM demoted to bottom strip (68px) — visible in cockpit, not primary UI
- Flash alerts: red border pulse on conflicting inputs, near-lockup, oversteer, pace delta > 1.5s
- `57df54b` Finish Race overlay on live dashboard showing final lap summary

## v0.2.0 — AI analysis + admin tools (2026-04-xx)

- `77f5c8c` `/analyze?id=X` endpoint — Claude API post-session analysis with historical baseline
- Prompt: per-lap table + last 3 sessions at same track for comparison
- `ca17928` `/admin` page — inject fake UDP packets, sliders for speed/throttle/brake/gear, presets
- `bd74c64` Debug console — SSE stream of all log output, color-coded, filter dropdown, autoscroll
- `311b1f5` Admin nav hidden by default; revealed with `?debug=true` on any page

## v0.1.0 — Core listener + dashboard (2026-04-xx)

- `b7abbc9` Initial commit: UDP listener for Forza Motorsport
- `2324d50` Full parser coverage (FM/FH5/ACC/F1), session lifecycle, lap tracking, live dashboard, replay tool
- `7a9d1d9` Setup page + persistent config (`simtelemetry.config.json`)
- `1acd604` Fix: read full POST body before parsing JSON config
- `807b928` `.gitignore` for config, local data, logs, raw archives
- `bc4a667` Idle detection — idle packets no longer create sessions or duplicate records
- `23b392f` Session idle timeout (30s no driving → auto-close); status dot shows active vs idle
- `b745b97` / `df43fe7` Forza track name resolution via `FORZA_TRACKS` ordinal map
- `38fa3cf` Storage path browser in Setup page
- FH5 auto-detect by packet size (311 vs 331 bytes)
- `56941f0` / `5fdb681` Topbar and sessions UI contrast improvements
