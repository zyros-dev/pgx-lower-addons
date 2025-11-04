.PHONY: help serve stop clean install report setup-ssl deploy update-remote

help:
	@echo "pgx-lower-addons Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install        - Install all dependencies (creates venv if needed)"
	@echo "  serve          - Start frontend and backend development servers"
	@echo "  stop           - Stop all running containers"
	@echo "  clean          - Clean build artifacts"
	@echo "  report         - Build LaTeX report"
	@echo "  setup-nginx    - Setup nginx reverse proxy (production only, requires root)"
	@echo "  get-ssl        - Get SSL certificate (run after serve, requires root)"
	@echo "  deploy         - Full deployment: nginx + containers + SSL (production only)"
	@echo "  update-remote  - Rebuild backend+frontend, push to Hub, update remote server"

install:
	@echo "Setting up backend..."
	@cd backend && [ -d venv ] || python3 -m venv venv
	@cd backend && ./venv/bin/pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Done!"

serve:
	@bash fix-dns.sh 2>/dev/null || true
	@bash setup-production.sh 2>/dev/null || true
	@echo "Stopping any running containers..."
	@docker-compose down
	@echo "Pulling Docker images from Docker Hub..."
	@docker-compose pull
	@echo "Starting Docker containers..."
	@docker-compose up -d
	@echo ""
	@echo "Services running:"
	@echo "  Frontend:       http://localhost:3001"
	@echo "  Backend API:    http://localhost:8000"
	@echo "  Health Monitor: http://localhost:8001"
	@echo "  PostgreSQL:     localhost:5433"

stop:
	@echo "Stopping all containers..."
	@docker-compose down

clean:
	rm -rf frontend/node_modules frontend/dist frontend/build frontend/.next
	rm -rf backend/__pycache__ backend/venv backend/*.db backend/*.sqlite
	cd pgx-lower-report && make clean

report:
	cd pgx-lower-report && make

setup-nginx:
	@echo "Setting up nginx (requires root)..."
	@bash setup-nginx.sh

get-ssl:
	@echo "Getting SSL certificate (requires root)..."
	@systemctl stop nginx
	@certbot certonly --standalone -d pgx.zyros.dev --non-interactive --agree-tos --email zyros.dev@gmail.com
	@cp nginx-host.conf /etc/nginx/sites-available/pgx.zyros.dev
	@systemctl start nginx
	@systemctl enable certbot.timer

deploy: stop setup-nginx serve get-ssl
	@echo "Deployment complete!"
	@echo "Site available at https://pgx.zyros.dev"

update-remote:
	@echo "Building backend image with --no-cache..."
	@docker build --no-cache -f backend/Dockerfile -t zyrosdev/pgx-lower-addons-backend:latest .
	@echo "Building frontend image with --no-cache..."
	@docker build --no-cache -f frontend/Dockerfile -t zyrosdev/pgx-lower-addons-frontend:latest .
	@echo "Pushing backend image to Docker Hub..."
	@docker push zyrosdev/pgx-lower-addons-backend:latest
	@echo "Pushing frontend image to Docker Hub..."
	@docker push zyrosdev/pgx-lower-addons-frontend:latest
	@echo "Deploying to remote server (root@37.27.24.142)..."
	@ssh -o StrictHostKeyChecking=no root@37.27.24.142 "cd ~/pgx-lower-addons && git pull && make serve"
	@echo "Remote server update complete!"
