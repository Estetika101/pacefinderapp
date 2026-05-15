# Home page — / (idle landing)
#
# The live dashboard previously served at / has moved to /dashboard.
# This is now the "browse mode" entry point: latest session, top
# circuits, top cars, recent sessions, Pi status.

HOME_HTML_PRE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<link rel="stylesheet" href="/static/home.css">
</head>
<body>
<div class="page">

  <!-- Topbar (full-width brand + status + nav) -->
  <div class="topbar">
    <a href="/" class="brand">pacefinder<span class="dot">.</span></a>
    <span class="status" id="status">
      <span class="status-dot" id="status-dot"></span>
      <span id="status-text">Loading&hellip;</span>
    </span>
    <span class="spacer"></span>
    <span class="top-nav">
      <a href="/dashboard" id="nav-live">Live dashboard</a>
      <a href="/setup">Setup</a>
    </span>
  </div>

  <!-- Welcome strip -->
  <div class="welcome">
    <div class="welcome-eyebrow" id="welcome-eyebrow">&mdash;</div>
    <h1 class="welcome-title">Welcome back.</h1>
  </div>

  <!-- Career strip (compact lifetime stats) -->
  <div class="career-strip" id="career-strip" style="display:none">
    <div class="cs-stats">
      <div class="cs-cell"><span class="cs-v muted" id="cs-total">&mdash;</span><span class="cs-l">Sessions</span></div>
      <div class="cs-cell"><span class="cs-v blue" id="cs-finish">&mdash;</span><span class="cs-l">Avg Finish</span></div>
      <div class="cs-cell"><span class="cs-v" id="cs-gained">&mdash;</span><span class="cs-l">Pos Gained</span></div>
      <div class="cs-cell"><span class="cs-v amber" id="cs-win">&mdash;</span><span class="cs-l">Win Rate</span></div>
      <div class="cs-cell"><span class="cs-v green" id="cs-podium">&mdash;</span><span class="cs-l">Podium</span></div>
      <div class="cs-cell"><span class="cs-v muted" id="cs-laps">&mdash;</span><span class="cs-l">Laps</span></div>
    </div>
    <div class="cs-form">
      <span class="cs-trend fl" id="cs-trend">&mdash;</span>
      <span class="cs-spark" id="cs-spark"></span>
    </div>
  </div>

  <!-- Hero: last session -->
  <a class="last-session" id="last-session" href="#" style="display:none">
    <div class="last-eyebrow">Pick up where you left off</div>
    <div class="last-grid">
      <div>
        <div class="last-time" id="last-time">&mdash;</div>
        <div class="last-sub" id="last-sub">&mdash;</div>
      </div>
      <div class="last-meta">
        <div class="last-track" id="last-track">&mdash;</div>
        <div class="last-car" id="last-car"></div>
        <div class="last-cond" id="last-cond"></div>
      </div>
      <div class="last-arrow">&rarr;</div>
    </div>
  </a>
  <div class="empty-hero" id="empty-hero" style="display:none">
    No sessions recorded yet. Open <a href="/dashboard">Live dashboard</a> and drive.
  </div>

  <!-- Twin grid: circuits + cars -->
  <div class="grid">
    <div class="panel">
      <div class="panel-head">
        <h2>Top circuits</h2>
        <a href="/sessions">All circuits &rarr;</a>
      </div>
      <div id="top-circuits"></div>
    </div>
    <div class="panel">
      <div class="panel-head">
        <h2>Top cars</h2>
        <a href="/cars">All cars &rarr;</a>
      </div>
      <div id="top-cars"></div>
    </div>
  </div>

  <!-- Recent sessions -->
  <div class="recent">
    <div class="section-head">
      <h2>Recent sessions</h2>
      <span class="count" id="recent-count">&mdash;</span>
    </div>
    <div id="recent-list"></div>
  </div>

  <!-- Footer: Pi stats -->
  <div class="footstrip">
    <div class="links">
      <a href="/setup">Setup</a>
      <a href="/admin" id="link-admin" style="display:none">Debug</a>
      <a href="/debug/perf">Performance</a>
    </div>
    <div class="pi-stats" id="pi-stats">&mdash;</div>
  </div>

</div>

<script>if(location.search.includes('debug=true'))document.getElementById('link-admin').style.display='';</script>
<script src="/static/js/home.js"></script>
</body>
</html>
"""
