TELEMETRY_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder &middot; Telemetry</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--color-bg);color:var(--color-text-primary);font-family:var(--font-mono);min-height:100vh;overflow-x:hidden}
a{color:inherit;text-decoration:none}
.tb{height:50px;display:flex;align-items:center;padding:0 var(--space-4);gap:14px;border-bottom:1px solid var(--color-border);background:var(--color-bg);z-index:20;position:sticky;top:0}
.tb h1{font-size:var(--text-md);color:var(--color-text-primary);letter-spacing:3px;text-transform:uppercase;flex:1}
.tb-nav{display:flex;gap:14px}
.tb-nav a{font-size:var(--text-xs);color:var(--color-text-secondary);letter-spacing:1px;text-transform:uppercase}
.tb-nav a:hover{color:var(--color-text-primary)}
.tb-nav a.cur{color:var(--color-text-primary);border-bottom:1px solid var(--color-text-secondary)}
.breadcrumb{font-size:var(--text-xs);color:var(--color-text-secondary);padding:8px var(--space-4);border-bottom:1px solid var(--color-border-subtle)}
.breadcrumb a{color:var(--n-400)}.breadcrumb a:hover{color:var(--n-200)}
.tele-layout{display:flex;min-height:calc(100vh - 90px)}
.ctrl-col{width:220px;flex-shrink:0;border-right:1px solid var(--border-sub);padding:var(--sp-3) var(--sp-4);overflow-y:auto;position:sticky;top:50px;max-height:calc(100vh - 50px)}
@media(max-width:768px){.tele-layout{flex-direction:column}.ctrl-col{width:100%;position:static;max-height:none;border-right:none;border-bottom:1px solid var(--border-sub)}}
.ctrl-section{margin-bottom:var(--sp-4)}
.ctrl-lbl{font-size:var(--text-xs);color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:2px;margin-bottom:var(--space-2)}
.lap-item{display:flex;align-items:center;gap:6px;padding:3px 4px;font-size:.76rem;cursor:pointer;border-radius:3px;user-select:none}
.lap-item:hover{background:var(--surface)}
.lap-swatch{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.lap-time-s{color:var(--n-300);margin-left:auto;font-size:.7rem;font-variant-numeric:tabular-nums}
.lap-best-badge{font-size:.6rem;color:var(--accent-soft)}
input[type=checkbox]{accent-color:var(--accent);width:12px;height:12px;flex-shrink:0}
.ch-grid{display:grid;grid-template-columns:1fr 1fr;gap:3px}
.ch-tog{display:flex;align-items:center;gap:4px;font-size:.7rem;color:var(--n-200);padding:3px 4px;border-radius:3px;cursor:pointer;user-select:none}
.ch-tog:hover{background:var(--surface)}
.xmode-btns{display:flex;gap:3px}
.xmode-btn{flex:1;background:var(--color-surface-2);border:1px solid var(--surface-bd);color:var(--color-text-secondary);font-family:inherit;font-size:var(--text-xs);padding:4px 0;border-radius:var(--radius-sm);cursor:pointer;text-align:center}
.xmode-btn.active{background:var(--accent-bg);border-color:var(--accent-bd);color:var(--accent-soft)}
.ctrl-sel{width:100%;background:var(--surface);border:1px solid var(--surface-bd);color:var(--text);font-family:inherit;font-size:.74rem;padding:5px 6px;border-radius:4px}
.panels-col{flex:1;min-width:0;padding:var(--sp-3) var(--sp-4) var(--sp-6)}
.sector-hdr{margin-bottom:var(--sp-3);border:1px solid var(--border-sub);border-radius:4px;background:var(--bg-raised);overflow:hidden}
.s-hdr-row{display:flex;align-items:center;padding:4px var(--sp-3);gap:var(--sp-2);border-bottom:1px solid var(--border-faint);font-size:.68rem}
.s-hdr-row:last-child{border-bottom:none}
.s-row-lbl{width:24px;color:var(--color-text-secondary);font-size:var(--text-xs);text-transform:uppercase;letter-spacing:1px;flex-shrink:0}
.s-cell{flex:1;text-align:center;font-variant-numeric:tabular-nums;font-size:.7rem;color:var(--n-400)}
.s-cell.best{color:var(--accent-soft);font-weight:bold}
.s-cell-d{flex:.7}
.s-cell-hd{flex:1;text-align:center;font-size:var(--text-xs);color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:.5px}
.lap-summaries{margin-bottom:var(--sp-3);display:flex;flex-direction:column;gap:3px}
.lap-sum-bar{display:flex;align-items:center;gap:var(--sp-3);flex-wrap:wrap;padding:5px var(--sp-3);border-radius:4px;background:var(--bg-raised);border-left:3px solid}
.lsb-l{font-size:.76rem;font-weight:900;width:48px;flex-shrink:0}
.lsb-t{font-size:.88rem;font-weight:900;font-variant-numeric:tabular-nums;width:80px;flex-shrink:0}
.lsb-s{font-size:.66rem;color:var(--n-400);font-variant-numeric:tabular-nums}
.lsb-d{font-size:.76rem;font-variant-numeric:tabular-nums;margin-left:auto}
.lsb-slip{font-size:1rem;color:var(--n-500)}
.panel-wrap{margin-bottom:2px}
.panel-lbl-row{display:flex;align-items:center;margin-bottom:1px;min-height:14px; font-size:1rem}
.p-lbl{font-size:1rem;color:var(--n-500);text-transform:uppercase;letter-spacing:1.5px}
.panel-svg-wrap{position:relative;overflow:hidden;border:1px solid var(--border-sub);border-radius:2px;background:var(--bg-raised);cursor:crosshair}
.panel-svg-wrap.panning{cursor:grab}
.chart-zoom-ctrl{position:absolute;top:4px;right:4px;display:flex;gap:3px;z-index:10;pointer-events:auto}
.czc-btn{background:rgba(20,20,28,.75);border:1px solid var(--color-border);color:var(--color-text-secondary);font-family:inherit;font-size:calc(var(--text-xs) * 1.3);padding:2px 7px;border-radius:var(--radius-sm);cursor:pointer;line-height:1.5;backdrop-filter:blur(4px)}
.czc-btn:hover{border-color:var(--n-300);color:var(--text)}
.panel-svg-wrap svg{display:block;width:100%}
.px-line{position:absolute;top:0;bottom:0;width:1px;background:rgba(255,255,255,.16);pointer-events:none;display:none}
#tele-tip{position:fixed;background:var(--color-surface-2);border:1px solid var(--color-border);color:var(--color-text-primary);font-size:var(--text-xs);padding:5px 10px;border-radius:4px;pointer-events:none;display:none;z-index:200;white-space:pre;line-height:1.7;font-family:var(--font-mono);min-width:160px}
.track-map-wrap{margin-top:var(--sp-4);border:1px solid var(--border-sub);border-radius:2px;background:var(--bg-raised);overflow:hidden}
.tm-lbl{font-size:.56rem;color:var(--n-500);text-transform:uppercase;letter-spacing:1.5px;padding:4px var(--sp-3)}
#drag-sel{position:absolute;background:rgba(74,154,239,.1);border:1px solid rgba(74,154,239,.35);pointer-events:none;display:none;top:0;bottom:0}
.x-lbl-row{display:flex;justify-content:space-between;font-size:.56rem;color:var(--n-600);margin-top:3px;padding:0 1px}
#tele-loading{color:var(--n-400);font-size:.9rem;padding:60px;text-align:center}
.delta-neg{color:var(--accent-soft)}.delta-pos{color:var(--danger)}
.ctrl-sub{font-size:.62rem;color:var(--n-400);margin-top:4px;padding-left:2px}
.cs-ovl{display:none;position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:300;align-items:center;justify-content:center}
.cs-ovl.open{display:flex}
.cs-panel{background:var(--bg-raised);border:1px solid var(--border-sub);border-radius:6px;padding:18px 20px;min-width:360px;max-width:640px;max-height:80vh;overflow:auto}
.cs-ttl{font-size:.85rem;color:var(--text);margin-bottom:14px;font-weight:bold}
.cs-sess{padding:8px 10px;border:1px solid var(--border-faint);border-radius:4px;margin-bottom:6px;cursor:pointer;background:var(--bg-deep)}
.cs-sess:hover{border-color:var(--n-400)}
.cs-sess-hd{display:flex;justify-content:space-between;font-size:.72rem;color:var(--text)}
.cs-sess-meta{font-size:.6rem;color:var(--n-500);margin-top:2px}
.cs-laps{display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--border-faint)}
.cs-sess.expanded .cs-laps{display:block}
.cs-lap{padding:4px 8px;font-size:.7rem;color:var(--n-300);cursor:pointer;border-radius:2px;font-variant-numeric:tabular-nums}
.cs-lap:hover{background:var(--surface);color:var(--text)}
.cs-empty{padding:18px;text-align:center;color:var(--n-500);font-size:.78rem}
.cs-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}
.cs-btn{background:var(--surface);border:1px solid var(--surface-bd);color:var(--text);font-family:inherit;font-size:.7rem;padding:6px 14px;border-radius:4px;cursor:pointer}
.cs-btn:hover{border-color:var(--n-300)}
@media(max-width:768px){.lsb-slip,.lsb-s{display:none}.lap-sum-bar{flex-wrap:nowrap}}
</style>
</head>
<body>
<div class="tb">
  <h1>Pacefinder</h1>
  <nav class="tb-nav">
    <a href="/">Live</a><a href="/sessions" class="cur">Sessions</a><a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>
if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';
if(new URLSearchParams(location.search).get('embed')==='1'){
  document.querySelector('.tb').style.display='none';
}
</script>
<div class="breadcrumb" id="tele-breadcrumb">
  <a href="/sessions">Sessions</a> &rsaquo;
  <a href="#" id="bc-game" style="display:none"></a><span id="bc-gsep" style="display:none"> &rsaquo; </span>
  <a href="#" id="bc-track"></a> &rsaquo;
  <a href="#" id="bc-sess"></a> &rsaquo;
  <span>Telemetry</span>
</div>
<div class="tele-layout">
<div class="ctrl-col" id="ctrl-col">
  <div id="ctrl-loading" style="color:var(--n-400);font-size:.78rem;padding:8px 0">Loading&hellip;</div>
  <div id="ctrl-inner" style="display:none">
    <div class="ctrl-section">
      <div class="ctrl-lbl">Laps (up to 4)</div>
      <div id="lap-list"></div>
    </div>
    <div class="ctrl-section">
      <div class="ctrl-lbl">Reference</div>
      <select class="ctrl-sel" id="ref-sel" onchange="onRefChange()">
        <option value="">None</option>
        <option value="best_lap" selected>My Best Lap</option>
        <option value="theoretical">Theoretical Best</option>
        <option value="last_lap">Last Lap</option>
        <option value="cross_session">Lap from another session…</option>
      </select>
      <div id="cs-ref-label" class="ctrl-sub" style="display:none"></div>
    </div>
    <div class="ctrl-section">
      <div class="ctrl-lbl">Channels</div>
      <div class="ch-grid">
        <label class="ch-tog"><input type="checkbox" id="ch-speed" checked onchange="renderAll()"> Speed</label>
        <label class="ch-tog"><input type="checkbox" id="ch-throttle" checked onchange="renderAll()"> Throttle</label>
        <label class="ch-tog"><input type="checkbox" id="ch-brake" checked onchange="renderAll()"> Brake</label>
        <label class="ch-tog"><input type="checkbox" id="ch-gear" checked onchange="renderAll()"> Gear</label>
        <label class="ch-tog"><input type="checkbox" id="ch-steer" onchange="renderAll()"> Steering</label>
        <label class="ch-tog"><input type="checkbox" id="ch-slip" checked onchange="renderAll()"> Slip</label>
        <label class="ch-tog"><input type="checkbox" id="ch-tyre" onchange="renderAll()"> Tyres</label>
      </div>
    </div>
    <div class="ctrl-section">
      <div class="ctrl-lbl">X Axis</div>
      <div class="xmode-btns">
        <button class="xmode-btn active" id="xm-dist" onclick="setXMode('distance')">Distance</button>
        <button class="xmode-btn" id="xm-time" onclick="setXMode('time')">Time</button>
      </div>
    </div>
  </div>
</div>
<div class="panels-col">
  <div id="tele-loading">Loading telemetry data&hellip;</div>
  <div id="panels-inner" style="display:none">
    <div id="sector-hdr" class="sector-hdr"></div>
    <div id="lap-summaries" class="lap-summaries"></div>
    <div id="charts-area" style="position:relative">
      <div class="chart-zoom-ctrl">
        <button class="czc-btn" onclick="resetZoom()">Reset</button>
        <button class="czc-btn" onclick="stepZoom(-1)">−</button>
        <button class="czc-btn" onclick="stepZoom(1)">+</button>
      </div>
      <div id="drag-sel"></div>
      <div id="panel-delta" class="panel-wrap"></div>
      <div id="panel-speed" class="panel-wrap"></div>
      <div id="panel-throttle" class="panel-wrap"></div>
      <div id="panel-brake" class="panel-wrap"></div>
      <div id="panel-gear" class="panel-wrap"></div>
      <div id="panel-steer" class="panel-wrap"></div>
      <div id="panel-slip" class="panel-wrap"></div>
      <div id="panel-tyre" class="panel-wrap"></div>
    </div>
    <div class="x-lbl-row"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
    <div class="track-map-wrap" id="track-map-wrap" style="display:none">
      <div class="tm-lbl">Track Map &mdash; colour = speed (blue slow &rarr; red fast)</div>
      <div id="track-map-inner"></div>
    </div>
  </div>
</div>
</div>
<div id="tele-tip"></div>
<script src="/static/js/charts.js"></script>
<!-- Cross-session reference picker — opened from the Reference dropdown -->
<div class="cs-ovl" id="cs-ovl">
  <div class="cs-panel">
    <div class="cs-ttl" id="cs-ttl">Pick a reference lap</div>
    <div id="cs-list"><div class="cs-empty">Loading…</div></div>
    <div class="cs-actions">
      <button class="cs-btn" onclick="closeCrossSessionPicker()">Cancel</button>
    </div>
  </div>
</div>
<script src="/static/js/telemetry.js"></script>
</body>
</html>
"""
