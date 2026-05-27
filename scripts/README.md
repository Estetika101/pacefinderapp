# Scripts

Utility scripts for maintenance, testing, and data management. These are one-off tools, not part of the core listener process.

## Database Maintenance

Use these to backfill or clean up session data.

### `clean_test_sessions.py`
Remove test sessions from the database that were created during development.

```bash
python3 scripts/clean_test_sessions.py
```

### `backfill_lap_sectors.py`
Compute sector deltas retroactively for existing sessions (useful after data import or schema changes).

```bash
python3 scripts/backfill_lap_sectors.py
```

### `backfill_lap_aggregates.py`
Recalculate lap statistics (min/max speed, avg throttle, etc.) for existing laps.

```bash
python3 scripts/backfill_lap_aggregates.py
```

### `backfill_lap_events.py`
Detect and classify race events (overtakes, crashes, pit stops) in archived sessions.

```bash
python3 scripts/backfill_lap_events.py
```

### `recompress_samples.py`
Re-encode telemetry samples in the database (useful for compression optimization when storage format changes).

```bash
python3 scripts/recompress_samples.py
```

## Testing

Use these for testing and validation.

### `smoke_test.py`
Integration test runner. Validates parser, session manager, and database layer with a synthetic race session.

```bash
python3 scripts/smoke_test.py
```

Run this after schema changes to ensure no regressions.

### `monte_carlo_session.py`
Generate a synthetic race session with randomized telemetry data. Useful for:
- Testing new features without needing real telemetry
- Performance testing with large datasets
- Reproducing edge cases

```bash
python3 scripts/monte_carlo_session.py [num_laps] [num_samples_per_lap]
```

## Adding a New Script

1. Create `scripts/myscript.py` in this directory
2. Add a `main()` function with your logic
3. Add this at the end:
```python
if __name__ == "__main__":
    main()
```
4. Run with `python3 scripts/myscript.py`
5. Document it in this README

## Notes

- Scripts assume the database and config file exist (they're created by `listener.py`)
- Always test on a copy of your database before running backfill scripts on production data
- Scripts can be run while the listener is stopped; don't run them while the listener is active

---

For more context on the codebase, see `docs/ARCHITECTURE.md`.
