"""
Anonymous, opt-out usage analytics. See docs/specs/usage-analytics-v2.md for
the full spec: what's tracked, why, and what's deliberately excluded
(track/car/lap-time data, IPs, raw error messages/tracebacks).

Fire-and-forget: every send happens on its own daemon thread with a short
timeout, so a slow or failed collector can never block the caller. Silently
a no-op whenever config["analytics_enabled"] is False or ANALYTICS_ENDPOINT
is unset — call sites never need to check state themselves.

Deliberately has no knowledge of session/listener internals (no import from
session.manager) — session.manager already imports this module to fire
session_saved, and a top-level import the other way would be circular.
Anything that needs live app state (e.g. the heartbeat's capture_ok/
session_active/uptime_s) is gathered by the caller and passed in as fields.
"""
import json
import logging
import platform as _platform_module
import sys
import threading
import urllib.request
from datetime import datetime, timezone

from config import config
from net.updater import detect_deployment

try:
    from _version import APP_VERSION  # generated at build; gitignored
except ImportError:
    APP_VERSION = "dev"

log = logging.getLogger("pacefinder")

# pacefindermarketing repo's POST /api/analytics/event — Neon-backed,
# verified live (docs/specs/usage-analytics.md). Still gated by
# config["analytics_enabled"] (default True, opt-out) on every call.
ANALYTICS_ENDPOINT = "https://pacefinder.app/api/analytics/event"

# Explicit allow-list — never a generic pass-through event name. Adding a
# new event means updating this set *and* the spec, and the collector's own
# mirrored allow-list in pacefindermarketing.
#
# telemetry_viewed (v1) is gone — it duplicated page_viewed:telemetry fired
# from the adjacent line in net/router.py. Two events for one action were
# guaranteed to diverge; the telemetry page keeps just page_viewed.
_ALLOWED_EVENTS = {
    "app_launch", "session_saved", "spotter_used", "error", "heartbeat",
    "page_viewed", "first_packet", "feature_used", "update_applied",
}

# page_viewed's own allow-list for the `page` field — same reasoning as the
# event names themselves: an explicit, enumerable set, never a raw path.
_ALLOWED_PAGES = {"home", "sessions", "session_detail", "circuits", "circuit_detail", "cars", "dashboard", "setup", "telemetry"}

# feature_used's `feature` field. deepdive/lap_compare/reference_set are the
# actual analysis surfaces (XHR endpoints that fired nothing in v1 — the
# open question was whether anyone uses the analysis at all). session_confirm
# vs session_skip is its own pair: ia.md treats deferral as reclaimable, and
# this is the only way to see whether deferred sessions actually get
# reclaimed or just abandoned.
_ALLOWED_FEATURES = {
    "deepdive", "lap_compare", "mistakes", "reference_set", "session_confirm",
    "session_skip", "session_edit", "session_delete", "car_nickname",
}

# error's `context` field. An explicit enum, not a raw f-string, is the whole
# point — it's what stops a future call site from leaking a local file path
# (or anything else identifying) through the "which" half of an error event.
_ALLOWED_ERROR_CONTEXTS = {
    "lap_samples_write", "session_json_write", "track_reference_update",
    "http_request", "udp_bind", "http_bind", "spotter_call",
    "storage_fallback", "db_migration",
}

_SEND_TIMEOUT_S = 3

# Every other event is one-shot — app_launch fires once at startup, and
# nothing fires again if the user just leaves the dashboard open for hours,
# which is normal for a background listener (especially on a Pi left
# running 24/7). Without a periodic signal, "still running right now" is
# unanswerable from the event stream alone. 20 minutes (online window 40,
# still 2x) — no question this data answers needs 10-minute resolution, and
# halving the interval halves the row volume a heartbeat-as-event-row would
# cost (moot once the collector routes heartbeat to an upsert instead, but
# still the right default either way).
HEARTBEAT_INTERVAL_S = 1200

_PY_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"

# sys.platform is win32 on Windows, not "windows" — normalise so a dashboard
# GROUP BY doesn't split a single OS across two labels. darwin/linux already
# read correctly and pass through unchanged.
def _platform() -> str:
    return "windows" if sys.platform == "win32" else sys.platform


def track(event: str, **fields):
    """Fire an analytics event. No-op if disabled, endpoint unset, or the
    event (or an event-specific field) isn't in its allow-list (a typo'd
    value — logged once so it's caught in dev instead of silently dropped
    forever)."""
    if event not in _ALLOWED_EVENTS:
        log.warning(f"analytics: unknown event {event!r} — dropped")
        return
    if event == "page_viewed" and fields.get("page") not in _ALLOWED_PAGES:
        log.warning(f"analytics: unknown page {fields.get('page')!r} — dropped")
        return
    if event == "feature_used" and fields.get("feature") not in _ALLOWED_FEATURES:
        log.warning(f"analytics: unknown feature {fields.get('feature')!r} — dropped")
        return
    if event == "error" and fields.get("context") not in _ALLOWED_ERROR_CONTEXTS:
        log.warning(f"analytics: unknown error context {fields.get('context')!r} — dropped")
        return
    if not ANALYTICS_ENDPOINT or not config.get("analytics_enabled"):
        return

    payload = {
        "schema_v":     2,
        "ts":           datetime.now(timezone.utc).isoformat(),
        "analytics_id": config.get("analytics_id", ""),
        "app_version":  APP_VERSION,
        "platform":     _platform(),
        "arch":         _platform_module.machine(),
        "py_version":   _PY_VERSION,
        "deployment":   detect_deployment(),
        "event":        event,
        **fields,
    }
    threading.Thread(target=_send, args=(payload,), daemon=True).start()


def _send(payload: dict):
    try:
        req = urllib.request.Request(
            ANALYTICS_ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=_SEND_TIMEOUT_S).close()
    except Exception:
        pass  # fire-and-forget — analytics must never surface an error to the user
