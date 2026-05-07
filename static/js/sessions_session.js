// race_type values land here from db.store._classify_race_type — primarily
// `real` (humans present), `ai` (AI grid), `time_trial` (no position changes,
// <=3 laps). Older code also wrote `race`, `race_ai`, etc. — keep those for
// backward compat with sessions classified before the rename.
const TYPE_LABELS={practice:'Practice',time_trial:'Time Trial',qualifying:'Qualifying',race:'Race',race_ai:'Race vs AI',race_online:'Online Race',hot_lap:'Hot Lap',real:'Race',ai:'AI Race'};
// Maps race_type to a color-modifier class on .type-chip. Folds older synonyms
// (race_ai → t-ai, race_online → t-race, etc.) onto the canonical buckets.
function typeChipClass(t){
  if(t==='real'||t==='race'||t==='race_online')return 't-race';
  if(t==='ai'||t==='race_ai')return 't-ai';
  if(t==='time_trial')return 't-time_trial';
  if(t==='practice')return 't-practice';
  if(t==='hot_lap')return 't-hot_lap';
  return '';
}
// Forza drivetrain_type spec: 0=FWD, 1=RWD, 2=AWD.
const DRIVETRAIN_LABELS={0:'FWD',1:'RWD',2:'AWD'};
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
  // Only render the THIS SESSION pill when we have a real car name —
  // otherwise it reads as noise ("Unknown Car / PI 900 / real").
  // Render priority: user nickname > resolved name > "Unknown Car (#ord)".
  // When a nickname is set AND we have a resolved name, show the resolved
  // name as a small subtitle so the user can still identify the actual car.
  let resolvedName=null;
  if(s.car&&s.car!=='unknown'&&!/^Unknown Car/i.test(s.car)){
    resolvedName=s.car;
  }else if(s.car_ordinal!=null){
    resolvedName=`Unknown Car (#${s.car_ordinal})`;
  }
  const nick=s.car_nickname||null;
  const carName=nick||resolvedName;
  const subtitle=(nick&&resolvedName&&nick!==resolvedName)?resolvedName:null;
  const cls=s.car_class!=null?CLASS_NAMES[s.car_class]:null;
  const pi=s.car_pi;
  const dt=s.drivetrain_type!=null?DRIVETRAIN_LABELS[s.drivetrain_type]:null;
  const cyl=s.num_cylinders;
  const effType=s.race_type||(s.session_type&&s.session_type!=='unknown'?s.session_type:null);
  const thisBlock=document.getElementById('lr-this');
  const carEl=document.getElementById('lr-car');
  const badgesEl=document.getElementById('lr-badges');
  if(carName){
    thisBlock.style.display='';
    carEl.innerHTML=carName + (subtitle?`<div style="font-size:.65rem;color:var(--color-text-muted);font-weight:normal;margin-top:2px">${subtitle}</div>`:'');
    let badges='';
    if(cls)badges+=`<span class="cc cc-${cls}">${cls}</span>`;
    if(pi)badges+=`<span style="font-size:.6rem;color:var(--color-text-muted)">PI ${pi}</span>`;
    if(dt)badges+=`<span style="font-size:.6rem;color:var(--color-text-muted)">${dt}</span>`;
    if(cyl)badges+=`<span style="font-size:.6rem;color:var(--color-text-muted)">${cyl}cyl</span>`;
    if(effType)badges+=`<span class="type-chip ${typeChipClass(effType)}" style="font-size:.55rem">${TYPE_LABELS[effType]||effType}</span>`;
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
  if(effType){
    const el=document.getElementById('hdr-type');
    el.textContent=TYPE_LABELS[effType]||effType;
    // Reset prior color class then apply current — keeps the chip from
    // accumulating modifiers across navigations (defensive, not strictly
    // necessary on a hard reload).
    el.className='type-chip '+typeChipClass(effType);
    el.style.display='';
  }
  // Race position: Grid / Finish / Gained header stats — shown only when present.
  const fp=s.finish_pos, gp=s.grid_pos;
  const gridStat=document.getElementById('hdr-grid-stat');
  const finishStat=document.getElementById('hdr-finish-stat');
  const gainedStat=document.getElementById('hdr-gained-stat');
  if(gp!=null && gp>0){
    document.getElementById('hdr-grid').textContent='P'+gp;
    gridStat.style.display='';
  }
  if(fp!=null){
    document.getElementById('hdr-finish').textContent='P'+fp;
    finishStat.style.display='';
  }
  if(gp!=null && gp>0 && fp!=null){
    const g=gp-fp;
    const el=document.getElementById('hdr-gained');
    el.textContent = g>0?'+'+g : g<0?String(g) : '0';
    el.style.color = g>0?'var(--color-green)' : g<0?'var(--color-red)' : '';
    gainedStat.style.display='';
  }
  // Weather + tyre compound badges (set via the edit modal)
  const wxEl=document.getElementById('hdr-weather');
  if(wxEl){
    if(s.weather_condition){wxEl.textContent=s.weather_condition;wxEl.style.display='';}
    else wxEl.style.display='none';
  }
  const tyEl=document.getElementById('hdr-tyre');
  if(tyEl){
    if(s.tyre_compound){tyEl.textContent=s.tyre_compound;tyEl.style.display='';}
    else tyEl.style.display='none';
  }
}
function renderLaps(){
  const best=_sess.best_lap_time_s;
  // Forza UDP lap_number is 0-indexed; lap 0 IS race lap 1, not an out-lap.
  // Drop the lap_number > 0 / OUT LAP carve-outs (those were ACC-style and
  // ACC support is parked).
  const validTimes=_laps.filter(l=>l.lap_time_s).map(l=>l.lap_time_s);
  validTimes.sort((a,b)=>a-b);
  const median=validTimes.length?validTimes[Math.floor(validTimes.length/2)]:null;
  document.getElementById('lap-tbody').innerHTML=_laps.map(l=>{
    const isSlow=median&&l.lap_time_s&&l.lap_time_s>median*1.4;
    const isB=best&&l.lap_time_s&&Math.abs(l.lap_time_s-best)<0.001;
    const rowCls=[isB?'best-row':'',isSlow?'outlier-row':''].filter(Boolean).join(' ');
    const timeHtml=isSlow?`<span class="outlier-time">${fmtLap(l.lap_time_s)}</span>`:fmtLap(l.lap_time_s);
    return `<tr class="${rowCls}">
      <td>${l.lap_number != null ? l.lap_number + 1 : '—'}</td>
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
let _editTrack='',_editRaceType=null,_editWeather='Dry',_editTyre=null;
// Autocomplete widget instances reused across modal opens (avoid leaking listeners).
let _trackAc=null;
let _carAc=null;
async function openEdit(){
  if(!_sess)return;
  const cur=_sess.track&&_sess.track!=='unknown'?_sess.track:'';
  // Fetch the merged track list at open time so newly-learned ordinals
  // (and any extended-CSV reload) are reflected without a page refresh.
  // Falls back to the page-embedded TRACK_NAMES if the endpoint fails.
  let tracks;
  try{
    tracks=await fetch('/sessions/track-options').then(r=>r.json());
    if(!Array.isArray(tracks)||!tracks.length)tracks=TRACK_NAMES;
  }catch(e){tracks=TRACK_NAMES;}
  if(cur && !tracks.includes(cur))tracks=[...tracks,cur].sort();
  // Autocomplete widget (replaces the old <datalist>). Attached once and
  // reused; setOptions on subsequent opens so newly-learned tracks show up.
  const trackInput=document.getElementById('edit-track');
  if(!_trackAc){
    _trackAc=Autocomplete.attach(trackInput,{
      options:tracks,
      allowFreeText:true,
      initialValue:cur,
    });
  }else{
    _trackAc.setOptions(tracks);
    trackInput.value=cur;
  }
  // Car field: searchable autocomplete drawn from CAR_CATALOG (inlined on the
  // page from FORZA_CARS). Free-text fallback preserved for unmapped ordinals
  // — the user can hunt down the actual name later. "Unknown Car (#NNN)"
  // pre-fills as the initial value so they have a starting point.
  const carInput=document.getElementById('edit-car');
  const carInitial=(_sess.car && _sess.car!=='unknown')?_sess.car:'';
  if(!_carAc){
    _carAc=Autocomplete.attach(carInput,{
      options:(typeof CAR_CATALOG!=='undefined')?CAR_CATALOG:[],
      allowFreeText:true,
      initialValue:carInitial,
    });
  }else{
    carInput.value=carInitial;
  }
  // Nickname row: only meaningful when we have a car_ordinal — otherwise
  // there's nothing to key the nickname to.
  const nickRow=document.getElementById('edit-nickname-row');
  const nickInput=document.getElementById('edit-nickname');
  if(_sess.car_ordinal!=null){
    nickRow.style.display='';
    nickInput.value=_sess.car_nickname||'';
  }else{
    nickRow.style.display='none';
    nickInput.value='';
  }
  _editTrack=cur;
  _editRaceType=_sess.race_type||_sess.session_type||null;
  // Default weather to Dry per spec; tyre has no default.
  _editWeather=_sess.weather_condition||'Dry';
  _editTyre=_sess.tyre_compound||null;
  // Activate the right pill in each chip group (scoped per-row to avoid cross-row collisions).
  document.querySelectorAll('#edit-ovl .edit-chips').forEach(g=>g.querySelectorAll('.etype').forEach(c=>c.classList.remove('sel')));
  document.querySelectorAll('#edit-ovl .edit-row .edit-chips .etype').forEach(c=>{
    if(c.dataset.val===_editRaceType && c.parentElement.id!=='edit-weather-chips' && c.parentElement.id!=='edit-tyre-chips')c.classList.add('sel');
  });
  document.querySelectorAll('#edit-weather-chips .etype').forEach(c=>c.classList.toggle('sel',c.dataset.val===_editWeather));
  document.querySelectorAll('#edit-tyre-chips .etype').forEach(c=>c.classList.toggle('sel',c.dataset.val===_editTyre));
  // Read-only conditions context: show track and air temps if telemetry captured them.
  const tt=_sess.track_temp_c, at=_sess.air_temp_c;
  const condEl=document.getElementById('edit-conditions');
  const condRow=document.getElementById('edit-conditions-row');
  if(tt!=null||at!=null){
    const parts=[];
    if(tt!=null)parts.push(`Track: ${tt.toFixed(0)}°C`);
    if(at!=null)parts.push(`Air: ${at.toFixed(0)}°C`);
    condEl.textContent=parts.join(' · ');
    condRow.style.display='';
  }else{
    condRow.style.display='none';
  }
  document.getElementById('edit-ovl').classList.add('open');
}
function closeEdit(){document.getElementById('edit-ovl').classList.remove('open');}
async function deleteSession(){
  if(!_id)return;
  // Two-step confirm — single click on a destructive button feels too easy.
  const trackHint = (_sess && _sess.track && _sess.track !== 'unknown') ? _sess.track : 'this session';
  const ok = window.confirm(
    'Permanently delete '+trackHint+'?\n\n'+
    'This removes the session, its lap data, raw archive, and any AI analysis. There is no undo.'
  );
  if(!ok) return;
  try{
    const res = await fetch('/sessions/delete', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id: _id})
    });
    if(!res.ok) throw new Error('HTTP '+res.status);
    // Redirect back to the sessions list — the current detail page no
    // longer has anything to show.
    location.href = '/sessions';
  }catch(e){
    alert('Could not delete session: '+(e && e.message || e));
  }
}
function editSelType(el){
  el.parentElement.querySelectorAll('.etype').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  _editRaceType=el.dataset.val;
}
function editSelWeather(el){
  el.parentElement.querySelectorAll('.etype').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  _editWeather=el.dataset.val;
}
function editSelTyre(el){
  // Tyre is optional — clicking the active pill toggles it off.
  if(el.classList.contains('sel')){el.classList.remove('sel');_editTyre=null;return;}
  el.parentElement.querySelectorAll('.etype').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  _editTyre=el.dataset.val;
}
async function saveEdit(){
  if(!_id)return;
  const body={id:_id};
  const track=document.getElementById('edit-track').value.trim();
  if(track)body.track=track;
  if(_editRaceType)body.race_type=_editRaceType;
  // If the user picked a track AND the session has a detected ordinal,
  // remember the ordinal→name mapping so future sessions auto-resolve it.
  // The /sessions/update endpoint upserts into learned_track_ordinals.
  if(track && _sess.track_ordinal && track !== _sess.track){
    body.learned_ordinal={
      ordinal: _sess.track_ordinal,
      game: _sess.game||'forza_motorsport',
      track_name: track,
    };
  }
  body.weather_condition=_editWeather||'';
  body.tyre_compound=_editTyre||'';
  // Free-text car override (covers Unknown Car / unmapped ordinals — see #6).
  const car=document.getElementById('edit-car').value.trim();
  body.car=car;  // empty string clears the override; "Unknown Car" passes through
  await fetch('/sessions/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  // Nickname is keyed to car_ordinal, not the session — separate POST.
  // Empty string deletes the nickname (matches server-side semantics).
  if(_sess.car_ordinal!=null){
    const nick=document.getElementById('edit-nickname').value.trim();
    if(nick !== (_sess.car_nickname||'')){
      await fetch('/cars/nickname',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ordinal:_sess.car_ordinal, nickname:nick})});
    }
  }
  closeEdit();
  const d=await fetch('/sessions/session/data?id='+encodeURIComponent(_id)).then(r=>r.json());
  if(d.session){_sess=d.session;_laps=d.laps||[];renderHeader();}
}

init();
