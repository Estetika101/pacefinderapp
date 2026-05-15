GAMES_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder &middot; Sessions</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<link rel="stylesheet" href="/static/sessions_home.css">
</head>
<body>
<div class="tb">
  <h1>Pacefinder</h1>
  <nav class="tb-nav">
    <a href="/dashboard">Live</a>
    <a href="/sessions" class="cur">Sessions</a>
    <a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';</script>
<div class="page">

  <!-- Game Tabs -->
  <div class="gtab-bar">
    <a class="gtab active" href="/sessions">All Sessions<span class="cnt" id="cnt-all"></span></a>
    <a class="gtab" href="/sessions/game?name=forza_motorsport">Forza<span class="cnt" id="cnt-forza"></span></a>
    <a class="gtab" href="/sessions/game?name=acc">ACC<span class="cnt" id="cnt-acc"></span></a>
    <a class="gtab" href="/sessions/game?name=f1">F1<span class="cnt" id="cnt-f1"></span></a>
  </div>

  <!-- KPI row -->
  <div class="kpi-row" id="kpi-row">
    <div class="kpi"><div class="kpi-label">Total Sessions</div><div class="kpi-val muted" id="kv-total">—</div><div class="kpi-sub" id="ks-total">&nbsp;</div></div>
    <div class="kpi"><div class="kpi-label">Avg Finish</div><div class="kpi-val blue" id="kv-finish">—</div><div class="kpi-sub">Race lobbies only</div></div>
    <div class="kpi"><div class="kpi-label">Avg Pos Gained</div><div class="kpi-val" id="kv-gained">—</div><div class="kpi-sub">From grid position</div></div>
    <div class="kpi"><div class="kpi-label">Win Rate</div><div class="kpi-val amber" id="kv-win">—</div><div class="kpi-sub">Real lobbies only</div></div>
    <div class="kpi"><div class="kpi-label">Podium Rate</div><div class="kpi-val green" id="kv-podium">—</div><div class="kpi-sub">Real lobbies only</div></div>
    <div class="kpi"><div class="kpi-label">Total Laps</div><div class="kpi-val muted" id="kv-laps">—</div><div class="kpi-sub" id="ks-circuits">&nbsp;</div></div>
  </div>

  <!-- Current Form + Trend -->
  <div class="form-card">
    <div class="form-left">
      <div class="form-sect-label">Current Form</div>
      <div class="form-trend fl" id="form-trend">—</div>
      <div class="form-pct" id="form-pct"></div>
      <div class="form-note" id="form-note"></div>
    </div>
    <div class="form-right">
      <div class="form-spark" id="trend-spark"></div>
      <div class="form-filters">
        <div class="filter-group" id="last-filters">
          <button class="ftog" data-val="5">Last 5</button>
          <button class="ftog on" data-val="10">Last 10</button>
          <button class="ftog" data-val="20">Last 20</button>
        </div>
      </div>
      <div class="form-chart" id="form-chart"><div class="form-empty">No race data<small>Finish a race to populate this chart.</small></div></div>
    </div>
  </div>

  <!-- Best Laps Pills -->
  <div class="pills-section">
    <div class="pills-label">Best Laps by Circuit</div>
    <div class="pills-row" id="pills-row"></div>
  </div>

  <!-- Circuit Table -->
  <div class="table-section">
    <div class="table-label">Circuits</div>
    <table class="ctable">
      <thead><tr>
        <th>Circuit</th><th>Sessions</th><th>Avg Finish</th><th>Best Lap</th><th>Trend</th>
      </tr></thead>
      <tbody id="circuit-tbody"></tbody>
    </table>
  </div>

  <!-- Game Cards -->
  <div class="games-section" id="games-section">
    <div class="table-label" style="margin-bottom:8px">By Game</div>
    <div class="games-grid" id="games-grid"></div>
  </div>

  <!-- Recent Sessions -->
  <div class="recent-section">
    <div class="recent-label">Recent Sessions</div>
    <div id="recent-feed"></div>
  </div>

</div>
<script src="/static/js/perf.js"></script>
<script>Perf.autoReport('/sessions');</script>
<script src="/static/js/sessions_home.js"></script>
</body>
</html>
"""

TRACKS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder &middot; Tracks</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<link rel="stylesheet" href="/static/sessions_game.css">
</head>
<body>
<div class="tb">
  <h1>Pacefinder</h1>
  <nav class="tb-nav">
    <a href="/dashboard">Live</a>
    <a href="/sessions" class="cur">Sessions</a>
    <a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';</script>
    <!-- Game overview — shown only when ?name= is set -->
    <div id="game-overview" style="display:none">
      <div class="ov">
        <!-- KPI cards -->
        <div class="kpi-row">
          <div class="kpi"><div class="kpi-label">Total Sessions</div><div class="kpi-val muted" id="gkv-total">—</div><div class="kpi-sub" id="gks-total">&nbsp;</div></div>
          <div class="kpi"><div class="kpi-label">Avg Finish</div><div class="kpi-val blue" id="gkv-finish">—</div><div class="kpi-sub">&nbsp;</div></div>
          <div class="kpi"><div class="kpi-label">Avg Pos Gained</div><div class="kpi-val" id="gkv-gained">—</div><div class="kpi-sub">From grid</div></div>
          <div class="kpi"><div class="kpi-label">Win Rate</div><div class="kpi-val amber" id="gkv-win">—</div><div class="kpi-sub">&nbsp;</div></div>
          <div class="kpi"><div class="kpi-label">Podium Rate</div><div class="kpi-val green" id="gkv-podium">—</div><div class="kpi-sub">&nbsp;</div></div>
          <div class="kpi"><div class="kpi-label">Total Laps</div><div class="kpi-val muted" id="gkv-laps">—</div><div class="kpi-sub" id="gks-circuits">&nbsp;</div></div>
        </div>
        <!-- Current Form (with sparkline; Performance Trend was a duplicate
             of this and got merged in Bundle 4 of the user UX review). -->
        <div class="ov-form">
          <div class="ov-form-left">
            <div class="ov-form-lbl">Current Form</div>
            <div class="ov-form-trend fl" id="gf-trend">—</div>
            <div class="ov-form-pct" id="gf-pct"></div>
            <div class="ov-form-note" id="gf-note"></div>
          </div>
          <div class="ov-form-right">
            <div class="ov-ffilters">
              <div class="ov-fgroup" id="gf-last">
                <button class="ftog on" data-val="5">Last 5</button>
                <button class="ftog" data-val="10">Last 10</button>
                <button class="ftog" data-val="20">Last 20</button>
              </div>
            </div>
            <div class="ov-form-chart" id="gf-chart"></div>
          </div>
        </div>
        <!-- Recent Sessions -->
        <div class="ov-recent">
          <div class="ov-recent-lbl">Recent Sessions</div>
          <div id="gf-recent"></div>
        </div>
      </div>
    </div>
    <div class="sec-hdr">
      <h2 id="page-title">Tracks</h2>
      <span class="count" id="count"></span>
    </div>
    <div class="tracks-list" id="list"><div class="empty-state">Loading&hellip;</div></div>
<script src="/static/js/sessions_game.js"></script>
</body>
</html>
"""

TRACK_DETAIL_HTML_PRE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder &middot; Track</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<link rel="stylesheet" href="/static/sessions_track.css">
</head>
<body>
<div class="tb">
  <h1>Pacefinder</h1>
  <nav class="tb-nav">
    <a href="/dashboard">Live</a>
    <a href="/sessions" class="cur">Sessions</a>
    <a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';</script>
<div class="breadcrumb"><a href="/sessions">Sessions</a> &rsaquo; <a href="#" id="bc-game" style="display:none"></a><span id="bc-sep" style="display:none"> &rsaquo; </span><span id="bc-track">Track</span></div>
<div class="lr-pills" id="lr-pills"></div>
<div class="layout">
  <nav class="left-rail" id="left-rail">
    <div class="lr-section-lbl">Circuits</div>
    <div id="lr-items"></div>
  </nav>
  <div class="main-content">
    <div class="track-hdr">
      <div class="track-name" id="hdr-name">Loading&hellip;</div>
      <div class="hdr-stat"><div class="v" id="hdr-best">&mdash;</div><div class="l">Best Lap</div></div>
      <div class="hdr-stat"><div class="v" id="hdr-count">&mdash;</div><div class="l">Sessions</div></div>
      <div class="hdr-stat"><div class="v" id="hdr-trend">&mdash;</div><div class="l">Trend</div></div>
    </div>

    <div id="trk-overview">
      <div class="track-tip-bar" id="tip-bar">
        <span id="tip-text"></span>
        <button class="tip-gen" id="tip-btn" onclick="generateTip()">Generate AI tip</button>
      </div>
      <div class="ref-card" id="ref-card">
        <div class="ref-card-lbl" id="ref-card-title">References</div>
        <div class="ref-rows" id="ref-rows"></div>
        <div class="ref-gap" id="ref-gap" style="display:none">
          <span>Gap to theoretical</span>
          <span class="ref-gap-val" id="ref-gap-val"></span>
        </div>
      </div>
      <div class="class-filter" id="type-filter" style="display:none;margin-bottom:8px"></div>
      <div id="acc-container"></div>
      <div class="empty-state" id="empty" style="display:none">No sessions at this track</div>
    </div>

  </div>
</div>
<script>
const FORZA_TRACK_NAMES=
"""

TRACK_DETAIL_HTML_POST = """;</script>
<script src="/static/js/perf.js"></script>
<script>Perf.autoReport('/sessions/track');</script>
<script src="/static/js/sessions_track.js"></script>
<div id="sp-tip"></div>
</body>
</html>
"""

SESSION_DETAIL_HTML_PRE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder &middot; Session</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<link rel="stylesheet" href="/static/sessions_session.css">
<link rel="stylesheet" href="/static/widgets/autocomplete.css">
</head>
<body>
<div class="tb">
  <h1>Pacefinder</h1>
  <nav class="tb-nav">
    <a href="/dashboard">Live</a>
    <a href="/sessions" class="cur">Sessions</a>
    <a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';</script>
<div class="page">

  <a class="crumb" id="bc-track" href="#">&larr; <span id="bc-track-name">Track</span></a>

  <div class="subnav">
    <span class="subnav-item active">Overview</span>
    <a class="subnav-item" id="link-telemetry" href="#">Full telemetry</a>
  </div>

  <div class="page-head">
    <div>
      <h1 class="page-h1" id="hdr-track">Loading&hellip;</h1>
      <a class="page-h2" id="hdr-car-link" href="#" style="display:none">
        <span id="hdr-car-name"></span>
        <span class="class-badge" id="hdr-car-class" style="display:none"></span>
        <span class="pi" id="hdr-car-pi" style="display:none"></span>
        <span class="page-h2-arrow">&rarr;</span>
      </a>
    </div>
    <div class="page-head-result" id="hdr-result" style="display:none">
      <div class="result-eyebrow">Grid &rarr; Finish</div>
      <div class="result-positions">
        <span id="hdr-grid-p">&mdash;</span>
        <span class="arrow">&rarr;</span>
        <span class="finish" id="hdr-finish-p">&mdash;</span>
      </div>
      <div class="result-delta" id="hdr-gained">&mdash;</div>
    </div>
  </div>

  <div class="strip">
    <span class="pill" id="hdr-when" style="display:none"><span class="label">When</span><span class="val" id="hdr-when-val"></span></span>
    <span class="pill" id="hdr-cond" style="display:none"><span class="label">Cond</span><span class="val" id="hdr-cond-val"></span></span>
    <span class="pill type-chip" id="hdr-type" style="display:none"></span>
    <span class="strip-spacer"></span>
    <button class="edit-btn" onclick="openEdit()" title="Edit session metadata">Edit &#x2303;</button>
  </div>
<!-- Edit modal -->
<div class="edit-ovl" id="edit-ovl">
  <div class="edit-panel">
    <div class="edit-ttl">Edit Session</div>
    <div class="edit-row"><label class="edit-lbl">Track</label>
      <input class="edit-sel" id="edit-track" placeholder="Search or type track name"></div>
    <div class="edit-row"><label class="edit-lbl">Car</label>
      <input class="edit-sel" id="edit-car" placeholder="e.g. 2018 Honda Civic Type R" autocomplete="off"></div>
    <div class="edit-row" id="edit-nickname-row" style="display:none">
      <label class="edit-lbl">Nickname <span style="font-weight:normal;text-transform:none;color:var(--color-text-muted)">(applies to every session in this car)</span></label>
      <input class="edit-sel" id="edit-nickname" placeholder="e.g. Lady Bug, Dreamliner" autocomplete="off" maxlength="40">
    </div>
    <div class="edit-row"><label class="edit-lbl">Type</label>
      <div class="edit-chips">
        <button class="etype" data-val="practice" onclick="editSelType(this)">Practice</button>
        <button class="etype" data-val="qualifying" onclick="editSelType(this)">Qualifying</button>
        <button class="etype" data-val="race" onclick="editSelType(this)">Race</button>
        <button class="etype" data-val="race_ai" onclick="editSelType(this)">AI Race</button>
        <button class="etype" data-val="hot_lap" onclick="editSelType(this)">Hot Lap</button>
        <button class="etype" data-val="time_trial" onclick="editSelType(this)">Time Trial</button>
      </div>
    </div>
    <div class="edit-row"><label class="edit-lbl">Weather</label>
      <div class="edit-chips" id="edit-weather-chips">
        <button class="etype" data-val="Dry"  onclick="editSelWeather(this)">Dry</button>
        <button class="etype" data-val="Damp" onclick="editSelWeather(this)">Damp</button>
        <button class="etype" data-val="Wet"  onclick="editSelWeather(this)">Wet</button>
        <button class="etype" data-val="Snow" onclick="editSelWeather(this)">Snow</button>
      </div>
    </div>
    <div class="edit-row"><label class="edit-lbl">Tyres</label>
      <!-- Forza Motorsport compounds. FH5 uses different categories
           (Street/Sport/Race/Slick/Rally/Off-Road/Drag) — to be split per
           game once FH5 support comes back online (see issue #84). -->
      <div class="edit-chips" id="edit-tyre-chips">
        <button class="etype" data-val="Soft"    onclick="editSelTyre(this)">Soft</button>
        <button class="etype" data-val="Medium"  onclick="editSelTyre(this)">Medium</button>
        <button class="etype" data-val="Hard"    onclick="editSelTyre(this)">Hard</button>
        <button class="etype" data-val="Wet"     onclick="editSelTyre(this)">Wet</button>
      </div>
    </div>
    <div class="edit-row">
      <!-- Grid + finish — Forza assesses penalties post-race in a screen
           we never see, so the captured finish_pos is the on-track result.
           Manual override here so corrected positions can be recorded. -->
      <label class="edit-lbl">Grid → Finish</label>
      <div style="display:flex;gap:8px;align-items:center">
        <span style="font-size:.7rem;color:var(--color-text-muted)">P</span>
        <input id="edit-grid" type="number" min="1" max="100" placeholder="—"
               style="width:60px;background:var(--color-surface-2);border:1px solid var(--color-border);color:var(--color-text-primary);font-family:var(--font-mono);font-size:var(--text-sm);padding:6px 8px;border-radius:var(--radius-sm)"/>
        <span style="font-size:.7rem;color:var(--color-text-muted)">→ P</span>
        <input id="edit-finish" type="number" min="1" max="100" placeholder="—"
               style="width:60px;background:var(--color-surface-2);border:1px solid var(--color-border);color:var(--color-text-primary);font-family:var(--font-mono);font-size:var(--text-sm);padding:6px 8px;border-radius:var(--radius-sm)"/>
      </div>
    </div>
    <div class="edit-row" id="edit-conditions-row" style="display:none">
      <label class="edit-lbl">Conditions</label>
      <span id="edit-conditions" style="font-size:.7rem;color:var(--color-text-secondary);font-variant-numeric:tabular-nums"></span>
    </div>
    <div class="edit-btns">
      <button class="edit-save" onclick="saveEdit()">Save</button>
      <button class="edit-cancel" onclick="closeEdit()">Cancel</button>
      <button class="edit-delete" onclick="deleteSession()" title="Permanently remove this session and its data">Delete session</button>
    </div>
  </div>
</div>
  <!-- Hero: best lap + gap to theoretical + sector deltas -->
  <div class="hero">
    <div class="hero-numbers">
      <div class="hero-time" id="hero-best">&mdash;</div>
      <div class="hero-time-sub" id="hero-best-sub">Best lap</div>
      <div class="hero-gap" id="hero-gap" style="display:none">&mdash;</div>
      <div class="hero-gap-sub" id="hero-gap-sub" style="display:none">left on the table vs theoretical</div>
    </div>
    <div class="sector-row" id="hero-sectors" style="display:none">
      <div><div class="val" id="hero-s1">&mdash;</div><div class="lbl">S1 &Delta; vs theoretical</div></div>
      <div><div class="val" id="hero-s2">&mdash;</div><div class="lbl">S2 &Delta; vs theoretical</div></div>
      <div><div class="val" id="hero-s3">&mdash;</div><div class="lbl">S3 &Delta; vs theoretical</div></div>
    </div>
  </div>

  <!-- Session profile strip (5-cell aggregate, immediately under hero) -->
  <div class="profile" id="profile" style="display:none">
    <div class="profile-cell">
      <div class="profile-label">Throttle avg</div>
      <div class="profile-value" id="prof-thr">&mdash;</div>
      <div class="profile-bar"><span id="prof-thr-bar" style="width:0"></span></div>
    </div>
    <div class="profile-cell">
      <div class="profile-label">Brake avg</div>
      <div class="profile-value" id="prof-brk">&mdash;</div>
      <div class="profile-bar brake"><span id="prof-brk-bar" style="width:0"></span></div>
    </div>
    <div class="profile-cell">
      <div class="profile-label">Slip avg</div>
      <div class="profile-value" id="prof-slip">&mdash;</div>
      <div class="profile-bar slip"><span id="prof-slip-bar" style="width:0"></span></div>
    </div>
    <div class="profile-cell">
      <div class="profile-label">Peak slip</div>
      <div class="profile-value" id="prof-pslip">&mdash;</div>
      <div class="profile-bar slip"><span id="prof-pslip-bar" style="width:0"></span></div>
    </div>
    <div class="profile-cell">
      <div class="profile-label">Slip &gt; 0.1</div>
      <div class="profile-value" id="prof-above">&mdash;</div>
      <div class="profile-bar slip"><span id="prof-above-bar" style="width:0"></span></div>
    </div>
  </div>

  <!-- Lap table -->
  <div class="laps">
    <div class="laps-head">
      <h2>Laps</h2>
      <span class="laps-hint">Click a header to sort &middot; click a row to inspect in telemetry</span>
    </div>
    <table class="lap-table">
      <thead><tr>
        <th class="sorted" data-sort="lap"  data-dir="asc">Lap <span class="sort-ind">&#x25B2;</span></th>
        <th data-sort="time">Time <span class="sort-ind">&#x21D5;</span></th>
        <th data-sort="s1">S1 &Delta; <span class="sort-ind">&#x21D5;</span></th>
        <th data-sort="s2">S2 &Delta; <span class="sort-ind">&#x21D5;</span></th>
        <th data-sort="s3">S3 &Delta; <span class="sort-ind">&#x21D5;</span></th>
        <th></th>
      </tr></thead>
      <tbody id="lap-tbody"></tbody>
    </table>
  </div>

  <!-- Three drill-in cards -->
  <div class="cards">
    <div class="card" id="card-loss">
      <div class="card-title">Where you lost time</div>
      <div class="card-headline" id="card-loss-headline">&mdash;</div>
      <div class="card-body" id="card-loss-body"></div>
      <a class="card-link" id="card-loss-link" href="#">Open in telemetry &rarr;</a>
    </div>
    <div class="card" id="card-car">
      <div class="card-title">Car context</div>
      <div class="card-headline" id="card-car-headline">&mdash;</div>
      <div class="card-body" id="card-car-body"></div>
      <a class="card-link" id="card-car-link" href="#" style="display:none">Show car history &rarr;</a>
    </div>
    <div class="card" id="card-ai">
      <div class="card-title">Coaching</div>
      <div class="card-body" id="card-ai-body" style="display:none"></div>
      <div class="ai-controls" id="ai-controls">
        <button class="btn-analyze" id="btn-analyze" onclick="runAnalysis(false)">Analyze with Claude</button>
        <button class="btn-re" id="btn-re" onclick="runAnalysis(true)" style="display:none">Re-analyze</button>
        <div class="ai-meta" id="ai-meta"></div>
      </div>
      <div class="ai-err" id="ai-err"></div>
    </div>
  </div>

</div> <!-- /.page -->
<script>
const TRACK_NAMES=
"""

# CAR_CATALOG is spliced between the two halves below — see listener.py.
SESSION_DETAIL_HTML_MID = """;
const CAR_CATALOG=
"""

SESSION_DETAIL_HTML_POST = """;</script>
<script src="/static/js/widgets/autocomplete.js"></script>
<script src="/static/js/sessions_session.js"></script>
</body>
</html>
"""
