#!/bin/bash

set -e

echo "=== Setting up nginx for pgx.zyros.dev ==="

# Install nginx and certbot
apt update
apt install -y nginx certbot python3-certbot-nginx

# Copy nginx config
cp nginx-host.conf /etc/nginx/sites-available/pgx.zyros.dev
ln -sf /etc/nginx/sites-available/pgx.zyros.dev /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

# Restart nginx to load config
systemctl restart nginx
systemctl enable nginx

echo "=== nginx setup complete! ==="
echo "Run 'make get-ssl' after containers are started to get SSL certificate"
