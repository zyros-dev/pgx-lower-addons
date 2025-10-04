import aiosqlite
from datetime import datetime
import json
from pathlib import Path
import os
import hashlib

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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT NOT NULL,
                query_text TEXT NOT NULL,
                database TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_log_timestamp
            ON query_log(timestamp)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_log_database
            ON query_log(database)
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS performance_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                database TEXT NOT NULL,
                hour_bucket DATETIME NOT NULL,
                query_count INTEGER NOT NULL,
                unique_queries INTEGER NOT NULL,
                min_latency_ms REAL NOT NULL,
                p25_latency_ms REAL NOT NULL,
                p50_latency_ms REAL NOT NULL,
                p75_latency_ms REAL NOT NULL,
                p95_latency_ms REAL NOT NULL,
                p99_latency_ms REAL NOT NULL,
                max_latency_ms REAL NOT NULL,
                mean_latency_ms REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(database, hour_bucket)
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

async def log_query_execution(query: str, database: str, latency_ms: float):
    query_hash = hashlib.sha256(query.strip().encode()).hexdigest()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO query_log (query_hash, query_text, database, latency_ms) VALUES (?, ?, ?, ?)",
            (query_hash, query, database, latency_ms)
        )
        await db.commit()

async def compute_hourly_stats():
    from logger import logger

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT MAX(hour_bucket) FROM performance_stats"
        ) as cursor:
            row = await cursor.fetchone()
            last_computed = row[0] if row[0] else "1970-01-01 00:00:00"

        async with db.execute("""
            SELECT DISTINCT
                datetime(strftime('%Y-%m-%d %H:00:00', timestamp)) as hour_bucket,
                database
            FROM query_log
            WHERE timestamp > ?
            GROUP BY hour_bucket, database
            ORDER BY hour_bucket
        """, (last_computed,)) as cursor:
            buckets = await cursor.fetchall()

        logger.info(f"Computing stats for {len(buckets)} hour buckets")

        for hour_bucket, database in buckets:
            async with db.execute("""
                SELECT latency_ms
                FROM query_log
                WHERE database = ?
                  AND datetime(strftime('%Y-%m-%d %H:00:00', timestamp)) = ?
                ORDER BY latency_ms
            """, (database, hour_bucket)) as cursor:
                latencies = []
                async for row in cursor:
                    latencies.append(row[0])

            if not latencies:
                continue

            n = len(latencies)

            def percentile(data, p):
                k = (len(data) - 1) * p
                f = int(k)
                c = k - f
                if f + 1 < len(data):
                    return data[f] * (1 - c) + data[f + 1] * c
                return data[f]

            async with db.execute("""
                SELECT COUNT(DISTINCT query_hash)
                FROM query_log
                WHERE database = ?
                  AND datetime(strftime('%Y-%m-%d %H:00:00', timestamp)) = ?
            """, (database, hour_bucket)) as cursor:
                unique_count = (await cursor.fetchone())[0]

            stats = {
                "database": database,
                "hour_bucket": hour_bucket,
                "query_count": n,
                "unique_queries": unique_count,
                "min_latency_ms": latencies[0],
                "p25_latency_ms": percentile(latencies, 0.25),
                "p50_latency_ms": percentile(latencies, 0.50),
                "p75_latency_ms": percentile(latencies, 0.75),
                "p95_latency_ms": percentile(latencies, 0.95),
                "p99_latency_ms": percentile(latencies, 0.99),
                "max_latency_ms": latencies[-1],
                "mean_latency_ms": sum(latencies) / n,
            }

            await db.execute("""
                INSERT OR REPLACE INTO performance_stats
                (database, hour_bucket, query_count, unique_queries,
                 min_latency_ms, p25_latency_ms, p50_latency_ms, p75_latency_ms,
                 p95_latency_ms, p99_latency_ms, max_latency_ms, mean_latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stats["database"], stats["hour_bucket"], stats["query_count"], stats["unique_queries"],
                stats["min_latency_ms"], stats["p25_latency_ms"], stats["p50_latency_ms"],
                stats["p75_latency_ms"], stats["p95_latency_ms"], stats["p99_latency_ms"],
                stats["max_latency_ms"], stats["mean_latency_ms"]
            ))

            logger.info(f"Computed stats for {database} at {hour_bucket}: {n} queries, {unique_count} unique")

        await db.commit()

async def get_performance_stats(limit: int = 24):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT database, hour_bucket, query_count, unique_queries,
                   min_latency_ms, p25_latency_ms, p50_latency_ms, p75_latency_ms,
                   p95_latency_ms, p99_latency_ms, max_latency_ms, mean_latency_ms,
                   created_at
            FROM performance_stats
            ORDER BY hour_bucket DESC, database
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()

            return [
                {
                    "database": row[0],
                    "hour_bucket": row[1],
                    "query_count": row[2],
                    "unique_queries": row[3],
                    "min_latency_ms": row[4],
                    "p25_latency_ms": row[5],
                    "p50_latency_ms": row[6],
                    "p75_latency_ms": row[7],
                    "p95_latency_ms": row[8],
                    "p99_latency_ms": row[9],
                    "max_latency_ms": row[10],
                    "mean_latency_ms": row[11],
                    "created_at": row[12],
                }
                for row in rows
            ]
