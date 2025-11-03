FROM python:3.13-slim

WORKDIR /app

# Install build dependencies for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Copy content and resources
COPY content /app/content
COPY resources /app/resources
COPY pgx-lower-report /app/pgx-lower-report
COPY slides /app/slides

# Create directories for volumes
RUN mkdir -p /data/database /data/logs

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
