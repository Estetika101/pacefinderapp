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
    <a href="/">Home</a>
    <a href="/sessions" class="cur">Career</a>
    <a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';</script>
<div class="page">

  <h1 class="title">Career</h1>
  <div class="subtitle">Your overall racing record. Per-track and per-car detail lives on
    <a href="/">Home</a> &rarr; circuits / cars.</div>

  <!-- Game filter -->
  <div class="gtab-bar">
    <a class="gtab active" href="/sessions">All<span class="cnt" id="cnt-all"></span></a>
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
<link rel="stylesheet" href="/static/nav.css">
</head>
<body>
<div id="pf-nav"></div>
<script src="/static/js/nav.js"></script>
<div class="page">

  <a href="/sessions" class="crumb">&larr; All circuits</a>

  <h1 class="title" id="hdr-name">Loading&hellip;</h1>
  <div class="subtitle" id="subtitle">&mdash;</div>

  <!-- Hero: personal best + gap to theoretical + progress chart -->
  <div class="hero">
    <div>
      <div class="hero-time" id="hero-pb">&mdash;</div>
      <div class="hero-time-sub" id="hero-pb-sub">Personal best</div>
      <div class="hero-gap" id="hero-gap" style="display:none">&mdash;</div>
      <div class="hero-gap-sub" id="hero-gap-sub" style="display:none">vs your theoretical</div>
    </div>
    <div class="progress">
      <div class="chart-header">
        <div class="chart-title">Best lap by session</div>
        <div class="chart-meta" id="chart-meta"></div>
      </div>
      <svg class="progress-svg" id="progress-svg" viewBox="0 0 1000 200" preserveAspectRatio="none"></svg>
      <div class="progress-empty" id="progress-empty" style="display:none">Not enough sessions to chart progress yet.</div>
    </div>
  </div>

  <!-- Theoretical breakdown -->
  <div class="theo" id="theo-card" style="display:none">
    <div>
      <div class="theo-label">Theoretical best</div>
      <div class="theo-time" id="theo-time">&mdash;</div>
      <div class="theo-note">Sum of your best sectors. Provenance &rarr;</div>
    </div>
    <div class="sectors">
      <div class="sect">
        <div class="sect-num">S1</div>
        <div class="sect-time" id="theo-s1">&mdash;</div>
        <div class="sect-prov" id="theo-s1-prov"></div>
      </div>
      <div class="sect">
        <div class="sect-num">S2</div>
        <div class="sect-time" id="theo-s2">&mdash;</div>
        <div class="sect-prov" id="theo-s2-prov"></div>
      </div>
      <div class="sect">
        <div class="sect-num">S3</div>
        <div class="sect-time" id="theo-s3">&mdash;</div>
        <div class="sect-prov" id="theo-s3-prov"></div>
      </div>
    </div>
  </div>

  <!-- AI track tip -->
  <div class="tip" id="tip-card">
    <div class="tip-head">
      <h2>Track tip</h2>
      <span class="tip-meta" id="tip-meta"></span>
    </div>
    <div class="tip-body" id="tip-text">No tip generated yet.</div>
    <button class="tip-gen" id="tip-btn" onclick="generateTip()">Generate AI tip</button>
  </div>

  <!-- Sessions list -->
  <div class="sessions">
    <div class="sessions-head">
      <h2>Sessions</h2>
      <span class="count" id="sessions-count">&mdash;</span>
    </div>
    <div class="filters" id="type-filter" style="display:none"></div>
    <div class="session-list" id="session-list"></div>
    <div class="empty-state" id="empty" style="display:none">No sessions at this track</div>
  </div>

</div>
<script>
const FORZA_TRACK_NAMES=
"""

TRACK_DETAIL_HTML_POST = """;</script>
<script src="/static/js/perf.js"></script>
<script>Perf.autoReport('/sessions/track');</script>
<script src="/static/js/class.js"></script>
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
<link rel="stylesheet" href="/static/nav.css">
</head>
<body>
<div id="pf-nav"></div>
<script src="/static/js/nav.js"></script>
<div class="page">

  <div class="breadcrumb" id="sess-breadcrumb">
    <a href="/sessions">Sessions</a> &rsaquo;
    <a href="#" id="bc-game" style="display:none"></a><span id="bc-gsep" style="display:none"> &rsaquo; </span>
    <a href="#" id="bc-track">Track</a> &rsaquo;
    <span id="bc-sess-cur">Session</span>
  </div>

  <div class="subnav">
    <span class="subnav-item active">Overview</span>
    <a class="subnav-item" id="link-telemetry" href="#">Full telemetry</a>
  </div>

  <div class="page-head">
    <div>
      <h1 class="page-h1" id="hdr-track">Loading&hellip;</h1>
      <div class="page-sub">
        <a class="page-sub-link" id="hdr-circuit-link" href="#"><span id="hdr-circuit-name">Circuit</span></a>
        <span class="page-sub-meta" id="hdr-submeta"></span>
        <a class="page-h2" id="hdr-car-link" href="#" style="display:none">
          <span id="hdr-car-name"></span>
          <span class="class-badge" id="hdr-car-class" style="display:none"></span>
          <span class="pi" id="hdr-car-pi" style="display:none"></span>
          <span class="page-h2-arrow">&rarr;</span>
        </a>
      </div>
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
    <span class="strip-spacer"></span>
    <button class="edit-btn" onclick="openEdit()" title="Edit session metadata">Edit &#x2303;</button>
  </div>
<!-- Edit modal -->
<div class="edit-ovl" id="edit-ovl" onclick="if(event.target===this)closeEdit()">
  <div class="edit-panel">
    <div class="edit-head">
      <div class="edit-ttl">Edit Session</div>
      <button class="edit-x" onclick="closeEdit()" aria-label="Close" title="Close">&times;</button>
    </div>
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
      <button class="edit-cancel" onclick="closeEdit()">Cancel</button>
      <button class="edit-save" onclick="saveEdit()">Save</button>
    </div>
    <div class="edit-danger">
      <button class="edit-delete-link" id="edit-del-link" onclick="deleteSession()">Delete session</button>
      <span class="edit-del-confirm" id="edit-del-confirm" style="display:none">
        Permanently delete this session?
        <button class="edit-del-yes" onclick="deleteSession(true)">Confirm delete</button>
        <button class="edit-del-no" onclick="cancelDelete()">Keep</button>
      </span>
    </div>
  </div>
</div>
  <!-- Hero: best lap + gap to theoretical + delta line + sector deltas -->
  <div class="hero">
    <div class="hero-numbers">
      <div class="hero-time" id="hero-best">&mdash;</div>
      <div class="hero-time-sub" id="hero-best-sub">Best lap</div>
      <div class="hero-gap" id="hero-gap" style="display:none">&mdash;</div>
      <div class="hero-gap-sub" id="hero-gap-sub" style="display:none">left on the table vs theoretical</div>
    </div>
    <div class="hero-chart">
      <div class="delta-header" id="delta-header" style="display:none">
        <span class="delta-title" id="delta-title">&Delta; — 2nd-best vs your best lap</span>
        <span class="delta-meta" id="delta-meta"></span>
      </div>
      <div class="delta-caption" id="delta-caption" style="display:none">
        Where your 2nd-best lap <span class="dc-slow">lost time</span> or
        <span class="dc-fast">gained time</span> against your best, around the lap.
      </div>
      <svg class="delta-svg" id="hero-delta-svg" viewBox="0 0 1000 180" preserveAspectRatio="none" style="display:none">
        <defs>
          <clipPath id="clipSlow"><rect x="0" y="0" width="1000" height="90"/></clipPath>
          <clipPath id="clipFast"><rect x="0" y="90" width="1000" height="90"/></clipPath>
        </defs>
        <line x1="333" y1="0" x2="333" y2="180" stroke="#1e1e1e" stroke-width="1" stroke-dasharray="3,4"/>
        <line x1="666" y1="0" x2="666" y2="180" stroke="#1e1e1e" stroke-width="1" stroke-dasharray="3,4"/>
        <line x1="0" y1="90" x2="1000" y2="90" stroke="#3a3a3a" stroke-width="1"/>
        <text x="166" y="14" fill="#888" font-size="10" font-family="monospace" text-anchor="middle" letter-spacing="0.1em">S1</text>
        <text x="500" y="14" fill="#888" font-size="10" font-family="monospace" text-anchor="middle" letter-spacing="0.1em">S2</text>
        <text x="833" y="14" fill="#888" font-size="10" font-family="monospace" text-anchor="middle" letter-spacing="0.1em">S3</text>
        <!-- y-axis cues: above the line = 2nd-best losing time, below = gaining -->
        <text x="6" y="20" fill="#f87171" font-size="10" font-family="monospace">slower ↑</text>
        <text x="6" y="86" fill="#8a8a8a" font-size="10" font-family="monospace">your best lap (0)</text>
        <text x="6" y="174" fill="#4ade80" font-size="10" font-family="monospace">faster ↓</text>
        <path id="hero-delta-fill-slow" d="" fill="#f87171" opacity="0.28" clip-path="url(#clipSlow)"/>
        <path id="hero-delta-fill-fast" d="" fill="#4ade80" opacity="0.26" clip-path="url(#clipFast)"/>
        <path id="hero-delta-line" d="" fill="none" stroke="#cfcfcf" stroke-width="1.5"/>
      </svg>
      <div class="delta-empty" id="delta-empty" style="display:none"></div>
      <div class="sector-row" id="hero-sectors" style="display:none">
        <div><div class="val" id="hero-s1">&mdash;</div><div class="lbl">S1 &Delta; vs theoretical</div></div>
        <div><div class="val" id="hero-s2">&mdash;</div><div class="lbl">S2 &Delta; vs theoretical</div></div>
        <div><div class="val" id="hero-s3">&mdash;</div><div class="lbl">S3 &Delta; vs theoretical</div></div>
      </div>
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
<script src="/static/js/class.js"></script>
<script src="/static/js/sessions_session.js"></script>
</body>
</html>
"""


# Sessions — the core content surface: a filter mechanism over every
# recorded session. H1 stays "Sessions"; filtering narrows all → slice.
# See docs/specs/ia.md.
SESSIONS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder &middot; Sessions</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<link rel="stylesheet" href="/static/sessions_car.css">
<link rel="stylesheet" href="/static/nav.css">
<style>
  .filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:var(--space-3) 0}
  .fgrp{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
  .fgrp .fl{font-size:11px;color:var(--color-text-quaternary);text-transform:uppercase;letter-spacing:.08em;margin-right:2px}
  .chip{border:1px solid var(--color-border);background:var(--color-surface);color:var(--color-text-secondary);
    padding:5px 12px;border-radius:999px;font-size:12px;cursor:pointer}
  .chip:hover{border-color:var(--color-text-tertiary);color:var(--color-text-primary)}
  .chip.on{background:var(--color-accent);border-color:var(--color-accent);color:#000;font-weight:600}
  .sortbar{display:flex;gap:8px;align-items:center;margin:var(--space-3) 0;color:var(--color-text-tertiary);font-size:12px}
  .seg{display:flex;border:1px solid var(--color-border);border-radius:6px;overflow:hidden}
  .seg button{background:var(--color-surface);border:none;color:var(--color-text-secondary);padding:5px 12px;font-size:12px;cursor:pointer}
  .seg button.on{background:var(--color-surface-2);color:var(--color-text-primary)}
  .seg button:disabled{opacity:.35;cursor:not-allowed}
  .shint{color:var(--color-text-quaternary);font-size:11px}
</style>
</head>
<body>
<div id="pf-nav"></div>
<script src="/static/js/nav.js"></script>
<div class="page">

  <div class="breadcrumb"><a href="/">Home</a> &rsaquo; <span>Sessions</span></div>

  <div class="titlewrap">
    <h1 class="nickname">Sessions</h1>
    <span class="canonical" id="sess-sub">Loading&hellip;</span>
  </div>

  <div class="filters" id="filters"></div>
  <div class="sortbar" id="sortbar"></div>

  <div class="section" style="padding-top:var(--space-2)">
    <div class="track-list" id="sess-list"></div>
  </div>

</div>

<script src="/static/js/class.js"></script>
<script src="/static/js/sessions_list.js"></script>
</body>
</html>
"""
