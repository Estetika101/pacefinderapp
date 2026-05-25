# Installer matrix

## Purpose

Pacefinder shipped through v0.7.1 as `git clone && python3 listener.py`. That works for developers but is a barrier for the broader Forza Motorsport audience. This spec captures the distribution pipeline introduced in v0.7.2-rc6 — five channels, all driven by a single tag push, no manual upload steps.

Tracked in [#210](https://github.com/Estetika101/pacefinderapp/issues/210); landed across PRs [#216](https://github.com/Estetika101/pacefinderapp/pull/216), [#217](https://github.com/Estetika101/pacefinderapp/pull/217), [#219](https://github.com/Estetika101/pacefinderapp/pull/219), [#220](https://github.com/Estetika101/pacefinderapp/pull/220), [#221](https://github.com/Estetika101/pacefinderapp/pull/221).

## Behavior

### Channels

| Platform | Channel | Build | Auto-update |
|---|---|---|---|
| macOS | TestFlight + Mac App Store | PyInstaller `.app` → codesign → `productbuild` `.pkg` → `xcrun altool` upload to App Store Connect | Apple handles silently |
| Linux x64 | AppImage from GitHub Releases | PyInstaller on `ubuntu-latest` → `appimagetool` | None (self-managed) |
| Linux ARM (Pi 4/5) | AppImage from GitHub Releases | PyInstaller on `ubuntu-24.04-arm` (native ARM runner, no QEMU) → `appimagetool` | None (self-managed) |
| Any OS (power-user) | Docker, multi-arch | `docker buildx` for `linux/amd64,linux/arm64` → push to `ghcr.io/estetika101/pacefinder` | `docker pull` |
| Any OS (power-user) | `git clone` + `python3 listener.py` | — | `git pull` |

Windows (Microsoft Store + Velopack `.exe`) is **out of scope** for v0.7.2 — listed in #210 as a separate channel slated for a later milestone.

### Trigger model

Tag push (`v*`) drives the whole matrix. The workflow also accepts `pull_request` (build-only, no publish) for validating spec/Dockerfile/workflow changes before merge, and `workflow_dispatch` for ad-hoc reruns.

### Versioning

`CFBundleShortVersionString` must be three integers per Apple. Pre-release tags strip the suffix:

- Git tag `v0.7.2-rc1` → short version `0.7.2`, `CFBundleVersion = GITHUB_RUN_NUMBER`.
- Git tag `v0.7.2` → short version `0.7.2`, `CFBundleVersion = GITHUB_RUN_NUMBER` (always higher than any earlier rc's number).

Successive rc builds and the eventual final all share the same short version; the build number keeps them monotonically distinct, satisfying Apple's per-short-version monotonicity rule.

### Cross-cutting code changes

Two architectural changes in the listener support frozen builds. Both are no-ops for source clones (Pi systemd, dev) so existing setups don't need migration.

- **`platformdirs` for storage fallback** — when `config["storage_path"]` is unavailable, fall back to `platformdirs.user_data_dir("Pacefinder")` instead of the in-tree `./data` directory. Bundles ship sensible defaults on Mac, Linux, and Windows without a config file.
- **Bundle-aware `CONFIG_FILE`** — when `sys.frozen`, the config file lives at `platformdirs.user_data_dir / "simtelemetry.config.json"`, never inside the `.app` or `.exe` bundle. Apple's codesign refuses to sign bundles with post-build writes; macOS App Sandbox enforces the same constraint at runtime. Source clones keep the in-tree path.

### Codesigning policy

- **macOS** — Mac App Distribution + Mac Installer Distribution certs signed by Apple. Notarization is implicit (App Store Connect handles it). Bundle is sandboxed with the entitlements at [`packaging/mac/entitlements.plist`](../../packaging/mac/entitlements.plist): `app-sandbox`, `network.server` (UDP 5300 + TCP 8000), `network.client` (Anthropic), `files.user-selected.read-write` (storage path override).
- **Linux AppImage** — unsigned. Apple-style notarization doesn't apply.
- **Docker** — unsigned. Tag immutability + GHCR audit log is the trust model.

## Scope

- All five channels listed above publishing on every `v*` tag push.
- Pre-release tag support (TestFlight uses the same upload path as the App Store; choice between TestFlight beta and App Store submission is made downstream in App Store Connect).
- PR-time smoke matrix (build everything, publish nothing) for validating workflow/spec/Dockerfile changes.
- App Store Connect API key auth (modern alternative to the deprecated Apple ID + app-specific-password flow).
- Pre-flight auth diagnostics that isolate auth failures from upload failures.
- Defensive bundle scrub between the macOS smoke test and codesign.
- Per-platform smoke test (boot → curl `/status` → SIGTERM) before any publish step.

## Out of scope

- **Windows** — Microsoft Store (`.msix`) + Velopack `.exe`. Tracked in #210, deferred.
- **`keyring` for secret storage** — Anthropic API key stays in `simtelemetry.config.json` (plain text inside the sandbox container on Mac, which Apple allows). MAS sandbox doesn't strictly require keyring; deferring to a follow-up.
- **Auto-update on Linux** — AppImages are self-managed. Snap / Flatpak / `.deb` not packaged.
- **iOS / Android** — separate project shape entirely.
- **Code-review automation for the workflow itself** — relying on standard PR review.

## Cross-repo work

- `pacefinderapp`: PyInstaller spec, GitHub Actions release workflow, packaging assets (entitlements, AppImage scaffolding, icons), Dockerfile + .dockerignore, README install section, CHANGELOG, this spec.
- `pacefindermarketing`: pacefinder.app install block needs to surface the four end-user channels (TestFlight request form, Linux AppImage download, Pi AppImage download, Docker pull). Tracked separately in the marketing repo — see the cross-repo rule in [docs/specs/README.md](README.md).

## Open questions

- **Icon artwork** — current `.icns` is a placeholder generated in CI debugging ([#221](https://github.com/Estetika101/pacefinderapp/pull/221)). Real artwork replaces `packaging/icons/pacefinder.{icns,png}` as a one-file swap; no workflow changes needed.
- **External TestFlight cadence** — internal-only access is enough until UI/spotter feedback stabilizes. Open question: when to open external TestFlight and through what funnel (form on pacefinder.app vs. invite-only via Discord/email).
- **Windows store path** — covered in #210, separate spec when it's time.
