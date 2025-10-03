.PHONY: help serve frontend backend clean install report

help:
	@echo "pgx-lower-addons Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install all dependencies (creates venv if needed)"
	@echo "  serve        - Start frontend and backend development servers"
	@echo "  clean        - Clean build artifacts"
	@echo "  report       - Build LaTeX report"

install:
	@echo "Setting up backend..."
	@cd backend && [ -d venv ] || python3 -m venv venv
	@cd backend && ./venv/bin/pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Done!"

serve:
	@echo "Starting frontend and backend..."
	@make -j2 frontend backend

clean:
	rm -rf frontend/node_modules frontend/dist frontend/build frontend/.next
	rm -rf backend/__pycache__ backend/venv backend/*.db backend/*.sqlite
	cd pgx-lower-report && make clean

report:
	cd pgx-lower-report && make
