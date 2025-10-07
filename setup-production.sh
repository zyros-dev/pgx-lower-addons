#!/bin/bash

# Production server setup script
# This runs automatically when `make serve` is called on the production server

set -e

echo "Checking if running on production server..."

# Only run on production server
if [ "$(hostname)" != "result-horse" ]; then
    echo "Not on production server, skipping production setup"
    exit 0
fi

echo "Setting up production server..."

# 1. Setup firewall (if not already configured)
if ! iptables -L DOCKER-USER -n | grep -q "tcp dpt:443"; then
    echo "Configuring firewall..."
    iptables -I DOCKER-USER -i eth0 -p tcp --dport 22 -j ACCEPT
    iptables -I DOCKER-USER -i eth0 -p tcp --dport 80 -j ACCEPT
    iptables -I DOCKER-USER -i eth0 -p tcp --dport 443 -j ACCEPT
    iptables -I DOCKER-USER -i eth0 -j DROP

    # Install iptables-persistent if not present
    if ! dpkg -l | grep -q iptables-persistent; then
        DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
    fi
    iptables-save > /etc/iptables/rules.v4
    echo "Firewall configured"
fi

# 2. Setup systemd service (auto-start on boot)
if [ ! -f /etc/systemd/system/pgx-lower-addons.service ]; then
    echo "Creating systemd service..."
    cat > /etc/systemd/system/pgx-lower-addons.service << 'EOFSVC'
[Unit]
Description=pgx-lower-addons website
After=docker.service network-online.target
Requires=docker.service
StartLimitIntervalSec=0

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/root/pgx-lower-addons
ExecStart=/usr/bin/make serve
ExecStop=/usr/bin/docker-compose down
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOFSVC
    systemctl daemon-reload
    systemctl enable pgx-lower-addons.service
    echo "Systemd service created and enabled"
fi

# 3. Setup cron jobs
CRON_DEPLOY="*/2 * * * * /root/pgx-lower-addons/pull-and-update.sh >> /var/log/pgx-deploy.log 2>&1"
CRON_HEALTH="* * * * * /root/pgx-lower-addons/health-check.sh >> /var/log/pgx-health.log 2>&1"

if ! crontab -l 2>/dev/null | grep -q "health-check.sh"; then
    echo "Setting up cron jobs..."
    (crontab -l 2>/dev/null || echo ""; echo "$CRON_HEALTH") | crontab -
    echo "Health-check cron added"
fi

if ! crontab -l 2>/dev/null | grep -q "pull-and-update.sh"; then
    (crontab -l 2>/dev/null || echo ""; echo "$CRON_DEPLOY") | crontab -
    echo "Auto-deploy cron added"
fi

# 4. Setup log rotation
if [ ! -f /etc/logrotate.d/pgx-lower ]; then
    echo "Setting up log rotation..."
    cat > /etc/logrotate.d/pgx-lower << 'EOFLOG'
/var/log/pgx-deploy.log /var/log/pgx-health.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0640 root root
}
/var/log/nginx/*.log {
    daily
    rotate 3
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
EOFLOG
    echo "Log rotation configured"
fi

# 5. Clean up existing nginx logs (one-time)
if [ -f /var/log/nginx/access.log ]; then
    echo "Truncating existing nginx logs..."
    truncate -s 0 /var/log/nginx/access.log
    truncate -s 0 /var/log/nginx/error.log
    echo "Nginx logs truncated"
fi

# 6. Update nginx config and reload
NGINX_LOG_CONFIG="/etc/nginx/conf.d/log-format.conf"
if [ -f "$NGINX_LOG_CONFIG" ]; then
    if grep -q "access_log.*timed" "$NGINX_LOG_CONFIG"; then
        echo "Updating nginx logging configuration..."
        cp /root/pgx-lower-addons/nginx-log-format.conf "$NGINX_LOG_CONFIG"
        nginx -t && systemctl reload nginx
        echo "Nginx logging disabled"
    fi
fi

echo "Production server setup complete!"
