import asyncpg
from typing import List
from .base import DatabaseConnector, QueryOutput

class PgxLowerConnector(DatabaseConnector):
    """pgx-lower database connector."""

    def __init__(self, host: str = "localhost", port: int = 5434,
                 user: str = "pgxuser", password: str = "pgxpassword",
                 database: str = "pgxdb"):
        super().__init__(
            name="pgx-lower",
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.conn = None

    async def connect(self):
        """Establish connection to pgx-lower."""
        self.conn = await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )

    async def disconnect(self):
        """Close pgx-lower connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def get_version(self) -> str:
        """Get pgx-lower version."""
        if not self.conn:
            await self.connect()

        pg_version = await self.conn.fetchval("SELECT version()")
        pg_parts = pg_version.split()
        pg_ver = f"{pg_parts[0]} {pg_parts[1]}"

        # TODO: Get actual pgx-lower version when available
        pgx_version = "0.1.0"

        return f"pgx-lower {pgx_version} ({pg_ver})"

    async def initialize_tables(self):
        """Initialize TPC-H tables if needed."""
        # This will be implemented when we load TPC-H data
        pass

    async def _execute_query(self, query: str) -> List[QueryOutput]:
        """Execute query and return optimized results."""
        if not self.conn:
            await self.connect()

        outputs = []

        # Execute query and get results
        import time
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
            title="Optimized Results",
            content=content,
            latency_ms=round(query_latency, 2)
        ))

        # Get query plan
        start = time.time()
        plan_results = await self.conn.fetch(f"EXPLAIN {query}")
        plan_latency = (time.time() - start) * 1000

        plan_content = "\n".join(row['QUERY PLAN'] for row in plan_results)

        outputs.append(QueryOutput(
            title="Optimized Query Plan",
            content=plan_content,
            latency_ms=round(plan_latency, 2)
        ))

        return outputs
