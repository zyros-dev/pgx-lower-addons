.PHONY: help serve stop clean install report setup-ssl deploy update-remote

serve:
	@echo "Pulling latest images..."
	@docker-compose pull frontend backend
	@echo "Stopping frontend and backend..."
	@docker-compose stop frontend backend
	@echo "Removing old containers..."
	@docker-compose rm -f frontend backend
	@echo "Starting updated containers..."
	@docker-compose up -d frontend backend
	@echo "Deployment complete!"

update-server:
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
