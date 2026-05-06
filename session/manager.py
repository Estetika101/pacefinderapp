import json
import struct
import threading
import time
from datetime import datetime
from typing import Optional
import logging

from config import storage_path, SESSION_TIMEOUT_S, IDLE_TIMEOUT_S, RACE_END_DETECTION_PACKETS
from db.store import (
    _classify_race_type,
    _db_write_session,
    _store_session_lap_samples,
    _update_track_references_bg,
)
from reference.loader import FORZA_CARS

_log = logging.getLogger("pacefinder")


def _is_driving(parsed: dict) -> bool:
    """True when the player has meaningful input — not parked or in a menu."""
    return (
        parsed.get("speed_mph", 0) > 2 or
        parsed.get("throttle_pct", 0) > 2 or
        parsed.get("brake_pct", 0) > 2 or
        abs(parsed.get("steer", 0)) > 5
    )


class LapRecord:
    def __init__(self, lap_number: int):
        self.lap_number   = lap_number
        self.started_at   = time.time()
        self.ended_at     = None
        self.lap_time_s   = None
        self.samples      = []
        self.max_speed    = 0.0
        self.sector_times = []

    def add_sample(self, parsed: dict):
        speed = parsed.get("speed_mph", 0)
        if speed > self.max_speed:
            self.max_speed = speed
        sample = {
            "t":            round(parsed.get("current_lap_time", parsed.get("_t", 0)), 3),
            "speed_mph":    round(parsed.get("speed_mph", 0), 1),
            "throttle_pct": round(parsed.get("throttle_pct", 0), 1),
            "brake_pct":    round(parsed.get("brake_pct", 0), 1),
            "clutch_pct":   round(parsed.get("clutch_pct", 0), 1),
            "gear":         parsed.get("gear", 0),
            "steer":        round(parsed.get("steer", 0), 3),
            "rpm":          parsed.get("rpm", parsed.get("current_engine_rpm", 0)),
            "slip_rl":      round(parsed.get("slip_ratio_rl", 0), 4),
            "slip_rr":      round(parsed.get("slip_ratio_rr", 0), 4),
            "g_lat":        round(parsed.get("g_lat", 0), 3),
            "g_lon":        round(parsed.get("g_lon", 0), 3),
        }
        if parsed.get("position_x") is not None:
            sample["px"] = round(parsed["position_x"], 2)
            sample["py"] = round(parsed["position_y"], 2)
            sample["pz"] = round(parsed["position_z"], 2)
        for corner in ("fl", "fr", "rl", "rr"):
            v = parsed.get(f"tire_temp_{corner}")
            if v is not None:
                sample[f"tyre_{corner}"] = round(v, 1)
        self.samples.append(sample)

    def close(self, lap_time_s: Optional[float] = None):
        self.ended_at   = time.time()
        self.lap_time_s = lap_time_s or (self.ended_at - self.started_at)

    def to_dict(self) -> dict:
        return {
            "lap_number":    self.lap_number,
            "lap_time_s":    round(self.lap_time_s, 3) if self.lap_time_s else None,
            "max_speed_mph": round(self.max_speed, 1),
            "sample_count":  len(self.samples),
            "samples":       self.samples,
        }


class Session:
    def __init__(self, game: str, started_at: datetime):
        self.game         = game
        self.started_at   = started_at
        self.session_id   = started_at.strftime("%Y-%m-%dT%H-%M-%S") + f"_{game}"
        self.last_packet  = time.time()
        self.packet_count = 0
        self.track        = "unknown"
        self.car          = "unknown"
        self.session_type = "unknown"

        self.current_lap_num = 0
        self.current_lap: Optional[LapRecord] = None
        self.completed_laps: list = []
        self.best_lap_time_s: Optional[float] = None
        self._last_seen_lap_time: Optional[float] = None

        self._motion_cache: dict = {}
        self._lap_cache: dict = {}

        self.race_type = None
        self._race_positions: list = []
        self.track_ordinal: Optional[int] = None
        self.car_class: Optional[int] = None
        self.car_pi: Optional[int] = None
        self.car_manufacturer: Optional[str] = None
        self.car_year: Optional[int] = None
        self.weather_condition: Optional[str] = None
        self.track_temp_c: Optional[float] = None
        self.air_temp_c: Optional[float] = None
        self.tyre_compound: Optional[str] = None

        self.last_activity = time.time()

        # Race-end detection state (see docs/specs/race-end-detection.md)
        self._last_is_race_on: Optional[int] = None
        self._race_off_streak: int = 0
        self._should_close_for_race_end: bool = False
        self.closed_reason: Optional[str] = None

        raw_path = storage_path() / "raw" / f"{self.session_id}.bin"
        try:
            self.raw_file = open(raw_path, "wb")
        except OSError as e:
            _log.error(f"Cannot open raw archive {raw_path}: {e} — raw recording disabled")
            self.raw_file = None
        _log.info(f"Session started: {self.session_id} (storage: {storage_path()})")

    def ingest(self, raw: bytes, parsed: dict):
        if self.raw_file:
            try:
                self.raw_file.write(struct.pack("<I", len(raw)) + raw)
            except OSError as e:
                _log.error(f"Raw write failed: {e} — closing raw archive")
                self.raw_file = None
        self.last_packet  = time.time()
        self.packet_count += 1

        if self._is_driving(parsed):
            self.last_activity = self.last_packet

        packet_type = parsed.get("_packet_type")

        if packet_type == "motion":
            self._motion_cache.update({
                k: v for k, v in parsed.items() if not k.startswith("_")
            })
            return

        if packet_type == "graphics":
            st = parsed.get("session_type", "unknown")
            if st and st != "unknown":
                self.session_type = st
            rp = parsed.get("race_position")
            # Only capture race_position when the race is actually live — Forza
            # broadcasts a phantom P1 during the pre-race countdown which would
            # otherwise be mis-cached as the grid position.
            if rp is not None and rp > 0 and parsed.get("is_race_on") == 1:
                self._race_positions.append(rp)
            if parsed.get("weather_condition") and self.weather_condition is None:
                self.weather_condition = parsed["weather_condition"]
            return

        if packet_type == "telemetry":
            if self._motion_cache:
                parsed = {**parsed, **self._motion_cache}
                self._motion_cache = {}
            if self._lap_cache:
                parsed = {**self._lap_cache, **parsed}
                self._lap_cache = {}

        if parsed.get("track", "unknown") != "unknown":
            self.track = parsed["track"]
        if parsed.get("track_ordinal") is not None and self.track_ordinal is None:
            self.track_ordinal = parsed["track_ordinal"]
        if parsed.get("car_class") is not None and self.car_class is None:
            _ordinal = parsed.get("car_ordinal")
            if _ordinal is None or _ordinal in FORZA_CARS:
                self.car_class = int(parsed["car_class"])
        if parsed.get("car_performance_index") is not None and self.car_pi is None:
            self.car_pi = int(parsed["car_performance_index"])
        if parsed.get("weather_condition") and self.weather_condition is None:
            self.weather_condition = parsed["weather_condition"]
        if parsed.get("track_temp_c") is not None and self.track_temp_c is None:
            self.track_temp_c = parsed["track_temp_c"]
        if parsed.get("air_temp_c") is not None and self.air_temp_c is None:
            self.air_temp_c = parsed["air_temp_c"]
        if parsed.get("session_type", "unknown") != "unknown":
            self.session_type = parsed["session_type"]
        if "car_ordinal" in parsed and self.car == "unknown":
            ordinal = parsed["car_ordinal"]
            car_info = FORZA_CARS.get(ordinal)
            if car_info:
                self.car              = car_info["name"]
                self.car_manufacturer = car_info["manufacturer"]
                self.car_year         = car_info["year"]
            else:
                # Unmapped ordinal — show "Unknown Car" in the UI rather than the raw
                # number. The user can override via the edit modal. Log the ordinal
                # once per session so it's easy to grep listener.log for additions
                # to data/fm8_cars_extended.csv. See pacefinderapp issue #6.
                self.car = "Unknown Car"
                _log.info(f"[{self.game}] Unmapped car_ordinal={ordinal} — displayed as 'Unknown Car'")

        rp = parsed.get("race_position")
        # Only capture race_position when the race is actually live — Forza
        # broadcasts a phantom P1 during the pre-race countdown which would
        # otherwise be mis-cached as the grid position.
        if rp is not None and rp > 0 and parsed.get("is_race_on") == 1:
            self._race_positions.append(rp)

        llt = parsed.get("last_lap_time")
        if llt and 0 < llt < 600:
            self._last_seen_lap_time = llt

        lap_num = parsed.get("lap_number", 0)
        if lap_num and lap_num != self.current_lap_num:
            self._transition_lap(
                new_lap=lap_num,
                lap_time_s=parsed.get("last_lap_time"),
            )

        if self.current_lap is None:
            self.current_lap = LapRecord(self.current_lap_num)

        parsed["_t"] = time.time() - self.current_lap.started_at
        self.current_lap.add_sample(parsed)

        self._update_race_end_state(parsed.get("is_race_on"))

    def _update_race_end_state(self, new_is_race_on):
        """Detect a sustained is_race_on 1 → 0 transition that signals a real
        race end (vs. a brief blip). See docs/specs/race-end-detection.md.

        We require: (a) the previous packet had is_race_on=1, (b) the current
        and a sustained run of subsequent packets are 0 (RACE_END_DETECTION_PACKETS),
        and (c) at least one lap was completed in this session — so a session
        that ends before any lap finishes still falls back to the timeout path.
        """
        if new_is_race_on is None:
            return
        if self._last_is_race_on == 1 and new_is_race_on == 0:
            self._race_off_streak = 1
            _log.info(
                f"[{self.game}] is_race_on 1→0 transition (race-end candidate) — "
                f"{len(self.completed_laps)} lap(s) completed so far"
            )
        elif new_is_race_on == 0 and self._race_off_streak > 0:
            self._race_off_streak += 1
            if (self._race_off_streak >= RACE_END_DETECTION_PACKETS
                    and self.completed_laps
                    and not self._should_close_for_race_end):
                self._should_close_for_race_end = True
                self.closed_reason = "race_end"
            elif (self._race_off_streak == RACE_END_DETECTION_PACKETS
                    and not self.completed_laps):
                # Threshold reached but the no-completed-laps guard held — log once
                # so we know why early-close didn't fire (will fall through to the
                # 10s timeout watchdog instead).
                _log.info(
                    f"[{self.game}] is_race_on=0 sustained {RACE_END_DETECTION_PACKETS} "
                    f"packets but no lap completed — early-close skipped, "
                    f"falling back to timeout watchdog"
                )
        elif new_is_race_on == 1:
            self._race_off_streak = 0
        self._last_is_race_on = new_is_race_on

    def _transition_lap(self, new_lap: int, lap_time_s: Optional[float] = None):
        if self.current_lap is not None:
            self.current_lap.close(lap_time_s)
            if lap_time_s:
                if self.best_lap_time_s is None or lap_time_s < self.best_lap_time_s:
                    self.best_lap_time_s = lap_time_s
            self.completed_laps.append(self.current_lap)
            _log.info(
                f"[{self.game}] Lap {self.current_lap.lap_number} complete | "
                f"time={lap_time_s:.3f}s | samples={len(self.current_lap.samples)}"
                if lap_time_s else
                f"[{self.game}] Lap {self.current_lap.lap_number} complete | "
                f"samples={len(self.current_lap.samples)}"
            )
        self.current_lap_num = new_lap
        self.current_lap = LapRecord(new_lap)

    def _infer_forza_session_type(self) -> str:
        positions = self._race_positions
        if not positions:
            return "unknown"
        unique = set(positions)
        if len(unique) == 1 and next(iter(unique)) == 1:
            valid_laps = len([l for l in self.completed_laps if l.lap_time_s and l.lap_time_s > 0])
            return "time_trial" if valid_laps <= 3 else "practice"
        return "race"

    def _is_driving(self, parsed: dict) -> bool:
        return _is_driving(parsed)

    def is_timed_out(self) -> bool:
        return time.time() - self.last_packet > SESSION_TIMEOUT_S

    def is_idle_timed_out(self) -> bool:
        return time.time() - self.last_activity > IDLE_TIMEOUT_S

    def close(self) -> dict:
        if self.closed_reason is None:
            self.closed_reason = "timeout"
        if self.raw_file:
            try:
                self.raw_file.close()
            except OSError:
                pass

        if self.current_lap and self.current_lap.samples:
            inferred_time: Optional[float] = None
            last_completed_time = (self.completed_laps[-1].lap_time_s
                                   if self.completed_laps else None)
            llt = self._last_seen_lap_time
            if (llt and 0 < llt < 600 and
                    (last_completed_time is None or abs(llt - last_completed_time) > 0.01)):
                inferred_time = llt
            elif self.current_lap.samples:
                t = self.current_lap.samples[-1].get("t", 0)
                if t and t > 1:
                    inferred_time = round(t, 3)
            self.current_lap.close(inferred_time)
            if inferred_time:
                if self.best_lap_time_s is None or inferred_time < self.best_lap_time_s:
                    self.best_lap_time_s = inferred_time
                _log.info(
                    f"[{self.game}] Final lap {self.current_lap.lap_number} recovered "
                    f"| time={inferred_time:.3f}s (source={'last_lap_time' if llt and abs(llt-inferred_time)<0.01 else 'current_lap_time'})"
                )
            self.completed_laps.append(self.current_lap)

        laps_summary = [
            {
                "lap_number":    lap.lap_number,
                "lap_time_s":    lap.lap_time_s,
                "max_speed_mph": lap.max_speed,
                "sample_count":  len(lap.samples),
            }
            for lap in self.completed_laps
        ]

        if self.game in ("forza_motorsport", "forza_horizon_5") and self.session_type == "unknown":
            self.session_type = self._infer_forza_session_type()

        grid_pos   = self._race_positions[0]  if self._race_positions and self.session_type == "race" else None
        finish_pos = self._race_positions[-1] if self._race_positions and self.session_type == "race" else None

        valid_laps = len([l for l in self.completed_laps if l.lap_time_s and l.lap_time_s > 0])
        self.race_type = _classify_race_type(self._race_positions, valid_laps)

        has_enough_laps = len(self.completed_laps) >= 2
        has_valid_lap   = bool(self.best_lap_time_s and 0 < self.best_lap_time_s < 600)
        if not (has_enough_laps or has_valid_lap):
            _log.info(
                f"Session discarded — insufficient data "
                f"({len(self.completed_laps)} lap(s), "
                f"best_lap={'%.3f' % self.best_lap_time_s if self.best_lap_time_s else 'none'})"
            )
            return {}

        session_data = {
            "session_id":       self.session_id,
            "game":             self.game,
            "track":            self.track,
            "car":              self.car,
            "session_type":     self.session_type,
            "race_type":        self.race_type,
            "started_at":       self.started_at.isoformat(),
            "ended_at":         datetime.now().isoformat(),
            "packet_count":     self.packet_count,
            "best_lap_time_s":  round(self.best_lap_time_s, 3) if self.best_lap_time_s else None,
            "laps":             laps_summary,
            "grid_pos":         grid_pos,
            "finish_pos":       finish_pos,
            "track_ordinal":    self.track_ordinal,
            "car_class":        self.car_class,
            "car_pi":           self.car_pi,
            "car_manufacturer": self.car_manufacturer,
            "car_year":         self.car_year,
            "weather_condition": self.weather_condition,
            "track_temp_c":     self.track_temp_c,
            "air_temp_c":       self.air_temp_c,
            "closed_reason":    self.closed_reason,
            "tyre_compound":    self.tyre_compound,
        }

        _db_write_session(session_data)
        _store_session_lap_samples(self.session_id, self.completed_laps)
        threading.Thread(
            target=_update_track_references_bg,
            args=(self.track, self.game),
            daemon=True,
        ).start()

        try:
            sp = storage_path()
            out_path = sp / "sessions" / f"{self.session_id}.json"
            with open(out_path, "w") as f:
                json.dump(session_data, f, indent=2)

            samples_path = sp / "sessions" / f"{self.session_id}_laps.json"
            with open(samples_path, "w") as f:
                json.dump([lap.to_dict() for lap in self.completed_laps], f, indent=2)
        except OSError as e:
            _log.error(f"Failed to write session files: {e}")

        _log.info(
            f"Session closed: {self.session_id} | "
            f"{self.packet_count} packets | {len(self.completed_laps)} laps | "
            f"best={self.best_lap_time_s:.3f}s" if self.best_lap_time_s
            else f"Session closed: {self.session_id} | {self.packet_count} packets"
        )
        return session_data


# ─── Shared State ─────────────────────────────────────────────────────────────

state = {
    "status":           "idle",
    "game":             None,
    "session_id":       None,
    "track":            None,
    "car":              None,
    "session_type":     None,
    "started_at":       None,
    "packet_count":     0,
    "lap":              0,
    "best_lap_time_s":  None,
    "speed_mph":        0,
    "throttle_pct":     0,
    "brake_pct":        0,
    "gear":             0,
    "rpm":              0,
    "engine_max_rpm":   0,
    "steer":            0,
    "slip_rl":          0,
    "slip_rr":          0,
    "g_lat":            0,
    "g_lon":            0,
    "drs":              False,
    "tyre_compound":    None,
    "race_position":    None,
    "grid_pos":         None,
    "fuel_remaining_laps": None,
    "current_lap_time": None,
    "last_lap_time_s":  None,
    "tyre_fl":          None,
    "tyre_fr":          None,
    "tyre_rl":          None,
    "tyre_rr":          None,
    "last_packet_at":   None,
    "udp_received":     {"forza_motorsport": 0, "acc": 0, "f1": 0},
    "udp_rejected":     {"forza_motorsport": 0, "acc": 0, "f1": 0},
    "last_rejected_size": {"forza_motorsport": None, "acc": None, "f1": None},
    "udp_last_at":      {"forza_motorsport": None, "acc": None, "f1": None},
    "bound_ports": {},
}

active_sessions: dict = {}


def update_state(game: str, session: Session, parsed: dict):
    if "_packet_type" in parsed and parsed["_packet_type"] in ("motion", "lap_data", "graphics"):
        return
    state["status"]       = "receiving" if session._is_driving(parsed) else "idle"
    state["game"]         = game
    state["session_id"]   = session.session_id
    state["track"]        = session.track
    state["car"]          = session.car
    state["session_type"] = session.session_type
    state["started_at"]   = session.started_at.isoformat()
    state["packet_count"] = session.packet_count
    state["lap"]          = session.current_lap_num
    state["best_lap_time_s"] = session.best_lap_time_s
    bl_pkt = parsed.get("best_lap_time")
    if bl_pkt and bl_pkt > 0:
        state["best_lap_time_s"] = round(bl_pkt, 3)
        if session.best_lap_time_s is None or bl_pkt < session.best_lap_time_s:
            session.best_lap_time_s = bl_pkt
    _driving = session._is_driving(parsed)
    state["speed_mph"]    = parsed.get("speed_mph", state["speed_mph"]) if _driving else 0
    state["throttle_pct"] = parsed.get("throttle_pct", state["throttle_pct"]) if _driving else 0
    state["brake_pct"]    = parsed.get("brake_pct", state["brake_pct"]) if _driving else 0
    state["gear"]         = parsed.get("gear", state["gear"])
    state["rpm"]          = parsed.get("rpm", parsed.get("current_engine_rpm", state["rpm"]))
    if parsed.get("engine_max_rpm", 0) > 2000:
        state["engine_max_rpm"] = parsed["engine_max_rpm"]
    state["steer"]        = round(parsed.get("steer", state["steer"]), 3) if _driving else 0
    state["slip_rl"]      = round(parsed.get("slip_ratio_rl", state["slip_rl"]), 4) if _driving else 0
    state["slip_rr"]      = round(parsed.get("slip_ratio_rr", state["slip_rr"]), 4) if _driving else 0
    state["g_lat"]        = round(parsed.get("g_lat", state["g_lat"]), 3)
    state["g_lon"]        = round(parsed.get("g_lon", state["g_lon"]), 3)
    state["drs"]          = parsed.get("drs", state["drs"])
    state["tyre_compound"]       = parsed.get("tyre_compound", state["tyre_compound"])
    # Race position: latest from packet history; grid is the first non-zero seen.
    # Clear on new sessions that haven't seen a position packet yet so the live
    # dashboard doesn't show stale values from the previous race.
    if session._race_positions:
        state["race_position"] = session._race_positions[-1]
        state["grid_pos"]      = session._race_positions[0]
    else:
        state["race_position"] = None
        state["grid_pos"]      = None
    state["fuel_remaining_laps"] = parsed.get("fuel_remaining_laps", state["fuel_remaining_laps"])
    state["current_lap_time"]    = parsed.get("current_lap_time", state["current_lap_time"])
    if parsed.get("last_lap_time"):
        state["last_lap_time_s"] = parsed["last_lap_time"]
    for corner in ("fl", "fr", "rl", "rr"):
        v = parsed.get(f"tire_temp_{corner}")
        if v is None:
            v = parsed.get(f"tyre_surface_temp_{corner}")
        if v is None:
            v = parsed.get(f"tyre_core_temp_{corner}")
        if v is not None:
            state[f"tyre_{corner}"] = round(v, 1)
    state["last_packet_at"] = datetime.now().isoformat()
