"""
Debug module with key-based authentication.
"""
import secrets
import base64
from logger import logger
from database import compute_hourly_stats

# Generate debug key at module load
DEBUG_KEY = base64.urlsafe_b64encode(secrets.token_bytes(15))[:20].decode('utf-8')

def init_debug():
    """Initialize debug module and log the key."""
    logger.info(f"=" * 80)
    logger.info(f"DEBUG KEY: {DEBUG_KEY}")
    logger.info(f"=" * 80)

async def handle_debug_request(key: str, request: str, content: str = ""):
    """
    Handle debug requests with key authentication.

    Args:
        key: Authentication key
        request: Debug command to execute
        content: Optional content for the request

    Returns:
        Response dict with status and result
    """
    if key != DEBUG_KEY:
        logger.warning(f"Invalid debug key attempt: {key}")
        return {"error": "Invalid debug key"}

    logger.info(f"Debug request: {request}")

    # Route to appropriate debug function
    if request == "compute_stats":
        return await debug_compute_stats()
    elif request == "query_log_count":
        return await debug_query_log_count()
    elif request == "clear_stats":
        return await debug_clear_stats()
    elif request == "info":
        return debug_info()
    else:
        return {"error": f"Unknown debug request: {request}"}

async def debug_compute_stats():
    """Manually trigger stats computation."""
    try:
        await compute_hourly_stats()
        return {"status": "success", "message": "Stats computation triggered"}
    except Exception as e:
        logger.error(f"Error in debug_compute_stats: {str(e)}")
        return {"status": "error", "message": str(e)}

async def debug_query_log_count():
    """Get count of queries in the log."""
    from database import DB_PATH
    import aiosqlite

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM query_log") as cursor:
                count = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(DISTINCT query_hash) FROM query_log") as cursor:
                unique = (await cursor.fetchone())[0]

        return {
            "status": "success",
            "total_queries": count,
            "unique_queries": unique
        }
    except Exception as e:
        logger.error(f"Error in debug_query_log_count: {str(e)}")
        return {"status": "error", "message": str(e)}

async def debug_clear_stats():
    """Clear performance stats table."""
    from database import DB_PATH
    import aiosqlite

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM performance_stats")
            await db.commit()

        logger.info("Performance stats cleared")
        return {"status": "success", "message": "Performance stats cleared"}
    except Exception as e:
        logger.error(f"Error in debug_clear_stats: {str(e)}")
        return {"status": "error", "message": str(e)}

def debug_info():
    """Get debug module information."""
    return {
        "status": "success",
        "available_requests": [
            "compute_stats - Manually trigger hourly stats computation",
            "query_log_count - Get query log statistics",
            "clear_stats - Clear performance_stats table",
            "info - Show this information"
        ]
    }
