// Shared chrome — the left rail (docs/specs/ia.md). Renders into
// <div id="pf-nav"></div>: Live state indicator (top), Home / Sessions
// / Tracks / Cars, Settings at the bottom. Fixed rail + a body offset
// (via html.pf-has-rail) so pages need no DOM changes. Collapsible to
// icons (persisted). Mobile (<760) is a bottom bar — CSS-driven, same
// DOM. The live indicator polls /status and links to the dashboard;
// the dramatic takeover is a separate layer.
(function(){
  var root = document.getElementById('pf-nav');
  if(!root) return;

  // Embedded telemetry (iframe in session detail): parent shows chrome.
  if(new URLSearchParams(location.search).get('embed') === '1'){
    root.style.display = 'none';
    return;
  }

  var doc = document.documentElement;
  doc.classList.add('pf-has-rail');
  if(localStorage.getItem('pf-rail-icons') === '1') doc.classList.add('pf-rail-icons');

  var p = location.pathname;
  function section(){
    if(p === '/' ) return 'home';
    if(p.indexOf('/sessions/track') === 0 || p.indexOf('/circuits') === 0) return 'tracks';
    if(p.indexOf('/cars') === 0) return 'cars';
    if(p.indexOf('/sessions') === 0) return 'sessions';
    if(p.indexOf('/setup') === 0) return 'settings';
    return '';
  }
  var cur = section();
  function item(id, href, ico, label, end){
    return '<a class="pf-it' + (end?' pf-end':'') + (cur===id?' cur':'') +
      '" href="' + href + '" data-tip="' + label + '">' +
      '<span class="pf-ic">' + ico + '</span><span class="pf-lb">' + label + '</span></a>';
  }

  root.className = 'pf-rail';
  root.innerHTML =
    '<div class="pf-top">' +
      '<a href="/" class="pf-brand">pacefinder<span class="pf-dot">.</span></a>' +
      '<button class="pf-collapse" id="pf-collapse" title="Collapse">⇆</button>' +
    '</div>' +
    '<a class="pf-live" id="pf-live" href="/dashboard">' +
      '<span class="pf-ld"></span><span id="pf-live-t">Loading…</span>' +
    '</a>' +
    '<div class="pf-items">' +
      item('home','/','⌂','Home') +
      item('sessions','/sessions','≣','Sessions') +
      item('tracks','/circuits','⌖','Tracks') +
      item('cars','/cars','⚙','Cars') +
      item('settings','/setup','⚙','Settings', true) +
    '</div>';

  document.getElementById('pf-collapse').addEventListener('click', function(){
    var on = doc.classList.toggle('pf-rail-icons');
    localStorage.setItem('pf-rail-icons', on ? '1' : '0');
  });

  var live = document.getElementById('pf-live');
  var lt   = document.getElementById('pf-live-t');
  function paint(s){
    var st = s && s.status;
    if(st === 'racing' || st === 'paused'){
      live.className = 'pf-live live'; lt.textContent = 'Recording · view live';
    } else if(st === 'race_ended'){
      live.className = 'pf-live ended'; lt.textContent = 'Race ended';
    } else {
      live.className = 'pf-live'; lt.textContent = 'Idle · no session';
    }
  }
  async function poll(){
    try{ paint(await fetch('/status').then(function(r){return r.json();})); }
    catch(e){}
  }
  poll();
  setInterval(poll, 10000);
})();
