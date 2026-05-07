const GAME_LABELS={'forza_motorsport':'Forza','acc':'ACC','f1':'F1'};
const CLASS_NAMES={0:'D',1:'C',2:'B',3:'A',4:'S1',5:'S2',6:'X',7:'R',8:'P'};
function fmtLap(s){if(!s)return '—';const m=Math.floor(s/60);return m+':'+(s%60).toFixed(3).padStart(6,'0');}
function fmtDate(iso){if(!iso)return '—';return new Date(iso).toLocaleDateString([],{month:'short',day:'numeric',year:'numeric'});}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function classBadge(cls){if(cls==null)return'';const n=CLASS_NAMES[cls]||'?';return`<span class="cc cc-${n}">${n}</span>`;}
function sparkSVG(vals){
  const v=(vals||[]).filter(t=>t>0);
  if(!v.length)return'';
  const W=180,H=36,p=3;
  const mn=Math.min(...v),mx=Math.max(...v),rng=mx-mn||0.001;
  if(v.length===1){
    return`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
      <circle cx="${W/2}" cy="${H/2}" r="3" fill="var(--color-accent)" opacity=".9"/>
    </svg>`;
  }
  const xs=v.map((_,i)=>p+(W-p*2)*i/(v.length-1));
  const ys=v.map(t=>H-p-(H-p*2)*(mx-t)/rng);
  const pts=xs.map((x,i)=>x.toFixed(1)+','+ys[i].toFixed(1)).join(' ');
  const fillPts=`${xs[0].toFixed(1)},${H} ${pts} ${xs[xs.length-1].toFixed(1)},${H}`;
  return`<svg width="100%" height="${H}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    <defs><linearGradient id="sg${Math.random().toString(36).slice(2)}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="var(--color-accent)" stop-opacity=".2"/>
      <stop offset="100%" stop-color="var(--color-accent)" stop-opacity="0"/>
    </linearGradient></defs>
    <polyline points="${pts}" fill="none" stroke="var(--color-accent)" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" opacity=".85"/>
  </svg>`;
}
// Forza is the only active game; ACC + F1 are parked. See docs/specs/park-acc-f1.md.
const _game=new URLSearchParams(location.search).get('name')||'forza_motorsport';

// ── Game Overview (only when ?name= is set) ───────────────────
// _gfType is fixed to 'all' since the Real/AI filter was removed (Bundle 4).
// _gfLast defaults to 5 — user prefers a tight window for "current form".
const _gfType='all';
let _gfLast=5,_gfFormData=[];

function gSetKV(id,val){const el=document.getElementById(id);if(!el)return;if(val==null||val==='—'){el.textContent='—';el.classList.add('dash');}else{el.textContent=val;el.classList.remove('dash');}}
function p1(v,d=1){return v==null?null:parseFloat(v.toFixed(d));}
function posToPercentile(fp){if(fp==null)return null;return Math.max(5,Math.min(100,Math.round(100-(fp-1)*6)));}

async function loadGameOverview(){
  document.getElementById('game-overview').style.display='';
  // KPIs
  let k={};
  try{k=await fetch('/sessions/career?game='+encodeURIComponent(_game)).then(r=>r.json());}catch(e){}
  const t=k.total_sessions||0,rc=k.real_count||0,ai=k.ai_count||0;
  gSetKV('gkv-total',t||'0');
  document.getElementById('gks-total').textContent=t?(rc+' real · '+ai+' AI'):'';
  gSetKV('gkv-finish',k.avg_finish_real!=null?'P'+p1(k.avg_finish_real):null);
  gSetKV('gkv-gained',k.avg_pos_gained!=null?(k.avg_pos_gained>=0?'+':'')+p1(k.avg_pos_gained):null);
  // Color by sign: green = positions gained on average, red = lost.
  const pgEl=document.getElementById('gkv-gained');
  if(pgEl){pgEl.classList.toggle('green', k.avg_pos_gained>0); pgEl.classList.toggle('red', k.avg_pos_gained<0);}
  gSetKV('gkv-win',k.win_rate!=null?p1(k.win_rate,0)+'%':null);
  gSetKV('gkv-podium',k.podium_rate!=null?p1(k.podium_rate,0)+'%':null);
  gSetKV('gkv-best',fmtLap(k.best_lap_time_s)||'—');
  gSetKV('gkv-laps',k.total_laps||'0');
  document.getElementById('gks-circuits').textContent=(k.circuit_count||0)+' circuits';
  // Form + Trend
  await loadGameForm();
  // Recent
  let recent=[];
  try{recent=await fetch('/sessions/recent?game='+encodeURIComponent(_game)+'&limit=5').then(r=>r.json());}catch(e){}
  renderGameRecent(recent);
}

async function loadGameForm(){
  try{_gfFormData=await fetch('/sessions/form?type='+_gfType+'&last=50&game='+encodeURIComponent(_game)).then(r=>r.json());}catch(e){_gfFormData=[];}
  renderGameForm();
}

function renderGameForm(){
  const sliced=_gfFormData.slice(-_gfLast);
  const el=document.getElementById('gf-chart');
  if(!sliced.length){el.innerHTML='<span style="font-size:var(--text-xs);color:var(--color-text-muted)">No race data</span>';
    document.getElementById('gf-trend').textContent='';document.getElementById('gf-pct').textContent='';document.getElementById('gf-note').textContent='';return;}
  el.innerHTML=sliced.map(s=>{
    const pct=posToPercentile(s.finish_pos);
    const h=pct!=null?Math.round(pct+20):0;
    const col=pct!=null?`hsl(${h},70%,38%)`:'#1a1a1a';
    // Hover card mirrors a Recent Sessions row — track, date, finish vs grid,
    // delta. Per Bundle 4 of the UX review.
    const date=fmtDate(s.started_at);
    const fp=s.finish_pos, gp=s.grid_pos;
    const posLine=fp!=null?(gp!=null&&gp>0?`P${gp} → P${fp}`:`P${fp}`):'(no pos)';
    let gainedLine='';
    if(fp!=null && gp!=null && gp>0){
      const g=gp-fp;
      const cls=g>0?'pos':g<0?'neg':'neu';
      gainedLine=`<span class="bar-tip-gained ${cls}">${g>0?'+':''}${g}</span>`;
    }
    const tipHtml=`<div class="bar-tip-track">${esc(s.track||'?')}</div><div class="bar-tip-meta">${date}</div><div class="bar-tip-pos">${posLine} ${gainedLine}</div>`;
    return`<div class="bar" style="height:${pct!=null?pct:20}%;background:${col}"><div class="bar-tip">${tipHtml}</div></div>`;
  }).join('');
  // meta
  const withPos=sliced.filter(s=>s.finish_pos!=null);
  const trend=document.getElementById('gf-trend');
  if(!withPos.length){trend.textContent='';document.getElementById('gf-pct').textContent='';document.getElementById('gf-note').textContent='';return;}
  const pcts=withPos.map(s=>posToPercentile(s.finish_pos));
  const avg=pcts.reduce((a,b)=>a+b,0)/pcts.length;
  const half=Math.floor(pcts.length/2);
  const diff=(pcts.slice(half).reduce((a,b)=>a+b,0)/((pcts.length-half)||1))-(pcts.slice(0,half).reduce((a,b)=>a+b,0)/(half||1));
  if(diff>4){trend.textContent='▲ Improving';trend.className='ov-form-trend up';}
  else if(diff<-4){trend.textContent='▼ Declining';trend.className='ov-form-trend dn';}
  else{trend.textContent='— Steady';trend.className='ov-form-trend fl';}
  document.getElementById('gf-pct').textContent='Top '+Math.round(100-avg)+'% avg finish';
  document.getElementById('gf-note').textContent=withPos.length+' sessions with position data';
}

function renderGameRecent(sessions){
  const el=document.getElementById('gf-recent');
  if(!sessions.length){el.innerHTML='<div style="color:var(--color-text-muted);font-size:var(--text-xs);padding:10px 0">No sessions yet</div>';return;}
  // Horizontal cards per Bundle 4 of the UX review. Each card is
  // self-contained (no horizontal alignment with neighbors needed) so the
  // user can scan them at a glance.
  el.innerHTML=`<div class="ov-recent-cards">${sessions.map(s=>{
    const fp=s.finish_pos,gp=s.grid_pos;
    const posCls=fp==null?'':(fp===1?'p1':fp<=3?'podium':'ok');
    const posHtml=fp!=null?`<span class="ov-recent-pos ${posCls}">P${fp}</span>`:'<span class="ov-recent-pos none">—</span>';
    let gainedHtml='';
    if(fp!=null && gp!=null && gp>0){
      const g=gp-fp;
      const cls=g>0?'pos':g<0?'neg':'neu';
      gainedHtml=`<div class="rc-gained ${cls}">${g>0?'+':''}${g} pos</div>`;
    }
    const gridHtml=(gp!=null&&gp>0)?`<span class="rc-grid">from P${gp}</span>`:'';
    const lap=s.best_lap_time_s?fmtLap(s.best_lap_time_s):'—';
    const href='/sessions/session?id='+encodeURIComponent(s.session_id)+'&game='+encodeURIComponent(s.game||'')+'&track='+encodeURIComponent(s.track||'');
    return`<div class="rc" onclick="location.href='${href}'">
      <div class="rc-date">${fmtDate(s.started_at)}</div>
      <div class="rc-track">${s.track&&s.track!=='unknown'?esc(s.track):'Unknown Track'}</div>
      <div class="rc-pos-row">${posHtml}${gridHtml}</div>
      ${gainedHtml}
      <div class="rc-lap">${lap}</div>
    </div>`;
  }).join('')}</div>`;
}

// AI/Real type filter removed in Bundle 4 — Form chart always shows all races.
document.getElementById('gf-last').addEventListener('click',e=>{
  const b=e.target.closest('.ftog');if(!b)return;
  document.querySelectorAll('#gf-last .ftog').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');_gfLast=+b.dataset.val;renderGameForm();
});

let _tracks=[];
async function init(){
  const label=GAME_LABELS[_game]||_game||'All';
  document.getElementById('page-title').textContent=label?label+' Circuits':'All Circuits';
  document.title='Pacefinder · '+(label||'Sessions');
  const url='/sessions/tracks'+(_game?'?game='+encodeURIComponent(_game):'');
  if(_game) loadGameOverview();
  try{_tracks=await fetch(url).then(r=>r.json());}catch(e){_tracks=[];}
  document.getElementById('count').textContent=_tracks.length+' circuit'+(_tracks.length!==1?'s':'');
  const withLap=_tracks.filter(t=>t.best_lap_time_s&&t.track!=='unknown');
  const noLap=_tracks.filter(t=>!t.best_lap_time_s&&t.track!=='unknown');
  const unk=_tracks.filter(t=>t.track==='unknown');
  // Main track list
  const list=document.getElementById('list');
  if(!_tracks.length){list.innerHTML='<div class="empty-state">No sessions recorded yet</div>';return;}
  list.innerHTML=[...withLap,...noLap,...unk].map((t,i)=>{
    const label=t.track==='unknown'?'Unknown Track':esc(t.track);
    const hasLap=!!t.best_lap_time_s;
    const badge=classBadge(t.best_car_class);
    const carLabel=t.best_car&&t.best_car!=='unknown'?esc(t.best_car):'';
    const metaParts=[];
    if(t.session_count)metaParts.push(t.session_count+(t.session_count===1?' session':' sessions'));
    if(t.last_raced)metaParts.push(fmtDate(t.last_raced));
    const meta=metaParts.join(' · ');
    const carMeta=(badge||carLabel)?`<span style="display:block;margin-top:2px">${badge}${carLabel}</span>`:'';
    const spark=hasLap?sparkSVG(t.spark_laps||[]):'';
    const trendArrow=hasLap?(t.trend==='up'?'<span class="tl-arrow" style="color:var(--color-green)">▲</span>':t.trend==='dn'?'<span class="tl-arrow" style="color:var(--color-red)">▼</span>':'<span class="tl-arrow" style="color:var(--color-text-dim)">—</span>'):'';
    const bestLap=hasLap?fmtLap(t.best_lap_time_s):'—';
    let avgFinish='';
    if(t.avg_finish!=null){
      let gainedStr='';
      if(t.avg_gained!=null){
        const g=t.avg_gained, cls=g>0?'pos':g<-0?'neg':'neu';
        gainedStr=` <span class="recent-gained ${cls}">${g>=0?'+':''}${g.toFixed(1)}</span>`;
      }
      avgFinish=`<div class="tl-finish">P${t.avg_finish} avg${gainedStr}</div>`;
    }
    const href=`/sessions/track?name=${encodeURIComponent(t.track)}${_game?'&game='+encodeURIComponent(_game):''}`;
    return`<div class="tl-row${hasLap?'':' no-lap'}" onclick="location.href='${href}'">
      <div class="tl-left">
        <div class="tl-name">${label}</div>
        <div class="tl-meta">${meta}${carMeta}</div>
      </div>
      <div class="tl-center">
        <div class="tl-spark">${spark}</div>
        ${trendArrow}
      </div>
      <div class="tl-right">
        <div class="tl-best">${bestLap}</div>
        ${avgFinish}
      </div>
    </div>`;
  }).join('');
}
init();
