// Car detail page — /cars/<ordinal>
// Loads /cars/<ordinal>/data and renders the page server-shaped payload
// into the static markup defined in net/pages/cars.py.

const DRIVETRAIN_LABELS = {0: 'FWD', 1: 'RWD', 2: 'AWD'};
const CLASS_NAMES = {0:'D',1:'C',2:'B',3:'A',4:'S1',5:'S2',6:'X',7:'R',8:'P'};

function fmtLap(s){if(s == null) return '—'; const m = Math.floor(s/60); return m+':'+(s%60).toFixed(3).padStart(6,'0');}
function fmtDate(iso){if(!iso) return '—'; return new Date(iso).toLocaleDateString([], {month:'short', day:'numeric', year:'numeric'});}
function fmtShortDate(iso){if(!iso) return '—'; return new Date(iso).toLocaleDateString([], {month:'short', day:'numeric'});}
function fmtTime(iso){if(!iso) return ''; return new Date(iso).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});}
function fmtRelative(iso){
  if(!iso) return '—';
  const dt = new Date(iso);
  const diffMs = Date.now() - dt.getTime();
  const days = Math.floor(diffMs / 86400000);
  if(days < 1) return 'today';
  if(days === 1) return '1 day ago';
  if(days < 30) return days + ' days ago';
  const months = Math.floor(days / 30);
  if(months === 1) return '1 month ago';
  if(months < 12) return months + ' months ago';
  return Math.floor(months / 12) + ' year' + (Math.floor(months/12) === 1 ? '' : 's') + ' ago';
}
function fmtDuration(seconds){
  if(seconds == null) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if(h > 0) return h + 'h ' + m + 'm';
  return m + 'm';
}

const _ordinal = location.pathname.split('/')[2] || '';

async function init(){
  if(!_ordinal){location.href = '/sessions'; return;}
  let d;
  try{d = await fetch('/cars/' + encodeURIComponent(_ordinal) + '/data').then(r => r.json());}
  catch(e){document.getElementById('nickname').textContent = 'Car not found'; return;}
  if(d.error){document.getElementById('nickname').textContent = 'Car not found'; return;}

  renderTitle(d.car);
  renderHero(d.car, d.stats);
  renderTracks(d.tracks);
  renderRecent(d.recent, d.stats.best_ever);
  document.title = 'Pacefinder · ' + (d.car.nickname || d.car.name || 'Car #' + _ordinal);
}

function renderTitle(car){
  const nickname = car.nickname || car.name || 'Unknown Car (#' + car.ordinal + ')';
  document.getElementById('nickname').textContent = nickname;
  // Show canonical name as subtitle if it differs from the nickname (typical case
  // when user has set a nickname).
  if(car.nickname && car.name){
    const yearName = (car.year ? car.year + ' ' : '') + car.name;
    document.getElementById('canonical').textContent = yearName;
  } else if(car.name && car.year){
    document.getElementById('canonical').textContent = car.year;
  }
  if(car.class != null){
    const cl = document.getElementById('car-class');
    cl.textContent = CLASS_NAMES[car.class] || '';
    cl.style.display = '';
  }
  if(car.pi){
    const pi = document.getElementById('car-pi');
    pi.textContent = 'PI ' + car.pi;
    pi.style.display = '';
  }
  if(car.drivetrain_type != null){
    const dt = document.getElementById('drivetrain');
    dt.textContent = DRIVETRAIN_LABELS[car.drivetrain_type] || '';
    dt.style.display = '';
  }
}

function renderHero(car, stats){
  // Subtitle line: total sessions · laps · total time
  const parts = [];
  if(stats.total_sessions) parts.push(stats.total_sessions + ' session' + (stats.total_sessions === 1 ? '' : 's'));
  if(stats.total_laps)     parts.push(stats.total_laps + ' lap' + (stats.total_laps === 1 ? '' : 's'));
  if(stats.total_seconds)  parts.push(fmtDuration(stats.total_seconds) + ' total');
  document.getElementById('subtitle').innerHTML = parts.map(p => `<span>${p}</span>`).join('<span class="dot">·</span>');

  // Hero best lap + link to track where it was set
  if(stats.best_ever){
    document.getElementById('hero-best').textContent = fmtLap(stats.best_ever.best_lap_time_s);
    const trackHref = '/sessions/track?name=' + encodeURIComponent(stats.best_ever.track || '');
    const date = stats.best_ever.started_at ? ' · ' + fmtDate(stats.best_ever.started_at) : '';
    document.getElementById('hero-best-sub').innerHTML =
      `Best ever — <a href="${trackHref}">${stats.best_ever.track || 'unknown track'}</a>${date}`;
  } else {
    document.getElementById('hero-best').textContent = '—';
    document.getElementById('hero-best-sub').textContent = 'No completed laps yet';
  }

  // Stat tiles
  document.getElementById('stat-tracks').textContent = stats.tracks_driven || 0;
  document.getElementById('stat-avg').textContent    = stats.avg_lap_s ? fmtLap(stats.avg_lap_s) : '—';
  document.getElementById('stat-total').textContent  = stats.total_seconds ? fmtDuration(stats.total_seconds) : '—';
  document.getElementById('stat-last').textContent   = fmtRelative(stats.last_driven);
}

function renderTracks(tracks){
  document.getElementById('tracks-count').textContent =
    tracks.length + ' circuit' + (tracks.length === 1 ? '' : 's');
  const list = document.getElementById('track-list');
  if(!tracks.length){
    list.innerHTML = '<div class="empty">No tracks driven yet in this car.</div>';
    return;
  }
  list.innerHTML = tracks.map(t => {
    const href = '/sessions/track?name=' + encodeURIComponent(t.track);
    const lastDate = t.last_session ? fmtDate(t.last_session) : '—';
    const gap = t.gap_to_theoretical;
    let gapHtml = '';
    if(gap == null){
      gapHtml = '<span class="track-gap none">—</span>';
    } else if(gap < 0.5){
      gapHtml = `<span class="track-gap tight">+${gap.toFixed(2)}s</span>`;
    } else {
      gapHtml = `<span class="track-gap">+${gap.toFixed(2)}s</span>`;
    }
    return `<a href="${href}" class="track-row">
      <div>
        <div class="track-name">${escapeHtml(t.track)}</div>
        <div class="track-meta">${t.sessions_count} session${t.sessions_count === 1 ? '' : 's'} · ${t.laps_count} lap${t.laps_count === 1 ? '' : 's'} · last ${lastDate}</div>
      </div>
      <div class="track-pb">${fmtLap(t.best_lap_s)}</div>
      ${gapHtml}
      <div class="track-sessions">${t.sessions_count}</div>
      <div class="track-arrow">→</div>
    </a>`;
  }).join('');
}

function renderRecent(recent, bestEver){
  document.getElementById('recent-count').textContent =
    'showing ' + recent.length + (recent.length === 5 ? ' latest' : '');
  const list = document.getElementById('recent-list');
  if(!recent.length){
    list.innerHTML = '<div class="empty">No sessions yet in this car.</div>';
    return;
  }
  const bestId = bestEver ? bestEver.session_id : null;
  list.innerHTML = recent.map(s => {
    const isBest = s.session_id === bestId;
    const cls = isBest ? ' is-best' : '';
    const href = '/sessions/session?id=' + encodeURIComponent(s.session_id);
    const date = fmtShortDate(s.started_at);
    const time = fmtTime(s.started_at);
    const condParts = [];
    if(s.weather_condition) condParts.push(s.weather_condition);
    if(s.tyre_compound) condParts.push(s.tyre_compound);
    if(s.track_temp_c != null) condParts.push(Math.round(s.track_temp_c) + '°C');
    const cond = condParts.join(' · ');
    const star = isBest ? '<span class="best-star">★</span>' : '';
    return `<a href="${href}" class="recent-row${cls}">
      <span class="recent-date">${date}<small>${time}</small></span>
      <span class="recent-track">${escapeHtml(s.track || '—')}</span>
      <span class="recent-cond">${escapeHtml(cond)}</span>
      <span class="recent-time">${fmtLap(s.best_lap_time_s)}${star}</span>
      <span class="recent-arrow">→</span>
    </a>`;
  }).join('');
}

function escapeHtml(s){
  if(s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

init();
