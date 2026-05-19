// Sessions — filter mechanism over every recorded session.
// Multi-select dropdown facets (count badge on the button, per-category
// clear, global clear). The Circuit dropdown enriches each option with
// best lap + a progression sparkline + improving/regressing icon.
// Column-header sort. URL-addressable. See docs/specs/ia.md.

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
let _tix = new Map();          // track name → {best_lap_time_s, spark_laps, trend}
let _openF = null;             // which facet dropdown panel is open
// Multi-select: each facet is an array of string values; [] = no filter.
const F = {car:[], track:[], cond:[], type:[], review:false};
const SORT_KEYS = ['date','track','car','lap'];
function defaultDir(k){ return k==='date' ? 'desc' : 'asc'; }
let SORT = {key:'date', dir:'desc'};

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

function sortRows(rows){
  const k = SORT.key, mul = SORT.dir === 'asc' ? 1 : -1;
  const val = s =>
    k==='date'  ? (s.started_at || '') :
    k==='track' ? (s.track || '').toLowerCase() :
    k==='car'   ? carName(s).toLowerCase() :
                  (s.best_lap_time_s == null ? Infinity : s.best_lap_time_s);
  return rows.slice().sort((a,b)=>{
    const x = val(a), y = val(b);
    if(k==='lap'){ if(x===Infinity && y!==Infinity) return 1;
                   if(y===Infinity && x!==Infinity) return -1; }
    return x < y ? -1*mul : x > y ? 1*mul : 0;
  });
}

const FACETS = ['car','track','cond','type'];
function readURL(){
  const q = new URLSearchParams(location.search);
  FACETS.forEach(g => { const v=q.get(g); F[g] = v ? v.split(',').filter(Boolean) : []; });
  F.review = q.get('review') === '1' ? '1' : false;
  const k = q.get('sort');
  SORT.key = SORT_KEYS.indexOf(k) >= 0 ? k : 'date';
  SORT.dir = (q.get('dir') === 'asc' || q.get('dir') === 'desc')
    ? q.get('dir') : defaultDir(SORT.key);
}
function writeURL(){
  const q = new URLSearchParams();
  FACETS.forEach(g => { if(F[g].length) q.set(g, F[g].join(',')); });
  if(F.review) q.set('review', '1');
  if(SORT.key !== 'date' || SORT.dir !== 'desc'){ q.set('sort', SORT.key); q.set('dir', SORT.dir); }
  const s = q.toString();
  history.replaceState(null, '', s ? '?' + s : location.pathname);
}

function facetVal(s, g){
  return g==='car'  ? String(s.car_ordinal) :
         g==='track'? s.track :
         g==='cond' ? s.weather_condition : typeOf(s);
}
function match(s){
  for(const g of FACETS){
    if(F[g].length && F[g].indexOf(String(facetVal(s,g))) < 0) return false;
  }
  if(F.review && !needsReview(s)) return false;
  return true;
}
function anyFilter(){ return F.review || FACETS.some(g => F[g].length); }

function uniq(getKey, getLabel){
  const m = new Map();
  _all.forEach(s => { const k = getKey(s); if(k==null||k==='') return;
    if(!m.has(String(k))) m.set(String(k), {val:String(k), label:getLabel(s), n:0});
    m.get(String(k)).n++; });
  return [...m.values()].sort((a,b)=>b.n-a.n);
}

// Progression sparkline from a circuit's chronological best laps. Lower
// time = faster, so a falling line = improving; coloured by trend.
function spark(vals, trend){
  if(!vals || vals.length < 2) return '';
  const w=58, h=16, mn=Math.min(...vals), mx=Math.max(...vals), rng=(mx-mn)||1;
  const col = trend==='up' ? '#22c55e' : trend==='dn' ? '#ef4444' : '#7a7a80';
  const pts = vals.map((v,i)=>{
    const x = (i/(vals.length-1))*w;
    const y = h - ((v-mn)/rng)*h;   // lower time → higher on chart
    return x.toFixed(1)+','+y.toFixed(1);
  }).join(' ');
  return `<svg class="fsp" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" preserveAspectRatio="none">`+
         `<polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.5"/></svg>`;
}
function trendIcon(t){
  if(t==='up') return '<span class="ftr up" title="Improving">▲</span>';
  if(t==='dn') return '<span class="ftr dn" title="Regressing">▼</span>';
  return '<span class="ftr fl" title="Flat">—</span>';
}

function dropdown(label, g, opts, rich){
  const sel = F[g];
  const head = `<button class="fdrop-btn${sel.length?' on':''}" data-fd="${g}">`+
    `${label}${sel.length?` <span class="fct">${sel.length}</span>`:''} <span class="fcar">▾</span></button>`;
  const rows = opts.map(o=>{
    const on = sel.indexOf(o.val) >= 0;
    let extra = '';
    if(rich){
      const t = _tix.get(o.val) || {};
      extra = `<span class="fbest">${fmtLap(t.best_lap_time_s)}</span>`+
              `${spark(t.spark_laps, t.trend)}${trendIcon(t.trend)}`;
    }
    return `<button class="fopt${on?' on':''}${rich?' rich':''}" data-g="${g}" data-v="${esc(o.val)}">`+
      `<span class="fck">${on?'✓':''}</span>`+
      `<span class="fnm">${esc(o.label)}</span>`+
      `<span class="fn">${o.n}</span>${extra}</button>`;
  }).join('');
  // Typeahead when the list is long (circuits especially).
  const srch = opts.length > 8
    ? `<input class="fsrch" placeholder="Filter ${label.toLowerCase()}…" autocomplete="off">` : '';
  return `<div class="fdrop${rich?' rich':''}${_openF===g?' open':''}">${head}`+
    `<div class="fdrop-panel">`+
      `<div class="fdrop-top"><span>${label}</span>`+
      `<button class="fclear" data-fc="${g}"${sel.length?'':' disabled'}>Clear</button></div>`+
      `${srch}`+
      `<div class="fdrop-list">${rows||'<div class="fempty">None</div>'}</div>`+
    `</div></div>`;
}

function render(){ renderFilters(); renderTable(); }

function renderFilters(){
  const cars   = uniq(s=>s.car_ordinal, s=>carName(s));
  const tracks = uniq(s=>s.track, s=>s.track);
  const conds  = uniq(s=>s.weather_condition, s=>s.weather_condition);
  const types  = uniq(s=>typeOf(s), s=>TYPE_LABELS[typeOf(s)]||typeOf(s));

  const revN = _all.filter(needsReview).length;
  const swtOn = F.review === '1';
  const toggle = revN ? `<label class="swt${swtOn?' on':''}">`+
    `<input type="checkbox" id="rev-t"${swtOn?' checked':''}>`+
    `<span class="tr"></span>Needs review (${revN})</label>` : '';

  // clear-all stays in the DOM (display-toggled) so an option click can
  // sync it in place without rebuilding — keeps the open panel/scroll.
  document.getElementById('filters').innerHTML =
    dropdown('Car','car',cars) + dropdown('Circuit','track',tracks,true) +
    dropdown('Condition','cond',conds) + dropdown('Type','type',types) +
    `<button class="fclear-all" style="${anyFilter()?'':'display:none'}">Clear all</button>` +
    toggle;
}

function renderTable(){
  // Sort IS the table header — column order = header order.
  const ar = SORT.dir === 'asc' ? '▲' : '▼';
  const th = (k,label,num) =>
    `<th data-k="${k}" class="${num?'num ':''}${SORT.key===k?'on':''}">${label}`+
    `${SORT.key===k?`<span class="ar">${ar}</span>`:''}</th>`;
  document.getElementById('sess-head').innerHTML =
    `<tr>${th('track','Circuit')}${th('car','Car')}`+
    `${th('lap','Best lap',true)}${th('date','Date',true)}</tr>`;

  let rows = sortRows(_all.filter(match));
  document.getElementById('sess-sub').textContent =
    rows.length === _all.length
      ? `${_all.length} session${_all.length===1?'':'s'}`
      : `${rows.length} of ${_all.length} sessions`;

  const list = document.getElementById('sess-list');
  if(!rows.length){ list.innerHTML = '<tr><td colspan="4" class="c-empty">No sessions match this filter.</td></tr>'; return; }
  list.innerHTML = rows.map(s=>{
    const href = '/sessions/session?id='+encodeURIComponent(s.session_id)
      + (s.game?'&game='+encodeURIComponent(s.game):'')
      + (s.track?'&track='+encodeURIComponent(s.track):'');
    const cc = pfCarClass(s.car_pi, s.car_class);
    const badge = cc ? ` <span class="class-badge">${cc}</span>` : '';
    const t = typeOf(s); const tl = t ? (TYPE_LABELS[t]||t) : '';
    const cond = [s.weather_condition, s.tyre_compound].filter(Boolean).join(' · ');
    const sub = [tl, cond].filter(Boolean).join(' &middot; ');
    return `<tr onclick="location.href='${href}'">`+
      `<td><div class="c-name">${esc(s.track||'Unknown Circuit')}</div>`+
      `${sub?`<div class="c-sub">${sub}</div>`:''}</td>`+
      `<td>${esc(carName(s))}${badge}</td>`+
      `<td class="num">${fmtLap(s.best_lap_time_s)}</td>`+
      `<td class="num">${fmtD(s.started_at)} <span style="opacity:.6">${fmtT(s.started_at)}</span></td>`+
      `</tr>`;
  }).join('');
}

// In-place sync so an option/clear click never rebuilds #filters —
// the open panel keeps its scroll position and typeahead text.
function syncDropBtn(drop, g){
  const dbtn = drop.querySelector('.fdrop-btn');
  dbtn.classList.toggle('on', F[g].length > 0);
  let ct = dbtn.querySelector('.fct');
  if(F[g].length){
    if(!ct){ ct = document.createElement('span'); ct.className = 'fct';
      dbtn.insertBefore(ct, dbtn.querySelector('.fcar')); }
    ct.textContent = F[g].length;
  } else if(ct){ ct.remove(); }
  const clr = drop.querySelector('.fclear'); if(clr) clr.disabled = !F[g].length;
}
function syncClearAll(){
  const b = document.querySelector('.fclear-all');
  if(b) b.style.display = anyFilter() ? '' : 'none';
}

document.addEventListener('click', e=>{
  const opt = e.target.closest('.fopt');
  if(opt){
    const g=opt.dataset.g, v=opt.dataset.v;
    const i=F[g].indexOf(v), now=i<0;
    if(now) F[g].push(v); else F[g].splice(i,1);
    opt.classList.toggle('on', now);
    opt.querySelector('.fck').textContent = now ? '✓' : '';
    syncDropBtn(opt.closest('.fdrop'), g);
    syncClearAll(); writeURL(); renderTable();
    return;
  }
  const fc = e.target.closest('.fclear');
  if(fc){
    if(!fc.disabled){
      const g=fc.dataset.fc, drop=fc.closest('.fdrop');
      F[g]=[];
      drop.querySelectorAll('.fopt.on').forEach(o=>{
        o.classList.remove('on'); o.querySelector('.fck').textContent=''; });
      syncDropBtn(drop,g); syncClearAll(); writeURL(); renderTable();
    }
    return;
  }
  if(e.target.closest('.fclear-all')){
    FACETS.forEach(g=>F[g]=[]); F.review=false; _openF=null; writeURL(); render(); return; }
  const fd = e.target.closest('.fdrop-btn');
  if(fd){ _openF = (_openF===fd.dataset.fd) ? null : fd.dataset.fd; render(); return; }
  const h = e.target.closest('.stbl th[data-k]');
  if(h){ const k=h.dataset.k;
    if(SORT.key===k) SORT.dir = SORT.dir==='asc' ? 'desc' : 'asc';
    else { SORT.key=k; SORT.dir=defaultDir(k); }
    writeURL(); renderTable(); return; }
  // Click outside an open panel closes it.
  if(_openF && !e.target.closest('.fdrop-panel') && !e.target.closest('.fdrop-btn')){
    _openF=null; render(); }
});
document.addEventListener('input', e=>{
  if(e.target.classList.contains('fsrch')){
    const q = e.target.value.trim().toLowerCase();
    e.target.closest('.fdrop-panel').querySelectorAll('.fopt').forEach(o=>{
      const nm = o.querySelector('.fnm').textContent.toLowerCase();
      o.style.display = (!q || nm.indexOf(q) >= 0) ? '' : 'none';
    });
  }
});
document.addEventListener('change', e=>{
  if(e.target.id==='rev-t'){ F.review = e.target.checked ? '1' : false; writeURL(); renderTable(); }
});

(async function init(){
  readURL();
  try{
    const [sess, tix] = await Promise.all([
      fetch('/sessions/data?limit=2000').then(r=>r.json()),
      fetch('/sessions/tracks').then(r=>r.json()).catch(()=>[]),
    ]);
    _all = sess || [];
    (tix||[]).forEach(t=>_tix.set(t.track, t));
  }catch(e){ document.getElementById('sess-sub').textContent='Failed to load.'; return; }
  // Mark these sessions as "seen" — the rail's "N new" badge reads
  // from this marker. Seeds on first-ever load so day one isn't noisy.
  if(_all.length){
    const newest = _all.map(s=>s.started_at||'').sort().slice(-1)[0];
    if(newest) localStorage.setItem('pf-last-seen-sessions', newest);
  }
  render();
})();
