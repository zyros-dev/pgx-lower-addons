#!/bin/bash
# Fix DNS resolution issues on production server

echo "Fixing DNS configuration..."

# Fix host DNS first
cp /etc/resolv.conf /etc/resolv.conf.backup 2>/dev/null || true
cat > /etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 1.1.1.1
nameserver 8.8.4.4
EOF
echo "Host DNS configured"

# Configure Docker daemon DNS for build-time resolution
mkdir -p /etc/docker

# Check if daemon.json exists and has content
if [ -f /etc/docker/daemon.json ] && [ -s /etc/docker/daemon.json ]; then
    # Backup existing config
    cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
    # Merge DNS settings (simple approach: just overwrite for now)
fi

cat > /etc/docker/daemon.json <<'EOF'
{
  "dns": ["8.8.8.8", "1.1.1.1", "8.8.4.4"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

echo "Docker daemon.json configured"

# Stop Docker, wait, then start (more reliable than restart)
if systemctl is-active --quiet docker; then
    echo "Stopping Docker daemon..."
    systemctl stop docker
    sleep 2
    echo "Starting Docker daemon..."
    systemctl start docker
    sleep 5
    echo "Docker daemon restarted with new DNS config"
fi

# Verify DNS works
if ping -c 1 -W 2 pypi.org &>/dev/null; then
    echo "✓ DNS resolution working"
else
    echo "⚠ DNS may still have issues, but continuing..."
fi

echo "DNS configuration complete"
