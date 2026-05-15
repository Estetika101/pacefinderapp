TELEMETRY_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder &middot; Telemetry</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--color-bg);color:var(--color-text-primary);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;font-variant-numeric:tabular-nums;min-height:100vh;overflow-x:hidden}
a{color:inherit;text-decoration:none}
.tb{height:50px;display:flex;align-items:center;padding:0 var(--space-4);gap:14px;border-bottom:1px solid var(--color-border);background:var(--color-bg);z-index:20;position:sticky;top:0}
.tb h1{font-size:var(--text-md);color:var(--color-text-primary);letter-spacing:3px;text-transform:uppercase;flex:1}
.tb-nav{display:flex;gap:14px}
.tb-nav a{font-size:var(--text-xs);color:var(--color-text-secondary);letter-spacing:1px;text-transform:uppercase}
.tb-nav a:hover{color:var(--color-text-primary)}
.tb-nav a.cur{color:var(--color-text-primary);border-bottom:1px solid var(--color-text-secondary)}
.breadcrumb{font-size:var(--text-xs);color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:0.08em;padding:var(--space-2) var(--space-4);border-bottom:1px solid var(--color-border)}
.breadcrumb a{color:var(--color-text-tertiary)}.breadcrumb a:hover{color:var(--color-text-primary)}
.tele-layout{display:flex;min-height:calc(100vh - 90px);gap:8px;padding:8px}
.ctrl-col{width:220px;flex-shrink:0;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-md);padding:var(--sp-3) var(--sp-4);overflow-y:auto;position:sticky;top:58px;max-height:calc(100vh - 66px);align-self:flex-start}
/* In embed mode the iframe's own .tb is hidden, so anchor sticky to 0 and
   give the iframe body min-height:0 so it doesn't double-scroll the parent. */
html.embed body{min-height:0}
html.embed .tele-layout{min-height:0}
html.embed .ctrl-col{top:0;max-height:100vh}
@media(max-width:768px){.tele-layout{flex-direction:column}.ctrl-col{width:100%;position:static;max-height:none;border-right:none;border-bottom:1px solid var(--border-sub)}}
.ctrl-section{margin-bottom:var(--sp-4)}
.ctrl-lbl{font-size:10px;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:var(--space-2)}
.lap-item{display:flex;align-items:center;gap:8px;padding:6px var(--space-2);font-size:var(--text-sm);cursor:pointer;border-radius:var(--radius-sm);user-select:none}
.lap-item:hover{background:var(--color-surface-2)}
.lap-swatch{width:10px;height:10px;border-radius:2px;flex-shrink:0}
.lap-time-s{color:var(--color-text-tertiary);margin-left:auto;font-size:11px;font-variant-numeric:tabular-nums}
.lap-best-badge{font-size:10px;color:var(--color-accent)}
input[type=checkbox]{accent-color:var(--color-accent);width:12px;height:12px;flex-shrink:0}
.ch-grid{display:grid;grid-template-columns:1fr 1fr;gap:2px}
.ch-tog{display:flex;align-items:center;gap:6px;font-size:var(--text-sm);color:var(--color-text-secondary);padding:6px var(--space-2);border-radius:var(--radius-sm);cursor:pointer;user-select:none}
.ch-tog:hover{background:var(--color-surface-2);color:var(--color-text-primary)}
.xmode-btns{display:flex;gap:3px}
.xmode-btn{flex:1;background:var(--color-surface-2);border:1px solid var(--surface-bd);color:var(--color-text-secondary);font-family:inherit;font-size:var(--text-xs);padding:4px 0;border-radius:var(--radius-sm);cursor:pointer;text-align:center}
.xmode-btn.active{background:var(--accent-bg);border-color:var(--accent-bd);color:var(--accent-soft)}
.ctrl-sel{width:100%;background:var(--color-surface-2);border:1px solid var(--color-border);color:var(--color-text-primary);font-family:inherit;font-size:var(--text-sm);padding:6px 8px;border-radius:var(--radius-sm)}
.panels-col{flex:1;min-width:0;padding:var(--sp-3) var(--sp-4) var(--sp-6)}
/* Track map promoted to a sticky panel at the top of the charts column.
   JS (renderTrackMap) still controls visibility — it only un-hides the
   wrap when the lap actually has px/pz position samples. */
.track-map-wrap{
  position:sticky;top:58px;z-index:20;
  margin:0 0 var(--sp-3);
  border:1px solid var(--color-border);border-radius:var(--radius-md);
  background:var(--color-bg);overflow:hidden;
  /* Hard mask: opaque page-bg + a shadow so charts scrolling under the
     pinned panel can never read through (was bleeding — the SVG
     letterboxes with transparent margins inside a wide column). */
  box-shadow:0 8px 14px -6px rgba(0,0,0,0.95);
}
/* The map SVG meet-fits with transparent side margins; give the SVG box
   the page bg so those margins are solid, not see-through. Cap height so
   the pinned panel stays compact instead of a tall void. */
#track-map-inner{background:var(--color-bg)}
#track-map-inner svg{
  background:var(--color-bg);
  max-height:180px !important;
  width:100%;display:block;
}
html.embed .track-map-wrap{top:0}
.sector-hdr{margin-bottom:var(--sp-3);border:1px solid var(--color-border);border-radius:var(--radius-md);background:var(--color-surface);overflow:hidden}
.s-hdr-row{display:flex;align-items:center;padding:8px var(--sp-3);gap:var(--sp-2);border-bottom:1px solid var(--color-border-subtle);font-size:11px}
.s-hdr-row:last-child{border-bottom:none}
.s-row-lbl{width:24px;color:var(--color-text-tertiary);font-size:10px;text-transform:uppercase;letter-spacing:0.08em;flex-shrink:0}
.s-cell{flex:1;text-align:center;font-variant-numeric:tabular-nums;font-size:var(--text-sm);color:var(--color-text-secondary)}
.s-cell.best{color:var(--color-accent);font-weight:600}
.s-cell-d{flex:.7}
.s-cell-hd{flex:1;text-align:center;font-size:10px;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:0.08em}
.lap-summaries{margin-bottom:var(--sp-3);display:flex;flex-direction:column;gap:4px}
.lap-sum-bar{display:flex;align-items:center;gap:var(--sp-3);flex-wrap:wrap;padding:10px var(--sp-3);border-radius:var(--radius-md);background:var(--color-surface);border:1px solid var(--color-border);border-left:3px solid}
.lsb-l{font-size:var(--text-sm);font-weight:600;width:48px;flex-shrink:0}
.lsb-t{font-size:var(--text-md);font-weight:700;font-variant-numeric:tabular-nums;width:84px;flex-shrink:0}
.lsb-s{font-size:11px;color:var(--color-text-tertiary);font-variant-numeric:tabular-nums}
.lsb-d{font-size:var(--text-sm);font-variant-numeric:tabular-nums;margin-left:auto}
.lsb-slip{font-size:var(--text-md);color:var(--color-text-tertiary)}
.panel-wrap{margin-bottom:8px}
.panel-lbl-row{display:flex;align-items:baseline;margin-bottom:6px;min-height:14px}
.p-lbl{font-size:10px;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:0.08em;font-weight:500}
.ref-tag{margin-left:auto;font-size:10px;color:var(--color-text-tertiary);letter-spacing:0.08em;text-transform:uppercase;padding:2px 7px;border:1px solid var(--color-border);border-radius:4px}
.panel-svg-wrap{position:relative;overflow:hidden;border:1px solid var(--color-border);border-radius:var(--radius-md);background:var(--color-surface);cursor:crosshair}
.panel-svg-wrap.panning{cursor:grab}
.chart-zoom-ctrl{position:absolute;top:4px;right:4px;display:flex;gap:3px;z-index:10;pointer-events:auto}
.czc-btn{background:rgba(20,20,28,.75);border:1px solid var(--color-border);color:var(--color-text-secondary);font-family:inherit;font-size:calc(var(--text-xs) * 1.3);padding:2px 7px;border-radius:var(--radius-sm);cursor:pointer;line-height:1.5;backdrop-filter:blur(4px)}
.czc-btn:hover{border-color:var(--color-text-secondary);color:var(--color-text-primary)}
.panel-svg-wrap svg{display:block;width:100%}
.px-line{position:absolute;top:0;bottom:0;width:1px;background:rgba(255,255,255,.16);pointer-events:none;display:none}
.px-line.locked{background:var(--color-accent,#f59e0b);width:2px;opacity:.85;box-shadow:0 0 4px rgba(245,158,11,.4)}
#tele-tip{position:fixed;background:var(--color-surface-2);border:1px solid var(--color-border);color:var(--color-text-primary);font-size:var(--text-xs);padding:5px 10px;border-radius:4px;pointer-events:none;display:none;z-index:200;white-space:pre;line-height:1.7;font-family:var(--font-mono);min-width:160px}
.tm-lbl{font-size:10px;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:0.08em;padding:8px var(--sp-3);border-bottom:1px solid var(--color-border-subtle)}
#drag-sel{position:absolute;background:rgba(245,158,11,.18);border:2px dashed rgba(245,158,11,.85);box-shadow:inset 0 0 0 1px rgba(0,0,0,.4),0 0 8px rgba(245,158,11,.35);pointer-events:none;display:none;top:0;bottom:0;border-radius:2px;z-index:5}
.tele-help{display:flex;flex-wrap:wrap;gap:10px;padding:8px 12px;margin-bottom:var(--sp-3);background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-md);font-size:11px;color:var(--color-text-tertiary)}
.tele-help kbd{background:var(--color-surface-2);border:1px solid var(--color-border);border-bottom-width:2px;border-radius:3px;padding:1px 5px;font-family:var(--font-mono);font-size:10px;color:var(--color-text-secondary)}
.tele-help-sep{color:var(--color-text-quaternary)}
.x-lbl-row{display:flex;justify-content:space-between;font-size:10px;color:var(--color-text-quaternary);margin-top:3px;padding:0 1px;font-family:var(--font-mono)}
/* Per-chart mini-axis (issue #12 polish bundle). Same percentages as
   .x-lbl-row but rendered under every chart for at-a-glance scanning. */
.px-axis{display:flex;justify-content:space-between;font-size:10px;color:var(--color-text-quaternary);padding:2px 1px 4px;line-height:1;font-family:var(--font-mono)}
#tele-loading{color:var(--color-text-tertiary);font-size:var(--text-sm);padding:60px;text-align:center}
.delta-neg{color:var(--color-green)}.delta-pos{color:var(--color-red)}
.ctrl-sub{font-size:11px;color:var(--color-text-tertiary);margin-top:4px;padding-left:2px}
.cs-ovl{display:none;position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:300;align-items:center;justify-content:center}
.cs-ovl.open{display:flex}
.cs-panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-md);padding:18px 20px;min-width:360px;max-width:640px;max-height:80vh;overflow:auto}
.cs-ttl{font-size:var(--text-md);color:var(--color-text-primary);margin-bottom:14px;font-weight:600}
.cs-sess{padding:10px 12px;border:1px solid var(--color-border-subtle);border-radius:var(--radius-sm);margin-bottom:6px;cursor:pointer;background:var(--color-bg)}
.cs-sess:hover{border-color:var(--color-text-tertiary)}
.cs-sess-hd{display:flex;justify-content:space-between;font-size:var(--text-sm);color:var(--color-text-primary)}
.cs-sess-meta{font-size:11px;color:var(--color-text-tertiary);margin-top:2px}
.cs-laps{display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--color-border-subtle)}
.cs-sess.expanded .cs-laps{display:block}
.cs-lap{padding:5px 8px;font-size:var(--text-sm);color:var(--color-text-secondary);cursor:pointer;border-radius:var(--radius-sm);font-variant-numeric:tabular-nums}
.cs-lap:hover{background:var(--color-surface-2);color:var(--color-text-primary)}
.cs-empty{padding:18px;text-align:center;color:var(--color-text-tertiary);font-size:var(--text-sm)}
.cs-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}
.cs-btn{background:var(--color-surface-2);border:1px solid var(--color-border);color:var(--color-text-primary);font-family:inherit;font-size:var(--text-sm);padding:6px 14px;border-radius:var(--radius-sm);cursor:pointer}
.cs-btn:hover{border-color:var(--color-text-secondary)}
@media(max-width:768px){.lsb-slip,.lsb-s{display:none}.lap-sum-bar{flex-wrap:nowrap}}
</style>
</head>
<body>
<div class="tb">
  <h1>Pacefinder</h1>
  <nav class="tb-nav">
    <a href="/dashboard">Live</a><a href="/">Home</a><a href="/sessions" class="cur">Career</a><a href="/setup">Setup</a>
    <a href="/admin" id="nav-admin" style="display:none">Admin</a>
  </nav>
</div>
<script>
if(location.search.includes('debug=true'))document.getElementById('nav-admin').style.display='';
if(new URLSearchParams(location.search).get('embed')==='1'){
  document.querySelector('.tb').style.display='none';
  // Hide the in-iframe breadcrumb — the parent session detail page already
  // shows one. Pin .ctrl-col to top:0 since the iframe topbar is gone.
  document.documentElement.classList.add('embed');
  const bc=document.getElementById('tele-breadcrumb');
  if(bc) bc.style.display='none';
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
      <div class="ctrl-lbl" title="Up to 4 laps can be selected for overlay comparison. Capped at 4 so the chart and track-map colors stay legible — picking a 5th drops the oldest selection.">Laps (up to 4)</div>
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
      <div id="ref-status" class="ctrl-sub" style="display:none;color:var(--warn,#f59e0b)"></div>
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
    <!-- X-axis toggle hidden until Time mode has a clear use case;
         distance is the default per-distance industry standard.
         Buttons kept off-page so setXMode() callers don't NPE. -->
    <div class="xmode-btns" style="display:none">
      <button class="xmode-btn active" id="xm-dist">Distance</button>
      <button class="xmode-btn" id="xm-time">Time</button>
    </div>
  </div>
</div>
<div class="panels-col">
  <div id="tele-loading">Loading telemetry data&hellip;</div>
  <div id="panels-inner" style="display:none">
    <div class="track-map-wrap" id="track-map-wrap" style="display:none">
      <div class="tm-lbl">Track map &mdash; colour = speed (blue slow &rarr; red fast)</div>
      <div id="track-map-inner"></div>
    </div>
    <div id="sector-hdr" class="sector-hdr"></div>
    <div id="lap-summaries" class="lap-summaries"></div>
    <div class="tele-help" id="tele-help">
      <span><kbd>drag</kbd> zoom to selection</span>
      <span class="tele-help-sep">·</span>
      <span><kbd>space</kbd>+<kbd>drag</kbd> pan when zoomed</span>
      <span class="tele-help-sep">·</span>
      <span><kbd>click</kbd> lock cursor</span>
      <span class="tele-help-sep">·</span>
      <span><kbd>←</kbd> <kbd>→</kbd> nudge (with <kbd>shift</kbd> = 10×)</span>
      <span class="tele-help-sep">·</span>
      <span><kbd>esc</kbd> unlock</span>
    </div>
    <div id="charts-area" style="position:relative">
      <div class="chart-zoom-ctrl">
        <button class="czc-btn" onclick="resetZoom()">Reset</button>
        <button class="czc-btn" onclick="stepZoom(-1)">−</button>
        <button class="czc-btn" onclick="stepZoom(1)">+</button>
      </div>
      <div id="drag-sel"></div>
      <div id="panels-empty" style="display:none;color:var(--n-400);font-size:.9rem;padding:60px;text-align:center">Select at least one lap to view telemetry.</div>
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
  </div>
</div>
</div>
<div id="tele-tip"></div>
<script src="/static/js/perf.js"></script>
<script>Perf.mark('page:start');Perf.autoReport('/sessions/telemetry');</script>
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
