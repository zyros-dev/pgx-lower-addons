# Deployment Guide

## Server Setup (One-time)

### 1. DNS Configuration (Namecheap)
```
Type: A Record
Host: pgx
Value: YOUR_DROPLET_IP
TTL: Automatic
```

### 2. Server Prerequisites
```bash
# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install -y docker-compose

# Add swap (for building)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### 3. Clone Repository
```bash
git clone https://github.com/yourusername/pgx-lower-addons.git
cd pgx-lower-addons
```

### 4. Setup nginx + SSL
```bash
# Update email in setup-ssl.sh first!
chmod +x setup-ssl.sh
./setup-ssl.sh
```

### 5. Start Services
```bash
make serve
```

## Multi-Site Setup

The nginx configuration supports multiple sites on one server:

### Add New Site
1. Create nginx config: `/etc/nginx/sites-available/newsite.zyros.dev`
```nginx
server {
    listen 80;
    server_name newsite.zyros.dev;

    location / {
        proxy_pass http://localhost:3002;
        # ... (copy proxy settings from pgx.zyros.dev)
    }
}
```

2. Enable site:
```bash
ln -s /etc/nginx/sites-available/newsite.zyros.dev /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

3. Add SSL:
```bash
certbot --nginx -d newsite.zyros.dev
```

## Deployment Updates

### Deploy New Version
```bash
git pull
make rebuild  # Stops, rebuilds, restarts all services
```

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Architecture

```
nginx (host, ports 80/443) - SSL termination & routing
├── pgx.zyros.dev → localhost:3001 (frontend)
│   └── /api → localhost:8000 (backend)
├── future.zyros.dev → localhost:3002
└── another.zyros.dev → localhost:3003
```

## Ports

- 80/443: nginx (host)
- 3001: pgx-lower frontend
- 5433: PostgreSQL
- 8000: FastAPI backend

## SSL Renewal

Certbot auto-renews. Check status:
```bash
systemctl status certbot.timer
certbot certificates
```
