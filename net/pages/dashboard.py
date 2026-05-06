DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<link rel="stylesheet" href="/static/dashboard.css">
</head>
<body>

<div class="tb">
  <div class="dot" id="dot"></div>
  <span class="tb-stat" id="tb-stat">IDLE</span>
  <div class="tb-meta">
    <span class="tb-game game-none" id="tb-game">—</span>
    <span class="tb-sep">·</span>
    <span class="tb-track" id="tb-track">—</span>
    <span class="tb-drs" id="tb-drs">DRS</span>
    <span class="tb-cmp" id="tb-cmp"></span>
  </div>
  <nav class="tb-nav">
    <a href="/" class="cur">Live</a>
    <a href="/sessions">Sessions</a>
    <a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';</script>

<div class="main">

  <!-- MAIN PANELS: Throttle | Brake | Rear Slip | Lap Timing -->
  <div class="panels">

    <div class="panel-col" id="thr-row">
      <div class="p-lbl">Throttle</div>
      <div class="vbar-wrap">
        <div class="vbar-fill thr-fill" id="thr-b"></div>
      </div>
      <div class="p-num thr-pct" id="thr-v">0%</div>
    </div>

    <div class="panel-col" id="brk-row">
      <div class="p-lbl">Brake</div>
      <div class="vbar-wrap">
        <div class="vbar-fill brk-fill" id="brk-b"></div>
      </div>
      <div class="p-num brk-pct" id="brk-v">0%</div>
    </div>

    <div class="panel-col" id="slip-panel">
      <div class="p-lbl">Rear Slip</div>
      <div class="slip-bars">
        <div class="slip-bar-col">
          <div class="slip-bar-lbl">RL</div>
          <div class="vbar-wrap">
            <div class="vbar-fill" id="srl-b"></div>
          </div>
          <div class="slip-num" id="srl-v">—</div>
        </div>
        <div class="slip-bar-col">
          <div class="slip-bar-lbl">RR</div>
          <div class="vbar-wrap">
            <div class="vbar-fill" id="srr-b"></div>
          </div>
          <div class="slip-num" id="srr-v">—</div>
        </div>
      </div>
    </div>

    <div class="panel-col">
      <div class="p-lbl">Lap Timing</div>
      <div class="timing-grid">
        <div>
          <div class="t-lbl">Current</div>
          <div class="t-val" id="t-cur">—</div>
        </div>
        <div>
          <div class="t-lbl">Best</div>
          <div class="t-val green" id="t-best">—</div>
        </div>
        <div>
          <div class="t-lbl">Last</div>
          <div class="t-val" id="t-last">—</div>
        </div>
        <div>
          <div class="t-lbl">L#</div>
          <div class="t-val" id="t-lap">—</div>
        </div>
      </div>
      <div class="t-delta-row">
        <div class="t-lbl">Delta</div>
        <div class="delta-val even" id="t-delta">—</div>
      </div>
      <div class="timing-grid" style="margin-top:10px">
        <div>
          <div class="t-lbl">Pos</div>
          <div class="t-val" id="pos-cur">—</div>
        </div>
        <div>
          <div class="t-lbl">Grid</div>
          <div class="t-val" id="pos-grid">—</div>
        </div>
        <div>
          <div class="t-lbl">±</div>
          <div class="delta-val even" id="pos-delta" style="font-size:var(--text-lg)">—</div>
        </div>
      </div>
      <div>
        <div class="t-lbl">Tyres</div>
        <div class="tyre-inline-grid" style="margin-top:6px">
          <div class="tyre-inline-cell">
            <div class="tyre-inline-lbl">FL</div>
            <span class="tyre-temp na" id="ty-fl">—</span>
          </div>
          <div class="tyre-inline-cell">
            <div class="tyre-inline-lbl">FR</div>
            <span class="tyre-temp na" id="ty-fr">—</span>
          </div>
          <div class="tyre-inline-cell">
            <div class="tyre-inline-lbl">RL</div>
            <span class="tyre-temp na" id="ty-rl">—</span>
          </div>
          <div class="tyre-inline-cell">
            <div class="tyre-inline-lbl">RR</div>
            <span class="tyre-temp na" id="ty-rr">—</span>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- BOTTOM STRIP: Gear · Speed · RPM · Tyres -->
  <div class="bot-panels">
    <div class="bp">
      <div class="bp-lbl">Gear</div>
      <div class="gear-val" id="gear">—</div>
    </div>
    <div class="bp">
      <div class="bp-lbl">Speed</div>
      <div class="speed-val" id="spd">—</div>
      <div class="speed-unit">mph</div>
    </div>
    <div class="bp rpm-bp">
      <div class="rpm-lbl-row">
        <span class="rpm-lbl">RPM</span>
        <span class="rpm-pct" id="rpm-pct">—</span>
      </div>
      <div class="rpm-track">
        <div class="rpm-fill" id="rpm-fill"></div>
        <div class="rpm-gear-mark" id="rpm-mark" style="left:75%"></div>
      </div>
      <div class="rpm-num" id="rpm-num">—</div>
    </div>
  </div>

</div><!-- /main -->

<div class="bot">
  <div class="udp-strip" id="udp-strip"></div>
  <button class="bot-finish" id="btn-finish" onclick="openFinish()">Finish Race</button>
  <button class="bot-btn" id="dbg-btn" onclick="toggleDebug()">Debug</button>
</div>

<div id="dbg">
  <div class="dh">
    <span>Debug Console</span>
    <div style="display:flex;gap:10px;align-items:center">
      <label style="font-size:var(--text-xs);color:var(--color-text-muted);cursor:pointer;display:flex;align-items:center;gap:4px"><input type="checkbox" id="dbg-as" checked> scroll</label>
      <select id="dbg-f" onchange="applyFilter()" style="background:var(--color-surface);border:1px solid var(--color-border-subtle);color:var(--color-text-muted);font-family:inherit;font-size:var(--text-xs);padding:2px 6px;border-radius:2px">
        <option value="all">All</option><option value="warn">Warn+</option><option value="udp">UDP</option>
      </select>
      <button onclick="clearDebug()" style="background:none;border:1px solid var(--color-border-subtle);color:var(--color-text-muted);font-family:inherit;font-size:var(--text-xs);padding:2px 8px;border-radius:2px;cursor:pointer">Clear</button>
    </div>
  </div>
  <div id="dbg-log"></div>
</div>

<div id="fo">
  <div class="fo-box">
    <div class="fo-head">
      <div class="fo-title-row"><div class="fo-title" id="fo-title">Session Complete</div><span class="game-badge" id="fo-game-badge" style="display:none"></span></div>
      <div class="fo-sub" id="fo-sub">—</div>
      <div class="fo-stats" id="fo-stats" style="display:none">
        <div class="fo-stat-item"><div class="fo-stat-v" id="fo-stat-laps">—</div><div class="fo-stat-l">Laps</div></div>
        <div class="fo-stat-item"><div class="fo-stat-v" id="fo-stat-best">—</div><div class="fo-stat-l">Best Lap</div></div>
      </div>
    </div>
    <div class="fo-body">
      <div class="fo-section">
        <div class="fo-lbl">Track</div>
        <select class="fo-input" id="fo-track">
          <option value="">— Unknown —</option>
        </select>
      </div>
      <div class="fo-section">
        <div class="fo-lbl">Car</div>
        <input class="fo-input" id="fo-car" type="text" placeholder="Car name or ordinal" />
      </div>
      <div class="fo-section">
        <div class="fo-lbl">Session Type</div>
        <div class="type-chips">
          <button class="type-chip" data-val="real" onclick="selType(this)">Real Race</button>
          <button class="type-chip" data-val="ai" onclick="selType(this)">AI Race</button>
          <button class="type-chip" data-val="time_trial" onclick="selType(this)">Time Trial</button>
        </div>
      </div>
      <div class="fo-section">
        <div class="fo-lbl">Laps</div>
        <div class="fo-lap-list" id="fo-laps"></div>
      </div>
    </div>
    <div class="fo-foot">
      <button class="fo-skip" onclick="closeFinish()">Skip</button>
      <button class="fo-save" onclick="saveFinish()">Save</button>
    </div>
  </div>
</div>

<script src="/static/js/dashboard.js"></script>
</body>
</html>
"""
