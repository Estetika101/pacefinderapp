const $=id=>document.getElementById(id);
const es=new EventSource('/stream');
let _maxRpm=8500,_dbgEs=null,_dbgOpen=false,_bestLap=null;
let state_sid=null;
const _dbgLines=[];
const _flashTimers={};
// Check ?edit=<sid> on load — open confirm modal for that session
const _editSid=new URLSearchParams(location.search).get('edit');
if(_editSid) setTimeout(()=>openFinish(_editSid),600);

function flash(id){
  const el=$(id); if(!el)return;
  if(_flashTimers[id])clearTimeout(_flashTimers[id]);
  el.classList.remove('flash');
  void el.offsetWidth; // reflow to restart animation
  el.classList.add('flash');
  _flashTimers[id]=setTimeout(()=>el.classList.remove('flash'),400);
}

function fmt(s){
  if(s==null)return'—';
  const m=Math.floor(s/60);
  return m+':'+(s%60).toFixed(3).padStart(6,'0');
}

function slipColor(v){
  if(v<0.1)return'#22c55e';
  if(v<0.3)return'#f59e0b';
  return'#ef4444';
}

function tyreClass(t){
  if(t==null)return'na';
  if(t<170)return'cold';
  if(t<=210)return'ok';
  if(t<=230)return'hot';
  return'over';
}

let _liveGame=null;
function setSlip(pfx,val){
  const v=val??0;
  // ACC wheelSlip is in m/s (0–3 range); Forza/F1 are dimensionless ratios (0–1 range)
  const scale=(_liveGame==='acc')?0.5:0.5;
  const pct=Math.min(100,v/scale*100);
  const col=slipColor(v/scale*0.5);
  $(pfx+'-b').style.height=pct+'%';
  $(pfx+'-b').style.background=col;
  $(pfx+'-v').textContent=val!=null?v.toFixed(3):'—';
  $(pfx+'-v').style.color=col;
}

es.onmessage=e=>{
  const d=JSON.parse(e.data);
  const recv=d.status==='receiving';
  const ended=d.status==='race_ended';

  // topbar
  $('dot').className='dot '+(recv?'receiving':ended?'race_ended':'idle');
  $('tb-stat').textContent=ended?'RACE ENDED':(d.status||'IDLE').toUpperCase();
  $('tb-stat').className='tb-stat'+(recv?' receiving':ended?' race_ended':'');
  const gameLabels={'forza_motorsport':'Forza Motorsport','forza_horizon_5':'Forza Horizon','acc':'ACC','f1':'F1 2024'};
  const gameClsMap={'forza_motorsport':'forza','forza_horizon_5':'forza','acc':'acc','f1':'f1'};
  const gEl=$('tb-game');
  gEl.textContent=d.game?gameLabels[d.game]||d.game.replace(/_/g,' ').toUpperCase():'—';
  gEl.className='tb-game game-'+(d.game?gameClsMap[d.game]||'none':'none');
  $('tb-track').textContent=d.track&&d.track!=='unknown'?d.track:'—';
  $('tb-drs').style.display=d.drs?'inline':'none';
  $('tb-cmp').textContent=d.tyre_compound||'';

  // track session id and show/hide finish button
  if(d.session_id) state_sid = d.session_id;
  $('btn-finish').style.display = (recv||ended) ? 'inline-block' : 'none';

  // Auto-open confirm modal shortly after race_ended. Short delay (500ms)
  // gives the user a beat to see the dashboard transition before the modal
  // pops; previously this was 5s which felt like a hang. See #32.
  if(ended&&!$('fo').classList.contains('open')){
    if(!_foAutoTimer) _foAutoTimer=setTimeout(()=>{_foAutoTimer=null;openFinish();},500);
  } else if(!ended&&_foAutoTimer){
    clearTimeout(_foAutoTimer);_foAutoTimer=null;
  }

  // gear
  const g=d.gear;
  const ge=$('gear');
  ge.textContent=g==null?'—':g===0?'N':g===-1?'R':String(g);
  ge.className='gear-val'+(g===0?' N':g===-1?' R':'');

  // speed
  $('spd').textContent=d.speed_mph!=null?d.speed_mph.toFixed(0):'—';

  // rpm bar
  const rpm=d.rpm||0;
  if(d.engine_max_rpm&&d.engine_max_rpm>2000)_maxRpm=d.engine_max_rpm;
  const rPct=Math.min(100,rpm/_maxRpm*100);
  const rf=$('rpm-fill');
  rf.style.width=rPct+'%';
  rf.className='rpm-fill '+(rPct>=88?'shift':rPct>=75?'hi':rPct>=55?'mid':'lo');
  $('rpm-pct').textContent=rPct>0?Math.round(rPct)+'%':'—';
  $('rpm-num').textContent=rpm?Math.round(rpm).toLocaleString()+' rpm':'—';

  // pedals
  const thr=d.throttle_pct||0,brk=d.brake_pct||0;
  $('thr-b').style.height=thr+'%';
  $('thr-v').textContent=Math.round(thr)+'%';
  $('brk-b').style.height=brk+'%';
  $('brk-v').textContent=Math.round(brk)+'%';
  // flash only while actively receiving — suppress during idle/race_ended
  if(recv&&brk>92) flash('brk-row');

  // slip
  _liveGame=d.game;
  setSlip('srl',d.slip_rl);
  setSlip('srr',d.slip_rr);
  // flash slip panel on oversteer — threshold is game-specific (ACC in m/s, Forza/F1 normalized ratio)
  const _slipAlert=(_liveGame==='acc')?0.6:0.6;
  if(recv&&((d.slip_rl||0)>_slipAlert||(d.slip_rr||0)>_slipAlert)) flash('slip-panel');

  // timing
  $('t-cur').textContent=fmt(d.current_lap_time);
  $('t-best').textContent=fmt(d.best_lap_time_s);
  $('t-last').textContent=fmt(d.last_lap_time_s);
  $('t-lap').textContent=d.lap!=null?'L'+d.lap:'—';

  // delta to best
  const dEl=$('t-delta');
  if(d.current_lap_time!=null&&d.best_lap_time_s!=null){
    const delta=d.current_lap_time-d.best_lap_time_s;
    const sign=delta<0?'':'+';
    dEl.textContent=sign+delta.toFixed(3)+'s';
    dEl.className='delta-val '+(delta<-0.01?'ahead':delta>0.01?'behind':'even');
    // flash delta when significantly behind pace
    if(recv&&delta>1.5) flash('t-delta');
  } else {
    dEl.textContent='—'; dEl.className='delta-val even';
  }

  // race position (current, grid, ± gained vs grid)
  const rp=d.race_position, gp=d.grid_pos;
  $('pos-cur').textContent  = rp ? 'P'+rp : '—';
  $('pos-grid').textContent = gp ? 'P'+gp : '—';
  const pdEl=$('pos-delta');
  if(rp && gp){
    const gained=gp-rp;  // positive = gained positions vs grid
    pdEl.textContent = gained>0 ? '+'+gained : gained<0 ? String(gained) : '0';
    pdEl.className='delta-val '+(gained>0?'ahead':gained<0?'behind':'even');
  } else {
    pdEl.textContent='—'; pdEl.className='delta-val even';
  }

  // tyres
  ['fl','fr','rl','rr'].forEach(c=>{
    const el=$('ty-'+c);
    const t=d['tyre_'+c];
    el.textContent=t!=null?Math.round(t)+'°':'—';
    el.className='tyre-temp '+tyreClass(t);
  });
  const tyCmp=$('ty-cmp');if(tyCmp)tyCmp.textContent=d.tyre_compound||'';

  // udp strip
  const udp=d.udp_received||{},rej=d.udp_rejected||{},rsz=d.last_rejected_size||{};
  $('udp-strip').innerHTML=['forza_motorsport','acc','f1'].map(gm=>{
    const n=udp[gm]||0,r=rej[gm]||0,sz=rsz[gm];
    const c=n>0?'#22c55e33':r>0?'#ef444433':'#1a1a1a';
    return `<span style="color:${c}">${gm.replace('_motorsport','').replace('_',' ')}: ${n}ok${r?' '+r+'rej':''}${sz?' ('+sz+'B)':''}</span>`;
  }).join('<span style="color:var(--color-border-subtle)"> · </span>');
};

es.onerror=()=>{$('dot').className='dot';};

function toggleDebug(){
  _dbgOpen=!_dbgOpen;
  $('dbg').style.display=_dbgOpen?'flex':'none';
  $('dbg-btn').className='bot-btn'+(_dbgOpen?' on':'');
  if(_dbgOpen&&!_dbgEs)startDbg();
}
function startDbg(){
  _dbgEs=new EventSource('/debug-stream');
  _dbgEs.onmessage=e=>addDbg(JSON.parse(e.data));
  _dbgEs.onerror=()=>{_dbgEs=null;if(_dbgOpen)setTimeout(startDbg,2000);};
}
function lnColor(l){
  if(l.includes('[ERROR]'))return'#ef4444';
  if(l.includes('[WARNING]')||l.includes('[REJECTED]'))return'#f59e0b';
  if(l.includes('[UDP OK]'))return'#22c55e33';
  return'#1e1e2a';
}
function lnVis(l){
  const f=$('dbg-f').value;
  if(f==='warn')return l.includes('[ERROR]')||l.includes('[WARNING]')||l.includes('[REJECTED]');
  if(f==='udp')return l.includes('[UDP OK]')||l.includes('[REJECTED]');
  return true;
}
function addDbg(line){
  _dbgLines.push(line);if(_dbgLines.length>2000)_dbgLines.shift();
  if(!lnVis(line))return;
  const el=$('dbg-log');
  const d=document.createElement('div');
  d.style.cssText='color:'+lnColor(line)+';border-bottom:1px solid var(--color-border-subtle);padding:1px 0';
  d.textContent=line;el.appendChild(d);
  while(el.children.length>1000)el.removeChild(el.firstChild);
  if($('dbg-as').checked)el.scrollTop=el.scrollHeight;
}
function applyFilter(){
  const el=$('dbg-log');el.innerHTML='';
  _dbgLines.filter(lnVis).slice(-500).forEach(l=>{
    const d=document.createElement('div');
    d.style.cssText='color:'+lnColor(l)+';border-bottom:1px solid var(--color-border-subtle);padding:1px 0';
    d.textContent=l;el.appendChild(d);
  });
  el.scrollTop=el.scrollHeight;
}
function clearDebug(){_dbgLines.length=0;$('dbg-log').innerHTML='';}

// ── Finish Race overlay ───────────────────────────────────────────────────────
let _foSid=null, _foRaceType=null, _foDropLast=false, _foLaps=[], _foClosed=false;
let _foTrackOrdinal=null, _foAutoTimer=null;

function selType(el){
  document.querySelectorAll('#fo .type-chip').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  _foRaceType=el.dataset.val;
}

async function openFinish(editSid){
  if(_foAutoTimer){clearTimeout(_foAutoTimer);_foAutoTimer=null;}

  // Optimistic UX: pop the modal IMMEDIATELY with a loading state so the
  // button feels responsive. The /finish POST blocks on synchronous DB +
  // file writes; we used to await it before opening, which made the click
  // feel multi-second slow. See #32.
  $('fo-title').textContent = 'Finishing race…';
  $('fo-sub').textContent   = 'Saving session…';
  $('fo-stats').style.display = 'none';
  $('fo').classList.add('open');

  let sid = editSid || null;
  if(!editSid){
    // Close active session
    const res = await fetch('/finish',{method:'POST'});
    const closed = await res.json().catch(()=>({}));
    if(closed.closed&&closed.closed.length) sid=closed.closed[0];
    if(!sid){
      const st = await fetch('/status').then(r=>r.json());
      sid = state_sid || st.session_id;
    }
  }
  _foSid=sid; _foRaceType=null; _foDropLast=false; _foClosed=false; _foTrackOrdinal=null;
  if(!_foSid){
    // Couldn't recover a session id — back out cleanly so the user isn't
    // stuck on a "Finishing race…" placeholder.
    $('fo').classList.remove('open');
    return;
  }

  try {
    // Load session metadata + track list
    const cd = await fetch('/sessions/confirm-data?id='+encodeURIComponent(_foSid)).then(r=>r.json());
    const cur = cd.session;
    if(!cur) return;
    _foSid = cur.session_id||_foSid;
    _foTrackOrdinal = cd.track_ordinal;

    // Load laps
    const ld = await fetch('/sessions/session/data?id='+encodeURIComponent(_foSid)).then(r=>r.json()).catch(()=>({}));
    _foLaps = ld.laps||[];

    // Header
    const track = cur.track&&cur.track!=='unknown' ? cur.track : null;
    $('fo-title').textContent = track||'Session Complete';
    const badge=$('fo-game-badge');
    if(cur.game){badge.textContent=(cur.game||'').replace(/_/g,' ').toUpperCase();badge.style.display='inline';}
    else badge.style.display='none';
    $('fo-sub').textContent = cur.started_at
      ? new Date(cur.started_at).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})
      : '—';

    // Stats row
    const validLaps=_foLaps.filter(l=>l.lap_time_s);
    if(validLaps.length){
      const best=Math.min(...validLaps.map(l=>l.lap_time_s));
      $('fo-stat-laps').textContent=validLaps.length;
      $('fo-stat-best').textContent=fmt(best);
      $('fo-stats').style.display='flex';
    } else {
      $('fo-stats').style.display='none';
    }

    // Track dropdown
    const sel=$('fo-track');
    sel.innerHTML='<option value="">— Unknown —</option>';
    (cd.track_list||[]).forEach(t=>{
      const o=document.createElement('option');
      o.value=t;o.textContent=t;
      if(t===cur.track)o.selected=true;
      sel.appendChild(o);
    });
    // If track is an unidentified ordinal, add as a selectable option too
    if(cur.track&&cur.track.startsWith('Track #')&&!sel.value){
      const o=document.createElement('option');
      o.value=cur.track;o.textContent=cur.track+' (unidentified)';o.selected=true;
      sel.insertBefore(o,sel.options[1]);
    }

    // Car input
    $('fo-car').value=cur.car&&cur.car!=='unknown'?cur.car:'';

    // Pre-select race_type
    if(cur.race_type){
      const chip=document.querySelector(`#fo .type-chip[data-val="${cur.race_type}"]`);
      if(chip) selType(chip);
    }
    renderFoLaps();
  } catch(e){
    // Don't strand the user on a "Finishing race…" placeholder if any of the
    // session/data fetches failed. Surface the error in the title and let
    // them dismiss with Skip.
    console.error(e);
    $('fo-title').textContent = 'Could not load session';
    $('fo-sub').textContent   = String(e && e.message || e);
    return;
  }
  // Modal is already open from the optimistic step at the top of openFinish.
}

function renderFoLaps(){
  const validTimes=_foLaps.filter(l=>l.lap_time_s).map(l=>l.lap_time_s);
  const best=validTimes.length?Math.min(...validTimes):null;
  const lastIdx=_foLaps.length-1;
  $('fo-laps').innerHTML=_foLaps.map((lap,i)=>{
    const t=lap.lap_time_s;
    const isLast=i===lastIdx;
    const isBest=t&&t===best;
    const isPartial=isLast&&(!t||_foDropLast);
    const timeStr=t?fmt(t):'partial';
    const delBtn=isLast
      ?`<button class="fo-lap-del${_foDropLast?' undone':''}" onclick="toggleDropLast()">${_foDropLast?'Restore':'Delete'}</button>`
      :'';
    return `<div class="fo-lap${isPartial?' partial':''}">
      <span class="fo-lap-num">L${lap.lap_number}</span>
      <span class="fo-lap-time${isBest&&!_foDropLast?' best':''}">${timeStr}</span>
      ${isPartial&&!_foDropLast?'<span class="fo-lap-badge">PARTIAL</span>':''}
      ${delBtn}
    </div>`;
  }).join('');
}

function toggleDropLast(){
  _foDropLast=!_foDropLast;
  renderFoLaps();
}

async function saveFinish(){
  if(!_foSid) return;
  const body={id:_foSid};
  if(_foRaceType) body.race_type=_foRaceType;
  if(_foDropLast) body.drop_last_lap=true;
  const selTrack=$('fo-track').value;
  if(selTrack&&!selTrack.startsWith('Track #')) body.track=selTrack;
  const carVal=$('fo-car').value.trim();
  if(carVal) body.car=carVal;
  // Learn the ordinal if user identified an unknown track
  if(_foTrackOrdinal&&selTrack&&!selTrack.startsWith('Track #')){
    body.learned_ordinal={ordinal:_foTrackOrdinal,game:'forza_motorsport',track_name:selTrack};
  }
  await fetch('/sessions/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  closeFinish();
}

function closeFinish(){
  $('fo').classList.remove('open');
  if(_foAutoTimer){clearTimeout(_foAutoTimer);_foAutoTimer=null;}
}
