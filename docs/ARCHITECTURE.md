# Pacefinder Architecture

## System Overview

Pacefinder is a self-contained Python application that listens for UDP telemetry from Forza Motorsport, stores racing sessions, and serves a web dashboard for live monitoring and analysis.

### Data Flow

```
┌─────────────────────────────────┐
│ Game (Forza Motorsport)         │
│ UDP Port 5300                   │
└────────────┬────────────────────┘
             │
┌────────────▼──────────────────────────────────────┐
│ listener.py (Main Entry Point)                    │
│ ├─ Starts HTTP server (port 8000)                │
│ ├─ Spins up TelemetryProtocol UDP listener       │
│ └─ Coordinates session manager                   │
└────────────┬──────────────────────────────────────┘
             │
    ┌────────┴────────┬──────────────────┐
    │                 │                  │
    ▼                 ▼                  ▼
┌─────────────┐ ┌───────────────┐ ┌──────────────┐
│Session      │ │SQLite DB      │ │Raw Archives  │
│Manager      │ │(store.py)     │ │(raw/*.bin)   │
│(manager.py) │ │               │ │              │
│             │ │• Sessions     │ │• Per-sample  │
│• Detects    │ │• Laps         │ │  telemetry   │
│  race start │ │• AI cache     │ │• Compression │
│• Tracks     │ │• References   │ │  optimized   │
│  lap state  │ └───────────────┘ └──────────────┘
│• Delegates  │
│  to storage │
└─────────────┘
                     ▲
                     │
                ┌────┴──────┐
                │            │
          ┌─────▼──┐   ┌─────▼──────┐
          │ Web UI │   │ API Routes │
          │(pages/)│   │ (api.py)   │
          └────────┘   └────────────┘
```

## Key Modules

### **listener.py** (Entry Point)
- Main process: starts HTTP server and UDP listener
- Coordinates between TelemetryProtocol, SessionManager, and database
- Handles graceful shutdown

### **net/** (Web Server & UI)
Provides the HTTP interface at port 8000.

| Module | Purpose |
|--------|---------|
| `router.py` | HTTP request routing, response handling, performance instrumentation |
| `api.py` | REST endpoints for telemetry injection and Claude AI integration |
| `perf.py` | Performance monitoring and request metrics |
| `pages/*.py` | Server-rendered HTML pages (home, dashboard, sessions, setup, etc.) |

**Pages** (`net/pages/`):
- `home.py` — Landing page with recent sessions and career stats
- `dashboard.py` — Live 10Hz telemetry stream (speed, throttle, brake, slip, temps)
- `sessions.py` — Session history browser with lap comparison and filtering
- `cars.py` — Car inventory and detail views
- `telemetry.py` — Detailed telemetry analysis and visualization
- `setup.py` — Configuration UI (storage path, API keys, port settings)
- `admin.py` — Admin debug panel (visible only in debug mode)
- `events.py` — Race events breakdown (overtakes, crashes, pit stops)

### **session/** (Session Lifecycle & State)
Manages the state machine for active racing sessions.

| Module | Purpose | Size |
|--------|---------|------|
| `manager.py` | Session coordinator—detects start/end, tracks lap state, delegates to storage | 56k LOC |
| `protocol.py` | TelemetryProtocol: receives UDP packets, parses them via parser modules | 6.8k LOC |
| `watchdog.py` | Session timeout detection and race-end logic | 1.8k LOC |

**How it works:**
1. `protocol.py` receives UDP packets and routes to the active parser
2. `watchdog.py` detects session boundaries (race start, race end, idle timeout)
3. `manager.py` accumulates lap-level state (current lap, sector times, samples)
4. On lap completion or session end, `manager.py` writes to database via `store.py`

### **parsers/** (Game-Specific Packet Decoders)
Each parser decodes binary telemetry packets from a specific game.

| Parser | Game | Status |
|--------|------|--------|
| `forza.py` | Forza Motorsport 2023+ | Active ✓ |
| `acc.py` | Assetto Corsa Competizione | Parked |
| `f1.py` | Codemasters F1 2023/2024 | Parked |

**Parser Interface:**
Each parser must expose a `parse(packet: bytes) -> dict` function that returns telemetry fields (speed, throttle, brake, lap_time, etc.).

### **db/** (SQLite Data Store)
Persistent storage layer.

| Module | Purpose | Size |
|--------|---------|------|
| `store.py` | Database schema, queries, and session persistence | 64.5k LOC |

**What's stored:**
- Sessions (metadata, race type, date)
- Laps (lap number, time, sector times, events)
- Telemetry samples (per-lap raw data, compressed)
- AI coaching cache (Claude API responses)
- Car/track reference data (ordinals, names)

### **reference/** (Lookup Tables & Metadata)
Game-specific reference data and ordinal resolution.

| Module | Purpose |
|--------|---------|
| `loader.py` | Load CSV reference data, sync with database |
| `data/fm8_cars.csv` | Car ordinal → make/model/year lookup |
| `data/fm8_tracks.csv` | Track ordinal → track name lookup |

### **analysis/** (Post-Race Analysis Tools)
High-level analysis after a session ends.

| Module | Purpose |
|--------|---------|
| `deepdive.py` | Detailed lap-by-lap telemetry breakdown |
| `events.py` | Race event classification (overtakes, crashes, pit stops) |

### **scripts/** (Maintenance & Debugging Tools)
Utility scripts for database maintenance and testing.

| Script | Purpose |
|--------|---------|
| `clean_test_sessions.py` | Remove test sessions from database |
| `smoke_test.py` | Integration test runner |
| `backfill_lap_sectors.py` | Compute sector deltas retroactively |
| `backfill_lap_aggregates.py` | Recalculate lap statistics |
| `backfill_lap_events.py` | Detect race events in archived sessions |
| `recompress_samples.py` | Re-encode telemetry samples for compression |
| `monte_carlo_session.py` | Synthetic session generator (for testing) |

See `scripts/README.md` for details.

### **replay.py** (CLI Tool)
Re-parse archived `.bin` files without the listener running. Useful for:
- Extracting session data from old backups
- Exporting to CSV/JSON for external analysis
- Debugging parser issues

Usage: `python3 replay.py archive.bin [--summary|--csv]`

## Configuration

### Runtime Config
Stored in `simtelemetry.config.json` (auto-created on first run):
```json
{
  "storage_path": "./data",
  "api_port": 8000,
  "udp_port": 5300,
  "anthropic_api_key": ""
}
```

Modified via the `/setup` page in the web UI.

### Code Config
`config.py` defines constants:
- `SESSION_TIMEOUT_S` — Idle time before session ends
- `IDLE_TIMEOUT_S` — Inactivity threshold
- `MIN_VALID_LAP_S` — Minimum lap duration to count as valid

## Static Assets

### JavaScript (`static/js/`)
Page-specific interactivity and live data updates.

| File | Purpose |
|------|---------|
| `dashboard.js` | Live 10Hz telemetry updates and visualization |
| `sessions.js` | Session list filtering and pagination |
| `charts.js` | Charting library wrapper (Chart.js) |
| `widgets/autocomplete.js` | Reusable search/filter widget |

### CSS (`static/css/`)
Modular stylesheets following a token-based design system.

| File | Scope |
|------|-------|
| `tokens.css` | Design tokens (colors, typography, spacing) |
| `base.css` | Base typography and layout rules |
| `dashboard.css` | Live dashboard layout and widgets |
| `sessions.css` | Session browser layout |
| `widgets/autocomplete.css` | Autocomplete widget styles |

## Adding New Features

### Adding a Parser for a New Game
1. Create `parsers/newgame.py` with a `parse(packet: bytes) -> dict` function
2. Return the standard telemetry dict (speed, throttle, brake, lap_time, etc.)
3. Import in `protocol.py` and add to the dispatcher
4. Update `parsers/__init__.py` to export the new parser

### Adding a New Page
1. Create `net/pages/newpage.py` with a page handler function
2. Return an HTML string (can use template strings or `net/pages/base.py` helpers)
3. Add a route in `router.py`
4. Link from the navigation (typically in a nav footer or header)

### Updating the Database Schema
1. Modify the schema in `db/store.py`
2. Run backfill scripts to update existing data (e.g., `backfill_lap_aggregates.py`)
3. Test with `scripts/smoke_test.py`

## Performance Notes

### Large Files
- **manager.py (56k LOC)**: Session lifecycle coordinator. Responsibilities are clearly delimited by internal function groups.
- **store.py (64.5k LOC)**: Database schema and query layer. Organized by table/entity (sessions, laps, samples, cache, references).

These are large because they're handling domain-specific complexity, not architectural confusion.

### Compression
Telemetry samples are stored compressed (pickle + gzip) in SQLite BLOBs to keep database size reasonable for long-term archival. See `recompress_samples.py` for re-encoding.

## Testing

- `test_listener.py` — Integration tests for packet parsing, session state, and database writes
- Run with: `python3 test_listener.py`
- See `docs/dev/TESTING.md` for unit test conventions

## Deployment

- **Linux/Pi**: Systemd service (`pacefinder.service`)
- **macOS**: Launchd service (installed via `install-mac.sh`)
- **Windows**: Task Scheduler entry (manual setup in README)

## Technology Stack

- **Language**: Python 3.9+
- **Web**: Pure Python HTTP server (asyncio)
- **Database**: SQLite with pickle/gzip compression
- **Frontend**: Vanilla JavaScript, Chart.js, CSS Grid/Flexbox
- **Optional AI**: Anthropic Claude API (for coaching)
- **Deployment**: systemd, launchd, or Windows Task Scheduler
