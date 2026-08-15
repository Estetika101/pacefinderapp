# Anonymous Usage Analytics

## Purpose
Understand real-world adoption and health of Pacefinder — how many people are actively racing with it, whether the telemetry/analysis features get used, and where it's breaking — without collecting anything about what anyone actually did on track. Opt-out, default opt-in.

## Behavior

**Consent.** A new Setup page toggle, "Share anonymous usage data," defaults to **on**. Turning it off stops all outbound analytics traffic immediately — no queued/delayed send, no exception. The toggle sits in its own small section (not buried in Display), with a one-line explanation of what is and isn't sent, plus a link to the exact event/field list (this spec, or a future user-facing summary of it).

**Identifier.** A random UUID (`analytics_id`), generated once on first run and stored in `simtelemetry.config.json` alongside the rest of config — not derived from hostname, MAC address, or any other hardware/account identifier. It exists only so the backend can distinguish "1 install racing 50 times" from "50 installs racing once" and compute rough retention (do installs come back). It is never linkable to a person, an IP is not stored server-side beyond whatever Vercel's edge network logs transiently for its own operational purposes (same posture already disclosed for the marketing site's Umami usage on `/privacy`).

**Transport.** Events are POSTed as they happen (fire-and-forget, never blocking the request/action that triggered them) to a new endpoint hosted in the `pacefindermarketing` repo (already deployed on Vercel, already the home for `/api/feedback` and the retired `/api/mac-beta`). A failed send is dropped, not retried or queued — analytics must never be a reason a race fails to save or the dashboard hangs.

**Backend.** New Postgres database (Neon — free tier covers this volume comfortably, pairs cleanly with Vercel/Next.js, avoids the sunsetted Vercel Postgres/KV). One `events` table, one API route (`POST /api/analytics/event`), no auth (it's a public, unauthenticated collector by necessity — the sender is a locally-run app with no way to hold a secret). Rate-limited per `analytics_id` + IP the same way the feedback/contact forms already are (`src/lib/spam-guard.ts`, landed today) to bound abuse.

## Events tracked

A short, explicit allow-list — never a generic pass-through event name. Every event carries: `analytics_id`, `app_version`, `platform` (`darwin`/`linux`/`windows`), `deployment` (`testflight`/`appimage`/`docker`/`systemd`/`source`/`dev`), `event`, and event-specific fields listed below. Nothing else.

- **`app_launch`** — fired once per process start (after the analytics toggle is confirmed on). Establishes the denominator the other rates are measured against.
- **`session_saved`** — fired when a race session finishes saving. Fields: `game` (`forza_motorsport`/`f1`/`acc`), `lap_count`, `duration_s`. **Not** track, car, lap times, or any field from the session that describes performance.
- **`telemetry_viewed`** — fired when the Full Telemetry page loads for a session. Signals whether the deeper analysis surface gets used at all, separate from just glancing at Overview.
- **`spotter_used`** — fired when the Claude-powered post-race analysis is requested. Adoption signal for that specific feature.
- **`error`** — fired on a caught, unexpected exception in the listener (startup failures, session-save failures, DB errors). Fields: `error_type` (the exception class name, e.g. `OSError`), `context` (a short fixed label for where it happened, e.g. `session_close`, `track_reference_update` — from a fixed set defined at each call site, never an f-string built from the exception itself). The exception message and traceback are **not** sent — they can contain local file paths (`/Users/petervanaller/...`), which is enough to deanonymize an install. `error_type` + `context` is enough to tell us something is breaking and roughly where, without shipping anyone's filesystem layout.
- **`heartbeat`** — fired every `HEARTBEAT_INTERVAL_S` (10 minutes) for as long as the process is alive, via an asyncio background task (`analytics.heartbeat_loop()`, alongside `session_watchdog()`). Every other event is one-shot, so without this there's no way to tell "launched once and still running" from "launched once, long gone" — the app can run unattended for days on a Pi. No extra fields. Powers the dashboard's "currently online" / "active in the last 24h" figures: an install counts as online if it has *any* event (heartbeat or otherwise) within 2x the interval, tolerating one missed beat.
- **`page_viewed`** — fired on every full-page navigation. Field: `page`, itself an explicit allow-list (`_ALLOWED_PAGES` in analytics.py) — `home`, `sessions`, `session_detail`, `circuits`, `circuit_detail`, `cars`, `dashboard` (live mode), `setup`, `telemetry` (fires alongside the existing `telemetry_viewed`, which stays as its own feature-adoption signal — this is the general navigation-coverage signal). Debug/dev-only screens (`/debug/raw`, `/f1`, `/admin`) are deliberately excluded — not real user-facing IA.

## Scope
- Setup page toggle (default on), config field `analytics_enabled`.
- `analytics_id` generation + persistence in config.
- A small `analytics.py` module in the listener: fire-and-forget POST, silent no-op on failure, silent no-op when disabled.
- Call sites for the events above, plus `analytics.heartbeat_loop()` scheduled from listener.py's main().
- New Postgres DB (Neon) + `POST /api/analytics/event` route in `pacefindermarketing`, behind the same spam-guard rate limiting already used for `/api/feedback`.
- `/privacy` page on the marketing site updated to disclose this (mirroring the existing Umami disclosure pattern).

## Out of scope
- Track names, car names/ordinals, lap times, sector times, or any telemetry sample data.
- IP-address persistence beyond Vercel's own transient edge logs.
- Retrying/queuing failed sends.
- Per-event opt-out granularity — it's one toggle, all events or none.

## Cross-repo work
- `pacefinderapp`: `analytics.py` (including `heartbeat_loop()`), Setup page toggle, `config.py` fields, call sites at each event location, this spec.
- `pacefinder` (marketing): Neon Postgres DB, `POST /api/analytics/event` route, spam-guard rate limiting on it, `/privacy` page update, and a password-gated dashboard at `stats.pacefinder.app` (`src/app/stats/`, `src/proxy.ts`) showing distinct/online/24h-active installs, launches over time, sessions by game, feature adoption, and recent errors — live-updating via 15s client-side polling.

## Open questions
- Exact retention window for raw events in Postgres (30/90/365 days? no expiry?) — deferred until there's a reason to care about storage cost.
- Whether `context` labels need a formal enum in code or just a house convention (lean enum — cheap, and prevents an accidental f-string leak at a future call site).
