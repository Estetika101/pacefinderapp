"""
F1 live-state accumulator.

The F1 (Codemasters) UDP feed splits a single car's state across multiple
packet types — telemetry, lap_data, motion, car_status — each at its own
cadence. The Forza dashboard assumes a single fully-formed packet; for F1
we merge by `_session_uid` so the live view and the raw screen see one
coherent dict instead of whichever packet type happened to arrive last.

Scope: this is intentionally minimal — exploratory surface for
`feature/f1-dip-toes`. It does not write to the DB and does not interact
with `session.manager`.
"""
import threading
import time
from typing import Optional

_lock = threading.Lock()
_state: dict = {}                 # merged latest fields (any session)
_session_uid: Optional[int] = None
_last_update_at: float = 0.0      # monotonic seconds
_packet_counts: dict = {}         # _packet_type -> count


def update(parsed: dict) -> None:
    """Merge a parsed F1 packet into the rolling state."""
    if not parsed:
        return
    global _session_uid, _last_update_at
    ptype = parsed.get("_packet_type", "unknown")
    uid   = parsed.get("_session_uid")
    with _lock:
        if uid is not None and uid != _session_uid:
            # New session — drop stale fields from the prior session.
            _state.clear()
            _packet_counts.clear()
            _session_uid = uid
        for k, v in parsed.items():
            if k.startswith("_") or v is None:
                continue
            _state[k] = v
        _packet_counts[ptype] = _packet_counts.get(ptype, 0) + 1
        _last_update_at = time.monotonic()


def snapshot() -> dict:
    """Return the merged state plus light metadata for the live/raw screens."""
    with _lock:
        age_s = (time.monotonic() - _last_update_at) if _last_update_at else None
        return {
            "_game":           "f1",
            "_session_uid":    _session_uid,
            "_last_update_age_s": round(age_s, 2) if age_s is not None else None,
            "_packet_counts":  dict(_packet_counts),
            **_state,
        }
