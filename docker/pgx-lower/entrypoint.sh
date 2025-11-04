#!/bin/bash
set -e

# Run as postgres user if we're root
if [ "$(id -u)" = '0' ]; then
    # Initialize database if needed (as postgres user)
    if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
        echo "Initializing PostgreSQL database..."
        gosu postgres /usr/local/pgsql/bin/initdb -D /var/lib/postgresql/data
    fi

    # Configure PostgreSQL for external connections (as postgres user)
    gosu postgres bash -c "sed -i \"s/^#*listen_addresses.*/listen_addresses = '*'/\" /var/lib/postgresql/data/postgresql.conf"

    # Configure port 5432 (default PostgreSQL port, docker maps to host port)
    if grep -q '^port' /var/lib/postgresql/data/postgresql.conf 2>/dev/null; then
        gosu postgres bash -c "sed -i \"s/^port.*/port = 5432/\" /var/lib/postgresql/data/postgresql.conf"
    else
        gosu postgres bash -c "echo 'port = 5432' >> /var/lib/postgresql/data/postgresql.conf"
    fi

    # Add trust entry for Docker network if not present
    gosu postgres bash -c "grep -q 'host all all 0.0.0.0/0 trust' /var/lib/postgresql/data/pg_hba.conf || echo 'host all all 0.0.0.0/0 trust' >> /var/lib/postgresql/data/pg_hba.conf"

    # Create IR temp directory
    mkdir -p /tmp/pgx_ir && chmod 777 /tmp/pgx_ir

    # Start PostgreSQL as postgres user
    echo "Starting PostgreSQL..."
    exec gosu postgres /usr/local/pgsql/bin/postgres -D /var/lib/postgresql/data
else
    # Already running as postgres
    if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
        echo "Initializing PostgreSQL database..."
        /usr/local/pgsql/bin/initdb -D /var/lib/postgresql/data
    fi

    sed -i "s/^#*listen_addresses.*/listen_addresses = '*'/" /var/lib/postgresql/data/postgresql.conf

    if grep -q '^port' /var/lib/postgresql/data/postgresql.conf 2>/dev/null; then
        sed -i "s/^port.*/port = 5432/" /var/lib/postgresql/data/postgresql.conf
    else
        echo "port = 5432" >> /var/lib/postgresql/data/postgresql.conf
    fi

    grep -q 'host all all 0.0.0.0/0 trust' /var/lib/postgresql/data/pg_hba.conf || \
        echo 'host all all 0.0.0.0/0 trust' >> /var/lib/postgresql/data/pg_hba.conf

    mkdir -p /tmp/pgx_ir && chmod 777 /tmp/pgx_ir

    echo "Starting PostgreSQL..."
    exec /usr/local/pgsql/bin/postgres -D /var/lib/postgresql/data
fi
