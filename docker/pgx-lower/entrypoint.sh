#!/bin/bash
set -e

# PostgreSQL is already initialized by apt, just start it
echo "Starting PostgreSQL..."

# Configure PostgreSQL for external connections
if grep -q '^listen_addresses' /etc/postgresql/16/main/postgresql.conf 2>/dev/null; then
    sed -i "s/^listen_addresses.*/listen_addresses = '*'/" /etc/postgresql/16/main/postgresql.conf || true
else
    echo "listen_addresses = '*'" >> /etc/postgresql/16/main/postgresql.conf || true
fi

# Configure port 54326
if grep -q '^port' /etc/postgresql/16/main/postgresql.conf 2>/dev/null; then
    sed -i "s/^port.*/port = 54326/" /etc/postgresql/16/main/postgresql.conf || true
else
    echo "port = 54326" >> /etc/postgresql/16/main/postgresql.conf || true
fi

# Add trust entry for Docker network if not present
HBA_FILE=/etc/postgresql/16/main/pg_hba.conf
if [ -f "$HBA_FILE" ]; then
    grep -q 'host all all 0.0.0.0/0 trust' "$HBA_FILE" || \
        echo 'host all all 0.0.0.0/0 trust' >> "$HBA_FILE"
fi

# Start PostgreSQL service
service postgresql start || service postgresql restart

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if pg_isready -h localhost -U postgres > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    sleep 1
done

# Keep the container running
tail -f /var/log/postgresql/postgresql-16-main.log
