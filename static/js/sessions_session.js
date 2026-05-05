const TYPE_LABELS={practice:'Practice',time_trial:'Time Trial',qualifying:'Qualifying',race:'Race',race_ai:'Race vs AI',race_online:'Online Race',hot_lap:'Hot Lap'};
function fmtLap(s){if(!s)return '—';const m=Math.floor(s/60);return m+':'+(s%60).toFixed(3).padStart(6,'0');}
function fmtDt(iso){if(!iso)return '—';return new Date(iso).toLocaleString([],{weekday:'short',month:'short',day:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit'});}
function scls(v){return v>0.25?'crit':v>0.12?'warn':'';}
const _qs=new URLSearchParams(location.search);
const _id=_qs.get('id')||'';
const _sgame=_qs.get('game')||'';
const _strack=_qs.get('track')||'';
const _initTab=_qs.get('tab')||'overview';
const SGAME_LABELS={'forza_motorsport':'Forza','acc':'ACC','f1':'F1'};
let _sess=null,_laps=[],_allTracks=[];

// ── Tab switching ─────────────────────────────────────────────
let _teleInited=false;
function switchTab(tab){
  document.getElementById('tab-overview').style.display=tab==='overview'?'':'none';
  document.getElementById('tab-telemetry').style.display=tab==='telemetry'?'':'none';
  document.getElementById('st-overview').classList.toggle('active',tab==='overview');
  document.getElementById('st-telemetry').classList.toggle('active',tab==='telemetry');
  const url=new URL(location.href);url.searchParams.set('tab',tab);history.replaceState({},'',url);
  if(tab==='telemetry'&&!_teleInited){
    _teleInited=true;
    const game=_sgame||(_sess&&_sess.game)||'';
    const track=_strack||(_sess&&_sess.track)||'';
    let src='/sessions/telemetry?embed=1&id='+encodeURIComponent(_id);
    if(game)src+='&game='+encodeURIComponent(game);
    if(track)src+='&track='+encodeURIComponent(track);
    document.getElementById('tele-frame').src=src;
  }
}

async function init(){
  if(!_id){location.href='/sessions';return;}
  let d;
  try{d=await fetch('/sessions/session/data?id='+encodeURIComponent(_id)).then(r=>r.json());}
  catch(e){document.getElementById('hdr-track').textContent='Session not found';return;}
  _sess=d.session;_laps=d.laps||[];
  // Load left rail circuit list
  const game=_sgame||_sess.game||'';
  try{_allTracks=await fetch('/sessions/tracks'+(game?'?game='+encodeURIComponent(game):'')).then(r=>r.json());}catch(e){_allTracks=[];}
  renderHeader();
  renderLeftRail();
  renderLaps();
  renderAI();
  switchTab(_initTab);
}

function renderLeftRail(){
  const s=_sess;
  const game=_sgame||s.game||'';
  const trackName=s.track&&s.track!=='unknown'?s.track:(_strack||'');
  const items=document.getElementById('lr-items');
  const pills=document.getElementById('lr-pills');
  items.innerHTML=_allTracks.map(t=>{
    const active=t.track===trackName;
    const href='/sessions/track?name='+encodeURIComponent(t.track)+(game?'&game='+encodeURIComponent(game):'');
    return`<a class="lr-item${active?' active':''}" href="${href}">
      <div class="lr-name">${t.track==='unknown'?'Unknown':t.track}</div>
      <div class="lr-sub">${t.session_count} session${t.session_count===1?'':'s'}</div>
    </a>`;
  }).join('');
  pills.innerHTML=_allTracks.map(t=>{
    const active=t.track===trackName;
    const href='/sessions/track?name='+encodeURIComponent(t.track)+(game?'&game='+encodeURIComponent(game):'');
    return`<a class="lr-pill${active?' active':''}" href="${href}">${t.track==='unknown'?'Unknown':t.track}</a>`;
  }).join('');
  // THIS SESSION block
  const carName=s.car&&s.car!=='unknown'?s.car:null;
  const cls=s.car_class!=null?CLASS_NAMES[s.car_class]:null;
  const pi=s.car_pi;
  const effType=s.race_type||(s.session_type&&s.session_type!=='unknown'?s.session_type:null);
  const thisBlock=document.getElementById('lr-this');
  const carEl=document.getElementById('lr-car');
  const badgesEl=document.getElementById('lr-badges');
  if(carName||cls||pi||effType){
    thisBlock.style.display='';
    carEl.textContent=carName||'Unknown Car';
    let badges='';
    if(cls)badges+=`<span class="cc cc-${cls}">${cls}</span>`;
    if(pi)badges+=`<span style="font-size:.6rem;color:var(--color-text-muted)">PI ${pi}</span>`;
    if(effType)badges+=`<span class="type-chip" style="font-size:.55rem">${TYPE_LABELS[effType]||effType}</span>`;
    badgesEl.innerHTML=badges;
  }
}

function renderHeader(){
  const s=_sess;
  const track=s.track&&s.track!=='unknown'?s.track:(_strack||'Unknown Track');
  const game=_sgame||s.game||'';
  document.title='Pacefinder · '+track;
  if(game){
    const bg=document.getElementById('bc-game');
    bg.textContent=SGAME_LABELS[game]||game;
    bg.href='/sessions/game?name='+encodeURIComponent(game);
    bg.style.display='';
    document.getElementById('bc-game-sep').style.display='';
  }
  let trackHref='/sessions/track?name='+encodeURIComponent(track);
  if(game)trackHref+='&game='+encodeURIComponent(game);
  document.getElementById('bc-track').textContent=track;
  document.getElementById('bc-track').href=trackHref;
  document.getElementById('bc-sess').textContent=fmtDt(s.started_at);
  document.getElementById('hdr-track').textContent=track;
  document.getElementById('hdr-sub').textContent=(s.game||'').replace(/_/g,' ')+' · '+fmtDt(s.started_at);
  document.getElementById('hdr-best').textContent=fmtLap(s.best_lap_time_s);
  document.getElementById('hdr-laps').textContent=_laps.length;
  const effType=s.race_type||(s.session_type&&s.session_type!=='unknown'?s.session_type:null);
  if(effType){const el=document.getElementById('hdr-type');el.textContent=TYPE_LABELS[effType]||effType;el.style.display='';}
}
function renderLaps(){
  const best=_sess.best_lap_time_s;
  const validTimes=_laps.filter(l=>l.lap_number>0&&l.lap_time_s).map(l=>l.lap_time_s);
  validTimes.sort((a,b)=>a-b);
  const median=validTimes.length?validTimes[Math.floor(validTimes.length/2)]:null;
  document.getElementById('lap-tbody').innerHTML=_laps.map(l=>{
    const isOut=l.lap_number===0;
    const isSlow=!isOut&&median&&l.lap_time_s&&l.lap_time_s>median*1.4;
    const isB=!isOut&&best&&l.lap_time_s&&Math.abs(l.lap_time_s-best)<0.001;
    const rowCls=[isB?'best-row':'',isSlow?'outlier-row':''].filter(Boolean).join(' ');
    const lapNumHtml=isOut?`<span class="out-lap-lbl">OUT LAP</span>`:l.lap_number;
    const timeHtml=isOut?`<span class="out-lap-time">${fmtLap(l.lap_time_s)}</span>`:(isSlow?`<span class="outlier-time">${fmtLap(l.lap_time_s)}</span>`:fmtLap(l.lap_time_s));
    return `<tr class="${rowCls}">
      <td>${lapNumHtml}</td>
      <td>${timeHtml}</td>
      <td>${l.max_speed_mph!=null?l.max_speed_mph.toFixed(1)+' mph':'—'}</td>
      <td>${l.avg_throttle!=null?l.avg_throttle.toFixed(1)+'%':'—'}</td>
      <td>${l.avg_brake!=null?l.avg_brake.toFixed(1)+'%':'—'}</td>
      <td class="${scls(l.avg_slip||0)}">${l.avg_slip!=null?l.avg_slip.toFixed(4):'—'}</td>
      <td class="${scls(l.peak_slip||0)}">${l.peak_slip!=null?l.peak_slip.toFixed(4):'—'}</td>
      <td>${l.slip_above_pct!=null?l.slip_above_pct.toFixed(1)+'%':'—'}</td>
    </tr>`;
  }).join('');
}
function renderAI(){
  if(_sess.ai_analysis){
    document.getElementById('ai-body').textContent=_sess.ai_analysis;
    document.getElementById('ai-body').style.display='block';
    document.getElementById('btn-analyze').style.display='none';
    document.getElementById('btn-re').style.display='inline-block';
    if(_sess.ai_analyzed_at){
      const dt=new Date(_sess.ai_analyzed_at).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
      document.getElementById('ai-meta').textContent='Cached · '+dt+(_sess.ai_model?' · '+_sess.ai_model:'');
    }
  }
}
async function runAnalysis(force){
  const btn=document.getElementById('btn-analyze');
  const rbtn=document.getElementById('btn-re');
  const body=document.getElementById('ai-body');
  const meta=document.getElementById('ai-meta');
  const err=document.getElementById('ai-err');
  err.style.display='none';
  btn.disabled=true;rbtn.disabled=true;
  if(force){rbtn.textContent='Analyzing…';}else{btn.textContent='Analyzing…';}
  try{
    const r=await fetch('/analyze?id='+encodeURIComponent(_id)+(force?'&force=true':''));
    const d=await r.json();
    if(!r.ok)throw new Error(d.error||'Unknown error');
    body.textContent=d.analysis;body.style.display='block';
    btn.style.display='none';rbtn.style.display='inline-block';rbtn.textContent='Re-analyze';rbtn.disabled=false;
    if(d.analyzed_at){
      const dt=new Date(d.analyzed_at).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
      meta.textContent='Analyzed '+dt+(d.model?' · '+d.model:'');
    }
  }catch(e){
    err.textContent='✗ '+e.message;err.style.display='block';
    btn.disabled=false;btn.textContent='Analyze with Claude';
    rbtn.disabled=false;if(!_sess.ai_analysis)rbtn.style.display='none';
  }
}
// ── Edit modal ────────────────────────────────────────────────
let _editTrack='',_editRaceType=null;
function openEdit(){
  if(!_sess)return;
  const cur=_sess.track&&_sess.track!=='unknown'?_sess.track:'';
  const allTracks=TRACK_NAMES.includes(cur)||!cur?TRACK_NAMES:[...TRACK_NAMES,cur].sort();
  const sel=document.getElementById('edit-track');
  sel.innerHTML='<option value="">— Unknown —</option>'+allTracks.map(t=>`<option value="${t}"${t===cur?' selected':''}>${t}</option>`).join('');
  _editTrack=cur;
  _editRaceType=_sess.race_type||_sess.session_type||null;
  document.querySelectorAll('#edit-ovl .etype').forEach(c=>c.classList.toggle('sel',c.dataset.val===_editRaceType));
  document.getElementById('edit-ovl').classList.add('open');
}
function closeEdit(){document.getElementById('edit-ovl').classList.remove('open');}
function editSelType(el){
  document.querySelectorAll('#edit-ovl .etype').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  _editRaceType=el.dataset.val;
}
async function saveEdit(){
  if(!_id)return;
  const body={id:_id};
  const track=document.getElementById('edit-track').value;
  if(track)body.track=track;
  if(_editRaceType)body.race_type=_editRaceType;
  await fetch('/sessions/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  closeEdit();
  const d=await fetch('/sessions/session/data?id='+encodeURIComponent(_id)).then(r=>r.json());
  if(d.session){_sess=d.session;_laps=d.laps||[];renderHeader();}
}

init();
