# Changelog

## v0.7.5 — Honest theoretical best (2026-06-12)

One bug fix, found in the field:

- **Track references: guard theoretical best against rotated lap traces** ([#242](https://github.com/Estetika101/pacefinderapp/pull/242)). `distance_norm` is anchored to a lap's first recorded sample, so a trace that starts mid-track (mid-race telemetry join, packet drop at the line) rotates the sector windows while keeping Σsectors == lap_time — invisible to the 5% sum gate. One such lap at Barcelona donated a 27.95s "S2" (real S2s: 37–40s) and showed **+9.958s off theoretical** on a lap that was really +0.9s off. Laps whose sectors deviate >20% from the track's per-sector median are now excluded from sector references and their stored sectors cleared. Existing data heals automatically the next time each track's references recompute (any session close at that track).

## v0.7.4 — Home tells you what to work on (2026-06-11)

The dashboard home stops being a stats wall and starts coaching:

- **Tip engine** ([#238](https://github.com/Estetika101/pacefinderapp/pull/238)) — up to 4 ranked "ways to get sharper" cards on Home, drawn from your own session history, flattened into one card grid ([#237](https://github.com/Estetika101/pacefinderapp/pull/237)).
- **PB celebration + actionable stats** ([#234](https://github.com/Estetika101/pacefinderapp/pull/234)) — personal bests get noticed; the headline stats now point somewhere.
- **Layout polish** ([#235](https://github.com/Estetika101/pacefinderapp/pull/235), [#236](https://github.com/Estetika101/pacefinderapp/pull/236)) — hero padding, side-by-side "where the time is" leak cards at an even 50/50 split, edge-aware tooltips on telemetry.
- **Session detail fixes** ([#239](https://github.com/Estetika101/pacefinderapp/pull/239)) — empty Car Context resolved, events headline calmed.
- **Listener: friendly port-in-use error** ([#233](https://github.com/Estetika101/pacefinderapp/pull/233)) — when the dashboard port is taken, you're told what to do instead of getting a traceback.
- **Docs + CI** ([#231](https://github.com/Estetika101/pacefinderapp/pull/231), [#240](https://github.com/Estetika101/pacefinderapp/pull/240)) — ARCHITECTURE.md and CONTRIBUTING.md land; runner-setup actions bumped to latest majors.

## v0.7.3 — DM Mono web font + screenshot pipeline (2026-05-25)

Two-line hotfix after v0.7.2:

- **`@import` DM Mono in `static/tokens.css`** ([#226](https://github.com/Estetika101/pacefinderapp/pull/226)). The font stack declared `'DM Mono', 'Fira Mono', 'Courier New', monospace` but DM Mono was never loaded — no `@font-face`, no `<link>`. Browsers fell through to Fira Mono (not installed on most systems), then Courier New (Mac only), then generic monospace. The fallback's wider metrics overflowed hero lap times, stat cards, and TRACK TIP headings. Now served from Google Fonts via `@import url('...family=DM+Mono...&display=swap')` at the top of tokens.css; all pages import tokens.css so this fires once per page.
- **CI: install listener `requirements.txt` from marketing-side screenshot pipeline** ([Estetika101/pacefindermarketing#34](https://github.com/Estetika101/pacefindermarketing/pull/34)). After v0.7.2-rc6 added `platformdirs` as a runtime dep, the marketing screenshot pipeline started failing with `ModuleNotFoundError` on listener boot. Marketing CI now pulls from `listener-app/requirements.txt`.

Together: the v0.7.0 IA carousel + format-matrix shots on the marketing site now render in DM Mono instead of generic monospace, matching what users see on their own dashboard.

No other runtime changes vs v0.7.2.

## v0.7.2-rc6 — Installer matrix lands (2026-05-25)

Full distribution pipeline (#210, #216, #217, #219, #220, #221) shipping on every tag push:

- **macOS** → `Pacefinder.app` codesigned with the Mac App Distribution + Mac Installer Distribution certs, packaged as a signed `.pkg`, uploaded to App Store Connect via `xcrun altool` using an App Store Connect API key. Becomes available immediately in TestFlight for internal testers; external testers after Apple's Beta App Review on the first build per short-version. App Store submission is a separate downstream click.
- **Linux x64** + **Linux ARM (Pi 4 / Pi 5)** → AppImages built on `ubuntu-latest` and `ubuntu-24.04-arm` (native ARM runner — no QEMU), attached to the GitHub Release.
- **Docker** → multi-arch image (`linux/amd64`, `linux/arm64`) built with `docker buildx`, pushed to `ghcr.io/estetika101/pacefinder` with tags `latest`, `0.7.2`, `0.7.2-rc6`, and `sha-<short>`.

Listener code stays stdlib-only beyond one new pip dep (`platformdirs`) used to resolve per-user data dirs when the configured `storage_path` is unavailable. Existing Pi USB / dev configs untouched.

`CFBundleShortVersionString` strips the `-rc*` suffix (`0.7.2-rc1` → `0.7.2`) so successive rc builds and the eventual `v0.7.2` final share a short version, distinguished by `CFBundleVersion = GITHUB_RUN_NUMBER`. Apple requires three-integer short versions and monotonic build numbers within a short version.

The road from rc1 → rc6 caught four issues in CI that would have been painful to find post-release: PyInstaller's `_maybe_open_browser_on_first_run` writing the config file into the .app bundle and breaking codesign (`CONFIG_FILE` now resolves to `user_data_dir` when frozen); a revoked App Store Connect API key returning the unhelpful `-26000` auth error (pre-flight diagnostic step now isolates auth from upload); the placeholder `.icns` not actually existing yet (now generated, ready to be swapped for real artwork).

No user-visible runtime changes vs v0.7.1.

## v0.7.1 — Security hardening + Pi load widget (2026-05-24)

A focused follow-up to v0.7.0. Originated from a same-day review of orphaned files / code-quality / security.

**Security**

- **Anthropic API key no longer leaks via `GET /config`.** The previous handler returned the full config dict including `anthropic_api_key`. With `Access-Control-Allow-Origin: *` and no auth, any host on the LAN — or any web page the user visited while on the LAN — could `fetch('http://pi.local:8000/config')` and grab the key. `_redact_config()` now strips the value and surfaces a boolean `anthropic_api_key_set` so the Setup page renders a "key set" placeholder without ever receiving the secret. `POST /config` treats empty key as no-op, explicit `null` as clear.
- **CSRF gate on POST.** Same `Access-Control-Allow-Origin: *` meant any visited page could drive-by-POST to `/admin/inject`, `/reset`, `/config`, `/sessions/update`, `/sessions/delete`, `/cars/nickname`, `/finish`. `_csrf_ok()` now rejects POSTs whose `Origin` host doesn't match `Host`. Origin-less calls (curl, native test harness) still pass.
- **Path traversal closed on `sid` params.** `/sessions/laps`, `/analyze`, `/sessions/update`, `/sessions/delete` interpolated `sid` into file paths without bounds checking — `../` was accepted. `_safe_sid()` now rejects anything with `/`, `\`, `..`, leading `.`, or length >128.
- **Stored-XSS escapes** on the highest-risk site (`sessions_session.js` car-PB headline interpolated user-mutable `track` / `car_nickname` raw into innerHTML). New shared `static/js/_safe.js` exposes a global `escHtml()` loaded on all rendered pages; applied at the unescaped site.
- **`/browse` gated** the same way as POSTs — directory enumeration was previously open to any LAN host.

**Reliability**

- `/stream` now caps concurrent SSE clients at 32 and exits cleanly on `ConnectionError` / `BrokenPipeError` / `writer.is_closing()`. The idle-throttle from #124 is preserved.

**Performance**

- `Cache-Control: public, max-age=31536000, immutable` on `/sessions/laps` — closed sessions are immutable on disk; browsers no longer re-fetch on lap-switching.

**Pi system load widget**

- New `GET /system/load` endpoint returns CPU%, load avg, memory, CPU temp, disk usage from `/proc` and `/sys`. Stdlib only; fails gracefully on Mac/Windows (fields return `null`).
- Strip rendered in the Debug Console header on the dashboard. Polls every 2s while the panel is open; stops when closed.

## v0.7.0 — IA rebuild, Spotter, Deep Dive, perf pass (2026-05-24)

A big release. 165 PRs since v0.6.0. The app got a new information architecture (Home is now the front door, left rail replaces the top bar, Sessions is a filterable index), an AI Spotter pass, the Deep Dive analysis tab, a Pi-aware perf pass, and a much sturdier race-end / lap-detection path.

**Information architecture — Home, rail, and filterable Sessions**

- `/` is now an idle landing page; the live cockpit moved to `/dashboard`. Live status pill on the rail jumps to it from anywhere ([#130](https://github.com/Estetika101/pacefinderapp/pull/130), [#156](https://github.com/Estetika101/pacefinderapp/pull/156), [#157](https://github.com/Estetika101/pacefinderapp/pull/157))
- Home leads with the last-session hero card, a "what to work on" regression watchlist + worst-sector card, then improvement-first stats ([#198](https://github.com/Estetika101/pacefinderapp/pull/198), [#199](https://github.com/Estetika101/pacefinderapp/pull/199), [#201](https://github.com/Estetika101/pacefinderapp/pull/201), [#160](https://github.com/Estetika101/pacefinderapp/pull/160), [#182](https://github.com/Estetika101/pacefinderapp/pull/182), [#186](https://github.com/Estetika101/pacefinderapp/pull/186))
- Career stats folded into Home; old `/sessions` Career view retired ([#145](https://github.com/Estetika101/pacefinderapp/pull/145))
- Left rail replaces the top bar; "N new" badge tracks unattended captures ([#168](https://github.com/Estetika101/pacefinderapp/pull/168), [#185](https://github.com/Estetika101/pacefinderapp/pull/185), [#163](https://github.com/Estetika101/pacefinderapp/pull/163)–[#165](https://github.com/Estetika101/pacefinderapp/pull/165))
- `/sessions` is now a filterable index: pagination (25/page), column-header sort, multi-select facets, real needs-review toggle, lap-time sparkline per row, sticky header ([#167](https://github.com/Estetika101/pacefinderapp/pull/167), [#174](https://github.com/Estetika101/pacefinderapp/pull/174), [#175](https://github.com/Estetika101/pacefinderapp/pull/175), [#178](https://github.com/Estetika101/pacefinderapp/pull/178), [#187](https://github.com/Estetika101/pacefinderapp/pull/187), [#203](https://github.com/Estetika101/pacefinderapp/pull/203), [#208](https://github.com/Estetika101/pacefinderapp/pull/208))
- New `/cars` index and `/cars/<ordinal>` detail pages ([#128](https://github.com/Estetika101/pacefinderapp/pull/128), [#129](https://github.com/Estetika101/pacefinderapp/pull/129))
- Circuit page rebuild — layered-IA, PB lap racing-line outline as hero ([#135](https://github.com/Estetika101/pacefinderapp/pull/135), [#181](https://github.com/Estetika101/pacefinderapp/pull/181))
- Session-detail rebuild — Overview view, delta-line SVG hero, breadcrumb+subnav, edit modal polish ([#127](https://github.com/Estetika101/pacefinderapp/pull/127), [#131](https://github.com/Estetika101/pacefinderapp/pull/131), [#142](https://github.com/Estetika101/pacefinderapp/pull/142), [#152](https://github.com/Estetika101/pacefinderapp/pull/152), [#158](https://github.com/Estetika101/pacefinderapp/pull/158), [#159](https://github.com/Estetika101/pacefinderapp/pull/159))

**AI Spotter — coaching, deep-linked to laps**

- Mistakes & events detector promoted to production ([#133](https://github.com/Estetika101/pacefinderapp/pull/133), [#141](https://github.com/Estetika101/pacefinderapp/pull/141))
- Structured AI output — Card C corner-keyed cards ([#134](https://github.com/Estetika101/pacefinderapp/pull/134))
- Layout: full-width Coaching + 2-up finding cards; each finding deep-links to the right lap; prompt sharpened ([#195](https://github.com/Estetika101/pacefinderapp/pull/195), [#196](https://github.com/Estetika101/pacefinderapp/pull/196), [#197](https://github.com/Estetika101/pacefinderapp/pull/197))
- Mistakes/Opportunities surfaced modal-only from Telemetry ([#171](https://github.com/Estetika101/pacefinderapp/pull/171))

**Deep Dive analysis tab**

- New tab with track map, G-G diagram, speed trace, events timeline, lap comparison ([#111](https://github.com/Estetika101/pacefinderapp/pull/111), spec [#110](https://github.com/Estetika101/pacefinderapp/pull/110))
- Per-lap sector times (s1/s2/s3) on the laps table ([#126](https://github.com/Estetika101/pacefinderapp/pull/126))

**Telemetry tab**

- Reskin + track-map promotion (engine untouched) ([#137](https://github.com/Estetika101/pacefinderapp/pull/137), [#138](https://github.com/Estetika101/pacefinderapp/pull/138), [#143](https://github.com/Estetika101/pacefinderapp/pull/143))
- Cockpit HUD column on the right rail ([#193](https://github.com/Estetika101/pacefinderapp/pull/193))
- Cross-chart cursor sync with click-to-lock ([#54](https://github.com/Estetika101/pacefinderapp/pull/54))
- Reference selector: Last Lap + cross-session lap picker; cleaner theoretical-best ([#49](https://github.com/Estetika101/pacefinderapp/pull/49), [#56](https://github.com/Estetika101/pacefinderapp/pull/56))
- Live in-race delta vs this session's best lap ([#65](https://github.com/Estetika101/pacefinderapp/pull/65))

**Race-end & lap detection robustness** — the long tail

- Race-end auto-detect within ~3s, non-blocking `session.close()`, pause-aware ([#122](https://github.com/Estetika101/pacefinderapp/pull/122), [#108](https://github.com/Estetika101/pacefinderapp/pull/108))
- Real grid_pos via `current_race_time` reset detection; FM2023 fallback ([#41](https://github.com/Estetika101/pacefinderapp/pull/41), [#107](https://github.com/Estetika101/pacefinderapp/pull/107))
- Final-lap recovery — Forza zeroes `last_lap_time` at race end; recovered from telemetry ([#148](https://github.com/Estetika101/pacefinderapp/pull/148), [#153](https://github.com/Estetika101/pacefinderapp/pull/153), [#146](https://github.com/Estetika101/pacefinderapp/pull/146))
- Honest lap times — no fabricated partials, `LapRecord.close` honors None ([#116](https://github.com/Estetika101/pacefinderapp/pull/116), [#117](https://github.com/Estetika101/pacefinderapp/pull/117))
- Race-start anchors LapRecord cleanly, restart detection fires reliably ([#119](https://github.com/Estetika101/pacefinderapp/pull/119), [#120](https://github.com/Estetika101/pacefinderapp/pull/120))
- Dashboard "Best" / "Last" no longer leak from the previous race ([#118](https://github.com/Estetika101/pacefinderapp/pull/118))
- Debug-mode audible race-end announcement ([#149](https://github.com/Estetika101/pacefinderapp/pull/149))

**Live dashboard**

- Live takeover when a session starts ([#169](https://github.com/Estetika101/pacefinderapp/pull/169))
- Track PB + best-finish records inline ([#209](https://github.com/Estetika101/pacefinderapp/pull/209))
- Δ vs your PB in this car at this circuit (hero + card) ([#189](https://github.com/Estetika101/pacefinderapp/pull/189))
- Cosmetic reskin; topbar shows car name + class badge + PI; gauge values inside bars; gear/speed below tyres; RPM next to throttle ([#132](https://github.com/Estetika101/pacefinderapp/pull/132), [#104](https://github.com/Estetika101/pacefinderapp/pull/104), [#105](https://github.com/Estetika101/pacefinderapp/pull/105), [#102](https://github.com/Estetika101/pacefinderapp/pull/102))
- Position publishes even when grid-start packet was missed ([#106](https://github.com/Estetika101/pacefinderapp/pull/106))

**Cars**

- Bluemanos catalog seeded — 806 cars ([#93](https://github.com/Estetika101/pacefinderapp/pull/93))
- Car ordinal stored + surfaced (drivetrain, cylinders), per-ordinal nicknames ([#72](https://github.com/Estetika101/pacefinderapp/pull/72), [#73](https://github.com/Estetika101/pacefinderapp/pull/73))
- Car picker on session edit modal ([#89](https://github.com/Estetika101/pacefinderapp/pull/89))
- Car class derived from PI at render (game-aware FM2023) ([#162](https://github.com/Estetika101/pacefinderapp/pull/162))
- Car-context card scoped to the circuit, not all tracks ([#173](https://github.com/Estetika101/pacefinderapp/pull/173))

**Performance**

- `gzip` for JSON/text responses when the client accepts it ([#190](https://github.com/Estetika101/pacefinderapp/pull/190))
- Precomputed `/sessions/session/data` lap aggregates — p95 ~500–1450ms → DB-only ([#69](https://github.com/Estetika101/pacefinderapp/pull/69))
- `/sessions/lap-samples?outline=1` — per-row mini payload down ~99% ([#207](https://github.com/Estetika101/pacefinderapp/pull/207))
- gzipped `lap_samples` blobs + missing per-sample fields captured ([#87](https://github.com/Estetika101/pacefinderapp/pull/87))
- Server + client perf instrumentation ([#61](https://github.com/Estetika101/pacefinderapp/pull/61))
- Debug-mode perf overlay on every page ([#194](https://github.com/Estetika101/pacefinderapp/pull/194))
- `bench_perf.py` — back-end perf bench + Pi baseline tracking ([#188](https://github.com/Estetika101/pacefinderapp/pull/188))
- `/stream` idle-throttle + 60s auto-close ([#124](https://github.com/Estetika101/pacefinderapp/pull/124))
- Stop the migrate→cull flood on every boot ([#123](https://github.com/Estetika101/pacefinderapp/pull/123))

**Setup, packaging, testing**

- Service renamed `simtelemetry` → `pacefinder` with migration notes ([#53](https://github.com/Estetika101/pacefinderapp/pull/53))
- Setup page reskin + time-format preference (12/24h, end-to-end) ([#139](https://github.com/Estetika101/pacefinderapp/pull/139), [#140](https://github.com/Estetika101/pacefinderapp/pull/140))
- Install instructions audit ([#80](https://github.com/Estetika101/pacefinderapp/pull/80))
- Minimal CI workflow ([#90](https://github.com/Estetika101/pacefinderapp/pull/90))
- Monte-carlo session lifecycle harness; fast 40/50/100-lap regression test ([#121](https://github.com/Estetika101/pacefinderapp/pull/121), [#147](https://github.com/Estetika101/pacefinderapp/pull/147))
- CONTRIBUTING hardened with testing + deployment checks ([#150](https://github.com/Estetika101/pacefinderapp/pull/150))
- Marketing concerns moved to a dedicated repo ([#86](https://github.com/Estetika101/pacefinderapp/pull/86))

**Tooling**

- `/debug/raw` — live raw telemetry inspector ([#57](https://github.com/Estetika101/pacefinderapp/pull/57))
- Searchable autocomplete widget (applied to track field, car picker) ([#88](https://github.com/Estetika101/pacefinderapp/pull/88))
- Delete-session button in the edit modal ([#52](https://github.com/Estetika101/pacefinderapp/pull/52))
- Drop incomplete laps at session close + cleanup script for old data ([#51](https://github.com/Estetika101/pacefinderapp/pull/51))
- Edit modal — Type/Weather/Tyres on one row; always show chips with placeholders when unset ([#94](https://github.com/Estetika101/pacefinderapp/pull/94), [#96](https://github.com/Estetika101/pacefinderapp/pull/96))

**Fixes worth calling out**

- Silence misleading "rejected" warnings for in-menu Forza packets ([#66](https://github.com/Estetika101/pacefinderapp/pull/66))
- Forza `lap_number=0` is race lap 1, not an out-lap; render 1-indexed ([#67](https://github.com/Estetika101/pacefinderapp/pull/67), [#68](https://github.com/Estetika101/pacefinderapp/pull/68))
- Sector delta sign + theoretical sector pollution ([#101](https://github.com/Estetika101/pacefinderapp/pull/101))
- Quieter dev console — empty data returns `200 []` instead of `404 []` ([#92](https://github.com/Estetika101/pacefinderapp/pull/92))
- `/sessions/lap-samples` accepts `lap=0` ([#205](https://github.com/Estetika101/pacefinderapp/pull/205))

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
