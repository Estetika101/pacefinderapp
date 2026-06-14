import os
import sys
import json
import hashlib
import platform
import urllib.request
import shutil
import subprocess
import tempfile
from pathlib import Path

# systemd unit name (matches packaging/ + README install instructions).
SERVICE_NAME = "pacefinder"


def _appimage_arch() -> str:
    """Map the host machine to the AppImage arch suffix in release asset names.

    Must key on the CPU architecture, not pointer width — a 64-bit Raspberry
    Pi is aarch64, and bitness alone (sys.maxsize) would mislabel it x86_64
    and hand it the wrong binary.
    """
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return "aarch64"
    return "x86_64"


def detect_deployment():
    """Detect deployment method: 'appimage', 'docker', 'systemd', or 'dev'."""
    # Check if running from .AppImage
    if os.environ.get('APPIMAGE'):
        return 'appimage'

    # Check if running in Docker (cgroup v1)
    try:
        with open('/proc/1/cgroup', 'r') as f:
            if 'docker' in f.read().lower():
                return 'docker'
    except (FileNotFoundError, OSError):
        pass

    # Check if running as systemd service
    if os.environ.get('INVOCATION_ID'):
        return 'systemd'

    # Development/source install
    return 'dev'


def _repo_dir() -> Path:
    """Repo root for source/systemd installs (net/updater.py → repo/)."""
    return Path(__file__).resolve().parent.parent


def get_latest_release_info():
    """Fetch latest release info from GitHub. /releases/latest excludes
    pre-releases, so rc tags are never offered as an update."""
    try:
        url = 'https://api.github.com/repos/Estetika101/pacefinderapp/releases/latest'
        headers = {'Accept': 'application/vnd.github.v3+json'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _asset_sha256(latest, download_url):
    """Expected sha256 hex for a release asset, from GitHub's `digest` field
    (e.g. "sha256:abc…"). Returns None if the API didn't provide one."""
    for asset in (latest or {}).get('assets', []):
        if asset.get('browser_download_url') == download_url:
            digest = asset.get('digest') or ''
            if digest.startswith('sha256:'):
                return digest.split(':', 1)[1]
    return None


def get_update_info():
    """Get update info including deployment method and available updates."""
    deployment = detect_deployment()
    latest = get_latest_release_info()

    if not latest:
        return {'deployment': deployment, 'update_available': False}

    info = {
        'deployment': deployment,
        'latest_version': latest['tag_name'],
        'release_url': latest['html_url'],
        'update_available': True,
    }

    # Find appropriate asset / restart story for the deployment method
    if deployment == 'appimage':
        asset_name = f'Pacefinder-{latest["tag_name"].lstrip("v")}-{_appimage_arch()}.AppImage'
        for asset in latest.get('assets', []):
            if asset['name'] == asset_name:
                info['download_url'] = asset['browser_download_url']
                info['can_auto_update'] = True
                break
    elif deployment == 'docker':
        info['download_info'] = f'docker pull ghcr.io/estetika101/pacefinder:{latest["tag_name"]}'
    elif deployment == 'systemd':
        # Auto-update = git pull + service restart. Restarting a system unit
        # needs root; flag that up front so the UI can warn before applying and
        # show the exact command when a manual restart is required.
        info['can_auto_update'] = True
        info['needs_sudo'] = (os.geteuid() != 0)
        info['restart_command'] = f'sudo systemctl restart {SERVICE_NAME}'

    return info


def _spawn_detached(script: str):
    """Run a bash script in its own session so it outlives this process —
    needed because the updater must replace/restart the very process it runs in.
    """
    subprocess.Popen(
        ['bash', '-c', script],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def perform_update(download_url=""):
    """Apply an update for the current deployment. Returns a status dict."""
    deployment = detect_deployment()
    if deployment == 'appimage':
        return _update_appimage(download_url)
    if deployment == 'systemd':
        return _update_systemd()
    return {'success': False, 'error': f'Auto-update not supported for {deployment}'}


def _update_appimage(download_url):
    """Download + verify the new AppImage, then hand off to a detached helper
    that waits for this process to exit, swaps the binary, and relaunches."""
    if not download_url:
        return {'success': False, 'error': 'No download URL provided'}
    appimage_path = os.environ.get('APPIMAGE')
    if not appimage_path:
        return {'success': False, 'error': 'Cannot determine AppImage path'}

    try:
        latest = get_latest_release_info()
        expected = _asset_sha256(latest, download_url)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.AppImage') as tmp:
            tmp_path = tmp.name
        print(f"Downloading update to {tmp_path}...", file=sys.stderr)
        urllib.request.urlretrieve(download_url, tmp_path)

        if os.path.getsize(tmp_path) < 1_000_000:  # <1MB → almost certainly a failed download
            os.unlink(tmp_path)
            return {'success': False, 'error': 'Downloaded file too small'}

        # Verify integrity against GitHub's published digest before we trust it.
        if expected:
            actual = _sha256(tmp_path)
            if actual != expected:
                os.unlink(tmp_path)
                return {'success': False,
                        'error': f'Checksum mismatch (expected {expected[:12]}…, got {actual[:12]}…)'}
        else:
            print("WARNING: release asset has no digest; skipping checksum verification",
                  file=sys.stderr)

        os.chmod(tmp_path, 0o755)

        backup_path = f"{appimage_path}.backup"
        if os.path.exists(appimage_path):
            shutil.copy2(appimage_path, backup_path)

        # The running process can't replace its own backing file and restart
        # cleanly, so a detached helper does it after we exit. The leading sleep
        # lets this request's HTTP response flush to the browser first.
        pid = os.getpid()
        helper = f"""
sleep 2
kill -TERM {pid} 2>/dev/null
for _ in $(seq 1 50); do kill -0 {pid} 2>/dev/null || break; sleep 0.2; done
mv -f '{tmp_path}' '{appimage_path}'
chmod +x '{appimage_path}'
exec '{appimage_path}'
"""
        _spawn_detached(helper)
        return {
            'success': True,
            'should_restart': True,
            'message': 'Update downloaded and verified. Restarting…',
        }
    except Exception as e:
        print(f"Update failed: {e}", file=sys.stderr)
        return {'success': False, 'error': str(e)}


def _update_systemd():
    """Pull the latest source, then restart the service — automatically if we're
    root, otherwise hand the exact sudo command back for the user to run."""
    repo = _repo_dir()
    try:
        pull = subprocess.run(
            ['git', '-C', str(repo), 'pull', '--ff-only'],
            capture_output=True, text=True, timeout=120,
        )
    except Exception as e:
        return {'success': False, 'error': f'git pull failed to run: {e}'}
    if pull.returncode != 0:
        detail = (pull.stderr.strip() or pull.stdout.strip() or 'unknown error')
        return {'success': False, 'error': f'git pull failed: {detail}'}

    restart_cmd = f'sudo systemctl restart {SERVICE_NAME}'

    # Root (the service often runs as root) can restart without sudo.
    if os.geteuid() == 0:
        _spawn_detached(f"sleep 1; systemctl restart {SERVICE_NAME}")
        return {'success': True, 'should_restart': True,
                'message': f'Updated. Restarting {SERVICE_NAME}…'}

    # Non-root: code is updated, but the restart needs admin rights. Don't
    # silently invoke sudo — tell the user exactly what to run.
    return {
        'success': True,
        'should_restart': False,
        'needs_manual_restart': True,
        'restart_command': restart_cmd,
        'message': f'Code updated. To finish, run:  {restart_cmd}',
    }
