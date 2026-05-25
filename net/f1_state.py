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
import struct
import threading
import time
from typing import Optional

_lock = threading.Lock()
_state: dict = {}                 # merged latest fields (any session)
_session_uid: Optional[int] = None
_last_update_at: float = 0.0      # monotonic seconds
_packet_counts: dict = {}         # _packet_type -> count
_raw_id_counts: dict = {}         # int packet_id -> count
_packet_format: Optional[int] = None  # 2023 / 2024 / 2025 / …
_last_sizes: dict = {}            # packet_id -> last observed size (bytes)
_last_session_time: Optional[float] = None  # game's internal clock (s)
_last_session_time_recv_at: Optional[float] = None  # wall clock at receive

# F1 telemetry packet-id catalog (Codemasters F1 2023+). Helps the raw
# screen show "id 3 = Event" instead of bare numbers when we get types
# parse_f1 hasn't been taught yet.
PACKET_ID_NAMES = {
    0:  "Motion",
    1:  "Session",
    2:  "LapData",
    3:  "Event",
    4:  "Participants",
    5:  "CarSetups",
    6:  "CarTelemetry",
    7:  "CarStatus",
    8:  "FinalClassification",
    9:  "LobbyInfo",
    10: "CarDamage",
    11: "SessionHistory",
    12: "TyreSets",
    13: "MotionEx",
    14: "TimeTrial",
    15: "LapPositions",
}


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


def note_raw(data: bytes) -> None:
    """Record every inbound F1 datagram by packet_id + size, regardless of
    whether parse_f1 can decode it. Lets the raw screen prove that packets
    are flowing even when parse_f1 returns None (e.g. Event packets in the
    pre-session menu, or a newer F1 25 layout the parser hasn't learned)."""
    if len(data) < 19:
        return
    global _packet_format, _last_session_time, _last_session_time_recv_at
    try:
        pid = data[6]
        fmt = struct.unpack_from("<H", data, 0)[0]
        # F1 header layout: packetFormat(H) gameYear(B) majorVer(B) minorVer(B)
        # packetVersion(B) packetId(B) sessionUID(Q) sessionTime(f) …
        # sessionTime is a float at offset 15.
        session_time = struct.unpack_from("<f", data, 15)[0]
    except Exception:
        return
    now = time.monotonic()
    with _lock:
        _packet_format = fmt
        _raw_id_counts[pid] = _raw_id_counts.get(pid, 0) + 1
        _last_sizes[pid] = len(data)
        _last_session_time = session_time
        _last_session_time_recv_at = now


def snapshot() -> dict:
    """Return the merged state plus light metadata for the live/raw screens."""
    with _lock:
        age_s = (time.monotonic() - _last_update_at) if _last_update_at else None
        raw_ids = {
            f"{pid} {PACKET_ID_NAMES.get(pid, '?')}": {
                "count": n, "last_size": _last_sizes.get(pid),
            }
            for pid, n in sorted(_raw_id_counts.items())
        }
        # game_clock_lag_s: how far behind wall-clock the in-packet sessionTime
        # is advancing. If the game side is buffering or downsampling, this
        # value grows; if the data is truly current, it stays ~0.
        # We anchor on the first observed sessionTime+recv pair (saved in
        # _state under "__anchor") and report (now - anchor_wall) - (st - anchor_st).
        game_lag = None
        if _last_session_time is not None and _last_session_time_recv_at is not None:
            anchor = _state.get("__anchor")
            if anchor is None:
                _state["__anchor"] = {"st": _last_session_time, "wall": _last_session_time_recv_at}
            else:
                wall_elapsed = _last_session_time_recv_at - anchor["wall"]
                game_elapsed = _last_session_time - anchor["st"]
                game_lag = round(wall_elapsed - game_elapsed, 2)
        return {
            "_game":           "f1",
            "_session_uid":    _session_uid,
            "_packet_format":  _packet_format,
            "_last_update_age_s": round(age_s, 2) if age_s is not None else None,
            "_session_time":   round(_last_session_time, 2) if _last_session_time is not None else None,
            "_game_clock_lag_s": game_lag,
            "_packet_counts":  dict(_packet_counts),
            "_raw_packet_ids": raw_ids,
            **{k: v for k, v in _state.items() if not k.startswith("__")},
        }
