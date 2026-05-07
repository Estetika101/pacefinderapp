# Install instructions audit + fix

## Purpose
Install copy across the in-app `/setup` page, the README, and the marketing site has drifted out of sync as the project evolved. A first-time Mac user just hit a hard 404 by following the suggested install command, and the Linux/Pi block on `/setup` still references the pre-rename `simtelemetry` systemd unit. Audit every install/setup surface, fix the broken bits, and align all three places to the same source of truth.

## Behavior

### Concrete known issues (must fix)

1. **`net/pages/setup.py` Mac install — broken 404.**
   Line ~187:
   ```
   curl -fsSL https://pacefinder.app/install-mac.sh | bash
   ```
   The marketing site does not host that file. Either (a) actually publish `install-mac.sh` on the marketing domain, or (b) rewrite the in-app instruction to point at the in-repo script. Recommend **(b)** — the marketing site shouldn't be a code-distribution channel; in-repo is auditable and version-pinned to whatever the user cloned.

2. **`net/pages/setup.py` Linux block — references the parked `simtelemetry` unit name.**
   Lines ~195–200 still say:
   ```
   sudo cp simtelemetry.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable simtelemetry
   sudo systemctl start simtelemetry
   ```
   The unit was renamed to `pacefinder.service` in PR #53. Replace `simtelemetry` → `pacefinder` in the file path, the `enable`/`start`, and the status/logs lines below.

3. **Same Linux block — no migration callout.**
   The README has a "Already installed under the old simtelemetry name?" migration block. The `/setup` page should either include the same callout or omit it (since fresh installers won't need it). Recommend **include** as a collapsible/dimmed footnote — same audience.

### Audit checklist (verify, fix anything found)
- [ ] `/setup` Mac block: command works end-to-end on a clean Mac with no existing install
- [ ] `/setup` Linux block: every `simtelemetry` reference replaced with `pacefinder`
- [ ] `/setup` Windows block (if present): Task Scheduler step matches reality
- [ ] `/setup` storage-path placeholder text matches the README's stated default
- [ ] README `Quick Start` commands match `/setup` Quick Start (same clone URL, same script names)
- [ ] README `Auto-start` commands match `/setup` (same migration footnote, same status/logs commands)
- [ ] Marketing site `pacefinder.app#install` block matches both — same commands, same paths, same systemd unit name
- [ ] README `Game Setup` section's port (5300) and packet format (Car Dash) match the in-app `/setup` instructions
- [ ] No remaining references to "simtelemetry" anywhere in user-facing copy except in the migration footnote

### Source-of-truth choice
The README is the canonical source today and is the most up-to-date. Mirror it into `/setup` and the marketing site rather than the other way around. Going forward, when install steps change, update the README first, then sync to the other two surfaces in the same PR.

### Acceptance
- Following the `/setup` Mac block on a clean Mac produces a working installation
- Following the `/setup` Linux block on a clean Pi produces a working `pacefinder.service`
- `grep -ri "simtelemetry" net/pages/setup.py` returns only the storage-path placeholder + the config-file name (both legitimate — those names didn't get renamed)
- All three surfaces (README, `/setup`, marketing site) prescribe the same commands

## Scope
- Edit `net/pages/setup.py` to fix the Mac 404 and the Linux unit-name drift
- Edit the marketing site (`pacefinder` repo) to match
- Confirm README accuracy after edits
- No code-behavior changes; pure copy

## Out of scope
- The first-run wizard / intro card (separate spec)
- Hosting `install-mac.sh` on the marketing domain (rejected above; in-repo is the answer)
- Renaming `simtelemetry.config.json` → `pacefinder.config.json` (would break existing installs; not worth it)
- Renaming the storage-path default `/mnt/usb/simtelemetry` (same — would break)

## Cross-repo work
- `pacefinderapp`: setup page edits + README accuracy check
- `pacefinder` (marketing): install block sync

## Open questions
- For the Mac install instruction, should we suggest `bash install-mac.sh` after `git clone`, or `./install-mac.sh` (with `chmod +x` already done in-repo)? Recommend `bash install-mac.sh` — matches the README, doesn't depend on file mode.
- Worth adding a `make install` shortcut so all three platforms have one command? Defer — adds a Makefile dependency for a one-line shortcut.
