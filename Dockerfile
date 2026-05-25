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

# Default storage lives in /data so it can be bind-mounted from the host.
ENV PYTHONUNBUFFERED=1
VOLUME ["/data"]

CMD ["python", "listener.py"]
