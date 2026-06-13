import os
import sys
import json
import urllib.request
import shutil
import subprocess
import tempfile
from pathlib import Path


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


def get_latest_release_info():
    """Fetch latest release info from GitHub."""
    try:
        url = 'https://api.github.com/repos/Estetika101/pacefinderapp/releases/latest'
        headers = {'Accept': 'application/vnd.github.v3+json'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception:
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

    # Find appropriate asset for deployment method
    if deployment == 'appimage':
        # Try to detect architecture
        arch = 'x86_64' if sys.maxsize > 2**32 else 'aarch64'
        asset_name = f'Pacefinder-{latest["tag_name"].lstrip("v")}-{arch}.AppImage'
        for asset in latest.get('assets', []):
            if asset['name'] == asset_name:
                info['download_url'] = asset['browser_download_url']
                info['can_auto_update'] = True
                break
    elif deployment == 'docker':
        info['download_info'] = f'docker pull ghcr.io/estetika101/pacefinder:{latest["tag_name"]}'
    elif deployment == 'systemd':
        # For systemd, guide to release page where they can download AppImage or use package manager
        info['download_info'] = 'See release page for installation instructions'

    return info


def perform_update(download_url):
    """Download and apply AppImage update. Returns status dict."""
    deployment = detect_deployment()

    if deployment != 'appimage':
        return {'success': False, 'error': f'Auto-update not supported for {deployment}'}

    appimage_path = os.environ.get('APPIMAGE')
    if not appimage_path:
        return {'success': False, 'error': 'Cannot determine AppImage path'}

    try:
        # Download to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.AppImage') as tmp:
            tmp_path = tmp.name
            print(f"Downloading update to {tmp_path}...", file=sys.stderr)
            urllib.request.urlretrieve(download_url, tmp_path)

        # Verify it's executable and not empty
        if os.path.getsize(tmp_path) < 1000000:  # Less than 1MB, likely failed
            os.unlink(tmp_path)
            return {'success': False, 'error': 'Downloaded file too small'}

        # Make executable
        os.chmod(tmp_path, 0o755)

        # Backup current version
        backup_path = f"{appimage_path}.backup"
        if os.path.exists(appimage_path):
            shutil.copy2(appimage_path, backup_path)
            print(f"Backed up to {backup_path}", file=sys.stderr)

        # Replace with new version
        shutil.move(tmp_path, appimage_path)
        print(f"Updated AppImage at {appimage_path}", file=sys.stderr)

        # Trigger restart
        # Exit with code 42 so the launcher knows to restart
        return {
            'success': True,
            'message': 'Update downloaded and applied. Restarting...',
            'should_restart': True
        }

    except Exception as e:
        print(f"Update failed: {e}", file=sys.stderr)
        return {'success': False, 'error': str(e)}
