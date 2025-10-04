#!/bin/sh

# Deadman healthcheck script
# Monitors containers and restarts the stack if any are unhealthy

CONTAINERS="pgx-lower-postgres pgx-lower-backend pgx-lower-frontend"
CHECK_INTERVAL=5

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_container_health() {
    container=$1

    # Check if container exists and is running
    status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)

    if [ "$status" != "running" ]; then
        log "ERROR: Container $container is not running (status: $status)"
        return 1
    fi

    # Check health status if healthcheck is defined
    health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)

    if [ "$health" = "unhealthy" ]; then
        log "ERROR: Container $container is unhealthy"
        return 1
    fi

    # For containers without healthcheck, just check if running
    if [ "$health" = "<no value>" ] || [ -z "$health" ]; then
        log "INFO: Container $container is running (no healthcheck defined)"
        return 0
    fi

    log "INFO: Container $container is healthy"
    return 0
}

restart_stack() {
    log "CRITICAL: Unhealthy containers detected. Restarting stack..."

    cd /workspace || exit 1

    log "Running: make serve"
    make serve

    if [ $? -eq 0 ]; then
        log "SUCCESS: Stack restarted successfully"
    else
        log "ERROR: Failed to restart stack"
    fi
}

log "Deadman healthcheck starting..."

while true; do
    all_healthy=true

    for container in $CONTAINERS; do
        if ! check_container_health "$container"; then
            all_healthy=false
            break
        fi
    done

    if [ "$all_healthy" = false ]; then
        restart_stack
        # Wait longer after restart to let services stabilize
        log "Waiting 30 seconds for services to stabilize..."
        sleep 30
    fi

    sleep $CHECK_INTERVAL
done
