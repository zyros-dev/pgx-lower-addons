#!/bin/bash

set -e

cd "$(dirname "$0")"

# Check if all required containers are running
containers_ok=true

frontend_status=$(docker ps --format "{{.Names}} {{.Status}}" | grep "pgx-lower-frontend" || echo "")
backend_status=$(docker ps --format "{{.Names}} {{.Status}}" | grep "pgx-lower-backend" || echo "")
postgres_status=$(docker ps --format "{{.Names}} {{.Status}}" | grep "pgx-lower-postgres" || echo "")

if ! echo "$frontend_status" | grep -q "Up"; then
    echo "$(date): Frontend container not running"
    containers_ok=false
fi
if ! echo "$backend_status" | grep -q "Up"; then
    echo "$(date): Backend container not running"
    containers_ok=false
fi
if ! echo "$postgres_status" | grep -q "healthy"; then
    echo "$(date): Postgres container not healthy"
    containers_ok=false
fi

# If containers are down, restart them
if [ "$containers_ok" = false ]; then
    echo "$(date): Containers unhealthy, restarting..."
    docker-compose up -d
    sleep 5
    exit 0
fi

# If containers are up, test HTTP endpoints
if ! curl -sf --max-time 5 https://pgx.zyros.dev > /dev/null; then
    echo "$(date): Frontend HTTP check failed, restarting containers..."
    docker-compose restart
    exit 0
fi

if ! curl -sf --max-time 5 https://pgx.zyros.dev/api/health > /dev/null; then
    echo "$(date): Backend API health check failed, restarting backend..."
    docker-compose restart backend
    exit 0
fi

# All checks passed
echo "$(date): All health checks passed"
