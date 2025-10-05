.PHONY: help serve stop clean install report setup-ssl deploy

help:
	@echo "pgx-lower-addons Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install all dependencies (creates venv if needed)"
	@echo "  serve        - Start frontend and backend development servers"
	@echo "  stop         - Stop all running containers"
	@echo "  clean        - Clean build artifacts"
	@echo "  report       - Build LaTeX report"
	@echo "  setup-ssl    - Setup nginx and SSL (production only, requires root)"
	@echo "  deploy       - Full deployment: setup SSL + serve (production only)"

install:
	@echo "Setting up backend..."
	@cd backend && [ -d venv ] || python3 -m venv venv
	@cd backend && ./venv/bin/pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Done!"

serve:
	@echo "Stopping any running containers..."
	@docker-compose down
	@echo "Building and starting Docker containers..."
	@docker-compose up -d --build

stop:
	@echo "Stopping all containers..."
	@docker-compose down

clean:
	rm -rf frontend/node_modules frontend/dist frontend/build frontend/.next
	rm -rf backend/__pycache__ backend/venv backend/*.db backend/*.sqlite
	cd pgx-lower-report && make clean

report:
	cd pgx-lower-report && make

setup-ssl:
	@echo "Setting up nginx and SSL (requires root)..."
	@bash setup-ssl.sh

deploy: setup-ssl serve
	@echo "Deployment complete!"
	@echo "Site available at https://pgx.zyros.dev"
