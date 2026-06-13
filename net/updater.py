import os
import sys
import json
import urllib.request
import shutil
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
                break
    elif deployment == 'docker':
        info['download_info'] = f'docker pull ghcr.io/estetika101/pacefinder:{latest["tag_name"]}'
    elif deployment == 'systemd':
        # For systemd, guide to release page where they can download AppImage or use package manager
        info['download_info'] = 'See release page for installation instructions'

    return info
