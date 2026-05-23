// Lap fingerprint glyph — a compact 3-layer SVG that encodes one lap's
// driving character in ~70×42px. Used on /sessions to give every row a
// visual DNA next to the track outline.
//
// Layers (top → bottom):
//   • Speed line   — polyline of speed_mph, range-normalised to this
//                    lap so shape (not absolute speed) carries meaning.
//   • Throttle band — center-anchored vertical bars; height = throttle%.
//   • Brake spikes — thin downward ticks where brake% > threshold.
//
// Samples come from /sessions/lap-samples — same endpoint the telemetry
// page uses, same payload, no new backend. Cache keyed by sid:lap so
// re-renders (filter, sort, paginate) don't re-fetch.
//
// Use: <div class="lap-fp" data-sid="…" data-lap="N"></div>
//      then window.pfLoadFingerprints(scopeElement)
//
// Renders nothing if the lap has no stored samples (older sessions).

(function(){
  const _cache = new Map();   // "sid:lap" → samples[] | null

  async function _fetch(sid, lap){
    const key = sid + ':' + lap;
    if(_cache.has(key)) return _cache.get(key);
    try{
      // ?outline=1 — server-side decimation to ≤80 points + drops every
      // field except the ones this renderer reads. Same flag as
      // track_mini.js; shared slim format.
      const s = await fetch('/sessions/lap-samples?session_id=' + encodeURIComponent(sid)
        + '&lap=' + encodeURIComponent(lap) + '&outline=1').then(r => r.json());
      const ok = Array.isArray(s) && s.length >= 20;
      _cache.set(key, ok ? s : null);
      return ok ? s : null;
    }catch(e){ _cache.set(key, null); return null; }
  }

  // Decimate to N points, sampled evenly across the lap.
  function _resample(s, n){
    const out = new Array(n);
    const step = (s.length - 1) / (n - 1);
    for(let i = 0; i < n; i++) out[i] = s[Math.round(i * step)];
    return out;
  }

  async function pfDrawFingerprint(el){
    const sid = el.dataset.sid, lap = el.dataset.lap;
    if(!sid || lap == null) return;
    const samples = await _fetch(sid, lap);
    if(!samples) return;
    // Drop the first/last few samples — pit-exit and pit-entry warps
    // skew the speed range. Keep the meat of the lap.
    const trim = samples.slice(2, Math.max(3, samples.length - 2));
    const pts = _resample(trim, Math.min(80, trim.length));

    const W = 70, H = 42, pad = 1;
    const SPEED_H = 14, THR_H = 16, BRK_H = 10;
    const SPEED_Y = pad;
    const THR_Y   = SPEED_Y + SPEED_H;
    const BRK_Y   = THR_Y + THR_H;
    const xAt = i => pad + ((W - 2*pad) * i / (pts.length - 1));

    // Speed line — range-normalised so shape > absolute mph
    const spds = pts.map(p => p.speed_mph || 0);
    const mnS = Math.min(...spds), mxS = Math.max(...spds);
    const spRng = Math.max(mxS - mnS, 1);
    const spY = v => SPEED_Y + SPEED_H - ((v - mnS) / spRng) * (SPEED_H - 2) - 1;
    const speedPath = pts.map((p, i) =>
      (i === 0 ? 'M' : 'L') + xAt(i).toFixed(1) + ' ' + spY(spds[i]).toFixed(1)
    ).join(' ');

    // Throttle band — vertical bars centered on a midline. Height = throttle%
    const thrMid = THR_Y + THR_H / 2;
    const thrBars = pts.map((p, i) => {
      const t = (p.throttle_pct || 0) / 100;
      const h = t * (THR_H / 2 - 0.5);
      const x = xAt(i);
      return `<line x1="${x.toFixed(1)}" y1="${(thrMid - h).toFixed(1)}" `+
             `x2="${x.toFixed(1)}" y2="${(thrMid + h).toFixed(1)}"/>`;
    }).join('');

    // Brake spikes — thin ticks dropping from the BRK_Y baseline
    const brkBars = pts.map((p, i) => {
      const b = (p.brake_pct || 0) / 100;
      if(b < 0.05) return '';
      const x = xAt(i);
      return `<line x1="${x.toFixed(1)}" y1="${BRK_Y.toFixed(1)}" `+
             `x2="${x.toFixed(1)}" y2="${(BRK_Y + b * (BRK_H - 1)).toFixed(1)}"/>`;
    }).join('');

    el.innerHTML =
      `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Lap fingerprint">`+
        `<path class="fp-speed" d="${speedPath}" fill="none"/>`+
        `<g class="fp-thr">${thrBars}</g>`+
        `<g class="fp-brk">${brkBars}</g>`+
      `</svg>`;
  }

  function pfLoadFingerprints(root){
    const scope = root || document;
    const els = scope.querySelectorAll('.lap-fp[data-sid]:empty');
    if(!('IntersectionObserver' in window)){ els.forEach(pfDrawFingerprint); return; }
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(e => {
        if(e.isIntersecting){ obs.unobserve(e.target); pfDrawFingerprint(e.target); }
      });
    }, {rootMargin: '200px 0px'});
    els.forEach(el => io.observe(el));
  }

  window.pfDrawFingerprint = pfDrawFingerprint;
  window.pfLoadFingerprints = pfLoadFingerprints;
})();
