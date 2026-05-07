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
    <a href="/">Live</a>
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
    <a href="/">Live</a>
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
    <a href="/">Live</a>
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
      <div class="class-filter" id="class-filter" style="display:none"></div>
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
</head>
<body>
<div class="tb">
  <h1>Pacefinder</h1>
  <nav class="tb-nav">
    <a href="/">Live</a>
    <a href="/sessions" class="cur">Sessions</a>
    <a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';</script>
<div class="breadcrumb">
  <a href="/sessions">Sessions</a> &rsaquo;
  <a href="#" id="bc-game" style="display:none"></a>
  <span id="bc-game-sep" style="display:none"> &rsaquo; </span>
  <a href="#" id="bc-track">Track</a> &rsaquo;
  <span id="bc-sess">Session</span>
</div>
<div class="sess-hdr">
  <div>
    <div class="sess-title" id="hdr-track">Loading&hellip;</div>
    <div class="sess-sub" id="hdr-sub"></div>
  </div>
  <div class="hdr-stat"><div class="v" id="hdr-best">&mdash;</div><div class="l">Best Lap</div></div>
  <div class="hdr-stat"><div class="v" id="hdr-laps">&mdash;</div><div class="l">Laps</div></div>
  <div class="hdr-stat" id="hdr-grid-stat" style="display:none"><div class="v" id="hdr-grid">&mdash;</div><div class="l">Grid</div></div>
  <div class="hdr-stat" id="hdr-finish-stat" style="display:none"><div class="v" id="hdr-finish">&mdash;</div><div class="l">Finish</div></div>
  <div class="hdr-stat" id="hdr-gained-stat" style="display:none"><div class="v" id="hdr-gained">&mdash;</div><div class="l">Gained</div></div>
  <span class="type-chip" id="hdr-type" style="display:none"></span>
  <span class="type-chip" id="hdr-weather" style="display:none"></span>
  <span class="type-chip" id="hdr-tyre" style="display:none"></span>
  <button class="btn-re" onclick="openEdit()" style="font-size:var(--text-xs);padding:4px 12px">Edit</button>
</div>
<!-- Edit modal -->
<div class="edit-ovl" id="edit-ovl">
  <div class="edit-panel">
    <div class="edit-ttl">Edit Session</div>
    <div class="edit-row"><label class="edit-lbl">Track</label>
      <input class="edit-sel" id="edit-track" list="edit-track-list" placeholder="Search or type track name" autocomplete="off">
      <datalist id="edit-track-list"></datalist></div>
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
      <div class="edit-chips" id="edit-tyre-chips">
        <button class="etype" data-val="Street"   onclick="editSelTyre(this)">Street</button>
        <button class="etype" data-val="Sport"    onclick="editSelTyre(this)">Sport</button>
        <button class="etype" data-val="Race"     onclick="editSelTyre(this)">Race</button>
        <button class="etype" data-val="Slick"    onclick="editSelTyre(this)">Slick</button>
        <button class="etype" data-val="Rally"    onclick="editSelTyre(this)">Rally</button>
        <button class="etype" data-val="Off-Road" onclick="editSelTyre(this)">Off-Road</button>
        <button class="etype" data-val="Drag"     onclick="editSelTyre(this)">Drag</button>
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
<!-- Tab bar -->
<div class="sess-tab-bar">
  <button class="sess-tab active" id="st-overview" onclick="switchTab('overview')">Overview</button>
  <button class="sess-tab" id="st-telemetry" onclick="switchTab('telemetry')">Telemetry</button>
</div>
<!-- Layout -->
<div class="layout">
  <nav class="left-rail" id="left-rail">
    <div class="lr-section-lbl">Circuits</div>
    <div id="lr-items"></div>
    <div class="lr-divider"></div>
    <div class="lr-this" id="lr-this" style="display:none">
      <div class="lr-this-lbl">This Session</div>
      <div class="lr-this-car" id="lr-car"></div>
      <div class="lr-this-badges" id="lr-badges"></div>
    </div>
  </nav>
  <div class="main-content">
    <div class="lr-pills" id="lr-pills"></div>
    <div id="tab-overview">
      <div class="section">
        <div class="section-lbl">Lap Times</div>
        <table>
          <thead><tr>
            <th>Lap</th>
            <th>Time</th>
            <th>Max Spd</th>
            <th>Thr%</th>
            <th>Brk%</th>
            <th>Avg Slip</th>
            <th>Peak Slip</th>
            <th>Slip&gt;0.1%</th>
          </tr></thead>
          <tbody id="lap-tbody"></tbody>
        </table>
      </div>
      <div class="ai-section">
        <div class="ai-lbl">AI Coaching</div>
        <div>
          <button class="btn-analyze" id="btn-analyze" onclick="runAnalysis(false)">Analyze with Claude</button>
          <button class="btn-re" id="btn-re" onclick="runAnalysis(true)" style="display:none">Re-analyze</button>
          <span class="ai-meta" id="ai-meta"></span>
        </div>
        <div class="ai-body" id="ai-body"></div>
        <div class="ai-err" id="ai-err"></div>
      </div>
    </div>
    <div id="tab-telemetry" style="display:none">
      <iframe id="tele-frame" src="" style="width:100%;height:calc(100vh - 120px);border:none;display:block"></iframe>
    </div>
  </div>
</div>
<script>
const TRACK_NAMES=
"""

SESSION_DETAIL_HTML_POST = """;</script>
<script src="/static/js/sessions_session.js"></script>
</body>
</html>
"""
