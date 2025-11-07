.PHONY: help serve stop clean install report setup-ssl deploy update-remote

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
