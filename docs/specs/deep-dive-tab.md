# Session Detail: "Deep Dive" tab

## Purpose
The session detail page today has two tabs: **Overview** (lap-times table, AI coaching button) and **Telemetry** (multi-channel charts vs distance/time). Both are valuable, but neither answers the question a hobbyist actually asks after parking the car: **"What should I do differently?"**

Telemetry charts are passive — they require the user to know what to look at. Lap-times tell you *how* slow you were, not *where* or *why*. We capture a rich per-sample stream (throttle/brake/steer, four-corner slip ratios + slip angles + combined slips, suspension travel, tyre temps, wheel-on-rumble, AI driving-line hint, AI brake-difference) — enough to point at concrete moments.

A new **Deep Dive** tab synthesises that stream into focused, actionable panels. Each panel answers one question and either highlights a moment to investigate or summarises a pattern.

## Behavior

### Tab placement
Add a third tab next to **Overview / Telemetry** on `/sessions/session?id=…`, labelled **Deep Dive**. URL param: `?tab=deepdive`. Inherits the same `_id` / `_sgame` / `_strack` query params used by the existing tabs. Loads from the same `/sessions/session/data` endpoint plus a new `/sessions/session/deepdive` endpoint that returns the panel payloads (computed server-side from `lap_samples` so the client doesn't ship 4 × 60 Hz × 90 s of JSON to render five summary numbers).

### Panels (v1)
Three panels, each rendered as a card with a one-line question header and a body. Cards stack vertically on narrow viewports, two-column grid above 1100 px. **Facts** is the first card and the simplest delivery — if implementation runs long, ship just Facts as v0 and follow up with the other two.

#### 1. Facts — "What can I say about this session?"
A flat bulleted list of objective statements about the session. No subjective scores, no 1–10 ratings, no "smooth / snappy" labels. Each bullet is one sentence with a number and a unit. The user reads it like a postgame stat sheet and knows immediately whether anything stands out.

Two grouping modes, toggled by a small segmented control at the top of the card:
- **Session** (default) — facts aggregated across all valid laps.
- **Per-lap** — collapsed accordion, one block per lap, same fact format inside each.

**Fact families** (~15–25 bullets total per view):

*Pace*
- `Best lap: 1:11.512 (lap 2)`
- `Slowest valid lap: 1:17.110 (lap 1, +5.6s vs best)`
- `Lap-time spread: 5.6 s across 4 laps`
- `Sector splits: S1 0:40.116 · S2 0:52.494 · S3 0:44.841` *(only if sector splits land first)*

*Speed & shifts*
- `Max speed: 185.7 mph (lap 3 @ 1820 m)`
- `Average shift RPM: 6,450 (redline 7,000 — shifting at 92%)`
- `Highest gear used: 6th`
- `Time at full throttle: 62.3% of lap`

*Inputs*
- `Trail-braking: 8.4% of samples (throttle + brake both > 5%)`
- `Coasting: 11.2% of samples (both inputs < 5%)`
- `Peak brake pressure: 87% (lap 2 @ 1450 m)`
- `Steering reversals: 142 over the session`

*Grip & slip*
- `Peak rear slip ratio: 0.61 (lap 3 @ 920 m — power-on)`
- `Average rear slip: 0.14`
- `Wheel-on-rumble events: 3 (laps 1, 2, 4)`
- `Maximum lateral G: 2.1 g`

*Tyres & suspension*
- `Front tyre temps averaged 175°F, rears 180°F (5°F front-rear delta)`
- `Hot corner: rear-right at 198°F peak`
- `Front-left suspension peaked at 0.95 compression — possible kerb hit at lap 1, 850 m`
- `Tyre wear (FH5 only): FL 1.2% · FR 1.1% · RL 2.4% · RR 2.5%` *(omit on FM2023 sessions)*

*Race outcome (race-type sessions only)*
- `Started P13, finished P4 (gained 9 positions)`
- `Closest gap to front: lost 0.34 s on lap 3 segment 2 vs your best lap`

**Generation**
- All bullets generated server-side from the same `lap_samples` aggregates the rest of the tab uses.
- Bullets are skipped silently when their underlying data is null — e.g. tyre-wear bullet doesn't render on FM2023 sessions; race-outcome bullets don't render in Time Trial.
- Each bullet has an internal `kind` tag (e.g. `pace.best_lap`, `inputs.trail_braking`) so we can later A/B which ones the user finds useful and prune the noise.

**Empty state**: single-lap session shows `Need at least 2 valid laps for the full Facts list.` plus the still-computable single-lap subset (max speed, shift RPM, peak slip, etc.).

#### 2. Lap Comparison — "Where did this lap lose time vs my best?"
Distance-aligned delta between a chosen lap and a reference lap.

- **Reference**: defaults to the session-best lap; user can pick any completed lap from a dropdown.
- **Compare**: defaults to the lap immediately following the reference; user can pick any.
- **Output**:
  - **Total delta** (signed seconds at the line).
  - **Top 3 lost segments**: the three 100 m windows where the comparison lap lost the most time, each shown as `+0.34s @ 1820 m` with a thumbnail strip showing the throttle/brake/steer trace for both laps in that window.
  - **Top 3 gained segments**: same, where the comparison lap was *faster*.
- Click a segment → opens the Telemetry tab pre-zoomed to that distance window with both laps overlaid.
- Reuse the existing `_interp_dist_to_t` timeline plumbing — same logic the live in-race delta uses, just applied between two completed laps instead of live-vs-best.

#### 3. Mistakes & Events — "What went wrong?"
Auto-detected per-lap incidents, sorted by severity. Each row: lap number, distance into lap, event label, one-line detail. Click → jump to that point in the telemetry tab.

**Detectors** (all heuristic, all tunable in `db/store.py` or a new `analysis/events.py`):
- **Spin / big slide** — `peak combined_slip on either rear corner > 1.5` for ≥ 0.3 s, OR rear slip ratio > 0.6 with throttle > 50% and yaw rate > 90°/s. Severity = peak slip × duration.
- **Off-track** — `wheel_on_rumble_strip_*` true for ≥ 0.5 s on the *outside* tyres, OR a velocity drop > 30% over < 0.5 s without proportional brake input.
- **Lockup** — brake > 70% and any wheel rotation speed dropped < 20% of the car's forward speed for ≥ 0.2 s.
- **Bad shift** — gear change accompanied by an RPM jump > 2000 in the wrong direction (e.g. upshift that *increased* RPM = downshift error, or downshift that landed in the redline).
- **Power-on oversteer event** — rear slip ratio > 0.5 with throttle > 70% (separate from spin since it doesn't always lose the car).

**Output**: max 10 events per session, sorted by severity. Empty state: "Clean session — no incidents flagged."

#### Numbered out — there's no third panel beyond Comparison and Events
Driving Style Summary (1–10 scoring panel) is dropped in favour of the Facts list. Subjective anchors ("smooth / snappy") were always going to need calibration data we don't yet have, and the same numbers read better as bullets.

### Backend
New endpoint `/sessions/session/deepdive?id=<sid>`:
- Returns JSON: `{ facts: { session: [...], per_lap: [{lap_number, bullets: [...]}] }, lap_comparison: {...}, events: [...] }`.
- Reads `lap_samples` (gzipped per-sample data) for the session, decompresses, computes the three panels.
- p95 target ≤ 200 ms — these are summary statistics over a few thousand samples, no DB writes, no external calls.
- Cache-safe: same input → same output, so an `If-None-Match` ETag based on `session_id + ended_at` is trivial to add later.
- All computation in a new module `analysis/deepdive.py` so it's importable + unit-testable independently of the HTTP path.

### Frontend
- New file `static/js/sessions_deepdive.js` loaded only on the session detail page (alongside `sessions_session.js`).
- Renders three cards into `<div id="tab-deepdive">` (added next to existing `tab-overview` / `tab-telemetry`).
- Inputs: dropdown for lap-comparison reference + comparison; everything else is read-only summary.
- Click-through to telemetry tab uses URL params `?tab=telemetry&zoomStart=<m>&zoomEnd=<m>&overlayLap=<n>` — the telemetry tab needs to learn those params (small extra work).
- No new dependencies. Vanilla DOM, same dark-mono aesthetic as the rest of the app.

### Data we already have, no schema change
All inputs are in `lap_samples` (gzipped JSON blob per lap, written at session close). No new captures, no migration. The whole spec is "use what we already have."

## Out of scope (v1)
- **Sector splits**. Real sector boundaries would make the lap-comparison panel much sharper but require either a configured-per-track sector definition or auto-segmentation (curvature-based). Track as a follow-up.
- **Tyre & setup panel** (temps over the lap, wear, suspension asymmetry). Valuable but heat asymmetry is hard to interpret without baseline calibration ("what is normal for this car/track?"). Keep the captured data; build the panel once we have enough data to set anchors.
- **Cross-session comparison**. Compare today's session against last week's at the same track. Different feature, different page.
- **Setup recommendations**. "Reduce rear toe by 0.1°" type advice. Out of scope until we see whether users want it (Forza setup files aren't accessible from UDP).
- **AI Coaching tied to events**. Feeding the events list into the existing `/analyze` endpoint as input is appealing but coupling the two complicates the AI prompt; do it as a follow-up if events prove useful in isolation.
- **Time Trial / Practice sessions**. Lap Comparison still works for any session with ≥ 2 valid laps; Mistakes & Events still works; Driving Style Summary still works. No special-casing.

## Acceptance
- A session with ≥ 2 completed laps in the DB renders all three panels (Facts, Lap Comparison, Mistakes & Events) under the **Deep Dive** tab.
- The Facts panel renders for any session with ≥ 1 lap (single-lap shows the still-computable subset).
- Per-lap Facts mode shows one accordion block per completed lap.
- Lap Comparison's "total delta" matches the difference between the two laps' `lap_time_s` values to within 0.05 s (rounding).
- Switching the reference or comparison lap updates the panel without a page reload.
- Clicking a Top-Lost segment opens the Telemetry tab pre-zoomed to that distance range.
- Mistakes & Events flags at least one event for any session containing a known spin (manual sanity check using a session the user remembers crashing in).
- The deep-dive endpoint p95 ≤ 200 ms on a typical 4-lap session.
- Bullets render their underlying data verbatim — a user copy-pasting "Best lap: 1:11.512 (lap 2)" must match what the Overview tab says.
- Session detail page loads with no JS errors when `car_class` is unset (regression guard for #109).

## Open questions
- **Severity scoring for events.** Should we cap the displayed list at 10 (current proposal) or show a "show all" expander? On a clean lap there might be 0–2 events; on a chaotic AI race there might be 30. Cap-at-10 keeps the panel scannable but hides info on chaotic sessions. Lean: cap with a "+N more" link that expands.
- **Reference-lap default**. Best lap is the obvious choice, but for diagnostic purposes "median lap" might be more useful (a typical lap, not the outlier-fast one). Worth picking one and running it; can change later.
- **Facts pruning**. ~20 bullets is roughly a phone screen — but on Time Trial / Practice the race-outcome bullets disappear, on FM2023 the wear bullet disappears, etc. We could end up with as few as 8 bullets on a TT session. Acceptable to leave it variable, or add filler like "Total samples captured" / "Session duration"? Lean: leave it variable, less noise.
- **Per-lap accordion default state**. Open all by default (scannable) or closed (compact)? Lean: closed except the highlighted "best lap" — a small "Best" badge on that one entry.
- **AI hints (`lane`, `ai_brk_diff`)**. Forza broadcasts the AI driving line and AI brake-input delta. These could power a fact like `Average distance from racing line: 1.2 m` or `Brake-point error vs AI: +18 m late on average`. Stretch goal — interesting only in AI races.
