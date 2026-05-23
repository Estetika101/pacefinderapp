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
<link rel="stylesheet" href="/static/nav.css">
</head>
<body>
<div id="pf-nav"></div>
<script src="/static/js/nav.js"></script>
<div class="page">

  <!-- Last session hero — answers "what happened while I was away?"
       and surfaces the single best CTA: jump into the trace you just
       drove. See docs/specs/home-last-session-hero.md (brainstorm). -->
  <div class="hero-last" id="hero-last" style="display:none">
    <div class="hl-outline track-outline" id="hl-outline"></div>
    <div class="hl-body">
      <div class="hl-eyebrow" id="hl-eyebrow">Last session</div>
      <h1 class="hl-title">
        <a id="hl-track-link" href="#"><span id="hl-track">&mdash;</span></a>
        <span class="hl-dot">&middot;</span>
        <a id="hl-car-link" href="#"><span id="hl-car">&mdash;</span></a>
        <span class="hl-class-badge" id="hl-class-badge"></span>
      </h1>
      <div class="hl-stats">
        <span class="hl-laptime" id="hl-laptime">&mdash;</span>
        <span class="hl-delta" id="hl-delta"></span>
      </div>
      <div class="hl-meta" id="hl-meta">&mdash;</div>
    </div>
    <div class="hl-actions">
      <a class="hl-cta primary" id="hl-cta-telemetry" href="#">Open telemetry &rarr;</a>
      <a class="hl-cta" id="hl-cta-session" href="#">Session details</a>
    </div>
  </div>
  <!-- Empty state when no session has ever been recorded. The hero
       above hides; this prompts the user toward the live dashboard. -->
  <div class="hero-empty" id="hero-empty" style="display:none">
    <h1>No sessions yet.</h1>
    <p>Point your game at port 5300 and drive — Pacefinder records every lap.</p>
    <a class="hl-cta primary" href="/dashboard">Open live dashboard &rarr;</a>
  </div>

  <!-- Career stats (improvement-first; results gated; see docs/specs/home-stats.md) -->
  <div class="career-strip" id="career-strip" style="display:none">
    <div class="cs-stats">
      <div class="cs-cell"><span class="cs-v muted" id="cs-total">&mdash;</span><span class="cs-l">Sessions</span></div>
      <div class="cs-cell"><span class="cs-v muted" id="cs-laps">&mdash;</span><span class="cs-l">Laps</span></div>
      <div class="cs-cell"><span class="cs-v muted" id="cs-circuits">&mdash;</span><span class="cs-l">Circuits</span></div>
      <div class="cs-cell"><span class="cs-v muted" id="cs-cars">&mdash;</span><span class="cs-l">Cars</span></div>
      <div class="cs-cell cs-trend-tally" id="cs-trend-tally" style="display:none">
        <span class="cs-v"><span class="t-up" id="cs-t-up">&mdash;</span>
          <span class="t-dn" id="cs-t-dn">&mdash;</span>
          <span class="t-fl" id="cs-t-fl">&mdash;</span></span>
        <span class="cs-l">Circuit progression</span>
      </div>
    </div>
    <a class="cs-form" id="cs-form-link" href="/sessions?type=race,race_ai,race_online" title="See the races behind this trend">
      <span class="cs-trend fl" id="cs-trend">&mdash;</span>
      <span class="cs-spark" id="cs-spark"></span>
    </a>
  </div>

  <!-- Results tier — hidden unless there are real races (spec gate) -->
  <div class="career-results" id="career-results" style="display:none">
    <div class="cs-cell"><span class="cs-v blue" id="cs-finish">&mdash;</span><span class="cs-l">Avg Finish</span></div>
    <div class="cs-cell"><span class="cs-v" id="cs-gained">&mdash;</span><span class="cs-l">Pos Gained</span></div>
    <div class="cs-cell"><span class="cs-v green" id="cs-podium">&mdash;</span><span class="cs-l">Podium</span></div>
    <span class="cs-results-sample" id="cs-results-sample"></span>
  </div>

  <!-- Two-column: recent feed leads, circuits/cars aside -->
  <div class="home-cols">
    <div class="home-main">
      <div class="section-head">
        <h2>Recent sessions</h2>
        <a href="/sessions" class="section-link">All sessions &rarr;</a>
      </div>
      <div id="recent-list"></div>
    </div>
    <div class="home-side">
      <div class="panel">
        <div class="panel-head">
          <h2>Top circuits</h2>
          <a href="/circuits">All circuits &rarr;</a>
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
<script src="/static/js/class.js"></script>
<script src="/static/js/track_mini.js"></script>
<script src="/static/js/home.js"></script>
</body>
</html>
"""
