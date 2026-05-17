// Home page — / (idle landing)
// Fetches /home/data and renders the page. Polls /status every 10 s so
// the recording indicator flips green→red when telemetry starts (the
// driver can then click "Live dashboard" knowing it has a session).

const CLASS_NAMES = {0:'D',1:'C',2:'B',3:'A',4:'S1',5:'S2',6:'X',7:'R',8:'P'};

function fmtLap(s){if(s == null) return '—'; const m = Math.floor(s/60); return m+':'+(s%60).toFixed(3).padStart(6,'0');}
function fmtShortDate(iso){if(!iso) return '—'; return new Date(iso).toLocaleDateString([], {month:'short', day:'numeric'});}
let _tf='24h';  // user time-format pref, set from /home/data
function fmtTime(iso){if(!iso) return ''; return new Date(iso).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', hour12:_tf==='12h'});}
function fmtRelative(iso){
  if(!iso) return '—';
  const dt = new Date(iso);
  const days = Math.floor((Date.now() - dt.getTime()) / 86400000);
  if(days < 1){
    const hours = Math.floor((Date.now() - dt.getTime()) / 3600000);
    if(hours < 1) return 'just now';
    if(hours === 1) return '1 hour ago';
    return hours + ' hours ago';
  }
  if(days === 1) return '1 day ago';
  if(days < 30) return days + ' days ago';
  const months = Math.floor(days / 30);
  if(months === 1) return '1 month ago';
  if(months < 12) return months + ' months ago';
  return Math.floor(months / 12) + ' year' + (Math.floor(months/12) === 1 ? '' : 's') + ' ago';
}
function fmtBytes(gb){
  if(gb == null) return '—';
  if(gb < 1) return (gb * 1024).toFixed(0) + ' MB';
  return gb.toFixed(1) + ' GB';
}
function escapeHtml(s){
  if(s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function carDisplay(s){
  // Priority: nickname > resolved name > "Car #N"
  if(s.car_nickname) return s.car_nickname;
  if(s.car_name)     return s.car_name;
  if(s.car && s.car !== 'unknown' && !/^Unknown Car/i.test(s.car)) return s.car;
  if(s.car_ordinal != null) return 'Car #' + s.car_ordinal;
  return '—';
}

async function init(){
  let d;
  try{d = await fetch('/home/data').then(r => r.json());}
  catch(e){ return; }  // nav.js owns the live status pill
  _tf = d.time_format || '24h';
  renderWelcome(d.last_session, d.stats);
  renderHero(d.last_session, d.pb_at_track_s);
  loadCareer();
  renderTopCircuits(d.top_circuits || []);
  renderTopCars(d.top_cars || []);
  renderRecent(d.recent_sessions || []);
  renderFooter(d.stats);
}

function renderWelcome(last, stats){
  const eyebrow = document.getElementById('welcome-eyebrow');
  if(last && last.started_at && last.track){
    eyebrow.textContent = 'Last drove ' + fmtRelative(last.started_at) + ' · ' + last.track;
  } else if(stats && stats.total_sessions){
    eyebrow.textContent = stats.total_sessions + ' session' + (stats.total_sessions === 1 ? '' : 's') + ' recorded';
  } else {
    eyebrow.textContent = 'No sessions yet';
  }
}

function renderHero(last, pbHere){
  const heroEl = document.getElementById('last-session');
  const emptyEl = document.getElementById('empty-hero');
  if(!last || !last.session_id){
    heroEl.style.display = 'none';
    emptyEl.style.display = '';
    return;
  }
  heroEl.style.display = '';
  emptyEl.style.display = 'none';

  heroEl.href = '/sessions/session?id=' + encodeURIComponent(last.session_id);
  document.getElementById('last-time').textContent = fmtLap(last.best_lap_time_s);

  // Subtitle: "Best lap · +0.84s vs your PB here" or fall back to lap count
  let sub = 'Best lap';
  if(last.best_lap_time_s && pbHere && last.best_lap_time_s > pbHere){
    const gap = last.best_lap_time_s - pbHere;
    sub += ' · +' + gap.toFixed(2) + 's vs your PB here';
  } else if(last.best_lap_time_s && pbHere && Math.abs(last.best_lap_time_s - pbHere) < 0.005){
    sub += ' · matches your PB here';
  } else if(last.best_lap_time_s && pbHere && last.best_lap_time_s < pbHere){
    sub += ' · new PB!';
  }
  document.getElementById('last-sub').textContent = sub;

  document.getElementById('last-track').textContent = last.track || '—';
  const carName = carDisplay(last);
  const cls = last.car_class != null ? `<span class="class-badge">${CLASS_NAMES[last.car_class] || ''}</span>` : '';
  const pi = last.car_pi ? `<span style="color:var(--color-text-quaternary);font-size:11px">PI ${last.car_pi}</span>` : '';
  document.getElementById('last-car').innerHTML =
    escapeHtml(carName) + ' ' + cls + (cls && pi ? ' · ' : '') + pi;
  const condBits = [];
  if(last.weather_condition) condBits.push(last.weather_condition);
  if(last.tyre_compound) condBits.push(last.tyre_compound);
  if(last.track_temp_c != null) condBits.push(Math.round(last.track_temp_c) + '°C');
  if(last.started_at) condBits.push(fmtShortDate(last.started_at) + ' ' + fmtTime(last.started_at));
  document.getElementById('last-cond').textContent = condBits.join(' · ');
}

function renderTopCircuits(circuits){
  const el = document.getElementById('top-circuits');
  if(!circuits.length){el.innerHTML = '<div class="panel-empty">No circuits yet.</div>'; return;}
  el.innerHTML = circuits.map(c => {
    const href = '/sessions/track?name=' + encodeURIComponent(c.track);
    return `<a href="${href}" class="panel-row">
      <div>
        <div class="panel-name">${escapeHtml(c.track)}</div>
        <div class="panel-meta">${c.sessions_count} session${c.sessions_count === 1 ? '' : 's'} · ${c.laps_count} lap${c.laps_count === 1 ? '' : 's'}</div>
      </div>
      <div class="panel-pb">${fmtLap(c.best_lap_s)}</div>
      <div class="panel-arrow">→</div>
    </a>`;
  }).join('');
}

function renderTopCars(cars){
  const el = document.getElementById('top-cars');
  if(!cars.length){el.innerHTML = '<div class="panel-empty">No cars yet.</div>'; return;}
  el.innerHTML = cars.map(c => {
    const href = '/cars/' + c.ordinal;
    const name = c.nickname || c.name || ('Car #' + c.ordinal);
    const cls = c.class != null ? `<span class="class-badge" style="margin-left:6px">${CLASS_NAMES[c.class] || ''}</span>` : '';
    return `<a href="${href}" class="panel-row">
      <div>
        <div class="panel-name">${escapeHtml(name)} ${cls}</div>
        <div class="panel-meta">${c.sessions_count} session${c.sessions_count === 1 ? '' : 's'} · ${c.laps_count} lap${c.laps_count === 1 ? '' : 's'}${c.name && c.nickname ? ' · ' + escapeHtml(c.name) : ''}</div>
      </div>
      <div class="panel-pb">${fmtLap(c.best_lap_s)}</div>
      <div class="panel-arrow">→</div>
    </a>`;
  }).join('');
}

function renderRecent(recents){
  document.getElementById('recent-count').textContent =
    recents.length ? ('showing ' + recents.length + ' latest') : '—';
  const list = document.getElementById('recent-list');
  if(!recents.length){
    list.innerHTML = '<div class="recent-empty">No sessions recorded yet.</div>';
    return;
  }
  list.innerHTML = recents.map(s => {
    const href = '/sessions/session?id=' + encodeURIComponent(s.session_id);
    const date = fmtShortDate(s.started_at);
    const time = fmtTime(s.started_at);
    const carName = carDisplay(s);
    const cls = s.car_class != null ? `<span class="class-badge">${CLASS_NAMES[s.car_class] || ''}</span>` : '';
    const condBits = [];
    if(s.weather_condition) condBits.push(s.weather_condition);
    if(s.tyre_compound) condBits.push(s.tyre_compound);
    if(s.track_temp_c != null) condBits.push(Math.round(s.track_temp_c) + '°C');
    return `<a href="${href}" class="recent-row">
      <span class="recent-date">${date}<small>${time}</small></span>
      <span class="recent-track">${escapeHtml(s.track || '—')}</span>
      <span class="recent-car">${escapeHtml(carName)} ${cls}</span>
      <span class="recent-cond">${condBits.join(' · ')}</span>
      <span class="recent-time">${fmtLap(s.best_lap_time_s)}</span>
      <span class="recent-arrow">→</span>
    </a>`;
  }).join('');
}

// ── Career strip ──────────────────────────────────────────────────
function posToPct(fp){if(fp == null) return null; return Math.max(5, Math.min(100, Math.round(100 - (fp - 1) * 6)));}
function setCV(id, val, cls){
  const el = document.getElementById(id);
  el.textContent = (val == null) ? '—' : val;
  el.className = 'cs-v' + (cls ? ' ' + cls : '');
}
async function loadCareer(){
  let k = {}, form = [];
  try{k = await fetch('/sessions/career').then(r => r.json());}catch(e){}
  try{form = await fetch('/sessions/form?type=all&last=20').then(r => r.json());}catch(e){}
  const strip = document.getElementById('career-strip');
  if(!k || (k.total_sessions || 0) === 0){strip.style.display = 'none'; return;}
  strip.style.display = '';
  setCV('cs-total', k.total_sessions || '0', 'muted');
  setCV('cs-finish', k.avg_finish_real != null ? 'P' + (+k.avg_finish_real.toFixed(1)) : null, 'blue');
  const pg = k.avg_pos_gained;
  setCV('cs-gained', pg != null ? ((pg >= 0 ? '+' : '') + (+pg.toFixed(1))) : null,
        pg > 0 ? 'green' : pg < 0 ? 'red' : null);
  setCV('cs-win', k.win_rate != null ? Math.round(k.win_rate) + '%' : null, 'amber');
  setCV('cs-podium', k.podium_rate != null ? Math.round(k.podium_rate) + '%' : null, 'green');
  setCV('cs-laps', k.total_laps || '0', 'muted');
  renderCareerSpark(form);
}
function renderCareerSpark(form){
  const withPos = (form || []).filter(s => s.finish_pos != null);
  const trendEl = document.getElementById('cs-trend');
  const sparkEl = document.getElementById('cs-spark');
  if(withPos.length < 2){trendEl.textContent = ''; trendEl.className = 'cs-trend fl'; sparkEl.innerHTML = ''; return;}
  const pcts = withPos.map(s => posToPct(s.finish_pos));
  const half = Math.floor(pcts.length / 2);
  const a1 = pcts.slice(0, half).reduce((a, b) => a + b, 0) / (half || 1);
  const a2 = pcts.slice(half).reduce((a, b) => a + b, 0) / ((pcts.length - half) || 1);
  const diff = a2 - a1;
  let col;
  if(diff > 4){trendEl.textContent = '▲ Improving'; trendEl.className = 'cs-trend up'; col = '#22c55e';}
  else if(diff < -4){trendEl.textContent = '▼ Declining'; trendEl.className = 'cs-trend dn'; col = '#ef4444';}
  else{trendEl.textContent = '— Steady'; trendEl.className = 'cs-trend fl'; col = '#888';}
  const w = 120, h = 32, pad = 3;
  const mn = Math.min(...pcts), mx = Math.max(...pcts), rng = Math.max(mx - mn, 15);
  const xs = pcts.map((_, i) => pad + (w - pad * 2) * i / Math.max(pcts.length - 1, 1));
  const ys = pcts.map(v => h - pad - (h - pad * 2) * (v - mn) / rng);
  const pts = xs.map((x, i) => x.toFixed(1) + ',' + ys[i].toFixed(1)).join(' ');
  sparkEl.innerHTML = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:100%"><polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" opacity=".85"/></svg>`;
}

function renderFooter(stats){
  const el = document.getElementById('pi-stats');
  if(!stats){el.innerHTML = '—'; return;}
  const bits = [];
  if(stats.udp_received_total != null){
    bits.push(`UDP <strong>${stats.udp_received_total.toLocaleString()}</strong> pkts`);
  }
  if(stats.last_packet_at){
    bits.push(`Last packet <strong>${fmtRelative(stats.last_packet_at)}</strong>`);
  }
  if(stats.storage_used_gb != null && stats.storage_total_gb != null){
    bits.push(`Storage <strong>${fmtBytes(stats.storage_used_gb)} / ${fmtBytes(stats.storage_total_gb)}</strong>`);
  }
  el.innerHTML = bits.map(b => `<span>${b}</span>`).join('');
}

init();
