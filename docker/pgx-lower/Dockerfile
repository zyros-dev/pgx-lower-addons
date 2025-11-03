FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PG_VERSION=17.6

# Install PostgreSQL and required dependencies
RUN apt-get update && apt-get install -y \
    postgresql-contrib \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create postgres user (already exists in postgres image, but just to be safe)
RUN useradd -m -d /var/lib/postgresql -s /bin/bash postgres || true

# Create IR temp directory
RUN mkdir -p /tmp/pgx_ir && chmod 777 /tmp/pgx_ir

# Copy entrypoint script
COPY docker/pgx-lower/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5432

ENTRYPOINT ["/entrypoint.sh"]
CMD ["postgres"]
