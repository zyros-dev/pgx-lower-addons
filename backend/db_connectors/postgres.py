import asyncpg
from typing import List
from .base import DatabaseConnector, QueryOutput

class PostgresConnector(DatabaseConnector):
    """PostgreSQL database connector."""

    def __init__(self, host: str = "postgres", port: int = 5432,
                 user: str = "pgxuser", password: str = "pgxpassword",
                 database: str = "pgxdb"):
        super().__init__(
            name="postgres",
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.conn = None

    async def connect(self):
        """Establish connection to PostgreSQL."""
        self.conn = await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )

    async def disconnect(self):
        """Close PostgreSQL connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def get_version(self) -> str:
        """Get PostgreSQL version."""
        if not self.conn:
            await self.connect()

        result = await self.conn.fetchval("SELECT version()")
        # Extract version number (e.g., "PostgreSQL 17.5")
        version_parts = result.split()
        return f"{version_parts[0]} {version_parts[1]}"

    async def initialize_tables(self):
        """Initialize TPC-H tables if needed."""
        # This will be implemented when we load TPC-H data
        pass

    async def _execute_query(self, query: str) -> List[QueryOutput]:
        """Execute query and return results."""
        if not self.conn:
            await self.connect()

        outputs = []

        # First, get EXPLAIN ANALYZE (for plan with execution stats)
        import time
        start = time.time()
        analyze_results = await self.conn.fetch(f"EXPLAIN ANALYZE {query}")
        analyze_latency = (time.time() - start) * 1000

        analyze_content = "\n".join(row['QUERY PLAN'] for row in analyze_results)

        outputs.append(QueryOutput(
            title="Query Plan (EXPLAIN ANALYZE)",
            content=analyze_content,
            latency_ms=None  # Don't include EXPLAIN time in total
        ))

        # Then execute the actual SELECT for clean timing
        start = time.time()
        results = await self.conn.fetch(query)
        query_latency = (time.time() - start) * 1000

        # Format results as table
        if results:
            columns = list(results[0].keys())
            table_lines = [" | ".join(columns)]
            table_lines.append("-" * len(table_lines[0]))

            for row in results:
                row_values = [str(row[col]) if row[col] is not None else "NULL" for col in columns]
                table_lines.append(" | ".join(row_values))

            content = "\n".join(table_lines)
        else:
            content = "No results returned"

        outputs.append(QueryOutput(
            title="Query Results",
            content=content,
            latency_ms=round(query_latency, 2)
        ))

        return outputs
