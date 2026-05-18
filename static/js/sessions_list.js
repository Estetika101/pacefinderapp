// Sessions — filter mechanism over every recorded session.
// H1 stays "Sessions"; chips narrow all → the slice. URL-addressable.
// Recent default; Fastest unlocks only when exactly one Track is
// selected (lap time isn't comparable across circuits). See ia.md.

const TYPE_LABELS = {practice:'Practice',time_trial:'Time Trial',qualifying:'Qualifying',race:'Race',race_ai:'AI Race',race_online:'Online Race',hot_lap:'Hot Lap',real:'Race',ai:'AI Race'};
function fmtLap(s){if(s==null)return '—';const m=Math.floor(s/60);return m+':'+(s%60).toFixed(3).padStart(6,'0');}
function fmtD(iso){if(!iso)return '—';return new Date(iso).toLocaleDateString([],{month:'short',day:'numeric',year:'numeric'});}
function fmtT(iso){if(!iso)return '';return new Date(iso).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}
function esc(s){return s==null?'':String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function carName(s){
  if(s.car && s.car!=='unknown' && !/^Unknown Car/i.test(s.car)) return s.car;
  if(s.car_ordinal!=null) return 'Car #'+s.car_ordinal;
  return 'Unknown Car';
}
function typeOf(s){ return s.race_type || (s.session_type && s.session_type!=='unknown' ? s.session_type : null); }

let _all = [];
const F = {car:null, track:null, cond:null, type:null, review:false};
let SORT = 'recent';

// Mirror of db/store.py _NEEDS_REVIEW_SQL — keep the two in sync.
const _RACEY = ['race','race_ai','race_online','real','ai'];
function needsReview(s){
  const t = s.track, c = s.car;
  if(t==null || t==='unknown' || /^Track #/.test(t)) return true;
  if(c==null || c==='unknown' || /^Unknown Car/i.test(c)) return true;
  if(s.race_type==null && (s.session_type==null || s.session_type==='unknown')) return true;
  const racey = _RACEY.indexOf(s.race_type)>=0 || s.session_type==='race';
  if(racey && (s.grid_pos==null || s.finish_pos==null)) return true;
  return false;
}

function readURL(){
  const q = new URLSearchParams(location.search);
  F.car = q.get('car'); F.track = q.get('track');
  F.cond = q.get('cond'); F.type = q.get('type');
  F.review = q.get('review') === '1' ? '1' : false;
  SORT = q.get('sort') === 'fastest' ? 'fastest' : 'recent';
}
function writeURL(){
  const q = new URLSearchParams();
  if(F.car) q.set('car', F.car);
  if(F.track) q.set('track', F.track);
  if(F.cond) q.set('cond', F.cond);
  if(F.type) q.set('type', F.type);
  if(F.review) q.set('review', '1');
  if(SORT === 'fastest') q.set('sort', 'fastest');
  const s = q.toString();
  history.replaceState(null, '', s ? '?' + s : location.pathname);
}

function match(s){
  if(F.car    && String(s.car_ordinal) !== String(F.car)) return false;
  if(F.track  && s.track !== F.track) return false;
  if(F.cond   && s.weather_condition !== F.cond) return false;
  if(F.type   && typeOf(s) !== F.type) return false;
  if(F.review && !needsReview(s)) return false;
  return true;
}

function uniq(getKey, getLabel){
  const m = new Map();
  _all.forEach(s => { const k = getKey(s); if(k==null||k==='') return;
    if(!m.has(String(k))) m.set(String(k), {val:String(k), label:getLabel(s), n:0});
    m.get(String(k)).n++; });
  return [...m.values()].sort((a,b)=>b.n-a.n);
}

function chip(grp, val, label, n){
  const on = String(F[grp]) === String(val);
  return `<button class="chip${on?' on':''}" data-g="${grp}" data-v="${esc(val)}">${esc(label)}<span style="opacity:.6"> ${n}</span></button>`;
}

function render(){
  const cars   = uniq(s=>s.car_ordinal, s=>carName(s));
  const tracks = uniq(s=>s.track, s=>s.track);
  const conds  = uniq(s=>s.weather_condition, s=>s.weather_condition);
  const types  = uniq(s=>typeOf(s), s=>TYPE_LABELS[typeOf(s)]||typeOf(s));

  const revN = _all.filter(needsReview).length;
  const revChip = revN ? `<div class="fgrp"><span class="fl">Flag</span>` +
    `<button class="chip${F.review==='1'?' on':''}" data-g="review" data-v="1">` +
    `Needs review<span style="opacity:.6"> ${revN}</span></button></div>` : '';

  document.getElementById('filters').innerHTML =
    grp('Car', cars, 'car') + grp('Track', tracks, 'track') +
    grp('Cond', conds, 'cond') + grp('Type', types, 'type') + revChip;

  function grp(label, opts, g){
    if(!opts.length) return '';
    return `<div class="fgrp"><span class="fl">${label}</span>` +
      opts.map(o=>chip(g,o.val,o.label,o.n)).join('') + `</div>`;
  }

  const trackOn = !!F.track;
  if(!trackOn && SORT==='fastest') SORT='recent';
  document.getElementById('sortbar').innerHTML =
    `<span>Sort</span><div class="seg">
       <button data-s="recent" class="${SORT==='recent'?'on':''}">Recent</button>
       <button data-s="fastest" class="${SORT==='fastest'?'on':''}" ${trackOn?'':'disabled'}>Fastest</button>
     </div><span class="shint">${trackOn
        ? 'Fastest = leaderboard for this circuit'
        : 'Fastest unlocks when one Track is selected'}</span>`;

  let rows = _all.filter(match);
  if(SORT==='fastest' && trackOn){
    rows = rows.slice().sort((a,b)=>{
      const x=a.best_lap_time_s, y=b.best_lap_time_s;
      if(x==null) return 1; if(y==null) return -1; return x-y;
    });
  }

  document.getElementById('sess-sub').textContent =
    rows.length === _all.length
      ? `${_all.length} session${_all.length===1?'':'s'}`
      : `${rows.length} of ${_all.length} sessions`;

  const list = document.getElementById('sess-list');
  if(!rows.length){ list.innerHTML = '<div class="empty">No sessions match this filter.</div>'; return; }
  list.innerHTML = rows.map(s=>{
    const href = '/sessions/session?id='+encodeURIComponent(s.session_id)
      + (s.game?'&game='+encodeURIComponent(s.game):'')
      + (s.track?'&track='+encodeURIComponent(s.track):'');
    const cc = pfCarClass(s.car_pi, s.car_class);
    const badge = cc ? ` <span class="class-badge">${cc}</span>` : '';
    const t = typeOf(s); const tl = t ? (TYPE_LABELS[t]||t) : '';
    const cond = [s.weather_condition, s.tyre_compound].filter(Boolean).join(' · ');
    const meta = [tl, esc(carName(s))+badge, cond].filter(Boolean).join(' &middot; ');
    return `<a href="${href}" class="track-row">
      <div>
        <div class="track-name">${esc(s.track||'Unknown Circuit')}</div>
        <div class="track-meta">${meta}</div>
      </div>
      <div class="track-pb">${fmtLap(s.best_lap_time_s)}</div>
      <div class="track-sessions">${fmtD(s.started_at)}<br><span style="opacity:.6">${fmtT(s.started_at)}</span></div>
      <div class="track-arrow">→</div>
    </a>`;
  }).join('');
}

document.addEventListener('click', e=>{
  const c = e.target.closest('.chip');
  if(c){ const g=c.dataset.g, v=c.dataset.v;
    F[g] = (String(F[g])===String(v)) ? null : v;
    if(!F.track && SORT==='fastest') SORT='recent';
    writeURL(); render(); return; }
  const sb = e.target.closest('.seg button');
  if(sb && !sb.disabled){ SORT = sb.dataset.s; writeURL(); render(); }
});

(async function init(){
  readURL();
  try{ _all = await fetch('/sessions/data?limit=2000').then(r=>r.json()); }
  catch(e){ document.getElementById('sess-sub').textContent='Failed to load.'; return; }
  _all = _all || [];
  render();
})();
