# Contributing to Pacefinder

Thanks for considering contributing! This guide will help you get started.

## Getting Started

### Prerequisites
- Python 3.9+
- Git

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/Estetika101/pacefinderapp.git
cd pacefinderapp
```

2. Run the listener:
```bash
python3 listener.py
```

3. Open `http://localhost:8000` in your browser and test against your game.

### Running Tests
```bash
python3 -m pytest tests/
```

Or for the legacy test runner:
```bash
python3 test_listener.py
```

## Contributing Changes

### Before You Start
- Check if there's an [open issue](https://github.com/Estetika101/pacefinderapp/issues) or discussion first
- For major features, consider opening a discussion to get feedback before starting work

### Making Changes

1. **Create a feature branch** from `main`:
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes** and test thoroughly:
   - If modifying a page, verify it renders correctly in your browser
   - If modifying the parser, test with real telemetry (or use `scripts/monte_carlo_session.py`)
   - If modifying the database, run backfill scripts on test data

3. **Commit with clear messages**:
```bash
git commit -m "Add feature: brief description"
```

4. **Push your branch and open a pull request**:
```bash
git push origin feature/your-feature-name
```

## How to Contribute

### Reporting Bugs
- Check the [issues](https://github.com/Estetika101/pacefinderapp/issues) to see if it's already reported
- Include: Python version, OS, game version, and steps to reproduce
- Attach relevant log files or screenshots if helpful

### Suggesting Features
- Open an [issue](https://github.com/Estetika101/pacefinderapp/issues) or start a [discussion](https://github.com/Estetika101/pacefinderapp/discussions)
- Describe the use case and how it improves the experience

### Common Tasks

#### Adding Support for a New Game

See `docs/ARCHITECTURE.md#Adding a Parser for a New Game`

Quick checklist:
1. Create `parsers/newgame.py` with `parse(packet: bytes) -> dict`
2. Return standard telemetry fields: `speed_mph`, `throttle_pct`, `brake_pct`, `lap_time_s`, etc.
3. Import in `session/protocol.py` and add to packet dispatcher
4. Test with real telemetry or synthetic data from `scripts/monte_carlo_session.py`

#### Adding a New Dashboard Page

See `docs/ARCHITECTURE.md#Adding a New Page`

Quick checklist:
1. Create `net/pages/mypage.py` with a page handler function
2. Return HTML string (can copy structure from `net/pages/home.py`)
3. Add route to `net/router.py` (pattern: `/mypage` maps to handler)
4. Optionally add JavaScript interactivity in `static/js/mypage.js`
5. Test at `http://localhost:8000/mypage`

#### Fixing a Bug in Session Detection

Session lifecycle is managed in `session/manager.py`. Key functions:
- `_is_driving()` — detects when the player has meaningful input
- `_detect_session_end()` — determines when a race has ended
- `_on_new_lap()` — called when a new lap is detected

Check `session/watchdog.py` for timeout thresholds.

#### Optimizing Database Queries

Database schema and queries are in `db/store.py`. Before optimizing:
- Identify the slow query (check perf instrumentation in logs)
- Add an index if scanning large tables
- Use EXPLAIN QUERY PLAN to verify the optimization works

Run `scripts/smoke_test.py` to verify no regressions.

## Code Style

- **Python**: Follow PEP 8, keep lines under 100 characters
- **JavaScript**: Clear variable names, avoid unnecessary complexity
- **HTML/CSS**: Semantic markup, use design tokens from `static/css/tokens.css`
- **Comments**: Only add if the WHY is non-obvious. Code should be self-documenting.

## Testing Checklist

- [ ] Code runs without errors (`python3 listener.py`)
- [ ] Existing tests still pass (`python3 test_listener.py`)
- [ ] New tests added for significant changes
- [ ] No new debug prints left in code
- [ ] Config changes are backwards-compatible

## Questions?

- Check `docs/ARCHITECTURE.md` for system overview
- Check `scripts/README.md` for utility script descriptions
- Open a [discussion](https://github.com/Estetika101/pacefinderapp/discussions) if you're stuck
- Look at existing code in a similar area for patterns

## License

By contributing, you agree your work will be licensed under the MIT License (see LICENSE).

---

Thanks for helping make Pacefinder better! 🏁
