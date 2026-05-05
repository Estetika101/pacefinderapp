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
import sqlite3
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
_DEMO_DB_PATH: Optional[str] = None  # set by --demo flag; overrides storage_path()/simtelemetry.db

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

FM_PACKET_SIZE    = 311  # Forza Motorsport 2023 / FM7 Car Dash
FM_PACKET_SIZE_FH = 331  # Forza Horizon 4 / 5 Car Dash (adds tire wear + track ordinal)

# Populated by _load_forza_reference_data() at startup.
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


# i I [51×f] [5×i: car_ordinal/class/pi/drivetrain/cylinders] [17×f] H [6×B] [3×b]
# drivetrain_type and num_cylinders are int32 per spec, not float.
FM_FORMAT    = "<iIfffffffffffffffffffffffffffffffffffffffffffffffffffiiiiifffffffffffffffffHBBBBBBbbb"
# FH4/FH5 appends: tireWearFL tireWearFR tireWearRL tireWearRR (4f) + trackOrdinal (i)
FM_FORMAT_FH = FM_FORMAT + "ffffi"

FM_FIELDS = [
    "is_race_on", "timestamp_ms",
    "engine_max_rpm", "engine_idle_rpm", "current_engine_rpm",
    "acceleration_x", "acceleration_y", "acceleration_z",
    "velocity_x", "velocity_y", "velocity_z",
    "angular_velocity_x", "angular_velocity_y", "angular_velocity_z",
    "yaw", "pitch", "roll",
    "normalized_suspension_travel_fl", "normalized_suspension_travel_fr",
    "normalized_suspension_travel_rl", "normalized_suspension_travel_rr",
    "tire_slip_ratio_fl", "tire_slip_ratio_fr",
    "tire_slip_ratio_rl", "tire_slip_ratio_rr",
    "wheel_rotation_speed_fl", "wheel_rotation_speed_fr",
    "wheel_rotation_speed_rl", "wheel_rotation_speed_rr",
    "wheel_on_rumble_strip_fl", "wheel_on_rumble_strip_fr",
    "wheel_on_rumble_strip_rl", "wheel_on_rumble_strip_rr",
    "wheel_in_puddle_fl", "wheel_in_puddle_fr",
    "wheel_in_puddle_rl", "wheel_in_puddle_rr",
    "surface_rumble_fl", "surface_rumble_fr",
    "surface_rumble_rl", "surface_rumble_rr",
    "tire_slip_angle_fl", "tire_slip_angle_fr",
    "tire_slip_angle_rl", "tire_slip_angle_rr",
    "tire_combined_slip_fl", "tire_combined_slip_fr",
    "tire_combined_slip_rl", "tire_combined_slip_rr",
    "suspension_travel_meters_fl", "suspension_travel_meters_fr",
    "suspension_travel_meters_rl", "suspension_travel_meters_rr",
    "car_ordinal", "car_class", "car_performance_index",
    "drivetrain_type", "num_cylinders",
    "position_x", "position_y", "position_z",
    "speed", "power", "torque",
    "tire_temp_fl", "tire_temp_fr", "tire_temp_rl", "tire_temp_rr",
    "boost", "fuel", "distance_traveled",
    "best_lap_time", "last_lap_time", "current_lap_time",
    "current_race_time",
    "lap_number", "race_position",
    "accel", "brake", "clutch", "handbrake",
    "gear", "steer",
    "normalized_driving_lane", "normalized_ai_brake_difference",
]

def parse_forza(data: bytes) -> Optional[dict]:
    if len(data) == FM_PACKET_SIZE_FH:
        fmt = FM_FORMAT_FH
    elif len(data) == FM_PACKET_SIZE:
        fmt = FM_FORMAT
    else:
        return None
    try:
        values = struct.unpack(fmt, data)
        parsed = dict(zip(FM_FIELDS, values))
        if not parsed.get("is_race_on"):
            return None  # race not active — values are stale/garbage
        if len(data) == FM_PACKET_SIZE_FH:
            parsed["tire_wear_fl"]  = values[len(FM_FIELDS)]
            parsed["tire_wear_fr"]  = values[len(FM_FIELDS) + 1]
            parsed["tire_wear_rl"]  = values[len(FM_FIELDS) + 2]
            parsed["tire_wear_rr"]  = values[len(FM_FIELDS) + 3]
            ord_val                 = values[len(FM_FIELDS) + 4]
            parsed["track_ordinal"] = ord_val
            track_name = _effective_tracks().get(ord_val)
            if ord_val and track_name is None and ord_val not in _unknown_ordinals_seen:
                _unknown_ordinals_seen.add(ord_val)
                log.warning(f"Unknown FH5 track ordinal {ord_val} — add to FORZA_TRACKS once identified")
            parsed["track"] = track_name if track_name else (f"Track #{ord_val}" if ord_val else "unknown")
        else:
            parsed["track"] = "unknown"  # FM2023 doesn't broadcast track in telemetry
        parsed["speed_mph"]      = parsed["speed"] * 2.237
        parsed["throttle_pct"]   = parsed["accel"] / 255 * 100
        parsed["brake_pct"]      = parsed["brake"] / 255 * 100
        parsed["clutch_pct"]     = parsed["clutch"] / 255 * 100
        parsed["slip_ratio_fl"]  = abs(parsed["tire_slip_ratio_fl"])
        parsed["slip_ratio_fr"]  = abs(parsed["tire_slip_ratio_fr"])
        parsed["slip_ratio_rl"]  = abs(parsed["tire_slip_ratio_rl"])
        parsed["slip_ratio_rr"]  = abs(parsed["tire_slip_ratio_rr"])
        parsed["g_lat"]          = parsed["acceleration_x"] / 9.81
        parsed["g_lon"]          = parsed["acceleration_z"] / 9.81
        return parsed
    except struct.error:
        return None

# ─── ACC Parser ───────────────────────────────────────────────────────────────
# ACC UDP plugin physics packet
# Full struct reference: https://www.assettocorsa.net/forum/index.php?threads/acc-udp-remote-telemetry-port.59734/

ACC_PHYSICS_SIZE = 328  # v1.7+ physics packet size

_ACC_SESSION_TYPES = {
    0: "unknown", 1: "practice", 2: "qualifying", 3: "qualifying",
    4: "race", 5: "time_trial", 6: "time_trial",
    7: "unknown", 8: "unknown", 9: "practice", 10: "qualifying",
}

def parse_acc(data: bytes) -> Optional[dict]:
    """Parse ACC physics (packetId=0) or graphics (packetId=1) packet."""
    if len(data) < 4:
        return None
    try:
        packet_id = struct.unpack_from("<i", data, 0)[0]
        if packet_id == 1:
            # Graphics packet: session type at offset 8, race position at offset 136
            if len(data) < 140:
                return None
            session_int = struct.unpack_from("<i", data, 8)[0]
            position    = struct.unpack_from("<i", data, 136)[0]
            result: dict = {
                "_packet_type": "graphics",
                "session_type": _ACC_SESSION_TYPES.get(session_int, "unknown"),
                "race_position": position if position > 0 else None,
            }
            # rainIntensity enum at offset 1552 (added in ACC 1.8 shared memory)
            if len(data) >= 1556:
                rain_int = struct.unpack_from("<i", data, 1552)[0]
                _ACC_RAIN = {0: "Clear", 1: "LightCloud", 2: "LightRain",
                             3: "Rain", 4: "HeavyRain", 5: "Thunderstorm"}
                w = _ACC_RAIN.get(rain_int)
                if w is not None:
                    result["weather_condition"] = w
            return result
        if packet_id != 0:
            return None  # Static or unknown packet — ignore
    except struct.error:
        return None
    try:
        o = 0
        def ri(fmt):
            nonlocal o
            val = struct.unpack_from(fmt, data, o)
            o += struct.calcsize(fmt)
            return val[0] if len(val) == 1 else val

        packet_id = ri("<i")
        gas       = ri("<f")
        brake     = ri("<f")
        fuel      = ri("<f")
        gear      = ri("<i")
        rpm       = ri("<i")
        steer     = ri("<f")
        speed_kmh = ri("<f")
        vel_x, vel_y, vel_z = ri("<fff")
        acc_x, acc_y, acc_z = ri("<fff")  # G-forces (m/s²)
        slip_fl, slip_fr, slip_rl, slip_rr = ri("<ffff")

        # wheelSlip done — continue with more fields if packet is large enough
        result = {
            "packet_id":    packet_id,
            "throttle_pct": round(gas * 100, 1),
            "brake_pct":    round(brake * 100, 1),
            "fuel":         round(fuel, 2),
            "gear":         gear,
            "rpm":          rpm,
            "steer":        round(steer, 3),
            "speed_mph":    round(speed_kmh * 0.621371, 1),
            "velocity_x":   round(vel_x, 3),
            "velocity_y":   round(vel_y, 3),
            "velocity_z":   round(vel_z, 3),
            "g_lat":        round(acc_x / 9.81, 3),
            "g_lon":        round(acc_z / 9.81, 3),
            "g_vert":       round(acc_y / 9.81, 3),
            "slip_ratio_fl": round(abs(slip_fl), 4),
            "slip_ratio_fr": round(abs(slip_fr), 4),
            "slip_ratio_rl": round(abs(slip_rl), 4),
            "slip_ratio_rr": round(abs(slip_rr), 4),
        }

        # Extended fields: wheelsPressure(4f), brakeTemp(4f), tyreCoreTemp(4f)
        if len(data) >= o + 48:
            slip_angle_fl, slip_angle_fr, slip_angle_rl, slip_angle_rr = ri("<ffff")
            slip_speed_fl, slip_speed_fr, slip_speed_rl, slip_speed_rr = ri("<ffff")
            slip_speed2_fl, slip_speed2_fr, slip_speed2_rl, slip_speed2_rr = ri("<ffff")

        if len(data) >= o + 32:
            p_fl, p_fr, p_rl, p_rr = ri("<ffff")
            b_fl, b_fr, b_rl, b_rr = ri("<ffff")
            result["tyre_pressure_fl"] = round(p_fl, 2)
            result["tyre_pressure_fr"] = round(p_fr, 2)
            result["tyre_pressure_rl"] = round(p_rl, 2)
            result["tyre_pressure_rr"] = round(p_rr, 2)
            result["brake_temp_fl"]    = round(b_fl, 1)
            result["brake_temp_fr"]    = round(b_fr, 1)
            result["brake_temp_rl"]    = round(b_rl, 1)
            result["brake_temp_rr"]    = round(b_rr, 1)

        if len(data) >= o + 16:
            t_fl, t_fr, t_rl, t_rr = ri("<ffff")
            result["tyre_core_temp_fl"] = round(t_fl, 1)
            result["tyre_core_temp_fr"] = round(t_fr, 1)
            result["tyre_core_temp_rl"] = round(t_rl, 1)
            result["tyre_core_temp_rr"] = round(t_rr, 1)

        # airTemp at byte 288, roadTemp at byte 292 (fixed offsets in SPageFilePhysics)
        if len(data) >= 296:
            air_t  = struct.unpack_from("<f", data, 288)[0]
            road_t = struct.unpack_from("<f", data, 292)[0]
            if -50 < air_t < 80:   # sanity range
                result["air_temp_c"]   = round(air_t, 1)
            if -10 < road_t < 100:
                result["track_temp_c"] = round(road_t, 1)

        return result
    except struct.error:
        return None

# ─── F1 Parser ────────────────────────────────────────────────────────────────
# Codemasters F1 UDP format (F1 2023/2024)
# Header: packetFormat(H), gameYear(B), gameMajorVersion(B), gameMinorVersion(B),
#         packetVersion(B), packetId(B), sessionUID(Q), sessionTime(f),
#         frameIdentifier(I), playerCarIndex(B), secondaryPlayerCarIndex(B)
# Packet IDs: 0=Motion, 1=Session, 6=CarTelemetry, 7=CarStatus

F1_HEADER_SIZE = 29  # F1 2023/2024 header

# Track names by F1 track ID (F1 2023)
F1_TRACKS = {
    0: "Melbourne", 1: "Paul Ricard", 2: "Shanghai", 3: "Sakhir (Bahrain)",
    4: "Catalunya", 5: "Monaco", 6: "Montreal", 7: "Silverstone",
    8: "Hockenheim", 9: "Hungaroring", 10: "Spa", 11: "Monza",
    12: "Singapore", 13: "Suzuka", 14: "Abu Dhabi", 15: "Texas",
    16: "Brazil", 17: "Austria", 18: "Sochi", 19: "Mexico",
    20: "Baku (Azerbaijan)", 21: "Sakhir Short", 22: "Silverstone Short",
    23: "Texas Short", 24: "Suzuka Short", 25: "Hanoi", 26: "Zandvoort",
    27: "Imola", 28: "Portimão", 29: "Jeddah", 30: "Miami",
    31: "Las Vegas", 32: "Losail",
}

# Per-session F1 state (track, session type) populated from packet ID 1
_f1_session_meta: dict = {}

def parse_f1(data: bytes) -> Optional[dict]:
    """Dispatch F1 packets by ID; return unified dict for telemetry packets."""
    if len(data) < 24:  # minimum valid header (F1 2023)
        return None
    try:
        # Detect game year from packetFormat field (uint16 @ 0): 2023 or 2024
        packet_format = struct.unpack_from("<H", data, 0)[0]
        is_2024 = (packet_format >= 2024)
        # F1 2023: 24-byte header, playerCarIndex @ 23
        # F1 2024: 29-byte header, playerCarIndex @ 27
        hdr      = 29 if is_2024 else 24
        pidx_off = 27 if is_2024 else 23

        packet_id   = struct.unpack_from("<B", data, 6)[0]
        session_uid = struct.unpack_from("<Q", data, 7)[0]

        if packet_id == 1:
            # Session — extract track, session type, weather, temperatures
            # layout: weather(B) trackTemp(b) airTemp(b) totalLaps(B) trackLength(H) sessionType(B) trackId(b)
            base = hdr
            if len(data) >= base + 8:
                weather_val  = struct.unpack_from("<B", data, base + 0)[0]
                track_temp   = struct.unpack_from("<b", data, base + 1)[0]
                air_temp     = struct.unpack_from("<b", data, base + 2)[0]
                session_type = struct.unpack_from("<B", data, base + 6)[0]
                track_id     = struct.unpack_from("<b", data, base + 7)[0]
                session_types = {
                    0: "unknown",
                    1: "practice", 2: "practice", 3: "practice", 4: "practice",
                    5: "qualifying", 6: "qualifying", 7: "qualifying",
                    8: "qualifying", 9: "qualifying",
                    10: "race", 11: "race", 12: "race",
                    13: "time_trial",
                }
                _F1_WEATHER = {0: "Clear", 1: "LightCloud", 2: "Overcast",
                               3: "LightRain", 4: "HeavyRain", 5: "Thunderstorm"}
                _f1_session_meta[session_uid] = {
                    "track":             F1_TRACKS.get(track_id, f"track_{track_id}"),
                    "session_type":      session_types.get(session_type, "unknown"),
                    "weather_condition": _F1_WEATHER.get(weather_val),
                    "track_temp_c":      float(track_temp) if -10 <= track_temp <= 100 else None,
                    "air_temp_c":        float(air_temp)   if -50 <= air_temp <= 80  else None,
                }
            return None

        if packet_id == 2:
            # LapData — lap number, times, position
            # F1 2024 per-car: 50 bytes  |  F1 2023 per-car: 43 bytes
            if is_2024:
                car_size     = 50
                off_last_lap = 0   # uint32 lastLapTimeInMS
                off_cur_lap  = 4   # uint32 currentLapTimeInMS
                off_pos      = 30  # uint8 carPosition
                off_lap_num  = 31  # uint8 currentLapNum
                off_grid_pos = 41  # uint8 gridPosition
            else:
                car_size     = 43
                off_last_lap = 0
                off_cur_lap  = 4
                off_pos      = 24
                off_lap_num  = 25
                off_grid_pos = 34
            player_idx = struct.unpack_from("<B", data, pidx_off)[0]
            base = hdr + player_idx * car_size
            if len(data) < base + car_size:
                return None
            last_lap_ms = struct.unpack_from("<I", data, base + off_last_lap)[0]
            cur_lap_ms  = struct.unpack_from("<I", data, base + off_cur_lap)[0]
            car_pos     = struct.unpack_from("<B", data, base + off_pos)[0]
            cur_lap_num = struct.unpack_from("<B", data, base + off_lap_num)[0]
            grid_pos    = struct.unpack_from("<B", data, base + off_grid_pos)[0]
            return {
                "_packet_type":     "lap_data",
                "_session_uid":     session_uid,
                "lap_number":       cur_lap_num,
                "current_lap_time": round(cur_lap_ms / 1000, 3) if cur_lap_ms < 600_000 else None,
                "last_lap_time":    round(last_lap_ms / 1000, 3) if 0 < last_lap_ms < 600_000 else None,
                "race_position":    car_pos,
                "grid_position":    grid_pos,
            }

        if packet_id == 0:
            # Motion — g-forces and velocity for player car
            # per-car: worldPos(3f) worldVel(3f) worldForwardDir(3H) worldRightDir(3H)
            #          gForceLateral(f) gForceLongitudinal(f) gForceVertical(f) yaw(f) pitch(f) roll(f)
            player_idx = struct.unpack_from("<B", data, pidx_off)[0]
            car_size = 60
            base = hdr + player_idx * car_size
            if len(data) < base + car_size:
                return None
            pos_x, pos_y, pos_z = struct.unpack_from("<fff", data, base)
            vel_x, vel_y, vel_z = struct.unpack_from("<fff", data, base + 12)
            g_lat  = struct.unpack_from("<f", data, base + 36)[0]
            g_lon  = struct.unpack_from("<f", data, base + 40)[0]
            g_vert = struct.unpack_from("<f", data, base + 44)[0]
            result = {
                "_packet_type": "motion",
                "_session_uid": session_uid,
                "position_x": round(pos_x, 2),
                "position_y": round(pos_y, 2),
                "position_z": round(pos_z, 2),
                "velocity_x": round(vel_x, 2),
                "velocity_y": round(vel_y, 2),
                "velocity_z": round(vel_z, 2),
                "g_lat":  round(g_lat, 3),
                "g_lon":  round(g_lon, 3),
                "g_vert": round(g_vert, 3),
            }
            # F1 2023: wheelSlip appended at end of Motion packet after all 22 cars
            # layout at tail: suspPos(4f) suspVel(4f) suspAcc(4f) wheelSpeed(4f) wheelSlip(4f) ...
            if not is_2024:
                slip_base = hdr + 22 * car_size + 64  # 64 = 4×4f before wheelSlip
                if len(data) >= slip_base + 16:
                    s_fl, s_fr, s_rl, s_rr = struct.unpack_from("<ffff", data, slip_base)
                    result["slip_ratio_fl"] = round(abs(s_fl), 4)
                    result["slip_ratio_fr"] = round(abs(s_fr), 4)
                    result["slip_ratio_rl"] = round(abs(s_rl), 4)
                    result["slip_ratio_rr"] = round(abs(s_rr), 4)
            return result

        if packet_id == 13:
            # MotionEx (F1 2024 only) — per-player extra motion including wheelSlip
            # layout: suspPos(4f) suspVel(4f) suspAcc(4f) wheelSpeed(4f) wheelSlip(4f) ...
            # wheelSlip order: FL=0, FR=1, RL=2, RR=3
            slip_base = hdr + 64  # 4 × 16 bytes before wheelSlip
            if len(data) < slip_base + 16:
                return None
            s_fl, s_fr, s_rl, s_rr = struct.unpack_from("<ffff", data, slip_base)
            return {
                "_packet_type":  "motion",
                "_session_uid":  session_uid,
                "slip_ratio_fl": round(abs(s_fl), 4),
                "slip_ratio_fr": round(abs(s_fr), 4),
                "slip_ratio_rl": round(abs(s_rl), 4),
                "slip_ratio_rr": round(abs(s_rr), 4),
            }

        if packet_id == 6:
            # CarTelemetry — speed, inputs, tyres, engine
            # per-car (60 bytes): speed(H) throttle(f) steer(f) brake(f) clutch(B)
            #   gear(b) engineRPM(H) drs(B) revLightsPercent(B) revLightsBitValue(H)
            #   brakesTemp(4H) tyresSurfaceTemp(4B) tyresInnerTemp(4B)
            #   engineTemp(H) tyresPressure(4f) surfaceType(4B)
            player_idx = struct.unpack_from("<B", data, pidx_off)[0]
            car_size = 60
            base = hdr + player_idx * car_size
            if len(data) < base + car_size:
                return None
            speed    = struct.unpack_from("<H", data, base)[0]
            throttle = struct.unpack_from("<f", data, base + 2)[0]
            steer    = struct.unpack_from("<f", data, base + 6)[0]
            brake    = struct.unpack_from("<f", data, base + 10)[0]
            clutch   = struct.unpack_from("<B", data, base + 14)[0]
            gear     = struct.unpack_from("<b", data, base + 15)[0]
            rpm      = struct.unpack_from("<H", data, base + 16)[0]
            drs      = struct.unpack_from("<B", data, base + 18)[0]
            # drs@18 + revLightsPercent(B)@19 + revLightsBitValue(H)@20 → brake temps at +22
            bt_rl, bt_rr, bt_fl, bt_fr = struct.unpack_from("<HHHH", data, base + 22)
            ts_rl, ts_rr, ts_fl, ts_fr = struct.unpack_from("<BBBB", data, base + 30)
            ti_rl, ti_rr, ti_fl, ti_fr = struct.unpack_from("<BBBB", data, base + 34)
            engine_temp = struct.unpack_from("<H", data, base + 38)[0]
            tp_rl, tp_rr, tp_fl, tp_fr = struct.unpack_from("<ffff", data, base + 40)
            meta = _f1_session_meta.get(session_uid, {})
            ret: dict = {
                "_packet_type":         "telemetry",
                "_session_uid":         session_uid,
                "track":                meta.get("track", "unknown"),
                "session_type":         meta.get("session_type", "unknown"),
                "speed_mph":            round(speed * 0.621371, 1),
                "throttle_pct":         round(throttle * 100, 1),
                "brake_pct":            round(brake * 100, 1),
                "clutch_pct":           round(clutch / 255 * 100, 1),
                "steer":                round(steer, 3),
                "gear":                 gear,
                "rpm":                  rpm,
                "drs":                  bool(drs),
                "brake_temp_fl":        bt_fl,
                "brake_temp_fr":        bt_fr,
                "brake_temp_rl":        bt_rl,
                "brake_temp_rr":        bt_rr,
                "tyre_surface_temp_fl": ts_fl,
                "tyre_surface_temp_fr": ts_fr,
                "tyre_surface_temp_rl": ts_rl,
                "tyre_surface_temp_rr": ts_rr,
                "tyre_inner_temp_fl":   ti_fl,
                "tyre_inner_temp_fr":   ti_fr,
                "tyre_inner_temp_rl":   ti_rl,
                "tyre_inner_temp_rr":   ti_rr,
                "tyre_pressure_fl":     round(tp_fl, 2),
                "tyre_pressure_fr":     round(tp_fr, 2),
                "tyre_pressure_rl":     round(tp_rl, 2),
                "tyre_pressure_rr":     round(tp_rr, 2),
                "engine_temp":          engine_temp,
            }
            # Carry weather/temp from session packet into each telemetry sample
            for k in ("weather_condition", "track_temp_c", "air_temp_c"):
                v = meta.get(k)
                if v is not None:
                    ret[k] = v
            return ret

        if packet_id == 7:
            # CarStatus — fuel, tyre compound
            # per-car (47 bytes): tractionControl(B) antiLockBrakes(B) fuelMix(B)
            #   frontBrakeBias(B) pitLimiterStatus(B) fuelInTank(f) fuelCapacity(f)
            #   fuelRemainingLaps(f) maxRPM(H) idleRPM(H) maxGears(B) drsAllowed(B)
            #   drsActivationDistance(H) actualTyreCompound(B) visualTyreCompound(B) tyresAgeLaps(B)
            player_idx = struct.unpack_from("<B", data, pidx_off)[0]
            car_size = 47
            base = hdr + player_idx * car_size
            if len(data) < base + car_size:
                return None
            fuel_in_tank        = struct.unpack_from("<f", data, base + 5)[0]
            fuel_remaining_laps = struct.unpack_from("<f", data, base + 13)[0]
            tyre_compound       = struct.unpack_from("<B", data, base + 23)[0]
            tyre_age_laps       = struct.unpack_from("<B", data, base + 25)[0]
            compounds = {16: "C5", 17: "C4", 18: "C3", 19: "C2", 20: "C1",
                         21: "C0", 7: "Inter", 8: "Wet", 9: "Wet"}
            return {
                "_packet_type":        "car_status",
                "_session_uid":        session_uid,
                "fuel_in_tank":        round(fuel_in_tank, 2),
                "fuel_remaining_laps": round(fuel_remaining_laps, 1),
                "tyre_compound":       compounds.get(tyre_compound, f"compound_{tyre_compound}"),
                "tyre_age_laps":       tyre_age_laps,
            }

        return None
    except struct.error:
        return None

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
    """Build valid UDP telemetry packets from user-friendly params."""
    speed_mph = float(p.get("speed_mph", 0))
    throttle  = max(0.0, min(100.0, float(p.get("throttle_pct", 0))))
    brake     = max(0.0, min(100.0, float(p.get("brake_pct", 0))))
    rpm       = float(p.get("rpm", 1000))
    gear      = int(p.get("gear", 1))
    lap       = int(p.get("lap", 1))

    if game == "forza_motorsport":
        speed_ms = speed_mph / 2.237
        vals = [
            1, 0,                                                  # is_race_on, timestamp_ms
            8500.0, 800.0, rpm,                                    # engine max/idle/current rpm
            0.0, 0.0, 0.0,                                         # accel xyz
            speed_ms, 0.0, 0.0,                                    # velocity xyz
            0.0, 0.0, 0.0,                                         # angular velocity
            0.0, 0.0, 0.0,                                         # yaw pitch roll
            0.5, 0.5, 0.5, 0.5,                                    # norm suspension travel x4
            0.0, 0.0, max(0.0,(speed_mph-20)/300), max(0.0,(speed_mph-20)/280),  # tire slip ratio x4
            speed_ms*4, speed_ms*4, speed_ms*4, speed_ms*4,        # wheel rotation speed x4
            0.0, 0.0, 0.0, 0.0,                                    # rumble strip x4
            0.0, 0.0, 0.0, 0.0,                                    # puddle x4
            0.0, 0.0, 0.0, 0.0,                                    # surface rumble x4
            0.0, 0.0, 0.0, 0.0,                                    # slip angle x4
            0.0, 0.0, 0.0, 0.0,                                    # combined slip x4
            0.1, 0.1, 0.1, 0.1,                                    # suspension travel meters x4
            42, 3, 750, 1, 6,                                      # car_ordinal/class/pi/drivetrain/cylinders
            0.0, 0.0, 0.0,                                         # position xyz
            speed_ms, 250000.0, 400.0,                             # speed, power, torque
            85.0, 85.0, 85.0, 85.0,                                # tire temp x4
            0.5, 0.6, 0.0,                                         # boost, fuel, distance
            0.0, 0.0, 0.0, 0.0,                                    # best/last/current lap / race time
            lap, 1,                                                # lap_number (H), race_position (B)
            int(throttle/100*255), int(brake/100*255), 0, 0, gear, # accel brake clutch handbrake gear
            0, 0, 0,                                               # steer, norm_driving_lane, norm_ai_brake
        ]
        return [struct.pack(FM_FORMAT, *vals)]

    if game == "acc":
        speed_kmh = speed_mph * 1.60934
        vals = [
            0,                            # packet_id
            throttle / 100,               # gas
            brake / 100,                  # brake
            50.0,                         # fuel
            gear,                         # gear
            int(rpm),                     # rpm
            0.0,                          # steer
            speed_kmh,                    # speed_kmh
            0.0, 0.0, speed_kmh / 3.6,   # vel xyz
            0.0, 0.0, 0.0,               # acc xyz
            0.0, 0.0, 0.0, 0.0,          # wheelSlip x4
        ]
        return [struct.pack("<ifffiiffffffffffff", *vals).ljust(200, b'\x00')]

    if game == "f1":
        speed_kmh = int(speed_mph * 1.60934)
        uid = 0xDEADCAFE
        def hdr(pid):
            # packetId at offset 6 (where parse_f1 reads it), packetVersion=1 at offset 5
            return struct.pack("<HBBBBBQfIIBB", 2024, 24, 1, 0, 1, pid, uid, 0.0, 0, 0, 0, 255)
        # Session packet — primes track/session_type meta
        sess = hdr(1) + struct.pack("<BbbBHBb", 0, 25, 20, 50, 5793, 10, 11)
        # CarTelemetry packet — speed, inputs, tyre temps
        car = struct.pack(
            "<HfffBbHBBH4H4B4BH4f4B",
            speed_kmh, throttle/100, 0.0, brake/100, 0, gear, int(rpm), 0, 0, 0,
            0, 0, 0, 0, 85, 85, 85, 85, 90, 90, 90, 90, 105,
            23.5, 23.5, 22.8, 22.8, 0, 0, 0, 0,
        ).ljust(60, b'\x00')
        # LapData packet — lap number and timing (offsets: lastLap@0 curLap@4 lapNum@31)
        lap_car = struct.pack("<II", 0, 15000)           # lastLap=0, curLap=15s
        lap_car += struct.pack("<HB", 0, 0)              # sector1
        lap_car += struct.pack("<HB", 0, 0)              # sector2
        lap_car += struct.pack("<II", 0, 0)              # deltas
        lap_car += struct.pack("<ff", 500.0, 5000.0)     # distances
        lap_car += struct.pack("<BB", 1, lap)            # carPosition=1, currentLapNum
        lap_car = lap_car.ljust(50, b'\x00')
        lapdata = hdr(2) + lap_car
        # MotionEx packet — wheelSlip at hdr+64 (fl/fr/rl/rr)
        slip_scale = max(0.0, (speed_mph - 20) / 150)   # gentle slip proportional to speed
        pre_slip = b'\x00' * 64
        slip_data = struct.pack("<ffff", slip_scale * 0.5, slip_scale * 0.5,
                                slip_scale, slip_scale * 1.1)
        motionex = hdr(13) + pre_slip + slip_data
        # Send car first to create the session, then motionex+lapdata to prime caches,
        # then car again so the second telemetry packet sees the merged slip+lap data.
        return [sess, hdr(6) + car, motionex, lapdata, hdr(6) + car]

    return []

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


# ─── SQLite Layer ─────────────────────────────────────────────────────────────

_db_lock = threading.Lock()

def _db_connect() -> sqlite3.Connection:
    db_path = Path(_DEMO_DB_PATH) if _DEMO_DB_PATH else storage_path() / "simtelemetry.db"
    conn = sqlite3.connect(str(db_path), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _db_init():
    with _db_lock:
        conn = _db_connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id       TEXT PRIMARY KEY,
                    game             TEXT,
                    track            TEXT,
                    car              TEXT,
                    session_type     TEXT,
                    race_type        TEXT,
                    started_at       TEXT,
                    ended_at         TEXT,
                    packet_count     INTEGER DEFAULT 0,
                    best_lap_time_s  REAL,
                    lap_count        INTEGER DEFAULT 0,
                    ai_analysis      TEXT,
                    ai_analyzed_at   TEXT,
                    ai_model         TEXT,
                    grid_pos         INTEGER,
                    finish_pos       INTEGER
                );
                CREATE TABLE IF NOT EXISTS laps (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id    TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                    lap_number    INTEGER,
                    lap_time_s    REAL,
                    max_speed_mph REAL,
                    sample_count  INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS track_tips (
                    track        TEXT PRIMARY KEY,
                    tip          TEXT,
                    generated_at TEXT,
                    model        TEXT
                );
                CREATE TABLE IF NOT EXISTS track_references (
                    track                      TEXT NOT NULL,
                    reference_type             TEXT NOT NULL,
                    session_id                 TEXT,
                    lap_number                 INTEGER,
                    samples_json               TEXT NOT NULL,
                    theoretical_s1_s           REAL,
                    theoretical_s1_session_id  TEXT,
                    theoretical_s1_lap         INTEGER,
                    theoretical_s2_s           REAL,
                    theoretical_s2_session_id  TEXT,
                    theoretical_s2_lap         INTEGER,
                    theoretical_s3_s           REAL,
                    theoretical_s3_session_id  TEXT,
                    theoretical_s3_lap         INTEGER,
                    theoretical_best_s         REAL,
                    updated_at                 TEXT,
                    PRIMARY KEY (track, reference_type)
                );
                CREATE TABLE IF NOT EXISTS lap_samples (
                    session_id    TEXT NOT NULL,
                    lap_number    INTEGER NOT NULL,
                    samples_json  TEXT NOT NULL,
                    distance_m_json TEXT NOT NULL,
                    created_at    TEXT,
                    PRIMARY KEY (session_id, lap_number)
                );
                CREATE TABLE IF NOT EXISTS learned_track_ordinals (
                    ordinal     INTEGER NOT NULL,
                    game        TEXT    NOT NULL,
                    track_name  TEXT    NOT NULL,
                    created_at  TEXT,
                    PRIMARY KEY (ordinal, game)
                );
                CREATE INDEX IF NOT EXISTS idx_laps_session  ON laps(session_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_track ON sessions(track);
                CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(started_at);
                CREATE INDEX IF NOT EXISTS idx_lap_samples_session ON lap_samples(session_id);
                CREATE INDEX IF NOT EXISTS idx_track_refs_track ON track_references(track);
            """)
            conn.commit()
            # Add columns introduced after initial schema — safe to re-run
            for col, defn in [
                ("grid_pos", "INTEGER"), ("finish_pos", "INTEGER"),
                ("track_ordinal", "INTEGER"), ("car_class", "INTEGER"), ("car_pi", "INTEGER"),
                ("weather_condition", "TEXT"), ("track_temp_c", "REAL"), ("air_temp_c", "REAL"),
                ("car_manufacturer", "TEXT"), ("car_year", "INTEGER"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {defn}")
                    conn.commit()
                except Exception:
                    pass
        finally:
            conn.close()
    _db_migrate()
    _db_backfill_race_types()

def _db_migrate():
    """Import existing session JSON files not yet in the database. Idempotent."""
    sessions_dir = storage_path() / "sessions"
    if not sessions_dir.exists():
        return
    imported = 0
    with _db_lock:
        conn = _db_connect()
        try:
            for f in sorted(sessions_dir.glob("*.json")):
                if f.name.endswith("_laps.json") or f.name.endswith("_analysis.json"):
                    continue
                try:
                    data = json.loads(f.read_text())
                    sid = data.get("session_id")
                    if not sid:
                        continue
                    if conn.execute("SELECT 1 FROM sessions WHERE session_id=?", (sid,)).fetchone():
                        continue
                    ai_text = ai_at = ai_model = None
                    af = sessions_dir / f"{sid}_analysis.json"
                    if af.exists():
                        try:
                            a = json.loads(af.read_text())
                            ai_text  = a.get("analysis")
                            ai_at    = a.get("analyzed_at")
                            ai_model = a.get("model")
                        except Exception:
                            pass
                    laps = data.get("laps", [])
                    conn.execute("""
                        INSERT OR IGNORE INTO sessions
                        (session_id,game,track,car,session_type,race_type,
                         started_at,ended_at,packet_count,best_lap_time_s,lap_count,
                         ai_analysis,ai_analyzed_at,ai_model)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (sid,
                          data.get("game"), data.get("track"), data.get("car"),
                          data.get("session_type"), data.get("race_type"),
                          data.get("started_at"), data.get("ended_at"),
                          data.get("packet_count", 0), data.get("best_lap_time_s"),
                          len(laps), ai_text, ai_at, ai_model))
                    for lap in laps:
                        conn.execute("""
                            INSERT INTO laps (session_id,lap_number,lap_time_s,max_speed_mph,sample_count)
                            VALUES (?,?,?,?,?)
                        """, (sid, lap.get("lap_number"), lap.get("lap_time_s"),
                              lap.get("max_speed_mph"), lap.get("sample_count", 0)))
                    imported += 1
                except Exception as e:
                    log.warning(f"DB migration: skipping {f.name}: {e}")
            conn.commit()
        finally:
            conn.close()
    if imported:
        log.info(f"SQLite: migrated {imported} session(s) from JSON files")


# Cache of learned track ordinals — invalidated when a new one is written
_learned_ordinals_cache: Optional[dict] = None


def _load_learned_track_ordinals() -> dict:
    """Return {ordinal: track_name} from the learned_track_ordinals table."""
    with _db_lock:
        conn = _db_connect()
        try:
            rows = conn.execute(
                "SELECT ordinal, track_name FROM learned_track_ordinals"
            ).fetchall()
            return {row["ordinal"]: row["track_name"] for row in rows}
        finally:
            conn.close()


def _db_write_learned_ordinal(ordinal: int, game: str, track_name: str):
    global _learned_ordinals_cache
    with _db_lock:
        conn = _db_connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO learned_track_ordinals (ordinal, game, track_name, created_at) "
                "VALUES (?,?,?,?)",
                (ordinal, game, track_name, datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()
    _learned_ordinals_cache = None  # invalidate
    # Re-merge learned ordinals into FORZA_TRACKS so new entries take effect immediately
    global FORZA_TRACKS
    FORZA_TRACKS[ordinal] = track_name


def _effective_tracks() -> dict:
    """Return merged {ordinal: track_name} combining FORZA_TRACKS and learned ordinals."""
    global _learned_ordinals_cache
    if _learned_ordinals_cache is None:
        _learned_ordinals_cache = _load_learned_track_ordinals()
    result = dict(FORZA_TRACKS)
    result.update(_learned_ordinals_cache)
    return result


def _classify_race_type(positions: list, lap_count: int) -> Optional[str]:
    """
    Derive race_type from sampled race positions and completed lap count.

    'real'       — position changed at least once (human opponents present)
    'time_trial' — lap count <= 3 and position never changed (solo / practice)
    'ai'         — more than 3 laps and position was always 1 (led wire-to-wire, AI grid)
    None         — not enough data to classify
    """
    if not positions:
        return "time_trial" if lap_count <= 3 else None
    unique = set(positions)
    if len(unique) > 1:
        return "real"
    # Position constant throughout
    if lap_count <= 3:
        return "time_trial"
    if next(iter(unique)) == 1:
        return "ai"
    return None


def _db_cull_ghost_sessions():
    """
    Move sessions with lap_count=1 AND best_lap_time_s IS NULL to
    discarded_sessions — these are Forza menu-browse artifacts.
    Deletes the corresponding _laps.json files but keeps .bin files.
    Runs once at startup; idempotent.
    """
    sessions_dir = storage_path() / "sessions"
    with _db_lock:
        conn = _db_connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discarded_sessions (
                    session_id  TEXT PRIMARY KEY,
                    game        TEXT,
                    track       TEXT,
                    started_at  TEXT,
                    reason      TEXT,
                    culled_at   TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.commit()
            ghosts = conn.execute(
                "SELECT session_id, game, track, started_at "
                "FROM sessions WHERE lap_count <= 1 AND best_lap_time_s IS NULL"
            ).fetchall()
            if not ghosts:
                return
            conn.executemany(
                "INSERT OR IGNORE INTO discarded_sessions "
                "(session_id, game, track, started_at, reason) VALUES (?,?,?,?,?)",
                [(r["session_id"], r["game"], r["track"], r["started_at"],
                  "lap_count<=1 and no lap time") for r in ghosts],
            )
            ids = [r["session_id"] for r in ghosts]
            conn.execute(
                f"DELETE FROM sessions WHERE session_id IN ({','.join('?'*len(ids))})", ids
            )
            conn.commit()
        finally:
            conn.close()

    # Delete _laps.json files for culled sessions (keep .bin)
    if sessions_dir.exists():
        for sid in ids:
            laps_file = sessions_dir / f"{sid}_laps.json"
            try:
                laps_file.unlink(missing_ok=True)
            except OSError:
                pass
    log.info(f"Culled {len(ghosts)} ghost session(s) to discarded_sessions table")


def _db_backfill_track_names():
    """
    For sessions stored as 'Track #<N>' or 'unknown' with a known track_ordinal,
    update track name from FORZA_TRACKS.  Also backfills car name/manufacturer/year
    from FORZA_CARS where car column is a raw ordinal string.
    Idempotent.
    """
    with _db_lock:
        conn = _db_connect()
        try:
            # ── Track name backfill ──────────────────────────────────────────
            rows = conn.execute(
                "SELECT session_id, track, track_ordinal FROM sessions "
                "WHERE track_ordinal IS NOT NULL "
                "AND (track = 'unknown' OR track LIKE 'Track #%')"
            ).fetchall()
            # Log all distinct ordinals found vs hits/misses
            distinct_ords = {r["track_ordinal"] for r in rows}
            if distinct_ords:
                hits   = {o for o in distinct_ords if FORZA_TRACKS.get(o)}
                misses = distinct_ords - hits
                log.info(
                    f"Track ordinal backfill: {len(distinct_ords)} distinct ordinals "
                    f"({len(hits)} hits, {len(misses)} misses). "
                    f"Misses: {sorted(misses)[:10]}"
                )
            track_updates = []
            for row in rows:
                name = FORZA_TRACKS.get(row["track_ordinal"])
                if name:
                    track_updates.append((name, row["session_id"]))
            if track_updates:
                conn.executemany("UPDATE sessions SET track=? WHERE session_id=?", track_updates)
                conn.commit()
                log.info(f"Backfilled track names for {len(track_updates)} session(s)")

            # ── Car name backfill ────────────────────────────────────────────
            # Sessions where car is a raw numeric string (unresolved ordinal)
            if FORZA_CARS:
                car_rows = conn.execute(
                    "SELECT session_id, car FROM sessions "
                    "WHERE car GLOB '[0-9]*' OR car = 'unknown'"
                ).fetchall()
                car_updates = []
                for row in car_rows:
                    try:
                        ordinal = int(row["car"]) if row["car"] != "unknown" else None
                    except (ValueError, TypeError):
                        ordinal = None
                    if ordinal is None:
                        continue
                    info = FORZA_CARS.get(ordinal)
                    if info:
                        car_updates.append((
                            info["name"], info["manufacturer"], info["year"],
                            row["session_id"]
                        ))
                if car_updates:
                    conn.executemany(
                        "UPDATE sessions SET car=?, car_manufacturer=?, car_year=? "
                        "WHERE session_id=?",
                        car_updates
                    )
                    conn.commit()
                    log.info(f"Backfilled car names for {len(car_updates)} session(s)")
        finally:
            conn.close()


def _db_backfill_race_types():
    """
    Classify sessions whose race_type is NULL.
    Runs at startup and re-runs safely (idempotent — only touches NULL rows).
    Uses stored grid_pos/finish_pos/lap_count with a broader heuristic than
    live classification so older sessions without full position history get tagged.
    """
    with _db_lock:
        conn = _db_connect()
        try:
            rows = conn.execute(
                "SELECT session_id, session_type, grid_pos, finish_pos, lap_count "
                "FROM sessions WHERE race_type IS NULL"
            ).fetchall()
            if not rows:
                return
            updates = []
            for row in rows:
                sid       = row["session_id"]
                stype     = row["session_type"] or "unknown"
                grid_pos  = row["grid_pos"]
                finish_pos = row["finish_pos"]
                lap_count = row["lap_count"] or 0

                # Try the standard classifier first (uses position variance)
                if grid_pos is not None and finish_pos is not None:
                    positions = [grid_pos, finish_pos]
                else:
                    positions = []
                rt = _classify_race_type(positions, lap_count)

                # Fall back to heuristics when classifier can't decide
                if rt is None:
                    if stype == "time_trial" or lap_count <= 3:
                        rt = "time_trial"
                    elif stype == "race" or lap_count > 5:
                        # Grid=finish and both non-1 → stayed in same position throughout
                        # Most likely a real-lobby race; AI races typically vary
                        if grid_pos is not None and finish_pos is not None and grid_pos == finish_pos and finish_pos != 1:
                            rt = "real"
                        elif grid_pos is None or finish_pos is None:
                            rt = "real"  # No position data: assume real-lobby
                        # else: handled by classifier above (ai or time_trial)

                if rt is not None:
                    updates.append((rt, sid))

            if updates:
                conn.executemany(
                    "UPDATE sessions SET race_type=? WHERE session_id=?", updates
                )
                conn.commit()
                log.info(f"SQLite: backfilled race_type for {len(updates)} session(s)")
        finally:
            conn.close()


def _db_write_session(session_data: dict):
    """Insert/replace a session and its lap summaries."""
    sid  = session_data["session_id"]
    laps = session_data.get("laps", [])
    with _db_lock:
        conn = _db_connect()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO sessions
                (session_id,game,track,car,session_type,race_type,
                 started_at,ended_at,packet_count,best_lap_time_s,lap_count,
                 grid_pos,finish_pos,track_ordinal,car_class,car_pi,
                 weather_condition,track_temp_c,air_temp_c,
                 car_manufacturer,car_year)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (sid,
                  session_data.get("game"), session_data.get("track"),
                  session_data.get("car"), session_data.get("session_type"),
                  session_data.get("race_type"),
                  session_data.get("started_at"), session_data.get("ended_at"),
                  session_data.get("packet_count", 0), session_data.get("best_lap_time_s"),
                  len(laps),
                  session_data.get("grid_pos"), session_data.get("finish_pos"),
                  session_data.get("track_ordinal"),
                  session_data.get("car_class"), session_data.get("car_pi"),
                  session_data.get("weather_condition"),
                  session_data.get("track_temp_c"), session_data.get("air_temp_c"),
                  session_data.get("car_manufacturer"), session_data.get("car_year")))
            conn.execute("DELETE FROM laps WHERE session_id=?", (sid,))
            for lap in laps:
                conn.execute("""
                    INSERT INTO laps (session_id,lap_number,lap_time_s,max_speed_mph,sample_count)
                    VALUES (?,?,?,?,?)
                """, (sid, lap.get("lap_number"), lap.get("lap_time_s"),
                      lap.get("max_speed_mph"), lap.get("sample_count", 0)))
            conn.commit()
        finally:
            conn.close()

def _db_sessions_list(limit: int = 100) -> list:
    """Return sessions newest-first — summary stats only, no sample data."""
    with _db_lock:
        conn = _db_connect()
        try:
            rows = conn.execute(
                "SELECT session_id,game,track,car,session_type,race_type,"
                "started_at,ended_at,packet_count,best_lap_time_s,lap_count "
                "FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def _db_games_index() -> list:
    """Return per-game aggregate stats, newest-first."""
    all_games = ["forza_motorsport", "acc", "f1"]
    with _db_lock:
        conn = _db_connect()
        try:
            rows = conn.execute("""
                SELECT game,
                       COUNT(*) as session_count,
                       COUNT(DISTINCT CASE WHEN track IS NOT NULL AND track != 'unknown'
                                           THEN track END) as track_count,
                       MAX(started_at) as last_played
                FROM sessions
                GROUP BY game
            """).fetchall()
            by_game = {r["game"]: dict(r) for r in rows}
            result = []
            for g in all_games:
                r = by_game.get(g, {"game": g, "session_count": 0, "track_count": 0, "last_played": None})
                # Best lap for this game + track it was set at
                bl = conn.execute("""
                    SELECT best_lap_time_s, track FROM sessions
                    WHERE game=? AND best_lap_time_s IS NOT NULL
                    ORDER BY best_lap_time_s ASC LIMIT 1
                """, (g,)).fetchone()
                r["best_lap_time_s"] = bl["best_lap_time_s"] if bl else None
                r["best_lap_track"]  = bl["track"] if bl else None
                # Last played track
                lp = conn.execute(
                    "SELECT track FROM sessions WHERE game=? ORDER BY started_at DESC LIMIT 1", (g,)
                ).fetchone()
                r["last_played_track"] = lp["track"] if lp else None
                # Spark — last 8 race best laps (non-null, newest first)
                spark_rows = conn.execute("""
                    SELECT best_lap_time_s FROM sessions
                    WHERE game=? AND best_lap_time_s IS NOT NULL
                    ORDER BY started_at DESC LIMIT 8
                """, (g,)).fetchall()
                r["spark"] = [s[0] for s in reversed(spark_rows)]
                result.append(r)
            result.sort(key=lambda x: (x["last_played"] is None, x["last_played"] or ""), reverse=False)
            result.sort(key=lambda x: x["last_played"] is None)
            return result
        finally:
            conn.close()

def _db_career_kpis(game: Optional[str] = None) -> dict:
    """Return career-level KPI aggregates. Optionally filtered to a single game."""
    with _db_lock:
        conn = _db_connect()
        try:
            where = "WHERE game=?" if game else ""
            params = [game] if game else []
            row = conn.execute(f"""
                SELECT
                  COUNT(*) as total_sessions,
                  SUM(CASE WHEN race_type='real' THEN 1 ELSE 0 END) as real_count,
                  SUM(CASE WHEN race_type='ai'   THEN 1 ELSE 0 END) as ai_count,
                  AVG(CASE WHEN race_type='real' AND session_type='race' AND finish_pos IS NOT NULL
                           THEN CAST(finish_pos AS REAL) END) as avg_finish_real,
                  AVG(CASE WHEN race_type='real' AND session_type='race'
                                AND grid_pos IS NOT NULL AND grid_pos > 0 AND finish_pos IS NOT NULL
                           THEN CAST(grid_pos AS REAL) - finish_pos END) as avg_pos_gained,
                  100.0 * SUM(CASE WHEN race_type='real' AND session_type='race' AND finish_pos=1 THEN 1 ELSE 0 END)
                        / NULLIF(SUM(CASE WHEN race_type='real' AND session_type='race' THEN 1 ELSE 0 END), 0) as win_rate,
                  100.0 * SUM(CASE WHEN race_type='real' AND session_type='race' AND finish_pos<=3 THEN 1 ELSE 0 END)
                        / NULLIF(SUM(CASE WHEN race_type='real' AND session_type='race' THEN 1 ELSE 0 END), 0) as podium_rate,
                  SUM(lap_count) as total_laps,
                  MIN(best_lap_time_s) as best_lap_time_s,
                  COUNT(DISTINCT CASE WHEN track IS NOT NULL AND track != 'unknown' THEN track END) as circuit_count
                FROM sessions {where}
            """, params).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

def _db_form_data(race_type_filter: Optional[str] = None, last_n: int = 10,
                  game: Optional[str] = None) -> list:
    """Return last N race sessions for the Current Form bar chart."""
    with _db_lock:
        conn = _db_connect()
        try:
            where = "WHERE session_type='race'"
            params: list = []
            if race_type_filter and race_type_filter != "all":
                where += " AND race_type=?"
                params.append(race_type_filter)
            if game:
                where += " AND game=?"
                params.append(game)
            params.append(last_n)
            rows = conn.execute(f"""
                SELECT session_id, track, started_at, finish_pos, grid_pos,
                       best_lap_time_s, lap_count, race_type, game
                FROM sessions {where}
                ORDER BY started_at DESC LIMIT ?
            """, params).fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            conn.close()

def _db_recent_sessions(limit: int = 8, game: Optional[str] = None) -> list:
    """Return last N sessions, optionally filtered by game."""
    with _db_lock:
        conn = _db_connect()
        try:
            where = "WHERE game=?" if game else ""
            params = [game, limit] if game else [limit]
            rows = conn.execute(f"""
                SELECT session_id, game, track, started_at, best_lap_time_s,
                       lap_count, finish_pos, grid_pos, race_type, session_type,
                       weather_condition, track_temp_c
                FROM sessions {where} ORDER BY started_at DESC LIMIT ?
            """, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def _db_tracks_index(game: Optional[str] = None) -> list:
    """Return aggregate stats per track, newest-first. Optionally filter by game."""
    with _db_lock:
        conn = _db_connect()
        try:
            where = "WHERE track IS NOT NULL"
            params: list = []
            if game:
                where += " AND game=?"
                params.append(game)
            rows = conn.execute(f"""
                SELECT track,
                       COUNT(*) as session_count,
                       MIN(best_lap_time_s) as best_lap_time_s,
                       MAX(started_at) as last_raced
                FROM sessions {where}
                GROUP BY track
                ORDER BY last_raced DESC
            """, params).fetchall()
            result = []
            for row in rows:
                r = dict(row)
                extra_where = (" AND game=?" if game else "")
                extra_params_base = [r["track"]] + (([game]) if game else [])
                last3 = conn.execute(
                    f"SELECT best_lap_time_s FROM sessions WHERE track=? AND best_lap_time_s IS NOT NULL{extra_where} ORDER BY started_at DESC LIMIT 3",
                    extra_params_base,
                ).fetchall()
                times = [l[0] for l in last3]
                if len(times) >= 2 and times[0] is not None and times[1] is not None:
                    diff = times[0] - times[1]
                    r["trend"] = "dn" if diff > 0.5 else ("up" if diff < -0.5 else "fl")
                else:
                    r["trend"] = "fl"
                # Spark: best lap per session, chronological oldest→newest (up to 20)
                spark_rows = conn.execute(
                    f"SELECT best_lap_time_s FROM sessions WHERE track=? AND best_lap_time_s IS NOT NULL{extra_where} ORDER BY started_at ASC LIMIT 20",
                    extra_params_base,
                ).fetchall()
                r["spark_laps"] = [sr[0] for sr in spark_rows]
                # Avg finish position (race sessions only)
                finish_row = conn.execute(
                    f"SELECT AVG(finish_pos) FROM sessions WHERE track=? AND finish_pos IS NOT NULL{extra_where}",
                    extra_params_base,
                ).fetchone()
                avg_f = finish_row[0] if finish_row else None
                r["avg_finish"] = round(avg_f, 1) if avg_f is not None else None
                # Car from best-lap session
                best_car_row = conn.execute(
                    f"SELECT car, car_class, car_pi FROM sessions WHERE track=? AND best_lap_time_s=?{extra_where} ORDER BY started_at DESC LIMIT 1",
                    [r["track"], r["best_lap_time_s"]] + (([game]) if game else []),
                ).fetchone()
                r["best_car"] = best_car_row["car"] if best_car_row else None
                r["best_car_class"] = best_car_row["car_class"] if best_car_row else None
                r["best_car_pi"] = best_car_row["car_pi"] if best_car_row else None
                result.append(r)
            return result
        finally:
            conn.close()

def _db_track_sessions(track: str, game: Optional[str] = None) -> list:
    """Return all sessions for a track, newest-first, with lap time arrays for spark graphs."""
    with _db_lock:
        conn = _db_connect()
        try:
            where = "WHERE track=?"
            params: list = [track]
            if game:
                where += " AND game=?"
                params.append(game)
            rows = conn.execute(f"""
                SELECT session_id,game,track,car,session_type,race_type,
                       started_at,ended_at,best_lap_time_s,lap_count,
                       ai_analyzed_at,ai_model,car_class,car_pi,finish_pos,grid_pos
                FROM sessions {where} ORDER BY started_at DESC
            """, params).fetchall()
            result = []
            for row in rows:
                s = dict(row)
                lap_rows = conn.execute(
                    "SELECT lap_time_s FROM laps WHERE session_id=? ORDER BY lap_number",
                    (s["session_id"],)
                ).fetchall()
                s["lap_times"] = [l[0] for l in lap_rows if l[0] is not None]
                result.append(s)
            return result
        finally:
            conn.close()

def _db_get_track_tip(track: str) -> Optional[dict]:
    """Return cached coaching tip for a track, or None."""
    with _db_lock:
        conn = _db_connect()
        try:
            row = conn.execute(
                "SELECT tip,generated_at,model FROM track_tips WHERE track=?", (track,)
            ).fetchone()
            return dict(row) if row and row["tip"] else None
        finally:
            conn.close()

def _db_save_track_tip(track: str, tip: str, model: str):
    with _db_lock:
        conn = _db_connect()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO track_tips (track,tip,generated_at,model)
                VALUES (?,?,?,?)
            """, (track, tip, datetime.now().isoformat(), model))
            conn.commit()
        finally:
            conn.close()

def _db_update_session(sid: str, **kwargs):
    """Update arbitrary columns on a session row."""
    if not kwargs:
        return
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [sid]
    with _db_lock:
        conn = _db_connect()
        try:
            conn.execute(f"UPDATE sessions SET {cols} WHERE session_id=?", vals)
            conn.commit()
        finally:
            conn.close()

def _db_drop_last_lap(sid: str):
    """Remove the last lap row and recalculate best_lap_time_s."""
    with _db_lock:
        conn = _db_connect()
        try:
            last = conn.execute(
                "SELECT id FROM laps WHERE session_id=? ORDER BY lap_number DESC LIMIT 1",
                (sid,)
            ).fetchone()
            if last:
                conn.execute("DELETE FROM laps WHERE id=?", (last["id"],))
                best = conn.execute(
                    "SELECT MIN(lap_time_s) FROM laps WHERE session_id=? AND lap_time_s IS NOT NULL",
                    (sid,)
                ).fetchone()[0]
                count = conn.execute(
                    "SELECT COUNT(*) FROM laps WHERE session_id=?", (sid,)
                ).fetchone()[0]
                conn.execute(
                    "UPDATE sessions SET best_lap_time_s=?, lap_count=? WHERE session_id=?",
                    (best, count, sid)
                )
                conn.commit()
        finally:
            conn.close()

def _db_get_ai_analysis(sid: str) -> Optional[dict]:
    """Return cached AI analysis from DB, or None if not yet analyzed."""
    with _db_lock:
        conn = _db_connect()
        try:
            row = conn.execute(
                "SELECT ai_analysis,ai_analyzed_at,ai_model FROM sessions WHERE session_id=?",
                (sid,)
            ).fetchone()
            if row and row["ai_analysis"]:
                return {
                    "session_id":  sid,
                    "analysis":    row["ai_analysis"],
                    "analyzed_at": row["ai_analyzed_at"],
                    "model":       row["ai_model"],
                    "cached":      True,
                }
            return None
        finally:
            conn.close()

def _db_save_ai_analysis(sid: str, analysis: str, model: str):
    """Persist AI analysis text to the sessions row."""
    _db_update_session(sid,
                       ai_analysis=analysis,
                       ai_analyzed_at=datetime.now().isoformat(),
                       ai_model=model)

# ─── Lap Normalization & Reference Storage ────────────────────────────────────

import math as _math

_DOWNSAMPLE_TARGET = 500  # max points stored per lap

def normalize_lap_samples(samples: list) -> tuple[list, list]:
    """
    Normalise a lap's raw sample list to distance-based coordinates.

    Returns (normalised_samples, cumulative_distances_m) where each sample
    gains a `distance_norm` field (0.0 lap-start → 1.0 lap-end).

    Strategy:
    - Primary: use px/py/pz position fields; compute Euclidean deltas.
    - Fallback: use elapsed time `t`; treat as linear distance proxy.

    Returned samples are downsampled to at most _DOWNSAMPLE_TARGET points.
    """
    if not samples:
        return [], []

    has_position = all("px" in s and "py" in s and "pz" in s for s in samples)

    cum_dist: list[float] = [0.0]
    if has_position:
        for i in range(1, len(samples)):
            dx = samples[i]["px"] - samples[i - 1]["px"]
            dy = samples[i]["py"] - samples[i - 1]["py"]
            dz = samples[i]["pz"] - samples[i - 1]["pz"]
            cum_dist.append(cum_dist[-1] + _math.sqrt(dx * dx + dy * dy + dz * dz))
    else:
        for s in samples[1:]:
            cum_dist.append(s["t"])

    total = cum_dist[-1]
    if total <= 0:
        # All identical positions — fall back to index-based
        total = len(samples) - 1 or 1
        cum_dist = [i for i in range(len(samples))]

    # Downsample evenly if over target
    step = max(1, len(samples) // _DOWNSAMPLE_TARGET)
    indices = list(range(0, len(samples), step))
    # Always include last sample
    if indices[-1] != len(samples) - 1:
        indices.append(len(samples) - 1)

    norm_samples = []
    dist_m_out = []
    for i in indices:
        s = dict(samples[i])
        s["distance_norm"] = round(cum_dist[i] / total, 6)
        norm_samples.append(s)
        dist_m_out.append(round(cum_dist[i], 2))

    return norm_samples, dist_m_out


def _db_save_lap_samples(session_id: str, lap_number: int,
                          samples: list, dist_m: list):
    with _db_lock:
        conn = _db_connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO lap_samples
                   (session_id, lap_number, samples_json, distance_m_json, created_at)
                   VALUES (?,?,?,?,?)""",
                (session_id, lap_number,
                 json.dumps(samples), json.dumps(dist_m),
                 datetime.now().isoformat())
            )
            conn.commit()
        finally:
            conn.close()


def _db_get_lap_samples(session_id: str, lap_number: int) -> Optional[dict]:
    with _db_lock:
        conn = _db_connect()
        try:
            row = conn.execute(
                "SELECT samples_json, distance_m_json FROM lap_samples "
                "WHERE session_id=? AND lap_number=?",
                (session_id, lap_number)
            ).fetchone()
            if row:
                return {
                    "samples": json.loads(row["samples_json"]),
                    "distance_m": json.loads(row["distance_m_json"]),
                }
            return None
        finally:
            conn.close()


def _store_session_lap_samples(session_id: str, completed_laps: list):
    """
    Normalise and persist lap_samples rows for every lap within 102% of
    the session best lap time. Called from Session.close().
    """
    if not completed_laps:
        return

    valid = [lap for lap in completed_laps
             if lap.lap_time_s and lap.lap_time_s > 0]
    if not valid:
        return

    for lap in valid:
        if lap.samples:
            try:
                norm, dist_m = normalize_lap_samples(lap.samples)
                _db_save_lap_samples(session_id, lap.lap_number, norm, dist_m)
            except Exception as exc:
                log.warning(f"lap_samples write failed lap {lap.lap_number}: {exc}")


def _backfill_lap_samples():
    """
    Back-fill lap_samples + track_references from existing _laps.json files
    for sessions that have no stored samples yet.  Runs once at startup in a
    daemon thread so it never blocks the listener.
    """
    sessions_dir = storage_path() / "sessions"
    if not sessions_dir.exists():
        return

    with _db_lock:
        conn = _db_connect()
        try:
            rows = conn.execute(
                """SELECT s.session_id, s.track, s.game
                   FROM sessions s
                   WHERE s.lap_count > 0
                   AND s.lap_count > (
                       SELECT COUNT(*) FROM lap_samples ls WHERE ls.session_id = s.session_id
                   )
                   ORDER BY s.started_at DESC LIMIT 500"""
            ).fetchall()
        finally:
            conn.close()

    if not rows:
        return

    tracks_to_update: set = set()
    filled = 0
    for row in rows:
        sid = row["session_id"]
        laps_file = sessions_dir / f"{sid}_laps.json"
        if not laps_file.exists():
            continue
        try:
            laps_data = json.loads(laps_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(laps_data, list):
            continue
        valid = [l for l in laps_data
                 if l.get("lap_number") and l.get("lap_time_s") and l["lap_time_s"] > 0]
        if not valid:
            continue
        for lap in valid:
            samples = lap.get("samples", [])
            if not samples:
                continue
            try:
                norm, dist_m = normalize_lap_samples(samples)
                _db_save_lap_samples(sid, lap["lap_number"], norm, dist_m)
                filled += 1
            except Exception as exc:
                log.warning(f"backfill lap_samples {sid} L{lap['lap_number']}: {exc}")
        track = row["track"] or ""
        game  = row["game"]  or ""
        if track and track != "unknown":
            tracks_to_update.add((track, game))

    for track, game in tracks_to_update:
        try:
            update_track_references(track, game)
        except Exception as exc:
            log.warning(f"backfill track_references {track!r}: {exc}")

    log.info(
        f"backfill_lap_samples: {filled} laps stored, "
        f"{len(tracks_to_update)} track references updated"
    )


def _sector_time_from_samples(samples: list, lo: float, hi: float) -> Optional[float]:
    """Time spent between two distance_norm boundaries, read from sample 't' field."""
    if not samples:
        return None

    def t_at(target: float) -> float:
        closest = min(samples, key=lambda s: abs(s.get("distance_norm", 0.0) - target))
        return closest["t"]

    t_lo = samples[0]["t"] if lo <= 0.0 else t_at(lo)
    t_hi = samples[-1]["t"] if hi >= 1.0 else t_at(hi)
    delta = t_hi - t_lo
    return round(delta, 3) if delta > 0 else None


def _stitch_sector_samples(
    s1_samples: list, s2_samples: list, s3_samples: list,
    s1_t: float, s2_t: float,
) -> list:
    """
    Combine three sector-best laps into one stitched trace.

    distance_norm values are kept from the original slices (already 0-1).
    t values are re-offset per sector so the stitched lap has a continuous
    elapsed-time axis: S1 t as-is, S2 offset to start at s1_t, S3 offset
    to start at s1_t+s2_t.
    """
    def _slice(samples, lo, hi):
        return [dict(s) for s in samples if lo <= s.get("distance_norm", 0.0) <= hi]

    part1 = _slice(s1_samples, 0.0,  0.334)
    part2 = _slice(s2_samples, 0.332, 0.668)
    part3 = _slice(s3_samples, 0.666, 1.0)

    # Re-offset t so sectors chain continuously
    if part2:
        off = s1_t - part2[0]["t"]
        for s in part2:
            s["t"] = round(s["t"] + off, 3)
    if part3:
        off = (s1_t + s2_t) - part3[0]["t"]
        for s in part3:
            s["t"] = round(s["t"] + off, 3)

    # Blend sample at each sector boundary
    def _blend(left, right, norm):
        if not left or not right:
            return []
        skip = {"distance_norm", "t", "px", "py", "pz"}
        shared = {k for k in left[-1] if k not in skip} & {k for k in right[0] if k not in skip}
        mid: dict = {
            "distance_norm": norm,
            "t": round((left[-1]["t"] + right[0]["t"]) / 2, 3),
        }
        for k in shared:
            try:
                mid[k] = round((left[-1][k] + right[0][k]) / 2, 4)
            except (TypeError, ValueError):
                mid[k] = right[0][k]
        return [mid]

    mid12 = _blend(part1, part2, 0.333)
    mid23 = _blend(part2, part3, 0.667)

    p1 = part1[:-1] if mid12 and part1 else part1
    p2 = part2[1:-1] if mid12 and mid23 and part2 else (
         part2[1:]  if mid12 and part2 else
         part2[:-1] if mid23 and part2 else part2)
    p3 = part3[1:] if mid23 and part3 else part3

    return p1 + mid12 + p2 + mid23 + p3


def update_track_references(track: str, game: str):
    """
    Recompute best-lap and theoretical-best references for *track*.

    Reads sessions+laps+lap_samples; writes track_references.
    Non-blocking: called via _update_track_references_bg() in a daemon thread.
    """
    if not track or track == "unknown":
        return

    # All timed laps at this track, fastest first
    with _db_lock:
        conn = _db_connect()
        try:
            rows = conn.execute(
                """SELECT l.session_id, l.lap_number, l.lap_time_s, s.started_at
                   FROM laps l
                   JOIN sessions s ON l.session_id = s.session_id
                   WHERE s.track=? AND s.game=?
                     AND l.lap_time_s IS NOT NULL AND l.lap_time_s > 0
                   ORDER BY l.lap_time_s ASC""",
                (track, game),
            ).fetchall()
        finally:
            conn.close()

    if not rows:
        return

    # ── Best lap reference ──────────────────────────────────────────────────
    best_row = rows[0]
    best_data = _db_get_lap_samples(best_row["session_id"], best_row["lap_number"])
    if best_data:
        with _db_lock:
            conn = _db_connect()
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO track_references
                       (track, reference_type, session_id, lap_number,
                        samples_json, updated_at)
                       VALUES (?,?,?,?,?,?)""",
                    (track, "best_lap",
                     best_row["session_id"], best_row["lap_number"],
                     json.dumps(best_data["samples"]),
                     datetime.now().isoformat()),
                )
                conn.commit()
            finally:
                conn.close()

    # ── Theoretical best ────────────────────────────────────────────────────
    # For each lap with stored samples, compute approximate sector times by
    # splitting the distance_norm range into equal thirds.
    best_s = [None, None, None]          # best sector time per sector
    best_meta = [None, None, None]       # {session_id, lap, samples} per sector
    sector_bounds = [(0.0, 0.333), (0.333, 0.667), (0.667, 1.0)]

    for row in rows:
        lap_data = _db_get_lap_samples(row["session_id"], row["lap_number"])
        if not lap_data or not lap_data["samples"]:
            continue
        samples = lap_data["samples"]
        for i, (lo, hi) in enumerate(sector_bounds):
            st = _sector_time_from_samples(samples, lo, hi)
            if st is None:
                continue
            if best_s[i] is None or st < best_s[i]:
                best_s[i] = st
                best_meta[i] = {
                    "session_id": row["session_id"],
                    "lap": row["lap_number"],
                    "samples": samples,
                }

    if not all(best_meta):
        return  # not enough data for a theoretical best

    s1_t, s2_t, s3_t = best_s
    theoretical_best = round(s1_t + s2_t + s3_t, 3)
    stitched = _stitch_sector_samples(
        best_meta[0]["samples"], best_meta[1]["samples"], best_meta[2]["samples"],
        s1_t, s2_t,
    )

    with _db_lock:
        conn = _db_connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO track_references
                   (track, reference_type, session_id, lap_number,
                    samples_json,
                    theoretical_s1_s, theoretical_s1_session_id, theoretical_s1_lap,
                    theoretical_s2_s, theoretical_s2_session_id, theoretical_s2_lap,
                    theoretical_s3_s, theoretical_s3_session_id, theoretical_s3_lap,
                    theoretical_best_s, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (track, "theoretical",
                 None, None,
                 json.dumps(stitched),
                 s1_t, best_meta[0]["session_id"], best_meta[0]["lap"],
                 s2_t, best_meta[1]["session_id"], best_meta[1]["lap"],
                 s3_t, best_meta[2]["session_id"], best_meta[2]["lap"],
                 theoretical_best,
                 datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    log.info(
        f"track_references: {track!r} | "
        f"best={best_row['lap_time_s']:.3f}s | theoretical={theoretical_best:.3f}s"
    )


def _update_track_references_bg(track: str, game: str):
    try:
        update_track_references(track, game)
    except Exception as exc:
        log.warning(f"track_references update failed ({track!r}): {exc}")


# ─── AI Analysis ──────────────────────────────────────────────────────────────

import statistics as _statistics
import urllib.request as _urllib_req

def _summarize_lap(lap: dict) -> Optional[dict]:
    samples = lap.get("samples", [])
    if not samples or not lap.get("lap_time_s"):
        return None
    throttle = [s.get("throttle_pct", 0) for s in samples]
    brake    = [s.get("brake_pct", 0)    for s in samples]
    g_lat    = [abs(s.get("g_lat", 0))   for s in samples]
    slip_rl  = [abs(s.get("slip_rl", 0)) for s in samples]
    slip_rr  = [abs(s.get("slip_rr", 0)) for s in samples]
    slip_avg = [(a + b) / 2 for a, b in zip(slip_rl, slip_rr)]
    n = len(samples)
    return {
        "lap_number":      lap["lap_number"],
        "lap_time_s":      lap["lap_time_s"],
        "max_speed_mph":   lap.get("max_speed_mph", 0),
        "avg_throttle":    round(sum(throttle) / n, 1),
        "avg_brake":       round(sum(brake)    / n, 1),
        "avg_g_lat":       round(sum(g_lat)    / n, 3),
        "avg_slip":        round(sum(slip_avg) / n, 4),
        "peak_slip":       round(max(slip_avg),     4) if slip_avg else 0,
        "slip_above_pct":  round(sum(1 for v in slip_avg if v > 0.1) / n * 100, 1),
    }


def _build_analysis_prompt(session: dict, laps: list, historical: list,
                           prev_analyses: Optional[list] = None) -> str:
    game  = session.get("game", "unknown").replace("_", " ").title()
    track = session.get("track", "unknown")
    date  = (session.get("started_at") or "")[:10]

    summaries = [s for lap in laps if (s := _summarize_lap(lap))]
    valid_times = [s["lap_time_s"] for s in summaries]
    best_time = min(valid_times) if valid_times else None
    avg_time  = sum(valid_times) / len(valid_times) if valid_times else None

    hdr = "Lap | Time      | Throttle% | Brake% | MaxSpd | AvgSlip | PeakSlip | Slip>0.1%\n"
    hdr += "-" * 80 + "\n"
    rows = ""
    for s in summaries:
        marker = " ◄" if best_time and abs(s["lap_time_s"] - best_time) < 0.001 else ""
        rows += (
            f"{s['lap_number']:<3} | {s['lap_time_s']:.3f}s   | "
            f"{s['avg_throttle']:.0f}%        | {s['avg_brake']:.0f}%     | "
            f"{s['max_speed_mph']:.0f}mph  | {s['avg_slip']:.4f}  | "
            f"{s['peak_slip']:.4f}   | {s['slip_above_pct']:.1f}%{marker}\n"
        )

    # Historical baseline — last 3 sessions at same track (from DB summaries)
    hist_block = ""
    if historical:
        hist_sessions = historical[-3:]
        h_best_times  = [h.get("best_lap_time_s") for h in hist_sessions if h.get("best_lap_time_s")]
        h_avg_slip_vals = []
        sessions_dir = storage_path() / "sessions"
        for h in hist_sessions:
            try:
                hlaps = json.loads((sessions_dir / f"{h['session_id']}_laps.json").read_text())
                hsums = [s for lap in hlaps if (s := _summarize_lap(lap))]
                if hsums:
                    h_avg_slip_vals.append(sum(s["avg_slip"] for s in hsums) / len(hsums))
            except Exception:
                pass
        h_best_str = f"{min(h_best_times):.3f}s" if h_best_times else "—"
        h_avg_str  = f"{sum(valid_times)/len(valid_times):.3f}s" if valid_times else "—"
        h_slip_str = f"{sum(h_avg_slip_vals)/len(h_avg_slip_vals):.4f}" if h_avg_slip_vals else "—"
        hist_block = (
            f"\nHISTORICAL BASELINE (last {len(hist_sessions)} sessions at this track):\n"
            f"Best lap: {h_best_str} | Avg lap: {h_avg_str} | Avg slip: {h_slip_str}\n"
        )

    return (
        f"Track: {track} | Game: {game} | Session: {date}\n\n"
        f"THIS SESSION — LAP TABLE:\n{hdr}{rows}\n"
        f"{hist_block}\n"
        "Analyze this session. Focus on slip management, throttle discipline, "
        "brake consistency, and lap time trend. Reference specific laps. "
        "Compare against historical baseline where relevant. Be direct, no padding."
    )


def _build_track_tip_prompt(track: str, stats: dict) -> str:
    best = f"{stats['best_lap_time_s']:.3f}s" if stats.get("best_lap_time_s") else "unknown"
    return (
        f"Track: {track} | Sessions: {stats.get('session_count',0)} | Best lap: {best} | Trend: {stats.get('trend','fl')}\n\n"
        "Write exactly one coaching focus sentence (max 20 words) for this sim racing driver at this track. "
        "Be specific to the track's characteristics if you know it. No intro, no padding, just the sentence."
    )

def _call_claude_api(prompt: str) -> str:
    api_key = config.get("anthropic_api_key", "").strip()
    model   = config.get("anthropic_model", "claude-sonnet-4-6").strip()
    if not api_key:
        raise ValueError("Anthropic API key not set — add it in Setup → AI Analysis")
    payload = json.dumps({
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = _urllib_req.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload, method="POST",
    )
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")
    with _urllib_req.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


def _http_response(status: str, content_type: str, body: bytes, extra_headers: str = "") -> bytes:
    return (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Access-Control-Allow-Private-Network: true\r\n"
        f"Connection: close\r\n"
        f"{extra_headers}\r\n"
    ).encode() + body


async def handle_status(reader, writer):
    try:
        # Read until the end of HTTP headers
        header_buf = b""
        while b"\r\n\r\n" not in header_buf:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=5)
            if not chunk:
                break
            header_buf += chunk

        header_bytes, _, body_so_far = header_buf.partition(b"\r\n\r\n")
        header_str = header_bytes.decode("utf-8", errors="ignore")
        header_lines = header_str.split("\r\n")
        request_line = header_lines[0] if header_lines else ""
        parts        = request_line.split(" ")
        method       = parts[0] if parts else "GET"
        raw_url      = parts[1] if len(parts) > 1 else "/"
        path         = raw_url.split("?")[0]
        query_string = raw_url.split("?", 1)[1] if "?" in raw_url else ""

        # Parse Content-Length so we read the full POST body
        content_length = 0
        for line in header_lines[1:]:
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
                break

        body_buf = body_so_far
        while len(body_buf) < content_length:
            chunk = await asyncio.wait_for(reader.read(content_length - len(body_buf)), timeout=5)
            if not chunk:
                break
            body_buf += chunk

        raw_body = body_buf.decode("utf-8", errors="ignore")

        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            static_file = Path(__file__).parent / "static" / rel
            if static_file.is_file() and static_file.resolve().is_relative_to((Path(__file__).parent / "static").resolve()):
                ext = static_file.suffix.lower()
                mime = {"css": "text/css", "js": "application/javascript"}.get(ext.lstrip("."), "application/octet-stream")
                writer.write(_http_response("200 OK", mime, static_file.read_bytes()))
            else:
                writer.write(_http_response("404 Not Found", "text/plain", b"Not found"))

        elif path in ("/", "/dashboard"):
            writer.write(_http_response("200 OK", "text/html", DASHBOARD_HTML.encode()))

        elif path == "/setup":
            writer.write(_http_response("200 OK", "text/html", SETUP_HTML.encode()))

        elif path == "/setup/ips":
            uptime = int(time.time() - _listener_started_at) if _listener_started_at else 0
            payload = {
                "ips": _get_local_ips(),
                "ports": config["ports"],
                "uptime_s": uptime,
                "udp_received": state["udp_received"],
                "udp_last_at": state["udp_last_at"],
            }
            writer.write(_http_response("200 OK", "application/json", json.dumps(payload).encode()))

        elif path == "/config" and method == "GET":
            payload = {**config, "disk": disk_info()}
            writer.write(_http_response("200 OK", "application/json", json.dumps(payload, indent=2).encode()))

        elif path == "/config" and method == "POST":
            try:
                incoming = json.loads(raw_body)
            except (json.JSONDecodeError, ValueError) as exc:
                err = json.dumps({"error": f"Invalid JSON: {exc}"}).encode()
                writer.write(_http_response("400 Bad Request", "application/json", err))
            else:
                new_path = str(incoming.get("storage_path", config["storage_path"])).strip()
                # Validate: try to create subdirs
                try:
                    test = Path(new_path)
                    for sub in ["raw", "sessions", "logs"]:
                        (test / sub).mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    err = json.dumps({"error": f"Cannot create storage path: {exc}"}).encode()
                    writer.write(_http_response("400 Bad Request", "application/json", err))
                else:
                    config["storage_path"]      = new_path
                    config["session_timeout_s"] = int(incoming.get("session_timeout_s", config["session_timeout_s"]))
                    if "ports" in incoming:
                        config["ports"].update({
                            k: int(v) for k, v in incoming["ports"].items()
                            if k in config["ports"]
                        })
                    if "anthropic_api_key" in incoming:
                        config["anthropic_api_key"] = str(incoming["anthropic_api_key"]).strip()
                    if "anthropic_model" in incoming:
                        config["anthropic_model"] = str(incoming["anthropic_model"]).strip()
                    save_config(config)
                    msg = "Saved."
                    if incoming.get("ports") and incoming["ports"] != PORTS:
                        msg += " Restart required for port changes to take effect."
                    result = json.dumps({"ok": True, "message": msg, "disk": disk_info()}).encode()
                    writer.write(_http_response("200 OK", "application/json", result))

        elif path == "/status":
            writer.write(_http_response("200 OK", "application/json", json.dumps(state, indent=2).encode()))

        elif path in ("/sessions", "/sessions/"):
            writer.write(_http_response("200 OK", "text/html", GAMES_HTML.encode()))

        elif path == "/sessions/game":
            writer.write(_http_response("200 OK", "text/html", TRACKS_HTML.encode()))

        elif path == "/sessions/track":
            writer.write(_http_response("200 OK", "text/html", TRACK_DETAIL_HTML.encode()))

        elif path == "/sessions/session":
            writer.write(_http_response("200 OK", "text/html", SESSION_DETAIL_HTML.encode()))

        elif path == "/sessions/telemetry":
            writer.write(_http_response("200 OK", "text/html", TELEMETRY_HTML.encode()))

        elif path == "/sessions/data":
            result = _db_sessions_list(100)
            writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

        elif path == "/sessions/games":
            result = _db_games_index()
            writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

        elif path == "/sessions/career":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            result = _db_career_kpis(qs.get("game") or None)
            writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

        elif path == "/sessions/form":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            rt   = qs.get("type", "all") or "all"
            last = int(qs.get("last", "10") or "10")
            result = _db_form_data(rt if rt != "all" else None, last, qs.get("game") or None)
            writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

        elif path == "/sessions/recent":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            _limit = int(qs.get("limit", "8") or "8")
            result = _db_recent_sessions(_limit, qs.get("game") or None)
            writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

        elif path == "/sessions/tracks":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            game_filter = qs.get("game", "") or None
            result = _db_tracks_index(game_filter)
            writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

        elif path == "/sessions/track/data":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            track_name = qs.get("name", "")
            game_filter = qs.get("game", "") or None
            result = _db_track_sessions(track_name, game_filter)
            writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

        elif path == "/sessions/track/tip":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            track_name = qs.get("name", "")
            generate   = qs.get("generate", "") == "true"
            cached = _db_get_track_tip(track_name)
            if cached:
                writer.write(_http_response("200 OK", "application/json",
                                            json.dumps(cached).encode()))
            elif generate and config.get("anthropic_api_key", "").strip():
                try:
                    stats = next((t for t in _db_tracks_index() if t["track"] == track_name), {})
                    tip_prompt = _build_track_tip_prompt(track_name, stats)
                    tip_text   = await asyncio.to_thread(_call_claude_api, tip_prompt)
                    tip_text   = tip_text.strip().split("\n")[0][:200]
                    model_name = config.get("anthropic_model", "claude-sonnet-4-6")
                    _db_save_track_tip(track_name, tip_text, model_name)
                    writer.write(_http_response("200 OK", "application/json",
                                                json.dumps({"tip": tip_text, "generated_at": datetime.now().isoformat(), "model": model_name}).encode()))
                except Exception as exc:
                    log.error(f"Track tip generation error: {exc}")
                    writer.write(_http_response("200 OK", "application/json", b'{"tip":null}'))
            else:
                writer.write(_http_response("200 OK", "application/json", b'{"tip":null}'))

        elif path == "/sessions/confirm-data":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            sid = qs.get("id", "")
            with _db_lock:
                conn = _db_connect()
                try:
                    cd_row = conn.execute(
                        "SELECT session_id,game,track,car,session_type,race_type,"
                        "started_at,ended_at,best_lap_time_s,lap_count,track_ordinal "
                        "FROM sessions WHERE session_id=?", (sid,)
                    ).fetchone()
                finally:
                    conn.close()
            if not cd_row:
                writer.write(_http_response("404 Not Found", "application/json",
                                            json.dumps({"error": "Session not found"}).encode()))
            else:
                cd_dict = dict(cd_row)
                all_tracks = _effective_tracks()
                # Build sorted unique track name list (known tracks + any sessions track names)
                track_names = sorted(set(all_tracks.values()))
                writer.write(_http_response("200 OK", "application/json", json.dumps({
                    "session":       cd_dict,
                    "track_list":    track_names,
                    "track_ordinal": cd_dict.get("track_ordinal"),
                }).encode()))

        elif path == "/sessions/session/data":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            sid = qs.get("id", "")
            with _db_lock:
                conn = _db_connect()
                try:
                    sess_row = conn.execute(
                        "SELECT session_id,game,track,car,session_type,race_type,started_at,ended_at,"
                        "best_lap_time_s,lap_count,ai_analysis,ai_analyzed_at,ai_model,"
                        "car_class,car_pi,finish_pos,grid_pos,weather_condition,track_temp_c,air_temp_c "
                        "FROM sessions WHERE session_id=?", (sid,)
                    ).fetchone()
                finally:
                    conn.close()
            if not sess_row:
                writer.write(_http_response("404 Not Found", "application/json",
                                            json.dumps({"error": "Session not found"}).encode()))
            else:
                sess_dict = dict(sess_row)
                # Resolve car ordinal stored as numeric string to full name
                car_val = sess_dict.get("car", "")
                if car_val and isinstance(car_val, str) and car_val.isdigit():
                    ordinal = int(car_val)
                    car_info = FORZA_CARS.get(ordinal)
                    if car_info:
                        sess_dict["car"] = f"{car_info.get('year','')} {car_info['name']}".strip()
                    else:
                        sess_dict["car"] = f"Unknown car ({car_val})"
                laps_file = storage_path() / "sessions" / f"{sid}_laps.json"
                _debug = {
                    "sid": sid,
                    "laps_file": str(laps_file),
                    "file_exists": laps_file.exists(),
                }
                try:
                    raw_laps = json.loads(laps_file.read_text())
                    _debug["raw_lap_count"] = len(raw_laps)
                    _debug["first_lap_keys"] = list(raw_laps[0].keys()) if raw_laps else []
                    log.info(f"[session/data] {sid}: {laps_file} exists={_debug['file_exists']}, "
                             f"{len(raw_laps)} raw laps, "
                             f"finish_pos={sess_dict.get('finish_pos')} race_type={sess_dict.get('race_type')} "
                             f"session_type={sess_dict.get('session_type')}")
                except OSError:
                    raw_laps = []
                    _debug["error"] = "OSError — file not found or unreadable"
                    log.warning(f"[session/data] {sid}: _laps.json NOT FOUND at {laps_file}")
                except Exception as exc:
                    raw_laps = []
                    _debug["error"] = str(exc)
                    log.error(f"[session/data] {sid}: error reading _laps.json: {exc}")
                computed_laps = []
                for lap in raw_laps:
                    samples  = lap.get("samples", [])
                    n        = len(samples)
                    lap_time = lap.get("lap_time_s")
                    row = {
                        "lap_number":    lap.get("lap_number"),
                        "lap_time_s":    lap_time,
                        "max_speed_mph": lap.get("max_speed_mph"),
                    }
                    if n:
                        throttle   = [s.get("throttle_pct", 0) for s in samples]
                        brake      = [s.get("brake_pct", 0)    for s in samples]
                        slip_vals  = [(abs(s.get("slip_rl", 0)) + abs(s.get("slip_rr", 0))) / 2
                                      for s in samples]
                        row["avg_throttle"]   = round(sum(throttle) / n, 1)
                        row["avg_brake"]      = round(sum(brake)    / n, 1)
                        row["avg_slip"]       = round(sum(slip_vals) / n, 4)
                        _sv_sorted = sorted(slip_vals)
                        _p99_idx = max(0, int(len(_sv_sorted) * 0.99) - 1)
                        row["peak_slip"]      = round(_sv_sorted[_p99_idx], 4)
                        row["slip_above_pct"] = round(
                            sum(1 for v in slip_vals if v > 0.1) / n * 100, 1)
                    else:
                        row["avg_throttle"] = row["avg_brake"] = None
                        row["avg_slip"] = row["peak_slip"] = row["slip_above_pct"] = None
                    computed_laps.append(row)
                _debug["computed_lap_count"] = len(computed_laps)
                log.info(f"[session/data] {sid}: returning {len(computed_laps)} computed laps")
                writer.write(_http_response("200 OK", "application/json",
                                            json.dumps({"session": sess_dict, "laps": computed_laps,
                                                        "_debug": _debug}).encode()))

        elif path == "/sessions/laps":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            sid = qs.get("id", "")
            laps_file = storage_path() / "sessions" / f"{sid}_laps.json"
            try:
                writer.write(_http_response("200 OK", "application/json", laps_file.read_bytes()))
            except OSError:
                writer.write(_http_response("404 Not Found", "application/json", b"[]"))

        elif path == "/sessions/references":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            track_q = qs.get("track", "")
            if not track_q:
                writer.write(_http_response("400 Bad Request", "application/json",
                                            b'{"error":"track required"}'))
            else:
                with _db_lock:
                    conn = _db_connect()
                    try:
                        rows = {
                            row["reference_type"]: row
                            for row in conn.execute(
                                "SELECT * FROM track_references WHERE track=?", (track_q,)
                            ).fetchall()
                        }
                    finally:
                        conn.close()
                result: dict = {}
                if "best_lap" in rows:
                    r = rows["best_lap"]
                    # Fetch session date
                    with _db_lock:
                        conn = _db_connect()
                        try:
                            srow = conn.execute(
                                "SELECT started_at FROM sessions WHERE session_id=?",
                                (r["session_id"],)
                            ).fetchone()
                        finally:
                            conn.close()
                    # Get lap time from laps table
                    with _db_lock:
                        conn = _db_connect()
                        try:
                            lrow = conn.execute(
                                "SELECT lap_time_s FROM laps WHERE session_id=? AND lap_number=?",
                                (r["session_id"], r["lap_number"])
                            ).fetchone()
                        finally:
                            conn.close()
                    result["best_lap"] = {
                        "lap_time_s": lrow["lap_time_s"] if lrow else None,
                        "session_id": r["session_id"],
                        "session_date": (srow["started_at"] or "")[:10] if srow else "",
                        "lap_number": r["lap_number"],
                    }
                if "theoretical" in rows:
                    r = rows["theoretical"]
                    def _sdate(sid):
                        if not sid:
                            return ""
                        with _db_lock:
                            conn = _db_connect()
                            try:
                                row = conn.execute(
                                    "SELECT started_at FROM sessions WHERE session_id=?", (sid,)
                                ).fetchone()
                            finally:
                                conn.close()
                        return (row["started_at"] or "")[:10] if row else ""
                    result["theoretical"] = {
                        "theoretical_best_s": r["theoretical_best_s"],
                        "s1_s": r["theoretical_s1_s"],
                        "s1_session_date": _sdate(r["theoretical_s1_session_id"]),
                        "s2_s": r["theoretical_s2_s"],
                        "s2_session_date": _sdate(r["theoretical_s2_session_id"]),
                        "s3_s": r["theoretical_s3_s"],
                        "s3_session_date": _sdate(r["theoretical_s3_session_id"]),
                    }
                writer.write(_http_response("200 OK", "application/json",
                                            json.dumps(result).encode()))

        elif path == "/sessions/reference-samples":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            track_q = qs.get("track", "")
            ref_type = qs.get("type", "best_lap")
            if ref_type not in ("best_lap", "theoretical"):
                ref_type = "best_lap"
            if not track_q:
                writer.write(_http_response("400 Bad Request", "application/json",
                                            b'{"error":"track required"}'))
            else:
                with _db_lock:
                    conn = _db_connect()
                    try:
                        row = conn.execute(
                            "SELECT samples_json FROM track_references "
                            "WHERE track=? AND reference_type=?",
                            (track_q, ref_type)
                        ).fetchone()
                    finally:
                        conn.close()
                if row:
                    writer.write(_http_response("200 OK", "application/json",
                                                row["samples_json"].encode()))
                else:
                    writer.write(_http_response("404 Not Found", "application/json", b"[]"))

        elif path == "/sessions/lap-samples":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            sid = qs.get("session_id", "")
            try:
                lap_n = int(qs.get("lap", "0"))
            except ValueError:
                lap_n = 0
            if not sid or not lap_n:
                writer.write(_http_response("400 Bad Request", "application/json",
                                            b'{"error":"session_id and lap required"}'))
            else:
                data = _db_get_lap_samples(sid, lap_n)
                if data:
                    writer.write(_http_response("200 OK", "application/json",
                                                json.dumps(data["samples"]).encode()))
                else:
                    writer.write(_http_response("404 Not Found", "application/json", b"[]"))

        elif path == "/sessions/update" and method == "POST":
            try:
                body_data = json.loads(raw_body)
            except (json.JSONDecodeError, ValueError) as exc:
                writer.write(_http_response("400 Bad Request", "application/json",
                                            json.dumps({"error": str(exc)}).encode()))
            else:
                sid = body_data.get("id", "")
                sessions_dir = storage_path() / "sessions"
                session_file = sessions_dir / f"{sid}.json"
                laps_file    = sessions_dir / f"{sid}_laps.json"
                try:
                    session_data = json.loads(session_file.read_text())
                except OSError:
                    writer.write(_http_response("404 Not Found", "application/json",
                                                json.dumps({"error": "Session not found"}).encode()))
                else:
                    # Update track
                    if "track" in body_data:
                        session_data["track"] = body_data["track"]

                    # Update race_type
                    if "race_type" in body_data:
                        session_data["race_type"] = body_data["race_type"]

                    # Update track name
                    if "track" in body_data:
                        session_data["track"] = body_data["track"]

                    # Update car
                    if "car" in body_data:
                        session_data["car"] = body_data["car"]

                    # Learn a new track ordinal mapping
                    if "learned_ordinal" in body_data:
                        lo = body_data["learned_ordinal"]
                        try:
                            _db_write_learned_ordinal(
                                int(lo["ordinal"]),
                                lo.get("game", "forza_motorsport"),
                                str(lo["track_name"]),
                            )
                        except (KeyError, TypeError, ValueError):
                            pass

                    # Drop last lap
                    if body_data.get("drop_last_lap") and session_data.get("laps"):
                        session_data["laps"] = session_data["laps"][:-1]
                        # Recalculate best
                        valid = [l["lap_time_s"] for l in session_data["laps"] if l.get("lap_time_s")]
                        session_data["best_lap_time_s"] = round(min(valid), 3) if valid else None
                        # Drop from laps detail file too
                        try:
                            laps_detail = json.loads(laps_file.read_text())
                            if laps_detail:
                                laps_detail = laps_detail[:-1]
                                laps_file.write_text(json.dumps(laps_detail, indent=2))
                        except OSError:
                            pass

                    session_file.write_text(json.dumps(session_data, indent=2))

                    # Sync to SQLite
                    db_kwargs = {}
                    if "track" in body_data:
                        db_kwargs["track"] = body_data["track"]
                    if "race_type" in body_data:
                        db_kwargs["race_type"] = body_data["race_type"]
                    if "track" in body_data:
                        db_kwargs["track"] = body_data["track"]
                    if "car" in body_data:
                        db_kwargs["car"] = body_data["car"]
                    if db_kwargs:
                        _db_update_session(sid, **db_kwargs)
                    if body_data.get("drop_last_lap"):
                        _db_drop_last_lap(sid)

                    writer.write(_http_response("200 OK", "application/json",
                                                json.dumps({"ok": True, "session": session_data}).encode()))

        elif path == "/analyze":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            sid   = qs.get("id", "")
            force = qs.get("force", "") == "true"
            sessions_dir  = storage_path() / "sessions"
            analysis_file = sessions_dir / f"{sid}_analysis.json"

            # Serve cached result unless caller requests a fresh one
            db_cached = _db_get_ai_analysis(sid)
            if not force and db_cached:
                writer.write(_http_response("200 OK", "application/json",
                                            json.dumps(db_cached).encode()))
            elif not force and analysis_file.exists():
                writer.write(_http_response("200 OK", "application/json", analysis_file.read_bytes()))
            else:
                # Get session from DB; fall back to JSON file
                with _db_lock:
                    conn = _db_connect()
                    try:
                        sess_row = conn.execute(
                            "SELECT * FROM sessions WHERE session_id=?", (sid,)
                        ).fetchone()
                    finally:
                        conn.close()
                session_data = dict(sess_row) if sess_row else None
                if not session_data:
                    try:
                        session_data = json.loads((sessions_dir / f"{sid}.json").read_text())
                    except OSError:
                        session_data = None
                try:
                    laps_data = json.loads((sessions_dir / f"{sid}_laps.json").read_text())
                except OSError:
                    laps_data = []
                if not session_data:
                    writer.write(_http_response("404 Not Found", "application/json",
                                                json.dumps({"error": "Session not found"}).encode()))
                else:
                    track = session_data.get("track", "unknown")
                    # Pull last 3 historical sessions at same track from DB
                    historical = []
                    if track and track != "unknown":
                        hist_rows = _db_track_sessions(track)
                        historical = [h for h in hist_rows if h["session_id"] != sid][:3]
                    try:
                        prompt   = _build_analysis_prompt(session_data, laps_data, historical)
                        analysis = await asyncio.to_thread(_call_claude_api, prompt)
                        result_obj = {
                            "session_id":  sid,
                            "analyzed_at": datetime.now().isoformat(),
                            "model":       config.get("anthropic_model", "claude-sonnet-4-6"),
                            "cached":      False,
                            "analysis":    analysis,
                        }
                        analysis_file.write_text(json.dumps(result_obj, indent=2))
                        _db_save_ai_analysis(sid, analysis,
                                             config.get("anthropic_model", "claude-sonnet-4-6"))
                        writer.write(_http_response("200 OK", "application/json",
                                                    json.dumps(result_obj).encode()))
                    except ValueError as exc:
                        writer.write(_http_response("400 Bad Request", "application/json",
                                                    json.dumps({"error": str(exc)}).encode()))
                    except Exception as exc:
                        log.error(f"Claude API error: {exc}")
                        writer.write(_http_response("502 Bad Gateway", "application/json",
                                                    json.dumps({"error": f"API error: {exc}"}).encode()))

        elif path == "/reset" and method == "POST":
            for game in PORTS:
                state["udp_received"][game] = 0
                state["udp_rejected"][game] = 0
                state["last_rejected_size"][game] = None
            writer.write(_http_response("200 OK", "application/json", b'{"ok":true}'))

        elif path == "/finish" and method == "POST":
            closed = []
            for game, session in list(active_sessions.items()):
                session.close()
                active_sessions.pop(game)
                closed.append(session.session_id)
            if closed:
                state["status"] = "race_ended"
                state["game"] = None
                asyncio.create_task(_clear_race_ended())
            writer.write(_http_response("200 OK", "application/json",
                                        json.dumps({"ok": True, "closed": closed}).encode()))

        elif path == "/admin" and method == "GET":
            writer.write(_http_response("200 OK", "text/html", ADMIN_HTML.encode()))

        elif path == "/admin/inject" and method == "POST":
            try:
                p = json.loads(raw_body)
            except (json.JSONDecodeError, ValueError) as exc:
                err = json.dumps({"error": f"Invalid JSON: {exc}"}).encode()
                writer.write(_http_response("400 Bad Request", "application/json", err))
            else:
                game = p.get("game", "forza_motorsport")
                if game not in PORTS:
                    err = json.dumps({"error": f"Unknown game: {game}"}).encode()
                    writer.write(_http_response("400 Bad Request", "application/json", err))
                else:
                    try:
                        packets = _build_inject_packets(game, p)
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        for pkt in packets:
                            sock.sendto(pkt, ("127.0.0.1", PORTS[game]))
                        sock.close()
                        result = json.dumps({"ok": True, "sent": len(packets)}).encode()
                        writer.write(_http_response("200 OK", "application/json", result))
                    except Exception as exc:
                        err = json.dumps({"error": str(exc)}).encode()
                        writer.write(_http_response("500 Internal Server Error", "application/json", err))

        elif path == "/browse":
            qs = {k: urllib.parse.unquote_plus(v)
                  for pair in query_string.split("&") if "=" in pair
                  for k, v in [pair.split("=", 1)]}
            browse_path = qs.get("path", "/") or "/"
            try:
                p = Path(browse_path)
                exists = p.is_dir()
                entries = []
                if exists:
                    try:
                        for item in sorted(p.iterdir()):
                            if item.is_dir() and not item.name.startswith("."):
                                entries.append({"name": item.name})
                    except PermissionError:
                        pass
                result = {
                    "path":          str(p.resolve()) if exists else str(p),
                    "parent":        str(p.parent),
                    "exists":        exists,
                    "parent_exists": p.parent.is_dir(),
                    "entries":       entries,
                }
            except Exception as exc:
                result = {
                    "path": browse_path, "parent": None,
                    "exists": False, "parent_exists": False,
                    "entries": [], "error": str(exc),
                }
            writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

        elif path == "/debug-stream":
            q: asyncio.Queue = asyncio.Queue(maxsize=2000)
            _debug_clients.append(q)
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/event-stream\r\n"
                b"Cache-Control: no-cache\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"Connection: keep-alive\r\n\r\n"
            )
            for line in list(_debug_buffer):
                writer.write(f"data: {json.dumps(line)}\n\n".encode())
            await writer.drain()
            try:
                while True:
                    line = await q.get()
                    writer.write(f"data: {json.dumps(line)}\n\n".encode())
                    await writer.drain()
            finally:
                if q in _debug_clients:
                    _debug_clients.remove(q)

        elif path == "/stream":
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/event-stream\r\n"
                b"Cache-Control: no-cache\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"Connection: keep-alive\r\n\r\n"
            )
            while True:
                data = f"data: {json.dumps(state)}\n\n"
                writer.write(data.encode())
                await writer.drain()
                await asyncio.sleep(0.1)  # 10 Hz

        elif path == "/health":
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")

        else:
            writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 9\r\n\r\nNot Found")

        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()

# ─── Main ─────────────────────────────────────────────────────────────────────

async def main(demo_mode: bool = False):
    global _listener_started_at
    _listener_started_at = time.time()
    ensure_storage()
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
        _DEMO_DB_PATH = _args.db
    if _args.port:
        STATUS_PORT = _args.port

    asyncio.run(main(demo_mode=_args.demo))
