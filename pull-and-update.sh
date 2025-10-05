#!/bin/bash

set -e

cd /root/pgx-lower-addons

git fetch origin main

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ $LOCAL != $REMOTE ]; then
    echo "$(date): Updates found, pulling and restarting..."
    git pull origin main
    make serve
    echo "$(date): Deployment complete"
else
    echo "$(date): No updates"
fi
