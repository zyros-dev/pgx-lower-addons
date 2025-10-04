from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import hashlib
import json
from pathlib import Path
from database import init_db, log_user_request, get_cached_query, cache_query, log_query_execution, compute_hourly_stats, get_performance_stats, VERSION
from logger import logger
from db_connectors.postgres import PostgresConnector
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import debug

CONTENT_DIR = Path(__file__).parent / "content"
REPORT_DIR = Path(__file__).parent / "pgx-lower-report"
SLIDES_DIR = Path(__file__).parent / "slides"
RESOURCES_DIR = Path(__file__).parent / "resources"

app = FastAPI(title="pgx-lower API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class DebugRequest(BaseModel):
    key: str
    request: str
    content: str = ""

postgres_connector = PostgresConnector()
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    logger.info("Starting pgx-lower API")
    await init_db()
    logger.info("Database initialized")

    # Initialize debug module
    debug.init_debug()

    # Connect to postgres
    await postgres_connector.connect()
    logger.info("Connected to PostgreSQL")

    # Start scheduler for hourly stats computation
    scheduler.add_job(compute_hourly_stats, 'cron', minute=0, id='hourly_stats')
    scheduler.start()
    logger.info("Scheduler started: hourly stats computation at minute 0 of every hour")

    # Run initial stats computation
    asyncio.create_task(compute_hourly_stats())

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    logger.info("Scheduler stopped")

@app.get("/")
async def root():
    return {"message": "pgx-lower API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/version")
async def get_version():
    return {"version": VERSION}

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
        # cached_result = None
        if cached_result:
            logger.info(f"Cache hit for request_id: {request_id}")
            return {"cached": True, "result": cached_result}

        logger.info(f"Cache miss for request_id: {request_id}, executing query")

        # Execute query against postgres
        postgres_result = await postgres_connector.run(query_request.query)

        # Log query execution for performance tracking
        await log_query_execution(
            query_request.query,
            postgres_result.database,
            postgres_result.latency_ms
        )

        # Format result
        result = {
            "main_display": f"Query executed successfully against {postgres_result.database}.",
            "results": [
                {
                    "database": postgres_result.database,
                    "version": postgres_result.version,
                    "cached": cached_result is not None,
                    "latency_ms": postgres_result.latency_ms,
                    "outputs": [
                        {
                            "content": output.content,
                            "title": output.title,
                            "latency_ms": output.latency_ms
                        }
                        for output in postgres_result.outputs
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

@app.get("/stats/performance")
async def get_stats(limit: int = 24):
    """Get hourly performance statistics."""
    try:
        stats = await get_performance_stats(limit=limit)
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error fetching performance stats: {str(e)}")
        raise

@app.post("/debug")
async def debug_endpoint(debug_request: DebugRequest):
    """Debug endpoint with key authentication."""
    return await debug.handle_debug_request(
        debug_request.key,
        debug_request.request,
        debug_request.content
    )
