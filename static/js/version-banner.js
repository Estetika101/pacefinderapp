(function(){
  const REPO_OWNER = 'Estetika101';
  const REPO_NAME = 'pacefinderapp';

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

      const latestResp = await fetch(
        `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases/latest`,
        { headers: { Accept: 'application/vnd.github.v3+json' } }
      );
      if (!latestResp.ok) return;
      const latestData = await latestResp.json();
      const latestVersion = latestData.tag_name;

      if (compareVersions(currentVersion, latestVersion) < 0) {
        showBanner(currentVersion, latestVersion, latestData.html_url);
      }
    } catch (e) {
      // Silently fail if GitHub API is unreachable or version check fails
    }
  }

  function showBanner(currentVersion, latestVersion, releaseUrl) {
    const existing = document.getElementById('pf-version-banner');
    if (existing) return; // Already shown

    const banner = document.createElement('div');
    banner.id = 'pf-version-banner';
    banner.className = 'pf-vbanner';
    banner.innerHTML = `
      <div class="pf-vb-content">
        <span class="pf-vb-text">
          New version available: <strong>${latestVersion}</strong>
          <span class="pf-vb-current">(running ${currentVersion})</span>
        </span>
        <a href="${releaseUrl}" target="_blank" class="pf-vb-btn">Update</a>
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkForUpdates);
  } else {
    checkForUpdates();
  }
})();
