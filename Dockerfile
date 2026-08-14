# Multi-arch Docker image for Pacefinder.
# Built and pushed to ghcr.io/estetika101/pacefinder by .github/workflows/release.yml
# for linux/amd64 and linux/arm64 (Raspberry Pi 4/5).
FROM python:3.13-slim

WORKDIR /app

# Listener is stdlib-only beyond platformdirs; copying the requirements first
# keeps the pip layer cached when only app code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# UDP: Forza telemetry · TCP: dashboard / status API
EXPOSE 5300/udp
EXPOSE 8000/tcp

# Default storage — and the config file itself — live in /data so both
# survive a bind mount and container recreation. config.py reads
# PACEFINDER_DATA_DIR to redirect CONFIG_FILE and the default storage_path
# here; without it, root (this container's default user) can always mkdir
# the Pi-only /mnt/usb/simtelemetry default, so the fallback that saves
# non-root installs never triggers and data silently lands outside /data.
ENV PYTHONUNBUFFERED=1 PACEFINDER_DATA_DIR=/data
VOLUME ["/data"]

CMD ["python", "listener.py"]
