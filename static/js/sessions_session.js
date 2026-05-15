// race_type values: `real` (humans), `ai`, `time_trial`. Older code wrote
// `race`, `race_ai`, etc. — keep both forms for backward compatibility.
const TYPE_LABELS={practice:'Practice',time_trial:'Time Trial',qualifying:'Qualifying',race:'Race',race_ai:'AI Race',race_online:'Online Race',hot_lap:'Hot Lap',real:'Race',ai:'AI Race'};
function typeChipClass(t){
  if(t==='real'||t==='race'||t==='race_online')return 't-race';
  if(t==='ai'||t==='race_ai')return 't-ai';
  if(t==='time_trial')return 't-time_trial';
  if(t==='practice')return 't-practice';
  if(t==='hot_lap')return 't-hot_lap';
  return '';
}
// Forza drivetrain_type spec: 0=FWD, 1=RWD, 2=AWD
const DRIVETRAIN_LABELS={0:'FWD',1:'RWD',2:'AWD'};
// FH5 nine-class scheme. #103 tracks the FM2023 vs FH5 split.
const CLASS_NAMES={0:'D',1:'C',2:'B',3:'A',4:'S1',5:'S2',6:'X',7:'R',8:'P'};

function fmtLap(s){if(s==null)return '—';const m=Math.floor(s/60);return m+':'+(s%60).toFixed(3).padStart(6,'0');}
function fmtDelta(d){if(d==null)return '—';const sign=d>0?'+':'';return sign+d.toFixed(3);}
function fmtDateShort(iso){
  if(!iso)return '—';
  const d=new Date(iso);
  return d.toLocaleString([],{weekday:'short',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
}
function fmtTimeRange(startIso, endIso){
  if(!startIso)return '—';
  const s=new Date(startIso);
  const start=s.toLocaleString([],{weekday:'short',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
  if(!endIso)return start;
  const e=new Date(endIso);
  const end=e.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
  return start+' – '+end;
}

const _qs=new URLSearchParams(location.search);
const _id=_qs.get('id')||'';
const _sgame=_qs.get('game')||'';
const _strack=_qs.get('track')||'';

let _sess=null,_laps=[],_theo=null,_carCtx=null;
let _sortKey='lap', _sortDir='asc';

async function init(){
  if(!_id){location.href='/sessions';return;}
  let d;
  try{d=await fetch('/sessions/session/data?id='+encodeURIComponent(_id)).then(r=>r.json());}
  catch(e){document.getElementById('hdr-track').textContent='Session not found';return;}
  _sess=d.session;_laps=d.laps||[];_theo=d.theoretical||null;_carCtx=d.car_context||null;
  renderCrumbAndNav();
  renderHeader();
  renderHero();
  renderProfile();
  renderLaps();
  renderCards();
  renderAI();
  attachSortHandlers();
  // Hero delta line — async, doesn't block initial render
  loadHeroDelta();
}

async function loadHeroDelta(){
  try{
    const d = await fetch('/sessions/session/hero-delta?id='+encodeURIComponent(_id)).then(r=>r.json());
    if(!d || !d.available){
      const empty = document.getElementById('delta-empty');
      if(empty){
        empty.textContent = (d && d.reason) || 'Delta line unavailable.';
        empty.style.display = '';
      }
      return;
    }
    renderDelta(d);
  }catch(e){
    // Silent fail — the rest of the page is already rendered.
  }
}

function renderDelta(d){
  const svg = document.getElementById('hero-delta-svg');
  const fill = document.getElementById('hero-delta-fill');
  const line = document.getElementById('hero-delta-line');
  const header = document.getElementById('delta-header');
  const meta = document.getElementById('delta-meta');
  if(!svg || !line || !d.points || !d.points.length) return;

  // Map dt → y. Symmetric scale based on max |dt| observed, with a floor
  // of 0.3s so a tight session still looks proportionate. Zero is y=90.
  const maxAbs = d.points.reduce((m, p) => Math.max(m, Math.abs(p.dt || 0)), 0.3);
  const W = 1000, H = 180, ZERO = 90;
  // Range: [-maxAbs, +maxAbs] mapped to [180, 0] (positive dt = above zero
  // means slower-than-best, so visually higher = worse)
  const dtToY = (dt) => ZERO - (dt / maxAbs) * (ZERO - 8);
  const dToX  = (dN)  => dN * W;

  // Path through every point
  const linePath = d.points.map((p, i) =>
    (i === 0 ? 'M ' : 'L ') + dToX(p.d).toFixed(1) + ' ' + dtToY(p.dt).toFixed(1)
  ).join(' ');
  // Fill area from line down/up to zero (closed polygon)
  const fillPath = linePath + ' L ' + dToX(d.points[d.points.length - 1].d).toFixed(1) +
                   ' ' + ZERO + ' L 0 ' + ZERO + ' Z';

  // Color the line and the fill gradient based on which side dominates.
  // If most points are slower, use the slower (red) gradient + amber line.
  // If most are faster, switch to faster (green) gradient + green line.
  const slowerCount = d.points.filter(p => p.dt > 0).length;
  const dominant = slowerCount > d.points.length / 2 ? 'slower' : 'faster';
  fill.setAttribute('d', fillPath);
  fill.setAttribute('fill', dominant === 'slower' ? 'url(#slowerGrad)' : 'url(#fasterGrad)');
  line.setAttribute('d', linePath);
  line.setAttribute('stroke', dominant === 'slower' ? 'var(--color-amber)' : 'var(--color-green)');

  // Header meta
  const bestLabel = 'L' + ((d.best && d.best.lap_number != null) ? d.best.lap_number + 1 : '—');
  const compLabel = 'L' + ((d.compare && d.compare.lap_number != null) ? d.compare.lap_number + 1 : '—');
  const totalDelta = d.points[d.points.length - 1].dt;
  const sign = totalDelta > 0 ? '+' : '';
  meta.textContent = compLabel + ' vs ' + bestLabel + ' · cumulative ' + sign + totalDelta.toFixed(3) + 's';

  svg.style.display = '';
  header.style.display = '';
}

function renderCrumbAndNav(){
  const s=_sess;
  const track=s.track&&s.track!=='unknown'?s.track:(_strack||'Unknown Track');
  const game=_sgame||s.game||'';
  document.title='Pacefinder · '+track;
  // Breadcrumb → /sessions/track?name=...
  let trackHref='/sessions/track?name='+encodeURIComponent(track);
  if(game)trackHref+='&game='+encodeURIComponent(game);
  const bc=document.getElementById('bc-track');
  bc.href=trackHref;
  document.getElementById('bc-track-name').textContent=track;
  // Telemetry subnav link
  let teleHref='/sessions/telemetry?id='+encodeURIComponent(_id);
  if(game)teleHref+='&game='+encodeURIComponent(game);
  if(track)teleHref+='&track='+encodeURIComponent(track);
  document.getElementById('link-telemetry').href=teleHref;
}

function renderHeader(){
  const s=_sess;
  const track=s.track&&s.track!=='unknown'?s.track:(_strack||'Unknown Track');
  document.getElementById('hdr-track').textContent=track;

  // H2 car link — nickname > resolved > Unknown Car (#N)
  let carText=null;
  if(s.car_nickname)carText=s.car_nickname;
  else if(s.car && s.car!=='unknown' && !/^Unknown Car/i.test(s.car))carText=s.car;
  else if(s.car_ordinal!=null)carText='Unknown Car (#'+s.car_ordinal+')';
  if(carText){
    document.getElementById('hdr-car-name').textContent=carText;
    document.getElementById('hdr-car-link').style.display='';
    if(s.car_ordinal!=null){
      document.getElementById('hdr-car-link').href='/cars/'+s.car_ordinal;
    }
    if(s.car_class!=null){
      const el=document.getElementById('hdr-car-class');
      el.textContent=CLASS_NAMES[s.car_class]||'';
      el.style.display='';
    }
    if(s.car_pi){
      const el=document.getElementById('hdr-car-pi');
      el.textContent=s.car_pi;
      el.style.display='';
    }
  }

  // Grid → Finish result block (race types only, both values present)
  const gp=s.grid_pos, fp=s.finish_pos;
  if(gp!=null && gp>0 && fp!=null){
    document.getElementById('hdr-grid-p').textContent='P'+gp;
    const fEl=document.getElementById('hdr-finish-p');
    fEl.textContent='P'+fp;
    const g=gp-fp;
    if(g>0){fEl.classList.add('finish');fEl.classList.remove('lost','same');}
    else if(g<0){fEl.classList.add('lost');fEl.classList.remove('finish','same');}
    else{fEl.classList.add('same');fEl.classList.remove('finish','lost');}
    const gEl=document.getElementById('hdr-gained');
    if(g>0){gEl.textContent='↗ '+g+' place'+(g===1?'':'s')+' gained';gEl.classList.remove('lost','same');}
    else if(g<0){gEl.textContent='↘ '+(-g)+' place'+(-g===1?'':'s')+' lost';gEl.classList.add('lost');}
    else{gEl.textContent='no change';gEl.classList.add('same');}
    document.getElementById('hdr-result').style.display='';
  }

  // Metadata strip pills
  const whenVal=fmtTimeRange(s.started_at, s.ended_at);
  if(whenVal && whenVal!=='—'){
    document.getElementById('hdr-when-val').textContent=whenVal;
    document.getElementById('hdr-when').style.display='';
  }
  // Conditions: weather + tyre + track_temp_c
  const condParts=[];
  if(s.weather_condition)condParts.push(s.weather_condition);
  if(s.tyre_compound)condParts.push(s.tyre_compound);
  if(s.track_temp_c!=null)condParts.push(Math.round(s.track_temp_c)+'°C');
  if(condParts.length){
    document.getElementById('hdr-cond-val').textContent=condParts.join(' · ');
    document.getElementById('hdr-cond').style.display='';
  }
  // Type
  const effType=s.race_type||(s.session_type&&s.session_type!=='unknown'?s.session_type:null);
  if(effType){
    const el=document.getElementById('hdr-type');
    el.textContent=TYPE_LABELS[effType]||effType;
    el.className='pill type-chip '+typeChipClass(effType);
    el.style.display='';
  }
}

function renderHero(){
  const s=_sess;
  const best=s.best_lap_time_s;
  document.getElementById('hero-best').textContent=fmtLap(best);
  // Find which lap is the best one for the subtitle
  let bestLap=null;
  _laps.forEach(l=>{
    if(l.lap_time_s && best && Math.abs(l.lap_time_s-best)<0.001)bestLap=l;
  });
  const subBits=[];
  if(bestLap && bestLap.lap_number!=null)subBits.push('Best lap · L'+(bestLap.lap_number+1));
  if(_laps.length)subBits.push((_laps.length-(bestLap?1:0))+(_laps.length-1===1?' other lap':' other laps'));
  document.getElementById('hero-best-sub').textContent = bestLap
    ? 'Best lap · L'+(bestLap.lap_number+1)+' of '+_laps.length
    : 'Best lap';

  // Gap to theoretical (if we have track-level theoretical and a best lap)
  if(_theo && _theo.theoretical_best_s && best){
    const gap = best - _theo.theoretical_best_s;
    if(gap > 0.001){
      const gapEl=document.getElementById('hero-gap');
      gapEl.textContent = '+'+gap.toFixed(3)+'s';
      gapEl.style.display='';
      document.getElementById('hero-gap-sub').style.display='';
    }
  }

  // Sector deltas vs theoretical (use the BEST lap's sectors)
  if(bestLap && _theo && bestLap.s1_time_s!=null && _theo.theoretical_s1_s!=null){
    const renderS=(elId, lapS, theoS)=>{
      const d = lapS - theoS;
      const el = document.getElementById(elId);
      el.textContent = fmtDelta(d);
      el.classList.remove('faster','slower');
      if(d < -0.005) el.classList.add('faster');
      else if(d > 0.005) el.classList.add('slower');
    };
    renderS('hero-s1', bestLap.s1_time_s, _theo.theoretical_s1_s);
    renderS('hero-s2', bestLap.s2_time_s, _theo.theoretical_s2_s);
    renderS('hero-s3', bestLap.s3_time_s, _theo.theoretical_s3_s);
    document.getElementById('hero-sectors').style.display='';
  }
}

function renderProfile(){
  // Session-level aggregates: mean of per-lap means/maxes. Excludes laps
  // with no data. If no valid lap aggregates exist, hide the strip.
  const valid = _laps.filter(l => l.avg_throttle != null);
  if(!valid.length) return;
  const mean = (key) => {
    const xs = valid.map(l=>l[key]).filter(v=>v!=null);
    if(!xs.length) return null;
    return xs.reduce((a,b)=>a+b,0)/xs.length;
  };
  const max = (key) => {
    const xs = valid.map(l=>l[key]).filter(v=>v!=null);
    if(!xs.length) return null;
    return Math.max(...xs);
  };
  const thr = mean('avg_throttle');
  const brk = mean('avg_brake');
  const slip = mean('avg_slip');
  const pslip = max('peak_slip');
  const above = mean('slip_above_pct');

  const set = (vid, bid, val, fmt, barPct) => {
    if(val == null) return;
    document.getElementById(vid).textContent = fmt(val);
    document.getElementById(bid).style.width = Math.max(0, Math.min(100, barPct)) + '%';
  };
  set('prof-thr',   'prof-thr-bar',   thr,   v=>v.toFixed(0)+'%',         thr);
  set('prof-brk',   'prof-brk-bar',   brk,   v=>v.toFixed(0)+'%',         brk);
  // Slip is unitless 0–1ish; scale to a 0.5 max for the bar visualization
  set('prof-slip',  'prof-slip-bar',  slip,  v=>v.toFixed(2),             slip != null ? slip*200 : 0);
  set('prof-pslip', 'prof-pslip-bar', pslip, v=>v.toFixed(2),             pslip != null ? pslip*200 : 0);
  set('prof-above', 'prof-above-bar', above, v=>v.toFixed(0)+'% of lap',  above);

  document.getElementById('profile').style.display='';
}

function attachSortHandlers(){
  document.querySelectorAll('.lap-table th[data-sort]').forEach(th=>{
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if(_sortKey === key){
        _sortDir = (_sortDir === 'asc') ? 'desc' : 'asc';
      } else {
        _sortKey = key;
        _sortDir = (key === 'lap') ? 'asc' : 'asc';  // ascending default
      }
      renderLaps();
    });
  });
}

function renderLaps(){
  const best = _sess.best_lap_time_s;
  // Sort
  const keyFn = (l) => {
    switch(_sortKey){
      case 'lap':  return l.lap_number != null ? l.lap_number : Infinity;
      case 'time': return l.lap_time_s != null ? l.lap_time_s : Infinity;
      case 's1':   return l.s1_time_s != null ? l.s1_time_s : Infinity;
      case 's2':   return l.s2_time_s != null ? l.s2_time_s : Infinity;
      case 's3':   return l.s3_time_s != null ? l.s3_time_s : Infinity;
      default:     return 0;
    }
  };
  const sorted = [..._laps].sort((a,b)=>{
    const ka = keyFn(a), kb = keyFn(b);
    if(ka === kb) return 0;
    return _sortDir === 'asc' ? (ka < kb ? -1 : 1) : (ka > kb ? -1 : 1);
  });

  // Sector deltas are vs THIS SESSION's best sectors (not vs theoretical)
  const bestLap = _laps.find(l => l.lap_time_s != null && best != null && Math.abs(l.lap_time_s - best) < 0.001);
  const bs1 = bestLap ? bestLap.s1_time_s : null;
  const bs2 = bestLap ? bestLap.s2_time_s : null;
  const bs3 = bestLap ? bestLap.s3_time_s : null;

  // Tag heuristics: lap 0 (Forza first lap) = out-lap if its time is wildly slower
  const validTimes = _laps.filter(l => l.lap_time_s).map(l => l.lap_time_s).sort((a,b)=>a-b);
  const median = validTimes.length ? validTimes[Math.floor(validTimes.length/2)] : null;
  const isOutOrInLap = (l) => {
    if(!median || !l.lap_time_s) return null;
    if(l.lap_time_s > median * 1.4){
      // Heuristic: first lap of the list = out, last lap = in
      const idx = _laps.indexOf(l);
      if(idx === 0) return 'Out';
      if(idx === _laps.length - 1) return 'In';
    }
    return null;
  };

  const tbody = document.getElementById('lap-tbody');
  tbody.innerHTML = sorted.map(l => {
    const isBest = best && l.lap_time_s && Math.abs(l.lap_time_s - best) < 0.001;
    const rowCls = isBest ? 'best' : '';
    const lapNum = l.lap_number != null ? 'L'+(l.lap_number+1) : '—';
    const tag = isOutOrInLap(l);
    const tagHtml = tag ? `<span class="tag tag-${tag.toLowerCase()}">${tag}</span>` : '';

    const sCell = (lapVal, bestVal) => {
      if(isBest) return '<span class="delta-zero">—</span>';
      if(lapVal == null || bestVal == null) return '<span class="delta-zero">—</span>';
      const d = lapVal - bestVal;
      const sign = d > 0 ? '+' : '';
      const cls = d > 0 ? 'delta-pos' : (d < 0 ? 'delta-neg' : 'delta-zero');
      return `<span class="${cls}">${sign}${d.toFixed(2)}</span>`;
    };

    const lapHref = '/sessions/telemetry?id='+encodeURIComponent(_id)+'&lap='+(l.lap_number != null ? l.lap_number : '');
    const sgame = _sgame || (_sess && _sess.game) || '';
    const fullHref = sgame ? lapHref + '&game=' + encodeURIComponent(sgame) : lapHref;

    return `<tr class="${rowCls}" onclick="location.href='${fullHref}'">
      <td>${lapNum}</td>
      <td>${fmtLap(l.lap_time_s)}</td>
      <td>${sCell(l.s1_time_s, bs1)}</td>
      <td>${sCell(l.s2_time_s, bs2)}</td>
      <td>${sCell(l.s3_time_s, bs3)}</td>
      <td>${tagHtml}</td>
    </tr>`;
  }).join('');

  // Sort indicators
  document.querySelectorAll('.lap-table th[data-sort]').forEach(th => {
    th.classList.remove('sorted');
    const ind = th.querySelector('.sort-ind');
    if(!ind) return;
    if(th.dataset.sort === _sortKey){
      th.classList.add('sorted');
      ind.textContent = _sortDir === 'asc' ? '▲' : '▼';
    } else {
      ind.textContent = '⇕';
    }
  });
}

function renderCards(){
  const s = _sess;

  // Card A — Where you lost time (simplified: slowest sector vs theoretical)
  // The full top-3 corner-window detector is a separate spec (Mistakes &
  // Events). Until that ships, surface the cheapest meaningful insight:
  // which sector left the most time on the table, with its gap value.
  const bestLap = _laps.find(l => l.lap_time_s != null && s.best_lap_time_s != null && Math.abs(l.lap_time_s - s.best_lap_time_s) < 0.001);
  if(bestLap && _theo && bestLap.s1_time_s != null){
    const gaps = [
      {name:'S1', d: bestLap.s1_time_s - (_theo.theoretical_s1_s||bestLap.s1_time_s)},
      {name:'S2', d: bestLap.s2_time_s - (_theo.theoretical_s2_s||bestLap.s2_time_s)},
      {name:'S3', d: bestLap.s3_time_s - (_theo.theoretical_s3_s||bestLap.s3_time_s)},
    ].filter(g => g.d > 0);
    if(gaps.length){
      gaps.sort((a,b)=>b.d-a.d);
      const worst = gaps[0];
      const totalGap = gaps.reduce((a,b)=>a+b.d,0);
      document.getElementById('card-loss-headline').innerHTML =
        `<em>${worst.name}</em> cost you ${worst.d.toFixed(2)}s`;
      document.getElementById('card-loss-body').innerHTML =
        gaps.map(g => `<span class="card-corner">${g.name} +${g.d.toFixed(2)}</span>`).join('');
      const teleHref = '/sessions/telemetry?id='+encodeURIComponent(_id);
      document.getElementById('card-loss-link').href = teleHref;
    } else {
      document.getElementById('card-loss-headline').textContent = 'On theoretical pace across all sectors';
      document.getElementById('card-loss-body').textContent = 'Your best lap matched or beat every personal-best sector.';
      document.getElementById('card-loss-link').style.display='none';
    }
  } else {
    document.getElementById('card-loss-headline').textContent = 'Not enough sector data yet';
    document.getElementById('card-loss-body').textContent = 'Sector splits appear after the first complete lap is recorded.';
    document.getElementById('card-loss-link').style.display='none';
  }

  // Card B — Car context
  if(_carCtx && _carCtx.rank_in_car != null){
    const rank = _carCtx.rank_in_car;
    const total = _carCtx.total_in_car;
    const ord = (n) => {
      if(n === 1) return '1st';
      if(n === 2) return '2nd';
      if(n === 3) return '3rd';
      return n + 'th';
    };
    const carText = s.car_nickname || s.car || 'this car';
    document.getElementById('card-car-headline').innerHTML =
      `Your <em>${ord(rank)}-best</em> of ${total} session${total===1?'':'s'} in this car`;
    const bh = _carCtx.best_in_car_at_track;
    if(bh && bh.best_lap_time_s){
      const dt = bh.started_at ? new Date(bh.started_at).toLocaleDateString([],{month:'short',day:'numeric',year:'numeric'}) : '';
      document.getElementById('card-car-body').innerHTML =
        `Best ever in ${carText} at ${s.track}:<br>` +
        `<strong style="color:var(--color-text-primary)">${fmtLap(bh.best_lap_time_s)}</strong>${dt?' — '+dt:''}`;
    } else {
      document.getElementById('card-car-body').textContent = `First session in this car at ${s.track}.`;
    }
    if(s.car_ordinal != null){
      const link = document.getElementById('card-car-link');
      link.href = '/cars/' + s.car_ordinal;
      link.style.display = '';
    }
  } else {
    document.getElementById('card-car-headline').textContent = 'No car context yet';
    document.getElementById('card-car-body').textContent = 'Car identification is unavailable for this session.';
  }
}

function renderAI(){
  const s = _sess;
  if(s.ai_analysis){
    const body = document.getElementById('card-ai-body');
    body.textContent = s.ai_analysis;
    body.style.display = 'block';
    document.getElementById('btn-analyze').style.display = 'none';
    document.getElementById('btn-re').style.display = 'inline-block';
    if(s.ai_analyzed_at){
      const dt = new Date(s.ai_analyzed_at).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
      document.getElementById('ai-meta').textContent = 'Cached · '+dt+(s.ai_model?' · '+s.ai_model:'');
    }
  }
}

async function runAnalysis(force){
  const btn = document.getElementById('btn-analyze');
  const rbtn = document.getElementById('btn-re');
  const body = document.getElementById('card-ai-body');
  const meta = document.getElementById('ai-meta');
  const err = document.getElementById('ai-err');
  err.style.display = 'none';
  btn.disabled = true; rbtn.disabled = true;
  if(force){rbtn.textContent = 'Analyzing…';} else {btn.textContent = 'Analyzing…';}
  try{
    const r = await fetch('/analyze?id='+encodeURIComponent(_id)+(force?'&force=true':''));
    const d = await r.json();
    if(!r.ok) throw new Error(d.error || 'Unknown error');
    body.textContent = d.analysis; body.style.display = 'block';
    btn.style.display = 'none';
    rbtn.style.display = 'inline-block'; rbtn.textContent = 'Re-analyze'; rbtn.disabled = false;
    if(d.analyzed_at){
      const dt = new Date(d.analyzed_at).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
      meta.textContent = 'Analyzed '+dt+(d.model?' · '+d.model:'');
    }
  } catch(e){
    err.textContent = '✗ '+e.message; err.style.display = 'block';
    btn.disabled = false; btn.textContent = 'Analyze with Claude';
    rbtn.disabled = false; if(!_sess.ai_analysis) rbtn.style.display = 'none';
  }
}

// ── Edit modal (unchanged from prior implementation) ─────────────────
let _editTrack='',_editRaceType=null,_editWeather='Dry',_editTyre=null;
let _trackAc=null, _carAc=null;

async function openEdit(){
  if(!_sess)return;
  const cur = _sess.track && _sess.track !== 'unknown' ? _sess.track : '';
  let tracks;
  try{
    tracks = await fetch('/sessions/track-options').then(r=>r.json());
    if(!Array.isArray(tracks) || !tracks.length) tracks = TRACK_NAMES;
  } catch(e){tracks = TRACK_NAMES;}
  if(cur && !tracks.includes(cur)) tracks = [...tracks, cur].sort();
  const trackInput = document.getElementById('edit-track');
  if(!_trackAc){
    _trackAc = Autocomplete.attach(trackInput, {options: tracks, allowFreeText: true, initialValue: cur});
  } else {
    _trackAc.setOptions(tracks);
    trackInput.value = cur;
  }
  const carInput = document.getElementById('edit-car');
  const carInitial = (_sess.car && _sess.car !== 'unknown') ? _sess.car : '';
  if(!_carAc){
    _carAc = Autocomplete.attach(carInput, {options: (typeof CAR_CATALOG!=='undefined') ? CAR_CATALOG : [], allowFreeText: true, initialValue: carInitial});
  } else {
    carInput.value = carInitial;
  }
  const nickRow = document.getElementById('edit-nickname-row');
  const nickInput = document.getElementById('edit-nickname');
  if(_sess.car_ordinal != null){
    nickRow.style.display = '';
    nickInput.value = _sess.car_nickname || '';
  } else {
    nickRow.style.display = 'none';
    nickInput.value = '';
  }
  document.getElementById('edit-grid').value   = _sess.grid_pos   != null ? _sess.grid_pos   : '';
  document.getElementById('edit-finish').value = _sess.finish_pos != null ? _sess.finish_pos : '';
  _editTrack = cur;
  _editRaceType = _sess.race_type || _sess.session_type || null;
  _editWeather = _sess.weather_condition || 'Dry';
  _editTyre = _sess.tyre_compound || null;
  document.querySelectorAll('#edit-ovl .edit-chips').forEach(g=>g.querySelectorAll('.etype').forEach(c=>c.classList.remove('sel')));
  document.querySelectorAll('#edit-ovl .edit-row .edit-chips .etype').forEach(c=>{
    if(c.dataset.val === _editRaceType && c.parentElement.id !== 'edit-weather-chips' && c.parentElement.id !== 'edit-tyre-chips') c.classList.add('sel');
  });
  document.querySelectorAll('#edit-weather-chips .etype').forEach(c=>c.classList.toggle('sel', c.dataset.val === _editWeather));
  document.querySelectorAll('#edit-tyre-chips .etype').forEach(c=>c.classList.toggle('sel', c.dataset.val === _editTyre));
  const tt = _sess.track_temp_c, at = _sess.air_temp_c;
  const condEl = document.getElementById('edit-conditions');
  const condRow = document.getElementById('edit-conditions-row');
  if(tt != null || at != null){
    const parts = [];
    if(tt != null) parts.push(`Track: ${tt.toFixed(0)}°C`);
    if(at != null) parts.push(`Air: ${at.toFixed(0)}°C`);
    condEl.textContent = parts.join(' · ');
    condRow.style.display = '';
  } else {
    condRow.style.display = 'none';
  }
  document.getElementById('edit-ovl').classList.add('open');
}

function closeEdit(){document.getElementById('edit-ovl').classList.remove('open');}

async function deleteSession(){
  if(!_id) return;
  const trackHint = (_sess && _sess.track && _sess.track !== 'unknown') ? _sess.track : 'this session';
  const ok = window.confirm(
    'Permanently delete '+trackHint+'?\n\n'+
    'This removes the session, its lap data, raw archive, and any AI analysis. There is no undo.'
  );
  if(!ok) return;
  try{
    const res = await fetch('/sessions/delete', {method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify({id: _id})});
    if(!res.ok) throw new Error('HTTP '+res.status);
    location.href = '/sessions';
  } catch(e){
    alert('Could not delete session: '+(e && e.message || e));
  }
}

function editSelType(el){
  el.parentElement.querySelectorAll('.etype').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  _editRaceType = el.dataset.val;
}
function editSelWeather(el){
  el.parentElement.querySelectorAll('.etype').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  _editWeather = el.dataset.val;
}
function editSelTyre(el){
  if(el.classList.contains('sel')){el.classList.remove('sel'); _editTyre = null; return;}
  el.parentElement.querySelectorAll('.etype').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  _editTyre = el.dataset.val;
}

async function saveEdit(){
  if(!_id) return;
  const body = {id: _id};
  const track = document.getElementById('edit-track').value.trim();
  if(track) body.track = track;
  if(_editRaceType) body.race_type = _editRaceType;
  if(track && _sess.track_ordinal && track !== _sess.track){
    body.learned_ordinal = {ordinal: _sess.track_ordinal, game: _sess.game || 'forza_motorsport', track_name: track};
  }
  body.weather_condition = _editWeather || '';
  body.tyre_compound = _editTyre || '';
  const car = document.getElementById('edit-car').value.trim();
  body.car = car;
  const gp = document.getElementById('edit-grid').value.trim();
  const fp = document.getElementById('edit-finish').value.trim();
  body.grid_pos   = gp ? parseInt(gp, 10) : null;
  body.finish_pos = fp ? parseInt(fp, 10) : null;
  if(Number.isNaN(body.grid_pos))   body.grid_pos = null;
  if(Number.isNaN(body.finish_pos)) body.finish_pos = null;
  await fetch('/sessions/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(_sess.car_ordinal != null){
    const nick = document.getElementById('edit-nickname').value.trim();
    if(nick !== (_sess.car_nickname || '')){
      await fetch('/cars/nickname',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ordinal: _sess.car_ordinal, nickname: nick})});
    }
  }
  closeEdit();
  const d = await fetch('/sessions/session/data?id='+encodeURIComponent(_id)).then(r=>r.json());
  if(d.session){
    _sess = d.session; _laps = d.laps || []; _theo = d.theoretical || null; _carCtx = d.car_context || null;
    renderCrumbAndNav();
    renderHeader();
    renderHero();
    renderProfile();
    renderLaps();
    renderCards();
    loadHeroDelta();
  }
}

init();
