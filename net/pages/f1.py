"""
F1 exploratory pages — feature/f1-dip-toes.

Two minimal screens that consume /f1/state.json:
  - F1_LIVE_HTML : compact live dashboard (gear/speed/rpm + bars + tyres)
  - F1_RAW_HTML  : raw key/value dump with change highlighting
"""

F1_LIVE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder · F1 Live</title>
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/base.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--color-bg);color:var(--color-text-primary);font-family:var(--font-mono);min-height:100vh}
.tb{height:50px;display:flex;align-items:center;padding:0 var(--space-4);gap:14px;border-bottom:1px solid var(--color-border);position:sticky;top:0;background:var(--color-bg);z-index:10}
.tb h1{font-size:var(--text-md);letter-spacing:3px;text-transform:uppercase;flex:1}
.tb .pill{font-size:var(--text-xs);color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:1px}
.tb .pill b{color:var(--color-text-primary);font-weight:var(--fw-medium)}
.tb a{font-size:var(--text-xs);color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:1px;text-decoration:none}
.tb a:hover{color:var(--color-text-primary)}
.main{padding:var(--space-4);display:grid;gap:var(--space-3);grid-template-columns:repeat(12,1fr)}
.card{background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-md);padding:var(--space-3);min-height:120px;display:flex;flex-direction:column;gap:8px}
.card h2{font-size:var(--text-xs);color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:.12em;font-weight:var(--fw-medium)}
.big{font-size:var(--dash-value-size);font-weight:var(--fw-black);font-variant-numeric:tabular-nums;line-height:1}
.sub{font-size:var(--text-xs);color:var(--color-text-muted)}
.span-3{grid-column:span 3}.span-4{grid-column:span 4}.span-6{grid-column:span 6}.span-12{grid-column:span 12}
.bar{height:14px;background:var(--color-surface-2);border:1px solid var(--color-border);border-radius:var(--radius-sm);overflow:hidden;position:relative}
.bar>i{display:block;height:100%;width:0;background:var(--color-green);transition:width .08s linear}
.bar.brake>i{background:var(--color-red)}
.bar.rpm>i{background:var(--color-amber)}
.bar .lbl{position:absolute;inset:0;display:flex;align-items:center;justify-content:flex-end;padding-right:6px;font-size:10px;color:var(--color-text-primary);mix-blend-mode:difference}
.row{display:flex;align-items:center;gap:10px}.row .l{flex:0 0 60px;color:var(--color-text-secondary);font-size:11px;text-transform:uppercase;letter-spacing:.1em}.row .v{flex:1}
.tyres{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.tyre{background:var(--color-surface-2);border:1px solid var(--color-border);border-radius:var(--radius-sm);padding:8px;text-align:center}
.tyre .pos{font-size:10px;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:.1em}
.tyre .t{font-size:var(--text-lg);font-weight:var(--fw-bold);font-variant-numeric:tabular-nums}
.tyre .p{font-size:11px;color:var(--color-text-secondary)}
.drs-on{color:var(--color-green)}.drs-off{color:var(--color-text-muted)}
.kv{display:grid;grid-template-columns:1fr auto;gap:4px 12px;font-size:12px}
.kv .k{color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:.08em;font-size:10px}
.kv .v{font-variant-numeric:tabular-nums;text-align:right}
.dot{width:8px;height:8px;border-radius:50%;background:#555;display:inline-block;margin-right:6px;vertical-align:middle}
.dot.live{background:var(--color-green);box-shadow:0 0 8px var(--color-green)}
.dot.stale{background:var(--color-amber)}
</style>
</head>
<body>
<div class="tb">
  <h1><span class="dot" id="dot"></span>F1 Live</h1>
  <span class="pill">Session <b id="m-session">—</b></span>
  <span class="pill">Track <b id="m-track">—</b></span>
  <span class="pill">Rate <b id="m-rate">—</b></span>
  <span class="pill">Age <b id="m-age">—</b></span>
  <a href="/f1/raw">Raw</a>
  <a href="/dashboard">Forza</a>
  <a href="/">Home</a>
</div>

<div class="main">
  <div class="card span-3">
    <h2>Gear</h2>
    <div class="big" id="gear">N</div>
    <div class="sub"><span class="drs-off" id="drs">DRS</span></div>
  </div>

  <div class="card span-3">
    <h2>Speed (mph)</h2>
    <div class="big" id="speed">—</div>
    <div class="sub" id="speed-kph">— km/h</div>
  </div>

  <div class="card span-3">
    <h2>RPM</h2>
    <div class="big" id="rpm">—</div>
    <div class="bar rpm"><i id="rpm-bar"></i><div class="lbl" id="rpm-pct">0%</div></div>
  </div>

  <div class="card span-3">
    <h2>Lap</h2>
    <div class="big" id="lap-num">—</div>
    <div class="sub">Cur <b id="lap-cur">—</b> · Last <b id="lap-last">—</b> · P<span id="pos">—</span></div>
  </div>

  <div class="card span-6">
    <h2>Inputs</h2>
    <div class="row"><div class="l">Throttle</div><div class="v"><div class="bar"><i id="thr"></i><div class="lbl" id="thr-v">0%</div></div></div></div>
    <div class="row"><div class="l">Brake</div><div class="v"><div class="bar brake"><i id="brk"></i><div class="lbl" id="brk-v">0%</div></div></div></div>
    <div class="row"><div class="l">Steer</div><div class="v" id="steer">0.000</div></div>
    <div class="row"><div class="l">Clutch</div><div class="v" id="clutch">0%</div></div>
  </div>

  <div class="card span-6">
    <h2>Tyres (surface °C / pressure psi)</h2>
    <div class="tyres">
      <div class="tyre"><div class="pos">FL</div><div class="t" id="t-fl">—</div><div class="p" id="p-fl">—</div></div>
      <div class="tyre"><div class="pos">FR</div><div class="t" id="t-fr">—</div><div class="p" id="p-fr">—</div></div>
      <div class="tyre"><div class="pos">RL</div><div class="t" id="t-rl">—</div><div class="p" id="p-rl">—</div></div>
      <div class="tyre"><div class="pos">RR</div><div class="t" id="t-rr">—</div><div class="p" id="p-rr">—</div></div>
    </div>
  </div>

  <div class="card span-4">
    <h2>Engine / Fuel</h2>
    <div class="kv">
      <div class="k">Engine °C</div><div class="v" id="eng-t">—</div>
      <div class="k">Fuel (kg)</div><div class="v" id="fuel">—</div>
      <div class="k">Fuel laps left</div><div class="v" id="fuel-laps">—</div>
      <div class="k">Compound</div><div class="v" id="cmp">—</div>
      <div class="k">Tyre age (laps)</div><div class="v" id="tage">—</div>
    </div>
  </div>

  <div class="card span-4">
    <h2>Brake temps (°C)</h2>
    <div class="kv">
      <div class="k">FL</div><div class="v" id="bt-fl">—</div>
      <div class="k">FR</div><div class="v" id="bt-fr">—</div>
      <div class="k">RL</div><div class="v" id="bt-rl">—</div>
      <div class="k">RR</div><div class="v" id="bt-rr">—</div>
    </div>
  </div>

  <div class="card span-4">
    <h2>G-forces / weather</h2>
    <div class="kv">
      <div class="k">g lat</div><div class="v" id="glat">—</div>
      <div class="k">g lon</div><div class="v" id="glon">—</div>
      <div class="k">g vert</div><div class="v" id="gver">—</div>
      <div class="k">Air °C</div><div class="v" id="air">—</div>
      <div class="k">Track °C</div><div class="v" id="trk">—</div>
      <div class="k">Weather</div><div class="v" id="wx">—</div>
    </div>
  </div>
</div>

<script>
let lastTs=null, rateBuf=[];
function num(x,d){return (typeof x==='number')?x.toFixed(d):'—'}
function pct(x){return (typeof x==='number')?Math.round(x)+'%':'—'}
function setBar(id,v,labelId){
  const el=document.getElementById(id);
  if(el)el.style.width=Math.max(0,Math.min(100,v||0))+'%';
  if(labelId){const l=document.getElementById(labelId);if(l)l.textContent=pct(v)}
}
function tick(d){
  const now=performance.now();
  if(lastTs!==null){rateBuf.push(now-lastTs);if(rateBuf.length>30)rateBuf.shift();}
  lastTs=now;
  const avg=rateBuf.length?(rateBuf.reduce((a,b)=>a+b,0)/rateBuf.length):0;
  document.getElementById('m-rate').textContent=avg?(1000/avg).toFixed(1)+' Hz':'—';

  const age=d._last_update_age_s;
  const dot=document.getElementById('dot');
  dot.className='dot '+(age==null?'':age<2?'live':'stale');
  document.getElementById('m-age').textContent=age==null?'—':age.toFixed(1)+'s';
  document.getElementById('m-session').textContent=d._session_uid?String(d._session_uid).slice(-6):'—';
  document.getElementById('m-track').textContent=d.track||'—';

  const g=d.gear; document.getElementById('gear').textContent=(g===0?'N':(g===-1?'R':(g==null?'—':String(g))));
  document.getElementById('drs').textContent='DRS';
  document.getElementById('drs').className=d.drs?'drs-on':'drs-off';

  document.getElementById('speed').textContent=num(d.speed_mph,0);
  document.getElementById('speed-kph').textContent=(typeof d.speed_mph==='number'?Math.round(d.speed_mph*1.60934):'—')+' km/h';

  document.getElementById('rpm').textContent=d.rpm!=null?d.rpm:'—';
  // F1 doesn't ship a max RPM in CarTelemetry; assume 15000 for the bar.
  const rpmPct = d.rpm!=null ? Math.min(100, d.rpm/15000*100) : 0;
  setBar('rpm-bar', rpmPct, 'rpm-pct');

  document.getElementById('lap-num').textContent=d.lap_number??'—';
  document.getElementById('lap-cur').textContent=d.current_lap_time!=null?d.current_lap_time.toFixed(3)+'s':'—';
  document.getElementById('lap-last').textContent=d.last_lap_time!=null?d.last_lap_time.toFixed(3)+'s':'—';
  document.getElementById('pos').textContent=d.race_position??'—';

  setBar('thr', d.throttle_pct, 'thr-v');
  setBar('brk', d.brake_pct,    'brk-v');
  document.getElementById('steer').textContent=num(d.steer,3);
  document.getElementById('clutch').textContent=pct(d.clutch_pct);

  for(const c of ['fl','fr','rl','rr']){
    const t=d['tyre_surface_temp_'+c], p=d['tyre_pressure_'+c];
    document.getElementById('t-'+c).textContent = t!=null?t+'°':'—';
    document.getElementById('p-'+c).textContent = p!=null?p.toFixed(1)+' psi':'—';
    const bt=d['brake_temp_'+c];
    document.getElementById('bt-'+c).textContent = bt!=null?bt+'°':'—';
  }
  document.getElementById('eng-t').textContent=d.engine_temp!=null?d.engine_temp+'°':'—';
  document.getElementById('fuel').textContent=num(d.fuel_in_tank,2);
  document.getElementById('fuel-laps').textContent=num(d.fuel_remaining_laps,1);
  document.getElementById('cmp').textContent=d.tyre_compound||'—';
  document.getElementById('tage').textContent=d.tyre_age_laps??'—';

  document.getElementById('glat').textContent=num(d.g_lat,2);
  document.getElementById('glon').textContent=num(d.g_lon,2);
  document.getElementById('gver').textContent=num(d.g_vert,2);
  document.getElementById('air').textContent=d.air_temp_c!=null?d.air_temp_c+'°':'—';
  document.getElementById('trk').textContent=d.track_temp_c!=null?d.track_temp_c+'°':'—';
  document.getElementById('wx').textContent=d.weather_condition||'—';
}
async function poll(){
  try{ tick(await fetch('/f1/state.json',{cache:'no-store'}).then(r=>r.json())); }catch(e){}
}
setInterval(poll,100);
poll();
</script>
</body>
</html>
"""

F1_RAW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder · F1 Raw</title>
<link rel="stylesheet" href="/static/tokens.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--color-bg);color:var(--color-text-primary);font-family:var(--font-mono);min-height:100vh}
.tb{height:50px;display:flex;align-items:center;padding:0 var(--space-4);gap:14px;border-bottom:1px solid var(--color-border);position:sticky;top:0;background:var(--color-bg);z-index:10}
.tb h1{font-size:var(--text-md);letter-spacing:3px;text-transform:uppercase;flex:1}
.tb a{font-size:var(--text-xs);color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:1px;text-decoration:none}
.tb a:hover{color:var(--color-text-primary)}
.meta{padding:14px var(--space-4);border-bottom:1px solid var(--color-border-subtle);font-size:var(--text-xs);color:var(--color-text-secondary);display:flex;gap:24px;flex-wrap:wrap}
.meta b{color:var(--color-text-primary);font-weight:var(--fw-medium)}
.search{padding:8px var(--space-4);border-bottom:1px solid var(--color-border-subtle)}
.search input{width:100%;max-width:420px;background:var(--color-surface);border:1px solid var(--color-border);color:var(--color-text-primary);font-family:inherit;font-size:var(--text-sm);padding:6px 10px;border-radius:var(--radius-sm)}
.grid{padding:14px var(--space-4);display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:0 24px}
.row{display:flex;justify-content:space-between;font-size:.78rem;padding:3px 0;border-bottom:1px dotted var(--n-900)}
.row.changed{background:rgba(74,154,239,.08)}
.k{color:var(--color-text-secondary)}
.v{color:var(--color-text-primary);font-variant-numeric:tabular-nums}
.empty{padding:60px;text-align:center;color:var(--color-text-muted)}
.counts{display:flex;gap:10px;flex-wrap:wrap}
.counts span{background:var(--color-surface);border:1px solid var(--color-border);padding:2px 8px;border-radius:var(--radius-sm)}
</style>
</head>
<body>
<div class="tb">
  <h1>F1 Raw Telemetry</h1>
  <a href="/f1">Live</a>
  <a href="/debug/raw">Forza Raw</a>
  <a href="/">Home</a>
</div>
<div class="meta">
  <span>Session UID: <b id="m-session">—</b></span>
  <span>Packet rate: <b id="m-rate">—</b></span>
  <span>Age: <b id="m-age">—</b></span>
  <span>Fields: <b id="m-count">0</b></span>
  <span class="counts" id="m-counts"></span>
</div>
<div class="search"><input id="filter" type="text" placeholder="Filter fields (tyre, brake, lap, …)"></div>
<div id="grid" class="grid"></div>
<div id="empty" class="empty">Waiting for telemetry… start an F1 session (or check UDP setup → port 20777).</div>
<script>
const grid=document.getElementById('grid');
const empty=document.getElementById('empty');
const filterEl=document.getElementById('filter');
let prev={}, lastTs=null, rateBuf=[];
function fmt(v){
  if(v===null||v===undefined)return '—';
  if(typeof v==='number')return Math.abs(v)>=1000?v.toFixed(0):v.toFixed(4).replace(/\\.?0+$/,'');
  if(typeof v==='boolean')return v?'true':'false';
  if(typeof v==='object')return JSON.stringify(v);
  return String(v);
}
function tick(d){
  const now=performance.now();
  if(lastTs!==null){rateBuf.push(now-lastTs);if(rateBuf.length>30)rateBuf.shift();}
  lastTs=now;
  const avg=rateBuf.length?(rateBuf.reduce((a,b)=>a+b,0)/rateBuf.length):0;
  document.getElementById('m-rate').textContent=avg?(1000/avg).toFixed(1)+' Hz':'—';
  document.getElementById('m-session').textContent=d._session_uid?String(d._session_uid):'—';
  document.getElementById('m-age').textContent=d._last_update_age_s!=null?d._last_update_age_s.toFixed(2)+'s':'—';

  const counts=d._packet_counts||{};
  document.getElementById('m-counts').innerHTML =
    Object.entries(counts).map(([k,v])=>`<span>${k}: <b>${v}</b></span>`).join('');

  const keys=Object.keys(d).filter(k=>!k.startsWith('_')).sort();
  document.getElementById('m-count').textContent=keys.length;
  if(!keys.length){empty.style.display='';grid.innerHTML='';return;}
  empty.style.display='none';
  const f=filterEl.value.toLowerCase();
  let html='';
  for(const k of keys){
    if(f && !k.toLowerCase().includes(f))continue;
    const v=d[k], pv=prev[k];
    const changed=(pv!==undefined && pv!==v)?' changed':'';
    html+=`<div class="row${changed}"><span class="k">${k}</span><span class="v">${fmt(v)}</span></div>`;
  }
  grid.innerHTML=html;
  prev=d;
}
async function poll(){
  try{ tick(await fetch('/f1/state.json',{cache:'no-store'}).then(r=>r.json())); }catch(e){}
}
setInterval(poll,200);
poll();
filterEl.addEventListener('input',()=>tick(prev));
</script>
</body>
</html>
"""
