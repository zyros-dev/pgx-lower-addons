import asyncpg
from typing import List
from .base import DatabaseConnector, QueryOutput

class PostgresConnector(DatabaseConnector):
    """PostgreSQL database connector."""

    def __init__(self, host: str = "localhost", port: int = 5433,
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
            latency_ms=round(analyze_latency, 2)
        ))

        # Then execute the actual SELECT for clean timing
        start = time.time()
        results = await self.conn.fetch(query)
        query_latency = (time.time() - start) * 1000

        # Format results as table
        if results:
            columns = results[0].keys()
            table_lines = [" | ".join(columns)]
            table_lines.append("-" * len(table_lines[0]))

            for row in results:
                table_lines.append(" | ".join(str(row[col]) for col in columns))

            content = "\n".join(table_lines)
        else:
            content = "No results returned"

        outputs.append(QueryOutput(
            title="Query Results",
            content=content,
            latency_ms=round(query_latency, 2)
        ))

        return outputs
