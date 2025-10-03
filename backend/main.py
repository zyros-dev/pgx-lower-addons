from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import hashlib
import json
from pathlib import Path
from database import init_db, log_user_request, get_cached_query, cache_query
from logger import logger

CONTENT_DIR = Path(__file__).parent.parent / "content"
REPORT_DIR = Path(__file__).parent.parent / "pgx-lower-report"
SLIDES_DIR = Path(__file__).parent.parent / "slides"
RESOURCES_DIR = Path(__file__).parent.parent / "resources"

app = FastAPI(title="pgx-lower API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.on_event("startup")
async def startup():
    logger.info("Starting pgx-lower API")
    await init_db()
    logger.info("Database initialized")

@app.get("/")
async def root():
    return {"message": "pgx-lower API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/content/{filename}")
async def get_content(filename: str):
    """Serve markdown and image files from the content directory."""
    file_path = CONTENT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not str(file_path.resolve()).startswith(str(CONTENT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"Serving content file: {filename}")
    return FileResponse(file_path)

@app.get("/download/paper")
async def download_paper(request: Request):
    """Serve the PDF report with download logging."""
    ip_address = request.client.host if request.client else "unknown"
    pdf_path = REPORT_DIR / "main.pdf"

    if not pdf_path.exists():
        logger.error(f"Paper PDF not found at {pdf_path}")
        raise HTTPException(status_code=404, detail="Paper not found")

    logger.info(f"Paper download request from {ip_address}")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="pgx-lower-paper.pdf"
    )

@app.get("/download/slides")
async def download_slides(request: Request):
    """Serve the slides PDF with download logging."""
    ip_address = request.client.host if request.client else "unknown"

    slides_path = SLIDES_DIR / "slides.pdf"

    if not slides_path.exists():
        logger.error(f"Slides PDF not found at {slides_path}")
        raise HTTPException(status_code=404, detail="Slides not found")

    logger.info(f"Slides download request from {ip_address}")

    return FileResponse(
        slides_path,
        media_type="application/pdf",
        filename="pgx-lower-slides.pdf"
    )

@app.get("/resources/{filename}")
async def get_resource(filename: str):
    """Serve TPC-H query files from resources directory."""
    file_path = RESOURCES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Resource not found")

    # Security check: ensure file is within resources directory
    if not str(file_path.resolve()).startswith(str(RESOURCES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"Serving resource file: {filename}")
    return FileResponse(file_path, media_type="text/plain")

@app.post("/query")
async def execute_query(query_request: QueryRequest, request: Request):
    ip_address = request.client.host if request.client else "unknown"

    request_id = hashlib.md5(query_request.query.encode()).hexdigest()

    logger.info(f"Query request from {ip_address} - request_id: {request_id}")

    try:
        await log_user_request(ip_address, request_id)

        cached_result = await get_cached_query(request_id)
        if cached_result:
            logger.info(f"Cache hit for request_id: {request_id}")
            return {"cached": True, "result": cached_result}

        logger.info(f"Cache miss for request_id: {request_id}, executing query")

        # TODO: Execute query against actual database
        # For now, return dummy result with new format
        result = {
            "main_display": "Query executed successfully. Results shown below.",
            "results": [
                {
                    "database": "postgres",
                    "version": "PostgreSQL 16.3",
                    "latency_ms": 45.2,
                    "outputs": [
                        {
                            "title": "Query Results",
                            "content": "id | value\n1  | dummy\n2  | data",
                            "latency_ms": 12.3
                        },
                        {
                            "title": "Query Plan",
                            "content": "Seq Scan on table\n  Filter: (condition)\n  Rows: 2"
                        }
                    ]
                },
                {
                    "database": "pgx-lower",
                    "version": "pgx-lower 0.1.0 (PostgreSQL 16.3)",
                    "latency_ms": 23.1,
                    "outputs": [
                        {
                            "title": "Optimized Results",
                            "content": "id | value\n1  | dummy\n2  | data",
                            "latency_ms": 8.7
                        }
                    ]
                }
            ]
        }

        await cache_query(request_id, query_request.query, json.dumps(result))
        logger.info(f"Query executed and cached for request_id: {request_id}")

        return {"cached": False, "result": result}
    except Exception as e:
        logger.error(f"Error processing query from {ip_address}: {str(e)}")
        raise
