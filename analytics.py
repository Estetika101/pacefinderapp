"""
Anonymous, opt-out usage analytics. See docs/specs/usage-analytics.md for
the full spec: what's tracked, why, and what's deliberately excluded
(track/car/lap-time data, IPs, raw error messages/tracebacks).

Fire-and-forget: every send happens on its own daemon thread with a short
timeout, so a slow or failed collector can never block the caller. Silently
a no-op whenever config["analytics_enabled"] is False or ANALYTICS_ENDPOINT
is unset — call sites never need to check state themselves.
"""
import asyncio
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

# pacefindermarketing repo's POST /api/analytics/event — Neon-backed,
# verified live (docs/specs/usage-analytics.md). Still gated by
# config["analytics_enabled"] (default True, opt-out) on every call.
ANALYTICS_ENDPOINT = "https://pacefinder.app/api/analytics/event"

# Explicit allow-list — never a generic pass-through event name. Adding a
# new event means updating this set *and* the spec.
_ALLOWED_EVENTS = {"app_launch", "session_saved", "telemetry_viewed", "spotter_used", "error", "heartbeat"}

_SEND_TIMEOUT_S = 3

# Every other event is one-shot — app_launch fires once at startup, and
# nothing fires again if the user just leaves the dashboard open for hours,
# which is normal for a background listener (especially on a Pi left
# running 24/7). Without a periodic signal, "still running right now" is
# unanswerable from the event stream alone. 10 minutes balances that against
# event volume for a process that can run indefinitely; the dashboard treats
# anything within 2x this window as "online" to tolerate a missed beat.
HEARTBEAT_INTERVAL_S = 600


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


async def heartbeat_loop():
    """Background task: fires a heartbeat event every HEARTBEAT_INTERVAL_S
    for as long as the process is alive. Run as an asyncio task from
    listener.py's main(), alongside session_watchdog()."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_S)
        track("heartbeat")


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
