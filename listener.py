"""
Pacefinder Listener
Supports: Forza Motorsport, Assetto Corsa Competizione, F1 (Codemasters 2023/2024)
Listens on all three ports simultaneously, auto-detects game from packet size/id.
Saves raw archives and structured JSON sessions to USB storage.
Exposes local web status server at http://pi.local:8000
"""

import asyncio
import collections
import json
import logging
import os
import shutil
import socket
import threading
import urllib.parse
import struct
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from net.pages.dashboard import DASHBOARD_HTML
from net.pages.setup import SETUP_HTML
from net.pages.admin import ADMIN_HTML
from net.pages.sessions import (
    GAMES_HTML, TRACKS_HTML,
    TRACK_DETAIL_HTML_PRE, TRACK_DETAIL_HTML_POST,
    SESSION_DETAIL_HTML_PRE, SESSION_DETAIL_HTML_POST,
)
from net.pages.telemetry import TELEMETRY_HTML
from net.router import make_handler
from net.api import (
    build_inject_packets as _build_inject_packets_core,
    build_analysis_prompt as _build_analysis_prompt_core,
    build_track_tip_prompt as _build_track_tip_prompt,
    call_claude_api as _call_claude_api_core,
)
from parsers.forza import (
    FM_PACKET_SIZE, FM_PACKET_SIZE_FH, FM_FORMAT, FM_FORMAT_FH, FM_FIELDS,
    parse_forza as _parse_forza_core,
)
from parsers.acc import parse_acc
from parsers.f1 import F1_HEADER_SIZE, parse_f1
from db.store import (
    initialize as _db_initialize,
    _db_lock,
    _db_connect,
    _db_init,
    _load_learned_track_ordinals,
    _db_write_learned_ordinal,
    _effective_tracks,
    _classify_race_type,
    _db_cull_ghost_sessions,
    _db_backfill_track_names,
    _db_write_session,
    _db_sessions_list,
    _db_games_index,
    _db_career_kpis,
    _db_form_data,
    _db_recent_sessions,
    _db_tracks_index,
    _db_track_sessions,
    _db_get_track_tip,
    _db_save_track_tip,
    _db_update_session,
    _db_drop_last_lap,
    _db_get_ai_analysis,
    _db_save_ai_analysis,
    _db_get_lap_samples,
    _store_session_lap_samples,
    _backfill_lap_samples,
    _update_track_references_bg,
)

# ─── Config file ──────────────────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).parent / "simtelemetry.config.json"

DEFAULTS: dict = {
    "storage_path":      "/mnt/usb/simtelemetry",
    "session_timeout_s": 10,
    "idle_timeout_s":    30,
    "status_port":       8000,
    "ports": {
        "forza_motorsport": 5300,
        "acc":              9996,
        "f1":               20777,
    },
    "anthropic_api_key": "",
    "anthropic_model":   "claude-sonnet-4-6",
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text())
            merged = {**DEFAULTS, **saved}
            merged["ports"] = {**DEFAULTS["ports"], **saved.get("ports", {})}
            return merged
        except Exception:
            pass
    return {**DEFAULTS, "ports": {**DEFAULTS["ports"]}}

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

config = load_config()

# Convenience accessors — always read through config so runtime updates take effect
_LOCAL_FALLBACK = Path(__file__).parent / "data"

def storage_path() -> Path:
    """Return the active storage root, falling back to a local data/ dir if USB isn't mounted."""
    p = Path(config["storage_path"])
    if p.exists():
        return p
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except OSError:
        _LOCAL_FALLBACK.mkdir(parents=True, exist_ok=True)
        return _LOCAL_FALLBACK

PORTS             = config["ports"]          # used at bind time; port changes need restart
SESSION_TIMEOUT_S = config["session_timeout_s"]
IDLE_TIMEOUT_S    = config["idle_timeout_s"]
STATUS_PORT       = config["status_port"]
LOG_LEVEL         = logging.INFO
_listener_started_at = None  # float, set in main()
_started_at: list = [None]  # mutable ref for router closure
_DEMO_DB_PATH_REF: list = [None]  # mutable ref; set by --demo flag; overrides storage_path()/simtelemetry.db

# ─── Logging ──────────────────────────────────────────────────────────────────

# Bootstrap log dir before logger is configured; use default path if storage
# doesn't exist yet so the process doesn't crash on first run.
_log_dir = Path(config["storage_path"]) / "logs"
try:
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_handler = logging.FileHandler(_log_dir / "listener.log")
except OSError:
    _log_handler = logging.StreamHandler()  # fallback if path isn't mounted yet

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[_log_handler, logging.StreamHandler()],
)
log = logging.getLogger("pacefinder")

# ─── Debug Console ────────────────────────────────────────────────────────────

_debug_clients: list = []
_debug_buffer: collections.deque = collections.deque(maxlen=500)

def _debug_push(line: str):
    _debug_buffer.append(line)
    for q in list(_debug_clients):
        try:
            q.put_nowait(line)
        except Exception:
            pass

class _DebugLogHandler(logging.Handler):
    def emit(self, record):
        _debug_push(self.format(record))

_dbg_log_handler = _DebugLogHandler()
_dbg_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
log.addHandler(_dbg_log_handler)

# ─── Storage Setup ────────────────────────────────────────────────────────────

def ensure_storage():
    for subdir in ["raw", "sessions", "logs"]:
        (storage_path() / subdir).mkdir(parents=True, exist_ok=True)

def disk_info() -> dict:
    """Return free/total bytes for the storage path volume."""
    try:
        usage = shutil.disk_usage(storage_path())
        return {
            "total_gb": round(usage.total / 1e9, 1),
            "used_gb":  round(usage.used  / 1e9, 1),
            "free_gb":  round(usage.free  / 1e9, 1),
        }
    except OSError:
        return {"total_gb": None, "used_gb": None, "free_gb": None}

def _get_local_ips() -> list:
    """Return non-loopback IPv4 addresses on all local interfaces."""
    ips: list = []
    seen: set = set()
    # Primary route — UDP trick sends no actual packets
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            seen.add(ip); ips.append(ip)
    except Exception:
        pass
    # All addresses advertised for this hostname
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip and not ip.startswith("127.") and ip not in seen:
                seen.add(ip); ips.append(ip)
    except Exception:
        pass
    return ips

# ─── Forza Motorsport Parser ──────────────────────────────────────────────────
# FM2023 Data Out "Car Dash" packet: 311 bytes
# Reference: https://support.forzamotorsport.net/hc/en-us/articles/21742934024211

# Hardcoded fallbacks below are merged as lowest-priority baseline.
FORZA_TRACKS: dict = {}   # ordinal (int) -> track name (str)
FORZA_CARS:   dict = {}   # ordinal (int) -> {name, manufacturer, year}

# Hardcoded fallbacks (pre-CSV, FH5-era research). CSV data overrides these.
_FORZA_TRACKS_FALLBACK = {
    860: "Brands Hatch Tor Grand Prix",
    0:   "Test Track Airfield",
    1:   "Test Track Airfield Drag",
}


def _load_forza_reference_data() -> None:
    """Parse data/fm8_tracks.csv and data/fm8_cars.csv into FORZA_TRACKS / FORZA_CARS.

    Precedence (highest first):
      1. learned_track_ordinals from SQLite
      2. fm8_tracks.csv data
      3. _FORZA_TRACKS_FALLBACK hardcoded dict
    """
    import csv as _csv

    global FORZA_TRACKS, FORZA_CARS

    # Start with hardcoded fallbacks
    merged: dict = dict(_FORZA_TRACKS_FALLBACK)

    data_dir = Path(__file__).parent / "data"

    # ── Tracks CSV ────────────────────────────────────────────────────────────
    tracks_csv = data_dir / "fm8_tracks.csv"
    track_count = 0
    if tracks_csv.exists():
        try:
            with tracks_csv.open(encoding="utf-8") as fh:
                for row in _csv.reader(fh):
                    if not row or row[0].startswith("#"):
                        continue
                    if len(row) < 5:
                        continue
                    try:
                        ordinal   = int(row[0].strip())
                        name_part = row[1].strip()
                        layout    = row[4].strip()
                        display   = f"{name_part} {layout}" if layout else name_part
                        merged[ordinal] = display
                        track_count += 1
                    except (ValueError, IndexError):
                        continue
        except Exception as exc:
            log.warning(f"Could not parse fm8_tracks.csv: {exc}")

    # ── Cars CSV ─────────────────────────────────────────────────────────────
    cars_csv = data_dir / "fm8_cars.csv"
    car_count = 0
    cars: dict = {}
    if cars_csv.exists():
        try:
            with cars_csv.open(encoding="utf-8") as fh:
                for row in _csv.reader(fh):
                    if not row or row[0].startswith("#"):
                        continue
                    if len(row) < 3:
                        continue
                    try:
                        ordinal = int(row[0].strip())
                        year    = int(row[1].strip())
                        make    = row[2].strip()
                        model   = row[3].strip() if len(row) > 3 else ""
                        if not make:
                            continue
                        full_name = f"{year} {make} {model}".strip()
                        cars[ordinal] = {"name": full_name, "manufacturer": make, "year": year}
                        car_count += 1
                    except (ValueError, IndexError):
                        continue
        except Exception as exc:
            log.warning(f"Could not parse fm8_cars.csv: {exc}")

    FORZA_CARS = cars

    # ── Merge learned DB ordinals (highest priority) ──────────────────────────
    try:
        learned = _load_learned_track_ordinals()
        merged.update(learned)
    except Exception:
        pass  # DB may not be init yet on first call

    FORZA_TRACKS = merged
    log.info(f"Loaded {track_count} FM tracks, {car_count} FM cars from reference data")
    # Diagnostic: first 20 entries so mismatches are visible at startup
    preview = sorted(merged.items())[:20]
    log.debug(f"FORZA_TRACKS sample: {preview}")

# Ordinals seen in live packets but not in FORZA_TRACKS — logged once each
_unknown_ordinals_seen: set = set()

# FM2023 track names for manual session track confirmation via Edit modal
FM2023_TRACKS = sorted([
    "Brands Hatch Grand Prix",
    "Brands Hatch Indy Circuit",
    "Circuit de Spa-Francorchamps",
    "Circuit de Spa-Francorchamps (24h Layout)",
    "Circuit de Catalunya Grand Prix",
    "Circuit de Catalunya National",
    "Daytona International Speedway (Oval)",
    "Daytona International Speedway (Road)",
    "Dubai Autodrome Club",
    "Dubai Autodrome Grand Prix",
    "Dubai Autodrome International",
    "Dubai Autodrome National",
    "Hakone Circuit",
    "Homestead-Miami Speedway",
    "Indianapolis Motor Speedway (Oval)",
    "Indianapolis Motor Speedway (Road)",
    "Kyalami Grand Prix Circuit",
    "Laguna Seca Full Circuit",
    "Le Mans Full Circuit",
    "Le Mans Old Mulsanne Circuit",
    "Lime Rock Full Circuit",
    "Maple Valley Full Circuit",
    "Maple Valley Short Circuit",
    "Mid-Ohio Sports Car Course",
    "Mugello Full Circuit",
    "Nürburgring 24h Course",
    "Nürburgring Grand Prix",
    "Nürburgring Nordschleife",
    "Road America East Route",
    "Road America Full Circuit",
    "Road America West Route",
    "Road Atlanta Full Circuit",
    "Sebring Full Circuit",
    "Sebring International Raceway",
    "Sebring Short Circuit",
    "Silverstone Grand Prix",
    "Silverstone International",
    "Silverstone National",
    "Suzuka East",
    "Suzuka Full Circuit",
    "Watkins Glen Grand Prix",
    "Watkins Glen Short Circuit",
    "Yas Marina Corkscrew",
    "Yas Marina Full Circuit",
    "Yas Marina North Corkscrew",
    "Yas Marina North Circuit",
    "Yas Marina South Circuit",
])



def parse_forza(data: bytes) -> Optional[dict]:
    return _parse_forza_core(data, _effective_tracks, _unknown_ordinals_seen, log)

# ─── Session Manager ──────────────────────────────────────────────────────────

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
        self.lap_number  = lap_number
        self.started_at  = time.time()
        self.ended_at    = None
        self.lap_time_s  = None
        self.samples     = []
        self.max_speed   = 0.0
        self.sector_times = []  # populated for Forza/F1 where available

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
            "lap_number":   self.lap_number,
            "lap_time_s":   round(self.lap_time_s, 3) if self.lap_time_s else None,
            "max_speed_mph": round(self.max_speed, 1),
            "sample_count": len(self.samples),
            "samples":      self.samples,
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

        # Lap tracking
        self.current_lap_num = 0
        self.current_lap: Optional[LapRecord] = None
        self.completed_laps: list[LapRecord] = []
        self.best_lap_time_s: Optional[float] = None
        self._last_seen_lap_time: Optional[float] = None  # last_lap_time field from packets

        # Motion cache (F1 motion packets arrive separately from telemetry)
        self._motion_cache: dict = {}
        # Lap data cache (F1 LapData packets arrive separately from telemetry)
        self._lap_cache: dict = {}

        self.race_type = None  # set post-session via /sessions/update
        self._race_positions: list[int] = []  # sampled positions for session type inference
        self.track_ordinal: Optional[int] = None  # raw ordinal for learned track mapping
        self.car_class: Optional[int] = None        # 0=D 1=C 2=B 3=A 4=S1 5=S2 6=X
        self.car_pi: Optional[int] = None           # performance index (100–999)
        self.car_manufacturer: Optional[str] = None # e.g. "Porsche"
        self.car_year: Optional[int] = None         # e.g. 1997
        self.weather_condition: Optional[str] = None
        self.track_temp_c: Optional[float] = None
        self.air_temp_c: Optional[float] = None

        self.last_activity = time.time()  # updated only when driver input is detected

        raw_path = storage_path() / "raw" / f"{self.session_id}.bin"
        try:
            self.raw_file = open(raw_path, "wb")
        except OSError as e:
            log.error(f"Cannot open raw archive {raw_path}: {e} — raw recording disabled")
            self.raw_file = None
        log.info(f"Session started: {self.session_id} (storage: {storage_path()})")

    def ingest(self, raw: bytes, parsed: dict):
        if self.raw_file:
            try:
                self.raw_file.write(struct.pack("<I", len(raw)) + raw)
            except OSError as e:
                log.error(f"Raw write failed: {e} — closing raw archive")
                self.raw_file = None
        self.last_packet  = time.time()
        self.packet_count += 1

        if self._is_driving(parsed):
            self.last_activity = self.last_packet

        packet_type = parsed.get("_packet_type")

        # Merge F1 motion data into next telemetry sample
        if packet_type == "motion":
            self._motion_cache.update({
                k: v for k, v in parsed.items() if not k.startswith("_")
            })
            return

        # ACC graphics packet — update session metadata only, not a lap sample
        if packet_type == "graphics":
            st = parsed.get("session_type", "unknown")
            if st and st != "unknown":
                self.session_type = st
            rp = parsed.get("race_position")
            if rp is not None and rp > 0:
                self._race_positions.append(rp)
            if parsed.get("weather_condition") and self.weather_condition is None:
                self.weather_condition = parsed["weather_condition"]
            return

        # Merge cached motion and lap data into telemetry
        if packet_type == "telemetry":
            if self._motion_cache:
                parsed = {**parsed, **self._motion_cache}
                self._motion_cache = {}
            if self._lap_cache:
                parsed = {**self._lap_cache, **parsed}  # telemetry fields take precedence
                self._lap_cache = {}

        # Update track/car metadata
        if parsed.get("track", "unknown") != "unknown":
            self.track = parsed["track"]
        if parsed.get("track_ordinal") is not None and self.track_ordinal is None:
            self.track_ordinal = parsed["track_ordinal"]
        if parsed.get("car_class") is not None and self.car_class is None:
            _ordinal = parsed.get("car_ordinal")
            # Only trust the broadcast class when the ordinal is confirmed in our CSV.
            # Unknown ordinals can broadcast a wrong class (e.g. X instead of R).
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
                self.car = str(ordinal)

        # Sample race_position for session type inference at close()
        # F1: comes from merged LapData; Forza: from packet directly
        rp = parsed.get("race_position")
        if rp is not None and rp > 0:
            self._race_positions.append(rp)

        # Track last_lap_time for end-of-race recovery (is_race_on may drop before lap_number increments)
        llt = parsed.get("last_lap_time")
        if llt and 0 < llt < 600:
            self._last_seen_lap_time = llt

        # Forza: lap transitions via lap_number field
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

        # Update car status fields (F1 car_status packets)
        if packet_type == "car_status":
            pass  # already merged into session via update_state

    def _transition_lap(self, new_lap: int, lap_time_s: Optional[float] = None):
        if self.current_lap is not None:
            self.current_lap.close(lap_time_s)
            if lap_time_s:
                if self.best_lap_time_s is None or lap_time_s < self.best_lap_time_s:
                    self.best_lap_time_s = lap_time_s
            self.completed_laps.append(self.current_lap)
            log.info(
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
        if self.raw_file:
            try:
                self.raw_file.close()
            except OSError:
                pass

        # Close current lap — attempt to recover the actual lap time when
        # is_race_on dropped to 0 before lap_number incremented (e.g. Forza race end).
        # Priority: (1) last_lap_time seen in packets if not already used for a prior lap,
        #           (2) current_lap_time from the last sample (close approximation),
        #           (3) wall-clock fallback (marked as unreliable by being absent from best).
        if self.current_lap and self.current_lap.samples:
            inferred_time: Optional[float] = None
            last_completed_time = (self.completed_laps[-1].lap_time_s
                                   if self.completed_laps else None)
            llt = self._last_seen_lap_time
            if (llt and 0 < llt < 600 and
                    (last_completed_time is None or abs(llt - last_completed_time) > 0.01)):
                inferred_time = llt
            elif self.current_lap.samples:
                # Use the current_lap_time from the last sample as approximation
                t = self.current_lap.samples[-1].get("t", 0)
                if t and t > 1:
                    inferred_time = round(t, 3)
            self.current_lap.close(inferred_time)
            if inferred_time:
                if self.best_lap_time_s is None or inferred_time < self.best_lap_time_s:
                    self.best_lap_time_s = inferred_time
                log.info(
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

        # Infer Forza session type from position history if not already known
        if self.game in ("forza_motorsport", "forza_horizon_5") and self.session_type == "unknown":
            self.session_type = self._infer_forza_session_type()

        # Derive grid/finish positions for race sessions
        grid_pos  = self._race_positions[0]  if self._race_positions and self.session_type == "race" else None
        finish_pos = self._race_positions[-1] if self._race_positions and self.session_type == "race" else None

        # Classify race_type from position history (overrides any existing value)
        valid_laps = len([l for l in self.completed_laps if l.lap_time_s and l.lap_time_s > 0])
        self.race_type = _classify_race_type(self._race_positions, valid_laps)

        # Minimum validity check — discard menu-browse ghost sessions
        has_enough_laps = len(self.completed_laps) >= 2
        has_valid_lap = bool(self.best_lap_time_s and 0 < self.best_lap_time_s < 600)
        if not (has_enough_laps or has_valid_lap):
            log.info(
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
            "track_ordinal":      self.track_ordinal,
            "car_class":          self.car_class,
            "car_pi":             self.car_pi,
            "car_manufacturer":   self.car_manufacturer,
            "car_year":           self.car_year,
            "weather_condition":  self.weather_condition,
            "track_temp_c":       self.track_temp_c,
            "air_temp_c":         self.air_temp_c,
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
            log.error(f"Failed to write session files: {e}")

        log.info(
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
    "fuel_remaining_laps": None,
    "current_lap_time": None,
    "last_lap_time_s":  None,
    "tyre_fl":          None,
    "tyre_fr":          None,
    "tyre_rl":          None,
    "tyre_rr":          None,
    "last_packet_at":   None,
    # per-game raw UDP counters (arrive regardless of whether parse succeeds)
    "udp_received": {"forza_motorsport": 0, "acc": 0, "f1": 0},
    "udp_rejected": {"forza_motorsport": 0, "acc": 0, "f1": 0},
    "last_rejected_size": {"forza_motorsport": None, "acc": None, "f1": None},
    "udp_last_at": {"forza_motorsport": None, "acc": None, "f1": None},
    "bound_ports": {},
}

active_sessions: dict[str, Session] = {}

def update_state(game: str, session: Session, parsed: dict):
    # Skip packets that carry no telemetry (motion, lap metadata, ACC graphics)
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
    # Forza broadcasts best_lap_time in every packet — use it as the authoritative value
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
    state["rpm"]            = parsed.get("rpm", parsed.get("current_engine_rpm", state["rpm"]))
    if parsed.get("engine_max_rpm", 0) > 2000:
        state["engine_max_rpm"] = parsed["engine_max_rpm"]
    state["steer"]        = round(parsed.get("steer", state["steer"]), 3) if _driving else 0
    state["slip_rl"]      = round(parsed.get("slip_ratio_rl", state["slip_rl"]), 4) if _driving else 0
    state["slip_rr"]      = round(parsed.get("slip_ratio_rr", state["slip_rr"]), 4) if _driving else 0
    state["g_lat"]        = round(parsed.get("g_lat", state["g_lat"]), 3)
    state["g_lon"]        = round(parsed.get("g_lon", state["g_lon"]), 3)
    state["drs"]          = parsed.get("drs", state["drs"])
    state["tyre_compound"]       = parsed.get("tyre_compound", state["tyre_compound"])
    state["fuel_remaining_laps"] = parsed.get("fuel_remaining_laps", state["fuel_remaining_laps"])
    state["current_lap_time"]    = parsed.get("current_lap_time", state["current_lap_time"])
    if parsed.get("last_lap_time"):
        state["last_lap_time_s"] = parsed["last_lap_time"]
    for corner in ("fl", "fr", "rl", "rr"):
        v = parsed.get(f"tire_temp_{corner}")               # Forza
        if v is None:
            v = parsed.get(f"tyre_surface_temp_{corner}")   # F1
        if v is None:
            v = parsed.get(f"tyre_core_temp_{corner}")      # ACC
        if v is not None:
            state[f"tyre_{corner}"] = round(v, 1)
    state["last_packet_at"]      = datetime.now().isoformat()

# ─── UDP Protocol Handlers ────────────────────────────────────────────────────

class TelemetryProtocol(asyncio.DatagramProtocol):
    def __init__(self, game: str, parser):
        self.game         = game
        self.parser       = parser
        self._logged_size = False  # log unexpected packet size once per run

    def datagram_received(self, data: bytes, addr):
        state["udp_received"][self.game] = state["udp_received"].get(self.game, 0) + 1
        state["udp_last_at"][self.game] = datetime.now().isoformat(timespec="seconds")

        parsed = self.parser(data)
        if not parsed:
            count = state["udp_rejected"].get(self.game, 0) + 1
            state["udp_rejected"][self.game] = count
            state["last_rejected_size"][self.game] = len(data)
            ts = datetime.now().strftime("%H:%M:%S")
            hex16 = data[:16].hex(" ") if len(data) >= 16 else data.hex(" ")
            _debug_push(f"{ts} [REJECTED] {self.game} {len(data)}B from {addr[0]}  hex={hex16}")
            # Log on first rejection and every 100th after
            if count == 1 or count % 100 == 0:
                log.warning(
                    f"[{self.game}] packet #{count} from {addr[0]} rejected — "
                    f"size={len(data)} bytes  first16={hex16}. "
                    f"Forza expects {FM_PACKET_SIZE} (FM2023) or {FM_PACKET_SIZE_FH} (FH4/FH5), "
                    f"ACC expects >={100}, F1 expects >={F1_HEADER_SIZE}. "
                    f"Check Data Out settings."
                )
            return

        ts = datetime.now().strftime("%H:%M:%S")
        speed = parsed.get("speed_mph", 0)
        gear  = parsed.get("gear", parsed.get("current_engine_rpm", "?"))
        rpm   = parsed.get("rpm", parsed.get("current_engine_rpm", 0))
        ptype = parsed.get("_packet_type", "telemetry")
        _debug_push(f"{ts} [UDP OK]  {self.game} {len(data)}B  {speed:.0f}mph  rpm={rpm:.0f}  gear={gear}  type={ptype}")

        driving = _is_driving(parsed)

        if self.game not in active_sessions:
            if not driving:
                return  # don't create a session from an idle broadcast
            session = Session(self.game, datetime.now())
            active_sessions[self.game] = session
            if self.game == "forza_motorsport":
                fmt_label = "FH5 (331-byte, track ordinal available)" if len(data) == FM_PACKET_SIZE_FH else "FM2023 (311-byte, no track in UDP)"
                log.info(f"Forza packet format detected: {fmt_label}")

        session = active_sessions[self.game]

        if not driving:
            session.last_packet = time.time()
            ptype = parsed.get("_packet_type")
            # F1 Motion / MotionEx — always cache so next driving telemetry sees slip data
            if ptype == "motion":
                session._motion_cache.update(
                    {k: v for k, v in parsed.items() if not k.startswith("_") and v is not None}
                )
            # F1 LapData — cache for merging into next telemetry packet
            elif ptype == "lap_data":
                session._lap_cache.update(
                    {k: v for k, v in parsed.items() if not k.startswith("_") and v is not None}
                )
                rp = parsed.get("race_position")
                if rp is not None and rp > 0:
                    session._race_positions.append(rp)
            # ACC Graphics — update session metadata (ingest() never called for non-driving packets)
            elif ptype == "graphics":
                st = parsed.get("session_type", "unknown")
                if st and st != "unknown":
                    session.session_type = st
                rp = parsed.get("race_position")
                if rp is not None and rp > 0:
                    session._race_positions.append(rp)
            update_state(self.game, session, parsed)
            return  # don't record idle packets as lap samples

        # Pre-merge motion and lap caches so both ingest() and update_state() see the data.
        # ingest() does the same merges internally but they're local rebinds, not visible here.
        if parsed.get("_packet_type") == "telemetry":
            if session._motion_cache:
                parsed = {**parsed, **session._motion_cache}
                session._motion_cache = {}
            if session._lap_cache:
                parsed = {**session._lap_cache, **parsed}  # telemetry fields take precedence
                session._lap_cache = {}

        session.ingest(data, parsed)
        update_state(self.game, session, parsed)

    def error_received(self, exc):
        log.error(f"[{self.game}] UDP error: {exc}")

    def connection_lost(self, exc):
        log.warning(f"[{self.game}] Connection lost: {exc}")

# ─── Session Watchdog ─────────────────────────────────────────────────────────

async def _clear_race_ended():
    await asyncio.sleep(30)
    # Only clear if still showing race_ended AND no sessions went live in the meantime
    if state["status"] == "race_ended" and not active_sessions:
        state["status"] = "idle"


async def session_watchdog():
    while True:
        await asyncio.sleep(2)
        to_close = []
        for game, session in active_sessions.items():
            if session.is_timed_out():
                to_close.append((game, "no packets"))
            elif session.is_idle_timed_out():
                to_close.append((game, "idle"))
        for game, reason in to_close:
            session = active_sessions.pop(game)
            log.info(f"[{game}] Closing session — {reason} for >{IDLE_TIMEOUT_S if reason == 'idle' else SESSION_TIMEOUT_S}s")
            session.close()
            if not active_sessions:
                state["status"] = "race_ended"
                state["game"]   = None
                state["session_id"] = None
                log.info("All sessions closed. Listening...")
                asyncio.create_task(_clear_race_ended())

# ─── Admin Packet Injection ───────────────────────────────────────────────────

def _build_inject_packets(game: str, p: dict) -> list:
    return _build_inject_packets_core(game, p, FM_FORMAT)

# ─── Local Status Server ──────────────────────────────────────────────────────

# Single source of truth for design tokens — injected into every page's <style>
_CSS_TOKENS = """
:root {
  /* Typography */
  --font-mono: 'DM Mono', 'Fira Mono', 'Courier New', monospace;
  --text-xs: clamp(9px, 1.2vw, 11px);
  --text-sm: clamp(11px, 1.5vw, 13px);
  --text-md: clamp(13px, 1.8vw, 15px);
  --text-lg: clamp(16px, 2.5vw, 20px);
  --text-xl: clamp(24px, 4vw, 36px);
  --text-2xl: clamp(36px, 6vw, 56px);
  --fw-normal: 400;
  --fw-medium: 500;
  --fw-bold: 700;
  --fw-black: 900;

  /* Colours */
  --color-bg: #0a0a0a;
  --color-surface: #111111;
  --color-surface-2: #161616;
  --color-border: #1e1e1e;
  --color-border-subtle: #141414;
  --color-text-primary: #ffffff;
  --color-text-secondary: lightgrey;
  --color-text-muted: lightgrey;
  --color-text-dim: lightgrey;
  --color-accent: #e8b84b;
  --color-green: #4ade80;
  --color-red: #f87171;
  --color-blue: #60a5fa;
  --color-amber: #fbbf24;

  /* Spacing */
  --space-1: clamp(4px, 0.5vw, 6px);
  --space-2: clamp(8px, 1vw, 12px);
  --space-3: clamp(12px, 1.5vw, 16px);
  --space-4: clamp(16px, 2vw, 24px);
  --space-6: clamp(24px, 3vw, 36px);
  --space-8: clamp(32px, 4vw, 48px);

  /* Dashboard specific */
  --dash-label-size: clamp(10px, 1.8vw, 14px);
  --dash-value-size: clamp(28px, 6vw, 56px);
  --dash-stat-size: clamp(11px, 1.5vw, 13px);
  --dash-bottom-size: clamp(14px, 2.5vw, 20px);
  --dash-gear-size: clamp(40px, 8vw, 72px);
  --dash-speed-size: clamp(28px, 5vw, 48px);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  /* Legacy aliases — keep old names resolving to new tokens */
  --bg:           var(--color-bg);
  --bg-page:      var(--color-bg);
  --bg-raised:    var(--color-surface);
  --bg-surface:   var(--color-surface);
  --bg-overlay:   #03030a;
  --surface:      var(--color-surface-2);
  --surface-bd:   #2a2a3a;
  --border:       var(--color-border);
  --border-sub:   var(--color-border-subtle);
  --border-faint: #0e0e0e;
  --text:         var(--color-text-primary);
  --text-head:    var(--color-text-primary);
  --text-label:   var(--color-text-secondary);
  --text-muted:   var(--color-text-secondary);
  --text-dim:     var(--color-text-muted);
  --text-ghost:   var(--color-text-dim);
  --accent:       var(--color-accent);
  --accent-soft:  var(--color-green);
  --accent-bg:    #4ade8018;
  --accent-bd:    #4ade8044;
  --accent-bd2:   #4ade8088;
  --danger:       var(--color-red);
  --danger-alpha: #f8717144;
  --danger-glow:  #ef000066;
  --warn:         var(--color-amber);
  --warn-bg:      #1a130a;
  --warn-bd:      #fbbf2444;
  --warn-bg2:     #fbbf2418;
  --info:         var(--color-blue);
  --n-900: #080808;
  --n-800: #111111;
  --n-700: #1a1a1a;
  --n-600: #2a2a2a;
  --n-500: var(--color-text-muted);
  --n-400: var(--color-text-secondary);
  --n-300: var(--color-text-secondary);
  --n-200: var(--color-text-secondary);
  --n-100: #aaaaaa;
  /* Text size scale — legacy aliases */
  --text-2xs: var(--text-xs);
  --text-val: var(--dash-value-size);
  /* Spacing — legacy aliases */
  --sp-1: var(--space-1);
  --sp-2: var(--space-2);
  --sp-3: var(--space-3);
  --sp-4: var(--space-4);
  --sp-5: clamp(20px, 2.5vw, 28px);
  --sp-6: var(--space-6);
}
"""

_PAGE_STYLE = '<link rel="stylesheet" href="/static/tokens.css"><link rel="stylesheet" href="/static/base.css">'








TRACK_DETAIL_HTML = TRACK_DETAIL_HTML_PRE + json.dumps(FM2023_TRACKS, ensure_ascii=False) + TRACK_DETAIL_HTML_POST


SESSION_DETAIL_HTML = SESSION_DETAIL_HTML_PRE + json.dumps(FM2023_TRACKS, ensure_ascii=False) + SESSION_DETAIL_HTML_POST


# ─── AI Analysis ──────────────────────────────────────────────────────────────


def _build_analysis_prompt(session: dict, laps: list, historical: list,
                           prev_analyses=None) -> str:
    return _build_analysis_prompt_core(session, laps, historical,
                                       storage_path() / "sessions", prev_analyses)


def _call_claude_api(prompt: str) -> str:
    return _call_claude_api_core(
        prompt,
        config.get("anthropic_api_key", "").strip(),
        config.get("anthropic_model", "claude-sonnet-4-6").strip(),
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main(demo_mode: bool = False):
    global _listener_started_at
    _listener_started_at = time.time()
    _started_at[0] = _listener_started_at
    ensure_storage()
    _db_initialize(_DEMO_DB_PATH_REF, storage_path, FORZA_TRACKS, FORZA_CARS, log)
    _db_init()
    _load_forza_reference_data()
    _db_cull_ghost_sessions()
    _db_backfill_track_names()
    threading.Thread(target=_backfill_lap_samples, daemon=True).start()
    log.info("Pacefinder listener starting%s...", " [DEMO MODE]" if demo_mode else "")

    loop = asyncio.get_event_loop()

    if not demo_mode:
        parsers = {
            "forza_motorsport": parse_forza,
            "acc":              parse_acc,
            "f1":               parse_f1,
        }

        for game, port in PORTS.items():
            try:
                await loop.create_datagram_endpoint(
                    lambda g=game, p=parsers[game]: TelemetryProtocol(g, p),
                    local_addr=("0.0.0.0", port),
                )
                state["bound_ports"][game] = port
                log.info(f"Listening for {game} on UDP port {port}")
            except OSError as e:
                log.error(f"Failed to bind {game} on port {port}: {e} — F1/ACC/Forza port conflict?")

        asyncio.create_task(session_watchdog())

    _ctx = {
        "state": state,
        "config": config,
        "log": log,
        "PORTS": PORTS,
        "active_sessions": active_sessions,
        "debug_clients": _debug_clients,
        "debug_buffer": _debug_buffer,
        "started_at": _started_at,
        "static_dir": Path(__file__).parent / "static",
        "DASHBOARD_HTML": DASHBOARD_HTML,
        "SETUP_HTML": SETUP_HTML,
        "ADMIN_HTML": ADMIN_HTML,
        "GAMES_HTML": GAMES_HTML,
        "TRACKS_HTML": TRACKS_HTML,
        "TRACK_DETAIL_HTML": TRACK_DETAIL_HTML,
        "SESSION_DETAIL_HTML": SESSION_DETAIL_HTML,
        "TELEMETRY_HTML": TELEMETRY_HTML,
        "get_local_ips": _get_local_ips,
        "disk_info": disk_info,
        "save_config": save_config,
        "storage_path": storage_path,
        "effective_tracks": _effective_tracks,
        "FORZA_CARS": FORZA_CARS,
        "db_sessions_list": _db_sessions_list,
        "db_games_index": _db_games_index,
        "db_career_kpis": _db_career_kpis,
        "db_form_data": _db_form_data,
        "db_recent_sessions": _db_recent_sessions,
        "db_tracks_index": _db_tracks_index,
        "db_track_sessions": _db_track_sessions,
        "db_get_track_tip": _db_get_track_tip,
        "db_save_track_tip": _db_save_track_tip,
        "build_track_tip_prompt": _build_track_tip_prompt,
        "call_claude_api": _call_claude_api,
        "db_connect": _db_connect,
        "db_lock": _db_lock,
        "db_get_ai_analysis": _db_get_ai_analysis,
        "db_save_ai_analysis": _db_save_ai_analysis,
        "db_update_session": _db_update_session,
        "db_drop_last_lap": _db_drop_last_lap,
        "db_write_learned_ordinal": _db_write_learned_ordinal,
        "db_get_lap_samples": _db_get_lap_samples,
        "build_inject_packets": _build_inject_packets,
        "build_analysis_prompt": _build_analysis_prompt,
        "clear_race_ended": _clear_race_ended,
    }
    handle_status = make_handler(_ctx)

    server = await asyncio.start_server(handle_status, "0.0.0.0", STATUS_PORT)
    log.info(f"Storage path: {storage_path()}")
    log.info(f"Dashboard at http://localhost:{STATUS_PORT}/")
    log.info(f"Setup     at http://localhost:{STATUS_PORT}/setup")
    log.info(f"Admin     at http://localhost:{STATUS_PORT}/admin")
    log.info(f"Status API at http://localhost:{STATUS_PORT}/status")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    import argparse as _argparse
    _parser = _argparse.ArgumentParser(description="Pacefinder listener")
    _parser.add_argument("--demo", action="store_true",
                         help="Demo mode: skip UDP listeners, serve HTTP only")
    _parser.add_argument("--db", type=str, default=None,
                         help="Path to SQLite database file (used with --demo)")
    _parser.add_argument("--port", type=int, default=None,
                         help="HTTP server port (overrides config/default)")
    _args = _parser.parse_args()

    if _args.demo and _args.db:
        _DEMO_DB_PATH_REF[0] = _args.db
    if _args.port:
        STATUS_PORT = _args.port

    asyncio.run(main(demo_mode=_args.demo))
