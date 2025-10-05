#!/bin/bash

set -e

cd /root/pgx-lower-addons

git fetch origin main

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ $LOCAL != $REMOTE ]; then
    echo "$(date): Updates found, pulling and restarting..."
    git pull origin main

    # Auto-setup any new nginx configs
    for conf in nginx-*.conf; do
        if [ -f "$conf" ]; then
            subdomain=$(basename "$conf" .conf | sed 's/nginx-//')
            if [ ! -f "/etc/nginx/sites-enabled/$subdomain.zyros.dev" ]; then
                echo "$(date): Setting up new subdomain: $subdomain.zyros.dev"
                cp "$conf" "/etc/nginx/sites-available/$subdomain.zyros.dev"
                ln -sf "/etc/nginx/sites-available/$subdomain.zyros.dev" "/etc/nginx/sites-enabled/"
                nginx -t && systemctl reload nginx
                certbot --nginx -d "$subdomain.zyros.dev" --non-interactive --agree-tos --email zyros.dev@gmail.com || true
            fi
        fi
    done

    make serve
    echo "$(date): Deployment complete"
else
    echo "$(date): No updates"
fi
