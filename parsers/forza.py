import struct
from typing import Optional

# FM2023 Data Out "Car Dash" packet: 311 bytes
# Reference: https://support.forzamotorsport.net/hc/en-us/articles/21742934024211

FM_PACKET_SIZE    = 311  # Forza Motorsport 2023 / FM7 Car Dash
FM_PACKET_SIZE_FH = 331  # Forza Horizon 4 / 5 Car Dash (adds tire wear + track ordinal)

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


def parse_forza(data: bytes, get_tracks, unknown_ordinals_seen: set, log_fn) -> Optional[dict]:
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
            track_name = get_tracks().get(ord_val)
            if ord_val and track_name is None and ord_val not in unknown_ordinals_seen:
                unknown_ordinals_seen.add(ord_val)
                log_fn.warning(f"Unknown FH5 track ordinal {ord_val} — add to FORZA_TRACKS once identified")
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
