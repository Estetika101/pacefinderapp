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
let _sessions=[], _allTracks=[], _classFilter=null;
function filteredSessions(){return _classFilter===null?_sessions:_sessions.filter(s=>s.car_class===_classFilter);}

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
  renderClassFilter();
  renderAccordions();
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

function renderClassFilter(){
  const classes=[...new Set(_sessions.map(s=>s.car_class).filter(c=>c!=null))].sort((a,b)=>b-a);
  const bar=document.getElementById('class-filter');
  if(!classes.length){bar.style.display='none';return;}
  bar.style.display='flex';
  bar.innerHTML=[{label:'ALL',val:null},...classes.map(c=>({label:CLASS_NAMES[c]||String(c),val:c}))].map(p=>`<button class="cf-pill${p.val===_classFilter?' active':''}" onclick="setClass(${p.val===null?'null':p.val})">${p.label}</button>`).join('');
}
function setClass(c){_classFilter=c;renderClassFilter();renderHeader();renderAccordions();}
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

// ── Accordion spark (80×24, amber) ───────────────────────────────────────────
function hdrSpark(sessChron){
  const v=sessChron.map(s=>s.best_lap_time_s).filter(t=>t>0);
  if(!v.length)return'';
  if(v.length===1)return`<svg width="80" height="24" style="vertical-align:middle"><circle class="sp-dot" cx="40" cy="12" r="2.5" fill="#f59e0b" data-t="${v[0].toFixed(3)}"/></svg>`;
  const mn=Math.min(...v),mx=Math.max(...v),W=80,H=24,p=2;
  const xf=i=>p+i/(v.length-1)*(W-p*2);
  const yf=t=>H-p-(mx===mn?(H-p*2)/2:(t-mn)/(mx-mn)*(H-p*2));
  const pts=v.map((t,i)=>xf(i).toFixed(1)+','+yf(t).toFixed(1)).join(' ');
  const dots=v.map((t,i)=>`<circle class="sp-dot" cx="${xf(i).toFixed(1)}" cy="${yf(t).toFixed(1)}" r="2.5" fill="#f59e0b" data-t="${t.toFixed(3)}"/>`).join('');
  return`<svg width="80" height="24" style="vertical-align:middle;overflow:visible"><polyline points="${pts}" fill="none" stroke="#f59e0b55" stroke-width="1.5" stroke-linejoin="round"/>${dots}</svg>`;
}
function trendArrow(sessChron){
  const v=sessChron.map(s=>s.best_lap_time_s).filter(t=>t>0);
  if(v.length<2)return'<span style="color:var(--color-text-dim)">—</span>';
  const d=v[v.length-1]-v[v.length-2];
  if(d<-0.5)return'<span style="color:var(--color-green)">↑</span>';
  if(d>0.5)return'<span style="color:var(--color-red)">↓</span>';
  return'<span style="color:var(--color-text-muted)">→</span>';
}

// ── sessionStorage open/close state ─────────────────────────────────────────
const _skey='acc_'+_track+'_'+_game;
function _loadAccState(){try{return JSON.parse(sessionStorage.getItem(_skey)||'null');}catch(e){return null;}}
function _saveAccState(st){try{sessionStorage.setItem(_skey,JSON.stringify(st));}catch(e){}}

// ── Session table body ────────────────────────────────────────────────────────
function sessTableHtml(sessArr){
  const bests=sessArr.map(s=>s.best_lap_time_s).filter(v=>v);
  const gb=bests.length?Math.min(...bests):null;
  return`<table><thead><tr><th>Date</th><th>Type</th><th>Best Lap</th><th>Laps</th><th>Pos</th><th>±</th><th>Class</th></tr></thead><tbody>`
    +sessArr.map((s,i)=>{
      const isGB=gb&&s.best_lap_time_s&&Math.abs(s.best_lap_time_s-gb)<0.001;
      const effType=s.race_type||(s.session_type&&s.session_type!=='unknown'?s.session_type:null);
      const typeHtml=effType?`<span class="type-chip">${TYPE_LABELS[effType]||effType}</span>`:'';
      const posHtml=s.finish_pos!=null?`P${s.finish_pos}`:'—';
      return`<tr class="clickable" data-idx="${i}"><td class="date-col">${fmtDt(s.started_at)}</td><td>${typeHtml}</td><td class="${isGB?'best-time':''}">${fmtLap(s.best_lap_time_s)}</td><td>${s.lap_count||0}</td><td>${posHtml}</td><td>${gainsBadge(s.grid_pos,s.finish_pos)}</td><td>${classBadge(s.car_class)}</td></tr>`;
    }).join('')
    +'</tbody></table>';
}

// ── Render accordions ─────────────────────────────────────────────────────────
const ACC_DEFS=[
  {key:'race',    label:'Race'},
  {key:'qualifying',label:'Qualifying / Hotlap'},
  {key:'practice',label:'Practice / Time Trial'},
  {key:'ai',      label:'AI Race',muted:true},
];
const _urlSection=new URLSearchParams(location.search).get('section')||null;

function renderAccordions(){
  const fs=filteredSessions();
  const container=document.getElementById('acc-container');
  const empty=document.getElementById('empty');

  // Group sessions (sessions come newest-first; reverse for chronological spark)
  const groups={};
  ACC_DEFS.forEach(d=>groups[d.key]=[]);
  fs.forEach(s=>groups[sessGroup(s,_game)].push(s));

  const nonEmpty=ACC_DEFS.filter(d=>groups[d.key].length);
  if(!nonEmpty.length){container.innerHTML='';empty.style.display='block';return;}
  empty.style.display='none';

  // Determine which section should be open
  const saved=_loadAccState();
  const defaultOpen=_urlSection||'race';

  container.innerHTML=nonEmpty.map(def=>{
    const key=def.key;
    const arr=groups[key]; // newest-first
    const chron=[...arr].reverse(); // chronological for spark/trend
    const bestAll=arr.map(s=>s.best_lap_time_s).filter(v=>v);
    const bestLap=bestAll.length?Math.min(...bestAll):null;
    const count=arr.length;
    const isOpen=saved?!!saved[key]:(key===defaultOpen);
    return`<div class="acc-section">
      <button class="acc-hdr${isOpen?' open':''}${def.muted?' muted':''}" id="acc-hdr-${key}" onclick="toggleAcc('${key}')">
        <span class="acc-arrow">&#9654;</span>
        <span class="acc-label">${def.label}</span>
        <span class="acc-count">${count} session${count===1?'':'s'}</span>
        <span class="acc-best">${bestLap?'Best: '+fmtLap(bestLap):''}</span>
        <span class="acc-spark">${hdrSpark(chron)}</span>
        <span class="acc-trend">${trendArrow(chron)}</span>
      </button>
      <div class="acc-body${isOpen?' open':''}" id="acc-body-${key}">
        <div class="acc-tbl" id="acc-tbl-${key}">${sessTableHtml(arr)}</div>
      </div>
    </div>`;
  }).join('');

  // Wire row clicks for each group
  nonEmpty.forEach(def=>{
    const arr=groups[def.key];
    document.querySelectorAll(`#acc-tbl-${def.key} tr.clickable`).forEach(tr=>{
      const i=parseInt(tr.dataset.idx);
      tr.addEventListener('click',()=>{
        let u='/sessions/session?id='+encodeURIComponent(arr[i].session_id);
        if(_game)u+='&game='+encodeURIComponent(_game);
        if(_track)u+='&track='+encodeURIComponent(_track);
        location.href=u;
      });
    });
  });

  // Wire spark dot tooltips
  const tip=document.getElementById('sp-tip');
  document.querySelectorAll('#acc-container .sp-dot').forEach(dot=>{
    dot.addEventListener('mouseenter',e=>{
      tip.textContent=fmtLap(parseFloat(dot.dataset.t));
      tip.style.display='block';
      tip.style.left=(e.clientX+12)+'px';
      tip.style.top=(e.clientY-24)+'px';
    });
    dot.addEventListener('mousemove',e=>{
      tip.style.left=(e.clientX+12)+'px';
      tip.style.top=(e.clientY-24)+'px';
    });
    dot.addEventListener('mouseleave',()=>{tip.style.display='none';});
  });
}

function toggleAcc(key){
  const hdr=document.getElementById('acc-hdr-'+key);
  const body=document.getElementById('acc-body-'+key);
  if(!hdr||!body)return;
  const opening=!hdr.classList.contains('open');
  hdr.classList.toggle('open',opening);
  body.classList.toggle('open',opening);
  // Persist
  const saved=_loadAccState()||{};
  saved[key]=opening;
  _saveAccState(saved);
  // Update URL section param without reload
  const url=new URL(location.href);
  if(opening)url.searchParams.set('section',key);
  else url.searchParams.delete('section');
  history.replaceState({},'',url);
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
    if(d.best_lap){const bl=d.best_lap;html+=`<div class="ref-row"><span class="ref-row-type">Best Lap</span><span class="ref-row-time green">${fmtLap(bl.lap_time_s)}</span><span class="ref-row-meta">${bl.session_date}&nbsp;&nbsp;Lap ${bl.lap_number}</span></div>`;}
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

// ── Track Telemetry Tab ───────────────────────────────────────
const _initTrackTab=new URLSearchParams(location.search).get('tab')||'overview';
let _teleInited=false,_teleSessData={},_teleLapSamples=null,_teleRefSamples=null;
let _teleSelSessId=null,_teleSelLapN=null,_teleSelRef='best';

function switchTrackTab(tab){
  document.getElementById('trk-overview').style.display=tab==='overview'?'':'none';
  document.getElementById('trk-telemetry').style.display=tab==='telemetry'?'':'none';
  document.getElementById('trk-tab-overview').classList.toggle('active',tab==='overview');
  document.getElementById('trk-tab-telemetry').classList.toggle('active',tab==='telemetry');
  const url=new URL(location.href);url.searchParams.set('tab',tab);history.replaceState({},'',url);
  if(tab==='telemetry'&&!_teleInited){_teleInited=true;initTelemetry();}
}

async function initTelemetry(){
  document.getElementById('tele-msg').textContent='Loading sessions…';
  // Build session selector from _sessions (already loaded)
  const sel=document.getElementById('tele-sess-sel');
  sel.innerHTML=_sessions.map(s=>`<option value="${s.session_id}">${fmtDt(s.started_at)} — ${fmtLap(s.best_lap_time_s)}</option>`).join('');
  if(!_sessions.length){document.getElementById('tele-msg').textContent='No sessions at this track.';return;}
  // Default to best-lap session
  const allWithLap=_sessions.filter(s=>s.best_lap_time_s);
  if(!allWithLap.length){document.getElementById('tele-msg').textContent='No lap data available.';return;}
  const bestSess=allWithLap.reduce((a,b)=>a.best_lap_time_s<b.best_lap_time_s?a:b);
  _teleSelSessId=bestSess.session_id;
  sel.value=_teleSelSessId;
  await loadTeleSessData(_teleSelSessId,true);
}

async function loadTeleSessData(sessId,selectBestLap){
  document.getElementById('tele-msg').textContent='Loading…';
  document.getElementById('tele-cmp-wrap').style.display='none';
  try{
    if(!_teleSessData[sessId]){
      const d=await fetch('/sessions/session/data?id='+encodeURIComponent(sessId)).then(r=>r.json());
      _teleSessData[sessId]=d;
    }
    const d=_teleSessData[sessId];
    const laps=(d.laps||[]).filter(l=>l.lap_number>0&&l.lap_time_s&&l.samples&&l.samples.length);
    // Populate lap selector
    const lapSel=document.getElementById('tele-lap-sel');
    lapSel.innerHTML=laps.map(l=>`<option value="${l.lap_number}">Lap ${l.lap_number} — ${fmtLap(l.lap_time_s)}</option>`).join('');
    if(!laps.length){document.getElementById('tele-msg').textContent='No telemetry laps in this session.';return;}
    if(selectBestLap){
      const bestLap=laps.reduce((a,b)=>a.lap_time_s<b.lap_time_s?a:b);
      _teleSelLapN=bestLap.lap_number;
      lapSel.value=_teleSelLapN;
    }
    // Populate ref selector
    buildTeleRefSel(d,laps);
    await renderTeleCharts();
  }catch(e){document.getElementById('tele-msg').textContent='Error loading telemetry.';}
}

function buildTeleRefSel(sessData,laps){
  const refSel=document.getElementById('tele-ref-sel');
  const opts=[{val:'none',label:'None'}];
  // Other sessions at this track
  _sessions.filter(s=>s.session_id!==_teleSelSessId&&s.best_lap_time_s).forEach(s=>{
    opts.push({val:'sess:'+s.session_id,label:'Best: '+fmtDt(s.started_at)+' '+fmtLap(s.best_lap_time_s)});
  });
  refSel.innerHTML=opts.map(o=>`<option value="${o.val}">${o.label}</option>`).join('');
  if(_teleSelRef&&refSel.querySelector(`[value="${_teleSelRef}"]`)){refSel.value=_teleSelRef;}
  else{refSel.value='none';_teleSelRef='none';}
}

function tInterp(samples,norm,field){
  if(!samples||!samples.length)return 0;
  let lo=0,hi=samples.length-1;
  while(lo<hi-1){const mid=(lo+hi)>>1;if(samples[mid].distance_norm<=norm)lo=mid;else hi=mid;}
  const a=samples[lo],b=samples[hi];
  const dn=b.distance_norm-a.distance_norm;
  if(dn<1e-9)return a[field]??0;
  const f=(norm-a.distance_norm)/dn;
  return (a[field]??0)+f*((b[field]??0)-(a[field]??0));
}

function tSvgPath(samples,field,W,H,mn,mx){
  const yr=mx-mn||1;
  return'M'+samples.map(s=>{
    const x=(s.distance_norm*W).toFixed(1);
    const y=(H-((s[field]??mn)-mn)/yr*H).toFixed(1);
    return x+','+y;
  }).join('L');
}

async function onTeleSessChange(){
  _teleSelSessId=document.getElementById('tele-sess-sel').value;
  await loadTeleSessData(_teleSelSessId,true);
}
async function onTeleLapChange(){
  _teleSelLapN=parseInt(document.getElementById('tele-lap-sel').value);
  await renderTeleCharts();
}
async function onTeleRefChange(){
  _teleSelRef=document.getElementById('tele-ref-sel').value;
  await renderTeleCharts();
}

async function renderTeleCharts(){
  const d=_teleSessData[_teleSelSessId];
  if(!d)return;
  const laps=(d.laps||[]);
  const lap=laps.find(l=>l.lap_number===_teleSelLapN);
  if(!lap||!lap.samples||!lap.samples.length){document.getElementById('tele-msg').textContent='No sample data for this lap.';document.getElementById('tele-cmp-wrap').style.display='none';return;}
  const lapS=lap.samples;
  let refS=null;
  const refVal=_teleSelRef;
  if(refVal&&refVal!=='none'&&refVal.startsWith('sess:')){
    const refSessId=refVal.slice(5);
    try{
      if(!_teleSessData[refSessId]){
        const rd=await fetch('/sessions/session/data?id='+encodeURIComponent(refSessId)).then(r=>r.json());
        _teleSessData[refSessId]=rd;
      }
      const rd=_teleSessData[refSessId];
      const rLaps=(rd.laps||[]).filter(l=>l.lap_number>0&&l.lap_time_s&&l.samples&&l.samples.length);
      if(rLaps.length){const best=rLaps.reduce((a,b)=>a.lap_time_s<b.lap_time_s?a:b);refS=best.samples;}
    }catch(e){}
  }
  const W=1000;
  const tracks=[
    {label:'Speed',field:'speed_ms',color:'rgba(96,165,250,.8)',refColor:'rgba(96,165,250,.35)',H:80},
    {label:'Throttle',field:'throttle',color:'rgba(34,197,94,.8)',refColor:'rgba(34,197,94,.35)',H:60},
    {label:'Brake',field:'brake',color:'rgba(248,113,113,.8)',refColor:'rgba(248,113,113,.35)',H:60},
    {label:'Slip RL',field:'slip_rl',color:'rgba(251,191,36,.8)',refColor:'rgba(251,191,36,.35)',H:50},
  ];
  let html='';
  for(const tr of tracks){
    const vals=lapS.map(s=>s[tr.field]??0);
    const mn=Math.min(...vals),mx=Math.max(...vals);
    const padMn=mn-(mx-mn)*0.05,padMx=mx+(mx-mn)*0.05||mx+1;
    const path=tSvgPath(lapS,tr.field,W,tr.H,padMn,padMx);
    let refPath='';
    if(refS){
      const rVals=refS.map(s=>s[tr.field]??0);
      const rMn=Math.min(mn,...rVals),rMx=Math.max(padMx,...rVals);
      refPath=`<path d="${tSvgPath(refS,tr.field,W,tr.H,rMn,rMx)}" fill="none" stroke="${tr.refColor}" stroke-width="1.5" stroke-linejoin="round"/>`;
    }
    html+=`<div class="chart-row" style="margin-bottom:8px">
      <div style="font-size:.6rem;color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:2px">${tr.label}</div>
      <svg viewBox="0 0 ${W} ${tr.H}" style="width:100%;display:block;overflow:visible">
        ${refPath}
        <path d="${path}" fill="none" stroke="${tr.color}" stroke-width="2" stroke-linejoin="round"/>
      </svg>
    </div>`;
  }
  document.getElementById('tele-charts-inner').innerHTML=html;
  document.getElementById('tele-msg').style.display='none';
  document.getElementById('tele-cmp-wrap').style.display='';
}

init().then(()=>{
  if(_initTrackTab==='telemetry')switchTrackTab('telemetry');
});
