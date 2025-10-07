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
from datetime import datetime, timedelta
from collections import defaultdict
from analytics import analytics

CONTENT_DIR = Path(__file__).parent / "content"
REPORT_DIR = Path(__file__).parent / "pgx-lower-report"
SLIDES_DIR = Path(__file__).parent / "slides"
RESOURCES_DIR = Path(__file__).parent / "resources"

app = FastAPI(title="pgx-lower API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost",
        "http://pgx.zyros.dev",
        "https://zyros.dev",
        "https://pgx.zyros.dev"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

MAX_QUERY_LENGTH = 10000

class DebugRequest(BaseModel):
    key: str
    request: str
    content: str = ""

postgres_connector = PostgresConnector()
scheduler = AsyncIOScheduler()

rate_limit_store = defaultdict(lambda: {"cached": [], "uncached": []})
MAX_CACHED_QUERIES_PER_MINUTE = 100
MAX_UNCACHED_QUERIES_PER_MINUTE = 10

def check_rate_limit(ip_address: str, is_cached: bool) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(minutes=1)

    query_type = "cached" if is_cached else "uncached"
    max_queries = MAX_CACHED_QUERIES_PER_MINUTE if is_cached else MAX_UNCACHED_QUERIES_PER_MINUTE

    rate_limit_store[ip_address][query_type] = [
        timestamp for timestamp in rate_limit_store[ip_address][query_type]
        if timestamp > cutoff
    ]

    if len(rate_limit_store[ip_address][query_type]) >= max_queries:
        return False

    rate_limit_store[ip_address][query_type].append(now)
    return True

@app.on_event("startup")
async def startup():
    logger.info("Starting pgx-lower API")
    await init_db()
    logger.info("Database initialized")

    debug.init_debug()
    await postgres_connector.connect()
    logger.info("Connected to PostgreSQL")
    scheduler.add_job(compute_hourly_stats, 'cron', minute=0, id='hourly_stats')
    scheduler.start()
    logger.info("Scheduler started: hourly stats computation at minute 0 of every hour")
    asyncio.create_task(compute_hourly_stats())

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
    await analytics.close()
    logger.info("Analytics client closed")

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
    file_path = CONTENT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not str(file_path.resolve()).startswith(str(CONTENT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"Serving content file: {filename}")
    return FileResponse(file_path)

@app.get("/resources/{filename}")
async def get_resource(filename: str):
    file_path = RESOURCES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not str(file_path.resolve()).startswith(str(RESOURCES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"Serving resource file: {filename}")
    return FileResponse(file_path)

@app.get("/download/paper")
async def download_paper(request: Request):
    ip_address = request.client.host if request.client else "unknown"
    pdf_path = REPORT_DIR / "main.pdf"

    if not pdf_path.exists():
        logger.error(f"Paper PDF not found at {pdf_path}")
        raise HTTPException(status_code=404, detail="Paper not found")

    logger.info(f"Paper download request from {ip_address}")

    asyncio.create_task(analytics.track_event(
        "download",
        {"content_type": "paper", "ip_address": ip_address},
        client_id=ip_address
    ))

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="pgx-lower-paper.pdf"
    )

@app.get("/download/slides")
async def download_slides(request: Request):
    ip_address = request.client.host if request.client else "unknown"

    slides_path = SLIDES_DIR / "slides.pdf"

    if not slides_path.exists():
        logger.error(f"Slides PDF not found at {slides_path}")
        raise HTTPException(status_code=404, detail="Slides not found")

    logger.info(f"Slides download request from {ip_address}")

    asyncio.create_task(analytics.track_event(
        "download",
        {"content_type": "slides", "ip_address": ip_address},
        client_id=ip_address
    ))

    return FileResponse(
        slides_path,
        media_type="application/pdf",
        filename="pgx-lower-slides.pdf"
    )

@app.get("/resources/{filename}")
async def get_resource(filename: str):
    file_path = RESOURCES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Resource not found")

    if not str(file_path.resolve()).startswith(str(RESOURCES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"Serving resource file: {filename}")
    return FileResponse(file_path, media_type="text/plain")

@app.post("/query")
async def execute_query(query_request: QueryRequest, request: Request):
    ip_address = request.client.host if request.client else "unknown"

    if len(query_request.query) > MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail=f"Query too long. Maximum {MAX_QUERY_LENGTH} characters.")

    request_id = hashlib.md5(query_request.query.encode()).hexdigest()

    try:
        await log_user_request(ip_address, request_id)

        cached_result = await get_cached_query(request_id)
        is_cached = cached_result is not None

        if not check_rate_limit(ip_address, is_cached):
            limit = MAX_CACHED_QUERIES_PER_MINUTE if is_cached else MAX_UNCACHED_QUERIES_PER_MINUTE
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Maximum {limit} {'cached' if is_cached else 'uncached'} queries per minute.")

        logger.info(f"Query request from {ip_address} - request_id: {request_id} - cached: {is_cached}")

        asyncio.create_task(analytics.track_event(
            "query_execution",
            {"cached": is_cached, "ip_address": ip_address},
            client_id=ip_address
        ))

        if cached_result:
            logger.info(f"Cache hit for request_id: {request_id}")
            return {"cached": True, "result": cached_result}

        logger.info(f"Cache miss for request_id: {request_id}, executing query")

        postgres_result = await postgres_connector.run(query_request.query)

        await log_query_execution(
            query_request.query,
            postgres_result.database,
            postgres_result.latency_ms
        )

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
    try:
        stats = await get_performance_stats(limit=limit)
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error fetching performance stats: {str(e)}")
        raise

@app.post("/debug")
async def debug_endpoint(debug_request: DebugRequest):
    return await debug.handle_debug_request(
        debug_request.key,
        debug_request.request,
        debug_request.content
    )
