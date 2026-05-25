# Contributing to Pacefinder

Pacefinder records UDP telemetry from Forza Motorsport, archives every session, and serves a live dashboard. Active focus is **Forza only** — ACC and F1 are parked (parser code is in tree but not bound at startup).

## Workflow

1. **Specs first.** Non-trivial features get a markdown file in [`docs/specs/`](./docs/specs/) before any code lands. Spec describes purpose, behavior, scope, out-of-scope, and open questions. Template at [`docs/specs/README.md`](./docs/specs/README.md).
2. **Issue per spec.** Each spec gets a matching GitHub issue with a 3-line body pointing back to the spec file. Use the templates in [`.github/ISSUE_TEMPLATE/`](./.github/ISSUE_TEMPLATE/).
3. **Branch + PR.** Implementation goes on a `feature/`, `fix/`, `cleanup/`, or `docs/` branch. PR closes the matching issue (`Closes #N`).
4. **One PR per concern.** If you find an unrelated bug while working, open a separate PR or issue rather than bundling.
5. **Green before merge.** The full pipeline suite passes locally before you merge — see [Testing](#testing). Squash-merging over a red suite is not allowed, including for self-merged PRs.

For tiny changes (typo fixes, one-line tweaks) the spec step can be skipped — just open the PR directly.

## Local development

Requires Python 3.9+, no other runtime dependencies for the listener itself.

```bash
git clone https://github.com/Estetika101/pacefinderapp
cd pacefinderapp
python3 listener.py
```

Open <http://localhost:8000>. Point your game's UDP Data Out at this machine on port 5300 (Forza Motorsport / Horizon — same port, packet format auto-detected).

To use the AI Spotter (post-race analysis), set your Anthropic API key in the Setup page or in `simtelemetry.config.json`. Optional — listener runs fine without it.

## Testing

The full pipeline suite runs in ~0.2s, needs no server, and is the merge gate:

```bash
python3 test_listener.py        # ~80 checks — parse → ingest → session lifecycle
```

It drives the real ingest path directly, including multi-lap (40/50/100) race
lap-counting and the Forza `is_race_on=0` race-end packet. A red check blocks the
merge. Fix the cause — never skip, comment out, or merge around a failing check.

Optional network smoke (needs a running listener):

```bash
python3 test_listener.py --smoke            # local UDP + /status poll
python3 test_listener.py --live --host <ip> # against a remote Pi
```

Syntax-gate touched files the way [CI](./.github/workflows/ci.yml) does:

```bash
python3 -m py_compile <changed .py files>
node --check static/js/<changed file>.js
```

New behavior ships with a test. A bug fix ships with a **regression test that
fails before the fix and passes after** — prove it by stashing the fix and
re-running the suite. Synthetic packets must model real game behavior (e.g.
Forza ends a race with `is_race_on=0`); a test that can't fail is false
confidence.

> **CI gap:** `.github/workflows/ci.yml` currently runs only an import smoke and
> JS syntax check — it does **not** run `test_listener.py`. Until that lands,
> the local suite is the only thing guarding the lap-counting regressions.
> Running it before every merge is mandatory, not optional.

### Performance bench

Hot back-end paths are tracked with a real bench, not vibes:

```bash
python3 bench_perf.py            # run + print table
python3 bench_perf.py --baseline # save current numbers as baseline
python3 bench_perf.py --check    # compare vs baseline; nonzero on regression
```

Seeds a deterministic synthetic DB in a temp dir (no Pi required) and times
the audit-flagged hot paths: `_db_tracks_index`, `_db_sessions_list(2000)`,
career KPIs, recent, needs-review, new-since. Reports median + p95 + payload
bytes per op. The baseline lives at [`bench_baseline.json`](./bench_baseline.json).

**Numbers are not Pi numbers** — they reflect the runner's CPU/SQLite. The
point is *relative tracking*: a fresh `--check` on the same machine catches
regressions before they hit the Pi.

When to run:
- Any change that touches `db/store.py`, the HTTP routes serving JSON, or
  any new endpoint hit on Home / Sessions / Circuits.
- Before/after a perf optimisation — capture before, ship the change, run
  `--check` after, attach numbers to the PR.
- Re-baseline (`--baseline`) only when an *intentional* speedup lands and
  you want it locked in as the new floor; explain why in the commit.

Default regression budget is +25 % median; tune with `--threshold` if a
change is expected to grow (e.g. wider query for a new feature).

## Before you merge

- [ ] `python3 test_listener.py` — every check green
- [ ] `py_compile` / `node --check` clean for every touched file
- [ ] Regression test added for any bug fix (proven to fail without the fix)
- [ ] `python3 bench_perf.py --check` clean *if your change touches a
      benched hot path* (else not required)
- [ ] CHANGELOG entry for user-facing changes
- [ ] One concern per PR

## Deploying to the Pi

Merging to `main` triggers CI (import + JS syntax smoke) but does **not** deploy.
The Pi pulls manually:

```bash
cd ~/simtelemetry
git checkout main && git pull        # must be on main, not a stale branch
sudo systemctl restart pacefinder
```

Verify the deploy before calling it done:

```bash
curl -s localhost:8000/status | head        # responds, status sane
journalctl -u pacefinder -n 30 --no-pager   # clean startup, no tracebacks
```

Then drive a validation session and confirm the expected behavior in the
post-race modal. **Code merged ≠ bug fixed** — a fix only counts once it's
confirmed on the Pi against real telemetry.

## Adding a track or car ordinal

Forza Motorsport doesn't always broadcast the track name in UDP — only the ordinal (FH5 also includes it). The reference CSVs in [`data/`](./data/) map ordinals to display names. To contribute:

- **Tracks:** open a PR adding rows to [`data/fm8_tracks_extended.csv`](./data/fm8_tracks_extended.csv). Format: `ordinal,track_display_name`.
- **Cars:** open a PR adding rows to [`data/fm8_cars_extended.csv`](./data/fm8_cars_extended.csv). Format: `ordinal,year,make,model`.

Or use the "Add a Forza track or car ordinal" issue template — easier than a PR for one-offs.

## Releasing

Tag pushes drive everything. The `.github/workflows/release.yml` matrix builds and publishes to five channels in parallel; no manual upload steps.

```bash
git checkout main && git pull
git tag -a vX.Y.Z -m "vX.Y.Z — <short summary>"
git push origin vX.Y.Z
```

What runs on a `v*` tag:

| Job | Outcome |
|---|---|
| `macOS .app (MAS)` | PyInstaller → codesign (Mac App Distribution + Installer cert) → `productbuild` .pkg → `xcrun altool` upload to App Store Connect. Build appears in TestFlight within 5–15 min. |
| `Linux AppImage x86_64` | PyInstaller on `ubuntu-latest` → `appimagetool` → attached to GitHub Release. |
| `Linux AppImage aarch64` | PyInstaller on `ubuntu-24.04-arm` (native ARM, no QEMU) → AppImage → attached to GitHub Release. |
| `Docker (multi-arch → GHCR)` | `docker buildx` for `linux/amd64,linux/arm64` → push to `ghcr.io/estetika101/pacefinder` with `vX.Y.Z`, `X.Y.Z`, `X.Y`, `latest`, and `sha-<short>` tags. |
| `Publish GitHub Release` | Attaches both AppImages to the auto-generated release. |

### Pre-release tags

Tags with a `-` suffix (e.g. `v0.7.2-rc1`, `v0.8.0-beta2`) reach App Store Connect via the same path — that's how TestFlight builds are populated. Apple's three-integer `CFBundleShortVersionString` requirement is honored by stripping the suffix in CI: `0.7.2-rc1` becomes short version `0.7.2 (build N)` where `N = GITHUB_RUN_NUMBER`. Pre-release and final tags can therefore share a short version; the build number keeps them distinct.

### Secrets

Nine repo secrets live at **Settings → Secrets and variables → Actions**. They're consumed only by the macOS job; Linux + Docker rely on `GITHUB_TOKEN` for GHCR. Full list and how-to-obtain in the comment block at the top of `.github/workflows/release.yml`. The Apple credentials are owned by **apple@estetika.org** (Apple Developer team `2MRMLK5999`). Rotate the App Store Connect API key by revoking + regenerating with **App Manager** role and updating `APP_STORE_CONNECT_API_KEY_ID` + `APP_STORE_CONNECT_API_KEY_P8` — the Issuer ID stays the same.

### TestFlight follow-up after a release

1. https://appstoreconnect.apple.com → My Apps → Pacefinder → **TestFlight** tab.
2. Build appears as `X.Y.Z (build N)` within 5–15 min of the workflow finishing.
3. First time only: answer the Export Compliance email — Pacefinder uses only standard HTTPS (libssl), so the answer is "No".
4. Internal testers: add yourself / the team to **Internal Testing → App Store Connect Users**. Builds are instantly available in the TestFlight macOS app.
5. External testers: create a group, add the build, fill out **Test Details**, submit for **Beta App Review** (~24 h).
6. Promote to the App Store via **Submit for Review** on the build, once happy with external feedback.

## Code style

- Pure Python 3.9+, stdlib only (plus `anthropic` for the optional Spotter feature)
- No frameworks for the frontend — vanilla JS, embedded `<style>` tags or single CSS files per page
- Modular: parsers in `parsers/`, DB in `db/`, session lifecycle in `session/`, HTTP in `net/`, reference data in `reference/`, page templates in `net/pages/`
- Logging via the `pacefinder` logger; user-facing diagnostic info goes to `INFO`

## Spec template

```markdown
# <Feature name>

## Purpose
<one paragraph: what problem this solves and for whom>

## Behavior
<what the user sees and what the system does>

## Scope
- bulleted list of what's in

## Out of scope
- bulleted list of what's NOT in

## Cross-repo work
- pacefinderapp: <changes here>
- pacefindermarketing: <changes there, or "none">

## Open questions
- anything not yet decided
```
