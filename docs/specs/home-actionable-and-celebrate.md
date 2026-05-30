# Home — celebrate the PB, then point at the next gain

## Purpose

Home currently reports "are you getting better?" in **four unrelated
currencies** at once, with no framing, so the screen contradicts itself:
a driver can set a genuine PB and the same view tells them they're
"slipping" and "declining."

The four currencies, all of which happen to mention the same circuit:

| Surface | Actually measures | Reads as |
|---|---|---|
| Last session "= car PB here" | single best lap, ever, this car | a PB |
| Where you're slipping | recent *average* pace vs earlier average | slower |
| Your biggest leak | best sector vs theoretical best | time left |
| ▲ Improving (career strip) | race *finish positions* over N races | improving |

None of these conflict — a one-lap PB sits fine alongside drifting
average pace, unrealized sector time, and improving race results — but
nothing on screen says so. This spec gives Home an explicit emotional
spine and makes its numbers actionable.

Builds on `home-stats.md` (the two-tier stats block) and reuses the
existing Mistakes & Opportunities modal (`mistakes-modal.md`,
`net/pages/events.py`), which is **already wired** into telemetry via the
generic `.mo-ovl` iframe overlay — not net-new.

## The spine

> **Celebrate what just happened → then point at what to do next.**

Top of page celebrates (PB hero). Middle reframes leaks as opportunity
("Ways to get sharper", wins paired with leaks). Bottom (career strip +
results) becomes navigable evidence instead of dead labels.

## Behavior

### 1. Last session — grade and celebrate the PB

The data already distinguishes PB types; the hero should say which and
react visually only when it's actually a record.

- **Tiered badge** instead of a flat gray "= car PB here":
  all-time PB > track PB > car-PB-here. A car PB at a circuit is a
  smaller deal than an all-time best; the badge should grade it.
- **Celebratory treatment when PB** — accent the time (green/gold),
  subtle glow/ribbon on `.hero-last`, optional one-shot load animation.
  When it is *not* a PB the hero stays neutral, so the celebration
  carries meaning.
- **Mood-driven primary CTA**: on a PB, lead with "Relive this lap"
  (telemetry); when not, lead with "See where you lost time" (events
  modal). Keep both buttons; just reorder by mood.

### 2. "Ways to get sharper" — positive reframe, wins paired with leaks

Rename the **WHERE YOU'RE SLIPPING** / **YOUR BIGGEST LEAK** block to one
positive section: **"Ways to get sharper."** Cards stay; framing flips
from accusation to opportunity. This is also where the side-by-side
layout lives (slipping + leak in a 2-column row rather than stacked).

**Pair wins with leaks (confirmed).** The regression-watchlist logic is
symmetric: invert the comparison (recent average *faster* than earlier)
and genuine improvements fall out for free. Show "Sharpening up" cards
(green) beside the leak cards (amber/red). The section then answers both
"what am I doing right" and "what's the opportunity," and ties directly
to the bottom "Improving" trend instead of contradicting it.

- Slipping cards remain **real, max 3** — sourced from
  `/home/regression-watchlist`, never padded to fill slots. Wins are the
  same query inverted.
- Section header reframed; per-card copy turns "+3.02s vs your earlier
  pace" into an opportunity, not a verdict.

### 3. Career strip counts — clickable

Straight anchors, no new pages:

| Element | Links to |
|---|---|
| N Sessions | `/sessions` |
| N Laps | `/sessions` (no laps-only view; honest target) |
| N Circuits | `/circuits` |
| N Cars | `/cars` |

### 4. Results tier (avg finish / pos gained / podium) — clickable evidence

Each results stat deep-links to the **races that prove it**, turning a
number into an inspectable list:

- **Avg finish** → races sorted by finish position.
- **Pos gained** → races sorted by positions gained — "your best
  comebacks" (the motivating one).
- **Podium rate** → races filtered to P1–P3 — the trophy cabinet.

Mechanically all `/sessions?type=race` plus a sort/filter param. The
sessions list already supports type filtering; gained/finish **sort
params would be new** (small).

## Brainstorm — not yet decided

These two were explicitly left open; capturing options, no commitment.

### A. Where a "slipping" card should land

- **Mistakes modal, sector-filtered** — open the existing events modal
  for that circuit's PB session (`worst-sector` returns
  `pb_session_id`/lap; watchlist returns last session), pre-filtered to
  the leaking sector. Most actionable: "tap to see the corners costing
  the 3s." Reuses `events.py` + a filter param.
- **Per-circuit detail** — `/sessions/track?name=` — broader context,
  less surgical.
- Decide by mocking both.

### B. A home for "Improving" / career form

The ▲ Improving sparkline (race finish form) and the ▲6 ▼3 —12 tally
(per-circuit lap-time trend) are the only surfaces with **no real
destination** today. Options:

- **Deep-link (cheap):** sparkline → `/sessions?type=race`; the tally →
  `/circuits` (ideally each arrow filters improving/regressing/flat).
- **Dedicated `/career` (Form & Trends) page:** race-form chart,
  per-circuit progression, PB/celebration history. The data already
  exists in `/sessions/career`; this is the only genuinely net-new page
  and the definitive home for "am I actually getting better?"
- Lean order TBD — deep-link first is viable, `/career` is the richer
  answer.

### C. Per-card coaching hint (later)

Tie leak cards into the AI track-tip endpoint (`/sessions/track/tip`) for
a human sentence ("S2 — braking ~15m early into Les Combes"). Quality-
dependent; nice-to-have.

## Scope

- Home hero: PB tiering + celebratory states + mood-driven CTA order.
- "Ways to get sharper" section: rename, 2-col side-by-side, wins+leaks
  (inverted watchlist query for wins).
- Clickable career counts (anchors) + results deep-links (needs
  finish/gained sort params on the sessions list).
- Reuse existing events modal for slip card click (target per Brainstorm
  A).

## Out of scope / deferred

- `/career` page — Brainstorm B, not committed.
- Slip-card landing target — Brainstorm A, not committed.
- AI coaching hints on cards — Brainstorm C.
- Pixel-level visual design — Figma; this spec fixes behavior and
  framing, not exact styling.

## Cross-repo work

- pacefinderapp: all of the above.
- pacefindermarketing: none.

## Open questions

- Tiered PB: is "track PB" (best ever at this circuit, any car) a
  meaningful third tier, or just all-time vs car-PB-here?
- Wins cards: show up to 3 like leaks, or cap at 1 to keep the section
  from ballooning?
- Results sort params: extend `/sessions/data` with sort, or compute the
  ordered lists server-side for the deep-link targets?
