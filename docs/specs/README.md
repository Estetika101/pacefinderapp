# Specs

Canonical home for Pacefinder feature specs. Lives in the product repo because most features are upstream of the marketing site.

## Convention

- One file per feature: `<feature-slug>.md` (e.g. `spotter-v2.md`, `acc-tire-pressure.md`)
- Write the spec first, commit it, then implement against it
- Cross-repo features (product + marketing) reference this folder by absolute path from the marketing repo

## Template

```markdown
# <Feature Name>

## Purpose
One sentence: what problem this solves and for whom.

## Behavior
What the user sees and what the system does. Be specific.

## Scope
- Bullet list of what's included.

## Out of scope
- Bullet list of what's deliberately not included.

## Cross-repo work
- `pacefinderapp`: <what changes>
- `pacefinder` (marketing): <what changes, or "none">

## Open questions
- Anything not yet decided.
```

Specs are living documents until shipped. Once a feature ships, the spec is historical — leave it as-is rather than editing to match reality (the code is the source of truth post-ship).
