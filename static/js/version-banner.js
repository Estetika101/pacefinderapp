(function(){
  const REPO_OWNER = 'Estetika101';
  const REPO_NAME = 'pacefinderapp';

  // Set in showBanner; read by handleUpdateClick for deployment-specific data
  // (download_url, needs_sudo, restart_command).
  let currentUpdate = null;

  function compareVersions(current, latest) {
    const parseVersion = (v) => {
      const parts = v.replace(/^v/, '').split(/[-.]/).map(p => {
        const num = parseInt(p, 10);
        return isNaN(num) ? p : num;
      });
      return parts;
    };

    const curr = parseVersion(current);
    const next = parseVersion(latest);
    const maxLen = Math.max(curr.length, next.length);

    for (let i = 0; i < maxLen; i++) {
      const a = curr[i] ?? 0;
      const b = next[i] ?? 0;

      const aNum = typeof a === 'number' ? a : NaN;
      const bNum = typeof b === 'number' ? b : NaN;

      if (!isNaN(aNum) && !isNaN(bNum)) {
        if (aNum < bNum) return -1;
        if (aNum > bNum) return 1;
      } else {
        const aStr = String(a);
        const bStr = String(b);
        if (aStr < bStr) return -1;
        if (aStr > bStr) return 1;
      }
    }
    return 0;
  }

  async function checkForUpdates() {
    try {
      const currentResp = await fetch('/version');
      if (!currentResp.ok) return;
      const currentData = await currentResp.json();
      const currentVersion = currentData.version;

      const updateResp = await fetch('/update/check');
      if (!updateResp.ok) return;
      const updateData = await updateResp.json();

      if (updateData.update_available && compareVersions(currentVersion, updateData.latest_version) < 0) {
        showBanner(currentVersion, updateData.latest_version, updateData);
      }
    } catch (e) {
      // Silently fail if update check fails
    }
  }

  function showBanner(currentVersion, latestVersion, updateData) {
    currentUpdate = updateData;
    const existing = document.getElementById('pf-version-banner');
    if (existing) return;

    const banner = document.createElement('div');
    banner.id = 'pf-version-banner';
    banner.className = 'pf-vbanner';

    // AppImage and systemd both support one-click apply; docker/dev link out.
    const oneClick = updateData.can_auto_update &&
                     (updateData.deployment === 'appimage' || updateData.deployment === 'systemd');
    const updateBtnText = oneClick ? 'Update now' : 'View release';
    const updateBtnHref = updateData.download_url || updateData.release_url;

    const btnElement = oneClick
      ? `<button class="pf-vb-btn" onclick="handleUpdateClick(event, '${updateData.deployment}'); return false;" data-url="${updateBtnHref}">${updateBtnText}</button>`
      : `<a href="${updateBtnHref}" target="_blank" class="pf-vb-btn" onclick="return handleUpdateClick(event, '${updateData.deployment}')">${updateBtnText}</a>`;

    banner.innerHTML = `
      <div class="pf-vb-content">
        <span class="pf-vb-text">
          New version available: <strong>${latestVersion}</strong>
          <span class="pf-vb-current">(running ${currentVersion})</span>
        </span>
        ${btnElement}
        <button class="pf-vb-close" aria-label="Dismiss" title="Dismiss">✕</button>
      </div>
    `;

    const closeBtn = banner.querySelector('.pf-vb-close');
    closeBtn.addEventListener('click', function() {
      banner.style.display = 'none';
      localStorage.setItem('pf-vb-dismissed', latestVersion);
    });

    document.body.insertBefore(banner, document.body.firstChild);
  }

  window.handleUpdateClick = function(event, deployment) {
    event.preventDefault();

    if (deployment === 'appimage') {
      const banner = document.getElementById('pf-version-banner');
      const content = banner.querySelector('.pf-vb-content');
      const btn = banner.querySelector('.pf-vb-btn');
      const closeBtn = banner.querySelector('.pf-vb-close');

      // Show loading state
      btn.disabled = true;
      closeBtn.style.display = 'none';
      content.querySelector('.pf-vb-text').textContent = 'Downloading update...';

      // Get download URL from button data attribute
      const downloadUrl = btn.getAttribute('data-url');

      // Trigger update
      fetch('/update/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ download_url: downloadUrl })
      }).then(r => r.json()).then(result => {
        if (result.success) {
          content.querySelector('.pf-vb-text').textContent = 'Update applied. Waiting for restart...';
          // Poll for server to come back up
          pollForRestart();
        } else {
          content.querySelector('.pf-vb-text').textContent = 'Update failed: ' + (result.error || 'Unknown error');
          btn.disabled = false;
          closeBtn.style.display = '';
        }
      }).catch(err => {
        content.querySelector('.pf-vb-text').textContent = 'Update error: ' + err.message;
        btn.disabled = false;
        closeBtn.style.display = '';
      });
      return false;
    } else if (deployment === 'systemd') {
      const banner = document.getElementById('pf-version-banner');
      const content = banner.querySelector('.pf-vb-content');
      const btn = banner.querySelector('.pf-vb-btn');
      const closeBtn = banner.querySelector('.pf-vb-close');
      const restartCmd = (currentUpdate && currentUpdate.restart_command) ||
                         'sudo systemctl restart pacefinder';

      // Warn up front when finishing will need admin rights, so the restart
      // step isn't a surprise — and so the user knows it's on them.
      if (currentUpdate && currentUpdate.needs_sudo) {
        const ok = window.confirm(
          'This pulls the latest code, but restarting the service needs admin ' +
          'rights. Once it finishes you\'ll need to run:\n\n  ' + restartCmd +
          '\n\nContinue?');
        if (!ok) return false;
      }

      btn.disabled = true;
      closeBtn.style.display = 'none';
      content.querySelector('.pf-vb-text').textContent = 'Updating (git pull)…';

      fetch('/update/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      }).then(r => r.json()).then(result => {
        const text = content.querySelector('.pf-vb-text');
        if (result.success && result.needs_manual_restart) {
          // Code is updated; the restart is the user's to run. Show the exact
          // command, keep it on screen, and stop the spinner.
          text.innerHTML = 'Updated. Finish with: <code class="pf-vb-cmd">' +
            (result.restart_command || restartCmd) + '</code>';
          btn.style.display = 'none';
          closeBtn.style.display = '';
        } else if (result.success) {
          text.textContent = 'Update applied. Waiting for restart…';
          pollForRestart();
        } else {
          text.textContent = 'Update failed: ' + (result.error || 'Unknown error');
          btn.disabled = false;
          closeBtn.style.display = '';
        }
      }).catch(err => {
        content.querySelector('.pf-vb-text').textContent = 'Update error: ' + err.message;
        btn.disabled = false;
        closeBtn.style.display = '';
      });
      return false;
    } else if (deployment === 'docker') {
      // Open release page in new tab
      window.open(event.currentTarget.href, '_blank');
      return false;
    }
    return true;
  };

  function pollForRestart() {
    const checkInterval = setInterval(async () => {
      try {
        const response = await fetch('/health', { method: 'GET' });
        if (response.ok) {
          clearInterval(checkInterval);
          // Server is back, reload the page
          location.reload();
        }
      } catch (e) {
        // Server still down, keep polling
      }
    }, 1000); // Check every second

    // Stop polling after 2 minutes
    setTimeout(() => clearInterval(checkInterval), 120000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkForUpdates);
  } else {
    checkForUpdates();
  }
})();

