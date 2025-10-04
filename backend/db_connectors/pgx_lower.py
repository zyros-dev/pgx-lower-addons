import asyncpg
from typing import List
from .base import DatabaseConnector, QueryOutput

class PgxLowerConnector(DatabaseConnector):
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
        self.conn = await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )

    async def disconnect(self):
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def get_version(self) -> str:
        if not self.conn:
            await self.connect()

        pg_version = await self.conn.fetchval("SELECT version()")
        pg_parts = pg_version.split()
        pg_ver = f"{pg_parts[0]} {pg_parts[1]}"

        pgx_version = "0.1.0"

        return f"pgx-lower {pgx_version} ({pg_ver})"

    async def initialize_tables(self):
        pass

    async def _execute_query(self, query: str) -> List[QueryOutput]:
        if not self.conn:
            await self.connect()

        outputs = []

        import time
        start = time.time()
        results = await self.conn.fetch(query)
        query_latency = (time.time() - start) * 1000

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
