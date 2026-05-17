# Information Architecture

## Purpose

Pacefinder is a review tool. Recording is passive — the Pi captures
telemetry whether or not anyone has the app open, and that path is now
solid. So the app has no "modes" to switch between: it is the analysis
surface, and being live is a *state*, not a *place*.

This spec fixes the model the UI drifted away from and is the reference
for any nav or page-structure change. Screen real-estate / on-page CTA
layout is designed in Figma against this frame, not invented per page.

## Behavior

**No mode toggle, no "Analysis" label.** Opening the app *is* the intent
to review. The top bar, identical on every page (one shared component):

`pacefinder.` (→ Home)  ·  live status pill  ·  Setup

- **Status pill** is the entire Live story. Idle: quiet —
  `IDLE · WAITING FOR TELEMETRY`. Active: rich and clickable →
  the live dashboard — e.g. `● RECORDING · LAP 3 · 0:49.1`. It is
  omnipresent and live-updating on every page (polls `/status`). The
  separate "Live dashboard" nav link is removed — the pill is the
  affordance.
- **Setup** (and the debug-gated Performance / Raw / Admin tools) is a
  utility cluster, visually separate from brand/pill. Not a "mode."

**Home is the hub.** Highlights: career strip (lifetime KPIs + form),
"pick up where you left off", and the permanent entry points
`All circuits →` and `All cars →`. These two links are the *only*
discoverability path for Circuits and Cars — they are contractually
always present and must work (today "All circuits →" is dead; see the
split-out fix). Sessions is the core content: the full, filterable list
(track, car, race-type) reached from Home.

**Circuit / Car / Session are a graph, not a tree.** Lateral links both
ways: Car detail → its circuits; Circuit detail → its sessions; Session
detail ↔ its car / circuit. No page is a dead end.

**Mistakes / Opportunities** is a modal, dug into from Telemetry — the
forensic deep-dive. (A concise summary on Session → Overview is a
separate, later decision; not in scope here.)

**Post-race modal is lossless, deferrable triage — not a transition.**
Race ends → modal offers confirm/tag in seconds. The user can skip the
entire modal and stay capture-ready (another session may start
immediately); lap data is already saved by `close()` regardless. Skipped
/ untagged sessions resurface on Home as a "needs review" affordance so
deferred triage is reclaimable, never lost. You never leave the
capture-ready state to review.

## Scope

- One shared top-bar component (brand · status pill · Setup), used on
  every page; remove the standalone "Live dashboard" link.
- Status pill: omnipresent, live, rich-when-active, click → dashboard.
- Home as the hub with always-present, working `All circuits →` /
  `All cars →` entries.
- Circuit / Car / Session cross-links (graph navigation).
- Post-race modal: skippable, lossless; "needs review" resurfacing on
  Home for deferred sessions.

## Out of scope

- Game-selector level above Home — future, only when a second game
  (ACC/F1) is unparked. Don't build it now.
- Mistakes/Opportunities summary on Session Overview — separate spec.
- AI Spotter placement — tabled.
- Post-race modal loading/empty state — its own shippable issue.
- Setup split (global vs game-specific) — premature at one game.

## Cross-repo work

- pacefinderapp: all of the above.
- pacefindermarketing: none.

## Open questions

- "Needs review" affordance: a Home strip, a per-row badge, or both?
- Does the status pill, when active, replace the breadcrumb on the live
  dashboard or sit alongside it?
