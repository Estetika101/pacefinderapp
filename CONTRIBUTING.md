# Contributing to Pacefinder

Pacefinder records UDP telemetry from Forza Motorsport, archives every session, and serves a live dashboard. Active focus is **Forza only** — ACC and F1 are parked (parser code is in tree but not bound at startup).

## Workflow

1. **Specs first.** Non-trivial features get a markdown file in [`docs/specs/`](./docs/specs/) before any code lands. Spec describes purpose, behavior, scope, out-of-scope, and open questions. Template at [`docs/specs/README.md`](./docs/specs/README.md).
2. **Issue per spec.** Each spec gets a matching GitHub issue with a 3-line body pointing back to the spec file. Use the templates in [`.github/ISSUE_TEMPLATE/`](./.github/ISSUE_TEMPLATE/).
3. **Branch + PR.** Implementation goes on a `feature/`, `fix/`, `cleanup/`, or `docs/` branch. PR closes the matching issue (`Closes #N`).
4. **One PR per concern.** If you find an unrelated bug while working, open a separate PR or issue rather than bundling.

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

## Adding a track or car ordinal

Forza Motorsport doesn't always broadcast the track name in UDP — only the ordinal (FH5 also includes it). The reference CSVs in [`data/`](./data/) map ordinals to display names. To contribute:

- **Tracks:** open a PR adding rows to [`data/fm8_tracks_extended.csv`](./data/fm8_tracks_extended.csv). Format: `ordinal,track_display_name`.
- **Cars:** open a PR adding rows to [`data/fm8_cars_extended.csv`](./data/fm8_cars_extended.csv). Format: `ordinal,year,make,model`.

Or use the "Add a Forza track or car ordinal" issue template — easier than a PR for one-offs.

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
