"""
Anonymous, opt-out usage analytics. See docs/specs/usage-analytics.md for
the full spec: what's tracked, why, and what's deliberately excluded
(track/car/lap-time data, IPs, raw error messages/tracebacks).

Fire-and-forget: every send happens on its own daemon thread with a short
timeout, so a slow or failed collector can never block the caller. Silently
a no-op whenever config["analytics_enabled"] is False or ANALYTICS_ENDPOINT
is unset — call sites never need to check state themselves.
"""
import json
import logging
import sys
import threading
import urllib.request

from config import config
from net.updater import detect_deployment

try:
    from _version import APP_VERSION  # generated at build; gitignored
except ImportError:
    APP_VERSION = "dev"

log = logging.getLogger("pacefinder")

# Left unset until the collector (pacefindermarketing repo, Neon-backed
# POST /api/analytics/event) actually exists — see docs/specs/
# usage-analytics.md's "open questions". Every send silently no-ops until
# this is filled in, so this module is safe to wire up ahead of that.
ANALYTICS_ENDPOINT = ""

# Explicit allow-list — never a generic pass-through event name. Adding a
# new event means updating this set *and* the spec.
_ALLOWED_EVENTS = {"app_launch", "session_saved", "telemetry_viewed", "spotter_used", "error"}

_SEND_TIMEOUT_S = 3


def track(event: str, **fields):
    """Fire an analytics event. No-op if disabled, endpoint unset, or the
    event isn't in the allow-list (a typo'd event name — logged once so
    it's caught in dev instead of silently dropped forever)."""
    if event not in _ALLOWED_EVENTS:
        log.warning(f"analytics: unknown event {event!r} — dropped")
        return
    if not ANALYTICS_ENDPOINT or not config.get("analytics_enabled"):
        return

    payload = {
        "analytics_id": config.get("analytics_id", ""),
        "app_version":  APP_VERSION,
        "platform":     sys.platform,
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
