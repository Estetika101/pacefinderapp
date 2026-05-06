DEBUG_RAW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pacefinder · Raw Telemetry</title>
<link rel="stylesheet" href="/static/tokens.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--color-bg);color:var(--color-text-primary);font-family:var(--font-mono);min-height:100vh}
.tb{height:50px;display:flex;align-items:center;padding:0 var(--space-4);gap:14px;border-bottom:1px solid var(--color-border);position:sticky;top:0;background:var(--color-bg);z-index:10}
.tb h1{font-size:var(--text-md);color:var(--color-text-primary);letter-spacing:3px;text-transform:uppercase;flex:1}
.tb a{font-size:var(--text-xs);color:var(--color-text-secondary);letter-spacing:1px;text-transform:uppercase;text-decoration:none}
.tb a:hover{color:var(--color-text-primary)}
.meta{padding:14px var(--space-4);border-bottom:1px solid var(--color-border-subtle);font-size:var(--text-xs);color:var(--color-text-secondary);display:flex;gap:24px;flex-wrap:wrap}
.meta b{color:var(--color-text-primary);font-weight:var(--fw-medium)}
.search{padding:8px var(--space-4);border-bottom:1px solid var(--color-border-subtle)}
.search input{width:100%;max-width:420px;background:var(--color-surface);border:1px solid var(--color-border);color:var(--color-text-primary);font-family:inherit;font-size:var(--text-sm);padding:6px 10px;border-radius:var(--radius-sm)}
.grid{padding:14px var(--space-4);display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:0 24px}
.row{display:flex;justify-content:space-between;font-size:.78rem;padding:3px 0;border-bottom:1px dotted var(--n-900)}
.row.changed{background:rgba(74,154,239,.06)}
.k{color:var(--color-text-secondary)}
.v{color:var(--color-text-primary);font-variant-numeric:tabular-nums}
.empty{padding:60px;text-align:center;color:var(--color-text-muted)}
</style>
</head>
<body>
<div class="tb">
  <h1>Raw Telemetry</h1>
  <a href="/">Dashboard</a>
  <a href="/sessions">Sessions</a>
</div>
<div class="meta">
  <span>Game: <b id="m-game">—</b></span>
  <span>Packet rate: <b id="m-rate">—</b></span>
  <span>Last update: <b id="m-age">—</b></span>
  <span>Fields: <b id="m-count">0</b></span>
</div>
<div class="search"><input id="filter" type="text" placeholder="Filter fields (e.g. wheel, slip, lane)…"></div>
<div id="grid" class="grid"></div>
<div id="empty" class="empty">Waiting for telemetry… start a race in Forza.</div>
<script>
const grid=document.getElementById('grid');
const empty=document.getElementById('empty');
const filterEl=document.getElementById('filter');
let prev={}, lastTs=null, rateBuf=[];
function fmt(v){
  if(v===null||v===undefined)return '—';
  if(typeof v==='number')return Math.abs(v)>=1000?v.toFixed(0):v.toFixed(4).replace(/\\.?0+$/,'');
  if(typeof v==='boolean')return v?'true':'false';
  return String(v);
}
function tick(d){
  const now=performance.now();
  if(lastTs!==null){rateBuf.push(now-lastTs);if(rateBuf.length>30)rateBuf.shift();}
  lastTs=now;
  const avg=rateBuf.length?(rateBuf.reduce((a,b)=>a+b,0)/rateBuf.length):0;
  document.getElementById('m-rate').textContent=avg?(1000/avg).toFixed(1)+' Hz':'—';
  document.getElementById('m-game').textContent=d._game||'—';
  document.getElementById('m-age').textContent=new Date().toLocaleTimeString();
  const keys=Object.keys(d).filter(k=>k!=='_game'&&k!=='_packet_type').sort();
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
  try{
    const d=await fetch('/debug/raw.json',{cache:'no-store'}).then(r=>r.json());
    tick(d);
  }catch(e){}
}
setInterval(poll,200);
poll();
filterEl.addEventListener('input',()=>tick(prev));
</script>
</body>
</html>
"""
