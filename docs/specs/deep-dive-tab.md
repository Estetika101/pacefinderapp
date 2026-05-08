# Session Detail: "Deep Dive" tab

## Purpose
The session detail page today has two tabs: **Overview** (lap-times table, AI coaching button) and **Telemetry** (multi-channel charts vs distance/time). Both are valuable, but neither answers the question a hobbyist actually asks after parking the car: **"What should I do differently?"**

Telemetry charts are passive — they require the user to know what to look at. Lap-times tell you *how* slow you were, not *where* or *why*. We capture a rich per-sample stream (throttle/brake/steer, four-corner slip ratios + slip angles + combined slips, suspension travel, tyre temps, wheel-on-rumble, AI driving-line hint, AI brake-difference) — enough to point at concrete moments.

A new **Deep Dive** tab synthesises that stream into focused, actionable panels. Each panel answers one question and either highlights a moment to investigate or summarises a pattern.

## Behavior

### Tab placement
Add a third tab next to **Overview / Telemetry** on `/sessions/session?id=…`, labelled **Deep Dive**. URL param: `?tab=deepdive`. Inherits the same `_id` / `_sgame` / `_strack` query params used by the existing tabs. Loads from the same `/sessions/session/data` endpoint plus a new `/sessions/session/deepdive` endpoint that returns the panel payloads (computed server-side from `lap_samples` so the client doesn't ship 4 × 60 Hz × 90 s of JSON to render five summary numbers).

### Panels (v1)
Three panels, each rendered as a card with a one-line question header and a body. Cards stack vertically on narrow viewports, two-column grid above 1100 px.

#### 1. Lap Comparison — "Where did this lap lose time vs my best?"
Distance-aligned delta between a chosen lap and a reference lap.

- **Reference**: defaults to the session-best lap; user can pick any completed lap from a dropdown.
- **Compare**: defaults to the lap immediately following the reference; user can pick any.
- **Output**:
  - **Total delta** (signed seconds at the line).
  - **Top 3 lost segments**: the three 100 m windows where the comparison lap lost the most time, each shown as `+0.34s @ 1820 m` with a thumbnail strip showing the throttle/brake/steer trace for both laps in that window.
  - **Top 3 gained segments**: same, where the comparison lap was *faster*.
- Click a segment → opens the Telemetry tab pre-zoomed to that distance window with both laps overlaid.
- Reuse the existing `_interp_dist_to_t` timeline plumbing — same logic the live in-race delta uses, just applied between two completed laps instead of live-vs-best.

#### 2. Mistakes & Events — "What went wrong?"
Auto-detected per-lap incidents, sorted by severity. Each row: lap number, distance into lap, event label, one-line detail. Click → jump to that point in the telemetry tab.

**Detectors** (all heuristic, all tunable in `db/store.py` or a new `analysis/events.py`):
- **Spin / big slide** — `peak combined_slip on either rear corner > 1.5` for ≥ 0.3 s, OR rear slip ratio > 0.6 with throttle > 50% and yaw rate > 90°/s. Severity = peak slip × duration.
- **Off-track** — `wheel_on_rumble_strip_*` true for ≥ 0.5 s on the *outside* tyres, OR a velocity drop > 30% over < 0.5 s without proportional brake input.
- **Lockup** — brake > 70% and any wheel rotation speed dropped < 20% of the car's forward speed for ≥ 0.2 s.
- **Bad shift** — gear change accompanied by an RPM jump > 2000 in the wrong direction (e.g. upshift that *increased* RPM = downshift error, or downshift that landed in the redline).
- **Power-on oversteer event** — rear slip ratio > 0.5 with throttle > 70% (separate from spin since it doesn't always lose the car).

**Output**: max 10 events per session, sorted by severity. Empty state: "Clean session — no incidents flagged."

#### 3. Driving Style Summary — "How am I driving?"
Aggregate stats across all valid laps in the session, with per-lap variance to show consistency.

- **Trail-braking %** — fraction of samples where throttle > 5% and brake > 5% simultaneously.
- **Coasting %** — fraction where both < 5%.
- **Average shift RPM** — mean RPM at gear-up transitions; flag if > 95% of `engine_max_rpm` (early shifter / over-rev habit) or < 80% (short shifter).
- **Steering smoothness** — std-dev of `d(steer)/dt`; lower = smoother. Show as a 1–10 score with "smooth" / "snappy" anchors.
- **Brake aggression** — p95 of brake input. High = stab-and-release; low = progressive.
- **Lap-time consistency** — std-dev of valid lap times in seconds. Anchor: < 0.5 s = consistent, > 2.0 s = inconsistent.

Each metric shows the session number plus a small spark-grid of per-lap values so the user can see whether their driving improved or degraded over the session.

### Backend
New endpoint `/sessions/session/deepdive?id=<sid>`:
- Returns JSON: `{ lap_comparison: {...}, events: [...], style: {...} }`.
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
- A session with ≥ 2 completed laps in the DB renders all three panels under the **Deep Dive** tab.
- Lap Comparison's "total delta" matches the difference between the two laps' `lap_time_s` values to within 0.05 s (rounding).
- Switching the reference or comparison lap updates the panel without a page reload.
- Clicking a Top-Lost segment opens the Telemetry tab pre-zoomed to that distance range.
- Mistakes & Events flags at least one event for any session containing a known spin (manual sanity check using a session the user remembers crashing in).
- The deep-dive endpoint p95 ≤ 200 ms on a typical 4-lap session.
- Session detail page loads with no JS errors when `car_class` is unset (regression guard for #109).
- Empty / single-lap sessions show a graceful "Need at least 2 laps for Deep Dive" message instead of erroring.

## Open questions
- **Severity scoring for events.** Should we cap the displayed list at 10 (current proposal) or show a "show all" expander? On a clean lap there might be 0–2 events; on a chaotic AI race there might be 30. Cap-at-10 keeps the panel scannable but hides info on chaotic sessions. Lean: cap with a "+N more" link that expands.
- **Reference-lap default**. Best lap is the obvious choice, but for diagnostic purposes "median lap" might be more useful (a typical lap, not the outlier-fast one). Worth picking one and running it; can change later.
- **Steering smoothness score scale**. Std-dev of d(steer)/dt is the metric, but the 1–10 mapping is arbitrary until we see real data ranges. Ship with placeholder anchors and tune after a few sessions.
- **AI hints (`lane`, `ai_brk_diff`)**. Forza broadcasts the AI driving line and AI brake-input delta. These are gold for "ideal vs actual" comparison but only meaningful in AI races. Worth surfacing in v1 as a fourth panel? Probably not — most pacefinder users right now seem to be running real races where these are zero. Stretch goal once AI-race usage grows.
