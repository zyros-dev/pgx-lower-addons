#!/bin/bash

set -e

echo "=== Setting up nginx and SSL for pgx.zyros.dev ==="

# Install nginx and certbot
apt update
apt install -y nginx certbot python3-certbot-nginx

# Stop nginx temporarily
systemctl stop nginx

# Copy nginx config
cp nginx-host.conf /etc/nginx/sites-available/pgx.zyros.dev
ln -sf /etc/nginx/sites-available/pgx.zyros.dev /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

# Start nginx
systemctl start nginx
systemctl enable nginx

# Get SSL certificate
certbot --nginx -d pgx.zyros.dev --non-interactive --agree-tos --email zyros.dev@gmail.com

# Auto-renewal
systemctl enable certbot.timer

echo "=== SSL setup complete! ==="
echo "Your site should be available at https://pgx.zyros.dev"
echo ""
echo "To add more sites later:"
echo "1. Create new config in /etc/nginx/sites-available/"
echo "2. Link to sites-enabled"
echo "3. Run: certbot --nginx -d newsite.zyros.dev"
