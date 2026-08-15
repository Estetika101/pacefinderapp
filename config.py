import json
import logging
import os
import sys
from pathlib import Path

from platformdirs import user_data_dir

# Where the user config lives. Frozen (PyInstaller) builds MUST write to a
# per-user dir — never inside the .app/.exe bundle. macOS App Sandbox enforces
# this, and codesign rejects bundles that contain post-build modifications.
# Source clones (Pi systemd service, dev macOS/Linux) keep the in-tree path
# so existing setups don't need migration.
#
# The Docker image sets PACEFINDER_DATA_DIR=/data (its declared VOLUME) so
# both the config file and the default storage_path below land on the bind
# mount. Without this, CONFIG_FILE fell inside WORKDIR /app and the default
# storage_path (/mnt/usb/simtelemetry, the Pi-USB default) was silently
# mkdir-able by the container's root user — both invisible to `docker run -v
# $(pwd)/data:/data` and wiped on every container recreation.
_DOCKER_DATA_DIR = os.environ.get("PACEFINDER_DATA_DIR")

if getattr(sys, "frozen", False):
    _USER_DATA = Path(user_data_dir("Pacefinder", appauthor=False))
    _USER_DATA.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE = _USER_DATA / "simtelemetry.config.json"
elif _DOCKER_DATA_DIR:
    CONFIG_FILE = Path(_DOCKER_DATA_DIR) / "simtelemetry.config.json"
else:
    CONFIG_FILE = Path(__file__).parent / "simtelemetry.config.json"

DEFAULTS: dict = {
    "storage_path":      _DOCKER_DATA_DIR or "/mnt/usb/simtelemetry",
    "session_timeout_s": 10,
    "idle_timeout_s":    30,
    "status_port":       8000,
    "ports": {
        # ACC (9996) is PARKED — see docs/specs/park-acc-f1.md
        # F1 (20777) is re-bound on feature/f1-dip-toes for the exploratory
        # /f1 live + /f1/raw screens; ingestion to the DB is still parked.
        "forza_motorsport": 5300,
        "f1":               20777,
    },
    "anthropic_api_key": "",
    "anthropic_model":   "claude-sonnet-4-6",
    # UI-only display preference. "24h" (default) or "12h".
    # See docs/specs/time-format-preference.md.
    "time_format":       "24h",
    # When true, the live dashboard speaks an audible "I think the race
    # is over" the moment race-end is detected — a diagnostic aid for
    # validating race-end timing against what actually happened on track.
    "debug_mode":        False,
    # Set to True the first time a frozen (PyInstaller) build auto-opens the
    # dashboard in the user's browser. Subsequent launches don't.
    "first_run_done":    False,
    # Anonymous, opt-out usage analytics (app launches, sessions saved,
    # feature usage, error rates) — never track/car/lap-time data or
    # anything else that describes what someone actually did on track.
    # See docs/specs/usage-analytics.md.
    "analytics_enabled": True,
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text())
            merged = {**DEFAULTS, **saved}
            # Only honor saved port overrides for known/active games.
            # Stale acc/f1 keys in user configs are ignored (parked).
            saved_ports = {k: v for k, v in saved.get("ports", {}).items() if k in DEFAULTS["ports"]}
            merged["ports"] = {**DEFAULTS["ports"], **saved_ports}
            return merged
        except Exception:
            pass
    return {**DEFAULTS, "ports": {**DEFAULTS["ports"]}}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


config = load_config()

# analytics_id: a random UUID generated once per install, never derived from
# hostname/MAC/hardware — exists only so the (opt-out) usage-analytics
# collector can tell "1 install racing 50 times" from "50 installs racing
# once". Deliberately not in DEFAULTS (a shared default would defeat the
# point); generated lazily here and persisted immediately so it's stable
# across restarts. See docs/specs/usage-analytics.md.
if not config.get("analytics_id"):
    import uuid
    config["analytics_id"] = str(uuid.uuid4())
    save_config(config)

# Per-user, per-OS data dir. Used when the configured storage_path is
# unavailable — e.g. the Pi USB isn't mounted, or a fresh Mac/Windows install
# inherits the DEFAULTS value (/mnt/usb/simtelemetry) that doesn't exist there.
# Linux: ~/.local/share/Pacefinder · macOS: ~/Library/Application Support/Pacefinder
# Windows: %LOCALAPPDATA%\Pacefinder
_LOCAL_FALLBACK = Path(user_data_dir("Pacefinder", appauthor=False))


def resolve_storage_path(candidate: str) -> Path:
    """Resolve a candidate storage path, creating it if needed and falling back
    to the per-user data dir if it can't be created/used (e.g. the Pi-only
    default /mnt/usb/simtelemetry on a Mac/Windows/dev box). Shared by
    storage_path() (the configured default) and the /config POST handler (a
    user-submitted candidate) so runtime and settings-save agree on what
    counts as a usable path — settings-save used to hard-fail on exactly the
    case runtime already tolerates silently, blocking a Setup save (e.g. just
    entering an Anthropic API key) on a storage_path field the user never
    touched."""
    p = Path(candidate)
    if p.exists():
        return p
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except OSError:
        _LOCAL_FALLBACK.mkdir(parents=True, exist_ok=True)
        return _LOCAL_FALLBACK


def storage_path() -> Path:
    """Return the active storage root, falling back to the per-user data dir if the configured path is unavailable."""
    return resolve_storage_path(config["storage_path"])


PORTS             = config["ports"]
SESSION_TIMEOUT_S = config["session_timeout_s"]
IDLE_TIMEOUT_S    = config["idle_timeout_s"]
STATUS_PORT       = config["status_port"]
LOG_LEVEL         = logging.INFO

# Floor below which a lap_time_s is treated as an out-lap or partial. Used by
# the session-close filter and the theoretical-best calculation. 20s is shorter
# than any real circuit lap, so anything under it is structurally suspect.
MIN_VALID_LAP_S = 20.0

# Max fractional deviation of a lap's sector time from the track's per-sector
# median before the lap is treated as rotated (distance_norm anchored to a
# mid-track first sample instead of the start/finish line) and excluded from
# sector references. Rotation preserves Σsectors == lap_time, so the 5% sum
# gate can't catch it; a rotated lap instead shows ~20-30% per-sector skew,
# while honest hot laps stay within a few percent of the median.
SECTOR_OUTLIER_FRAC = 0.20
