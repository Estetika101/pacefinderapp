import asyncio
import json
import socket
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

from net.perf import _perf_ctx, _perf_ring, _perf_client_ring, _PERF_LOG_THRESHOLD_MS


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


def make_handler(ctx: dict):
    state                  = ctx["state"]
    config                 = ctx["config"]
    log                    = ctx["log"]
    PORTS                  = ctx["PORTS"]
    active_sessions        = ctx["active_sessions"]
    debug_clients          = ctx["debug_clients"]
    debug_buffer           = ctx["debug_buffer"]
    started_at             = ctx["started_at"]          # mutable list [float|None]
    static_dir             = ctx["static_dir"]
    DASHBOARD_HTML         = ctx["DASHBOARD_HTML"]
    SETUP_HTML             = ctx["SETUP_HTML"]
    ADMIN_HTML             = ctx["ADMIN_HTML"]
    GAMES_HTML             = ctx["GAMES_HTML"]
    TRACKS_HTML            = ctx["TRACKS_HTML"]
    TRACK_DETAIL_HTML      = ctx["TRACK_DETAIL_HTML"]
    SESSION_DETAIL_HTML    = ctx["SESSION_DETAIL_HTML"]
    TELEMETRY_HTML         = ctx["TELEMETRY_HTML"]
    DEBUG_RAW_HTML         = ctx["DEBUG_RAW_HTML"]
    DEBUG_PERF_HTML        = ctx["DEBUG_PERF_HTML"]
    last_parsed            = ctx["last_parsed"]
    get_local_ips          = ctx["get_local_ips"]
    disk_info              = ctx["disk_info"]
    save_config            = ctx["save_config"]
    storage_path           = ctx["storage_path"]
    effective_tracks       = ctx["effective_tracks"]
    FM2023_TRACKS          = ctx["FM2023_TRACKS"]
    FORZA_CARS             = ctx["FORZA_CARS"]
    db_sessions_list       = ctx["db_sessions_list"]
    db_games_index         = ctx["db_games_index"]
    db_career_kpis         = ctx["db_career_kpis"]
    db_form_data           = ctx["db_form_data"]
    db_recent_sessions     = ctx["db_recent_sessions"]
    db_tracks_index        = ctx["db_tracks_index"]
    db_track_sessions      = ctx["db_track_sessions"]
    db_get_track_tip       = ctx["db_get_track_tip"]
    db_save_track_tip      = ctx["db_save_track_tip"]
    build_track_tip_prompt = ctx["build_track_tip_prompt"]
    call_claude_api        = ctx["call_claude_api"]
    db_connect             = ctx["db_connect"]
    db_lock                = ctx["db_lock"]
    db_get_ai_analysis     = ctx["db_get_ai_analysis"]
    db_save_ai_analysis    = ctx["db_save_ai_analysis"]
    db_update_session      = ctx["db_update_session"]
    db_drop_last_lap       = ctx["db_drop_last_lap"]
    db_delete_session      = ctx["db_delete_session"]
    db_write_learned_ordinal = ctx["db_write_learned_ordinal"]
    db_get_car_nickname = ctx["db_get_car_nickname"]
    db_get_car_nicknames = ctx["db_get_car_nicknames"]
    db_set_car_nickname = ctx["db_set_car_nickname"]
    db_get_lap_samples     = ctx["db_get_lap_samples"]
    db_get_all_lap_samples = ctx["db_get_all_lap_samples"]
    decode_samples         = ctx["decode_samples"]
    build_inject_packets   = ctx["build_inject_packets"]
    build_analysis_prompt  = ctx["build_analysis_prompt"]
    clear_race_ended       = ctx["clear_race_ended"]

    async def handle_status(reader, writer):
        # Per-request perf state — populated once we know the path.
        _perf_token = None
        _perf_started = time.perf_counter()
        _perf_method = "?"
        _perf_path = "?"
        # Wrap writer.write so we can sum response bytes for the perf log.
        _bytes_written = [0]
        _orig_write = writer.write
        def _counting_write(data):
            try:
                _bytes_written[0] += len(data)
            except TypeError:
                pass
            return _orig_write(data)
        writer.write = _counting_write
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

            _perf_method = method
            _perf_path = path
            _perf_token = _perf_ctx.set({"db_ms": 0.0})

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
                static_file = static_dir / rel
                if static_file.is_file() and static_file.resolve().is_relative_to(static_dir.resolve()):
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
                uptime = int(time.time() - started_at[0]) if started_at[0] else 0
                payload = {
                    "ips": get_local_ips(),
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

            elif path == "/debug/raw":
                writer.write(_http_response("200 OK", "text/html", DEBUG_RAW_HTML.encode()))

            elif path == "/debug/raw.json":
                writer.write(_http_response("200 OK", "application/json", json.dumps(last_parsed).encode()))

            elif path == "/debug/perf":
                # Two flavors: HTML inspector (default) and ?json=1 raw dump.
                if "json=1" in query_string:
                    payload = {
                        "server": list(_perf_ring),
                        "client": list(_perf_client_ring),
                    }
                    writer.write(_http_response("200 OK", "application/json", json.dumps(payload).encode()))
                else:
                    writer.write(_http_response("200 OK", "text/html", DEBUG_PERF_HTML.encode()))

            elif path == "/debug/perf/client" and method == "POST":
                # Rate limit: drop entries that arrive within 200ms of the last
                # entry from the same path. Cheap defense against polling spam.
                try:
                    payload = json.loads(raw_body) if raw_body else {}
                    now = time.time()
                    p = payload.get("path", "?")
                    last = next((e for e in reversed(_perf_client_ring) if e.get("path") == p), None)
                    if last is None or (now - last.get("ts", 0)) > 0.2:
                        _perf_client_ring.append({
                            "ts": now,
                            "path": p,
                            "ua": payload.get("ua", "")[:80],
                            "marks": payload.get("marks", {}),
                        })
                    writer.write(_http_response("204 No Content", "text/plain", b""))
                except Exception:
                    writer.write(_http_response("400 Bad Request", "text/plain", b"bad json"))

            elif path in ("/sessions", "/sessions/"):
                # Forza is the only active game; serve the per-game overview as the home page.
                # See docs/specs/park-acc-f1.md.
                writer.write(_http_response("200 OK", "text/html", TRACKS_HTML.encode()))

            elif path == "/sessions/game":
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                name = qs.get("name", "")
                if name in ("acc", "f1"):
                    # ACC + F1 are parked — see docs/specs/park-acc-f1.md
                    writer.write(_http_response(
                        "404 Not Found", "text/plain",
                        b"This game's support is currently parked.",
                    ))
                else:
                    # forza_motorsport (or missing) → 301 to canonical /sessions
                    writer.write(_http_response(
                        "301 Moved Permanently", "text/plain", b"",
                        "Location: /sessions\r\n",
                    ))

            elif path == "/sessions/track":
                writer.write(_http_response("200 OK", "text/html", TRACK_DETAIL_HTML.encode()))

            elif path == "/sessions/session":
                writer.write(_http_response("200 OK", "text/html", SESSION_DETAIL_HTML.encode()))

            elif path == "/sessions/telemetry":
                writer.write(_http_response("200 OK", "text/html", TELEMETRY_HTML.encode()))

            elif path == "/sessions/data":
                result = db_sessions_list(100)
                writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

            elif path == "/sessions/games":
                result = db_games_index()
                writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

            elif path == "/sessions/career":
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                result = db_career_kpis(qs.get("game") or None)
                writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

            elif path == "/sessions/track-options":
                # Merged unique track-name list for the session edit modal dropdown.
                # Sources combined: FM2023_TRACKS hardcoded list +
                # FORZA_TRACKS values from CSVs (incl. fm8_tracks_extended.csv) +
                # learned_track_ordinals from prior user confirmations.
                # See docs/specs/post-race-track-dropdown.md.
                names = set(FM2023_TRACKS)
                names.update(effective_tracks().values())
                # Filter out the placeholder "unknown" entry — it's reserved for the
                # blank state in the UI and shouldn't appear as a selectable option.
                names.discard("unknown")
                result = sorted(names)
                writer.write(_http_response("200 OK", "application/json",
                                            json.dumps(result).encode()))

            elif path == "/cars/nicknames" and method == "GET":
                # Full {ordinal: nickname} map. Cheap lookup; no pagination.
                writer.write(_http_response("200 OK", "application/json",
                                            json.dumps(db_get_car_nicknames()).encode()))

            elif path == "/cars/nickname" and method == "POST":
                # Body: {"ordinal": int, "nickname": "..."}; nickname=""/null deletes.
                try:
                    body = json.loads(raw_body) if raw_body else {}
                    ordinal = int(body.get("ordinal"))
                except (ValueError, TypeError, json.JSONDecodeError):
                    writer.write(_http_response("400 Bad Request", "application/json",
                                                json.dumps({"error": "ordinal required"}).encode()))
                else:
                    nick = body.get("nickname")
                    db_set_car_nickname(ordinal, nick if nick else None)
                    writer.write(_http_response("200 OK", "application/json",
                                                json.dumps({"ok": True, "ordinal": ordinal,
                                                            "nickname": nick or None}).encode()))

            elif path == "/sessions/form":
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                rt   = qs.get("type", "all") or "all"
                last = int(qs.get("last", "10") or "10")
                result = db_form_data(rt if rt != "all" else None, last, qs.get("game") or None)
                writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

            elif path == "/sessions/recent":
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                _limit = int(qs.get("limit", "8") or "8")
                result = db_recent_sessions(_limit, qs.get("game") or None)
                writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

            elif path == "/sessions/tracks":
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                game_filter = qs.get("game", "") or None
                result = db_tracks_index(game_filter)
                writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

            elif path == "/sessions/track/data":
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                track_name = qs.get("name", "")
                game_filter = qs.get("game", "") or None
                result = db_track_sessions(track_name, game_filter)
                writer.write(_http_response("200 OK", "application/json", json.dumps(result).encode()))

            elif path == "/sessions/track/tip":
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                track_name = qs.get("name", "")
                generate   = qs.get("generate", "") == "true"
                cached = db_get_track_tip(track_name)
                if cached:
                    writer.write(_http_response("200 OK", "application/json",
                                                json.dumps(cached).encode()))
                elif generate and config.get("anthropic_api_key", "").strip():
                    try:
                        stats = next((t for t in db_tracks_index() if t["track"] == track_name), {})
                        tip_prompt = build_track_tip_prompt(track_name, stats)
                        tip_text   = await asyncio.to_thread(call_claude_api, tip_prompt)
                        tip_text   = tip_text.strip().split("\n")[0][:200]
                        model_name = config.get("anthropic_model", "claude-sonnet-4-6")
                        db_save_track_tip(track_name, tip_text, model_name)
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
                with db_lock:
                    conn = db_connect()
                    try:
                        cd_row = conn.execute(
                            "SELECT session_id,game,track,car,session_type,race_type,"
                            "started_at,ended_at,best_lap_time_s,lap_count,track_ordinal,"
                            "weather_condition,tyre_compound "
                            "FROM sessions WHERE session_id=?", (sid,)
                        ).fetchone()
                    finally:
                        conn.close()
                if not cd_row:
                    writer.write(_http_response("404 Not Found", "application/json",
                                                json.dumps({"error": "Session not found"}).encode()))
                else:
                    cd_dict = dict(cd_row)
                    # Merge FM2023's hardcoded canonical circuits with the CSV-backed
                    # FORZA_TRACKS so the post-race dropdown shows every known track,
                    # not just the FH5 ordinals. Same source-of-truth as
                    # /sessions/track-options. See docs/specs/post-race-track-dropdown.md.
                    names = set(FM2023_TRACKS)
                    names.update(effective_tracks().values())
                    names.discard("unknown")
                    track_names = sorted(names)
                    writer.write(_http_response("200 OK", "application/json", json.dumps({
                        "session":       cd_dict,
                        "track_list":    track_names,
                        "track_ordinal": cd_dict.get("track_ordinal"),
                    }).encode()))

            elif path == "/sessions/session/data":
                # Pure-SQL handler — per-lap aggregates are precomputed at session
                # close (see compute_lap_aggregates in db/store.py). Was reading
                # <sid>_laps.json from disk and iterating every sample on each
                # request, which made p95 500–1450 ms. See PR #63 / spec
                # docs/specs/perf-session-data-precompute.md.
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                sid = qs.get("id", "")
                with db_lock:
                    conn = db_connect()
                    try:
                        sess_row = conn.execute(
                            "SELECT session_id,game,track,car,session_type,race_type,started_at,ended_at,"
                            "best_lap_time_s,lap_count,ai_analysis,ai_analyzed_at,ai_model,"
                            "car_class,car_pi,car_ordinal,drivetrain_type,num_cylinders,"
                            "finish_pos,grid_pos,weather_condition,tyre_compound,track_temp_c,air_temp_c "
                            "FROM sessions WHERE session_id=?", (sid,)
                        ).fetchone()
                        lap_rows = conn.execute(
                            "SELECT lap_number,lap_time_s,max_speed_mph,"
                            "avg_throttle,avg_brake,avg_slip,peak_slip,slip_above_pct "
                            "FROM laps WHERE session_id=? ORDER BY lap_number",
                            (sid,)
                        ).fetchall() if sess_row else []
                    finally:
                        conn.close()
                if not sess_row:
                    writer.write(_http_response("404 Not Found", "application/json",
                                                json.dumps({"error": "Session not found"}).encode()))
                else:
                    sess_dict = dict(sess_row)
                    # Resolve the car name. Two legacy cases + the new
                    # car_ordinal column from Bundle 2:
                    #   1) `car` stored as a numeric string → look up
                    #   2) `car` is "Unknown Car" (or "unknown") AND we now
                    #      have car_ordinal → re-attempt lookup; if still
                    #      unmapped, surface the raw ordinal so the user can
                    #      identify it (see issue #6 / cars bundle)
                    car_val = sess_dict.get("car", "")
                    car_ord = sess_dict.get("car_ordinal")
                    if car_val and isinstance(car_val, str) and car_val.isdigit():
                        car_ord = int(car_val)
                    if car_ord is not None:
                        car_info = FORZA_CARS.get(int(car_ord))
                        if car_info:
                            sess_dict["car"] = f"{car_info.get('year','')} {car_info['name']}".strip()
                        elif not car_val or car_val.lower().startswith("unknown") or (isinstance(car_val, str) and car_val.isdigit()):
                            sess_dict["car"] = f"Unknown Car (#{car_ord})"
                        # Bundle 3: surface user-set nickname for this ordinal
                        # so the UI can display it in priority over the
                        # resolved/fallback name (see Bundle 3 PR).
                        sess_dict["car_nickname"] = db_get_car_nickname(int(car_ord))
                    laps = [dict(r) for r in lap_rows]
                    writer.write(_http_response("200 OK", "application/json",
                                                json.dumps({"session": sess_dict, "laps": laps}).encode()))

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
                    with db_lock:
                        conn = db_connect()
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
                        with db_lock:
                            conn = db_connect()
                            try:
                                srow = conn.execute(
                                    "SELECT started_at FROM sessions WHERE session_id=?",
                                    (r["session_id"],)
                                ).fetchone()
                            finally:
                                conn.close()
                        # Get lap time from laps table
                        with db_lock:
                            conn = db_connect()
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
                            with db_lock:
                                conn = db_connect()
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
                    with db_lock:
                        conn = db_connect()
                        try:
                            row = conn.execute(
                                "SELECT samples_json FROM track_references "
                                "WHERE track=? AND reference_type=?",
                                (track_q, ref_type)
                            ).fetchone()
                        finally:
                            conn.close()
                    if row:
                        # samples_json is now gzipped (legacy rows are still
                        # accepted via the sniff in _decode_samples).
                        decoded = decode_samples(row["samples_json"])
                        writer.write(_http_response("200 OK", "application/json",
                                                    json.dumps(decoded).encode()))
                    else:
                        # No row yet for this track is normal (first session at
                        # a track, or before track_references is computed) —
                        # not a real "not found." Return an empty array as 200
                        # so it doesn't show up as a red 404 in dev tools. The
                        # client treats [] and 404+[] identically anyway.
                        writer.write(_http_response("200 OK", "application/json", b"[]"))

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
                    data = db_get_lap_samples(sid, lap_n)
                    if data:
                        writer.write(_http_response("200 OK", "application/json",
                                                    json.dumps(data["samples"]).encode()))
                    else:
                        # Lap with no stored samples is normal for older sessions
                        # that pre-date the lap_samples migration — return an
                        # empty array as 200 so it doesn't read as a real error
                        # in dev tools. Client treats [] and 404+[] identically.
                        writer.write(_http_response("200 OK", "application/json", b"[]"))

            elif path == "/sessions/session/deepdive":
                # Compute the Deep Dive tab payload from a session's stored
                # lap_samples + the sessions/laps rows. Pure compute — no DB
                # writes, no external calls. See docs/specs/deep-dive-tab.md.
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                sid = qs.get("id", "")
                ref_lap = qs.get("ref")
                cmp_lap = qs.get("cmp")
                try:
                    ref_lap = int(ref_lap) if ref_lap is not None else None
                    cmp_lap = int(cmp_lap) if cmp_lap is not None else None
                except ValueError:
                    ref_lap = cmp_lap = None
                with db_lock:
                    conn = db_connect()
                    try:
                        sess_row = conn.execute(
                            "SELECT session_id,game,track,car,session_type,race_type,"
                            "best_lap_time_s,lap_count,grid_pos,finish_pos "
                            "FROM sessions WHERE session_id=?", (sid,)
                        ).fetchone()
                        lap_rows = conn.execute(
                            "SELECT lap_number,lap_time_s,max_speed_mph,"
                            "avg_throttle,avg_brake,avg_slip,peak_slip,slip_above_pct "
                            "FROM laps WHERE session_id=? ORDER BY lap_number",
                            (sid,)
                        ).fetchall() if sess_row else []
                    finally:
                        conn.close()
                if not sess_row:
                    writer.write(_http_response("404 Not Found", "application/json",
                                                json.dumps({"error": "Session not found"}).encode()))
                else:
                    laps_with_samples = db_get_all_lap_samples(sid)
                    from analysis.deepdive import compute_deepdive
                    payload = compute_deepdive(
                        sess=dict(sess_row),
                        laps=[dict(r) for r in lap_rows],
                        laps_with_samples=laps_with_samples,
                        ref_lap=ref_lap,
                        cmp_lap=cmp_lap,
                    )
                    writer.write(_http_response("200 OK", "application/json",
                                                json.dumps(payload).encode()))

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

                        # Update weather condition (Dry / Damp / Wet / Snow)
                        if "weather_condition" in body_data:
                            wc = body_data["weather_condition"]
                            session_data["weather_condition"] = wc if wc else None

                        # Update tyre compound (FM: Soft / Medium / Hard / Wet)
                        if "tyre_compound" in body_data:
                            tc = body_data["tyre_compound"]
                            session_data["tyre_compound"] = tc if tc else None

                        # Learn a new track ordinal mapping
                        if "learned_ordinal" in body_data:
                            lo = body_data["learned_ordinal"]
                            try:
                                db_write_learned_ordinal(
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
                        if "car" in body_data:
                            db_kwargs["car"] = body_data["car"]
                        if "weather_condition" in body_data:
                            wc = body_data["weather_condition"]
                            db_kwargs["weather_condition"] = wc if wc else None
                        if "tyre_compound" in body_data:
                            tc = body_data["tyre_compound"]
                            db_kwargs["tyre_compound"] = tc if tc else None
                        if db_kwargs:
                            db_update_session(sid, **db_kwargs)
                        if body_data.get("drop_last_lap"):
                            db_drop_last_lap(sid)

                        writer.write(_http_response("200 OK", "application/json",
                                                    json.dumps({"ok": True, "session": session_data}).encode()))

            elif path == "/sessions/delete" and method == "POST":
                # Permanently remove a session from DB tables AND backing
                # files on disk. Used by the Edit modal's Delete button and
                # by the bulk-cleanup script. No undo — caller is expected
                # to confirm before posting.
                try:
                    body_data = json.loads(raw_body)
                except (json.JSONDecodeError, ValueError) as exc:
                    writer.write(_http_response("400 Bad Request", "application/json",
                                                json.dumps({"error": str(exc)}).encode()))
                else:
                    sid = body_data.get("id", "")
                    if not sid:
                        writer.write(_http_response("400 Bad Request", "application/json",
                                                    b'{"error":"id required"}'))
                    else:
                        deleted = db_delete_session(sid)
                        sessions_dir = storage_path() / "sessions"
                        raw_dir      = storage_path() / "raw"
                        for f in [
                            sessions_dir / f"{sid}.json",
                            sessions_dir / f"{sid}_laps.json",
                            sessions_dir / f"{sid}_analysis.json",
                            raw_dir      / f"{sid}.bin",
                        ]:
                            if f.exists():
                                try:
                                    f.unlink()
                                except OSError as exc:
                                    log.warning(f"Could not remove {f}: {exc}")
                        writer.write(_http_response("200 OK", "application/json",
                                                    json.dumps({"ok": True, "deleted": deleted}).encode()))

            elif path == "/analyze":
                qs = {k: urllib.parse.unquote_plus(v)
                      for pair in query_string.split("&") if "=" in pair
                      for k, v in [pair.split("=", 1)]}
                sid   = qs.get("id", "")
                force = qs.get("force", "") == "true"
                sessions_dir  = storage_path() / "sessions"
                analysis_file = sessions_dir / f"{sid}_analysis.json"

                # Serve cached result unless caller requests a fresh one
                db_cached = db_get_ai_analysis(sid)
                if not force and db_cached:
                    writer.write(_http_response("200 OK", "application/json",
                                                json.dumps(db_cached).encode()))
                elif not force and analysis_file.exists():
                    writer.write(_http_response("200 OK", "application/json", analysis_file.read_bytes()))
                else:
                    # Get session from DB; fall back to JSON file
                    with db_lock:
                        conn = db_connect()
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
                            hist_rows = db_track_sessions(track)
                            historical = [h for h in hist_rows if h["session_id"] != sid][:3]
                        try:
                            prompt   = build_analysis_prompt(session_data, laps_data, historical)
                            analysis = await asyncio.to_thread(call_claude_api, prompt)
                            result_obj = {
                                "session_id":  sid,
                                "analyzed_at": datetime.now().isoformat(),
                                "model":       config.get("anthropic_model", "claude-sonnet-4-6"),
                                "cached":      False,
                                "analysis":    analysis,
                            }
                            analysis_file.write_text(json.dumps(result_obj, indent=2))
                            db_save_ai_analysis(sid, analysis,
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
                    asyncio.create_task(clear_race_ended())
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
                            packets = build_inject_packets(game, p)
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
                debug_clients.append(q)
                writer.write(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/event-stream\r\n"
                    b"Cache-Control: no-cache\r\n"
                    b"Access-Control-Allow-Origin: *\r\n"
                    b"Connection: keep-alive\r\n\r\n"
                )
                for line in list(debug_buffer):
                    writer.write(f"data: {json.dumps(line)}\n\n".encode())
                await writer.drain()
                try:
                    while True:
                        line = await q.get()
                        writer.write(f"data: {json.dumps(line)}\n\n".encode())
                        await writer.drain()
                finally:
                    if q in debug_clients:
                        debug_clients.remove(q)

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
            try:
                total_ms = (time.perf_counter() - _perf_started) * 1000
                ctx_perf = _perf_ctx.get() or {"db_ms": 0.0}
                db_ms = ctx_perf.get("db_ms", 0.0)
                bytes_out = _bytes_written[0]
                # Skip noisy paths (long-lived SSE, polling instrument endpoints)
                # to keep the log signal-rich and the ring buffer representative.
                _perf_skip = (
                    _perf_path.startswith("/events")
                    or _perf_path == "/debug/perf"
                    or _perf_path == "/debug/perf/client"
                    or _perf_path == "/debug/raw.json"
                )
                if not _perf_skip:
                    _perf_ring.append({
                        "ts": time.time(),
                        "method": _perf_method,
                        "path": _perf_path,
                        "total_ms": round(total_ms, 1),
                        "db_ms": round(db_ms, 1),
                        "bytes": bytes_out,
                    })
                    line = (f"perf method={_perf_method} path={_perf_path} "
                            f"total_ms={total_ms:.1f} db_ms={db_ms:.1f} bytes={bytes_out}")
                    if total_ms > _PERF_LOG_THRESHOLD_MS:
                        log.info(line)
                    else:
                        log.debug(line)
            except Exception:
                pass
            if _perf_token is not None:
                try:
                    _perf_ctx.reset(_perf_token)
                except (LookupError, ValueError):
                    pass
            writer.close()

    return handle_status
