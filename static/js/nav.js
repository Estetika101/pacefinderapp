// Shared top bar — one component, every page (docs/specs/ia.md).
// Renders into <div id="pf-nav"></div>: brand → Home, the live status
// pill (the entire Live story), and Setup. Polls /status so the pill is
// live on every page. No standalone "Live dashboard" link — the pill is
// the affordance: quiet when idle, alive + clickable when recording.
(function(){
  var root = document.getElementById('pf-nav');
  if(!root) return;

  // Embedded (telemetry iframe inside session detail) → the parent page
  // already shows the bar; suppress this one to avoid a double header.
  if(new URLSearchParams(location.search).get('embed') === '1'){
    root.style.display = 'none';
    return;
  }

  var path = location.pathname;
  var setupCur = (path === '/setup') ? ' class="cur"' : '';
  root.className = 'pf-nav';
  root.innerHTML =
    '<a href="/" class="pf-brand">pacefinder<span class="pf-dot">.</span></a>' +
    '<a class="pf-pill" id="pf-pill">' +
      '<span class="pf-pill-dot"></span>' +
      '<span id="pf-pill-text">Loading…</span>' +
    '</a>' +
    '<span class="pf-spacer"></span>' +
    '<span class="pf-util">' +
      '<a href="/setup"' + setupCur + '>Setup</a>' +
    '</span>';

  var pill = document.getElementById('pf-pill');
  var txt  = document.getElementById('pf-pill-text');

  // The pill is ALWAYS a link to the live dashboard — you can open it
  // before a session to check the dash. Only the state styling/text
  // changes.
  pill.href = '/dashboard';

  function paint(s){
    var status = s && s.status;
    if(status === 'racing' || status === 'paused'){
      pill.className = 'pf-pill live';
      txt.textContent = 'Recording · view live';
    } else if(status === 'race_ended'){
      pill.className = 'pf-pill ended';
      txt.textContent = 'Race ended';
    } else {
      pill.className = 'pf-pill';
      txt.textContent = 'Idle · open live dashboard';
    }
  }

  async function poll(){
    try{
      var s = await fetch('/status').then(function(r){ return r.json(); });
      paint(s);
    }catch(e){ /* keep last state on a transient failure */ }
  }
  poll();
  setInterval(poll, 10000);
})();
