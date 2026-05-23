// Circuits index page — /circuits
// Lists every circuit driven, most-recent first. Rows link into the
// per-circuit detail. Data from /sessions/tracks (bare list).

function fmtLap(s){if(s == null) return '—'; const m = Math.floor(s/60); return m+':'+(s%60).toFixed(3).padStart(6,'0');}
function fmtRelative(iso){
  if(!iso) return '—';
  const dt = new Date(iso);
  const days = Math.floor((Date.now() - dt.getTime()) / 86400000);
  if(days < 1) return 'today';
  if(days === 1) return '1 day ago';
  if(days < 30) return days + ' days ago';
  const months = Math.floor(days / 30);
  if(months === 1) return '1 month ago';
  if(months < 12) return months + ' months ago';
  return Math.floor(months / 12) + ' year' + (Math.floor(months/12) === 1 ? '' : 's') + ' ago';
}
function escapeHtml(s){
  if(s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

async function init(){
  let tracks;
  try{tracks = await fetch('/sessions/tracks').then(r => r.json());}
  catch(e){document.getElementById('circuits-subtitle').textContent = 'Failed to load circuits.'; return;}
  tracks = tracks || [];
  document.getElementById('circuits-subtitle').textContent =
    tracks.length + ' circuit' + (tracks.length === 1 ? '' : 's') + ' driven';
  document.getElementById('circuits-count').textContent =
    tracks.length + (tracks.length === 1 ? ' circuit' : ' circuits');
  render(tracks);
}

function render(tracks){
  const list = document.getElementById('circuits-list');
  if(!tracks.length){
    list.innerHTML = '<div class="empty">No circuits driven yet.</div>';
    return;
  }
  list.innerHTML = tracks.map(t => {
    const href = '/sessions/track?name=' + encodeURIComponent(t.track);
    const name = (t.track === 'unknown' || !t.track) ? 'Unknown Circuit' : t.track;
    const sc = t.session_count || 0;
    const meta = sc + ' session' + (sc === 1 ? '' : 's')
      + (t.best_car ? ' · best in ' + escapeHtml(t.best_car) : '');
    const outAttr = (t.pb_session_id && t.pb_lap_number != null)
      ? ` data-sid="${escapeHtml(t.pb_session_id)}" data-lap="${t.pb_lap_number}"` : '';
    return `<a href="${href}" class="track-row">
      <div class="track-outline"${outAttr}></div>
      <div>
        <div class="track-name">${escapeHtml(name)}</div>
        <div class="track-meta">${meta}</div>
      </div>
      <div class="track-pb">${fmtLap(t.best_lap_time_s)}</div>
      <div class="track-sessions">${fmtRelative(t.last_raced)}</div>
      <div class="track-arrow">→</div>
    </a>`;
  }).join('');
  loadOutlines();
}

// Lazy-load the PB lap polyline per row — IntersectionObserver keeps
// fetches off-screen rows quiet until the user scrolls.
async function drawOutline(el){
  const sid = el.dataset.sid, lap = el.dataset.lap;
  if(!sid || lap == null) return;
  let s;
  try{
    s = await fetch('/sessions/lap-samples?session_id=' + encodeURIComponent(sid)
      + '&lap=' + encodeURIComponent(lap)).then(r => r.json());
  }catch(e){ return; }
  if(!s || s.length < 8 || s.some(p => p.px == null)) return;
  const hasPz = s.some(p => p.pz != null);
  const zf = hasPz ? p => p.pz : p => (p.py ?? 0);
  const xs = s.map(p => p.px), zs = s.map(zf);
  const mnX = Math.min(...xs), mxX = Math.max(...xs);
  const mnZ = Math.min(...zs), mxZ = Math.max(...zs);
  const W = 100, H = 75, pd = 4;
  const sc = Math.min((W - pd*2)/((mxX - mnX) || 1), (H - pd*2)/((mxZ - mnZ) || 1));
  const ox = (W - (mxX - mnX) * sc) / 2;
  const oz = (H - (mxZ - mnZ) * sc) / 2;
  const cx = x => (ox + (x - mnX) * sc).toFixed(1);
  const cy = z => (H - oz - (z - mnZ) * sc).toFixed(1);
  const step = Math.max(1, Math.floor(s.length / 80));
  const pts = [];
  for(let i = 0; i < s.length; i += step) pts.push(cx(s[i].px) + ',' + cy(zf(s[i])));
  pts.push(cx(s[0].px) + ',' + cy(zf(s[0])));
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Track outline">`+
    `<polyline class="tm-line" points="${pts.join(' ')}"/></svg>`;
}
function loadOutlines(){
  const els = document.querySelectorAll('.track-outline[data-sid]');
  if(!('IntersectionObserver' in window)){ els.forEach(drawOutline); return; }
  const io = new IntersectionObserver((entries, obs) => {
    entries.forEach(e => {
      if(e.isIntersecting){ obs.unobserve(e.target); drawOutline(e.target); }
    });
  }, {rootMargin: '200px 0px'});
  els.forEach(el => io.observe(el));
}

init();
