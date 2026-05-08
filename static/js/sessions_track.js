const TYPE_LABELS={practice:'Practice',time_trial:'Time Trial',qualifying:'Qualifying',race:'Race',race_ai:'Race vs AI',race_online:'Online Race',hot_lap:'Hot Lap',real:'Real Race',ai:'AI Race'};
const CLASS_NAMES={0:'D',1:'C',2:'B',3:'A',4:'S1',5:'S2',6:'X',7:'R',8:'P'};
const GAME_LABELS={'forza_motorsport':'Forza','acc':'ACC','f1':'F1'};
function fmtLap(s){if(!s)return '—';const m=Math.floor(s/60);return m+':'+(s%60).toFixed(3).padStart(6,'0');}
function fmtDt(iso){if(!iso)return '—';return new Date(iso).toLocaleString([],{month:'short',day:'numeric',year:'2-digit',hour:'2-digit',minute:'2-digit'});}
function classBadge(c){if(c==null)return'';const n=CLASS_NAMES[c]||'?';return`<span class="cc-badge cc-${n}">${n}</span>`;}
function gainsBadge(gp,fp){if(gp==null||fp==null||gp===0)return'';const g=gp-fp;if(g===0)return'<span class="gains-badge even">—</span>';return g>0?`<span class="gains-badge pos">+${g}</span>`:`<span class="gains-badge neg">${g}</span>`;}
function spark(times){
  const v=(times||[]).filter(t=>t>0);
  if(v.length<2)return '<span style="color:var(--color-text-dim)">—</span>';
  const mn=Math.min(...v),mx=Math.max(...v),W=80,H=26,p=2;
  const xf=i=>p+i/(v.length-1)*(W-p*2);
  const yf=t=>H-p-(mx===mn?(H-p*2)/2:(t-mn)/(mx-mn)*(H-p*2));
  const pts=v.map((t,i)=>xf(i).toFixed(1)+','+yf(t).toFixed(1)).join(' ');
  const best=Math.min(...v);
  const dots=v.map((t,i)=>Math.abs(t-best)<0.001?`<circle cx="${xf(i).toFixed(1)}" cy="${yf(t).toFixed(1)}" r="2" fill="#22c55e"/>`:``).join('');
  return `<svg width="${W}" height="${H}" style="vertical-align:middle"><polyline points="${pts}" fill="none" stroke="#22c55e66" stroke-width="1.5" stroke-linejoin="round"/>${dots}</svg>`;
}
const _track=new URLSearchParams(location.search).get('name')||'';
const _game=new URLSearchParams(location.search).get('game')||'';
let _sessions=[], _allTracks=[], _typeFilter=null;
// Race-type filter buckets — mirrors the previous accordion groupings so the
// filter chips replace the same conceptual sections users were navigating.
const TYPE_BUCKETS=[
  {key:'race',       label:'Race'},
  {key:'ai',         label:'AI Race'},
  {key:'qualifying', label:'Qualifying / Hotlap'},
  {key:'practice',   label:'Practice / Time Trial'},
];
function filteredSessions(){
  return _sessions.filter(s=>{
    if(_typeFilter!==null && sessGroup(s,_game)!==_typeFilter)return false;
    return true;
  });
}

// ── Game tab setup ────────────────────────────────────────────
(async()=>{
  // Tab game navigation — same track in that game if sessions exist, else game tracks index
  async function gameTabHref(g){
    if(!_track)return'/sessions/game?name='+encodeURIComponent(g);
    try{
      const d=await fetch('/sessions/track/data?name='+encodeURIComponent(_track)+'&game='+encodeURIComponent(g)).then(r=>r.json());
      if(d&&d.length)return'/sessions/track?name='+encodeURIComponent(_track)+'&game='+encodeURIComponent(g);
    }catch(e){}
    return'/sessions/game?name='+encodeURIComponent(g);
  }
  const games=['forza_motorsport','acc','f1'];
  const ids=['tab-forza','tab-acc','tab-f1'];
  games.forEach(async(g,i)=>{document.getElementById(ids[i]).href=await gameTabHref(g);});
  // Active tab
  if(_game){const m={'forza_motorsport':'tab-forza','acc':'tab-acc','f1':'tab-f1'}[_game];if(m)document.getElementById(m).classList.add('active');}
  else document.getElementById('tab-all').classList.add('active');
  // Tab counts
  let gs=[];try{gs=await fetch('/sessions/games').then(r=>r.json());}catch(e){}
  let all=0;gs.forEach(g=>{const n=g.session_count||0;all+=n;
    const m={'forza_motorsport':'cnt-forza','acc':'cnt-acc','f1':'cnt-f1'}[g.game];
    if(m){const el=document.getElementById(m);if(el&&n)el.textContent='('+n+')';}
  });
  const ca=document.getElementById('cnt-all');if(ca&&all)ca.textContent='('+all+')';
})();

async function init(){
  if(!_track){location.href='/sessions';return;}
  document.getElementById('bc-track').textContent=_track;
  document.title='Pacefinder · '+_track;
  const bcGame=document.getElementById('bc-game');
  const bcSep=document.getElementById('bc-sep');
  if(_game&&bcGame){bcGame.textContent=GAME_LABELS[_game]||_game;bcGame.href='/sessions/game?name='+encodeURIComponent(_game);bcGame.style.display='';if(bcSep)bcSep.style.display='';}
  const dataUrl='/sessions/track/data?name='+encodeURIComponent(_track)+(_game?'&game='+encodeURIComponent(_game):'');
  try{_sessions=await fetch(dataUrl).then(r=>r.json());}catch(e){_sessions=[];}
  // Load left rail circuit list
  try{_allTracks=await fetch('/sessions/tracks'+(_game?'?game='+encodeURIComponent(_game):'')).then(r=>r.json());}catch(e){_allTracks=[];}
  renderLeftRail();
  renderHeader();
  renderTypeFilter();
  renderSessionsTable();
  loadTip();
  loadReferences();
}

function renderLeftRail(){
  const items=document.getElementById('lr-items');
  const pills=document.getElementById('lr-pills');
  const known=_allTracks.filter(t=>t.track!=='unknown');
  const unk=_allTracks.filter(t=>t.track==='unknown');
  const sorted=[...known,...unk];
  items.innerHTML=sorted.map(t=>{
    const isUnk=t.track==='unknown';
    const label=isUnk?`Unidentified (${t.session_count})`:t.track;
    const active=t.track===_track;
    const href='/sessions/track?name='+encodeURIComponent(t.track)+(_game?'&game='+encodeURIComponent(_game):'');
    return`<a class="lr-item${active?' active':''}${isUnk?' lr-item-unk':''}" href="${href}">
      <div class="lr-name">${label}</div>
      ${isUnk?'':'<div class="lr-sub">'+t.session_count+' session'+(t.session_count===1?'':'s')+'</div>'}
    </a>`;
  }).join('');
  pills.innerHTML=sorted.map(t=>{
    const isUnk=t.track==='unknown';
    const active=t.track===_track;
    const href='/sessions/track?name='+encodeURIComponent(t.track)+(_game?'&game='+encodeURIComponent(_game):'');
    return`<a class="lr-pill${active?' active':''}${isUnk?' lr-pill-unk':''}" href="${href}">${isUnk?`Unidentified (${t.session_count})`:t.track}</a>`;
  }).join('');
}

function renderTypeFilter(){
  const counts={};
  TYPE_BUCKETS.forEach(b=>counts[b.key]=0);
  _sessions.forEach(s=>{const g=sessGroup(s,_game);if(counts[g]!=null)counts[g]++;});
  const present=TYPE_BUCKETS.filter(b=>counts[b.key]>0);
  const bar=document.getElementById('type-filter');
  if(!bar){return;}  // graceful if the page template hasn't been updated
  if(!present.length){bar.style.display='none';return;}
  bar.style.display='flex';
  const pills=[{label:`ALL (${_sessions.length})`,val:null}]
    .concat(present.map(b=>({label:`${b.label} (${counts[b.key]})`,val:b.key})));
  // Quote string values with single quotes so the inline onclick (already
  // wrapped in double quotes) doesn't break — JSON.stringify here was
  // emitting `setType("race")` inside `onclick="..."`, which the browser
  // parsed as truncated and silently dropped the click.
  bar.innerHTML=pills.map(p=>{
    const arg=p.val===null?'null':"'"+p.val+"'";
    return`<button class="cf-pill${p.val===_typeFilter?' active':''}" onclick="setType(${arg})">${p.label}</button>`;
  }).join('');
}
function setType(t){_typeFilter=t;renderTypeFilter();renderHeader();renderSessionsTable();}
function renderHeader(){
  const fs=filteredSessions();
  document.getElementById('hdr-name').textContent=_track;
  const allBest=fs.map(s=>s.best_lap_time_s).filter(v=>v);
  document.getElementById('hdr-best').textContent=allBest.length?fmtLap(Math.min(...allBest)):'—';
  document.getElementById('hdr-count').textContent=fs.length;
  const last3=fs.slice(0,3).map(s=>s.best_lap_time_s).filter(v=>v);
  let trendHtml='—';
  if(last3.length>=2){const d=last3[0]-last3[1];trendHtml=d<-0.5?'<span style="color:var(--color-green)">▲ Improving</span>':d>0.5?'<span style="color:var(--color-red)">▼ Declining</span>':'<span style="color:var(--color-text-muted)">Stable</span>';}
  document.getElementById('hdr-trend').innerHTML=trendHtml;
}

// ── Session grouping ──────────────────────────────────────────────────────────
function sessGroup(s,game){
  const rt=s.race_type, st=s.session_type;
  if(game==='forza_motorsport'){
    if(rt==='real')return'race';
    if(rt==='ai')return'ai';
    if(rt==='time_trial'||rt==='hot_lap')return'practice';
    if(st==='race')return'race';
    if(st==='qualifying'||st==='hot_lap')return'qualifying';
    return'practice';
  }
  // ACC and F1 — session_type is already normalised
  if(st==='race')return'race';
  if(st==='qualifying'||st==='hot_lap')return'qualifying';
  return'practice';
}

// ── Session table body ────────────────────────────────────────────────────────
function sessTableHtml(sessArr){
  const bests=sessArr.map(s=>s.best_lap_time_s).filter(v=>v);
  const gb=bests.length?Math.min(...bests):null;
  return`<table><thead><tr><th>Date</th><th>Type</th><th>Best Lap</th><th>Laps</th><th>Grid</th><th>Finish</th><th>±</th><th>Class</th></tr></thead><tbody>`
    +sessArr.map((s,i)=>{
      const isGB=gb&&s.best_lap_time_s&&Math.abs(s.best_lap_time_s-gb)<0.001;
      const effType=s.race_type||(s.session_type&&s.session_type!=='unknown'?s.session_type:null);
      const typeHtml=effType?`<span class="type-chip">${TYPE_LABELS[effType]||effType}</span>`:'';
      const gridHtml=s.grid_pos!=null && s.grid_pos>0 ? `P${s.grid_pos}` : '—';
      const posHtml =s.finish_pos!=null ? `P${s.finish_pos}` : '—';
      return`<tr class="clickable" data-idx="${i}"><td class="date-col">${fmtDt(s.started_at)}</td><td>${typeHtml}</td><td class="${isGB?'best-time':''}">${fmtLap(s.best_lap_time_s)}</td><td>${s.lap_count||0}</td><td>${gridHtml}</td><td>${posHtml}</td><td>${gainsBadge(s.grid_pos,s.finish_pos)}</td><td>${classBadge(s.car_class)}</td></tr>`;
    }).join('')
    +'</tbody></table>';
}

// ── Flat sessions table (replaces former race/qualifying/practice/ai
// accordion). Filter chips above (race-type + class) drive the visible rows.
function renderSessionsTable(){
  const fs=filteredSessions();
  const container=document.getElementById('acc-container');
  const empty=document.getElementById('empty');
  if(!fs.length){
    container.innerHTML='';
    empty.style.display='block';
    return;
  }
  empty.style.display='none';
  container.innerHTML=`<div class="acc-tbl">${sessTableHtml(fs)}</div>`;
  // Wire row clicks
  document.querySelectorAll('#acc-container tr.clickable').forEach(tr=>{
    const i=parseInt(tr.dataset.idx);
    tr.addEventListener('click',()=>{
      let u='/sessions/session?id='+encodeURIComponent(fs[i].session_id);
      if(_game)u+='&game='+encodeURIComponent(_game);
      if(_track)u+='&track='+encodeURIComponent(_track);
      location.href=u;
    });
  });
}
async function loadReferences(){
  try{
    const url='/sessions/references?track='+encodeURIComponent(_track)+(_game?'&game='+encodeURIComponent(_game):'');
    const d=await fetch(url).then(r=>r.json());
    if(!d.best_lap&&!d.theoretical)return;
    const card=document.getElementById('ref-card');
    const rows=document.getElementById('ref-rows');
    document.getElementById('ref-card-title').textContent=(_track.toUpperCase()||'TRACK')+' References';
    let html='';
    if(d.best_lap){const bl=d.best_lap;html+=`<div class="ref-row"><span class="ref-row-type">Best Lap</span><span class="ref-row-time green">${fmtLap(bl.lap_time_s)}</span><span class="ref-row-meta">${bl.session_date}&nbsp;&nbsp;Lap ${bl.lap_number != null ? bl.lap_number + 1 : '—'}</span></div>`;}
    if(d.theoretical){const th=d.theoretical;html+=`<div class="ref-row"><span class="ref-row-type">Theoretical</span><span class="ref-row-time">${fmtLap(th.theoretical_best_s)}</span><span class="ref-row-meta"></span></div><div class="ref-sectors">S1 ${th.s1_s!=null?fmtLap(th.s1_s):'—'} ${th.s1_session_date||''} &nbsp;·&nbsp; S2 ${th.s2_s!=null?fmtLap(th.s2_s):'—'} ${th.s2_session_date||''} &nbsp;·&nbsp; S3 ${th.s3_s!=null?fmtLap(th.s3_s):'—'} ${th.s3_session_date||''}</div>`;if(d.best_lap&&d.best_lap.lap_time_s&&th.theoretical_best_s){const gap=d.best_lap.lap_time_s-th.theoretical_best_s;if(gap>0.01){document.getElementById('ref-gap-val').textContent='+'+gap.toFixed(3)+'s';document.getElementById('ref-gap').style.display='flex';}}}
    rows.innerHTML=html;card.classList.add('on');
  }catch(e){}
}
async function loadTip(){
  try{
    const d=await fetch('/sessions/track/tip?name='+encodeURIComponent(_track)).then(r=>r.json());
    document.getElementById('tip-bar').classList.add('on');
    if(d&&d.tip){document.getElementById('tip-text').textContent=d.tip;document.getElementById('tip-btn').style.display='none';}
  }catch(e){}
}
async function generateTip(){
  const btn=document.getElementById('tip-btn');btn.textContent='Generating…';btn.disabled=true;
  try{const d=await fetch('/sessions/track/tip?name='+encodeURIComponent(_track)+'&generate=true').then(r=>r.json());if(d&&d.tip){document.getElementById('tip-text').textContent=d.tip;btn.style.display='none';}else{btn.textContent='Generate AI tip';btn.disabled=false;}}catch(e){btn.textContent='Error — retry';btn.disabled=false;}
}

init();
