# Usage Analytics v2 — activation, liveness, and honest denominators

## Purpose

v1 (`usage-analytics.md`, shipped) answers *what happened*: launches,
sessions, page views, a thin error trickle. It cannot answer the question
that actually decides whether Pacefinder works for anyone — **did telemetry
ever reach this install?** Data Out pointed at the wrong IP, a closed
firewall, or the wrong machine is the single most common failure in the
product, and today an install in that state emits `app_launch` and
heartbeats forever, indistinguishable from a healthy install that simply
hasn't raced this week.

v2 turns the event stream into an activation funnel, moves liveness off the
events table before heartbeats swallow it, and wires the error channel v1
promised but never connected. Same privacy posture as v1 — allow-lists,
no telemetry content, no tracebacks, no IP persistence. Nothing here relaxes
what is collected about what anyone did on track.

## Behavior

### The funnel this exists to measure

```
install (analytics_id first seen)
  → launched            app_launch
  → captured            first_packet     ← new; the missing step
  → raced               session_saved
  → returned            session_saved in a later week
```

Four of five steps already exist. `first_packet` is the one that makes the
rest legible: without it, every zero is ambiguous.

### New and changed events

**`first_packet`** — fires once per install, ever, the first time any parser
decodes a valid packet. Field: `game`. Call site is
`session/protocol.py`'s `TelemetryProtocol.datagram_received`, immediately
after the `if not parsed` guard. Persisted via a new config key
`analytics_first_packet_sent` (bool) so it survives restarts and cannot
re-fire. This is the activation marker; it is the only new one-shot event.

**Split the failure, because the app already knows.** `datagram_received`
maintains `state["udp_received"]`, `state["udp_rejected"]`, and
`state["last_rejected_size"]` in memory today. Those distinguish two
failures that look identical from the outside and have completely
different answers:

- **nothing arriving** — wrong Data Out IP, closed firewall, wrong port.
- **arriving and rejected** — right machine, wrong packet format (Car Dash
  not selected); `last_rejected_size` names it exactly.

The heartbeat carries both as booleans (`udp_ok`, `udp_rejected`), read
straight off that existing state. No new bookkeeping, and the funnel's
capture step stops being a single "didn't work" bucket. This is the
difference between knowing the setup rate is bad and knowing which sentence
of the install docs to rewrite.

**`session_saved`** — gains `sessions_total` and `laps_total`, and
`duration_min` replaces `duration_s`, rounded to whole minutes. The two
counts already exist as `total_sessions` / `total_laps` in
`db/store.py`'s `_db_career_kpis()` — one existing query at close, no new
aggregate.

Cumulative counters are the fix for a lossy transport. Sends are
fire-and-forget with no retry by design (correctly — analytics must never
block a race from saving), which means every v1 count is silently a lower
bound with no way to know by how much. A cumulative counter is self-healing:
nine dropped sends out of ten and the tenth still carries the true total.
This is strictly better than a retry queue and costs one query at close.

Whole minutes rather than `round(duration_s, 1)`: 0.1s precision on duration
alongside `lap_count`, `game`, and a timestamp is a usable fingerprint at low
install counts, and no question the dashboard asks needs better than minutes.

**`app_launch`** — gains `launches_total`, same reasoning.

**`feature_used`** — new, with an allow-listed `feature` field:
`deepdive`, `lap_compare`, `mistakes`, `reference_set`, `session_confirm`,
`session_skip`, `session_edit`, `session_delete`, `car_nickname`.

v1 has exactly two feature signals (`telemetry_viewed`, `spotter_used`) for
a dozen features, and the deep-analysis surfaces — the actual product value
— are all XHR endpoints (`/sessions/session/deepdive`, `/sessions/references`,
`/sessions/lap-samples`) that fire nothing. The open question v1 cannot
answer is whether anyone uses the analysis at all or whether this is a
live-dashboard toy.

`session_confirm` vs `session_skip` is worth its own pair: `ia.md` treats
deferral as lossless and reclaimable, and this is the only way to find out
whether deferred sessions are actually reclaimed or just abandoned.

**`error`** — gains `fatal` (bool). A recovered JSON-write failure and a
listener that cannot bind are currently the same shape.

**`update_applied`** — new. Fields: `from_version`, `to_version`, `ok`
(bool). Five distribution channels with entirely different update mechanics,
and the AppImage self-updater is the most fragile path in the product. Today
a broken updater is only discoverable via bug report.

**`telemetry_viewed`** — removed. It is `page_viewed:telemetry` fired from
the adjacent line in `net/router.py`; v1's spec concedes the duplication.
Two events for one action are guaranteed to diverge. The telemetry page
keeps its `page_viewed`.

**`heartbeat`** — stops being an event row (see below), and gains state:
`capture_ok` (has this install ever seen a packet), `session_active`
(recording right now), `uptime_s`. Interval moves from 10 min to 20 min.

### Heartbeat becomes an upsert, not an append

At 10-minute intervals a single install writes 144 rows/day to assert one
boolean. A hundred always-on installs is ~5M rows/year — on a free-tier
Neon instance where every dashboard query is already a full table scan.
Heartbeat volume becomes the database, and it answers the least interesting
question in the system.

`heartbeat` POSTs to the same endpoint, but the collector routes it to an
**upsert on a new `analytics_installs` table** (one row per `analytics_id`)
instead of an insert into `analytics_events`. `analytics_events` keeps only
things that *happened*; `analytics_installs` holds current state.

Every "right now" tile then reads a single indexed row-per-install table,
and every "over time" tile reads the events table. That split is what keeps
the free tier viable and the dashboard fast.

The interval change to 20 min (online window 40 min, still 2x) halves the
remaining volume and costs nothing analytically — no question asked of this
data has 10-minute resolution.

### Wire the error channel

v1 promises "startup failures, session-save failures, DB errors." Three call
sites exist, all inside `session/manager.py`'s `_close_finalize_async`.
Everything else is silent:

- `net/router.py:2454` — the top-level request handler is a bare
  `except Exception: pass`. **Every 500 in the entire HTTP layer is
  swallowed.** Largest source of invisible breakage in the app.
- `listener.py:473` — UDP bind failure (port conflict) logs only.
- `listener.py:554–565` — dashboard port bind failure logs only.
- `/analyze` — the Claude call's `except Exception` logs
  `f"Claude API error: {exc}"` and returns 500 to the client, but tracks
  nothing. Bad key, rate limit, and no-credit are the three most likely
  Spotter failures and all are invisible; it is also the feature most
  likely to fail in a way users attribute to Pacefinder.
- `config.py`'s `resolve_storage_path()` returns `_LOCAL_FALLBACK` from a
  bare `except OSError` — it does not even log. An install silently writing
  to the per-user dir instead of the configured path is undetectable both
  in the field and in the logs.

New `context` values, added to a module-level frozenset in `analytics.py`
(v1's open question resolved in favour of the enum — it prevents an
f-string leak at a future call site, which is the whole reason `context` is
constrained):

`http_request`, `udp_bind`, `http_bind`, `spotter_call`, `storage_fallback`,
`db_migration`, plus the three existing `lap_samples_write`,
`session_json_write`, `track_reference_update`.

`http_request` carries the matched **route pattern** (`/sessions/session`),
never `path` as received and never the query string — same allow-list
discipline as `page`, for the same reason.

### Envelope

Every event gains:

- **`schema_v`** (int, starts at `2`) — one integer now instead of guessing
  which rows are old the first time a field changes shape.
- **`ts`** — client UTC timestamp. The collector keeps its own
  `created_at` alongside it, so clock skew becomes *detectable* rather than
  silently corrupting the timeline; an install that was offline and sent
  late currently lands at the wrong time with no way to notice.
- **`arch`** — `platform.machine()`. The install matrix splits x86_64 from
  aarch64 and states "Pi 4/5 only, Pi 3 is 32-bit"; not knowing which
  architecture is in the field is a real gap for a Pi-targeted product.
- **`py_version`** — major.minor only. 3.9 is the supported floor and the
  cost of holding it is currently invisible.

**`platform`** is corrected: `sys.platform` emits `win32`, not `windows` as
v1's spec claims. Normalise in `analytics.py` to `darwin` / `linux` /
`windows` so a dashboard `GROUP BY` doesn't split on it.

### Collector fixes

- **Hoist the DDL.** `CREATE TABLE IF NOT EXISTS` currently runs on *every
  insert* — on serverless Postgres that is a second HTTP round trip per
  event, doubling collector cost to assert something already true. Move it
  to checked-in SQL (`db/migrations/*.sql`) applied once against Neon at
  deploy; the repo has no JS migration tooling and does not need any for
  two tables.
- **Add indexes.** The table has none. Every dashboard query is a full scan:
  `(created_at DESC)`, `(event, created_at DESC)`,
  `(analytics_id, created_at DESC)`.
- **Stop stringifying numbers.** `fields[key] = String(v)` stores
  `lap_count` and `duration_s` as text in JSONB, so every numeric
  aggregation needs a cast and any sort is lexical. Preserve numbers; keep
  the type check, drop the coercion.
- **Rate limit on `analytics_id` as well as IP.** v1's spec says
  "per `analytics_id` + IP"; the route limits IP only, so installs behind
  one NAT share a bucket and no single client can be isolated. Note the
  existing in-memory `Map` in `spam-guard.ts` is per serverless instance and
  therefore approximate — acceptable as an abuse backstop, not a guarantee,
  and the file already says so.
- **Count what it drops.** The endpoint returns `200` when the DB write
  fails and when `DATABASE_URL` is unset, and the client drops failures
  silently. There is currently no observability of collector health
  anywhere in the system. A `analytics_collector_health` row (accepted /
  persisted / rejected counters, bumped per request) makes the dashboard's
  delivery tile possible.
- **Derive `ONLINE_WINDOW_MINUTES` from a shared constant** or, failing
  that, have the client send its own `heartbeat_interval_s` on each beat.
  It is currently hardcoded in `stats-queries.ts` with a comment asking a
  human to keep two repos in sync by hand.

### Dashboard

Reordered. v1 leads with distinct / online / 24h-active installs — a vanity
row, and "online" is actively misleading for an app whose intended
deployment is an always-on Pi. **Online ≠ active ≠ racing.** Racing is the
only one of the three that means anything.

1. **Activation funnel** — installs → launched → captured → raced →
   returned. The drop between *launched* and *captured* is the
   setup-failure rate, and it breaks down three ways from the heartbeat
   flags: no packets at all (network/IP/port), packets rejected (wrong
   Data Out format), or captured fine and simply not racing yet. The
   headline tile, and the only one that maps directly onto a support answer.
2. **Weekly active racers** (≥1 `session_saved` in 7 days) and sessions/week.
3. **Retention cohorts**, defined rather than left to whatever is easiest to
   compute: of installs whose **first `session_saved`** fell in week N, the
   share that saved a session in N+1 and in N+4, cohorted by install week.
   Session-based, never launch-based — a Pi retains "launch" trivially by
   never being turned off, which makes launch retention a measure of
   uptime, not of the product.
4. **Feature adoption** as a share of *racing* installs, not of all events.
   (`featureAdoption` currently mixes `app_launch` into the feature list —
   it is the denominator, not a feature.)
5. **Errors** — rate per 100 launches, top contexts, split by deployment
   channel. Split matters: an AppImage-only failure and a universal one
   need different responses.
6. **Version / deployment / arch distribution.**
7. **Delivery health** — collector accepted-vs-persisted, and the share of
   installs whose last heartbeat is stale. The honesty tile; it says how
   much to trust the six above.

`launchesByDay` also switches to distinct installs per day, or carries both
— a crash-looping systemd unit currently inflates the chart without limit.

### Consent

The toggle stays opt-out, default on, and stays in Setup. It is **also**
surfaced once in the first-run wizard (`first-run-wizard.md`): one line, on
by default, "change any time in Settings." A consent control the user has
to go looking for is disclosed rather than given, and the wizard already
exists as the place a new install passes through exactly once.

## Scope

**`pacefinderapp`**

- `analytics.py`: `schema_v`/`ts`/`arch`/`py_version` in the envelope,
  `platform` normalisation, `_ALLOWED_EVENTS` updated (`first_packet`,
  `feature_used`, `update_applied` in; `telemetry_viewed` out),
  `_ALLOWED_FEATURES` and `_ALLOWED_ERROR_CONTEXTS` frozensets,
  `HEARTBEAT_INTERVAL_S` 600 → 1200, heartbeat state fields.
- `config.py`: `analytics_first_packet_sent` (bool, default False).
- `first_packet` call site in `session/protocol.py`'s
  `datagram_received`; `capture_ok` / `udp_ok` / `udp_rejected` on the
  heartbeat, read from the existing `state["udp_*"]` counters.
- Cumulative counters: `sessions_total` / `laps_total` at session close,
  `launches_total` at launch.
- `feature_used` call sites at the nine allow-listed features.
- `error` call sites at the six unwired locations above, plus `fatal`.
- `update_applied` in the `/update/apply` handler.
- Remove the `telemetry_viewed` call site (`net/router.py:1066`).
- First-run wizard consent line.
- This spec.

**`pacefinder` (marketing)**

- `analytics_installs` table + upsert path for `heartbeat`.
- Hoisted DDL as a migration; indexes on `analytics_events`.
- Allow-lists updated to match (events, features, error contexts, envelope
  fields); numbers no longer stringified.
- Rate limit keyed on `analytics_id` + IP.
- Collector health counters.
- `stats-queries.ts`: funnel, weekly active racers, retention cohorts,
  adoption over racing installs, error rate per 100 launches, delivery
  health; `launchesByDay` to distinct installs.
- `StatsView.tsx` reordered to match.
- `/privacy` updated for the new fields.

## Out of scope

- Any change to what is collected about on-track activity. Track names, car
  names/ordinals, lap times, sector times, and telemetry samples remain out,
  as does the exception message and traceback on `error`.
- Retry or queueing of failed sends. Cumulative counters replace the need;
  the fire-and-forget rule holds.
- IP persistence.
- Per-event opt-out granularity — still one toggle, all or nothing.
- Backfill of `analytics_events` rows written under v1. They keep
  `schema_v` absent, which is how the dashboard tells them apart; funnel and
  cohort tiles simply start from the v2 cutover.
- Replacing `spam-guard.ts`'s in-memory limiter with anything durable.

## Cross-repo work

- `pacefinderapp`: client instrumentation, config key, consent line — the
  dominant work, so the spec lives here.
- `pacefinder` (marketing): collector schema and allow-lists, migration,
  indexes, dashboard queries and layout, `/privacy`. Slim issue there
  referencing this spec, per `docs/specs/README.md`.

## Open questions

- **Ship order.** Collector allow-lists must accept the new events before
  the client sends them, or v2 events 400 at the boundary during the window
  between deploys. Marketing first, then the app release — worth stating in
  the issue so it isn't rediscovered.
- **`first_packet` on pre-v2 installs.** Existing installs have already
  captured but have no `analytics_first_packet_sent` key, so they will all
  fire `first_packet` once on upgrade. Harmless for the ongoing funnel, but
  it puts a spike at the cutover. Accept and annotate, or seed the flag True
  when the install has any prior `session_saved` in local SQLite? (Leaning
  seed — it makes the first cohort honest.)
- **Retention window.** W1/W4 assumes a weekly racing cadence. Reasonable
  for a sim-racing hobby, unverified against actual data. Revisit once there
  are enough cohorts to see the real shape.
- **Events retention.** Still deferred from v1. The `analytics_installs`
  split makes it much less urgent — the events table stops growing at
  heartbeat rate — but a 365-day expiry on `analytics_events` is the obvious
  default once anything needs deciding.
- **`session_active` on the heartbeat** makes "rigs recording right now" a
  real number, which is the most interesting live figure the system could
  show. Worth a tile of its own, or is it just a nicer version of "online"?
