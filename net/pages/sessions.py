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
    <div class="kpi"><div class="kpi-label">Avg Pos Gained</div><div class="kpi-val green" id="kv-gained">—</div><div class="kpi-sub">From grid position</div></div>
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
        <div class="filter-group" id="type-filters">
          <button class="ftog on" data-val="real">Real</button>
          <button class="ftog" data-val="ai">AI</button>
          <button class="ftog" data-val="all">All</button>
        </div>
        <div class="filter-group" id="last-filters">
          <button class="ftog" data-val="5">Last 5</button>
          <button class="ftog on" data-val="10">Last 10</button>
          <button class="ftog" data-val="20">Last 20</button>
        </div>
      </div>
      <div class="form-chart" id="form-chart"><div class="form-empty">No race data<small>Finish position data needed — check session race_type classification.</small></div></div>
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
<div class="gtab-bar" id="gtab-bar">
  <a class="gtab" href="/sessions" id="tab-all">All Sessions<span class="cnt" id="cnt-all"></span></a>
  <a class="gtab" href="/sessions/game?name=forza_motorsport" id="tab-forza">Forza<span class="cnt" id="cnt-forza"></span></a>
  <a class="gtab" href="/sessions/game?name=acc" id="tab-acc">ACC<span class="cnt" id="cnt-acc"></span></a>
  <a class="gtab" href="/sessions/game?name=f1" id="tab-f1">F1<span class="cnt" id="cnt-f1"></span></a>
</div>
    <!-- Game overview — shown only when ?name= is set -->
    <div id="game-overview" style="display:none">
      <div class="ov">
        <!-- KPI cards -->
        <div class="kpi-row">
          <div class="kpi"><div class="kpi-label">Total Sessions</div><div class="kpi-val muted" id="gkv-total">—</div><div class="kpi-sub" id="gks-total">&nbsp;</div></div>
          <div class="kpi"><div class="kpi-label">Avg Finish</div><div class="kpi-val blue" id="gkv-finish">—</div><div class="kpi-sub">Race lobbies</div></div>
          <div class="kpi"><div class="kpi-label">Avg Pos Gained</div><div class="kpi-val green" id="gkv-gained">—</div><div class="kpi-sub">From grid</div></div>
          <div class="kpi"><div class="kpi-label">Win Rate</div><div class="kpi-val amber" id="gkv-win">—</div><div class="kpi-sub">Real lobbies</div></div>
          <div class="kpi"><div class="kpi-label">Podium Rate</div><div class="kpi-val green" id="gkv-podium">—</div><div class="kpi-sub">Real lobbies</div></div>
          <div class="kpi"><div class="kpi-label">Best Lap</div><div class="kpi-val amber" id="gkv-best">—</div><div class="kpi-sub" id="gks-best">&nbsp;</div></div>
          <div class="kpi"><div class="kpi-label">Total Laps</div><div class="kpi-val muted" id="gkv-laps">—</div><div class="kpi-sub" id="gks-circuits">&nbsp;</div></div>
        </div>
        <!-- Performance Trend -->
        <div class="ov-trend">
          <div class="ov-trend-meta">
            <div class="ov-trend-lbl">Performance Trend</div>
            <div class="ov-trend-dir fl" id="gtd-dir">—</div>
          </div>
          <div class="ov-trend-spark" id="gtd-spark"></div>
        </div>
        <!-- Current Form -->
        <div class="ov-form">
          <div class="ov-form-left">
            <div class="ov-form-lbl">Current Form</div>
            <div class="ov-form-trend fl" id="gf-trend">—</div>
            <div class="ov-form-pct" id="gf-pct"></div>
            <div class="ov-form-note" id="gf-note"></div>
          </div>
          <div class="ov-form-right">
            <div class="ov-ffilters">
              <div class="ov-fgroup" id="gf-type">
                <button class="ftog on" data-val="real">Real</button>
                <button class="ftog" data-val="ai">AI</button>
                <button class="ftog" data-val="all">All</button>
              </div>
              <div class="ov-fgroup" id="gf-last">
                <button class="ftog" data-val="5">Last 5</button>
                <button class="ftog on" data-val="10">Last 10</button>
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
<div class="gtab-bar" id="gtab-bar">
  <a class="gtab" href="/sessions" id="tab-all">All Sessions<span class="cnt" id="cnt-all"></span></a>
  <a class="gtab" href="#" id="tab-forza">Forza<span class="cnt" id="cnt-forza"></span></a>
  <a class="gtab" href="#" id="tab-acc">ACC<span class="cnt" id="cnt-acc"></span></a>
  <a class="gtab" href="#" id="tab-f1">F1<span class="cnt" id="cnt-f1"></span></a>
</div>
<div class="breadcrumb"><a href="/sessions">Sessions</a> &rsaquo; <a href="#" id="bc-game" style="display:none"></a><span id="bc-sep" style="display:none"> &rsaquo; </span><span id="bc-track">Track</span></div>
<div class="lr-pills" id="lr-pills"></div>
<div class="trk-tab-bar">
  <button class="trk-tab active" id="trk-tab-overview" onclick="switchTrackTab('overview')">Overview</button>
  <button class="trk-tab" id="trk-tab-telemetry" onclick="switchTrackTab('telemetry')">Telemetry</button>
</div>
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

    <!-- Overview tab -->
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

    <!-- Telemetry tab -->
    <div id="trk-telemetry" style="display:none">
      <div class="tele-ctrl">
        <div>
          <div class="tele-label">Lap</div>
          <select class="tele-sel" id="tele-sess-sel" onchange="onTeleSessChange()"></select>
        </div>
        <div>
          <div class="tele-label">Lap #</div>
          <select class="tele-sel" id="tele-lap-sel" onchange="onTeleLapChange()"></select>
        </div>
        <div>
          <div class="tele-label">Reference</div>
          <select class="tele-sel" id="tele-ref-sel" onchange="onTeleRefChange()"></select>
        </div>
      </div>
      <div class="tele-chart-area" id="tele-chart-area">
        <div class="tele-empty-msg" id="tele-msg">Loading best lap&hellip;</div>
        <div id="tele-cmp-wrap" style="display:none">
          <div id="tele-crosshair" style="position:absolute;top:0;bottom:0;width:1px;background:rgba(255,255,255,.2);pointer-events:none;display:none"></div>
          <div id="tele-tooltip" style="position:absolute;top:4px;background:var(--color-surface);border:1px solid var(--color-border);color:var(--color-text-primary);font-size:.7rem;padding:3px 8px;border-radius:3px;pointer-events:none;display:none;white-space:nowrap"></div>
          <div id="tele-charts-inner"></div>
          <div style="display:flex;justify-content:space-between;font-size:.6rem;color:var(--color-text-muted);margin-top:2px"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
        </div>
      </div>
    </div>

  </div>
</div>
<script>
const FORZA_TRACK_NAMES=
"""

TRACK_DETAIL_HTML_POST = """;</script>
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
  <span class="type-chip" id="hdr-type" style="display:none"></span>
  <button class="btn-re" onclick="openEdit()" style="font-size:var(--text-xs);padding:4px 12px">Edit</button>
</div>
<!-- Edit modal -->
<div class="edit-ovl" id="edit-ovl">
  <div class="edit-panel">
    <div class="edit-ttl">Edit Session</div>
    <div class="edit-row"><label class="edit-lbl">Track</label>
      <select class="edit-sel" id="edit-track"></select></div>
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
    <div class="edit-btns">
      <button class="edit-save" onclick="saveEdit()">Save</button>
      <button class="edit-cancel" onclick="closeEdit()">Cancel</button>
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
