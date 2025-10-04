import aiosqlite
from datetime import datetime
import json
from pathlib import Path
import os

DB_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).parent / "database" / "pgx_lower.db"))
VERSION = "0.1.0"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                request_id TEXT NOT NULL,
                version TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                request_id TEXT PRIMARY KEY,
                input_json TEXT NOT NULL,
                output_json TEXT NOT NULL
            )
        """)

        await db.commit()

async def log_user_request(ip_address: str, request_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_requests (ip_address, request_id, version) VALUES (?, ?, ?)",
            (ip_address, request_id, VERSION)
        )
        await db.commit()

async def get_cached_query(request_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT output_json FROM queries WHERE request_id = ?",
            (request_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
    return None

async def cache_query(request_id: str, input_json: str, output_json: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO queries (request_id, input_json, output_json) VALUES (?, ?, ?)",
            (request_id, input_json, output_json)
        )
        await db.commit()
