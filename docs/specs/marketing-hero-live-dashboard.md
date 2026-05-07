# Marketing hero — live dashboard visual

## Purpose
The marketing site's hero needs to convey "this thing actually works and looks good" inside the first 3 seconds. A static screenshot doesn't sell live telemetry — the value is *the data moving*. Show the live dashboard "raving" (gauges spinning, bars sweeping, lap timer ticking) as the central hero element so visitors immediately see what they'd get if they installed Pacefinder.

## Behavior

### Visual concept
- The hero contains a faux-dashboard widget that mimics the real Pacefinder live dashboard at `http://localhost:8000/` — the speedo / throttle / brake / RPM bars, lap timer, tyre temps tile.
- The widget is **animated** (loops on repeat) — speed climbs and falls, throttle/brake bars sweep, gear shifts, lap time ticks, position counter blinks.
- The animation should look like a real ~60-second hot lap, not a 5-second loop. Subtle is better than busy.
- The visual should feel embedded *in* the page (depth / shadow / inset border), not floating *on* it. Imply the dashboard is "running" inside a device/screen frame.

### Implementation options (pick during impl)
1. **Recorded MP4/WebM loop** — record an actual session at 1080p, lift the dashboard region, loop it. Simplest, smallest LCP risk if the file is reasonably-sized. Recommended.
2. **CSS/JS animated mockup** — simulate the dashboard with hand-coded animations driven by `requestAnimationFrame`. More work; lighter on bandwidth; less visually "real".
3. **Live iframe** — embed an actual running dashboard via an iframe pointed at a publicly-accessible Pacefinder demo instance. Cool, but requires hosting + adds a dependency for the marketing site. Defer.

Recommend Option 1: record once, ship a static asset, lazy-load below the fold if needed.

### Performance
- Hero asset must not regress LCP. Target: hero loads visible (poster frame) within 1s on a cable connection, animation kicks in after `loadeddata`.
- Use `<video autoplay muted loop playsinline preload="metadata" poster="...">` with a static poster frame so the hero has *something* to show even before the video downloads.
- Recorded loop ≤ 2 MB ideal, ≤ 5 MB max. WebM (VP9) tends to compress UI animation well; provide MP4 fallback for Safari.

### Copy alignment
The animated dashboard should reinforce the existing hero headline ("Records UDP telemetry from Forza Motorsport. Saves every session automatically..." or whatever the current site uses). If the headline emphasizes "live, automatic, every lap recorded", the animation should make those three words feel literal.

### Acceptance
- Hero shows a moving dashboard within 1s of page load on a typical broadband connection
- The animation reads as "telemetry from a real lap" — recognizable speedo, RPM, lap timer, gear; not just abstract bars
- Mobile (≤ 600 px wide): animation either scales down cleanly or is replaced with a static screenshot; no horizontal scroll
- LCP score on the hero unchanged or improved vs. the current marketing hero (per Lighthouse)
- The video is `muted` + `playsinline` so it doesn't trigger autoplay blocking on iOS Safari

## Scope
- Cross-repo work in the marketing site (`pacefinder` repo, separate from the product)
- Recording infrastructure: a one-shot capture session (or a short JS snippet inside the actual app to record while racing)
- Encode + optimize the asset
- Hero markup change in the marketing site's index page
- Add poster frame asset

## Out of scope
- A "click to interact" mode — defer
- Localized voiceover / sound — the hero is muted
- Live demo backend (Option 3 above)
- Adding the recorded loop to the in-app dashboard (it's marketing-only)

## Cross-repo work
- `pacefinder` (marketing): hero markup + asset hosting (this is where the work lands)
- `pacefinderapp` (product): may need a temporary "demo mode" / pre-recorded packet replay for clean recording — tracked separately if so

## Open questions
- Recording source — record an actual session live, or use the existing `replay.py` to drive a clean, repeatable hot lap into the dashboard for capture? Recommend the replay route — gives consistent footage, no shaky human input, easier to re-shoot.
- Mobile fallback: full static screenshot, or scaled-down video? Recommend static screenshot below ~600 px — videos on mobile cost data and battery for a marginal benefit.
- Does this hero replace the existing one entirely, or augment it? Recommend replace — having both creates competing focal points.
